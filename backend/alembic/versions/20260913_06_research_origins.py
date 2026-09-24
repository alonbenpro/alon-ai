"""Explicit selected origins and scoped immutable research returns.

Revision ID: 20260913_06
Revises: 20260913_05
"""

from alembic import op

revision = "20260913_06"
down_revision = "20260913_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE TABLE record_candidate_selections (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, artifact_id uuid NOT NULL,
 artifact_kind varchar(64) NOT NULL, artifact_version integer NOT NULL, artifact_hash varchar(64) NOT NULL,
 workflow_id uuid NOT NULL, agent_id uuid NOT NULL, profile_id uuid NOT NULL, profile_version integer NOT NULL,
 selected_by uuid NOT NULL, reason varchar(4000) NOT NULL, created_at timestamptz NOT NULL,
 FOREIGN KEY (artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY (workflow_id,experiment_id) REFERENCES record_workflows(id,experiment_id),
 FOREIGN KEY (agent_id,workflow_id) REFERENCES record_agents(id,workflow_id),
 FOREIGN KEY (profile_id,profile_version) REFERENCES record_operator_profiles(id,version),
 UNIQUE(experiment_id), UNIQUE(id,experiment_id),
 CHECK(artifact_kind='IDEA_CANDIDATE' AND length(btrim(reason)) BETWEEN 1 AND 4000)
);
CREATE INDEX ix_record_candidate_selections_fk_0 ON record_candidate_selections(agent_id,workflow_id);
CREATE INDEX ix_record_candidate_selections_fk_1 ON record_candidate_selections(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash);
CREATE INDEX ix_record_candidate_selections_fk_2 ON record_candidate_selections(profile_id,profile_version);
CREATE INDEX ix_record_candidate_selections_fk_3 ON record_candidate_selections(workflow_id,experiment_id);
ALTER TABLE record_cycles ADD COLUMN idea_mode varchar(32), ADD COLUMN selection_id uuid,
 ADD COLUMN purpose varchar(32), ADD COLUMN episode_id uuid;
ALTER TABLE record_returns ADD COLUMN kind varchar(32), ADD COLUMN applicable_scope_id uuid,
 ADD COLUMN idea_artifact_id uuid, ADD COLUMN offer_input_bundle_id uuid;
ALTER TABLE record_cycles DISABLE TRIGGER record_cycles_guard;
UPDATE record_cycles c SET idea_mode='USER_SEEDED_REFINEMENT',
 purpose=CASE WHEN ordinal=1 THEN 'INITIAL' WHEN EXISTS(SELECT 1 FROM record_returns r JOIN record_verdicts v ON v.id=r.verdict_id WHERE r.to_cycle_id=c.id AND v.verdict='MATERIAL_PIVOT_RECOMMENDED') THEN 'MATERIAL_PIVOT_RETURN' ELSE 'SAME_INTENT_RETURN' END,
 episode_id=(SELECT id FROM record_cycles root WHERE root.experiment_id=c.experiment_id AND root.ordinal=1);
ALTER TABLE record_cycles ENABLE TRIGGER record_cycles_guard;
ALTER TABLE record_returns DISABLE TRIGGER record_returns_guard;
UPDATE record_returns r SET kind=CASE WHEN (SELECT verdict FROM record_verdicts WHERE id=r.verdict_id)='MATERIAL_PIVOT_RECOMMENDED' THEN 'MATERIAL_PIVOT' ELSE 'SAME_INTENT' END,
 applicable_scope_id=(SELECT CASE WHEN (SELECT verdict FROM record_verdicts WHERE id=r.verdict_id)='MATERIAL_PIVOT_RECOMMENDED' THEN c.episode_id ELSE c.seed_artifact_id END FROM record_cycles c WHERE c.id=r.from_cycle_id),
 idea_artifact_id=(SELECT artifact_id FROM record_idea_acceptances a WHERE a.cycle_id=r.from_cycle_id);
ALTER TABLE record_returns DROP CONSTRAINT record_returns_experiment_id_ordinal_key;
WITH numbered AS (SELECT id,row_number() OVER(PARTITION BY experiment_id,kind,applicable_scope_id ORDER BY ordinal) AS n FROM record_returns)
 UPDATE record_returns r SET ordinal=numbered.n FROM numbered WHERE r.id=numbered.id;
ALTER TABLE record_returns ENABLE TRIGGER record_returns_guard;
ALTER TABLE record_cycles ALTER COLUMN idea_mode SET NOT NULL, ALTER COLUMN purpose SET NOT NULL, ALTER COLUMN episode_id SET NOT NULL;
ALTER TABLE record_returns ALTER COLUMN kind SET NOT NULL, ALTER COLUMN applicable_scope_id SET NOT NULL, ALTER COLUMN idea_artifact_id SET NOT NULL;
ALTER TABLE record_cycles DROP CONSTRAINT record_cycles_check;
ALTER TABLE record_cycles ADD CONSTRAINT ck_record_cycle_ordinal CHECK(ordinal>0),
 ADD CONSTRAINT ck_record_cycle_origin CHECK((idea_mode='USER_SEEDED_REFINEMENT' AND seed_kind='IDEA_SEED' AND selection_id IS NULL) OR (idea_mode='SYSTEM_DISCOVERY' AND seed_kind='IDEA_CANDIDATE' AND selection_id IS NOT NULL)),
 ADD CONSTRAINT ck_record_cycle_purpose CHECK(purpose IN ('INITIAL','SAME_INTENT_RETURN','MATERIAL_PIVOT_RETURN','INCONCLUSIVE_SUPPLEMENT','OFFER_GAP_RETURN')),
 ADD FOREIGN KEY(selection_id,experiment_id) REFERENCES record_candidate_selections(id,experiment_id),
 ADD FOREIGN KEY(episode_id,experiment_id) REFERENCES record_cycles(id,experiment_id);
ALTER TABLE record_idea_acceptances DROP CONSTRAINT record_idea_acceptances_artifact_id_key;
ALTER TABLE record_returns DROP CONSTRAINT record_returns_check;
ALTER TABLE record_returns ADD CHECK((kind='SAME_INTENT' AND ordinal BETWEEN 1 AND 2) OR (kind IN ('INCONCLUSIVE_SUPPLEMENT','OFFER_GAP') AND ordinal=1) OR (kind='MATERIAL_PIVOT' AND ordinal>0)),
 ADD CHECK((kind='OFFER_GAP' AND feedback_kind='OFFER_RESEARCH_GAP_BRIEF') OR (kind<>'OFFER_GAP' AND feedback_kind='RESEARCH_FEEDBACK_BRIEF')),
 ADD CHECK((kind='OFFER_GAP')=(offer_input_bundle_id IS NOT NULL)),
 ADD UNIQUE(experiment_id,kind,applicable_scope_id,ordinal),
 ADD FOREIGN KEY(idea_artifact_id,experiment_id) REFERENCES record_artifacts(id,experiment_id),
 ADD FOREIGN KEY(offer_input_bundle_id,experiment_id) REFERENCES record_artifacts(id,experiment_id);
