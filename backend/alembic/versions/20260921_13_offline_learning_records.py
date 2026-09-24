"""immutable offline learning proposal and evaluation records

Revision ID: 20260921_13
Revises: 20260920_12
"""

from alembic import op

revision = "20260921_13"
down_revision = "20260920_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE record_learning_runs (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, workflow_id UUID NOT NULL, agent_id UUID NOT NULL,
 agent_version_hash VARCHAR(64) NOT NULL, evaluator_version VARCHAR(100) NOT NULL, evaluator_hash VARCHAR(64) NOT NULL,
 content_hash VARCHAR(64) NOT NULL, created_by UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(experiment_id) REFERENCES record_experiments(id),
 FOREIGN KEY(workflow_id,experiment_id) REFERENCES record_workflows(id,experiment_id),
 FOREIGN KEY(agent_id,workflow_id) REFERENCES record_agents(id,workflow_id),
 FOREIGN KEY(created_by) REFERENCES record_operators(id),
 CHECK(agent_version_hash ~ '^[0-9a-f]{64}$' AND evaluator_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_input_bundles (
 id UUID PRIMARY KEY, run_id UUID NOT NULL UNIQUE, experiment_id UUID NOT NULL,
 content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(run_id) REFERENCES record_learning_runs(id),
 FOREIGN KEY(experiment_id) REFERENCES record_experiments(id),
 CHECK(content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_input_artifacts (
 bundle_id UUID NOT NULL, role VARCHAR(64) NOT NULL, artifact_id UUID NOT NULL, experiment_id UUID NOT NULL,
 artifact_kind VARCHAR(64) NOT NULL, artifact_version INTEGER NOT NULL, artifact_hash VARCHAR(64) NOT NULL,
 PRIMARY KEY(bundle_id,role), FOREIGN KEY(bundle_id) REFERENCES record_learning_input_bundles(id),
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash)
   REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 CHECK(role ~ '^[A-Z][A-Z0-9_]{0,63}$' AND artifact_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_input_evidence (
 bundle_id UUID NOT NULL, role VARCHAR(64) NOT NULL, evidence_id UUID NOT NULL, call_id UUID NOT NULL,
 PRIMARY KEY(bundle_id,role), FOREIGN KEY(bundle_id) REFERENCES record_learning_input_bundles(id),
 FOREIGN KEY(evidence_id) REFERENCES gov_evidence(id), FOREIGN KEY(call_id) REFERENCES gov_calls(id),
 CHECK(role ~ '^[A-Z][A-Z0-9_]{0,63}$')
);
CREATE TABLE record_learning_input_call_snapshots (
 bundle_id UUID NOT NULL, role VARCHAR(64) NOT NULL, call_id UUID NOT NULL, snapshot JSONB NOT NULL,
 snapshot_hash VARCHAR(64) NOT NULL, PRIMARY KEY(bundle_id,role), FOREIGN KEY(bundle_id) REFERENCES record_learning_input_bundles(id),
 FOREIGN KEY(call_id) REFERENCES gov_calls(id), CHECK(role ~ '^[A-Z][A-Z0-9_]{0,63}$' AND snapshot_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_input_usage (
 bundle_id UUID NOT NULL, role VARCHAR(64) NOT NULL, usage_id UUID NOT NULL, call_id UUID NOT NULL, component VARCHAR NOT NULL,
 PRIMARY KEY(bundle_id,role), FOREIGN KEY(bundle_id) REFERENCES record_learning_input_bundles(id),
 FOREIGN KEY(usage_id,call_id,component) REFERENCES gov_usage(id,call_id,component), CHECK(role ~ '^[A-Z][A-Z0-9_]{0,63}$')
);
CREATE TABLE record_learning_input_costs (
 bundle_id UUID NOT NULL, role VARCHAR(64) NOT NULL, cost_id UUID NOT NULL, call_id UUID NOT NULL, kind VARCHAR(16) NOT NULL,
 PRIMARY KEY(bundle_id,role), FOREIGN KEY(bundle_id) REFERENCES record_learning_input_bundles(id),
 FOREIGN KEY(call_id) REFERENCES gov_calls(id), CHECK(role ~ '^[A-Z][A-Z0-9_]{0,63}$' AND kind IN ('SETTLEMENT','CASH_ENTRY'))
);
CREATE TABLE record_learning_scopes (
 id UUID PRIMARY KEY, run_id UUID NOT NULL UNIQUE, target_subsystem VARCHAR(64) NOT NULL, protected_components JSONB NOT NULL,
 content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL, FOREIGN KEY(run_id) REFERENCES record_learning_runs(id),
 CHECK(target_subsystem IN ('PROMPT_CONFIGURATION','MODEL_CONFIGURATION','DISCOVERY_STRATEGY','QUALIFICATION_STRATEGY','OUTREACH_STRATEGY','REPLY_STRATEGY','PRODUCT_REVIEW','ENGINEERING_REVIEW')
   AND protected_components='["AUTHORIZATION","COMPLIANCE","COMMERCIAL_POLICY","OFFER_ACCEPTANCE","PRODUCT_POLICY"]'::jsonb
   AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_proposals (
 id UUID PRIMARY KEY, logical_id UUID NOT NULL, version INTEGER NOT NULL, supersedes_id UUID, run_id UUID NOT NULL,
 input_bundle_id UUID NOT NULL, scope_id UUID NOT NULL, class VARCHAR(40) NOT NULL, bottleneck VARCHAR(4000) NOT NULL,
 expected_effect JSONB NOT NULL, target_metrics JSONB NOT NULL, protected_metrics JSONB NOT NULL, confidence DOUBLE PRECISION NOT NULL,
 sample_size INTEGER NOT NULL, confounders JSONB NOT NULL, evaluation_criteria JSONB NOT NULL, rollback_criteria JSONB NOT NULL,
 content_hash VARCHAR(64) NOT NULL, proposed_by UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(supersedes_id) REFERENCES record_learning_proposals(id), FOREIGN KEY(run_id) REFERENCES record_learning_runs(id),
 FOREIGN KEY(input_bundle_id) REFERENCES record_learning_input_bundles(id), FOREIGN KEY(scope_id) REFERENCES record_learning_scopes(id),
 FOREIGN KEY(proposed_by) REFERENCES record_operators(id), UNIQUE(logical_id,version),
 CHECK(version>0 AND class IN ('PROMPT_CHANGE','CONFIG_CHANGE','STRATEGY_CHANGE','OFFER_OR_PRODUCT_CHANGE','ENGINEERING_CAPABILITY_REQUEST')
   AND length(btrim(bottleneck)) BETWEEN 1 AND 4000 AND confidence BETWEEN 0 AND 1 AND sample_size>0
   AND jsonb_typeof(target_metrics)='array' AND jsonb_array_length(target_metrics)>0
   AND jsonb_typeof(protected_metrics)='array' AND jsonb_array_length(protected_metrics)>0
   AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_candidate_versions (
 id UUID PRIMARY KEY, logical_id UUID NOT NULL, version INTEGER NOT NULL, proposal_id UUID NOT NULL UNIQUE,
 baseline_artifact_id UUID NOT NULL, baseline_experiment_id UUID NOT NULL, baseline_artifact_kind VARCHAR(64) NOT NULL,
 baseline_artifact_version INTEGER NOT NULL, baseline_artifact_hash VARCHAR(64) NOT NULL, candidate_configuration JSONB NOT NULL,
 config_diff JSONB NOT NULL, diff_hash VARCHAR(64) NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(proposal_id) REFERENCES record_learning_proposals(id),
 FOREIGN KEY(baseline_artifact_id,baseline_experiment_id,baseline_artifact_kind,baseline_artifact_version,baseline_artifact_hash)
   REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash), UNIQUE(logical_id,version),
 CHECK(version>0 AND jsonb_typeof(config_diff)='array' AND jsonb_array_length(config_diff)>0
   AND diff_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_offline_comparisons (
 id UUID PRIMARY KEY, proposal_id UUID NOT NULL, candidate_id UUID, input_bundle_id UUID NOT NULL,
 evaluator_version VARCHAR(100) NOT NULL, evaluator_hash VARCHAR(64) NOT NULL, baseline_hash VARCHAR(64) NOT NULL,
 candidate_hash VARCHAR(64) NOT NULL, metric_results JSONB NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(proposal_id) REFERENCES record_learning_proposals(id), FOREIGN KEY(candidate_id) REFERENCES record_learning_candidate_versions(id),
 FOREIGN KEY(input_bundle_id) REFERENCES record_learning_input_bundles(id),
 CHECK(evaluator_hash ~ '^[0-9a-f]{64}$' AND baseline_hash ~ '^[0-9a-f]{64}$' AND candidate_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_regression_assessments (
 id UUID PRIMARY KEY, comparison_id UUID NOT NULL UNIQUE, disposition VARCHAR(16) NOT NULL, metric_results JSONB NOT NULL,
 rollback_satisfied BOOLEAN NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(comparison_id) REFERENCES record_learning_offline_comparisons(id),
 CHECK(disposition IN ('PASS','FAIL','INCONCLUSIVE','REJECTED') AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_failure_analyses (
 id UUID PRIMARY KEY, comparison_id UUID NOT NULL UNIQUE, reason_codes JSONB NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(comparison_id) REFERENCES record_learning_offline_comparisons(id),
 CHECK(jsonb_typeof(reason_codes)='array' AND jsonb_array_length(reason_codes)>0 AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_negative_learning_records (
 id UUID PRIMARY KEY, proposal_id UUID NOT NULL, comparison_id UUID, classification VARCHAR(100) NOT NULL,
 reason_codes JSONB NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(proposal_id) REFERENCES record_learning_proposals(id), FOREIGN KEY(comparison_id) REFERENCES record_learning_offline_comparisons(id),
 CHECK(length(btrim(classification)) BETWEEN 1 AND 100 AND jsonb_typeof(reason_codes)='array' AND jsonb_array_length(reason_codes)>0 AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_capability_gaps (
 id UUID PRIMARY KEY, run_id UUID NOT NULL, proposal_id UUID NOT NULL, description VARCHAR(4000) NOT NULL,
 content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL, FOREIGN KEY(run_id) REFERENCES record_learning_runs(id),
 FOREIGN KEY(proposal_id) REFERENCES record_learning_proposals(id), CHECK(length(btrim(description)) BETWEEN 1 AND 4000 AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_engineering_capability_requests (
 id UUID PRIMARY KEY, gap_id UUID NOT NULL UNIQUE, proposal_id UUID NOT NULL UNIQUE, description VARCHAR(4000) NOT NULL,
 boundary VARCHAR(4000) NOT NULL, expected_benefit VARCHAR(4000) NOT NULL, risk VARCHAR(4000) NOT NULL, content_hash VARCHAR(64) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL, FOREIGN KEY(gap_id) REFERENCES record_capability_gaps(id), FOREIGN KEY(proposal_id) REFERENCES record_learning_proposals(id),
 CHECK(length(btrim(description)) BETWEEN 1 AND 4000 AND length(btrim(boundary)) BETWEEN 1 AND 4000
   AND length(btrim(expected_benefit)) BETWEEN 1 AND 4000 AND length(btrim(risk)) BETWEEN 1 AND 4000 AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_learning_review_controls (
 id UUID PRIMARY KEY, run_id UUID NOT NULL, kind VARCHAR(32) NOT NULL, baseline_candidate_id UUID, operator_id UUID NOT NULL,
 content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL, FOREIGN KEY(run_id) REFERENCES record_learning_runs(id),
 FOREIGN KEY(baseline_candidate_id) REFERENCES record_learning_candidate_versions(id), FOREIGN KEY(operator_id) REFERENCES record_operators(id),
 CHECK(kind IN ('PAUSE_OFFLINE_REVIEW','PIN_BASELINE') AND ((kind='PIN_BASELINE')=(baseline_candidate_id IS NOT NULL)) AND content_hash ~ '^[0-9a-f]{64}$')
);

CREATE FUNCTION record_learning_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable learning record'; END $$;
CREATE FUNCTION record_learning_input_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b record_learning_input_bundles;
BEGIN
 SELECT * INTO b FROM record_learning_input_bundles WHERE id=NEW.bundle_id;
 IF b.id IS NULL THEN RAISE EXCEPTION 'missing learning input bundle'; END IF;
 IF TG_TABLE_NAME='record_learning_input_evidence' AND NOT EXISTS(SELECT 1 FROM gov_evidence WHERE id=NEW.evidence_id AND call_id=NEW.call_id) THEN RAISE EXCEPTION 'learning evidence call mismatch'; END IF;
 IF TG_TABLE_NAME='record_learning_input_costs' AND NOT EXISTS(SELECT 1 FROM gov_settlements WHERE id=NEW.cost_id AND call_id=NEW.call_id) AND NOT EXISTS(SELECT 1 FROM gov_cash_entries WHERE id=NEW.cost_id AND call_id=NEW.call_id) THEN RAISE EXCEPTION 'learning cost call mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_learning_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.protected_components <> '["AUTHORIZATION","COMPLIANCE","COMMERCIAL_POLICY","OFFER_ACCEPTANCE","PRODUCT_POLICY"]'::jsonb THEN RAISE EXCEPTION 'protected learning components changed'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_learning_proposal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r record_learning_runs; b record_learning_input_bundles; s record_learning_scopes;
BEGIN
 SELECT * INTO r FROM record_learning_runs WHERE id=NEW.run_id; SELECT * INTO b FROM record_learning_input_bundles WHERE id=NEW.input_bundle_id; SELECT * INTO s FROM record_learning_scopes WHERE id=NEW.scope_id;
 IF r.id IS NULL OR b.run_id<>r.id OR s.run_id<>r.id THEN RAISE EXCEPTION 'learning proposal lineage mismatch'; END IF;
 IF (NEW.class='OFFER_OR_PRODUCT_CHANGE' AND s.target_subsystem<>'PRODUCT_REVIEW') OR (NEW.class='ENGINEERING_CAPABILITY_REQUEST' AND s.target_subsystem<>'ENGINEERING_REVIEW') OR (NEW.class IN ('PROMPT_CHANGE','CONFIG_CHANGE','STRATEGY_CHANGE') AND s.target_subsystem IN ('PRODUCT_REVIEW','ENGINEERING_REVIEW')) THEN RAISE EXCEPTION 'invalid learning target subsystem'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_learning_candidate_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p record_learning_proposals; path text;
BEGIN
 SELECT * INTO p FROM record_learning_proposals WHERE id=NEW.proposal_id;
 IF p.id IS NULL OR p.class NOT IN ('PROMPT_CHANGE','CONFIG_CHANGE','STRATEGY_CHANGE') THEN RAISE EXCEPTION 'candidate not allowed for proposal class'; END IF;
 FOR path IN SELECT value->>'path' FROM jsonb_array_elements(NEW.config_diff) LOOP
  IF path IS NULL OR path !~ '^/' OR path ~* '(authorization|compliance|commercial_policy|offer_acceptance|product_policy)' THEN RAISE EXCEPTION 'protected learning diff'; END IF;
 END LOOP;
 RETURN NEW;
END $$;
CREATE FUNCTION record_learning_proposal_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p record_learning_proposals; n integer;
BEGIN
 SELECT * INTO p FROM record_learning_proposals WHERE id=NEW.id;
 SELECT count(*) INTO n FROM record_learning_candidate_versions WHERE proposal_id=NEW.id;
 IF (p.class IN ('PROMPT_CHANGE','CONFIG_CHANGE','STRATEGY_CHANGE') AND n<>1) OR (p.class NOT IN ('PROMPT_CHANGE','CONFIG_CHANGE','STRATEGY_CHANGE') AND n<>0) THEN RAISE EXCEPTION 'learning candidate class mismatch'; END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION record_learning_comparison_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p record_learning_proposals; c record_learning_candidate_versions;
BEGIN
 SELECT * INTO p FROM record_learning_proposals WHERE id=NEW.proposal_id;
 IF p.id IS NULL OR NEW.input_bundle_id<>p.input_bundle_id THEN RAISE EXCEPTION 'learning comparison lineage mismatch'; END IF;
 IF NEW.candidate_id IS NOT NULL THEN SELECT * INTO c FROM record_learning_candidate_versions WHERE id=NEW.candidate_id; IF c.id IS NULL OR c.proposal_id<>p.id THEN RAISE EXCEPTION 'learning candidate comparison mismatch'; END IF; END IF;
 IF (p.class IN ('PROMPT_CHANGE','CONFIG_CHANGE','STRATEGY_CHANGE')) <> (NEW.candidate_id IS NOT NULL) THEN RAISE EXCEPTION 'learning comparison candidate mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_learning_assessment_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_learning_regression_assessments; f integer; n integer;
BEGIN
 SELECT * INTO a FROM record_learning_regression_assessments WHERE id=NEW.id;
 SELECT count(*) INTO f FROM record_learning_failure_analyses WHERE comparison_id=a.comparison_id;
 SELECT count(*) INTO n FROM record_negative_learning_records WHERE comparison_id=a.comparison_id;
 IF a.disposition IN ('FAIL','INCONCLUSIVE','REJECTED') AND (f<>1 OR n<1) THEN RAISE EXCEPTION 'negative learning evaluation requires retained analysis'; END IF;
 IF a.disposition='PASS' AND (f<>0 OR n<>0) THEN RAISE EXCEPTION 'successful evaluation cannot retain negative result'; END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION record_learning_engineering_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p record_learning_proposals; g record_capability_gaps;
BEGIN
 SELECT * INTO p FROM record_learning_proposals WHERE id=NEW.proposal_id; SELECT * INTO g FROM record_capability_gaps WHERE id=NEW.gap_id;
 IF p.id IS NULL OR g.id IS NULL OR g.proposal_id<>p.id OR p.class<>'ENGINEERING_CAPABILITY_REQUEST' THEN RAISE EXCEPTION 'engineering capability request must be descriptive'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_learning_input_evidence_guard BEFORE INSERT ON record_learning_input_evidence FOR EACH ROW EXECUTE FUNCTION record_learning_input_guard();
CREATE TRIGGER record_learning_input_cost_guard BEFORE INSERT ON record_learning_input_costs FOR EACH ROW EXECUTE FUNCTION record_learning_input_guard();
CREATE TRIGGER record_learning_scope_invariants BEFORE INSERT ON record_learning_scopes FOR EACH ROW EXECUTE FUNCTION record_learning_scope_guard();
CREATE TRIGGER record_learning_proposal_invariants BEFORE INSERT ON record_learning_proposals FOR EACH ROW EXECUTE FUNCTION record_learning_proposal_guard();
CREATE TRIGGER record_learning_candidate_invariants BEFORE INSERT ON record_learning_candidate_versions FOR EACH ROW EXECUTE FUNCTION record_learning_candidate_guard();
CREATE CONSTRAINT TRIGGER record_learning_proposal_candidate_complete AFTER INSERT ON record_learning_proposals DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION record_learning_proposal_complete();
CREATE TRIGGER record_learning_comparison_invariants BEFORE INSERT ON record_learning_offline_comparisons FOR EACH ROW EXECUTE FUNCTION record_learning_comparison_guard();
CREATE CONSTRAINT TRIGGER record_learning_assessment_negative_complete AFTER INSERT ON record_learning_regression_assessments DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION record_learning_assessment_complete();
CREATE TRIGGER record_learning_engineering_invariants BEFORE INSERT ON record_engineering_capability_requests FOR EACH ROW EXECUTE FUNCTION record_learning_engineering_guard();
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['runs','input_bundles','input_artifacts','input_evidence','input_call_snapshots','input_usage','input_costs','scopes','proposals','candidate_versions','offline_comparisons','regression_assessments','failure_analyses','negative_learning_records','capability_gaps','engineering_capability_requests','review_controls'] LOOP EXECUTE format('CREATE TRIGGER record_learning_%s_immutable BEFORE UPDATE OR DELETE ON record_%s FOR EACH ROW EXECUTE FUNCTION record_learning_immutable()',t,CASE WHEN t='capability_gaps' THEN 'capability_gaps' WHEN t='engineering_capability_requests' THEN 'engineering_capability_requests' WHEN t='negative_learning_records' THEN 'negative_learning_records' ELSE 'learning_'||t END); END LOOP; END $$;
""")


def downgrade() -> None:
    op.execute("""
DROP TABLE record_learning_review_controls;
DROP TABLE record_engineering_capability_requests;
DROP TABLE record_capability_gaps;
DROP TABLE record_negative_learning_records;
DROP TABLE record_learning_failure_analyses;
DROP TABLE record_learning_regression_assessments;
DROP TABLE record_learning_offline_comparisons;
DROP TABLE record_learning_candidate_versions;
DROP TABLE record_learning_proposals;
DROP TABLE record_learning_scopes;
DROP TABLE record_learning_input_costs;
DROP TABLE record_learning_input_usage;
DROP TABLE record_learning_input_call_snapshots;
DROP TABLE record_learning_input_evidence;
DROP TABLE record_learning_input_artifacts;
DROP TABLE record_learning_input_bundles;
DROP TABLE record_learning_runs;
DROP FUNCTION record_learning_engineering_guard();
DROP FUNCTION record_learning_assessment_complete();
DROP FUNCTION record_learning_comparison_guard();
DROP FUNCTION record_learning_proposal_complete();
DROP FUNCTION record_learning_candidate_guard();
DROP FUNCTION record_learning_proposal_guard();
DROP FUNCTION record_learning_scope_guard();
DROP FUNCTION record_learning_input_guard();
DROP FUNCTION record_learning_immutable();
""")
