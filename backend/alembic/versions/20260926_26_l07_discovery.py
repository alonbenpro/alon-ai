"""Durable system discovery batches and selected-candidate refinement.

Revision ID: 20260926_26
Revises: 20260925_25
"""

from alembic import op

revision = "20260926_26"
down_revision = "20260925_25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE TABLE record_idea_discoveries (
 run_id uuid PRIMARY KEY,
 experiment_id uuid NOT NULL REFERENCES record_experiments(id),
 operation_id uuid NOT NULL REFERENCES gov_operations(id),
 state varchar(32) NOT NULL,
 advice_source varchar(16) NOT NULL,
 advice jsonb,
 output_hash varchar(64),
 candidate_ids jsonb,
 created_at timestamptz NOT NULL,
 finished_at timestamptz,
 CHECK(state IN ('RUNNING','SUCCEEDED','DISCOVERY_FAILED','DISCOVERY_BLOCKED')),
 CHECK(advice_source IN ('RECORDED_FAKE','OPENAI')),
 CHECK((state='RUNNING' AND candidate_ids IS NULL AND finished_at IS NULL)
   OR (state='SUCCEEDED' AND advice IS NOT NULL AND output_hash ~ '^[0-9a-f]{64}$'
     AND jsonb_array_length(candidate_ids) BETWEEN 3 AND 5 AND finished_at IS NOT NULL)
   OR (state IN ('DISCOVERY_FAILED','DISCOVERY_BLOCKED') AND candidate_ids IS NULL AND finished_at IS NOT NULL))
);
CREATE INDEX ix_record_idea_discoveries_experiment ON record_idea_discoveries(experiment_id,created_at DESC);
CREATE FUNCTION record_idea_discovery_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE intent openai_run_intents; operation gov_operations;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'discovery history is immutable'; END IF;
 IF TG_OP='UPDATE' AND (OLD.state<>'RUNNING' OR NEW.state='RUNNING'
   OR (to_jsonb(OLD)-ARRAY['state','advice','output_hash','candidate_ids','finished_at'])
      IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['state','advice','output_hash','candidate_ids','finished_at']))
 THEN RAISE EXCEPTION 'discovery identity or terminal result is immutable'; END IF;
 SELECT * INTO operation FROM gov_operations WHERE id=NEW.operation_id AND experiment_id=NEW.experiment_id;
 IF operation.id IS NULL THEN RAISE EXCEPTION 'discovery scope mismatch'; END IF;
 IF NEW.state='SUCCEEDED' THEN
  SELECT * INTO intent FROM openai_run_intents WHERE idempotency_key=NEW.run_id
    AND experiment_id=NEW.experiment_id AND operation_id=NEW.operation_id
    AND outcome='SUCCEEDED' AND output_hash=NEW.output_hash;
  IF intent.idempotency_key IS NULL THEN RAISE EXCEPTION 'discovery output is not a governed run'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_idea_discovery_guard BEFORE INSERT OR UPDATE OR DELETE
 ON record_idea_discoveries FOR EACH ROW EXECUTE FUNCTION record_idea_discovery_guard();
CREATE TABLE record_idea_intent_reviews (
 run_id uuid PRIMARY KEY REFERENCES record_idea_refinements(run_id),
 experiment_id uuid NOT NULL REFERENCES record_experiments(id),
 cycle_id uuid NOT NULL REFERENCES record_cycles(id),
 source_artifact_id uuid NOT NULL REFERENCES record_artifacts(id),
 output_hash varchar(64) NOT NULL,
 relationship varchar(32) NOT NULL,
 rationale varchar(4000) NOT NULL,
 confirmed_by uuid NOT NULL,
 command_key uuid NOT NULL UNIQUE,
 created_at timestamptz NOT NULL,
 CHECK(relationship IN ('PRESERVES_CORE_INTENT','CLARIFIES_CORE_INTENT','NARROWS_CORE_INTENT')),
 CHECK(length(btrim(rationale)) BETWEEN 1 AND 4000),
 CHECK(output_hash ~ '^[0-9a-f]{64}$')
);
CREATE FUNCTION record_idea_intent_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE refinement record_idea_refinements; source record_artifacts;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'intent review is immutable'; END IF;
 SELECT * INTO refinement FROM record_idea_refinements WHERE run_id=NEW.run_id
   AND experiment_id=NEW.experiment_id AND cycle_id=NEW.cycle_id
   AND seed_artifact_id=NEW.source_artifact_id AND output_hash=NEW.output_hash
   AND state='SUCCEEDED';
 SELECT * INTO source FROM record_artifacts WHERE id=NEW.source_artifact_id
   AND experiment_id=NEW.experiment_id AND kind IN ('IDEA_SEED','IDEA_CANDIDATE');
 IF refinement.run_id IS NULL OR source.id IS NULL
 THEN RAISE EXCEPTION 'intent review must bind exact successful output and source'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_idea_intent_review_guard BEFORE INSERT OR UPDATE OR DELETE
 ON record_idea_intent_reviews FOR EACH ROW EXECUTE FUNCTION record_idea_intent_review_guard();
