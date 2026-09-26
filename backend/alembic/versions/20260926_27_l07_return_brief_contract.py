"""Allow the versioned L07 return brief and structured research feedback."""

from alembic import op

revision = "20260926_27"
down_revision = "20260926_26"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE OR REPLACE FUNCTION record_payload_valid(kind text, value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE kind
  WHEN 'IDEA_BRIEF' THEN
   (record_json_exact(value,ARRAY['title','customer','problem','core_intent','material_pivot'])
    AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'customer')
    AND record_nonempty_text(value->'problem') AND record_nonempty_text(value->'core_intent')
    AND jsonb_typeof(value->'material_pivot')='boolean')
   OR
   (record_json_exact(value,ARRAY['title','customer','problem','core_intent','material_pivot','buyer','service_hypothesis','value_hypothesis','assumptions','exclusions','research_questions'])
    AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'customer')
    AND record_nonempty_text(value->'problem') AND record_nonempty_text(value->'core_intent')
    AND jsonb_typeof(value->'material_pivot')='boolean'
    AND jsonb_typeof(value->'buyer')='object'
    AND record_json_exact(value->'buyer',ARRAY['segment','role'])
    AND record_nonempty_text(value->'buyer'->'segment') AND record_nonempty_text(value->'buyer'->'role')
    AND record_nonempty_text(value->'service_hypothesis') AND record_nonempty_text(value->'value_hypothesis')
    AND record_nonempty_text_array(value->'assumptions') AND record_nonempty_text_array(value->'exclusions')
    AND record_nonempty_text_array(value->'research_questions'))
  WHEN 'RESEARCH_FEEDBACK_BRIEF' THEN
   (record_json_exact(value,ARRAY['preserve','change']) AND record_nonempty_text_array(value->'preserve') AND record_nonempty_text_array(value->'change'))
   OR
   (record_json_exact(value,ARRAY['preserve','change','failed_dimensions','research_questions'])
    AND record_nonempty_text_array(value->'preserve') AND record_nonempty_text_array(value->'change')
    AND record_nonempty_text_array(value->'failed_dimensions') AND record_nonempty_text_array(value->'research_questions')
    AND jsonb_array_length(value->'failed_dimensions')=(SELECT count(DISTINCT x) FROM jsonb_array_elements_text(value->'failed_dimensions') x))
  WHEN 'EXPERIMENT_BRIEF' THEN
   (record_json_exact(value,ARRAY['objective']) AND record_nonempty_text(value->'objective'))
   OR (record_json_exact(value,ARRAY['objective','target_customer','problem','geographies','commercial_boundaries','budget_usd','evidence_definitions','launch_stage'])
       AND record_nonempty_text(value->'objective') AND record_nonempty_text(value->'target_customer') AND record_nonempty_text(value->'problem')
       AND record_nonempty_text_array(value->'geographies') AND record_nonempty_text(value->'commercial_boundaries')
       AND value->>'budget_usd' ~ '^[0-9]+(\.[0-9]{1,2})?$' AND (value->>'budget_usd')::numeric>0
       AND record_nonempty_text_array(value->'evidence_definitions') AND value->>'launch_stage'='SHADOW')
  WHEN 'IDEA_SEED' THEN record_json_exact(value,ARRAY['origin','statement']) AND value->>'origin'='USER_SUPPLIED' AND record_nonempty_text(value->'statement')
  WHEN 'IDEA_CANDIDATE' THEN record_json_exact(value,ARRAY['title','hypothesis']) AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'hypothesis')
  WHEN 'RESEARCH_PLAN' THEN record_json_exact(value,ARRAY['questions','method']) AND record_nonempty_text_array(value->'questions') AND record_nonempty_text(value->'method')
  WHEN 'RESEARCH_EVIDENCE' THEN record_json_exact(value,ARRAY['claim','finding']) AND record_nonempty_text(value->'claim') AND record_nonempty_text(value->'finding')
  WHEN 'COMPETITOR_PROFILE' THEN record_json_exact(value,ARRAY['name','positioning']) AND record_nonempty_text(value->'name') AND record_nonempty_text(value->'positioning')
  WHEN 'SERVICE_PROFILE' THEN record_json_exact(value,ARRAY['name','scope']) AND record_nonempty_text(value->'name') AND record_nonempty_text(value->'scope')
  WHEN 'PRICE_OBSERVATION' THEN record_json_exact(value,ARRAY['status','currency','amount','unit','source_note']) AND record_nonempty_text(value->'unit') AND record_nonempty_text(value->'source_note')
  WHEN 'MARKET_RESEARCH_REPORT' THEN record_json_exact(value,ARRAY['finding','limitations']) AND record_nonempty_text(value->'finding') AND record_nonempty_text_array(value->'limitations')
  WHEN 'MARKET_RESEARCH_RECOMMENDATION' THEN record_json_exact(value,ARRAY['recommendation','rationale']) AND value->>'recommendation' IN ('PROCEED_TO_OFFER','REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED','KILL_IDEA','INCONCLUSIVE') AND record_nonempty_text(value->'rationale')
  WHEN 'OFFER_RESEARCH_GAP_BRIEF' THEN record_json_exact(value,ARRAY['required_evidence','justification']) AND record_nonempty_text_array(value->'required_evidence') AND record_nonempty_text(value->'justification')
  WHEN 'VALIDATION_RESULT' THEN record_json_exact(value,ARRAY['validator','disposition','reason']) AND record_nonempty_text(value->'validator') AND value->>'disposition' IN ('PASS','FAIL') AND record_nonempty_text(value->'reason')
  WHEN 'ACCEPTANCE_RECEIPT' THEN record_json_exact(value,ARRAY['disposition','reason']) AND value->>'disposition' IN ('ACCEPTED','REJECTED','SUPERSEDED') AND record_nonempty_text(value->'reason')
  ELSE record_payload_valid_before_l07(kind,value)
 END