CREATE INDEX ix_record_cycles_episode ON record_cycles(episode_id,experiment_id);
CREATE INDEX ix_record_cycles_selection ON record_cycles(selection_id,experiment_id);
CREATE INDEX ix_record_returns_idea ON record_returns(idea_artifact_id,experiment_id);
CREATE INDEX ix_record_returns_offer_bundle ON record_returns(offer_input_bundle_id,experiment_id);
ALTER TABLE record_artifacts DROP CONSTRAINT record_artifacts_kind_check;
ALTER TABLE record_artifacts ADD CHECK(kind IN ('EXPERIMENT_BRIEF','IDEA_SEED','IDEA_CANDIDATE','IDEA_BRIEF','RESEARCH_PLAN','RESEARCH_EVIDENCE','COMPETITOR_PROFILE','SERVICE_PROFILE','PRICE_OBSERVATION','MARKET_RESEARCH_REPORT','MARKET_RESEARCH_RECOMMENDATION','RESEARCH_FEEDBACK_BRIEF','OFFER_RESEARCH_GAP_BRIEF','VALIDATION_RESULT','ACCEPTANCE_RECEIPT'));

CREATE OR REPLACE FUNCTION record_payload_valid(kind text, value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE kind
  WHEN 'EXPERIMENT_BRIEF' THEN record_json_exact(value,ARRAY['objective']) AND record_nonempty_text(value->'objective')
  WHEN 'IDEA_SEED' THEN record_json_exact(value,ARRAY['origin','statement']) AND value->>'origin' ='USER_SUPPLIED' AND record_nonempty_text(value->'statement')
  WHEN 'IDEA_CANDIDATE' THEN record_json_exact(value,ARRAY['title','hypothesis']) AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'hypothesis')
  WHEN 'IDEA_BRIEF' THEN record_json_exact(value,ARRAY['title','customer','problem','core_intent','material_pivot']) AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'customer') AND record_nonempty_text(value->'problem') AND record_nonempty_text(value->'core_intent') AND jsonb_typeof(value->'material_pivot')='boolean'
  WHEN 'RESEARCH_PLAN' THEN record_json_exact(value,ARRAY['questions','method']) AND record_nonempty_text_array(value->'questions') AND record_nonempty_text(value->'method')
  WHEN 'RESEARCH_EVIDENCE' THEN record_json_exact(value,ARRAY['claim','finding']) AND record_nonempty_text(value->'claim') AND record_nonempty_text(value->'finding')
  WHEN 'COMPETITOR_PROFILE' THEN record_json_exact(value,ARRAY['name','positioning']) AND record_nonempty_text(value->'name') AND record_nonempty_text(value->'positioning')
  WHEN 'SERVICE_PROFILE' THEN record_json_exact(value,ARRAY['name','scope']) AND record_nonempty_text(value->'name') AND record_nonempty_text(value->'scope')
  WHEN 'PRICE_OBSERVATION' THEN record_json_exact(value,ARRAY['status','currency','amount','unit','source_note']) AND record_nonempty_text(value->'unit') AND record_nonempty_text(value->'source_note') AND ((value->>'status'='QUOTED' AND value->>'currency' ~ '^[A-Z]{3}$' AND value->>'amount' ~ '^[0-9]+(\.[0-9]{1,6})?$' AND (value->>'amount')::numeric>0 AND (value->>'amount')::numeric<1000000000000) OR (value->>'status'='REQUIRED_UNAVAILABLE' AND value->'currency'='null'::jsonb AND value->'amount'='null'::jsonb))
  WHEN 'MARKET_RESEARCH_REPORT' THEN record_json_exact(value,ARRAY['finding','limitations']) AND record_nonempty_text(value->'finding') AND record_nonempty_text_array(value->'limitations')
  WHEN 'MARKET_RESEARCH_RECOMMENDATION' THEN record_json_exact(value,ARRAY['recommendation','rationale']) AND value->>'recommendation' IN ('PROCEED_TO_OFFER','REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED','KILL_IDEA','INCONCLUSIVE') AND record_nonempty_text(value->'rationale')
  WHEN 'RESEARCH_FEEDBACK_BRIEF' THEN record_json_exact(value,ARRAY['preserve','change']) AND record_nonempty_text_array(value->'preserve') AND record_nonempty_text_array(value->'change')
  WHEN 'OFFER_RESEARCH_GAP_BRIEF' THEN record_json_exact(value,ARRAY['required_evidence','justification']) AND record_nonempty_text_array(value->'required_evidence') AND record_nonempty_text(value->'justification')
  WHEN 'VALIDATION_RESULT' THEN record_json_exact(value,ARRAY['validator','disposition','reason']) AND record_nonempty_text(value->'validator') AND value->>'disposition' IN ('PASS','FAIL') AND record_nonempty_text(value->'reason')
  WHEN 'ACCEPTANCE_RECEIPT' THEN record_json_exact(value,ARRAY['disposition','reason']) AND value->>'disposition' IN ('ACCEPTED','REJECTED','SUPERSEDED') AND record_nonempty_text(value->'reason')
  ELSE false END
