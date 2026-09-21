"""strategy promotion, live observation, rollback, and controls

Revision ID: 20260921_14
Revises: 20260921_13
"""

from alembic import op

revision = "20260921_14"
down_revision = "20260921_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE record_learning_input_bundle_seals (
 bundle_id UUID PRIMARY KEY REFERENCES record_learning_input_bundles(id),
 reference_count INTEGER NOT NULL, reference_set_hash VARCHAR(64) NOT NULL,
 sealed_at TIMESTAMPTZ NOT NULL,
 CHECK(reference_count>0 AND reference_set_hash ~ '^[0-9a-f]{64}$')
);
INSERT INTO record_learning_input_bundle_seals(bundle_id,reference_count,reference_set_hash,sealed_at)
SELECT b.id,
 (SELECT count(*) FROM record_learning_input_artifacts a WHERE a.bundle_id=b.id)
 +(SELECT count(*) FROM record_learning_input_evidence e WHERE e.bundle_id=b.id)
 +(SELECT count(*) FROM record_learning_input_call_snapshots c WHERE c.bundle_id=b.id)
 +(SELECT count(*) FROM record_learning_input_usage u WHERE u.bundle_id=b.id)
 +(SELECT count(*) FROM record_learning_input_costs c WHERE c.bundle_id=b.id),
 b.content_hash,b.created_at FROM record_learning_input_bundles b;

