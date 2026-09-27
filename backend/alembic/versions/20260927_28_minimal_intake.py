"""Optional idea intake with durable command identity and revision provenance."""

from alembic import op

revision = "20260927_28"
down_revision = "20260926_27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
ALTER FUNCTION record_payload_valid(text,jsonb) RENAME TO record_payload_valid_before_intake;
CREATE FUNCTION record_payload_valid(kind text,value jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE WHEN kind='EXPERIMENT_BRIEF' AND value ? 'intake_policy' THEN
   record_json_exact(value,ARRAY['intake_policy','budget_usd','launch_stage','guidance'])
   AND value->>'intake_policy'='R01A_UX_V1' AND value->>'launch_stage'='SHADOW'
   AND jsonb_typeof(value->'guidance')='string' AND length(value->>'guidance')<=4000
   AND value->>'budget_usd' ~ '^[0-9]+(\.[0-9]{1,2})?$' AND (value->>'budget_usd')::numeric>0
 ELSE record_payload_valid_before_intake(kind,value) END $$;
CREATE TABLE record_intakes (
 experiment_id uuid PRIMARY KEY, command_key uuid NOT NULL,
 operator_id uuid NOT NULL REFERENCES record_operators(id), idea_seed varchar(4000),
 profile_id uuid NOT NULL, profile_version integer NOT NULL, budget_usd varchar(64) NOT NULL,
 created_at timestamptz NOT NULL, draft boolean NOT NULL, blocked_reason varchar(100),
 FOREIGN KEY(profile_id,profile_version) REFERENCES record_operator_profiles(id,version)
);
CREATE FUNCTION record_intake_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_OP='DELETE' OR (TG_OP='UPDATE' AND ((to_jsonb(OLD)-ARRAY['draft','blocked_reason']) IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['draft','blocked_reason']) OR (NOT OLD.draft AND NEW.draft)))
 THEN RAISE EXCEPTION 'intake context is immutable'; END IF; RETURN NEW; END $$;
CREATE TRIGGER record_intake_guard BEFORE UPDATE OR DELETE ON record_intakes FOR EACH ROW EXECUTE FUNCTION record_intake_guard();
CREATE TABLE record_intake_commands (
 command_key uuid PRIMARY KEY, experiment_id uuid NOT NULL REFERENCES record_experiments(id),
 request_hash varchar(64) NOT NULL, action varchar(16) NOT NULL, state varchar(16) NOT NULL,
 payload jsonb NOT NULL, result jsonb, created_at timestamptz NOT NULL,
 CHECK(state IN ('RUNNING','COMPLETE','BLOCKED'))
);
CREATE FUNCTION record_intake_command_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_OP='DELETE' OR (TG_OP='UPDATE' AND (
   (to_jsonb(OLD)-ARRAY['state','result']) IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['state','result'])
   OR (OLD.state='RUNNING' AND NEW.state='RUNNING')
   OR (OLD.state<>'RUNNING' AND (NEW.state<>OLD.state OR OLD.result IS NOT NULL OR NEW.result IS NULL))))
 THEN RAISE EXCEPTION 'intake command identity and terminal outcome are immutable'; END IF;
 RETURN NEW; END $$;
CREATE TRIGGER record_intake_command_guard BEFORE UPDATE OR DELETE ON record_intake_commands
 FOR EACH ROW EXECUTE FUNCTION record_intake_command_guard();
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN IF EXISTS(SELECT 1 FROM record_intakes) OR EXISTS(SELECT 1 FROM record_intake_commands)
 OR EXISTS(SELECT 1 FROM record_artifacts WHERE payload ? 'intake_policy')
 THEN RAISE EXCEPTION 'cannot discard intake evidence'; END IF; END $$;
DROP TABLE record_intake_commands;
DROP FUNCTION record_intake_command_guard();
DROP TABLE record_intakes;
DROP FUNCTION record_intake_guard();
DROP FUNCTION record_payload_valid(text,jsonb);
ALTER FUNCTION record_payload_valid_before_intake(text,jsonb) RENAME TO record_payload_valid;
""")
