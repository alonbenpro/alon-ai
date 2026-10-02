"""Durable R01A Idea run admission and operator status."""

from alembic import op

revision = "20260928_29"
down_revision = "20260927_28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE record_agent_runs (
 run_id uuid PRIMARY KEY,
 command_key uuid NOT NULL UNIQUE,
 experiment_id uuid NOT NULL REFERENCES record_experiments(id),
 operator_id uuid NOT NULL REFERENCES record_operators(id),
 task_kind varchar(32) NOT NULL CHECK(task_kind IN ('IDEA_DISCOVERY','IDEA_REFINEMENT')),
 request_hash varchar(64) NOT NULL CHECK(request_hash ~ '^[0-9a-f]{64}$'),
 input_refs jsonb NOT NULL,
 profile_id uuid NOT NULL,
 profile_version integer NOT NULL,
 profile_hash varchar(64) NOT NULL CHECK(profile_hash ~ '^[0-9a-f]{64}$'),
 provider_mode varchar(16) NOT NULL CHECK(provider_mode IN ('live','fake','disabled')),
 dbos_workflow_id varchar(200) NOT NULL UNIQUE,
 application_version varchar(100) NOT NULL,
 status varchar(24) NOT NULL CHECK(status IN ('QUEUED','RUNNING','SUCCEEDED','BLOCKED','FAILED','CANCELLED','OUTCOME_UNKNOWN')),
 outcome varchar(40), blocked_reason varchar(100), events jsonb NOT NULL,
 cancel_key uuid, cancel_requested_at timestamptz, cancel_confirmed boolean NOT NULL,
 review_key uuid, review_status varchar(16) NOT NULL CHECK(review_status IN ('PENDING','ACCEPTED','REJECTED')),
 review_reason varchar(4000),
 created_at timestamptz NOT NULL, started_at timestamptz, finished_at timestamptz,
 FOREIGN KEY(profile_id,profile_version) REFERENCES record_operator_profiles(id,version)
);
CREATE INDEX ix_record_agent_runs_pending ON record_agent_runs(status,created_at);
CREATE INDEX ix_record_agent_runs_experiment ON record_agent_runs(experiment_id,created_at DESC);
CREATE FUNCTION record_agent_run_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_OP='DELETE' OR (TG_OP='UPDATE' AND
   (to_jsonb(OLD)-ARRAY['status','outcome','blocked_reason','events','cancel_key','cancel_requested_at','cancel_confirmed','review_key','review_status','review_reason','started_at','finished_at'])
   IS DISTINCT FROM
   (to_jsonb(NEW)-ARRAY['status','outcome','blocked_reason','events','cancel_key','cancel_requested_at','cancel_confirmed','review_key','review_status','review_reason','started_at','finished_at']))
 THEN RAISE EXCEPTION 'agent run identity is immutable'; END IF;
 RETURN NEW; END $$;
CREATE TRIGGER record_agent_run_guard BEFORE UPDATE OR DELETE ON record_agent_runs
 FOR EACH ROW EXECUTE FUNCTION record_agent_run_guard();
""")


def downgrade() -> None:
    op.execute("""
DO $$ BEGIN IF EXISTS(SELECT 1 FROM record_agent_runs) THEN
 RAISE EXCEPTION 'cannot discard retained agent runs'; END IF; END $$;
DROP TABLE record_agent_runs;
DROP FUNCTION record_agent_run_guard();
""")