$$;
CREATE OR REPLACE FUNCTION record_lineage_closed(target uuid, scope uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
 WITH RECURSIVE authoritative(id) AS (
  SELECT artifact_id FROM record_artifact_dispositions WHERE experiment_id=scope AND disposition IN ('ACCEPTED','VALIDATED')
  UNION SELECT validation_artifact_id FROM record_artifact_dispositions WHERE experiment_id=scope AND validation_artifact_id IS NOT NULL
  UNION SELECT artifact_id FROM record_candidate_selections WHERE experiment_id=scope
  UNION SELECT seed_artifact_id FROM record_cycles WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_idea_acceptances WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_pivot_decisions WHERE experiment_id=scope
  UNION SELECT plan_artifact_id FROM record_research_attempts WHERE experiment_id=scope
  UNION SELECT report_artifact_id FROM record_verdicts WHERE experiment_id=scope
  UNION SELECT recommendation_artifact_id FROM record_verdicts WHERE experiment_id=scope
  UNION SELECT feedback_artifact_id FROM record_returns WHERE experiment_id=scope
 ), lineage(id) AS (
  SELECT id FROM authoritative
  UNION
  SELECT link.producer_id FROM record_artifact_links link JOIN lineage ON lineage.id=link.consumer_id WHERE link.experiment_id=scope
 ) SELECT EXISTS(SELECT 1 FROM lineage WHERE id=target)
$$;
CREATE OR REPLACE FUNCTION record_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_artifacts; c record_cycles; parent_idea record_artifacts;
        decision record_pivot_decisions; proof gov_evidence; retained gov_retained;
        call gov_calls; validation record_artifacts; recommendation record_artifacts;
        committed record_verdicts; attempt record_research_attempts; parent_cycle record_cycles;
BEGIN
 IF TG_OP='UPDATE' OR TG_OP='DELETE' THEN
  RAISE EXCEPTION 'immutable product record' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME<>'record_operator_profiles' AND to_jsonb(NEW)->>'experiment_id' IS NOT NULL THEN
  PERFORM 1 FROM gov_experiments WHERE id=(to_jsonb(NEW)->>'experiment_id')::uuid FOR UPDATE;
 END IF;
 IF TG_TABLE_NAME='record_operator_profiles' THEN
  NEW.content_hash:=encode(sha256(convert_to(NEW.capabilities::text || E'\n' || NEW.constraints::text, 'UTF8')), 'hex');
  IF jsonb_typeof(NEW.capabilities)<>'array' OR jsonb_array_length(NEW.capabilities)=0
     OR jsonb_typeof(NEW.constraints)<>'array' OR jsonb_array_length(NEW.constraints)=0
     OR EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.capabilities) x WHERE NOT record_nonempty_text(x))
     OR EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.constraints) x WHERE NOT record_nonempty_text(x))
     OR jsonb_array_length(NEW.capabilities)<>(SELECT count(DISTINCT x) FROM jsonb_array_elements(NEW.capabilities) x)
     OR jsonb_array_length(NEW.constraints)<>(SELECT count(DISTINCT x) FROM jsonb_array_elements(NEW.constraints) x)
  THEN RAISE EXCEPTION 'invalid operator profile'; END IF;
 ELSIF TG_TABLE_NAME='record_artifacts' THEN
  NEW.content_hash:=encode(sha256(convert_to(NEW.payload::text, 'UTF8')), 'hex');
  IF record_payload_valid(NEW.kind,NEW.payload) IS NOT TRUE THEN RAISE EXCEPTION 'invalid artifact payload'; END IF;
 ELSIF TG_TABLE_NAME='record_artifact_links' THEN
  IF record_lineage_closed(NEW.consumer_id,NEW.experiment_id)
  THEN RAISE EXCEPTION 'accepted artifact lineage is closed'; END IF;
 ELSIF TG_TABLE_NAME='record_source_refs' THEN
  IF record_lineage_closed(NEW.artifact_id,NEW.experiment_id)
  THEN RAISE EXCEPTION 'accepted artifact lineage is closed'; END IF;
  IF NEW.kind='GOVERNANCE_EVIDENCE' THEN
   SELECT * INTO proof FROM gov_evidence WHERE id=NEW.evidence_id;
   IF NOT FOUND OR (proof.call_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM gov_calls WHERE id=proof.call_id AND experiment_id=NEW.experiment_id))
   THEN RAISE EXCEPTION 'invalid evidence scope'; END IF;
  ELSE
   SELECT * INTO retained FROM gov_retained WHERE id=NEW.retained_id;
   SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id;
   IF retained.id IS NULL OR call.id IS NULL OR retained.call_id IS DISTINCT FROM NEW.call_id OR retained.grant_id IS DISTINCT FROM NEW.grant_id
      OR retained.grant_version IS DISTINCT FROM NEW.grant_version OR retained.field IS DISTINCT FROM NEW.field
      OR retained.expires_at IS DISTINCT FROM NEW.expires_at OR call.experiment_id IS DISTINCT FROM NEW.experiment_id
   THEN RAISE EXCEPTION 'invalid retained source scope'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_cycles' THEN
  IF NEW.ordinal <> (SELECT count(*)+1 FROM record_cycles WHERE experiment_id=NEW.experiment_id)
  THEN RAISE EXCEPTION 'noncontiguous research cycle'; END IF;
  IF NEW.ordinal=1 THEN
   IF NEW.parent_cycle_id IS NOT NULL THEN RAISE EXCEPTION 'initial cycle cannot have a parent'; END IF;
  ELSE
   SELECT * INTO parent_cycle FROM record_cycles WHERE id=NEW.parent_cycle_id AND experiment_id=NEW.experiment_id;
   IF parent_cycle.id IS NULL OR parent_cycle.ordinal<>NEW.ordinal-1
      OR ROW(NEW.seed_artifact_id,NEW.seed_kind,NEW.seed_version,NEW.seed_hash)
         IS DISTINCT FROM ROW(parent_cycle.seed_artifact_id,parent_cycle.seed_kind,parent_cycle.seed_version,parent_cycle.seed_hash)
   THEN RAISE EXCEPTION 'research cycle must preserve original seed and exact parent'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_pivot_decisions' THEN
  SELECT * INTO a FROM record_artifacts WHERE id=NEW.artifact_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.cycle_id;
  IF NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1) THEN RAISE EXCEPTION 'pivot requires current cycle'; END IF;
  IF a.payload->'material_pivot' IS DISTINCT FROM 'true'::jsonb OR record_operator_authorized(NEW.experiment_id,NEW.approved_by) IS NOT TRUE
  THEN RAISE EXCEPTION 'invalid material pivot approval'; END IF;
 ELSIF TG_TABLE_NAME='record_idea_acceptances' THEN
  SELECT * INTO a FROM record_artifacts WHERE id=NEW.artifact_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.cycle_id;
  IF NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1) THEN RAISE EXCEPTION 'idea requires current cycle'; END IF;
  IF c.parent_cycle_id IS NOT NULL THEN
   SELECT prior_artifact.* INTO parent_idea FROM record_idea_acceptances prior
    JOIN record_artifacts prior_artifact ON prior_artifact.id=prior.artifact_id
    WHERE prior.cycle_id=c.parent_cycle_id;
   SELECT prior_verdict.* INTO committed FROM record_returns r
    JOIN record_verdicts prior_verdict ON prior_verdict.id=r.verdict_id
    WHERE r.to_cycle_id=NEW.cycle_id;
  END IF;
  IF c.parent_cycle_id IS NOT NULL AND parent_idea.id IS NULL THEN RAISE EXCEPTION 'missing parent accepted idea'; END IF;
  IF record_operator_authorized(NEW.experiment_id,NEW.accepted_by) IS NOT TRUE
  THEN RAISE EXCEPTION 'idea acceptance requires operator capability'; END IF;
  IF committed.verdict='MATERIAL_PIVOT_RECOMMENDED' AND parent_idea.payload->>'core_intent' IS NOT DISTINCT FROM a.payload->>'core_intent'
  THEN RAISE EXCEPTION 'material pivot must change core intent'; END IF;
  IF c.parent_cycle_id IS NOT NULL AND parent_idea.payload->>'core_intent' IS DISTINCT FROM a.payload->>'core_intent' THEN
   IF a.payload->'material_pivot'<>'true'::jsonb OR NEW.pivot_approval_id IS NULL THEN RAISE EXCEPTION 'material pivot requires approval'; END IF;
  ELSIF c.parent_cycle_id IS NOT NULL AND c.purpose NOT IN ('INCONCLUSIVE_SUPPLEMENT','OFFER_GAP_RETURN') AND (a.payload->'material_pivot'='true'::jsonb OR NEW.pivot_approval_id IS NOT NULL) THEN
   RAISE EXCEPTION 'invalid pivot classification';
  END IF;
  IF c.parent_cycle_id IS NULL AND a.payload->'material_pivot'='true'::jsonb AND NEW.pivot_approval_id IS NULL
  THEN RAISE EXCEPTION 'initial material pivot requires approval'; END IF;
  IF c.parent_cycle_id IS NULL AND a.payload->'material_pivot'='false'::jsonb AND NEW.pivot_approval_id IS NOT NULL
  THEN RAISE EXCEPTION 'invalid initial pivot classification'; END IF;
  IF c.purpose IN ('INCONCLUSIVE_SUPPLEMENT','OFFER_GAP_RETURN') AND a.id IS DISTINCT FROM parent_idea.id
  THEN RAISE EXCEPTION 'supplement must preserve exact accepted idea'; END IF;
  IF NEW.pivot_approval_id IS NOT NULL THEN
   SELECT * INTO decision FROM record_pivot_decisions WHERE id=NEW.pivot_approval_id;
   IF decision.cycle_id IS DISTINCT FROM NEW.cycle_id OR decision.artifact_id IS DISTINCT FROM NEW.artifact_id OR decision.approved_by IS DISTINCT FROM NEW.accepted_by
   THEN RAISE EXCEPTION 'invalid pivot approval binding'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_research_attempts' THEN
  IF NOT EXISTS(SELECT 1 FROM record_idea_acceptances WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
     OR EXISTS(SELECT 1 FROM record_verdicts WHERE cycle_id=NEW.cycle_id)
     OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
     OR NEW.ordinal <> (SELECT count(*)+1 FROM record_research_attempts WHERE cycle_id=NEW.cycle_id)
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.plan_artifact_id AND role='ACCEPTED_IDEA')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links link JOIN record_idea_acceptances idea ON idea.artifact_id=link.producer_id
         WHERE link.consumer_id=NEW.plan_artifact_id AND link.role='ACCEPTED_IDEA' AND idea.cycle_id=NEW.cycle_id)
  THEN RAISE EXCEPTION 'research attempt requires current accepted idea and exact plan lineage'; END IF;
 ELSIF TG_TABLE_NAME='record_verdicts' THEN
  SELECT * INTO attempt FROM record_research_attempts WHERE id=NEW.attempt_id;
  IF attempt.id IS NULL
     OR NOT EXISTS(SELECT 1 FROM record_idea_acceptances WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
     OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
     OR attempt.ordinal IS DISTINCT FROM (SELECT max(ordinal) FROM record_research_attempts WHERE cycle_id=NEW.cycle_id)
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.report_artifact_id AND role='PLAN')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.report_artifact_id AND producer_id=attempt.plan_artifact_id AND role='PLAN')
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.recommendation_artifact_id AND role='REPORT')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.recommendation_artifact_id AND producer_id=NEW.report_artifact_id AND role='REPORT')
  THEN RAISE EXCEPTION 'verdict requires current attempt and exact report lineage'; END IF;
  SELECT * INTO recommendation FROM record_artifacts WHERE id=NEW.recommendation_artifact_id;
  IF recommendation.payload->>'recommendation' IS DISTINCT FROM NEW.verdict OR record_operator_authorized(NEW.experiment_id,NEW.committed_by) IS NOT TRUE
  THEN RAISE EXCEPTION 'verdict recommendation or operator mismatch'; END IF;
 ELSIF TG_TABLE_NAME='record_artifact_dispositions' THEN
  IF NEW.disposition IN ('VALIDATED','ACCEPTED') THEN
   SELECT * INTO validation FROM record_artifacts WHERE id=NEW.validation_artifact_id AND experiment_id=NEW.experiment_id;
   IF validation.kind IS DISTINCT FROM 'VALIDATION_RESULT' OR validation.payload->>'disposition' IS DISTINCT FROM 'PASS'
      OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=validation.id AND role='TARGET')<>1
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=validation.id AND role='TARGET'
          AND producer_id=NEW.artifact_id AND producer_kind=NEW.artifact_kind
          AND producer_version=NEW.artifact_version AND producer_hash=NEW.artifact_hash)
   THEN RAISE EXCEPTION 'passing validation required'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_cycle_return_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.ordinal>1 AND NOT EXISTS(
  SELECT 1 FROM record_returns r JOIN record_verdicts v ON v.id=r.verdict_id
  WHERE r.to_cycle_id=NEW.id AND r.from_cycle_id=NEW.parent_cycle_id
    AND r.experiment_id=NEW.experiment_id
    AND v.cycle_id=NEW.parent_cycle_id AND v.verdict IN ('REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED','INCONCLUSIVE','PROCEED_TO_OFFER'))
 THEN RAISE EXCEPTION 'research cycle requires exact committed return'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION record_origin_return_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_artifacts; parent record_cycles; root record_cycles; c record_cycles;
 v record_verdicts; idea record_idea_acceptances; selection record_candidate_selections;
 scope_id uuid; expected_verdict text; expected_purpose text;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable product record'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF TG_TABLE_NAME='record_candidate_selections' THEN
  SELECT * INTO a FROM record_artifacts WHERE id=NEW.artifact_id;
  IF record_operator_authorized(NEW.experiment_id,NEW.selected_by) IS NOT TRUE
    OR ROW(a.workflow_id,a.agent_id) IS DISTINCT FROM ROW(NEW.workflow_id,NEW.agent_id)
    OR NOT EXISTS(SELECT 1 FROM record_experiments e WHERE e.id=NEW.experiment_id AND e.operator_profile_id=NEW.profile_id AND e.operator_profile_version=NEW.profile_version)
    OR EXISTS(SELECT 1 FROM record_cycles WHERE experiment_id=NEW.experiment_id)
  THEN RAISE EXCEPTION 'invalid candidate selection'; END IF;
 ELSIF TG_TABLE_NAME='record_cycles' THEN
  IF record_operator_authorized(NEW.experiment_id,(SELECT p.operator_id FROM record_experiments e JOIN record_operator_profiles p ON p.id=e.operator_profile_id AND p.version=e.operator_profile_version WHERE e.id=NEW.experiment_id)) IS NOT TRUE
  THEN RAISE EXCEPTION 'inactive experiment owner'; END IF;
  IF NEW.ordinal=1 THEN
   IF NEW.purpose IS DISTINCT FROM 'INITIAL' OR NEW.episode_id IS DISTINCT FROM NEW.id THEN RAISE EXCEPTION 'invalid initial episode'; END IF;
   SELECT * INTO a FROM record_artifacts WHERE id=NEW.seed_artifact_id;
   IF NEW.idea_mode='SYSTEM_DISCOVERY' THEN
    SELECT * INTO selection FROM record_candidate_selections WHERE id=NEW.selection_id;
    IF ROW(selection.artifact_id,selection.artifact_kind,selection.artifact_version,selection.artifact_hash,selection.experiment_id)
      IS DISTINCT FROM ROW(NEW.seed_artifact_id,NEW.seed_kind,NEW.seed_version,NEW.seed_hash,NEW.experiment_id)
    THEN RAISE EXCEPTION 'exact selection required'; END IF;
   ELSIF a.payload->>'origin' IS DISTINCT FROM 'USER_SUPPLIED' OR EXISTS(SELECT 1 FROM record_candidate_selections WHERE experiment_id=NEW.experiment_id)
   THEN RAISE EXCEPTION 'original user seed required'; END IF;
  ELSE
   SELECT * INTO parent FROM record_cycles WHERE id=NEW.parent_cycle_id;
   IF ROW(NEW.idea_mode,NEW.selection_id,NEW.episode_id) IS DISTINCT FROM ROW(parent.idea_mode,parent.selection_id,parent.episode_id)
      OR NEW.purpose='INITIAL'
   THEN RAISE EXCEPTION 'immutable origin and episode required'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_returns' THEN
  SELECT * INTO v FROM record_verdicts WHERE id=NEW.verdict_id;
  SELECT * INTO parent FROM record_cycles WHERE id=NEW.from_cycle_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.to_cycle_id;
  SELECT * INTO root FROM record_cycles WHERE experiment_id=NEW.experiment_id AND ordinal=1;
  SELECT * INTO idea FROM record_idea_acceptances WHERE cycle_id=NEW.from_cycle_id;
  expected_verdict:=CASE NEW.kind WHEN 'SAME_INTENT' THEN 'REFINE_SAME_IDEA' WHEN 'MATERIAL_PIVOT' THEN 'MATERIAL_PIVOT_RECOMMENDED' WHEN 'INCONCLUSIVE_SUPPLEMENT' THEN 'INCONCLUSIVE' WHEN 'OFFER_GAP' THEN 'PROCEED_TO_OFFER' END;
  expected_purpose:=CASE NEW.kind WHEN 'SAME_INTENT' THEN 'SAME_INTENT_RETURN' WHEN 'MATERIAL_PIVOT' THEN 'MATERIAL_PIVOT_RETURN' WHEN 'INCONCLUSIVE_SUPPLEMENT' THEN 'INCONCLUSIVE_SUPPLEMENT' WHEN 'OFFER_GAP' THEN 'OFFER_GAP_RETURN' END;
  scope_id:=CASE NEW.kind WHEN 'SAME_INTENT' THEN CASE WHEN parent.idea_mode='USER_SEEDED_REFINEMENT' THEN parent.seed_artifact_id ELSE (SELECT artifact_id FROM record_idea_acceptances WHERE cycle_id=root.id) END WHEN 'OFFER_GAP' THEN idea.artifact_id ELSE parent.episode_id END;
  IF v.id IS NULL OR c.id IS NULL OR parent.id IS NULL OR idea.id IS NULL OR expected_verdict IS NULL
   OR v.cycle_id IS DISTINCT FROM parent.id OR v.verdict IS DISTINCT FROM expected_verdict
   OR c.parent_cycle_id IS DISTINCT FROM parent.id OR c.ordinal<>parent.ordinal+1 OR c.purpose IS DISTINCT FROM expected_purpose
   OR c.id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
   OR NEW.applicable_scope_id IS DISTINCT FROM scope_id OR NEW.idea_artifact_id IS DISTINCT FROM idea.artifact_id
   OR NEW.ordinal<>(SELECT count(*)+1 FROM record_returns WHERE experiment_id=NEW.experiment_id AND kind=NEW.kind AND applicable_scope_id=scope_id)
  THEN RAISE EXCEPTION 'invalid scoped research return'; END IF;
  IF NOT EXISTS(SELECT 1 FROM record_artifact_dispositions WHERE artifact_id=NEW.feedback_artifact_id AND disposition='ACCEPTED')
   OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.feedback_artifact_id AND role IN ('REPORT','RECOMMENDATION','ACCEPTED_IDEA'))<>3
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.feedback_artifact_id AND role='REPORT' AND producer_id=v.report_artifact_id)
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.feedback_artifact_id AND role='RECOMMENDATION' AND producer_id=v.recommendation_artifact_id)
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.feedback_artifact_id AND role='ACCEPTED_IDEA' AND producer_id=idea.artifact_id)
  THEN RAISE EXCEPTION 'accepted exact return evidence required'; END IF;
  IF NEW.kind='OFFER_GAP' THEN
   -- Activation requires the future offer-owner migration to establish this typed accepted bundle.
   IF NOT EXISTS(SELECT 1 FROM record_artifacts a JOIN record_artifact_dispositions d ON d.artifact_id=a.id AND d.disposition='ACCEPTED' WHERE a.id=NEW.offer_input_bundle_id AND a.experiment_id=NEW.experiment_id AND a.kind='OFFER_DESIGN_INPUT_BUNDLE')
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.feedback_artifact_id AND producer_id=NEW.offer_input_bundle_id AND role='OFFER_INPUT_BUNDLE')
      OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.offer_input_bundle_id AND role IN ('ACCEPTED_IDEA','REPORT','RECOMMENDATION'))<>3
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.offer_input_bundle_id AND role='ACCEPTED_IDEA' AND producer_id=idea.artifact_id)
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.offer_input_bundle_id AND role='REPORT' AND producer_id=v.report_artifact_id)
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.offer_input_bundle_id AND role='RECOMMENDATION' AND producer_id=v.recommendation_artifact_id)
   THEN RAISE EXCEPTION 'accepted offer input bundle required'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_artifacts' THEN
  IF record_operator_authorized(NEW.experiment_id,NEW.created_by) IS NOT TRUE THEN RAISE EXCEPTION 'inactive artifact owner'; END IF;
 ELSIF TG_TABLE_NAME='record_research_attempts' THEN
  IF record_operator_authorized(NEW.experiment_id,(SELECT p.operator_id FROM record_experiments e JOIN record_operator_profiles p ON p.id=e.operator_profile_id AND p.version=e.operator_profile_version WHERE e.id=NEW.experiment_id)) IS NOT TRUE THEN RAISE EXCEPTION 'inactive experiment owner'; END IF;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.cycle_id;
  IF c.ordinal>1 AND NOT EXISTS(SELECT 1 FROM record_returns r JOIN record_artifact_links l ON l.producer_id=r.feedback_artifact_id AND l.consumer_id=NEW.plan_artifact_id AND l.role='RETURN_FEEDBACK' WHERE r.to_cycle_id=c.id)
  THEN RAISE EXCEPTION 'research plan requires exact return feedback'; END IF;
 ELSIF TG_TABLE_NAME='record_artifact_dispositions' THEN
  IF record_operator_authorized(NEW.experiment_id,NEW.decided_by) IS NOT TRUE THEN RAISE EXCEPTION 'inactive decision owner'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_candidate_selections_origin_guard BEFORE INSERT OR UPDATE OR DELETE ON record_candidate_selections FOR EACH ROW EXECUTE FUNCTION record_origin_return_guard();
