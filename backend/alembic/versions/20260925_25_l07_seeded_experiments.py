"""Bounded experiment briefs and durable reviewed Idea advice.

Revision ID: 20260925_25
Revises: 20260924_24
"""

from alembic import op

revision = "20260925_25"
down_revision = "20260924_24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
ALTER FUNCTION record_payload_valid(text,jsonb) RENAME TO record_payload_valid_before_l07;
CREATE FUNCTION record_payload_valid(kind text, value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE WHEN kind='EXPERIMENT_BRIEF' AND value ? 'target_customer' THEN
   record_json_exact(value,ARRAY['objective','target_customer','problem','geographies',
     'commercial_boundaries','budget_usd','evidence_definitions','launch_stage'])
   AND record_nonempty_text(value->'objective')
   AND record_nonempty_text(value->'target_customer')
   AND record_nonempty_text(value->'problem')
   AND record_nonempty_text(value->'commercial_boundaries')
   AND record_nonempty_text_array(value->'geographies')
   AND record_nonempty_text_array(value->'evidence_definitions')
   AND value->>'launch_stage'='SHADOW'
   AND value->>'budget_usd' ~ '^[0-9]+(\.[0-9]{1,2})?$'
   AND (value->>'budget_usd')::numeric>0
   AND jsonb_array_length(value->'geographies') =
     (SELECT count(DISTINCT item) FROM jsonb_array_elements(value->'geographies') item)
 ELSE record_payload_valid_before_l07(kind,value) END
$$;
CREATE TABLE record_idea_refinements (
 run_id uuid PRIMARY KEY,
 experiment_id uuid NOT NULL REFERENCES record_experiments(id),
 cycle_id uuid NOT NULL REFERENCES record_cycles(id),
 seed_artifact_id uuid NOT NULL REFERENCES record_artifacts(id),
 operation_id uuid NOT NULL REFERENCES gov_operations(id),
 state varchar(32) NOT NULL,
 advice_source varchar(16) NOT NULL,
 advice jsonb,
 output_hash varchar(64),
 created_at timestamptz NOT NULL,
 finished_at timestamptz,
 CHECK(state IN ('RUNNING','SUCCEEDED','REFINEMENT_FAILED','REFINEMENT_BLOCKED')),
 CHECK(advice_source IN ('RECORDED_FAKE','OPENAI')),
 CHECK((state='RUNNING' AND advice IS NULL AND output_hash IS NULL AND finished_at IS NULL)
    OR (state IN ('REFINEMENT_FAILED','REFINEMENT_BLOCKED') AND advice IS NULL AND output_hash IS NULL AND finished_at IS NOT NULL)
    OR (state='SUCCEEDED' AND advice IS NOT NULL AND output_hash ~ '^[0-9a-f]{64}$' AND finished_at IS NOT NULL))
);
CREATE INDEX ix_record_idea_refinements_cycle ON record_idea_refinements(cycle_id,created_at DESC);
CREATE FUNCTION record_idea_refinement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER record_idea_refinement_guard BEFORE INSERT OR UPDATE OR DELETE
 ON record_idea_refinements FOR EACH ROW EXECUTE FUNCTION record_idea_refinement_guard();
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM record_idea_refinements) OR
    EXISTS(SELECT 1 FROM record_artifacts WHERE kind='EXPERIMENT_BRIEF' AND payload ? 'target_customer')
 THEN RAISE EXCEPTION 'cannot discard L07 experiment evidence'; END IF;
END $$;
DROP TABLE record_idea_refinements;
DROP FUNCTION record_idea_refinement_guard();
DROP FUNCTION record_payload_valid(text,jsonb);
ALTER FUNCTION record_payload_valid_before_l07(text,jsonb) RENAME TO record_payload_valid;
""")
