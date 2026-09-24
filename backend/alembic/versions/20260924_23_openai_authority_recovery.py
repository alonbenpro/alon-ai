"""Durable dispatch authority and truthful OpenAI recovery states.

Revision ID: 20260924_23
Revises: 20260924_22
"""

from alembic import op

revision = "20260924_23"
down_revision = "20260924_22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE openai_premium_approvals (
 authorization_id UUID PRIMARY KEY,
 scope UUID NOT NULL,
 config_id UUID NOT NULL REFERENCES gov_configs(id),
 approved_by UUID NOT NULL,
 approved_at TIMESTAMPTZ NOT NULL,
 expires_at TIMESTAMPTZ NOT NULL,
 revoked_at TIMESTAMPTZ,
 UNIQUE(authorization_id, config_id),
 CHECK(approved_at < expires_at),
 CHECK(revoked_at IS NULL OR revoked_at >= approved_at)
);
CREATE TABLE openai_route_decisions (
 idempotency_key UUID PRIMARY KEY,
 experiment_id UUID NOT NULL,
 workflow_id UUID NOT NULL,
 operation_id UUID NOT NULL,
 config_version UUID NOT NULL,
 correlation_id UUID NOT NULL,
 logical_operation_id UUID NOT NULL,
 attribution_hash VARCHAR(64) NOT NULL,
 facts_hash VARCHAR(64) NOT NULL,
 route VARCHAR(16) NOT NULL,
 config_id UUID,
 approval_id UUID,
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(operation_id, workflow_id, experiment_id, config_version)
  REFERENCES gov_operations(id, workflow_id, experiment_id, config_version),
 FOREIGN KEY(config_id, workflow_id, config_version)
  REFERENCES gov_configs(id, workflow_id, version),
 FOREIGN KEY(approval_id, config_id)
  REFERENCES openai_premium_approvals(authorization_id, config_id),
 CHECK(attribution_hash ~ '^[0-9a-f]{64}$'),
 CHECK(facts_hash ~ '^[0-9a-f]{64}$'),
 CHECK(route IN ('NO_AI','CHEAP','STRONGER','PREMIUM')),
 CHECK((route='NO_AI' AND config_id IS NULL AND approval_id IS NULL)
    OR (route IN ('CHEAP','STRONGER') AND config_id IS NOT NULL AND approval_id IS NULL)
    OR (route='PREMIUM' AND config_id IS NOT NULL AND approval_id IS NOT NULL))
);
CREATE INDEX ix_openai_route_decisions_operation
 ON openai_route_decisions(operation_id, created_at);
CREATE FUNCTION openai_premium_approval_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'OpenAI premium approval cannot be deleted'; END IF;
 IF (to_jsonb(NEW)-ARRAY['revoked_at']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['revoked_at'])
    OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at)
    OR (NEW.revoked_at IS NOT NULL AND NEW.revoked_at < OLD.approved_at) THEN
  RAISE EXCEPTION 'OpenAI premium approval is immutable except first revocation';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER openai_premium_approval_immutable BEFORE UPDATE OR DELETE
 ON openai_premium_approvals FOR EACH ROW EXECUTE FUNCTION openai_premium_approval_guard();
CREATE FUNCTION openai_route_decision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'OpenAI route decision is immutable';
END $$;
CREATE TRIGGER openai_route_decision_immutable BEFORE UPDATE OR DELETE
 ON openai_route_decisions FOR EACH ROW EXECUTE FUNCTION openai_route_decision_guard();

DROP TRIGGER openai_run_intent_immutable ON openai_run_intents;
DROP FUNCTION openai_run_intent_guard();
DO $$ DECLARE constraint_name text; BEGIN
 FOR constraint_name IN SELECT conname FROM pg_constraint
  WHERE conrelid='openai_run_intents'::regclass AND contype='c'
 LOOP
  EXECUTE format('ALTER TABLE openai_run_intents DROP CONSTRAINT %I', constraint_name);
 END LOOP;