CREATE TRIGGER record_cycles_origin_guard BEFORE INSERT OR UPDATE OR DELETE ON record_cycles FOR EACH ROW EXECUTE FUNCTION record_origin_return_guard();
CREATE TRIGGER record_returns_origin_guard BEFORE INSERT OR UPDATE OR DELETE ON record_returns FOR EACH ROW EXECUTE FUNCTION record_origin_return_guard();
CREATE TRIGGER record_artifacts_origin_guard BEFORE INSERT OR UPDATE OR DELETE ON record_artifacts FOR EACH ROW EXECUTE FUNCTION record_origin_return_guard();
CREATE TRIGGER record_research_attempts_origin_guard BEFORE INSERT OR UPDATE OR DELETE ON record_research_attempts FOR EACH ROW EXECUTE FUNCTION record_origin_return_guard();
CREATE TRIGGER record_artifact_dispositions_origin_guard BEFORE INSERT OR UPDATE OR DELETE ON record_artifact_dispositions FOR EACH ROW EXECUTE FUNCTION record_origin_return_guard();
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM record_cycles WHERE ordinal>3 OR idea_mode<>'USER_SEEDED_REFINEMENT' OR purpose NOT IN ('INITIAL','SAME_INTENT_RETURN','MATERIAL_PIVOT_RETURN'))
  OR EXISTS(SELECT 1 FROM record_returns WHERE kind NOT IN ('SAME_INTENT','MATERIAL_PIVOT'))
  OR EXISTS(SELECT 1 FROM record_artifacts WHERE kind='OFFER_RESEARCH_GAP_BRIEF')
 THEN RAISE EXCEPTION 'new research history cannot be represented by previous schema'; END IF;
