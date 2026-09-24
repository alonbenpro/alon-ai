"""Immutable OpenAI execution intent and one terminal result binding.

Revision ID: 20260924_22
Revises: 20260923_21
"""

from alembic import op

revision = "20260924_22"
down_revision = "20260923_21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE openai_run_intents (
 idempotency_key UUID PRIMARY KEY,
 config_id UUID NOT NULL,
 config_version UUID NOT NULL,
 experiment_id UUID NOT NULL,
 workflow_id UUID NOT NULL,
 operation_id UUID NOT NULL,
 agent_run_id UUID REFERENCES gov_agents(id),
 prompt_version VARCHAR(64) NOT NULL,
 prompt_hash VARCHAR(64) NOT NULL,
 schema_version VARCHAR(64) NOT NULL,
 output_schema_hash VARCHAR(64) NOT NULL,
 model_identifier VARCHAR(100) NOT NULL,
 reasoning_effort VARCHAR(16) NOT NULL,
 accepted_input_refs UUID[] NOT NULL,
 input_hash VARCHAR(64) NOT NULL,
 client_request_id UUID NOT NULL,
 created_at TIMESTAMPTZ NOT NULL,
 call_id UUID UNIQUE REFERENCES gov_calls(id),
 outcome VARCHAR(32) NOT NULL,
 output_hash VARCHAR(64),
 finished_at TIMESTAMPTZ,
 FOREIGN KEY(config_id,workflow_id,config_version)
  REFERENCES gov_configs(id,workflow_id,version),
 FOREIGN KEY(operation_id,workflow_id,experiment_id,config_version)
  REFERENCES gov_operations(id,workflow_id,experiment_id,config_version),
 CHECK(input_hash ~ '^[0-9a-f]{64}$'),
 CHECK(prompt_hash ~ '^[0-9a-f]{64}$'),
 CHECK(output_schema_hash ~ '^[0-9a-f]{64}$'),
 CHECK(output_hash IS NULL OR output_hash ~ '^[0-9a-f]{64}$'),
 CHECK(length(prompt_version) BETWEEN 1 AND 64),
 CHECK(length(schema_version) BETWEEN 1 AND 64),
 CHECK(length(model_identifier) BETWEEN 1 AND 100),
 CHECK(reasoning_effort IN ('none','minimal','low','medium','high','xhigh')),
 CHECK(outcome IN ('NO_AI','READY','SUCCEEDED','REFUSED','SCHEMA_MISMATCH',
                   'INCOMPLETE','TIMEOUT','FAILED','UNCERTAIN','CANCELLED')),
 CHECK((outcome='READY' AND call_id IS NULL AND output_hash IS NULL AND finished_at IS NULL)
    OR (outcome<>'READY' AND finished_at IS NOT NULL)),
 CHECK(outcome<>'NO_AI' OR call_id IS NULL)
);
CREATE INDEX ix_openai_run_intents_operation ON openai_run_intents(operation_id,created_at);
CREATE FUNCTION openai_run_intent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'OpenAI run intent cannot be deleted'; END IF;
 IF (to_jsonb(NEW)-ARRAY['call_id','outcome','output_hash','finished_at'])
    IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['call_id','outcome','output_hash','finished_at'])
    OR OLD.outcome<>'READY' OR NEW.outcome='READY'
 THEN RAISE EXCEPTION 'OpenAI run identity or terminal result is immutable'; END IF;
 IF NEW.call_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM gov_calls c WHERE c.id=NEW.call_id
   AND c.idempotency_key=NEW.idempotency_key
   AND c.config_id=NEW.config_id AND c.config_version=NEW.config_version
   AND c.experiment_id=NEW.experiment_id AND c.workflow_id=NEW.workflow_id
   AND c.operation_id=NEW.operation_id
 ) THEN RAISE EXCEPTION 'OpenAI run call lineage mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER openai_run_intent_immutable BEFORE UPDATE OR DELETE ON openai_run_intents
 FOR EACH ROW EXECUTE FUNCTION openai_run_intent_guard();
""")


def downgrade() -> None:
    op.execute("""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM openai_run_intents) THEN
  RAISE EXCEPTION 'cannot discard OpenAI run evidence';
 END IF;
END $$;
DROP TABLE openai_run_intents;
DROP FUNCTION openai_run_intent_guard();
""")