END $$;
UPDATE openai_run_intents i SET outcome='RESULT_UNAVAILABLE'
 WHERE i.outcome='SUCCEEDED'
   AND NOT EXISTS(SELECT 1 FROM gov_calls c WHERE c.id=i.call_id AND c.state='FINAL');
ALTER TABLE openai_run_intents
 ADD CONSTRAINT openai_run_intents_input_hash_check CHECK(input_hash ~ '^[0-9a-f]{64}$'),
 ADD CONSTRAINT openai_run_intents_prompt_hash_check CHECK(prompt_hash ~ '^[0-9a-f]{64}$'),
 ADD CONSTRAINT openai_run_intents_schema_hash_check CHECK(output_schema_hash ~ '^[0-9a-f]{64}$'),
 ADD CONSTRAINT openai_run_intents_output_hash_check CHECK(output_hash IS NULL OR output_hash ~ '^[0-9a-f]{64}$'),
 ADD CONSTRAINT openai_run_intents_prompt_version_check CHECK(length(prompt_version) BETWEEN 1 AND 64),
 ADD CONSTRAINT openai_run_intents_schema_version_check CHECK(length(schema_version) BETWEEN 1 AND 64),
 ADD CONSTRAINT openai_run_intents_model_identifier_check CHECK(length(model_identifier) BETWEEN 1 AND 100),
 ADD CONSTRAINT openai_run_intents_reasoning_effort_check CHECK(reasoning_effort IN ('none','minimal','low','medium','high','xhigh')),
 ADD CONSTRAINT openai_run_intents_outcome_check CHECK(outcome IN ('NO_AI','READY','SUCCEEDED','REFUSED','SCHEMA_MISMATCH','INCOMPLETE','TIMEOUT','FAILED','UNCERTAIN','CANCELLED','RECOVERING','RESULT_UNAVAILABLE')),
 ADD CONSTRAINT openai_run_intents_lifecycle_check CHECK(
  (outcome='READY' AND call_id IS NULL AND output_hash IS NULL AND finished_at IS NULL)
  OR (outcome='RECOVERING' AND output_hash IS NULL AND finished_at IS NULL)
  OR (outcome NOT IN ('READY','RECOVERING') AND finished_at IS NOT NULL)),
 ADD CONSTRAINT openai_run_intents_no_ai_call_check CHECK(outcome<>'NO_AI' OR call_id IS NULL);
CREATE FUNCTION openai_run_intent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'OpenAI run intent cannot be deleted'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.outcome<>'READY' THEN RAISE EXCEPTION 'OpenAI run must begin READY'; END IF;
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW)-ARRAY['call_id','outcome','output_hash','finished_at'])
    IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['call_id','outcome','output_hash','finished_at']) THEN
  RAISE EXCEPTION 'OpenAI run identity is immutable';
 END IF;
 IF NOT ((OLD.outcome='READY' AND NEW.outcome NOT IN ('READY','RECOVERING'))
      OR (OLD.outcome='READY' AND NEW.outcome='RECOVERING')
      OR (OLD.outcome='RECOVERING' AND NEW.outcome NOT IN ('READY','RECOVERING'))) THEN
  RAISE EXCEPTION 'OpenAI run result is immutable';
 END IF;
 IF NEW.call_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM gov_calls c WHERE c.id=NEW.call_id
   AND c.idempotency_key=NEW.idempotency_key AND c.config_id=NEW.config_id
   AND c.config_version=NEW.config_version AND c.experiment_id=NEW.experiment_id
   AND c.workflow_id=NEW.workflow_id AND c.operation_id=NEW.operation_id
 ) THEN RAISE EXCEPTION 'OpenAI run call lineage mismatch'; END IF;
 IF NEW.outcome='SUCCEEDED' AND (NEW.output_hash IS NULL OR NOT EXISTS(
  SELECT 1 FROM gov_calls c WHERE c.id=NEW.call_id AND c.state='FINAL'
   AND c.result_metadata->>'status'='SUCCEEDED'
 )) THEN RAISE EXCEPTION 'OpenAI succeeded run requires final usage ledger'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER openai_run_intent_immutable BEFORE INSERT OR UPDATE OR DELETE ON openai_run_intents
 FOR EACH ROW EXECUTE FUNCTION openai_run_intent_guard();