$$;
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
CREATE OR REPLACE FUNCTION record_idea_intent_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE refinement record_idea_refinements; source record_artifacts;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'intent review is immutable'; END IF;
 SELECT * INTO refinement FROM record_idea_refinements WHERE run_id=NEW.run_id
   AND experiment_id=NEW.experiment_id AND cycle_id=NEW.cycle_id
   AND seed_artifact_id=NEW.source_artifact_id AND output_hash=NEW.output_hash
   AND state='SUCCEEDED';
 SELECT * INTO source FROM record_artifacts WHERE id=NEW.source_artifact_id
   AND experiment_id=NEW.experiment_id AND kind IN ('IDEA_SEED','IDEA_CANDIDATE','IDEA_BRIEF');
 IF refinement.run_id IS NULL OR source.id IS NULL THEN RAISE EXCEPTION 'intent review must bind exact successful output and source'; END IF;
 RETURN NEW;
END $$;
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(
   SELECT 1 FROM record_artifacts
   WHERE (kind='IDEA_BRIEF' AND payload ? 'buyer')
      OR (kind='RESEARCH_FEEDBACK_BRIEF' AND payload ? 'failed_dimensions')
 ) OR EXISTS(
   SELECT 1 FROM record_idea_refinements
   WHERE advice ? 'buyer'
 ) OR EXISTS(
   SELECT 1 FROM record_idea_refinements refinement
   JOIN record_cycles cycle ON cycle.id=refinement.cycle_id
   WHERE cycle.purpose='SAME_INTENT_RETURN'
 ) OR EXISTS(
   SELECT 1 FROM record_idea_intent_reviews review
   JOIN record_artifacts source ON source.id=review.source_artifact_id
   WHERE source.kind='IDEA_BRIEF'
 )
 THEN RAISE EXCEPTION 'cannot discard L07 rich return evidence'; END IF;
END $$;
CREATE OR REPLACE FUNCTION record_payload_valid(kind text, value jsonb) RETURNS boolean
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
CREATE OR REPLACE FUNCTION record_idea_intent_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
""")