CREATE TABLE record_strategy_agent_versions (
 id UUID PRIMARY KEY, logical_id UUID NOT NULL, version INTEGER NOT NULL, supersedes_id UUID,
 origin_candidate_id UUID, role VARCHAR(32) NOT NULL,
 prompt_artifact_id UUID NOT NULL, prompt_experiment_id UUID NOT NULL, prompt_kind VARCHAR(64) NOT NULL,
 prompt_version INTEGER NOT NULL, prompt_hash VARCHAR(64) NOT NULL,
 few_shot_artifact_id UUID, few_shot_experiment_id UUID, few_shot_kind VARCHAR(64),
 few_shot_version INTEGER, few_shot_hash VARCHAR(64),
 model_identifier VARCHAR(100) NOT NULL, reasoning_effort VARCHAR(16) NOT NULL,
 budget_policy_version VARCHAR(64) NOT NULL, max_tool_calls INTEGER NOT NULL,
 max_searches INTEGER NOT NULL, max_pages INTEGER NOT NULL,
 configuration JSONB NOT NULL, configuration_hash VARCHAR(64) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(supersedes_id) REFERENCES record_strategy_agent_versions(id),
 FOREIGN KEY(origin_candidate_id) REFERENCES record_learning_candidate_versions(id),
 FOREIGN KEY(prompt_artifact_id,prompt_experiment_id,prompt_kind,prompt_version,prompt_hash)
  REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(few_shot_artifact_id,few_shot_experiment_id,few_shot_kind,few_shot_version,few_shot_hash)
  REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 UNIQUE(logical_id,version), UNIQUE(id,role,configuration_hash),
 CHECK(version>0 AND role IN ('DISCOVERY','QUALIFICATION','OUTREACH','REPLY')),
 CHECK(reasoning_effort IN ('NONE','MINIMAL','LOW','MEDIUM','HIGH','XHIGH')),
 CHECK(budget_policy_version='STRATEGY_BUDGET_LIMITS_V1'
  AND max_tool_calls BETWEEN 0 AND 100 AND max_searches BETWEEN 0 AND 100 AND max_pages BETWEEN 0 AND 500
  AND max_tool_calls+max_searches+max_pages>0),
 CHECK(configuration->>'role'=role AND configuration_hash ~ '^[0-9a-f]{64}$'),
 CHECK((few_shot_artifact_id IS NULL AND few_shot_experiment_id IS NULL AND few_shot_kind IS NULL AND few_shot_version IS NULL AND few_shot_hash IS NULL)
    OR (few_shot_artifact_id IS NOT NULL AND few_shot_experiment_id IS NOT NULL AND few_shot_kind IS NOT NULL AND few_shot_version IS NOT NULL AND few_shot_hash IS NOT NULL))
);
CREATE TABLE record_global_strategy_packages (
 id UUID PRIMARY KEY, logical_id UUID NOT NULL, version INTEGER NOT NULL, supersedes_id UUID,
 package_hash VARCHAR(64) NOT NULL, created_by UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(supersedes_id) REFERENCES record_global_strategy_packages(id),
 FOREIGN KEY(created_by) REFERENCES record_operators(id),
 UNIQUE(logical_id,version), UNIQUE(id,version,package_hash),
 CHECK(version>0 AND package_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_strategy_package_members (
 package_id UUID NOT NULL REFERENCES record_global_strategy_packages(id), role VARCHAR(32) NOT NULL,
 agent_version_id UUID NOT NULL, configuration_hash VARCHAR(64) NOT NULL,
 PRIMARY KEY(package_id,role), UNIQUE(package_id,agent_version_id),
 FOREIGN KEY(agent_version_id,role,configuration_hash)
  REFERENCES record_strategy_agent_versions(id,role,configuration_hash),
 CHECK(role IN ('DISCOVERY','QUALIFICATION','OUTREACH','REPLY'))
);
CREATE TABLE record_strategy_package_seals (
 package_id UUID PRIMARY KEY REFERENCES record_global_strategy_packages(id),
 member_count INTEGER NOT NULL, member_set_hash VARCHAR(64) NOT NULL, sealed_at TIMESTAMPTZ NOT NULL,
 CHECK(member_count=4 AND member_set_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_experiment_strategy_bindings (
 experiment_id UUID PRIMARY KEY REFERENCES record_experiments(id), package_id UUID NOT NULL,
 package_version INTEGER NOT NULL, package_hash VARCHAR(64) NOT NULL, frozen_by UUID NOT NULL,
 content_hash VARCHAR(64) NOT NULL, frozen_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(package_id,package_version,package_hash)
  REFERENCES record_global_strategy_packages(id,version,package_hash),
 FOREIGN KEY(frozen_by) REFERENCES record_operators(id),
 UNIQUE(experiment_id,package_id),
 CHECK(content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_strategy_execution_bindings (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, workflow_id UUID NOT NULL, agent_id UUID NOT NULL,
 operation_id UUID NOT NULL, package_id UUID NOT NULL, role VARCHAR(32) NOT NULL,
 agent_version_id UUID NOT NULL, configuration_hash VARCHAR(64) NOT NULL,
 model_config_id UUID NOT NULL, model_config_workflow_id UUID NOT NULL, model_config_version UUID NOT NULL,
 content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(experiment_id,package_id) REFERENCES record_experiment_strategy_bindings(experiment_id,package_id),
 FOREIGN KEY(operation_id,workflow_id,experiment_id)
  REFERENCES gov_operations(id,workflow_id,experiment_id),
 FOREIGN KEY(agent_id,workflow_id) REFERENCES record_agents(id,workflow_id),
 FOREIGN KEY(package_id,role) REFERENCES record_strategy_package_members(package_id,role),
 FOREIGN KEY(agent_version_id,role,configuration_hash)
  REFERENCES record_strategy_agent_versions(id,role,configuration_hash),
 FOREIGN KEY(model_config_id,model_config_workflow_id,model_config_version)
  REFERENCES gov_configs(id,workflow_id,version),
 UNIQUE(operation_id), CHECK(content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_strategy_registry (
 id INTEGER PRIMARY KEY CHECK(id=1)
);
INSERT INTO record_strategy_registry(id) VALUES(1);
CREATE TABLE record_strategy_promotion_decisions (
 id UUID PRIMARY KEY, proposal_id UUID NOT NULL, candidate_id UUID NOT NULL,
 comparison_id UUID NOT NULL, assessment_id UUID NOT NULL, baseline_package_id UUID NOT NULL,
 promoted_package_id UUID, disposition VARCHAR(16) NOT NULL, reason_codes JSONB NOT NULL,
 policy_version VARCHAR(64) NOT NULL, decided_by UUID NOT NULL, content_hash VARCHAR(64) NOT NULL,
 decided_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(proposal_id) REFERENCES record_learning_proposals(id),
 FOREIGN KEY(candidate_id) REFERENCES record_learning_candidate_versions(id),
 FOREIGN KEY(comparison_id) REFERENCES record_learning_offline_comparisons(id),
 FOREIGN KEY(assessment_id) REFERENCES record_learning_regression_assessments(id),
 FOREIGN KEY(baseline_package_id) REFERENCES record_global_strategy_packages(id),
 FOREIGN KEY(promoted_package_id) REFERENCES record_global_strategy_packages(id),
 FOREIGN KEY(decided_by) REFERENCES record_operators(id), UNIQUE(candidate_id),
 CHECK(disposition IN ('ACCEPTED','REJECTED') AND policy_version='STRATEGY_PROMOTION_V1'
  AND ((disposition='ACCEPTED')=(promoted_package_id IS NOT NULL))
  AND jsonb_typeof(reason_codes)='array' AND jsonb_array_length(reason_codes)>0
  AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_live_strategy_observations (
 id UUID PRIMARY KEY, execution_binding_id UUID NOT NULL, experiment_id UUID NOT NULL,
 package_id UUID NOT NULL, agent_version_id UUID NOT NULL, role VARCHAR(32) NOT NULL,
 input_bundle_id UUID NOT NULL UNIQUE, segment_kind VARCHAR(32) NOT NULL, segment_key VARCHAR(200) NOT NULL,
 segment_hash VARCHAR(64) NOT NULL, observed_from TIMESTAMPTZ NOT NULL, observed_to TIMESTAMPTZ NOT NULL,
 content_hash VARCHAR(64) NOT NULL, recorded_by UUID NOT NULL, recorded_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(execution_binding_id) REFERENCES record_strategy_execution_bindings(id),
 FOREIGN KEY(experiment_id,package_id) REFERENCES record_experiment_strategy_bindings(experiment_id,package_id),
 FOREIGN KEY(agent_version_id) REFERENCES record_strategy_agent_versions(id),
 FOREIGN KEY(input_bundle_id) REFERENCES record_learning_input_bundle_seals(bundle_id),
 FOREIGN KEY(recorded_by) REFERENCES record_operators(id),
 CHECK(segment_kind IN ('GLOBAL','OFFER','INDUSTRY','ORGANIZATION_TYPE','RECIPIENT_MODE')
  AND observed_from<=observed_to AND segment_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_live_strategy_metrics (
 observation_id UUID NOT NULL REFERENCES record_live_strategy_observations(id), category VARCHAR(16) NOT NULL,
 code VARCHAR(64) NOT NULL, value DOUBLE PRECISION NOT NULL, unit VARCHAR(32) NOT NULL,
 content_hash VARCHAR(64) NOT NULL, PRIMARY KEY(observation_id,category,code),
 CHECK(category IN ('COMMERCIAL','QUALITY','SAFETY','LATENCY','COST')
  AND value NOT IN ('Infinity'::float8,'-Infinity'::float8) AND value<>'NaN'::float8
  AND code ~ '^[A-Z][A-Z0-9_]{0,63}$' AND unit ~ '^[A-Z][A-Z0-9_]{0,31}$'
  AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_live_strategy_observation_seals (
 observation_id UUID PRIMARY KEY REFERENCES record_live_strategy_observations(id),
 metric_count INTEGER NOT NULL, metric_set_hash VARCHAR(64) NOT NULL, sealed_at TIMESTAMPTZ NOT NULL,
 CHECK(metric_count>=5 AND metric_set_hash ~ '^[0-9a-f]{64}$')
);

ALTER TABLE record_learning_regression_assessments ALTER COLUMN comparison_id DROP NOT NULL;
ALTER TABLE record_learning_regression_assessments ADD COLUMN subject_kind VARCHAR(16) NOT NULL DEFAULT 'OFFLINE';
ALTER TABLE record_learning_regression_assessments ADD COLUMN live_package_id UUID REFERENCES record_global_strategy_packages(id);
ALTER TABLE record_learning_regression_assessments ADD COLUMN confidence DOUBLE PRECISION;
ALTER TABLE record_learning_regression_assessments ADD COLUMN sample_size INTEGER;
ALTER TABLE record_learning_regression_assessments ADD COLUMN live_evaluator_version VARCHAR(100);
ALTER TABLE record_learning_regression_assessments ADD COLUMN live_evaluator_hash VARCHAR(64);
ALTER TABLE record_learning_regression_assessments ADD CONSTRAINT record_learning_assessment_subject_check CHECK(
 (subject_kind='OFFLINE' AND comparison_id IS NOT NULL AND live_package_id IS NULL AND confidence IS NULL
  AND sample_size IS NULL AND live_evaluator_version IS NULL AND live_evaluator_hash IS NULL)
 OR (subject_kind='LIVE' AND comparison_id IS NULL AND live_package_id IS NOT NULL AND confidence BETWEEN 0 AND 1
  AND confidence NOT IN ('Infinity'::float8,'-Infinity'::float8) AND confidence<>'NaN'::float8 AND sample_size>0
  AND length(btrim(live_evaluator_version)) BETWEEN 1 AND 100 AND live_evaluator_hash ~ '^[0-9a-f]{64}$'));
CREATE TABLE record_live_regression_observations (
 assessment_id UUID NOT NULL REFERENCES record_learning_regression_assessments(id),
 observation_id UUID NOT NULL REFERENCES record_live_strategy_observations(id),
 PRIMARY KEY(assessment_id,observation_id)
);
CREATE TABLE record_live_regression_assessment_seals (
 assessment_id UUID PRIMARY KEY REFERENCES record_learning_regression_assessments(id),
 observation_count INTEGER NOT NULL, observation_set_hash VARCHAR(64) NOT NULL, sealed_at TIMESTAMPTZ NOT NULL,
 CHECK(observation_count>0 AND observation_set_hash ~ '^[0-9a-f]{64}$')
);
ALTER TABLE record_learning_failure_analyses ALTER COLUMN comparison_id DROP NOT NULL;
ALTER TABLE record_learning_failure_analyses ADD COLUMN live_assessment_id UUID UNIQUE REFERENCES record_learning_regression_assessments(id);
ALTER TABLE record_negative_learning_records ALTER COLUMN proposal_id DROP NOT NULL;
ALTER TABLE record_negative_learning_records ADD COLUMN live_assessment_id UUID REFERENCES record_learning_regression_assessments(id);
ALTER TABLE record_negative_learning_records ADD COLUMN strategy_package_id UUID REFERENCES record_global_strategy_packages(id);
ALTER TABLE record_negative_learning_records ADD COLUMN promotion_decision_id UUID REFERENCES record_strategy_promotion_decisions(id);
ALTER TABLE record_negative_learning_records ADD COLUMN rollback_decision_id UUID;
ALTER TABLE record_negative_learning_records ADD CONSTRAINT record_negative_learning_subject_check CHECK(
 (proposal_id IS NOT NULL AND strategy_package_id IS NULL AND live_assessment_id IS NULL
     AND promotion_decision_id IS NULL AND rollback_decision_id IS NULL)
 OR (proposal_id IS NOT NULL AND comparison_id IS NOT NULL AND strategy_package_id IS NULL
     AND live_assessment_id IS NULL AND promotion_decision_id IS NOT NULL AND rollback_decision_id IS NULL)
 OR (proposal_id IS NULL AND live_assessment_id IS NOT NULL AND strategy_package_id IS NOT NULL
     AND promotion_decision_id IS NULL));

CREATE TABLE record_strategy_rollback_decisions (
 id UUID PRIMARY KEY, current_package_id UUID NOT NULL, target_package_id UUID NOT NULL,
 assessment_id UUID NOT NULL, forced BOOLEAN NOT NULL, policy_version VARCHAR(64) NOT NULL,
 decided_by UUID NOT NULL, reason_codes JSONB NOT NULL, content_hash VARCHAR(64) NOT NULL,
 decided_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(current_package_id) REFERENCES record_global_strategy_packages(id),
 FOREIGN KEY(target_package_id) REFERENCES record_global_strategy_packages(id),
 FOREIGN KEY(assessment_id) REFERENCES record_learning_regression_assessments(id),
 FOREIGN KEY(decided_by) REFERENCES record_operators(id),
 UNIQUE(current_package_id,assessment_id),
 CHECK(current_package_id<>target_package_id AND policy_version='HIGHEST_CONFIDENCE_ELIGIBLE_V1'
  AND jsonb_typeof(reason_codes)='array' AND jsonb_array_length(reason_codes)>0
  AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_strategy_rollback_candidates (
 rollback_id UUID NOT NULL REFERENCES record_strategy_rollback_decisions(id), package_id UUID NOT NULL,
 confidence DOUBLE PRECISION NOT NULL, eligible BOOLEAN NOT NULL, reason_codes JSONB NOT NULL,
 PRIMARY KEY(rollback_id,package_id), FOREIGN KEY(package_id) REFERENCES record_global_strategy_packages(id),
 CHECK(confidence BETWEEN 0 AND 1 AND confidence NOT IN ('Infinity'::float8,'-Infinity'::float8) AND confidence<>'NaN'::float8
  AND jsonb_typeof(reason_codes)='array' AND jsonb_array_length(reason_codes)>0)
);
CREATE TABLE record_strategy_rollback_seals (
 rollback_id UUID PRIMARY KEY REFERENCES record_strategy_rollback_decisions(id),
 candidate_count INTEGER NOT NULL, candidate_set_hash VARCHAR(64) NOT NULL, sealed_at TIMESTAMPTZ NOT NULL,
 CHECK(candidate_count>0 AND candidate_set_hash ~ '^[0-9a-f]{64}$')
);
ALTER TABLE record_negative_learning_records ADD CONSTRAINT record_negative_learning_rollback_fk
 FOREIGN KEY(rollback_decision_id) REFERENCES record_strategy_rollback_decisions(id);
ALTER TABLE record_learning_failure_analyses ADD COLUMN rollback_decision_id UUID UNIQUE
 REFERENCES record_strategy_rollback_decisions(id);
ALTER TABLE record_learning_failure_analyses ADD CONSTRAINT record_learning_failure_subject_check CHECK(
 (comparison_id IS NOT NULL AND live_assessment_id IS NULL AND rollback_decision_id IS NULL)
 OR (comparison_id IS NULL AND live_assessment_id IS NOT NULL AND rollback_decision_id IS NULL)
 OR (comparison_id IS NULL AND live_assessment_id IS NULL AND rollback_decision_id IS NOT NULL));

ALTER TABLE record_learning_review_controls ALTER COLUMN run_id DROP NOT NULL;
ALTER TABLE record_learning_review_controls DROP CONSTRAINT record_learning_review_controls_check;
ALTER TABLE record_learning_review_controls ADD COLUMN registry_scope BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE record_learning_review_controls ADD COLUMN package_id UUID REFERENCES record_global_strategy_packages(id);
ALTER TABLE record_learning_review_controls ADD COLUMN rollback_decision_id UUID REFERENCES record_strategy_rollback_decisions(id);
ALTER TABLE record_learning_review_controls ADD COLUMN reason_codes JSONB;
ALTER TABLE record_learning_review_controls ADD COLUMN event_ordinal BIGSERIAL UNIQUE;
ALTER TABLE record_learning_review_controls ADD COLUMN prior_event_id UUID REFERENCES record_learning_review_controls(id);
ALTER TABLE record_learning_review_controls ADD CONSTRAINT record_learning_review_controls_phase3b_check CHECK(
 content_hash ~ '^[0-9a-f]{64}$' AND (
  (NOT registry_scope AND run_id IS NOT NULL AND kind IN ('PAUSE_OFFLINE_REVIEW','PIN_BASELINE')
   AND ((kind='PIN_BASELINE')=(baseline_candidate_id IS NOT NULL)) AND package_id IS NULL AND rollback_decision_id IS NULL)
  OR
  (registry_scope AND kind IN ('BOOTSTRAP_PACKAGE','PROMOTE_PACKAGE','PAUSE','RESUME','PIN','UNPIN','ASSESSED_ROLLBACK','FORCED_ROLLBACK')
   AND reason_codes IS NOT NULL AND jsonb_typeof(reason_codes)='array' AND jsonb_array_length(reason_codes)>0
   AND ((kind IN ('BOOTSTRAP_PACKAGE','PROMOTE_PACKAGE','PIN','ASSESSED_ROLLBACK','FORCED_ROLLBACK'))=(package_id IS NOT NULL))
   AND ((kind IN ('ASSESSED_ROLLBACK','FORCED_ROLLBACK'))=(rollback_decision_id IS NOT NULL)))));

CREATE FUNCTION record_strategy_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable strategy record'; END $$;
CREATE FUNCTION record_learning_input_sealed_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF EXISTS(SELECT 1 FROM record_learning_input_bundle_seals WHERE bundle_id=NEW.bundle_id)
 THEN RAISE EXCEPTION 'learning input bundle is sealed'; END IF; RETURN NEW; END $$;
CREATE OR REPLACE FUNCTION record_learning_input_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b record_learning_input_bundles;
BEGIN
 SELECT * INTO b FROM record_learning_input_bundles WHERE id=NEW.bundle_id;
 IF b.id IS NULL THEN RAISE EXCEPTION 'missing learning input bundle'; END IF;
 IF TG_TABLE_NAME='record_learning_input_evidence' THEN
  IF NOT EXISTS(SELECT 1 FROM gov_evidence WHERE id=NEW.evidence_id AND call_id=NEW.call_id)
  THEN RAISE EXCEPTION 'learning evidence call mismatch'; END IF;
 END IF;
 IF TG_TABLE_NAME='record_learning_input_costs' THEN
  IF (NEW.kind='SETTLEMENT' AND NOT EXISTS(SELECT 1 FROM gov_settlements WHERE id=NEW.cost_id AND call_id=NEW.call_id))
    OR (NEW.kind='CASH_ENTRY' AND NOT EXISTS(SELECT 1 FROM gov_cash_entries WHERE id=NEW.cost_id AND call_id=NEW.call_id))
  THEN RAISE EXCEPTION 'learning cost kind or call mismatch'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_strategy_agent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior record_strategy_agent_versions;
BEGIN
 IF NEW.configuration::text ~* '"(authorization|compliance|commercial_policy|offer_acceptance|product_policy)"[[:space:]]*:'
 THEN RAISE EXCEPTION 'invalid strategy agent configuration'; END IF;
 IF NEW.supersedes_id IS NULL AND NEW.version<>1 THEN RAISE EXCEPTION 'strategy version requires predecessor'; END IF;
 IF NEW.supersedes_id IS NOT NULL THEN SELECT * INTO prior FROM record_strategy_agent_versions WHERE id=NEW.supersedes_id;
  IF prior.id IS NULL OR prior.logical_id<>NEW.logical_id OR prior.version+1<>NEW.version OR prior.role<>NEW.role THEN RAISE EXCEPTION 'invalid strategy predecessor'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_strategy_package_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior record_global_strategy_packages;
BEGIN
 IF NEW.supersedes_id IS NULL AND EXISTS(SELECT 1 FROM record_global_strategy_packages)
 THEN RAISE EXCEPTION 'global strategy package already bootstrapped'; END IF;
 IF NEW.supersedes_id IS NULL AND NEW.version<>1 THEN RAISE EXCEPTION 'package version requires predecessor'; END IF;
 IF NEW.supersedes_id IS NOT NULL THEN SELECT * INTO prior FROM record_global_strategy_packages WHERE id=NEW.supersedes_id;
  IF prior.id IS NULL OR prior.logical_id<>NEW.logical_id OR prior.version+1<>NEW.version THEN RAISE EXCEPTION 'invalid package predecessor'; END IF;
 END IF; RETURN NEW;
END $$;
CREATE FUNCTION record_strategy_package_seal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (SELECT count(*) FROM record_strategy_package_members WHERE package_id=NEW.package_id)<>4
  OR (SELECT array_agg(role ORDER BY role) FROM record_strategy_package_members WHERE package_id=NEW.package_id)
     <> ARRAY['DISCOVERY','OUTREACH','QUALIFICATION','REPLY']::varchar[]
 THEN RAISE EXCEPTION 'strategy package is incomplete'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_strategy_member_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF EXISTS(SELECT 1 FROM record_strategy_package_seals WHERE package_id=NEW.package_id)
 THEN RAISE EXCEPTION 'strategy package is sealed'; END IF; RETURN NEW; END $$;
CREATE FUNCTION record_strategy_execution_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cfg gov_configs; strategy_version record_strategy_agent_versions;
BEGIN
 SELECT * INTO cfg FROM gov_configs c WHERE c.id=NEW.model_config_id AND c.workflow_id=NEW.model_config_workflow_id AND c.version=NEW.model_config_version;
 SELECT * INTO strategy_version FROM record_strategy_agent_versions WHERE id=NEW.agent_version_id;
 IF NOT EXISTS(SELECT 1 FROM record_strategy_package_members m
   WHERE m.package_id=NEW.package_id AND m.role=NEW.role AND m.agent_version_id=NEW.agent_version_id AND m.configuration_hash=NEW.configuration_hash)
  OR NOT EXISTS(SELECT 1 FROM gov_operations o WHERE o.id=NEW.operation_id AND o.workflow_id=NEW.workflow_id
   AND o.experiment_id=NEW.experiment_id AND o.agent_id=NEW.agent_id AND o.config_version=NEW.model_config_version)
  OR EXISTS(SELECT 1 FROM gov_calls c WHERE c.operation_id=NEW.operation_id)
  OR cfg.id IS NULL OR cfg.capability<>'OPENAI_GENERATE' OR cfg.data->>'model_identifier' IS DISTINCT FROM strategy_version.model_identifier
 THEN RAISE EXCEPTION 'strategy execution lineage mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_strategy_promotion_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_learning_regression_assessments; c record_learning_offline_comparisons;
BEGIN
 SELECT * INTO a FROM record_learning_regression_assessments WHERE id=NEW.assessment_id;
 SELECT * INTO c FROM record_learning_offline_comparisons WHERE id=NEW.comparison_id;
 IF (SELECT kind='PAUSE' FROM record_learning_review_controls
     WHERE registry_scope AND kind IN ('PAUSE','RESUME') ORDER BY event_ordinal DESC LIMIT 1)
  OR a.id IS NULL OR a.subject_kind<>'OFFLINE' OR a.comparison_id<>c.id OR a.disposition<>'PASS'
  OR c.proposal_id<>NEW.proposal_id OR c.candidate_id<>NEW.candidate_id
  OR NOT EXISTS(SELECT 1 FROM record_strategy_package_seals WHERE package_id=NEW.baseline_package_id)
  OR (NEW.disposition='ACCEPTED' AND NOT EXISTS(SELECT 1 FROM record_strategy_package_seals WHERE package_id=NEW.promoted_package_id))
  OR (NEW.disposition='ACCEPTED' AND NOT EXISTS(
    SELECT 1 FROM record_global_strategy_packages p WHERE p.id=NEW.promoted_package_id
      AND p.supersedes_id=NEW.baseline_package_id))
  OR (NEW.disposition='ACCEPTED' AND (SELECT count(*) FROM record_strategy_agent_versions
      WHERE origin_candidate_id=NEW.candidate_id)<>1)
  OR (NEW.disposition='ACCEPTED' AND EXISTS(
    SELECT 1 FROM record_strategy_package_members pm
    JOIN record_strategy_agent_versions av ON av.id=pm.agent_version_id
    WHERE pm.package_id=NEW.promoted_package_id AND av.origin_candidate_id IS NOT NULL
      AND av.origin_candidate_id<>NEW.candidate_id))
  OR (NEW.disposition='ACCEPTED' AND EXISTS(
    SELECT 1 FROM record_strategy_package_members pm
    JOIN record_strategy_agent_versions av ON av.id=pm.agent_version_id
    LEFT JOIN record_strategy_package_members bm ON bm.package_id=NEW.baseline_package_id
      AND bm.role=pm.role AND bm.agent_version_id=av.supersedes_id
    WHERE pm.package_id=NEW.promoted_package_id AND bm.package_id IS NULL))
  OR (NEW.disposition='ACCEPTED' AND EXISTS(
    SELECT 1 FROM record_strategy_package_members pm
    JOIN record_strategy_agent_versions av ON av.id=pm.agent_version_id
    JOIN record_strategy_agent_versions prior ON prior.id=av.supersedes_id
    WHERE pm.package_id=NEW.promoted_package_id AND (
      ROW(av.prompt_artifact_id,av.prompt_kind,av.prompt_version,av.prompt_hash,
          av.few_shot_artifact_id,av.few_shot_kind,av.few_shot_version,av.few_shot_hash,
          av.model_identifier,av.reasoning_effort,av.budget_policy_version,
          av.max_tool_calls,av.max_searches,av.max_pages)
      IS DISTINCT FROM
      ROW(prior.prompt_artifact_id,prior.prompt_kind,prior.prompt_version,prior.prompt_hash,
          prior.few_shot_artifact_id,prior.few_shot_kind,prior.few_shot_version,prior.few_shot_hash,
          prior.model_identifier,prior.reasoning_effort,prior.budget_policy_version,
          prior.max_tool_calls,prior.max_searches,prior.max_pages)
      OR (av.origin_candidate_id IS NULL AND av.configuration_hash<>prior.configuration_hash))))
  OR (NEW.disposition='ACCEPTED' AND NOT EXISTS(
    SELECT 1 FROM record_strategy_agent_versions av
    JOIN record_learning_candidate_versions candidate ON candidate.id=av.origin_candidate_id
    JOIN record_strategy_agent_versions prior ON prior.id=av.supersedes_id
    WHERE av.origin_candidate_id=NEW.candidate_id
      AND (av.configuration-'schema_version')=candidate.candidate_configuration
      AND ROW(prior.prompt_artifact_id,prior.prompt_kind,prior.prompt_version,prior.prompt_hash)
          =ROW(candidate.baseline_artifact_id,candidate.baseline_artifact_kind,
               candidate.baseline_artifact_version,candidate.baseline_artifact_hash)))
 THEN RAISE EXCEPTION 'promotion evidence mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_experiment_strategy_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE paused BOOLEAN; pinned UUID; selected UUID;
BEGIN
 SELECT kind='PAUSE' INTO paused FROM record_learning_review_controls
  WHERE registry_scope AND kind IN ('PAUSE','RESUME') ORDER BY event_ordinal DESC LIMIT 1;
 SELECT CASE WHEN kind='PIN' THEN package_id END INTO pinned FROM record_learning_review_controls
  WHERE registry_scope AND kind IN ('PIN','UNPIN') ORDER BY event_ordinal DESC LIMIT 1;
 SELECT package_id INTO selected FROM record_learning_review_controls
  WHERE registry_scope AND kind IN ('BOOTSTRAP_PACKAGE','PROMOTE_PACKAGE','ASSESSED_ROLLBACK','FORCED_ROLLBACK')
  ORDER BY event_ordinal DESC LIMIT 1;
 IF coalesce(paused,false) OR NEW.package_id<>coalesce(pinned,selected)
  OR EXISTS(SELECT 1 FROM gov_calls WHERE experiment_id=NEW.experiment_id)
 THEN RAISE EXCEPTION 'experiment strategy selection is not currently authorized'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_live_observation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b record_strategy_execution_bindings;
BEGIN
 SELECT * INTO b FROM record_strategy_execution_bindings WHERE id=NEW.execution_binding_id;
 IF b.id IS NULL OR ROW(NEW.experiment_id,NEW.package_id,NEW.agent_version_id,NEW.role)
   IS DISTINCT FROM ROW(b.experiment_id,b.package_id,b.agent_version_id,b.role)
  OR NOT EXISTS(SELECT 1 FROM record_learning_input_bundles i JOIN record_learning_input_bundle_seals s ON s.bundle_id=i.id
    WHERE i.id=NEW.input_bundle_id AND i.experiment_id=NEW.experiment_id)
  OR NOT EXISTS(SELECT 1 FROM record_learning_input_usage WHERE bundle_id=NEW.input_bundle_id)
  OR NOT EXISTS(SELECT 1 FROM record_learning_input_costs WHERE bundle_id=NEW.input_bundle_id)
  OR EXISTS(SELECT 1 FROM record_learning_input_evidence i JOIN gov_calls c ON c.id=i.call_id
    WHERE i.bundle_id=NEW.input_bundle_id
      AND ROW(c.experiment_id,c.workflow_id,c.operation_id) IS DISTINCT FROM ROW(b.experiment_id,b.workflow_id,b.operation_id))
  OR EXISTS(SELECT 1 FROM record_learning_input_call_snapshots i JOIN gov_calls c ON c.id=i.call_id
    WHERE i.bundle_id=NEW.input_bundle_id
      AND ROW(c.experiment_id,c.workflow_id,c.operation_id) IS DISTINCT FROM ROW(b.experiment_id,b.workflow_id,b.operation_id))
  OR EXISTS(SELECT 1 FROM record_learning_input_usage i JOIN gov_calls c ON c.id=i.call_id
    WHERE i.bundle_id=NEW.input_bundle_id
      AND ROW(c.experiment_id,c.workflow_id,c.operation_id) IS DISTINCT FROM ROW(b.experiment_id,b.workflow_id,b.operation_id))
  OR EXISTS(SELECT 1 FROM record_learning_input_costs i JOIN gov_calls c ON c.id=i.call_id
    WHERE i.bundle_id=NEW.input_bundle_id
      AND ROW(c.experiment_id,c.workflow_id,c.operation_id) IS DISTINCT FROM ROW(b.experiment_id,b.workflow_id,b.operation_id))
 THEN RAISE EXCEPTION 'live observation lineage mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_live_metric_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF EXISTS(SELECT 1 FROM record_live_strategy_observation_seals WHERE observation_id=NEW.observation_id)
 THEN RAISE EXCEPTION 'live observation is sealed'; END IF; RETURN NEW; END $$;
CREATE FUNCTION record_live_observation_seal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (SELECT count(DISTINCT category) FROM record_live_strategy_metrics WHERE observation_id=NEW.observation_id)<>5
 THEN RAISE EXCEPTION 'live observation metrics incomplete'; END IF; RETURN NEW;
END $$;
CREATE FUNCTION record_live_assessment_observation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_learning_regression_assessments; o record_live_strategy_observations;
BEGIN
 IF EXISTS(SELECT 1 FROM record_live_regression_assessment_seals WHERE assessment_id=NEW.assessment_id)
 THEN RAISE EXCEPTION 'live assessment is sealed'; END IF;
 SELECT * INTO a FROM record_learning_regression_assessments WHERE id=NEW.assessment_id;
 SELECT * INTO o FROM record_live_strategy_observations WHERE id=NEW.observation_id;
 IF a.subject_kind<>'LIVE' OR o.package_id<>a.live_package_id THEN RAISE EXCEPTION 'live assessment observation mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_live_assessment_seal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF (SELECT count(*) FROM record_live_regression_observations WHERE assessment_id=NEW.assessment_id)<>NEW.observation_count
 THEN RAISE EXCEPTION 'live assessment observation set mismatch'; END IF; RETURN NEW; END $$;
CREATE OR REPLACE FUNCTION record_learning_assessment_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_learning_regression_assessments; f integer; n integer;
BEGIN
 SELECT * INTO a FROM record_learning_regression_assessments WHERE id=NEW.id;
 IF a.subject_kind='OFFLINE' THEN
  SELECT count(*) INTO f FROM record_learning_failure_analyses WHERE comparison_id=a.comparison_id;
  SELECT count(*) INTO n FROM record_negative_learning_records WHERE comparison_id=a.comparison_id;
 ELSE
  IF NOT EXISTS(SELECT 1 FROM record_live_regression_assessment_seals WHERE assessment_id=a.id) THEN RAISE EXCEPTION 'live assessment must be sealed'; END IF;
  SELECT count(*) INTO f FROM record_learning_failure_analyses WHERE live_assessment_id=a.id;
  SELECT count(*) INTO n FROM record_negative_learning_records WHERE live_assessment_id=a.id;
 END IF;
 IF a.disposition IN ('FAIL','INCONCLUSIVE','REJECTED') AND (f<>1 OR n<1) THEN RAISE EXCEPTION 'negative learning evaluation requires retained analysis'; END IF;
 IF a.disposition='PASS' AND (f<>0 OR n<>0) THEN RAISE EXCEPTION 'successful evaluation cannot retain negative result'; END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION record_learning_negative_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_learning_regression_assessments;
BEGIN
 IF TG_TABLE_NAME='record_learning_failure_analyses' AND NEW.rollback_decision_id IS NOT NULL THEN
  RETURN NEW;
 ELSIF TG_TABLE_NAME='record_learning_failure_analyses' AND NEW.live_assessment_id IS NOT NULL THEN
  SELECT * INTO a FROM record_learning_regression_assessments WHERE id=NEW.live_assessment_id;
 ELSIF TG_TABLE_NAME='record_negative_learning_records' AND NEW.live_assessment_id IS NOT NULL THEN
  SELECT * INTO a FROM record_learning_regression_assessments WHERE id=NEW.live_assessment_id;
 ELSE RETURN NEW; END IF;
 IF a.disposition='PASS' THEN
  IF TG_TABLE_NAME='record_learning_failure_analyses' THEN
   RAISE EXCEPTION 'successful assessment cannot gain negative lineage';
  ELSIF NEW.rollback_decision_id IS NULL THEN
   RAISE EXCEPTION 'successful assessment cannot gain negative lineage';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_strategy_rollback_candidate_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF EXISTS(SELECT 1 FROM record_strategy_rollback_seals WHERE rollback_id=NEW.rollback_id)
 THEN RAISE EXCEPTION 'rollback candidate set is sealed'; END IF; RETURN NEW; END $$;
CREATE FUNCTION record_strategy_rollback_seal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r record_strategy_rollback_decisions; current record_global_strategy_packages; expected UUID;
BEGIN
 SELECT * INTO r FROM record_strategy_rollback_decisions WHERE id=NEW.rollback_id;
 SELECT * INTO current FROM record_global_strategy_packages WHERE id=r.current_package_id;
 SELECT package_id INTO expected FROM record_strategy_rollback_candidates WHERE rollback_id=NEW.rollback_id AND eligible
  ORDER BY confidence DESC,package_id ASC LIMIT 1;
 IF expected IS NULL OR expected<>r.target_package_id
  OR (SELECT count(*) FROM record_strategy_rollback_candidates WHERE rollback_id=NEW.rollback_id)<>NEW.candidate_count
  OR EXISTS(SELECT 1 FROM record_strategy_rollback_candidates c
    JOIN record_global_strategy_packages p ON p.id=c.package_id
    WHERE c.rollback_id=NEW.rollback_id AND c.eligible
      AND (p.logical_id<>current.logical_id OR p.version>=current.version OR p.created_at>current.created_at
        OR EXISTS(SELECT 1 FROM record_strategy_rollback_decisions prior WHERE prior.current_package_id=p.id)))
 THEN RAISE EXCEPTION 'rollback target is not highest confidence eligible package'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_strategy_rollback_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_learning_regression_assessments;
BEGIN
 SELECT * INTO a FROM record_learning_regression_assessments WHERE id=NEW.assessment_id;
 IF a.id IS NULL OR a.subject_kind<>'LIVE' OR a.live_package_id<>NEW.current_package_id
  OR (NOT NEW.forced AND NOT a.rollback_satisfied)
  OR NOT EXISTS(SELECT 1 FROM record_strategy_package_seals WHERE package_id=NEW.target_package_id)
 THEN RAISE EXCEPTION 'rollback evidence mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_strategy_control_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior UUID; paused BOOLEAN; pinned UUID;
BEGIN
 IF NOT NEW.registry_scope THEN RETURN NEW; END IF;
 PERFORM 1 FROM record_strategy_registry WHERE id=1 FOR UPDATE;
 SELECT id INTO prior FROM record_learning_review_controls WHERE registry_scope ORDER BY event_ordinal DESC LIMIT 1;
 IF prior IS DISTINCT FROM NEW.prior_event_id THEN RAISE EXCEPTION 'strategy registry event conflict'; END IF;
 IF NEW.package_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM record_strategy_package_seals WHERE package_id=NEW.package_id)
 THEN RAISE EXCEPTION 'strategy control package is not sealed'; END IF;
 SELECT kind='PAUSE' INTO paused FROM record_learning_review_controls
  WHERE registry_scope AND kind IN ('PAUSE','RESUME') ORDER BY event_ordinal DESC LIMIT 1;
 SELECT CASE WHEN kind='PIN' THEN package_id END INTO pinned FROM record_learning_review_controls
  WHERE registry_scope AND kind IN ('PIN','UNPIN') ORDER BY event_ordinal DESC LIMIT 1;
 IF (NEW.kind='PAUSE' AND coalesce(paused,false))
  OR (NEW.kind='RESUME' AND NOT coalesce(paused,false))
  OR (NEW.kind='UNPIN' AND pinned IS NULL)
 THEN RAISE EXCEPTION 'invalid strategy control transition'; END IF;
 RETURN NEW;
END $$;

DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY[
 'record_learning_input_artifacts','record_learning_input_evidence','record_learning_input_call_snapshots','record_learning_input_usage','record_learning_input_costs'
] LOOP EXECUTE format('CREATE TRIGGER record_learning_%s_sealed BEFORE INSERT ON %I FOR EACH ROW EXECUTE FUNCTION record_learning_input_sealed_guard()',replace(t,'record_learning_',''),t); END LOOP; END $$;
CREATE TRIGGER record_strategy_agent_lineage BEFORE INSERT ON record_strategy_agent_versions FOR EACH ROW EXECUTE FUNCTION record_strategy_agent_guard();
CREATE TRIGGER record_strategy_package_lineage BEFORE INSERT ON record_global_strategy_packages FOR EACH ROW EXECUTE FUNCTION record_strategy_package_guard();
CREATE TRIGGER record_strategy_package_seal BEFORE INSERT ON record_strategy_package_seals FOR EACH ROW EXECUTE FUNCTION record_strategy_package_seal_guard();
CREATE TRIGGER record_strategy_member_sealed BEFORE INSERT ON record_strategy_package_members FOR EACH ROW EXECUTE FUNCTION record_strategy_member_guard();
CREATE TRIGGER record_experiment_strategy_selection BEFORE INSERT ON record_experiment_strategy_bindings FOR EACH ROW EXECUTE FUNCTION record_experiment_strategy_guard();
CREATE TRIGGER record_strategy_execution_lineage BEFORE INSERT ON record_strategy_execution_bindings FOR EACH ROW EXECUTE FUNCTION record_strategy_execution_guard();
CREATE TRIGGER record_strategy_promotion_lineage BEFORE INSERT ON record_strategy_promotion_decisions FOR EACH ROW EXECUTE FUNCTION record_strategy_promotion_guard();
CREATE TRIGGER record_live_observation_lineage BEFORE INSERT ON record_live_strategy_observations FOR EACH ROW EXECUTE FUNCTION record_live_observation_guard();
CREATE TRIGGER record_live_metric_unsealed BEFORE INSERT ON record_live_strategy_metrics FOR EACH ROW EXECUTE FUNCTION record_live_metric_guard();
CREATE TRIGGER record_live_observation_seal_complete BEFORE INSERT ON record_live_strategy_observation_seals FOR EACH ROW EXECUTE FUNCTION record_live_observation_seal_guard();
CREATE TRIGGER record_live_assessment_observation_lineage BEFORE INSERT ON record_live_regression_observations FOR EACH ROW EXECUTE FUNCTION record_live_assessment_observation_guard();
CREATE TRIGGER record_live_assessment_seal_complete BEFORE INSERT ON record_live_regression_assessment_seals FOR EACH ROW EXECUTE FUNCTION record_live_assessment_seal_guard();
CREATE TRIGGER record_learning_failure_live_guard BEFORE INSERT ON record_learning_failure_analyses FOR EACH ROW EXECUTE FUNCTION record_learning_negative_guard();
CREATE TRIGGER record_learning_negative_live_guard BEFORE INSERT ON record_negative_learning_records FOR EACH ROW EXECUTE FUNCTION record_learning_negative_guard();
CREATE TRIGGER record_strategy_rollback_candidate_unsealed BEFORE INSERT ON record_strategy_rollback_candidates FOR EACH ROW EXECUTE FUNCTION record_strategy_rollback_candidate_guard();
CREATE TRIGGER record_strategy_rollback_lineage BEFORE INSERT ON record_strategy_rollback_decisions FOR EACH ROW EXECUTE FUNCTION record_strategy_rollback_guard();
CREATE TRIGGER record_strategy_rollback_seal_complete BEFORE INSERT ON record_strategy_rollback_seals FOR EACH ROW EXECUTE FUNCTION record_strategy_rollback_seal_guard();
CREATE TRIGGER record_strategy_registry_event BEFORE INSERT ON record_learning_review_controls FOR EACH ROW EXECUTE FUNCTION record_strategy_control_guard();
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY[
 'record_learning_input_bundle_seals','record_strategy_agent_versions','record_global_strategy_packages',
 'record_strategy_package_members','record_strategy_package_seals','record_experiment_strategy_bindings','record_strategy_execution_bindings',
 'record_strategy_promotion_decisions','record_live_strategy_observations','record_live_strategy_metrics','record_live_strategy_observation_seals',
 'record_live_regression_observations','record_live_regression_assessment_seals','record_strategy_rollback_decisions',
 'record_strategy_rollback_candidates','record_strategy_rollback_seals'
] LOOP EXECUTE format('CREATE TRIGGER %s_immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION record_strategy_immutable()',t,t); END LOOP; END $$;
""")


def downgrade() -> None:
    op.execute("""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM record_global_strategy_packages)
  OR EXISTS(SELECT 1 FROM record_live_strategy_observations)
  OR EXISTS(SELECT 1 FROM record_strategy_promotion_decisions)
 OR EXISTS(SELECT 1 FROM record_strategy_rollback_decisions)
  OR EXISTS(SELECT 1 FROM record_learning_review_controls WHERE registry_scope)
 THEN RAISE EXCEPTION 'cannot downgrade strategy learning with retained Phase 3B history'; END IF;
END $$;
DROP TRIGGER record_strategy_registry_event ON record_learning_review_controls;
DELETE FROM record_learning_review_controls WHERE registry_scope;
ALTER TABLE record_learning_review_controls DROP CONSTRAINT record_learning_review_controls_phase3b_check;
ALTER TABLE record_learning_review_controls DROP COLUMN prior_event_id;
ALTER TABLE record_learning_review_controls DROP COLUMN event_ordinal;
ALTER TABLE record_learning_review_controls DROP COLUMN reason_codes;
ALTER TABLE record_learning_review_controls DROP COLUMN rollback_decision_id;
ALTER TABLE record_learning_review_controls DROP COLUMN package_id;
ALTER TABLE record_learning_review_controls DROP COLUMN registry_scope;
ALTER TABLE record_learning_review_controls ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE record_learning_review_controls ADD CONSTRAINT record_learning_review_controls_check CHECK(
 kind IN ('PAUSE_OFFLINE_REVIEW','PIN_BASELINE')
 AND ((kind='PIN_BASELINE')=(baseline_candidate_id IS NOT NULL))
 AND content_hash ~ '^[0-9a-f]{64}$');

DROP TRIGGER record_learning_negative_live_guard ON record_negative_learning_records;
ALTER TABLE record_negative_learning_records DROP CONSTRAINT record_negative_learning_subject_check;
ALTER TABLE record_negative_learning_records DROP CONSTRAINT record_negative_learning_rollback_fk;
ALTER TABLE record_negative_learning_records DROP COLUMN rollback_decision_id;
ALTER TABLE record_negative_learning_records DROP COLUMN promotion_decision_id;
ALTER TABLE record_negative_learning_records DROP COLUMN strategy_package_id;
ALTER TABLE record_negative_learning_records DROP COLUMN live_assessment_id;
ALTER TABLE record_negative_learning_records ALTER COLUMN proposal_id SET NOT NULL;
DROP TRIGGER record_learning_failure_live_guard ON record_learning_failure_analyses;
ALTER TABLE record_learning_failure_analyses DROP CONSTRAINT record_learning_failure_subject_check;
ALTER TABLE record_learning_failure_analyses DROP COLUMN rollback_decision_id;
ALTER TABLE record_learning_failure_analyses DROP COLUMN live_assessment_id;
ALTER TABLE record_learning_failure_analyses ALTER COLUMN comparison_id SET NOT NULL;

DROP TABLE record_strategy_rollback_seals;
DROP TABLE record_strategy_rollback_candidates;
DROP TABLE record_strategy_rollback_decisions;
DROP TABLE record_live_regression_assessment_seals;
DROP TABLE record_live_regression_observations;
ALTER TABLE record_learning_regression_assessments DROP CONSTRAINT record_learning_assessment_subject_check;
ALTER TABLE record_learning_regression_assessments DROP COLUMN sample_size;
ALTER TABLE record_learning_regression_assessments DROP COLUMN confidence;
ALTER TABLE record_learning_regression_assessments DROP COLUMN live_package_id;
ALTER TABLE record_learning_regression_assessments DROP COLUMN live_evaluator_hash;
ALTER TABLE record_learning_regression_assessments DROP COLUMN live_evaluator_version;
ALTER TABLE record_learning_regression_assessments DROP COLUMN subject_kind;
ALTER TABLE record_learning_regression_assessments ALTER COLUMN comparison_id SET NOT NULL;
DROP TABLE record_live_strategy_observation_seals;
DROP TABLE record_live_strategy_metrics;
DROP TABLE record_live_strategy_observations;
DROP TABLE record_strategy_promotion_decisions;

DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY[
 'record_learning_input_artifacts','record_learning_input_evidence','record_learning_input_call_snapshots','record_learning_input_usage','record_learning_input_costs'
] LOOP EXECUTE format('DROP TRIGGER record_learning_%s_sealed ON %I',replace(t,'record_learning_',''),t); END LOOP; END $$;
DROP TABLE record_strategy_execution_bindings;
DROP TABLE record_experiment_strategy_bindings;
DROP TABLE record_strategy_package_seals;
DROP TABLE record_strategy_package_members;
DROP TABLE record_global_strategy_packages;
DROP TABLE record_strategy_agent_versions;
DROP TABLE record_strategy_registry;
DROP TABLE record_learning_input_bundle_seals;
DROP FUNCTION record_strategy_control_guard();
DROP FUNCTION record_strategy_rollback_seal_guard();
DROP FUNCTION record_strategy_rollback_candidate_guard();
DROP FUNCTION record_strategy_rollback_guard();
DROP FUNCTION record_learning_negative_guard();
DROP FUNCTION record_live_assessment_seal_guard();
DROP FUNCTION record_live_assessment_observation_guard();
DROP FUNCTION record_live_observation_seal_guard();
DROP FUNCTION record_live_metric_guard();
DROP FUNCTION record_live_observation_guard();
DROP FUNCTION record_strategy_promotion_guard();
DROP FUNCTION record_experiment_strategy_guard();
DROP FUNCTION record_strategy_execution_guard();
DROP FUNCTION record_strategy_member_guard();
DROP FUNCTION record_strategy_package_seal_guard();
DROP FUNCTION record_strategy_package_guard();
DROP FUNCTION record_strategy_agent_guard();
DROP FUNCTION record_learning_input_sealed_guard();
DROP FUNCTION record_strategy_immutable();

CREATE OR REPLACE FUNCTION record_learning_input_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b record_learning_input_bundles;
BEGIN
 SELECT * INTO b FROM record_learning_input_bundles WHERE id=NEW.bundle_id;
 IF b.id IS NULL THEN RAISE EXCEPTION 'missing learning input bundle'; END IF;
 IF TG_TABLE_NAME='record_learning_input_evidence' AND NOT EXISTS(SELECT 1 FROM gov_evidence WHERE id=NEW.evidence_id AND call_id=NEW.call_id) THEN RAISE EXCEPTION 'learning evidence call mismatch'; END IF;
 IF TG_TABLE_NAME='record_learning_input_costs' AND NOT EXISTS(SELECT 1 FROM gov_settlements WHERE id=NEW.cost_id AND call_id=NEW.call_id) AND NOT EXISTS(SELECT 1 FROM gov_cash_entries WHERE id=NEW.cost_id AND call_id=NEW.call_id) THEN RAISE EXCEPTION 'learning cost call mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_learning_assessment_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_learning_regression_assessments; f integer; n integer;
BEGIN
 SELECT * INTO a FROM record_learning_regression_assessments WHERE id=NEW.id;
 SELECT count(*) INTO f FROM record_learning_failure_analyses WHERE comparison_id=a.comparison_id;
 SELECT count(*) INTO n FROM record_negative_learning_records WHERE comparison_id=a.comparison_id;
 IF a.disposition IN ('FAIL','INCONCLUSIVE','REJECTED') AND (f<>1 OR n<1) THEN RAISE EXCEPTION 'negative learning evaluation requires retained analysis'; END IF;
 IF a.disposition='PASS' AND (f<>0 OR n<>0) THEN RAISE EXCEPTION 'successful evaluation cannot retain negative result'; END IF;
 RETURN NULL;
END $$;
""")