CREATE OR REPLACE FUNCTION record_idea_refinement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE intent openai_run_intents; cycle record_cycles; operation gov_operations;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'refinement history is immutable'; END IF;
 IF TG_OP='UPDATE' AND (OLD.state<>'RUNNING' OR NEW.state='RUNNING'
   OR (to_jsonb(OLD)-ARRAY['state','advice','output_hash','finished_at'])
      IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['state','advice','output_hash','finished_at']))
 THEN RAISE EXCEPTION 'refinement identity or terminal result is immutable'; END IF;
 SELECT * INTO cycle FROM record_cycles WHERE id=NEW.cycle_id AND experiment_id=NEW.experiment_id
   AND seed_artifact_id=NEW.seed_artifact_id AND purpose='INITIAL'
   AND idea_mode IN ('USER_SEEDED_REFINEMENT','SYSTEM_DISCOVERY');
 SELECT * INTO operation FROM gov_operations WHERE id=NEW.operation_id AND experiment_id=NEW.experiment_id;
 IF cycle.id IS NULL OR operation.id IS NULL THEN RAISE EXCEPTION 'refinement scope mismatch'; END IF;
 IF NEW.state='SUCCEEDED' THEN
  SELECT * INTO intent FROM openai_run_intents WHERE idempotency_key=NEW.run_id
    AND experiment_id=NEW.experiment_id AND operation_id=NEW.operation_id
    AND outcome='SUCCEEDED' AND output_hash=NEW.output_hash;
  IF intent.idempotency_key IS NULL THEN RAISE EXCEPTION 'refinement output is not a successful governed run'; END IF;
 END IF;
 RETURN NEW;
END $$;
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM record_idea_discoveries)
 OR EXISTS(SELECT 1 FROM record_idea_intent_reviews)
 OR EXISTS(SELECT 1 FROM record_idea_refinements r JOIN record_cycles c ON c.id=r.cycle_id
   WHERE c.idea_mode='SYSTEM_DISCOVERY')
 THEN RAISE EXCEPTION 'cannot discard L07 discovery evidence'; END IF;
END $$;
DROP TABLE record_idea_discoveries;
DROP FUNCTION record_idea_discovery_guard();
DROP TABLE record_idea_intent_reviews;
DROP FUNCTION record_idea_intent_review_guard();
CREATE OR REPLACE FUNCTION record_idea_refinement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE intent openai_run_intents; cycle record_cycles; operation gov_operations;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'refinement history is immutable'; END IF;
 IF TG_OP='UPDATE' AND (OLD.state<>'RUNNING' OR NEW.state='RUNNING'
   OR (to_jsonb(OLD)-ARRAY['state','advice','output_hash','finished_at'])
      IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['state','advice','output_hash','finished_at']))
 THEN RAISE EXCEPTION 'refinement identity or terminal result is immutable'; END IF;
 SELECT * INTO cycle FROM record_cycles WHERE id=NEW.cycle_id AND experiment_id=NEW.experiment_id
   AND seed_artifact_id=NEW.seed_artifact_id AND idea_mode='USER_SEEDED_REFINEMENT' AND purpose='INITIAL';
 SELECT * INTO operation FROM gov_operations WHERE id=NEW.operation_id AND experiment_id=NEW.experiment_id;
 IF cycle.id IS NULL OR operation.id IS NULL THEN RAISE EXCEPTION 'refinement scope mismatch'; END IF;
 IF NEW.state='SUCCEEDED' THEN
  SELECT * INTO intent FROM openai_run_intents WHERE idempotency_key=NEW.run_id
    AND experiment_id=NEW.experiment_id AND operation_id=NEW.operation_id
    AND outcome='SUCCEEDED' AND output_hash=NEW.output_hash;
  IF intent.idempotency_key IS NULL
  THEN RAISE EXCEPTION 'refinement output is not a successful governed run'; END IF;
 END IF;
 RETURN NEW;
END $$;
""")
