"""Durable, scoped child checkpoints for R01A Idea runs."""

from alembic import op

revision = "20260928_30"
down_revision = "20260928_29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
ALTER FUNCTION record_payload_valid(text,jsonb) RENAME TO record_payload_valid_before_r01a_steps;
CREATE FUNCTION record_research_text_array(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE WHEN jsonb_typeof(value)='array' THEN
   jsonb_array_length(value)<=30
   AND NOT EXISTS(
     SELECT 1 FROM jsonb_array_elements(value) item
     WHERE NOT record_nonempty_text(item)
   )
 ELSE false END
$$;
CREATE FUNCTION record_payload_valid(kind text,value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE
 WHEN kind='RESEARCH_EVIDENCE' AND value ? 'research_schema' THEN
   record_json_exact(value,ARRAY['research_schema','run_id','step_key','dimension','claim','finding','evidence_status','limitations'])
   AND value->>'research_schema'='SOURCE_FINDING_V1'
   AND jsonb_typeof(value->'run_id')='string'
   AND value->>'run_id' ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   AND jsonb_typeof(value->'step_key')='string'
   AND value->>'step_key' ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   AND value->>'dimension' IN ('CUSTOMER_PAIN','BUYER','DEMAND','ALTERNATIVES','COMPETITION','PRICING','REACHABILITY','DELIVERY')
   AND record_nonempty_text(value->'claim') AND record_nonempty_text(value->'finding')
   AND value->>'evidence_status' IN ('SUPPORTED','CONTRADICTED','INCONCLUSIVE','UNAVAILABLE')
   AND record_research_text_array(value->'limitations')
 WHEN kind='MARKET_RESEARCH_REPORT' AND value ? 'research_schema' THEN
   record_json_exact(value,ARRAY['research_schema','finding','limitations','unresolved_questions'])
   AND value->>'research_schema'='MARKET_RESEARCH_CASE_V1'
   AND record_nonempty_text(value->'finding')
   AND record_research_text_array(value->'limitations')
   AND record_research_text_array(value->'unresolved_questions')
 ELSE record_payload_valid_before_r01a_steps(kind,value) END
$$;
ALTER TABLE record_agent_runs
 ADD CONSTRAINT uq_record_agent_runs_run_experiment UNIQUE(run_id,experiment_id);
CREATE TABLE record_agent_run_steps (
 run_id uuid NOT NULL,
 experiment_id uuid NOT NULL,
 step_key uuid NOT NULL,
 ordinal integer NOT NULL,
 kind varchar(40) NOT NULL,
 candidate_artifact_id uuid,
 candidate_kind varchar(64),
 candidate_version integer,
 candidate_hash varchar(64),
 request_ref uuid NOT NULL,
 request_version integer NOT NULL,
 request_hash varchar(64) NOT NULL,
 config_ref uuid NOT NULL,
 config_version integer NOT NULL,
 config_hash varchar(64) NOT NULL,
 operation_id uuid,
 operation_workflow_id uuid,
 provider_call_id uuid,
 status varchar(24) NOT NULL,
 reason_code varchar(100),
 result_artifact_id uuid,
 result_kind varchar(64),
 result_version integer,
 result_hash varchar(64),
 output_hash varchar(64),
 created_at timestamptz NOT NULL,
 finished_at timestamptz,
 PRIMARY KEY(run_id,step_key),
 FOREIGN KEY(run_id,experiment_id) REFERENCES record_agent_runs(run_id,experiment_id),
 FOREIGN KEY(candidate_artifact_id,experiment_id,candidate_kind,candidate_version,candidate_hash)
  REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(operation_id,operation_workflow_id,experiment_id)
  REFERENCES gov_operations(id,workflow_id,experiment_id),
 FOREIGN KEY(provider_call_id) REFERENCES gov_calls(id),
 FOREIGN KEY(result_artifact_id,experiment_id,result_kind,result_version,result_hash)
  REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 UNIQUE(provider_call_id),
 CHECK(ordinal > 0),
 CHECK(kind IN ('MODEL_REQUEST','BRAVE_SEARCH','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL','ARTIFACT_SAVE')),
 CHECK((candidate_artifact_id IS NULL AND candidate_kind IS NULL AND candidate_version IS NULL AND candidate_hash IS NULL)
   OR (candidate_artifact_id IS NOT NULL AND candidate_kind='IDEA_CANDIDATE' AND candidate_version > 0 AND candidate_hash ~ '^[0-9a-f]{64}$')),
 CHECK(request_version > 0 AND config_version > 0 AND request_hash ~ '^[0-9a-f]{64}$' AND config_hash ~ '^[0-9a-f]{64}$'),
 CHECK((operation_id IS NULL) = (operation_workflow_id IS NULL)),
 CHECK(status IN ('CLAIMED','SUCCEEDED','BLOCKED','FAILED','OUTCOME_UNKNOWN')),
 CHECK(reason_code IS NULL OR reason_code ~ '^[A-Z][A-Z0-9_]{0,99}$'),
 CHECK((result_artifact_id IS NULL AND result_kind IS NULL AND result_version IS NULL AND result_hash IS NULL)
   OR (result_artifact_id IS NOT NULL AND result_kind IS NOT NULL AND result_version > 0 AND result_hash ~ '^[0-9a-f]{64}$')),
 CHECK(output_hash IS NULL OR (kind='ARTIFACT_SAVE' AND status='SUCCEEDED' AND output_hash ~ '^[0-9a-f]{64}$')),
 CHECK((status='CLAIMED' AND reason_code IS NULL AND result_artifact_id IS NULL AND finished_at IS NULL)
   OR (status='SUCCEEDED' AND reason_code IS NULL AND finished_at IS NOT NULL)
   OR (status IN ('BLOCKED','FAILED','OUTCOME_UNKNOWN') AND reason_code IS NOT NULL AND result_artifact_id IS NULL AND finished_at IS NOT NULL))
);
CREATE INDEX ix_record_agent_run_steps_order ON record_agent_run_steps(run_id,ordinal,step_key);
CREATE FUNCTION record_agent_run_step_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE bound_call gov_calls;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'agent run step is immutable';
 END IF;
 IF TG_OP='UPDATE' THEN
  IF OLD.status<>'CLAIMED'
   OR (OLD.operation_id IS NOT NULL AND NEW.operation_id IS DISTINCT FROM OLD.operation_id)
   OR (OLD.operation_workflow_id IS NOT NULL AND NEW.operation_workflow_id IS DISTINCT FROM OLD.operation_workflow_id)
   OR (OLD.provider_call_id IS NOT NULL AND NEW.provider_call_id IS DISTINCT FROM OLD.provider_call_id)
   OR (to_jsonb(OLD)-ARRAY['operation_id','operation_workflow_id','provider_call_id','status','reason_code','result_artifact_id','result_kind','result_version','result_hash','output_hash','finished_at'])
      IS DISTINCT FROM
      (to_jsonb(NEW)-ARRAY['operation_id','operation_workflow_id','provider_call_id','status','reason_code','result_artifact_id','result_kind','result_version','result_hash','output_hash','finished_at'])
  THEN RAISE EXCEPTION 'agent run step identity or terminal result is immutable'; END IF;
 END IF;
 IF NEW.provider_call_id IS NOT NULL THEN
  SELECT * INTO bound_call FROM gov_calls WHERE id=NEW.provider_call_id;
  IF bound_call.id IS NULL OR bound_call.experiment_id<>NEW.experiment_id
   OR (NEW.operation_id IS NOT NULL AND bound_call.operation_id<>NEW.operation_id)
  THEN RAISE EXCEPTION 'agent run step provider call scope mismatch'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_agent_run_step_guard BEFORE INSERT OR UPDATE OR DELETE
 ON record_agent_run_steps FOR EACH ROW EXECUTE FUNCTION record_agent_run_step_guard();
CREATE FUNCTION record_combined_idea_proof(
 p_run_id uuid,p_experiment_id uuid,p_operation_id uuid,p_task_kind text,p_output_hash text
) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(
   SELECT 1 FROM record_agent_runs parent
   JOIN record_agent_run_steps saved ON saved.run_id=parent.run_id
     AND saved.experiment_id=parent.experiment_id
   WHERE parent.run_id=p_run_id AND parent.experiment_id=p_experiment_id
     AND parent.task_kind=p_task_kind AND parent.provider_mode='live'
     AND parent.status='RUNNING'
     AND saved.kind='ARTIFACT_SAVE' AND saved.status='SUCCEEDED'
     AND saved.operation_id=p_operation_id AND saved.output_hash=p_output_hash
 ) AND EXISTS(
   SELECT 1 FROM record_agent_run_steps model
   JOIN record_agent_runs parent ON parent.run_id=model.run_id
     AND parent.experiment_id=model.experiment_id
   JOIN gov_calls call ON call.id=model.provider_call_id
     AND call.idempotency_key=model.step_key
     AND call.experiment_id=model.experiment_id
     AND call.operation_id=model.operation_id
     AND call.created_at>=parent.started_at
     AND call.state='FINAL'
   WHERE model.run_id=p_run_id AND model.experiment_id=p_experiment_id
     AND model.kind='MODEL_REQUEST' AND model.status='SUCCEEDED'
     AND model.operation_id=p_operation_id
 ) AND NOT EXISTS(
   SELECT 1 FROM record_agent_run_steps child
   JOIN record_agent_runs parent ON parent.run_id=child.run_id
     AND parent.experiment_id=child.experiment_id
   LEFT JOIN gov_calls call ON call.id=child.provider_call_id
     AND call.idempotency_key=child.step_key
     AND call.experiment_id=child.experiment_id
     AND call.operation_id=child.operation_id
     AND call.created_at>=parent.started_at
     AND call.state='FINAL'
   WHERE child.run_id=p_run_id AND child.experiment_id=p_experiment_id
     AND child.kind<>'ARTIFACT_SAVE'
     AND (child.status<>'SUCCEEDED' OR child.operation_id IS DISTINCT FROM p_operation_id
       OR call.id IS NULL)
 )
$$;
CREATE OR REPLACE FUNCTION record_idea_discovery_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
  IF intent.idempotency_key IS NULL AND NOT record_combined_idea_proof(
    NEW.run_id,NEW.experiment_id,NEW.operation_id,'IDEA_DISCOVERY',NEW.output_hash)
  THEN RAISE EXCEPTION 'discovery output is not a governed run'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_idea_refinement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE intent openai_run_intents; cycle record_cycles; operation gov_operations;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'refinement history is immutable'; END IF;
 IF TG_OP='UPDATE' AND (OLD.state<>'RUNNING' OR NEW.state='RUNNING'
   OR (to_jsonb(OLD)-ARRAY['state','advice','output_hash','finished_at'])
      IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['state','advice','output_hash','finished_at']))
 THEN RAISE EXCEPTION 'refinement identity or terminal result is immutable'; END IF;
 SELECT * INTO cycle FROM record_cycles c WHERE c.id=NEW.cycle_id AND c.experiment_id=NEW.experiment_id
   AND ((c.purpose='INITIAL' AND c.seed_artifact_id=NEW.seed_artifact_id)
     OR (c.purpose='SAME_INTENT_RETURN' AND EXISTS(SELECT 1 FROM record_returns r WHERE r.to_cycle_id=c.id AND r.idea_artifact_id=NEW.seed_artifact_id)))
   AND c.idea_mode IN ('USER_SEEDED_REFINEMENT','SYSTEM_DISCOVERY');
 SELECT * INTO operation FROM gov_operations WHERE id=NEW.operation_id AND experiment_id=NEW.experiment_id;
 IF cycle.id IS NULL OR operation.id IS NULL THEN RAISE EXCEPTION 'refinement scope mismatch'; END IF;
 IF NEW.state='SUCCEEDED' THEN
  SELECT * INTO intent FROM openai_run_intents WHERE idempotency_key=NEW.run_id
    AND experiment_id=NEW.experiment_id AND operation_id=NEW.operation_id
    AND outcome='SUCCEEDED' AND output_hash=NEW.output_hash;
  IF intent.idempotency_key IS NULL AND NOT record_combined_idea_proof(
    NEW.run_id,NEW.experiment_id,NEW.operation_id,'IDEA_REFINEMENT',NEW.output_hash)
  THEN RAISE EXCEPTION 'refinement output is not a successful governed run'; END IF;
 END IF;
 RETURN NEW;
END $$;
""")


def downgrade() -> None:
    op.execute("""
DO $$ BEGIN IF EXISTS(SELECT 1 FROM record_agent_run_steps) THEN
 RAISE EXCEPTION 'cannot discard retained agent run steps'; END IF; END $$;
CREATE OR REPLACE FUNCTION record_idea_discovery_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE OR REPLACE FUNCTION record_idea_refinement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE intent openai_run_intents; cycle record_cycles; operation gov_operations;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'refinement history is immutable'; END IF;
 IF TG_OP='UPDATE' AND (OLD.state<>'RUNNING' OR NEW.state='RUNNING'
   OR (to_jsonb(OLD)-ARRAY['state','advice','output_hash','finished_at'])
      IS DISTINCT FROM (to_jsonb(NEW)-ARRAY['state','advice','output_hash','finished_at']))
 THEN RAISE EXCEPTION 'refinement identity or terminal result is immutable'; END IF;
 SELECT * INTO cycle FROM record_cycles c WHERE c.id=NEW.cycle_id AND c.experiment_id=NEW.experiment_id
   AND ((c.purpose='INITIAL' AND c.seed_artifact_id=NEW.seed_artifact_id)
     OR (c.purpose='SAME_INTENT_RETURN' AND EXISTS(SELECT 1 FROM record_returns r WHERE r.to_cycle_id=c.id AND r.idea_artifact_id=NEW.seed_artifact_id)))
   AND c.idea_mode IN ('USER_SEEDED_REFINEMENT','SYSTEM_DISCOVERY');
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
DROP FUNCTION IF EXISTS record_combined_idea_proof(uuid,uuid,uuid,text,text);
DROP TABLE record_agent_run_steps;
DROP FUNCTION record_agent_run_step_guard();
ALTER TABLE record_agent_runs DROP CONSTRAINT uq_record_agent_runs_run_experiment;
DROP FUNCTION record_payload_valid(text,jsonb);
DROP FUNCTION record_research_text_array(jsonb);
ALTER FUNCTION record_payload_valid_before_r01a_steps(text,jsonb) RENAME TO record_payload_valid;
""")