END $$;
DROP TRIGGER record_candidate_selections_origin_guard ON record_candidate_selections;
DROP TRIGGER record_cycles_origin_guard ON record_cycles;
DROP TRIGGER record_returns_origin_guard ON record_returns;
DROP TRIGGER record_artifacts_origin_guard ON record_artifacts;
DROP TRIGGER record_research_attempts_origin_guard ON record_research_attempts;
DROP TRIGGER record_artifact_dispositions_origin_guard ON record_artifact_dispositions;
DROP FUNCTION record_origin_return_guard();
CREATE OR REPLACE FUNCTION record_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_artifacts; c record_cycles; parent_idea record_artifacts;
        decision record_pivot_decisions; proof gov_evidence; retained gov_retained;
        call gov_calls; validation record_artifacts; recommendation record_artifacts;
        committed record_verdicts; attempt record_research_attempts; parent_cycle record_cycles;
BEGIN
 IF TG_OP='UPDATE' OR TG_OP='DELETE' THEN
  RAISE EXCEPTION 'immutable product record' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME<>'record_operator_profiles' AND to_jsonb(NEW)->>'experiment_id' IS NOT NULL THEN
  PERFORM 1 FROM gov_experiments WHERE id=(to_jsonb(NEW)->>'experiment_id')::uuid FOR UPDATE;
 END IF;
 IF TG_TABLE_NAME='record_operator_profiles' THEN
  NEW.content_hash:=encode(sha256(convert_to(NEW.capabilities::text || E'\n' || NEW.constraints::text, 'UTF8')), 'hex');
  IF jsonb_typeof(NEW.capabilities)<>'array' OR jsonb_array_length(NEW.capabilities)=0
     OR jsonb_typeof(NEW.constraints)<>'array' OR jsonb_array_length(NEW.constraints)=0
     OR EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.capabilities) x WHERE NOT record_nonempty_text(x))
     OR EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.constraints) x WHERE NOT record_nonempty_text(x))
     OR jsonb_array_length(NEW.capabilities)<>(SELECT count(DISTINCT x) FROM jsonb_array_elements(NEW.capabilities) x)
     OR jsonb_array_length(NEW.constraints)<>(SELECT count(DISTINCT x) FROM jsonb_array_elements(NEW.constraints) x)
  THEN RAISE EXCEPTION 'invalid operator profile'; END IF;
 ELSIF TG_TABLE_NAME='record_artifacts' THEN
  NEW.content_hash:=encode(sha256(convert_to(NEW.payload::text, 'UTF8')), 'hex');
  IF record_payload_valid(NEW.kind,NEW.payload) IS NOT TRUE THEN RAISE EXCEPTION 'invalid artifact payload'; END IF;
 ELSIF TG_TABLE_NAME='record_artifact_links' THEN
  IF record_lineage_closed(NEW.consumer_id,NEW.experiment_id)
  THEN RAISE EXCEPTION 'accepted artifact lineage is closed'; END IF;
 ELSIF TG_TABLE_NAME='record_source_refs' THEN
  IF record_lineage_closed(NEW.artifact_id,NEW.experiment_id)
  THEN RAISE EXCEPTION 'accepted artifact lineage is closed'; END IF;
  IF NEW.kind='GOVERNANCE_EVIDENCE' THEN
   SELECT * INTO proof FROM gov_evidence WHERE id=NEW.evidence_id;
   IF NOT FOUND OR (proof.call_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM gov_calls WHERE id=proof.call_id AND experiment_id=NEW.experiment_id))
   THEN RAISE EXCEPTION 'invalid evidence scope'; END IF;
  ELSE
   SELECT * INTO retained FROM gov_retained WHERE id=NEW.retained_id;
   SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id;
   IF retained.id IS NULL OR call.id IS NULL OR retained.call_id IS DISTINCT FROM NEW.call_id OR retained.grant_id IS DISTINCT FROM NEW.grant_id
      OR retained.grant_version IS DISTINCT FROM NEW.grant_version OR retained.field IS DISTINCT FROM NEW.field
      OR retained.expires_at IS DISTINCT FROM NEW.expires_at OR call.experiment_id IS DISTINCT FROM NEW.experiment_id
   THEN RAISE EXCEPTION 'invalid retained source scope'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_cycles' THEN
  IF NEW.ordinal <> (SELECT count(*)+1 FROM record_cycles WHERE experiment_id=NEW.experiment_id)
  THEN RAISE EXCEPTION 'noncontiguous research cycle'; END IF;
  IF NEW.ordinal=1 THEN
   IF NEW.parent_cycle_id IS NOT NULL THEN RAISE EXCEPTION 'initial cycle cannot have a parent'; END IF;
  ELSE
   SELECT * INTO parent_cycle FROM record_cycles WHERE id=NEW.parent_cycle_id AND experiment_id=NEW.experiment_id;
   IF parent_cycle.id IS NULL OR parent_cycle.ordinal<>NEW.ordinal-1
      OR ROW(NEW.seed_artifact_id,NEW.seed_kind,NEW.seed_version,NEW.seed_hash)
         IS DISTINCT FROM ROW(parent_cycle.seed_artifact_id,parent_cycle.seed_kind,parent_cycle.seed_version,parent_cycle.seed_hash)
   THEN RAISE EXCEPTION 'research cycle must preserve original seed and exact parent'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_pivot_decisions' THEN
  SELECT * INTO a FROM record_artifacts WHERE id=NEW.artifact_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.cycle_id;
  IF a.payload->'material_pivot'<>'true'::jsonb OR c.parent_cycle_id IS NULL OR NOT EXISTS(
    SELECT 1 FROM record_experiments e JOIN record_operator_profiles p
      ON p.id=e.operator_profile_id AND p.version=e.operator_profile_version
    WHERE e.id=NEW.experiment_id AND p.operator_id=NEW.approved_by
      AND p.capabilities @> '["MATERIAL_PIVOT_APPROVAL"]'::jsonb)
  THEN RAISE EXCEPTION 'invalid material pivot approval'; END IF;
 ELSIF TG_TABLE_NAME='record_idea_acceptances' THEN
  SELECT * INTO a FROM record_artifacts WHERE id=NEW.artifact_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.cycle_id;
  IF c.parent_cycle_id IS NOT NULL THEN
   SELECT prior_artifact.* INTO parent_idea FROM record_idea_acceptances prior
    JOIN record_artifacts prior_artifact ON prior_artifact.id=prior.artifact_id
    WHERE prior.cycle_id=c.parent_cycle_id;
   SELECT prior_verdict.* INTO committed FROM record_returns r
    JOIN record_verdicts prior_verdict ON prior_verdict.id=r.verdict_id
    WHERE r.to_cycle_id=NEW.cycle_id;
  END IF;
  IF c.parent_cycle_id IS NOT NULL AND parent_idea.id IS NULL THEN RAISE EXCEPTION 'missing parent accepted idea'; END IF;
  IF NOT EXISTS(
    SELECT 1 FROM record_experiments e JOIN record_operator_profiles p
      ON p.id=e.operator_profile_id AND p.version=e.operator_profile_version
    WHERE e.id=NEW.experiment_id AND p.operator_id=NEW.accepted_by
      AND p.capabilities @> '["RESEARCH_REVIEW"]'::jsonb)
  THEN RAISE EXCEPTION 'idea acceptance requires operator capability'; END IF;
  IF committed.verdict='MATERIAL_PIVOT_RECOMMENDED' AND parent_idea.payload->>'core_intent' IS NOT DISTINCT FROM a.payload->>'core_intent'
  THEN RAISE EXCEPTION 'material pivot must change core intent'; END IF;
  IF c.parent_cycle_id IS NOT NULL AND parent_idea.payload->>'core_intent' IS DISTINCT FROM a.payload->>'core_intent' THEN
   IF a.payload->'material_pivot'<>'true'::jsonb OR NEW.pivot_approval_id IS NULL THEN RAISE EXCEPTION 'material pivot requires approval'; END IF;
  ELSIF a.payload->'material_pivot'='true'::jsonb OR NEW.pivot_approval_id IS NOT NULL THEN
   RAISE EXCEPTION 'invalid pivot classification';
  END IF;
  IF NEW.pivot_approval_id IS NOT NULL THEN
   SELECT * INTO decision FROM record_pivot_decisions WHERE id=NEW.pivot_approval_id;
   IF decision.cycle_id IS DISTINCT FROM NEW.cycle_id OR decision.artifact_id IS DISTINCT FROM NEW.artifact_id OR decision.approved_by IS DISTINCT FROM NEW.accepted_by
   THEN RAISE EXCEPTION 'invalid pivot approval binding'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_research_attempts' THEN
  IF NOT EXISTS(SELECT 1 FROM record_idea_acceptances WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
     OR EXISTS(SELECT 1 FROM record_verdicts WHERE cycle_id=NEW.cycle_id)
     OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
     OR NEW.ordinal <> (SELECT count(*)+1 FROM record_research_attempts WHERE cycle_id=NEW.cycle_id)
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.plan_artifact_id AND role='ACCEPTED_IDEA')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links link JOIN record_idea_acceptances idea ON idea.artifact_id=link.producer_id
         WHERE link.consumer_id=NEW.plan_artifact_id AND link.role='ACCEPTED_IDEA' AND idea.cycle_id=NEW.cycle_id)
  THEN RAISE EXCEPTION 'research attempt requires current accepted idea and exact plan lineage'; END IF;
 ELSIF TG_TABLE_NAME='record_verdicts' THEN
  SELECT * INTO attempt FROM record_research_attempts WHERE id=NEW.attempt_id;
  IF attempt.id IS NULL
     OR NOT EXISTS(SELECT 1 FROM record_idea_acceptances WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
     OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
     OR attempt.ordinal IS DISTINCT FROM (SELECT max(ordinal) FROM record_research_attempts WHERE cycle_id=NEW.cycle_id)
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.report_artifact_id AND role='PLAN')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.report_artifact_id AND producer_id=attempt.plan_artifact_id AND role='PLAN')
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.recommendation_artifact_id AND role='REPORT')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.recommendation_artifact_id AND producer_id=NEW.report_artifact_id AND role='REPORT')
  THEN RAISE EXCEPTION 'verdict requires current attempt and exact report lineage'; END IF;
  SELECT * INTO recommendation FROM record_artifacts WHERE id=NEW.recommendation_artifact_id;
  IF recommendation.payload->>'recommendation' IS DISTINCT FROM NEW.verdict OR NOT EXISTS(
    SELECT 1 FROM record_experiments e JOIN record_operator_profiles p
      ON p.id=e.operator_profile_id AND p.version=e.operator_profile_version
    WHERE e.id=NEW.experiment_id AND p.operator_id=NEW.committed_by
      AND p.capabilities @> '["RESEARCH_REVIEW"]'::jsonb)
  THEN RAISE EXCEPTION 'verdict recommendation or operator mismatch'; END IF;
 ELSIF TG_TABLE_NAME='record_returns' THEN
  SELECT * INTO committed FROM record_verdicts WHERE id=NEW.verdict_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.to_cycle_id;
  IF committed.id IS NULL OR c.id IS NULL OR committed.cycle_id IS DISTINCT FROM NEW.from_cycle_id OR committed.verdict NOT IN ('REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED')
     OR c.parent_cycle_id IS DISTINCT FROM NEW.from_cycle_id OR c.ordinal<>NEW.ordinal+1
     OR NEW.ordinal IS DISTINCT FROM (SELECT ordinal FROM record_cycles WHERE id=NEW.from_cycle_id)
  THEN RAISE EXCEPTION 'invalid research return'; END IF;
 ELSIF TG_TABLE_NAME='record_artifact_dispositions' THEN
  IF NEW.disposition IN ('VALIDATED','ACCEPTED') THEN
   SELECT * INTO validation FROM record_artifacts WHERE id=NEW.validation_artifact_id AND experiment_id=NEW.experiment_id;
   IF validation.kind IS DISTINCT FROM 'VALIDATION_RESULT' OR validation.payload->>'disposition' IS DISTINCT FROM 'PASS'
      OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=validation.id AND role='TARGET')<>1
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=validation.id AND role='TARGET'
          AND producer_id=NEW.artifact_id AND producer_kind=NEW.artifact_kind
          AND producer_version=NEW.artifact_version AND producer_hash=NEW.artifact_hash)
   THEN RAISE EXCEPTION 'passing validation required'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_cycle_return_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.ordinal>1 AND NOT EXISTS(
  SELECT 1 FROM record_returns r JOIN record_verdicts v ON v.id=r.verdict_id
  WHERE r.to_cycle_id=NEW.id AND r.from_cycle_id=NEW.parent_cycle_id
    AND r.experiment_id=NEW.experiment_id AND r.ordinal=NEW.ordinal-1
    AND v.cycle_id=NEW.parent_cycle_id AND v.verdict IN ('REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED'))
 THEN RAISE EXCEPTION 'research cycle requires exact committed return'; END IF;
 RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION record_lineage_closed(target uuid, scope uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
 WITH RECURSIVE authoritative(id) AS (
  SELECT artifact_id FROM record_artifact_dispositions WHERE experiment_id=scope AND disposition IN ('ACCEPTED','VALIDATED')
  UNION SELECT validation_artifact_id FROM record_artifact_dispositions WHERE experiment_id=scope AND validation_artifact_id IS NOT NULL
  UNION SELECT seed_artifact_id FROM record_cycles WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_idea_acceptances WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_pivot_decisions WHERE experiment_id=scope
  UNION SELECT plan_artifact_id FROM record_research_attempts WHERE experiment_id=scope
  UNION SELECT report_artifact_id FROM record_verdicts WHERE experiment_id=scope
  UNION SELECT recommendation_artifact_id FROM record_verdicts WHERE experiment_id=scope
  UNION SELECT feedback_artifact_id FROM record_returns WHERE experiment_id=scope
 ), lineage(id) AS (
  SELECT id FROM authoritative
  UNION
  SELECT link.producer_id FROM record_artifact_links link JOIN lineage ON lineage.id=link.consumer_id WHERE link.experiment_id=scope
 ) SELECT EXISTS(SELECT 1 FROM lineage WHERE id=target)
$$;
CREATE OR REPLACE FUNCTION record_payload_valid(kind text, value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE kind
  WHEN 'EXPERIMENT_BRIEF' THEN record_json_exact(value,ARRAY['objective']) AND record_nonempty_text(value->'objective')
  WHEN 'IDEA_SEED' THEN record_json_exact(value,ARRAY['origin','statement']) AND value->>'origin' IN ('USER_SUPPLIED','AGENT_DISCOVERED') AND record_nonempty_text(value->'statement')
  WHEN 'IDEA_CANDIDATE' THEN record_json_exact(value,ARRAY['title','hypothesis']) AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'hypothesis')
  WHEN 'IDEA_BRIEF' THEN record_json_exact(value,ARRAY['title','customer','problem','core_intent','material_pivot']) AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'customer') AND record_nonempty_text(value->'problem') AND record_nonempty_text(value->'core_intent') AND jsonb_typeof(value->'material_pivot')='boolean'
  WHEN 'RESEARCH_PLAN' THEN record_json_exact(value,ARRAY['questions','method']) AND record_nonempty_text_array(value->'questions') AND record_nonempty_text(value->'method')
  WHEN 'RESEARCH_EVIDENCE' THEN record_json_exact(value,ARRAY['claim','finding']) AND record_nonempty_text(value->'claim') AND record_nonempty_text(value->'finding')
  WHEN 'COMPETITOR_PROFILE' THEN record_json_exact(value,ARRAY['name','positioning']) AND record_nonempty_text(value->'name') AND record_nonempty_text(value->'positioning')
  WHEN 'SERVICE_PROFILE' THEN record_json_exact(value,ARRAY['name','scope']) AND record_nonempty_text(value->'name') AND record_nonempty_text(value->'scope')
  WHEN 'PRICE_OBSERVATION' THEN record_json_exact(value,ARRAY['status','currency','amount','unit','source_note']) AND record_nonempty_text(value->'unit') AND record_nonempty_text(value->'source_note') AND ((value->>'status'='QUOTED' AND value->>'currency' ~ '^[A-Z]{3}$' AND value->>'amount' ~ '^[0-9]+(\.[0-9]{1,6})?$' AND (value->>'amount')::numeric>0 AND (value->>'amount')::numeric<1000000000000) OR (value->>'status'='REQUIRED_UNAVAILABLE' AND value->'currency'='null'::jsonb AND value->'amount'='null'::jsonb))
  WHEN 'MARKET_RESEARCH_REPORT' THEN record_json_exact(value,ARRAY['finding','limitations']) AND record_nonempty_text(value->'finding') AND record_nonempty_text_array(value->'limitations')
  WHEN 'MARKET_RESEARCH_RECOMMENDATION' THEN record_json_exact(value,ARRAY['recommendation','rationale']) AND value->>'recommendation' IN ('PROCEED_TO_OFFER','REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED','KILL_IDEA','INCONCLUSIVE') AND record_nonempty_text(value->'rationale')
  WHEN 'RESEARCH_FEEDBACK_BRIEF' THEN record_json_exact(value,ARRAY['preserve','change']) AND record_nonempty_text_array(value->'preserve') AND record_nonempty_text_array(value->'change')
  WHEN 'VALIDATION_RESULT' THEN record_json_exact(value,ARRAY['validator','disposition','reason']) AND record_nonempty_text(value->'validator') AND value->>'disposition' IN ('PASS','FAIL') AND record_nonempty_text(value->'reason')
  WHEN 'ACCEPTANCE_RECEIPT' THEN record_json_exact(value,ARRAY['disposition','reason']) AND value->>'disposition' IN ('ACCEPTED','REJECTED','SUPERSEDED') AND record_nonempty_text(value->'reason')
  ELSE false END