""")


def downgrade() -> None:
    op.execute("""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM openai_premium_approvals)
    OR EXISTS(SELECT 1 FROM openai_route_decisions)
    OR EXISTS(SELECT 1 FROM openai_run_intents WHERE outcome IN ('RECOVERING','RESULT_UNAVAILABLE')) THEN
  RAISE EXCEPTION 'cannot discard OpenAI authority or recovery evidence';
 END IF;
END $$;
DROP TRIGGER openai_run_intent_immutable ON openai_run_intents;
DROP FUNCTION openai_run_intent_guard();
DO $$ DECLARE constraint_name text; BEGIN
 FOR constraint_name IN SELECT conname FROM pg_constraint
  WHERE conrelid='openai_run_intents'::regclass AND contype='c'
 LOOP
  EXECUTE format('ALTER TABLE openai_run_intents DROP CONSTRAINT %I', constraint_name);
 END LOOP;
END $$;
ALTER TABLE openai_run_intents
 ADD CHECK(input_hash ~ '^[0-9a-f]{64}$'),
 ADD CHECK(prompt_hash ~ '^[0-9a-f]{64}$'),
 ADD CHECK(output_schema_hash ~ '^[0-9a-f]{64}$'),
 ADD CHECK(output_hash IS NULL OR output_hash ~ '^[0-9a-f]{64}$'),
 ADD CHECK(length(prompt_version) BETWEEN 1 AND 64),
 ADD CHECK(length(schema_version) BETWEEN 1 AND 64),
 ADD CHECK(length(model_identifier) BETWEEN 1 AND 100),
 ADD CHECK(reasoning_effort IN ('none','minimal','low','medium','high','xhigh')),
 ADD CHECK(outcome IN ('NO_AI','READY','SUCCEEDED','REFUSED','SCHEMA_MISMATCH','INCOMPLETE','TIMEOUT','FAILED','UNCERTAIN','CANCELLED')),
 ADD CHECK((outcome='READY' AND call_id IS NULL AND output_hash IS NULL AND finished_at IS NULL) OR (outcome<>'READY' AND finished_at IS NOT NULL)),
 ADD CHECK(outcome<>'NO_AI' OR call_id IS NULL);
CREATE FUNCTION openai_run_intent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'OpenAI run intent cannot be deleted'; END IF;
 IF (to_jsonb(NEW)-ARRAY['call_id','outcome','output_hash','finished_at'])
    IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['call_id','outcome','output_hash','finished_at'])
    OR OLD.outcome<>'READY' OR NEW.outcome='READY' THEN
  RAISE EXCEPTION 'OpenAI run identity or terminal result is immutable';
 END IF;
 IF NEW.call_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM gov_calls c WHERE c.id=NEW.call_id AND c.idempotency_key=NEW.idempotency_key
   AND c.config_id=NEW.config_id AND c.config_version=NEW.config_version
   AND c.experiment_id=NEW.experiment_id AND c.workflow_id=NEW.workflow_id
   AND c.operation_id=NEW.operation_id
 ) THEN RAISE EXCEPTION 'OpenAI run call lineage mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER openai_run_intent_immutable BEFORE UPDATE OR DELETE ON openai_run_intents
 FOR EACH ROW EXECUTE FUNCTION openai_run_intent_guard();
DROP TRIGGER openai_route_decision_immutable ON openai_route_decisions;
DROP FUNCTION openai_route_decision_guard();
DROP TABLE openai_route_decisions;
DROP TRIGGER openai_premium_approval_immutable ON openai_premium_approvals;
DROP FUNCTION openai_premium_approval_guard();
DROP TABLE openai_premium_approvals;
""")