$$;

ALTER TABLE record_returns DISABLE TRIGGER record_returns_guard;
UPDATE record_returns r SET ordinal=(SELECT ordinal FROM record_cycles WHERE id=r.from_cycle_id);
ALTER TABLE record_returns ENABLE TRIGGER record_returns_guard;
ALTER TABLE record_returns DROP COLUMN kind, DROP COLUMN applicable_scope_id, DROP COLUMN idea_artifact_id, DROP COLUMN offer_input_bundle_id;
ALTER TABLE record_returns ADD UNIQUE(experiment_id,ordinal), ADD CHECK(ordinal BETWEEN 1 AND 2 AND feedback_kind='RESEARCH_FEEDBACK_BRIEF');
ALTER TABLE record_cycles DROP CONSTRAINT ck_record_cycle_ordinal;
ALTER TABLE record_cycles DROP COLUMN idea_mode, DROP COLUMN selection_id, DROP COLUMN purpose, DROP COLUMN episode_id;
ALTER TABLE record_cycles ADD CHECK(ordinal BETWEEN 1 AND 3 AND seed_kind='IDEA_SEED');
ALTER TABLE record_idea_acceptances ADD UNIQUE(artifact_id);
DROP TABLE record_candidate_selections;
ALTER TABLE record_artifacts DROP CONSTRAINT record_artifacts_kind_check;
ALTER TABLE record_artifacts ADD CHECK(kind IN ('EXPERIMENT_BRIEF','IDEA_SEED','IDEA_CANDIDATE','IDEA_BRIEF','RESEARCH_PLAN','RESEARCH_EVIDENCE','COMPETITOR_PROFILE','SERVICE_PROFILE','PRICE_OBSERVATION','MARKET_RESEARCH_REPORT','MARKET_RESEARCH_RECOMMENDATION','RESEARCH_FEEDBACK_BRIEF','VALIDATION_RESULT','ACCEPTANCE_RECEIPT'));
""")
