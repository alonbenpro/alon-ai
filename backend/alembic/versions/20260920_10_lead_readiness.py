"""Persist lead readiness, aggregate calibration and append-only requalification."""

from alembic import op

revision = "20260920_10"
down_revision = "0d1db464e1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""

CREATE TABLE record_readiness_provider_results (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	candidate_id UUID,
	batch_id UUID NOT NULL,
	call_id UUID NOT NULL,
	operation_id UUID NOT NULL,
	config_id UUID NOT NULL,
	config_version UUID NOT NULL,
	grant_id UUID NOT NULL,
	grant_version INTEGER NOT NULL,
	result_evidence_id UUID NOT NULL,
	retained_id UUID,
	rights_mode VARCHAR(32) NOT NULL,
	rights_reason VARCHAR(32) NOT NULL,
	result_hash VARCHAR(64) NOT NULL,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(candidate_id, experiment_id) REFERENCES supply_candidates (id, experiment_id),
	FOREIGN KEY(batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id),
	FOREIGN KEY(call_id) REFERENCES gov_calls (id),
	FOREIGN KEY(operation_id) REFERENCES gov_operations (id),
	FOREIGN KEY(config_id) REFERENCES gov_configs (id),
	FOREIGN KEY(grant_id, grant_version) REFERENCES gov_grants (id, version),
	FOREIGN KEY(result_evidence_id) REFERENCES gov_evidence (id),
	FOREIGN KEY(retained_id) REFERENCES gov_retained (id),
	UNIQUE (id, experiment_id, candidate_id),
	UNIQUE (id, experiment_id, batch_id),
	CHECK (observed_at<valid_until AND result_hash ~ '^[0-9a-f]{64}$' AND batch_id IS NOT NULL),
	CHECK (rights_mode IN ('RETAIN_SCOPED_CONTENT')),
	CHECK (rights_reason IN ('ALLOWED')),
	UNIQUE (call_id),
	UNIQUE (result_evidence_id)
)


""")
    op.execute(r"""

CREATE TABLE record_readiness_contactability_decisions (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	candidate_id UUID NOT NULL,
	organization_id UUID,
	recipient_id UUID,
	recipient_source_id UUID,
	source_fact_id UUID,
	verification_fact_id UUID,
	provider_result_id UUID,
	version INTEGER NOT NULL,
	outcome VARCHAR(32) NOT NULL,
	reason_code VARCHAR(64) NOT NULL,
	payload_hash VARCHAR(64) NOT NULL,
	decided_by UUID NOT NULL,
	decided_at TIMESTAMP WITH TIME ZONE NOT NULL,
	valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(candidate_id, experiment_id) REFERENCES supply_candidates (id, experiment_id),
	FOREIGN KEY(recipient_source_id, experiment_id, organization_id, recipient_id) REFERENCES record_org_recipient_sources (id, experiment_id, organization_id, recipient_id),
	FOREIGN KEY(source_fact_id, experiment_id) REFERENCES supply_facts (id, experiment_id),
	FOREIGN KEY(verification_fact_id, experiment_id) REFERENCES supply_facts (id, experiment_id),
	FOREIGN KEY(provider_result_id, experiment_id, candidate_id) REFERENCES record_readiness_provider_results (id, experiment_id, candidate_id),
	UNIQUE (candidate_id, version),
	UNIQUE (id, experiment_id, candidate_id),
	CHECK (outcome IN ('SUPPORTED_CONTACT_ADDRESS','EMAIL_NOT_FOUND')),
	CHECK (version>0 AND decided_at<valid_until AND payload_hash ~ '^[0-9a-f]{64}$'),
	CHECK ((outcome='SUPPORTED_CONTACT_ADDRESS' AND organization_id IS NOT NULL AND recipient_id IS NOT NULL AND recipient_source_id IS NOT NULL AND source_fact_id IS NOT NULL) OR (outcome='EMAIL_NOT_FOUND' AND organization_id IS NOT NULL AND recipient_id IS NULL AND recipient_source_id IS NULL AND source_fact_id IS NULL AND verification_fact_id IS NULL))
)


""")
    op.execute(r"""

CREATE TABLE record_calibration_proposals (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	base_offer_acceptance_id UUID NOT NULL,
	base_offer_id UUID NOT NULL,
	base_profile_id UUID NOT NULL,
	base_policy_id UUID NOT NULL,
	mismatch_code VARCHAR(64) NOT NULL,
	proposed_change_codes VARCHAR(64)[] NOT NULL,
	evidence_hash VARCHAR(64) NOT NULL,
	proposed_by UUID NOT NULL,
	proposed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(base_offer_acceptance_id, experiment_id) REFERENCES record_offer_acceptances (id, experiment_id),
	FOREIGN KEY(base_offer_id, experiment_id) REFERENCES record_offer_packages (id, experiment_id),
	FOREIGN KEY(base_profile_id) REFERENCES record_offer_qualification_profiles (id),
	FOREIGN KEY(base_policy_id) REFERENCES record_initial_outreach_policies (id),
	UNIQUE (id, experiment_id),
	CHECK (cardinality(proposed_change_codes)>0)
)


""")
    op.execute(r"""

CREATE TABLE record_readiness_discovery_plans (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	batch_id UUID NOT NULL,
	offer_acceptance_id UUID NOT NULL,
	offer_id UUID NOT NULL,
	profile_id UUID NOT NULL,
	policy_id UUID NOT NULL,
	mode VARCHAR(24) NOT NULL,
	geography_filter_ids UUID[] NOT NULL,
	idea_artifact_id UUID NOT NULL,
	idea_kind VARCHAR(64) NOT NULL,
	idea_version INTEGER NOT NULL,
	idea_hash VARCHAR(64) NOT NULL,
	research_artifact_id UUID NOT NULL,
	research_kind VARCHAR(64) NOT NULL,
	research_version INTEGER NOT NULL,
	research_hash VARCHAR(64) NOT NULL,
	batch_plan_hash VARCHAR(64) NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id),
	FOREIGN KEY(offer_acceptance_id, experiment_id) REFERENCES record_offer_acceptances (id, experiment_id),
	FOREIGN KEY(idea_artifact_id, experiment_id, idea_kind, idea_version, idea_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	FOREIGN KEY(research_artifact_id, experiment_id, research_kind, research_version, research_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	UNIQUE (id, experiment_id, batch_id),
	CHECK (mode IN ('LOCAL_BUSINESS','ONLINE_COMPANY','HYBRID')),
	CHECK (idea_kind='IDEA_BRIEF' AND research_kind='MARKET_RESEARCH_REPORT' AND idea_version>0 AND research_version>0 AND idea_hash ~ '^[0-9a-f]{64}$' AND research_hash ~ '^[0-9a-f]{64}$' AND batch_plan_hash ~ '^[0-9a-f]{64}$'),
	CHECK (mode='ONLINE_COMPANY' OR cardinality(geography_filter_ids)>0),
	UNIQUE (batch_id)
)


""")
    op.execute(r"""

CREATE TABLE record_readiness_research_plans (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	candidate_id UUID NOT NULL,
	organization_id UUID NOT NULL,
	recipient_id UUID NOT NULL,
	recipient_source_id UUID NOT NULL,
	contactability_id UUID,
	offer_acceptance_id UUID NOT NULL,
	offer_id UUID NOT NULL,
	profile_id UUID NOT NULL,
	policy_id UUID NOT NULL,
	profile_criteria_hash VARCHAR(64) NOT NULL,
	artifact_id UUID NOT NULL,
	artifact_kind VARCHAR(64) NOT NULL,
	artifact_version INTEGER NOT NULL,
	artifact_hash VARCHAR(64) NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(candidate_id, experiment_id) REFERENCES supply_candidates (id, experiment_id),
	FOREIGN KEY(recipient_source_id, experiment_id, organization_id, recipient_id) REFERENCES record_org_recipient_sources (id, experiment_id, organization_id, recipient_id),
	FOREIGN KEY(contactability_id, experiment_id, candidate_id) REFERENCES record_readiness_contactability_decisions (id, experiment_id, candidate_id),
	FOREIGN KEY(offer_acceptance_id, experiment_id) REFERENCES record_offer_acceptances (id, experiment_id),
	FOREIGN KEY(artifact_id, experiment_id, artifact_kind, artifact_version, artifact_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	UNIQUE (id, experiment_id, candidate_id),
	CHECK (artifact_kind='RESEARCH_PLAN' AND artifact_version>0 AND artifact_hash ~ '^[0-9a-f]{64}$' AND profile_criteria_hash ~ '^[0-9a-f]{64}$'),
	UNIQUE (artifact_id)
)


""")
    op.execute(r"""

CREATE TABLE record_calibration_decisions (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	proposal_id UUID NOT NULL,
	base_offer_acceptance_id UUID NOT NULL,
	base_offer_id UUID NOT NULL,
	base_profile_id UUID NOT NULL,
	base_policy_id UUID NOT NULL,
	evidence_hash VARCHAR(64) NOT NULL,
	outcome VARCHAR(24) NOT NULL,
	rule_version VARCHAR(64) NOT NULL,
	reason_code VARCHAR(64) NOT NULL,
	decided_by UUID NOT NULL,
	decided_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(proposal_id, experiment_id) REFERENCES record_calibration_proposals (id, experiment_id),
	FOREIGN KEY(base_offer_acceptance_id, experiment_id) REFERENCES record_offer_acceptances (id, experiment_id),
	UNIQUE (id, experiment_id),
	CHECK (outcome IN ('ACCEPT','REJECT','INSUFFICIENT_EVIDENCE') AND rule_version='qualification-calibration-v1'),
	UNIQUE (proposal_id)
)


""")
    op.execute(r"""

CREATE TABLE record_readiness_research_runs (
	id UUID NOT NULL,
	plan_id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	candidate_id UUID NOT NULL,
	provider_result_id UUID,
	independent_source_id UUID,
	payload_hash VARCHAR(64) NOT NULL,
	completed_by UUID NOT NULL,
	completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(plan_id, experiment_id, candidate_id) REFERENCES record_readiness_research_plans (id, experiment_id, candidate_id),
	FOREIGN KEY(provider_result_id, experiment_id, candidate_id) REFERENCES record_readiness_provider_results (id, experiment_id, candidate_id),
	FOREIGN KEY(independent_source_id, experiment_id) REFERENCES supply_references (id, experiment_id),
	UNIQUE (id, experiment_id, candidate_id),
	UNIQUE (id, experiment_id),
	CHECK ((provider_result_id IS NULL)<>(independent_source_id IS NULL) AND payload_hash ~ '^[0-9a-f]{64}$')
)


""")
    op.execute(r"""

CREATE TABLE record_calibration_fulfillments (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	calibration_decision_id UUID NOT NULL,
	base_offer_acceptance_id UUID NOT NULL,
	offer_acceptance_id UUID NOT NULL,
	offer_id UUID NOT NULL,
	profile_id UUID NOT NULL,
	policy_id UUID NOT NULL,
	fulfilled_by UUID NOT NULL,
	fulfilled_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(calibration_decision_id, experiment_id) REFERENCES record_calibration_decisions (id, experiment_id),
	FOREIGN KEY(base_offer_acceptance_id, experiment_id) REFERENCES record_offer_acceptances (id, experiment_id),
	FOREIGN KEY(offer_acceptance_id, experiment_id) REFERENCES record_offer_acceptances (id, experiment_id),
	FOREIGN KEY(offer_id, experiment_id) REFERENCES record_offer_packages (id, experiment_id),
	FOREIGN KEY(profile_id) REFERENCES record_offer_qualification_profiles (id),
	FOREIGN KEY(policy_id) REFERENCES record_initial_outreach_policies (id),
	UNIQUE (id, experiment_id),
	UNIQUE (offer_acceptance_id),
	UNIQUE (calibration_decision_id)
)


""")
    op.execute(r"""

CREATE TABLE record_readiness_evidence_links (
	id UUID NOT NULL,
	run_id UUID NOT NULL,
	dossier_id UUID NOT NULL,
	dossier_evidence_id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	payload_hash VARCHAR(64) NOT NULL,
	linked_by UUID NOT NULL,
	linked_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(run_id, experiment_id) REFERENCES record_readiness_research_runs (id, experiment_id),
	FOREIGN KEY(dossier_id, experiment_id) REFERENCES record_qualification_dossiers (id, experiment_id),
	FOREIGN KEY(dossier_evidence_id, dossier_id) REFERENCES record_qualification_evidence (id, dossier_id),
	UNIQUE (run_id, dossier_evidence_id),
	CHECK (payload_hash ~ '^[0-9a-f]{64}$')
)


""")
    op.execute(r"""

CREATE TABLE record_calibration_accepted_affected (
	calibration_decision_id UUID NOT NULL,
	candidate_id UUID NOT NULL,
	previous_decision_id UUID NOT NULL,
	previous_dossier_id UUID NOT NULL,
	previous_matrix_id UUID NOT NULL,
	PRIMARY KEY (calibration_decision_id, candidate_id),
	FOREIGN KEY(calibration_decision_id) REFERENCES record_calibration_decisions (id),
	FOREIGN KEY(previous_decision_id) REFERENCES record_qualification_decisions (id),
	FOREIGN KEY(previous_dossier_id) REFERENCES record_qualification_dossiers (id),
	FOREIGN KEY(previous_matrix_id) REFERENCES record_qualification_matrices (id)
)


""")
    op.execute(r"""

CREATE TABLE record_calibration_obligations (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	fulfillment_id UUID NOT NULL,
	candidate_id UUID NOT NULL,
	previous_decision_id UUID NOT NULL,
	previous_dossier_id UUID NOT NULL,
	previous_matrix_id UUID NOT NULL,
	required_offer_acceptance_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(fulfillment_id, experiment_id) REFERENCES record_calibration_fulfillments (id, experiment_id),
	FOREIGN KEY(previous_decision_id) REFERENCES record_qualification_decisions (id),
	FOREIGN KEY(previous_dossier_id) REFERENCES record_qualification_dossiers (id),
	FOREIGN KEY(previous_matrix_id) REFERENCES record_qualification_matrices (id),
	FOREIGN KEY(required_offer_acceptance_id, experiment_id) REFERENCES record_offer_acceptances (id, experiment_id),
	UNIQUE (id, experiment_id),
	UNIQUE (fulfillment_id, candidate_id)
)


""")
    op.execute(r"""

CREATE TABLE record_calibration_proposal_evidence (
	proposal_id UUID NOT NULL,
	decision_id UUID NOT NULL,
	candidate_id UUID NOT NULL,
	dossier_id UUID NOT NULL,
	matrix_id UUID NOT NULL,
	finding_code VARCHAR(64) NOT NULL,
	PRIMARY KEY (proposal_id, decision_id),
	FOREIGN KEY(proposal_id) REFERENCES record_calibration_proposals (id),
	FOREIGN KEY(decision_id) REFERENCES record_qualification_decisions (id),
	FOREIGN KEY(dossier_id) REFERENCES record_qualification_dossiers (id),
	FOREIGN KEY(matrix_id) REFERENCES record_qualification_matrices (id),
	UNIQUE (proposal_id, candidate_id)
)


""")
    op.execute(r"""

CREATE TABLE record_calibration_completions (
	obligation_id UUID NOT NULL,
	decision_id UUID NOT NULL,
	completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (obligation_id),
	FOREIGN KEY(obligation_id) REFERENCES record_calibration_obligations (id),
	FOREIGN KEY(decision_id) REFERENCES record_qualification_decisions (id),
	UNIQUE (decision_id)
)


""")
    op.execute(r"""
CREATE UNIQUE INDEX uq_record_calibration_one_accepted_per_experiment ON record_calibration_decisions (experiment_id) WHERE outcome = 'ACCEPT'
""")
    op.execute(r"""
ALTER TABLE record_offer_packages ADD COLUMN calibration_decision_id uuid
""")
    op.execute(r"""
ALTER TABLE record_offer_packages DROP CONSTRAINT record_offer_packages_bundle_id_key
""")
    op.execute(r"""
ALTER TABLE record_offer_packages ADD CONSTRAINT record_offer_packages_calibration_decision_id_key UNIQUE(calibration_decision_id)
""")
    op.execute(r"""
ALTER TABLE record_offer_packages ADD CONSTRAINT fk_offer_calibration_decision FOREIGN KEY(calibration_decision_id,experiment_id) REFERENCES record_calibration_decisions(id,experiment_id)
""")
    op.execute(r"""
CREATE UNIQUE INDEX uq_record_offer_uncalibrated_bundle ON record_offer_packages(bundle_id) WHERE calibration_decision_id IS NULL
""")
    op.execute(r"""
CREATE FUNCTION record_offer_calibration_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d record_calibration_decisions; base record_offer_packages;
BEGIN
 IF NEW.calibration_decision_id IS NULL THEN RETURN NEW; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO d FROM record_calibration_decisions WHERE id=NEW.calibration_decision_id;
 SELECT * INTO base FROM record_offer_packages WHERE id=d.base_offer_id;
 IF d.outcome IS DISTINCT FROM 'ACCEPT' OR d.experiment_id IS DISTINCT FROM NEW.experiment_id
 OR base.bundle_id IS DISTINCT FROM NEW.bundle_id
 OR d.base_offer_acceptance_id IS DISTINCT FROM (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
 OR EXISTS(SELECT 1 FROM record_calibration_fulfillments WHERE calibration_decision_id=d.id)
 OR EXISTS(SELECT 1 FROM record_qualification_cohorts WHERE experiment_id=NEW.experiment_id)
 THEN RAISE EXCEPTION 'calibration cannot bypass offer acceptance'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_offer_calibration_guard BEFORE INSERT ON record_offer_packages FOR EACH ROW EXECUTE FUNCTION record_offer_calibration_guard();

""")
    op.execute(r"""
ALTER TABLE record_qualification_decisions DROP CONSTRAINT record_qualification_decision_candidate_id_experiment_id_p_fkey
""")
    op.execute(r"""
ALTER TABLE record_qualification_decisions ADD CONSTRAINT fk_qualification_proposal_fact FOREIGN KEY(proposal_fact_id,experiment_id) REFERENCES supply_facts(id,experiment_id)
""")
    op.execute(r"""
CREATE VIEW record_current_supply_qualifications AS
WITH latest AS (
 SELECT DISTINCT ON (d.candidate_id) d.* FROM record_qualification_decisions d
 JOIN record_qualification_dossiers dossier ON dossier.id=d.dossier_id
 ORDER BY d.candidate_id,dossier.version DESC
)
SELECT old.candidate_id,old.experiment_id,old.fact_id,old.accepted_at,
 CASE WHEN old.outcome='QUALIFIED' AND EXISTS(SELECT 1 FROM record_offer_acceptances a WHERE a.experiment_id=old.experiment_id)
 THEN 'REJECTED_EVIDENCE' ELSE old.outcome END
FROM supply_qualifications old WHERE NOT EXISTS(SELECT 1 FROM latest d WHERE d.candidate_id=old.candidate_id)
UNION ALL
SELECT d.candidate_id,d.experiment_id,d.proposal_fact_id,d.decided_at,
 CASE WHEN d.offer_acceptance_id=(SELECT id FROM record_offer_acceptances WHERE experiment_id=d.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
 AND d.outcome IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE')
 AND d.valid_until>record_org_now()
 AND EXISTS(SELECT 1 FROM supply_contacts c WHERE c.candidate_id=d.candidate_id AND c.outcome='SUPPORTED' AND c.resolved_at<=record_org_now() AND c.valid_until>record_org_now())
 AND NOT EXISTS(SELECT 1 FROM record_readiness_contactability_decisions rc WHERE rc.candidate_id=d.candidate_id AND rc.version=(SELECT max(version) FROM record_readiness_contactability_decisions WHERE candidate_id=d.candidate_id) AND (rc.outcome<>'SUPPORTED_CONTACT_ADDRESS' OR rc.recipient_source_id<>d.recipient_source_id OR rc.valid_until<=record_org_now()))
 AND EXISTS(SELECT 1 FROM record_org_recipient_sources source WHERE source.id=d.recipient_source_id AND record_org_source_current(source.retained_id,'EMAIL'))
 AND record_org_block_reason(d.organization_id,d.recipient_id,d.experiment_id) IS NULL
 THEN 'QUALIFIED' ELSE 'REJECTED_EVIDENCE' END
FROM latest d;

CREATE FUNCTION record_readiness_cohort_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM record_calibration_decisions d WHERE d.experiment_id=NEW.experiment_id AND d.outcome='ACCEPT' AND NOT EXISTS(SELECT 1 FROM record_calibration_fulfillments f WHERE f.calibration_decision_id=d.id)) THEN
  RAISE EXCEPTION 'accepted calibration awaits fulfillment';
 END IF;
 IF TG_TABLE_NAME='record_qualification_cohort_members' THEN
 IF NOT EXISTS(
  SELECT 1 FROM record_current_supply_qualifications current
  JOIN record_qualification_decisions d ON d.proposal_fact_id=current.fact_id
  WHERE d.id=NEW.decision_id AND current.outcome='QUALIFIED'
 ) THEN RAISE EXCEPTION 'cohort requires current readiness'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_readiness_cohort_guard BEFORE INSERT ON record_qualification_cohorts FOR EACH ROW EXECUTE FUNCTION record_readiness_cohort_guard();
CREATE TRIGGER record_readiness_member_guard BEFORE INSERT ON record_qualification_cohort_members FOR EACH ROW EXECUTE FUNCTION record_readiness_cohort_guard();

CREATE FUNCTION record_readiness_target() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE')
 AND (SELECT count(*) FROM record_current_supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')=50 THEN
  INSERT INTO supply_outcomes SELECT NEW.experiment_id,NEW.proposal_fact_id,'TARGET_50_REACHED',50,
   (SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id),
   (SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id);
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_readiness_target AFTER INSERT ON record_qualification_decisions FOR EACH ROW EXECUTE FUNCTION record_readiness_target();

CREATE FUNCTION record_readiness_outreach_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid; exp uuid;
BEGIN
 IF TG_TABLE_NAME='record_outreach_contexts' THEN target:=NEW.decision_id;
 ELSE SELECT c.decision_id INTO target FROM record_outreach_contexts c JOIN record_outreach_drafts d ON d.context_id=c.id WHERE d.artifact_id=NEW.draft_artifact_id;
 END IF;
 SELECT experiment_id INTO exp FROM record_qualification_decisions WHERE id=target;
 PERFORM 1 FROM gov_experiments WHERE id=exp FOR UPDATE;
 IF NOT EXISTS(SELECT 1 FROM record_current_supply_qualifications current
 JOIN record_qualification_decisions d ON d.proposal_fact_id=current.fact_id
 WHERE d.id=target AND current.outcome='QUALIFIED') THEN
 RAISE EXCEPTION 'outreach requires current qualification'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_readiness_context_guard BEFORE INSERT ON record_outreach_contexts FOR EACH ROW EXECUTE FUNCTION record_readiness_outreach_guard();
CREATE TRIGGER record_readiness_draft_guard BEFORE INSERT ON record_outreach_validations FOR EACH ROW EXECUTE FUNCTION record_readiness_outreach_guard();

""")
    op.execute(r"""

CREATE OR REPLACE FUNCTION record_qualification_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d record_qualification_dossiers; m record_qualification_matrices; decision record_qualification_decisions; cohort record_qualification_cohorts; acceptance record_offer_acceptances; result_count integer; criterion_count integer;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable qualification record'; END IF;
 IF TG_TABLE_NAME='record_qualification_dossiers' THEN
  SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.offer_acceptance_id;
  IF ROW(acceptance.experiment_id,acceptance.offer_id,acceptance.profile_id,acceptance.policy_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.offer_id,NEW.profile_id,NEW.policy_id)
   OR NOT EXISTS(SELECT 1 FROM supply_candidates c JOIN record_org_bindings b ON b.identity_id=c.identity_id AND b.id=NEW.binding_id JOIN record_org_admissions a ON a.binding_id=b.id AND a.id=NEW.admission_id JOIN record_org_recipient_sources r ON r.binding_id=b.id AND r.candidate_id=c.id AND r.id=NEW.recipient_source_id WHERE c.id=NEW.candidate_id AND c.experiment_id=NEW.experiment_id AND b.organization_id=NEW.organization_id AND r.recipient_id=NEW.recipient_id)
  THEN RAISE EXCEPTION 'exact dossier lineage required'; END IF;
 ELSIF TG_TABLE_NAME='record_qualification_matrices' THEN
  SELECT * INTO d FROM record_qualification_dossiers WHERE id=NEW.dossier_id;
  IF ROW(d.experiment_id,d.candidate_id,d.organization_id,d.recipient_id,d.recipient_source_id,d.offer_acceptance_id,d.offer_id,d.profile_id,d.policy_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.candidate_id,NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id,NEW.offer_acceptance_id,NEW.offer_id,NEW.profile_id,NEW.policy_id) THEN RAISE EXCEPTION 'exact matrix lineage required'; END IF;
 ELSIF TG_TABLE_NAME='record_qualification_decisions' THEN
  SELECT * INTO m FROM record_qualification_matrices WHERE id=NEW.matrix_id;
  SELECT count(*) INTO result_count FROM record_qualification_criterion_results r WHERE r.matrix_id=NEW.matrix_id AND EXISTS(SELECT 1 FROM record_qualification_result_evidence e WHERE e.matrix_id=r.matrix_id AND e.criterion_code=r.criterion_code);
  SELECT count(*) INTO criterion_count FROM record_qualification_criteria WHERE profile_id=NEW.profile_id;
  IF ROW(m.experiment_id,m.dossier_id,m.candidate_id,m.organization_id,m.recipient_id,m.recipient_source_id,m.offer_acceptance_id,m.offer_id,m.profile_id,m.policy_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.dossier_id,NEW.candidate_id,NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id,NEW.offer_acceptance_id,NEW.offer_id,NEW.profile_id,NEW.policy_id)
   OR ((EXISTS(SELECT 1 FROM record_readiness_research_plans p WHERE p.candidate_id=NEW.candidate_id) OR EXISTS(SELECT 1 FROM record_readiness_contactability_decisions contact WHERE contact.candidate_id=NEW.candidate_id)) AND EXISTS(
    SELECT 1 FROM record_qualification_evidence e WHERE e.dossier_id=NEW.dossier_id AND NOT EXISTS(
     SELECT 1 FROM record_readiness_evidence_links l
     JOIN record_readiness_research_runs r ON r.id=l.run_id
     JOIN record_readiness_research_plans p ON p.id=r.plan_id
     LEFT JOIN record_readiness_provider_results pr ON pr.id=r.provider_result_id
     LEFT JOIN gov_retained retained ON retained.id=pr.retained_id
     WHERE l.dossier_evidence_id=e.id AND p.candidate_id=NEW.candidate_id AND p.offer_acceptance_id=NEW.offer_acceptance_id
     AND (r.independent_source_id IS NOT NULL OR (pr.valid_until>NEW.decided_at AND retained.id IS NOT NULL AND record_org_source_current(retained.id,retained.field)))
    )))
   OR result_count<>criterion_count
   OR NEW.offer_acceptance_id IS DISTINCT FROM (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
   OR (NEW.outcome IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE') AND EXISTS(SELECT 1 FROM record_qualification_criterion_results r JOIN record_qualification_criteria c ON c.profile_id=r.profile_id AND c.code=r.criterion_code WHERE r.matrix_id=NEW.matrix_id AND ((c.rule_kind='HARD_GATE' AND r.status<>'SATISFIED') OR (c.rule_kind='FATAL_DISQUALIFIER' AND r.status<>'NOT_SATISFIED'))))
   OR (NEW.outcome='PILOT_FIT_CONTACTABLE' AND NOT EXISTS(SELECT 1 FROM record_qualification_criterion_results r JOIN record_qualification_criteria c ON c.profile_id=r.profile_id AND c.code=r.criterion_code WHERE r.matrix_id=NEW.matrix_id AND c.category='PILOT_FIT' AND r.status='SATISFIED'))
   OR NOT EXISTS(SELECT 1 FROM supply_facts f JOIN supply_candidates c ON c.identity_id=f.identity_id AND c.experiment_id=f.experiment_id JOIN supply_plans p ON p.experiment_id=c.experiment_id WHERE c.id=NEW.candidate_id AND c.deep_started AND f.id=NEW.proposal_fact_id AND f.experiment_id=NEW.experiment_id AND f.observed_at<=NEW.decided_at AND f.valid_until>NEW.decided_at AND f.policy_ref::text=p.initial_plan->>'qualification_rule_id' AND ((NEW.outcome IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE') AND f.kind='QUALIFIED') OR (NEW.outcome NOT IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE') AND f.kind IN ('REJECTED_FIT','REJECTED_EVIDENCE'))))
  THEN RAISE EXCEPTION 'complete authoritative qualification required'; END IF;
 ELSIF TG_TABLE_NAME='record_qualification_cohorts' THEN
  SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.offer_acceptance_id;
  IF ROW(acceptance.experiment_id,acceptance.offer_id,acceptance.profile_id,acceptance.policy_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.offer_id,NEW.profile_id,NEW.policy_id)
   OR NEW.offer_acceptance_id IS DISTINCT FROM (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
  THEN RAISE EXCEPTION 'exact cohort offer required'; END IF;
 ELSIF TG_TABLE_NAME='record_qualification_cohort_members' THEN
  SELECT * INTO decision FROM record_qualification_decisions WHERE id=NEW.decision_id;
  SELECT * INTO cohort FROM record_qualification_cohorts WHERE id=NEW.cohort_id;
  IF decision.outcome NOT IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE') OR decision.valid_until<=record_org_now()
   OR ROW(decision.experiment_id,decision.candidate_id,decision.organization_id,decision.recipient_id,decision.recipient_source_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.candidate_id,NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id)
   OR ROW(decision.experiment_id,decision.offer_acceptance_id,decision.offer_id,decision.profile_id,decision.policy_id) IS DISTINCT FROM ROW(cohort.experiment_id,cohort.offer_acceptance_id,cohort.offer_id,cohort.profile_id,cohort.policy_id)
   OR NOT EXISTS(SELECT 1 FROM record_org_reservations r WHERE r.id=NEW.reservation_id AND ROW(r.experiment_id,r.organization_id,r.recipient_id,r.source_id)=ROW(NEW.experiment_id,NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id))
  THEN RAISE EXCEPTION 'invalid cohort member'; END IF;
 END IF;
 RETURN NEW;
END $$;

""")
    op.execute(r"""

CREATE OR REPLACE FUNCTION supply_feedback_payload(batch uuid, gate text) RETURNS jsonb LANGUAGE sql STABLE AS $$
 WITH b AS (SELECT * FROM supply_batches WHERE id=batch), results AS (
  SELECT c.id,c.observations,CASE WHEN gate='EMAIL' THEN coalesce(t.outcome,'PENDING') ELSE coalesce(q.outcome,t.outcome,'PENDING') END reason
  FROM supply_candidates c JOIN b ON b.experiment_id=c.experiment_id LEFT JOIN supply_contacts t ON t.candidate_id=c.id LEFT JOIN record_current_supply_qualifications q ON q.candidate_id=c.id
 ), reasons AS (SELECT reason,count(*) n FROM results GROUP BY reason), performance AS (
  SELECT f->>'dimension' dimension,f->>'value' value,reason,count(*) n FROM results CROSS JOIN LATERAL jsonb_array_elements(observations) f GROUP BY 1,2,3
  UNION ALL SELECT dc.filter->>'dimension',dc.filter->>'value','QUERY_YIELD_SHORTFALL',(SELECT count(*) FROM results WHERE observations @> jsonb_build_array(dc.filter)) FROM supply_discovery_completions dc WHERE dc.batch_id=batch AND gate='EMAIL' AND (SELECT count(*) FROM results WHERE reason='SUPPORTED')<50
 )
 SELECT jsonb_build_object('prior_plan',b.plan,'deficit',50-(SELECT count(*) FROM results WHERE reason=CASE WHEN gate='EMAIL' THEN 'SUPPORTED' ELSE 'QUALIFIED' END),
 'reasons',coalesce((SELECT jsonb_agg(jsonb_build_object('reason',reason,'count',n) ORDER BY reason) FROM reasons),'[]'::jsonb),
 'performance',coalesce((SELECT jsonb_agg(jsonb_build_object('dimension',dimension,'value',value,'reason',reason,'count',n) ORDER BY dimension,value,reason) FROM performance),'[]'::jsonb)) FROM b
$$

""")
    op.execute(r"""

CREATE OR REPLACE FUNCTION supply_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p supply_plans; b supply_batches; i supply_identities; f supply_facts; v supply_facts; cl supply_facts; c supply_candidates; fb supply_feedback; op gov_operations; cfg gov_configs; payload jsonb; expected text; total integer; item jsonb; prior jsonb; diff jsonb; dim text;
BEGIN
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF TG_OP='UPDATE' THEN
  IF TG_TABLE_NAME='supply_plans' THEN
   IF (to_jsonb(NEW)-'state')<>(to_jsonb(OLD)-'state') OR OLD.state<>'ACTIVE' OR NOT EXISTS(SELECT 1 FROM supply_outcomes WHERE experiment_id=NEW.experiment_id AND reason=NEW.state) THEN RAISE EXCEPTION 'invalid supply transition'; END IF;
  ELSIF TG_TABLE_NAME='supply_batches' THEN
   IF (to_jsonb(NEW)-ARRAY['stage','completed_at'])<>(to_jsonb(OLD)-ARRAY['stage','completed_at']) OR (OLD.completed_at IS NOT NULL AND NEW.completed_at IS DISTINCT FROM OLD.completed_at) OR NOT ((OLD.stage='CONTACT' AND NEW.stage IN ('EMAIL_RETRY_READY','QUALIFICATION','DONE')) OR (OLD.stage='QUALIFICATION' AND NEW.stage IN ('QUALIFICATION_RETRY_READY','DONE'))) THEN RAISE EXCEPTION 'invalid batch transition'; END IF;
   IF OLD.stage='CONTACT' AND EXISTS(SELECT 1 FROM supply_candidates cand LEFT JOIN supply_contacts t ON t.candidate_id=cand.id WHERE cand.batch_id=NEW.id AND (t.candidate_id IS NULL OR t.outcome='SOURCE_FAILURE')) THEN RAISE EXCEPTION 'unresolved contact gate'; END IF;
   IF NEW.stage='QUALIFICATION' AND (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')<50 THEN RAISE EXCEPTION 'email shortage'; END IF;
   IF NEW.stage IN ('EMAIL_RETRY_READY','QUALIFICATION_RETRY_READY') AND NOT EXISTS(SELECT 1 FROM supply_feedback WHERE batch_id=NEW.id AND gate=CASE WHEN NEW.stage='EMAIL_RETRY_READY' THEN 'EMAIL' ELSE 'QUALIFICATION' END) THEN RAISE EXCEPTION 'missing feedback'; END IF;
  ELSIF TG_TABLE_NAME='supply_candidates' THEN
   IF (to_jsonb(NEW)-ARRAY['deep_started','stopped'])<>(to_jsonb(OLD)-ARRAY['deep_started','stopped']) OR (OLD.deep_started AND NOT NEW.deep_started) OR (OLD.stopped AND NOT NEW.stopped) THEN RAISE EXCEPTION 'immutable candidate intent'; END IF;
   IF NEW.deep_started AND NOT OLD.deep_started THEN
    IF NEW.stopped OR NOT EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE') OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=NEW.id AND outcome='SUPPORTED') OR (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')<50 OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND stage='QUALIFICATION') THEN RAISE EXCEPTION 'deep work denied'; END IF;
   END IF;
  ELSE RAISE EXCEPTION 'immutable supply fact'; END IF;
  RETURN NEW;
 END IF;
 SELECT * INTO p FROM supply_plans WHERE experiment_id=NEW.experiment_id;
 IF TG_TABLE_NAME='supply_plans' THEN
  IF NEW.state<>'ACTIVE' OR NOT supply_plan_valid(NEW.initial_plan,NEW.experiment_id) OR NOT supply_filters_valid(NEW.allowed,NEW.experiment_id) OR NOT NEW.allowed @> (NEW.initial_plan->'filters') OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.verification_policy_id AND kind='VERIFICATION_POLICY') THEN RAISE EXCEPTION 'invalid supply plan'; END IF;
 ELSIF TG_TABLE_NAME='supply_identities' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.provenance_ref AND experiment_id=NEW.experiment_id AND kind='INDEPENDENT_SOURCE' AND mode=NEW.mode) THEN RAISE EXCEPTION 'missing permitted provenance'; END IF;
 ELSIF TG_TABLE_NAME='supply_facts' THEN
  SELECT * INTO i FROM supply_identities WHERE id=NEW.identity_id;
  IF i.mode<>NEW.mode THEN RAISE EXCEPTION 'mixed evidence mode'; END IF;
  IF NEW.kind='SOURCE_EMAIL' AND NEW.contact_ref<>NEW.id THEN RAISE EXCEPTION 'source contact identity'; END IF;
  IF NEW.kind IN ('VERIFIED','VERIFICATION_REJECTED') AND (NOT EXISTS(SELECT 1 FROM supply_facts WHERE id=NEW.contact_ref AND identity_id=NEW.identity_id AND kind='SOURCE_EMAIL' AND observed_at<=NEW.observed_at) OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.policy_ref AND kind='VERIFICATION_POLICY')) THEN RAISE EXCEPTION 'invalid verification lineage'; END IF;
  IF NEW.kind IN ('QUALIFIED','REJECTED_FIT','REJECTED_EVIDENCE') AND NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.policy_ref AND kind='QUALIFICATION_RULE') THEN RAISE EXCEPTION 'invalid qualification rule'; END IF;
 ELSIF TG_TABLE_NAME='supply_batches' THEN
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.stage<>'CONTACT' OR NOT supply_plan_valid(NEW.plan,NEW.experiment_id) OR NOT p.allowed @> (NEW.plan->'filters') OR NEW.plan->>'qualification_rule_id'<>p.initial_plan->>'qualification_rule_id' THEN RAISE EXCEPTION 'invalid batch plan'; END IF;
  IF NEW.slot=1 THEN
   IF EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id) OR NEW.plan<>p.initial_plan THEN RAISE EXCEPTION 'initial batch conflict'; END IF;
  ELSE
   SELECT * INTO b FROM supply_batches WHERE experiment_id=NEW.experiment_id ORDER BY slot DESC LIMIT 1;
   SELECT * INTO fb FROM supply_feedback WHERE id=NEW.feedback_id;
   IF fb.experiment_id IS DISTINCT FROM NEW.experiment_id OR fb.batch_id IS DISTINCT FROM b.id OR fb.payload IS DISTINCT FROM supply_feedback_payload(b.id,fb.gate) OR (NEW.slot=2 AND (b.slot<>1 OR b.stage<>'EMAIL_RETRY_READY' OR fb.gate<>'EMAIL')) OR (NEW.slot=3 AND (b.slot NOT IN (1,2) OR b.stage<>'QUALIFICATION_RETRY_READY' OR fb.gate<>'QUALIFICATION')) THEN RAISE EXCEPTION 'stale or wrong feedback'; END IF;
   prior:=b.plan->'filters'; diff:='[]'::jsonb;
   FOR item IN SELECT value FROM jsonb_array_elements(prior || (NEW.plan->'filters')) LOOP
    IF (prior @> jsonb_build_array(item)) <> ((NEW.plan->'filters') @> jsonb_build_array(item)) THEN diff:=diff || jsonb_build_array(item); END IF;
   END LOOP;
   IF jsonb_array_length(diff)=0 THEN RAISE EXCEPTION 'cosmetic plan change'; END IF;
   FOR item IN SELECT * FROM jsonb_array_elements(diff) LOOP
    dim:=item->>'dimension';
    IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(fb.payload->'performance') x WHERE x->>'dimension'=dim AND x->>'reason' NOT IN ('SUPPORTED','QUALIFIED','PENDING','SOURCE_FAILURE') AND EXISTS(SELECT 1 FROM jsonb_array_elements(prior) y WHERE y->>'dimension'=dim AND y->>'value'=x->>'value')) THEN RAISE EXCEPTION 'unjustified plan change'; END IF;
   END LOOP;
  END IF;
 ELSIF TG_TABLE_NAME='supply_candidates' THEN
  SELECT * INTO b FROM supply_batches WHERE id=NEW.batch_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.clearance_id;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR b.stage<>'CONTACT' OR f.kind NOT IN ('IDENTITY_CLEAR','IDENTITY_EXCLUDED') OR NEW.deep_started OR NEW.stopped OR NOT supply_filters_valid(NEW.observations,NEW.experiment_id) OR NOT (b.plan->'filters') @> NEW.observations OR NEW.ordinal<>(SELECT count(*)+1 FROM supply_candidates WHERE batch_id=NEW.batch_id) THEN RAISE EXCEPTION 'candidate admission denied'; END IF;
 ELSIF TG_TABLE_NAME='supply_contacts' THEN
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO b FROM supply_batches WHERE id=c.batch_id;
  SELECT * INTO i FROM supply_identities WHERE id=c.identity_id;
  SELECT * INTO cl FROM supply_facts WHERE id=c.clearance_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.source_id;
  SELECT * INTO v FROM supply_facts WHERE id=NEW.verification_id;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR b.stage<>'CONTACT' OR f.identity_id<>c.identity_id THEN RAISE EXCEPTION 'contact scope or phase'; END IF;
  expected:=CASE WHEN cl.kind='IDENTITY_EXCLUDED' AND f.id=cl.id THEN 'IDENTITY_EXCLUDED' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='EMAIL_ABSENT' THEN 'EMAIL_NOT_FOUND' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='SOURCE_FAILURE' THEN 'SOURCE_FAILURE' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='SOURCE_EMAIL' AND v.identity_id=c.identity_id AND v.contact_ref=f.id AND v.policy_ref=p.verification_policy_id THEN CASE v.kind WHEN 'VERIFIED' THEN 'SUPPORTED' WHEN 'VERIFICATION_REJECTED' THEN 'VERIFICATION_REJECTED' END END;
  IF expected IS NULL OR NEW.outcome<>expected OR (NEW.verification_id IS NOT NULL)<>(expected IN ('SUPPORTED','VERIFICATION_REJECTED')) OR NEW.resolved_at<greatest(i.observed_at,cl.observed_at,f.observed_at,coalesce(v.observed_at,f.observed_at)) OR NEW.resolved_at>=NEW.valid_until OR NEW.valid_until<>least(i.valid_until,cl.valid_until,f.valid_until,coalesce(v.valid_until,f.valid_until)) THEN RAISE EXCEPTION 'invalid contact evidence'; END IF;
 ELSIF TG_TABLE_NAME='supply_contact_failures' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_candidates cand JOIN supply_facts proof ON proof.id=NEW.source_id AND proof.identity_id=cand.identity_id WHERE cand.id=NEW.candidate_id AND proof.kind='SOURCE_FAILURE') THEN RAISE EXCEPTION 'invalid failure lineage'; END IF;
 ELSIF TG_TABLE_NAME='supply_qualifications' THEN
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.fact_id;
  IF NOT f.observed_at<=NEW.accepted_at OR NEW.accepted_at>=f.valid_until OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=c.id AND resolved_at<=NEW.accepted_at AND valid_until>NEW.accepted_at) OR EXISTS(SELECT 1 FROM record_current_supply_qualifications WHERE experiment_id=NEW.experiment_id AND accepted_at>NEW.accepted_at) OR EXISTS(SELECT 1 FROM record_current_supply_qualifications q JOIN supply_facts proof ON proof.id=q.fact_id JOIN supply_contacts t ON t.candidate_id=q.candidate_id WHERE q.experiment_id=NEW.experiment_id AND q.outcome='QUALIFIED' AND (proof.valid_until<=NEW.accepted_at OR t.valid_until<=NEW.accepted_at)) THEN RAISE EXCEPTION 'expired accepted evidence'; END IF;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NOT c.deep_started OR c.stopped OR f.identity_id<>c.identity_id OR f.kind<>NEW.outcome OR f.policy_ref::text<>p.initial_plan->>'qualification_rule_id' OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=c.id AND outcome='SUPPORTED') OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND stage='QUALIFICATION') OR (NEW.outcome='QUALIFIED' AND (SELECT count(*) FROM record_current_supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')>=50) THEN RAISE EXCEPTION 'qualification denied'; END IF;
 ELSIF TG_TABLE_NAME='supply_feedback' THEN
  SELECT * INTO b FROM supply_batches WHERE id=NEW.batch_id;
  payload:=supply_feedback_payload(NEW.batch_id,NEW.gate);
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.payload IS DISTINCT FROM payload OR (payload->>'deficit')::int NOT BETWEEN 1 AND 50 OR b.slot=3 OR (NEW.gate='EMAIL' AND (b.slot<>1 OR b.stage<>'CONTACT')) OR (NEW.gate='QUALIFICATION' AND b.stage<>'QUALIFICATION') OR EXISTS(SELECT 1 FROM jsonb_array_elements(payload->'reasons') x WHERE x->>'reason' IN ('PENDING','SOURCE_FAILURE') OR (NEW.gate='QUALIFICATION' AND x->>'reason'='SUPPORTED')) THEN RAISE EXCEPTION 'incomplete or malformed feedback'; END IF;
 ELSIF TG_TABLE_NAME='supply_operations' THEN
  SELECT * INTO op FROM gov_operations WHERE id=NEW.operation_id;
  SELECT * INTO cfg FROM gov_configs WHERE id=NEW.config_id;
  IF op.gate_kind IS DISTINCT FROM (CASE WHEN NEW.kind='CONTACT' THEN 'CONTACT' ELSE 'SUPPLY' END) OR p.state IS DISTINCT FROM 'ACTIVE' THEN RAISE EXCEPTION 'unbound supply gate'; END IF;
  IF (NEW.kind='DISCOVERY' AND cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','BRAVE_WEB_COVERAGE')) OR (NEW.kind='CONTACT' AND cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT','HUNTER_EMAIL_VERIFICATION','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL')) OR (NEW.kind='DEEP' AND cfg.capability NOT IN ('OPENAI_GENERATE','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL','BRAVE_WEB_COVERAGE')) THEN RAISE EXCEPTION 'work capability mismatch'; END IF;
 ELSIF TG_TABLE_NAME='supply_discovery_completions' THEN
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NOT supply_filters_valid(jsonb_build_array(NEW.filter),NEW.experiment_id) OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE id=NEW.batch_id AND stage='CONTACT' AND plan->'filters' @> jsonb_build_array(NEW.filter)) OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=(NEW.filter->>'value')::uuid AND mode=NEW.mode) THEN RAISE EXCEPTION 'invalid discovery completion'; END IF;
 ELSIF TG_TABLE_NAME='supply_plan_changes' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_batches batch JOIN supply_feedback brief ON brief.id=batch.feedback_id WHERE batch.id=NEW.batch_id AND batch.plan=NEW.new_plan AND brief.id=NEW.feedback_id AND brief.batch_id=NEW.source_batch_id AND brief.payload->'prior_plan'=NEW.prior_plan) THEN RAISE EXCEPTION 'invalid plan change lineage'; END IF;
 ELSIF TG_TABLE_NAME='supply_outcomes' THEN
  SELECT count(*) INTO total FROM record_current_supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED';
  IF NEW.reason='EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2' AND (NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND slot=2 AND stage='CONTACT') OR (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')>=50 OR EXISTS(SELECT 1 FROM supply_candidates cand LEFT JOIN supply_contacts t ON t.candidate_id=cand.id WHERE cand.experiment_id=NEW.experiment_id AND (t.candidate_id IS NULL OR t.outcome='SOURCE_FAILURE'))) THEN RAISE EXCEPTION 'invalid email shortage'; END IF;
  IF NEW.reason='QUALIFIED_SUPPLY_INSUFFICIENT_AFTER_BATCH_3' AND (NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND slot=3 AND stage='QUALIFICATION') OR EXISTS(SELECT 1 FROM supply_contacts t LEFT JOIN record_current_supply_qualifications q ON q.candidate_id=t.candidate_id WHERE t.experiment_id=NEW.experiment_id AND t.outcome='SUPPORTED' AND q.candidate_id IS NULL)) THEN RAISE EXCEPTION 'invalid qualification shortage'; END IF;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.achieved<>total OR NEW.batches_used<>(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id) OR NEW.businesses_discovered<>(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id) OR NEW.reason='ACTIVE' THEN RAISE EXCEPTION 'invalid outcome facts'; END IF;
 END IF;
 RETURN NEW;
END $$

""")
    op.execute(r"""

CREATE OR REPLACE FUNCTION supply_after_fact() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='supply_batches' THEN
  IF NEW.slot>1 THEN
   INSERT INTO supply_plan_changes SELECT NEW.id,NEW.experiment_id,f.batch_id,f.id,f.payload->'prior_plan',NEW.plan FROM supply_feedback f WHERE f.id=NEW.feedback_id;
  END IF;
 ELSIF TG_TABLE_NAME='supply_outcomes' THEN
  UPDATE supply_plans SET state=NEW.reason WHERE experiment_id=NEW.experiment_id;
  UPDATE supply_candidates SET stopped=true WHERE experiment_id=NEW.experiment_id AND NOT deep_started;
 ELSIF NEW.outcome='QUALIFIED' AND (SELECT count(*) FROM record_current_supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')=50 THEN
  INSERT INTO supply_outcomes SELECT NEW.experiment_id,NEW.fact_id,'TARGET_50_REACHED',50,(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id),(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id);
 END IF;
 RETURN NEW;
END $$

""")
    op.execute(r"""

CREATE FUNCTION record_calibration_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable calibration record'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_calibration_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE proposal record_calibration_proposals; decision record_calibration_decisions;
 acceptance record_offer_acceptances; fulfillment record_calibration_fulfillments;
 obligation record_calibration_obligations;
 qualification record_qualification_decisions; package record_offer_packages;
BEGIN
 IF TG_TABLE_NAME='record_calibration_proposals' THEN
  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
  SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.base_offer_acceptance_id;
  IF acceptance.id IS NULL OR ROW(acceptance.experiment_id,acceptance.offer_id,acceptance.profile_id,acceptance.policy_id)
     IS DISTINCT FROM ROW(NEW.experiment_id,NEW.base_offer_id,NEW.base_profile_id,NEW.base_policy_id)
     OR NEW.base_offer_acceptance_id IS DISTINCT FROM
       (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
  THEN RAISE EXCEPTION 'exact calibration base required'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_proposal_evidence' THEN
  SELECT * INTO proposal FROM record_calibration_proposals WHERE id=NEW.proposal_id;
  SELECT * INTO qualification FROM record_qualification_decisions WHERE id=NEW.decision_id;
  IF proposal.id IS NULL OR qualification.id IS NULL
     OR ROW(qualification.candidate_id,qualification.dossier_id,qualification.matrix_id,qualification.experiment_id,qualification.offer_acceptance_id)
        IS DISTINCT FROM ROW(NEW.candidate_id,NEW.dossier_id,NEW.matrix_id,proposal.experiment_id,proposal.base_offer_acceptance_id)
     OR NEW.finding_code<>proposal.mismatch_code
     OR NOT (NEW.finding_code,qualification.outcome) IN (
       ('TECHNICAL_MISMATCH','REJECTED_TECHNICAL_MISMATCH'),
       ('ECONOMIC_MISMATCH','REJECTED_ECONOMIC_MISMATCH'),
       ('BUYER_MISMATCH','REJECTED_BUYER_MISMATCH'))
     OR NOT NEW.finding_code=ANY(qualification.finding_codes)
  THEN RAISE EXCEPTION 'exact calibration evidence required'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_decisions' THEN
  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
  SELECT * INTO proposal FROM record_calibration_proposals WHERE id=NEW.proposal_id;
  IF proposal.id IS NULL
     OR ROW(NEW.experiment_id,NEW.base_offer_acceptance_id,NEW.base_offer_id,NEW.base_profile_id,NEW.base_policy_id,NEW.evidence_hash)
        IS DISTINCT FROM ROW(proposal.experiment_id,proposal.base_offer_acceptance_id,proposal.base_offer_id,proposal.base_profile_id,proposal.base_policy_id,proposal.evidence_hash)
     OR NOT EXISTS(SELECT 1 FROM record_calibration_proposal_evidence e WHERE e.proposal_id=NEW.proposal_id GROUP BY e.proposal_id HAVING count(*)>=2 AND count(DISTINCT e.candidate_id)>=2)
     OR (NEW.outcome='ACCEPT' AND (EXISTS(SELECT 1 FROM record_qualification_cohorts WHERE experiment_id=NEW.experiment_id)
       OR EXISTS(SELECT 1 FROM record_calibration_decisions WHERE experiment_id=NEW.experiment_id AND outcome='ACCEPT')))
  THEN RAISE EXCEPTION 'invalid calibration decision'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_accepted_affected' THEN
  SELECT * INTO decision FROM record_calibration_decisions WHERE id=NEW.calibration_decision_id;
  SELECT * INTO qualification FROM record_qualification_decisions WHERE id=NEW.previous_decision_id;
  IF decision.id IS NULL OR qualification.id IS NULL OR decision.outcome<>'ACCEPT'
     OR ROW(qualification.candidate_id,qualification.dossier_id,qualification.matrix_id,qualification.experiment_id,qualification.offer_acceptance_id)
        IS DISTINCT FROM ROW(NEW.candidate_id,NEW.previous_dossier_id,NEW.previous_matrix_id,decision.experiment_id,decision.base_offer_acceptance_id)
     OR EXISTS(SELECT 1 FROM record_qualification_decisions later JOIN record_qualification_dossiers later_dossier ON later_dossier.id=later.dossier_id
       JOIN record_qualification_dossiers current_dossier ON current_dossier.id=qualification.dossier_id
       WHERE later.candidate_id=qualification.candidate_id AND later.offer_acceptance_id=decision.base_offer_acceptance_id
       AND later_dossier.version>current_dossier.version)
  THEN RAISE EXCEPTION 'invalid accepted calibration set'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_fulfillments' THEN
  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
  SELECT * INTO decision FROM record_calibration_decisions WHERE id=NEW.calibration_decision_id;
  SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.offer_acceptance_id;
  SELECT * INTO package FROM record_offer_packages WHERE id=acceptance.offer_id;
  IF decision.id IS NULL OR decision.outcome<>'ACCEPT' OR acceptance.id IS NULL OR package.id IS NULL
     OR ROW(NEW.experiment_id,NEW.base_offer_acceptance_id) IS DISTINCT FROM ROW(decision.experiment_id,decision.base_offer_acceptance_id)
     OR ROW(NEW.experiment_id,NEW.offer_id,NEW.profile_id,NEW.policy_id) IS DISTINCT FROM ROW(acceptance.experiment_id,acceptance.offer_id,acceptance.profile_id,acceptance.policy_id)
     OR package.calibration_decision_id IS DISTINCT FROM decision.id OR acceptance.id=decision.base_offer_acceptance_id
     OR acceptance.accepted_at<decision.decided_at
     OR acceptance.id IS DISTINCT FROM (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
     OR EXISTS(SELECT 1 FROM record_qualification_cohorts WHERE experiment_id=NEW.experiment_id)
  THEN RAISE EXCEPTION 'invalid calibration fulfillment'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_obligations' THEN
  SELECT * INTO fulfillment FROM record_calibration_fulfillments WHERE id=NEW.fulfillment_id;
  SELECT * INTO qualification FROM record_qualification_decisions WHERE id=NEW.previous_decision_id;
  IF fulfillment.id IS NULL OR qualification.id IS NULL
     OR ROW(NEW.experiment_id,NEW.required_offer_acceptance_id,NEW.candidate_id,NEW.previous_dossier_id,NEW.previous_matrix_id)
        IS DISTINCT FROM ROW(fulfillment.experiment_id,fulfillment.offer_acceptance_id,qualification.candidate_id,qualification.dossier_id,qualification.matrix_id)
     OR qualification.offer_acceptance_id<>fulfillment.base_offer_acceptance_id
 THEN RAISE EXCEPTION 'invalid requalification obligation'; END IF;
 ELSIF TG_TABLE_NAME='record_calibration_completions' THEN
  SELECT * INTO obligation FROM record_calibration_obligations WHERE id=NEW.obligation_id;
  SELECT * INTO fulfillment FROM record_calibration_fulfillments WHERE id=obligation.fulfillment_id;
  SELECT * INTO qualification FROM record_qualification_decisions WHERE id=NEW.decision_id;
  IF fulfillment.id IS NULL OR qualification.id IS NULL OR qualification.outcome NOT IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE')
     OR ROW(qualification.candidate_id,qualification.experiment_id,qualification.offer_acceptance_id)
        IS DISTINCT FROM ROW(obligation.candidate_id,fulfillment.experiment_id,obligation.required_offer_acceptance_id)
     OR qualification.decided_at<fulfillment.fulfilled_at
  THEN RAISE EXCEPTION 'invalid requalification completion'; END IF;
 END IF;
 RETURN NEW;
END $$;

""")
    op.execute(r"""
CREATE TRIGGER record_calibration_guard BEFORE INSERT ON record_calibration_proposals FOR EACH ROW EXECUTE FUNCTION record_calibration_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_calibration_guard BEFORE INSERT ON record_calibration_proposal_evidence FOR EACH ROW EXECUTE FUNCTION record_calibration_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_calibration_guard BEFORE INSERT ON record_calibration_decisions FOR EACH ROW EXECUTE FUNCTION record_calibration_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_calibration_guard BEFORE INSERT ON record_calibration_fulfillments FOR EACH ROW EXECUTE FUNCTION record_calibration_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_calibration_guard BEFORE INSERT ON record_calibration_accepted_affected FOR EACH ROW EXECUTE FUNCTION record_calibration_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_calibration_guard BEFORE INSERT ON record_calibration_obligations FOR EACH ROW EXECUTE FUNCTION record_calibration_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_calibration_guard BEFORE INSERT ON record_calibration_completions FOR EACH ROW EXECUTE FUNCTION record_calibration_guard()
""")
    op.execute(r"""

CREATE FUNCTION record_readiness_provider_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE call gov_calls; operation supply_operations; proof gov_evidence; retained gov_retained;
BEGIN
 SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id;
 SELECT * INTO operation FROM supply_operations WHERE operation_id=NEW.operation_id;
 SELECT * INTO proof FROM gov_evidence WHERE id=NEW.result_evidence_id;
 IF call.id IS NULL OR operation.operation_id IS NULL OR proof.id IS NULL
    OR call.state<>'FINAL' OR proof.kind<>'PROVIDER_RESULT' OR proof.call_id<>call.id
    OR NEW.experiment_id<>call.experiment_id OR NEW.operation_id<>call.operation_id
    OR NEW.config_id<>call.config_id OR NEW.config_version<>call.config_version
    OR NEW.grant_id<>call.grant_id OR NEW.grant_version<>call.grant_version
    OR NEW.batch_id<>operation.batch_id
    OR NEW.candidate_id IS DISTINCT FROM operation.candidate_id
 THEN RAISE EXCEPTION 'invalid readiness provider lineage'; END IF;
 IF NEW.observed_at>record_org_now() OR NEW.valid_until<=record_org_now() OR NOT EXISTS(
   SELECT 1 FROM gov_grants g JOIN gov_configs cfg ON cfg.id=call.config_id
   JOIN gov_authorities a ON a.account=g.account AND a.capability=g.capability
   WHERE g.id=call.grant_id AND g.version=call.grant_version
     AND g.effective_at<=record_org_now() AND g.expires_at>record_org_now()
     AND NEW.valid_until<=least(g.expires_at,NEW.observed_at+make_interval(secs=>(g.data->>'retention_seconds')::integer))
     AND (g.data->>'outbound_use_permitted')::boolean
     AND (g.data->'storage_fields') @> (cfg.data->'intended_use'->'required_fields')
     AND cfg.data->'intended_use'->>'purpose'=g.data->>'purpose' AND a.enabled
     AND NOT EXISTS(SELECT 1 FROM gov_grants newer WHERE newer.data->>'supersedes_id'=g.id::text AND newer.effective_at<=record_org_now() AND newer.expires_at>record_org_now())
     AND NOT EXISTS(SELECT 1 FROM gov_grant_events e WHERE e.grant_id=g.id AND e.grant_version=g.version AND (e.data->>'effective_at')::timestamptz<=record_org_now() AND e.data->>'kind'<>'ACTIVATED')
 ) THEN RAISE EXCEPTION 'provider source rights unavailable'; END IF;
 IF NEW.retained_id IS NOT NULL THEN
  SELECT * INTO retained FROM gov_retained WHERE id=NEW.retained_id;
  IF retained.id IS NULL OR retained.call_id<>call.id OR retained.grant_id<>call.grant_id
     OR retained.grant_version<>call.grant_version OR retained.expires_at<NEW.valid_until
     OR record_org_source_current(retained.id,retained.field) IS NOT TRUE
  THEN RAISE EXCEPTION 'invalid retained provider lineage'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_readiness_research_plan_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidate supply_candidates; source record_org_recipient_sources; acceptance record_offer_acceptances; artifact record_artifacts;
BEGIN
 SELECT * INTO candidate FROM supply_candidates WHERE id=NEW.candidate_id;
 SELECT * INTO source FROM record_org_recipient_sources WHERE id=NEW.recipient_source_id;
 SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.offer_acceptance_id;
 SELECT * INTO artifact FROM record_artifacts WHERE id=NEW.artifact_id;
 IF candidate.id IS NULL OR source.id IS NULL OR acceptance.id IS NULL OR artifact.id IS NULL
    OR candidate.experiment_id<>NEW.experiment_id OR source.experiment_id<>NEW.experiment_id
    OR source.candidate_id<>NEW.candidate_id OR source.organization_id<>NEW.organization_id OR source.recipient_id<>NEW.recipient_id
    OR acceptance.experiment_id<>NEW.experiment_id OR acceptance.offer_id<>NEW.offer_id OR acceptance.profile_id<>NEW.profile_id OR acceptance.policy_id<>NEW.policy_id
    OR artifact.experiment_id<>NEW.experiment_id OR artifact.kind<>NEW.artifact_kind OR artifact.version<>NEW.artifact_version OR artifact.content_hash<>NEW.artifact_hash
 THEN RAISE EXCEPTION 'invalid research plan lineage'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_readiness_research_run_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE plan record_readiness_research_plans; result record_readiness_provider_results; source supply_references;
BEGIN
 SELECT * INTO plan FROM record_readiness_research_plans WHERE id=NEW.plan_id;
 IF plan.id IS NULL OR plan.experiment_id<>NEW.experiment_id OR plan.candidate_id<>NEW.candidate_id THEN RAISE EXCEPTION 'invalid research run plan'; END IF;
 IF NEW.provider_result_id IS NOT NULL THEN
  SELECT * INTO result FROM record_readiness_provider_results WHERE id=NEW.provider_result_id;
  IF result.id IS NULL OR result.experiment_id<>NEW.experiment_id OR result.candidate_id<>NEW.candidate_id OR result.retained_id IS NULL THEN RAISE EXCEPTION 'invalid provider research provenance'; END IF;
 ELSE
  SELECT * INTO source FROM supply_references WHERE id=NEW.independent_source_id;
  IF source.id IS NULL OR source.experiment_id<>NEW.experiment_id OR source.kind<>'INDEPENDENT_SOURCE' THEN RAISE EXCEPTION 'invalid independent research provenance'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_readiness_evidence_link_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE run record_readiness_research_runs; plan record_readiness_research_plans; dossier record_qualification_dossiers; evidence record_qualification_evidence;
BEGIN
 SELECT * INTO run FROM record_readiness_research_runs WHERE id=NEW.run_id;
 SELECT * INTO dossier FROM record_qualification_dossiers WHERE id=NEW.dossier_id;
 SELECT * INTO evidence FROM record_qualification_evidence WHERE id=NEW.dossier_evidence_id;
 IF run.id IS NULL OR dossier.id IS NULL OR evidence.id IS NULL OR run.experiment_id<>NEW.experiment_id
    OR dossier.experiment_id<>NEW.experiment_id OR evidence.dossier_id<>dossier.id OR dossier.candidate_id<>run.candidate_id THEN RAISE EXCEPTION 'invalid research evidence lineage'; END IF;
 SELECT * INTO plan FROM record_readiness_research_plans WHERE id=run.plan_id;
 IF plan.offer_acceptance_id<>dossier.offer_acceptance_id THEN RAISE EXCEPTION 'stale research evidence offer'; END IF;
 IF run.provider_result_id IS NOT NULL AND evidence.source_ref<>('provider-result:'||run.provider_result_id::text) THEN RAISE EXCEPTION 'provider evidence provenance mismatch'; END IF;
 IF run.independent_source_id IS NOT NULL AND evidence.source_ref<>('independent-source:'||run.independent_source_id::text) THEN RAISE EXCEPTION 'independent evidence provenance mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_readiness_contact_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidate supply_candidates; contact supply_contacts; source record_org_recipient_sources; binding record_org_bindings;
BEGIN
 SELECT * INTO candidate FROM supply_candidates WHERE id=NEW.candidate_id;
 SELECT * INTO contact FROM supply_contacts WHERE candidate_id=NEW.candidate_id;
 IF candidate.id IS NULL OR contact.candidate_id IS NULL OR candidate.experiment_id<>NEW.experiment_id
    OR NEW.valid_until>contact.valid_until THEN RAISE EXCEPTION 'invalid contactability lineage'; END IF;
 IF NEW.provider_result_id IS NULL OR NOT EXISTS(
  SELECT 1 FROM record_readiness_provider_results pr WHERE pr.id=NEW.provider_result_id AND pr.candidate_id=NEW.candidate_id
  AND (EXISTS(SELECT 1 FROM contact_cases cc WHERE cc.candidate_id=NEW.candidate_id AND cc.brave_call_id=pr.call_id)
   OR EXISTS(SELECT 1 FROM contact_attempts a WHERE a.candidate_id=NEW.candidate_id AND a.call_id=pr.call_id AND a.output_fact_id IN (contact.source_id,contact.verification_id)))
 ) THEN RAISE EXCEPTION 'missing governed contact receipt'; END IF;
 IF contact.verification_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM contact_attempts a JOIN contact_operations o ON o.operation_id=a.operation_id
  WHERE a.candidate_id=NEW.candidate_id AND a.output_fact_id=contact.verification_id
  AND o.source_fact_id=contact.source_id AND o.capability='HUNTER_EMAIL_VERIFICATION'
  AND ((NEW.outcome='SUPPORTED_CONTACT_ADDRESS' AND a.outcome='VALID')
   OR (NEW.outcome='EMAIL_NOT_FOUND' AND a.outcome IN ('INVALID','ACCEPT_ALL','UNKNOWN')))
 ) THEN RAISE EXCEPTION 'missing governed verification'; END IF;
 IF NEW.outcome='SUPPORTED_CONTACT_ADDRESS' THEN
  SELECT * INTO source FROM record_org_recipient_sources WHERE id=NEW.recipient_source_id;
  IF source.id IS NULL OR source.experiment_id<>NEW.experiment_id OR source.candidate_id<>NEW.candidate_id
     OR source.organization_id<>NEW.organization_id OR source.recipient_id<>NEW.recipient_id
     OR source.source_fact_id<>NEW.source_fact_id OR contact.outcome<>'SUPPORTED'
     OR contact.source_id<>NEW.source_fact_id OR contact.verification_id IS DISTINCT FROM NEW.verification_fact_id
  THEN RAISE EXCEPTION 'invalid supported contactability'; END IF;
ELSEIF contact.outcome NOT IN ('EMAIL_NOT_FOUND','VERIFICATION_REJECTED') THEN
  RAISE EXCEPTION 'invalid no-email contactability';
 ELSE
  SELECT * INTO binding FROM record_org_bindings WHERE experiment_id=NEW.experiment_id AND identity_id=candidate.identity_id;
  IF binding.id IS NULL OR binding.organization_id<>NEW.organization_id THEN RAISE EXCEPTION 'missing no-email organization'; END IF;
 END IF;
 RETURN NEW;
END $$;

""")
    op.execute(r"""
CREATE TRIGGER record_readiness_provider_guard BEFORE INSERT ON record_readiness_provider_results FOR EACH ROW EXECUTE FUNCTION record_readiness_provider_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_readiness_contact_guard BEFORE INSERT ON record_readiness_contactability_decisions FOR EACH ROW EXECUTE FUNCTION record_readiness_contact_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_readiness_research_plan_guard BEFORE INSERT ON record_readiness_research_plans FOR EACH ROW EXECUTE FUNCTION record_readiness_research_plan_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_readiness_research_run_guard BEFORE INSERT ON record_readiness_research_runs FOR EACH ROW EXECUTE FUNCTION record_readiness_research_run_guard()
""")
    op.execute(r"""
CREATE TRIGGER record_readiness_evidence_link_guard BEFORE INSERT ON record_readiness_evidence_links FOR EACH ROW EXECUTE FUNCTION record_readiness_evidence_link_guard()
""")
    op.execute(r"""
CREATE FUNCTION record_lead_readiness_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable lead readiness record'; END $$;
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_readiness_provider_results FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_readiness_contactability_decisions FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_calibration_proposals FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_readiness_discovery_plans FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_readiness_research_plans FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_calibration_decisions FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_readiness_research_runs FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_calibration_fulfillments FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_readiness_evidence_links FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_calibration_accepted_affected FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_calibration_obligations FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_calibration_proposal_evidence FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
CREATE TRIGGER record_lead_readiness_immutable BEFORE UPDATE OR DELETE ON record_calibration_completions FOR EACH ROW EXECUTE FUNCTION record_lead_readiness_immutable()
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN IF EXISTS(SELECT 1 FROM record_offer_packages WHERE calibration_decision_id IS NOT NULL) OR EXISTS(SELECT 1 FROM record_qualification_decisions d WHERE NOT EXISTS(SELECT 1 FROM supply_qualifications s WHERE s.candidate_id=d.candidate_id AND s.experiment_id=d.experiment_id AND s.fact_id=d.proposal_fact_id)) THEN RAISE EXCEPTION 'lead readiness downgrade requires an empty checkpoint: historical calibration and requalification cannot be represented by the previous schema'; END IF; END $$
""")
    op.execute(r"""
DROP TRIGGER record_offer_calibration_guard ON record_offer_packages
""")
    op.execute(r"""
DROP FUNCTION record_offer_calibration_guard()
""")
    op.execute(r"""
DROP INDEX uq_record_offer_uncalibrated_bundle
""")
    op.execute(r"""
ALTER TABLE record_offer_packages DROP COLUMN calibration_decision_id
""")
    op.execute(r"""
ALTER TABLE record_offer_packages ADD CONSTRAINT record_offer_packages_bundle_id_key UNIQUE(bundle_id)
""")
    op.execute(r"""
DROP TRIGGER record_readiness_draft_guard ON record_outreach_validations
""")
    op.execute(r"""
DROP TRIGGER record_readiness_context_guard ON record_outreach_contexts
""")
    op.execute(r"""
DROP FUNCTION record_readiness_outreach_guard()
""")
    op.execute(r"""
DROP TRIGGER record_readiness_target ON record_qualification_decisions
""")
    op.execute(r"""
DROP FUNCTION record_readiness_target()
""")
    op.execute(r"""
DROP TRIGGER record_readiness_member_guard ON record_qualification_cohort_members
""")
    op.execute(r"""
DROP TRIGGER record_readiness_cohort_guard ON record_qualification_cohorts
""")
    op.execute(r"""
DROP FUNCTION record_readiness_cohort_guard()
""")
    op.execute(r"""

CREATE OR REPLACE FUNCTION record_qualification_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d record_qualification_dossiers; m record_qualification_matrices; decision record_qualification_decisions; cohort record_qualification_cohorts; acceptance record_offer_acceptances; result_count integer; criterion_count integer;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable qualification record'; END IF;
 IF TG_TABLE_NAME='record_qualification_dossiers' THEN
  SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.offer_acceptance_id;
  IF ROW(acceptance.experiment_id,acceptance.offer_id,acceptance.profile_id,acceptance.policy_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.offer_id,NEW.profile_id,NEW.policy_id)
   OR NOT EXISTS(SELECT 1 FROM supply_candidates c JOIN record_org_bindings b ON b.identity_id=c.identity_id AND b.id=NEW.binding_id JOIN record_org_admissions a ON a.binding_id=b.id AND a.id=NEW.admission_id JOIN record_org_recipient_sources r ON r.binding_id=b.id AND r.candidate_id=c.id AND r.id=NEW.recipient_source_id WHERE c.id=NEW.candidate_id AND c.experiment_id=NEW.experiment_id AND b.organization_id=NEW.organization_id AND r.recipient_id=NEW.recipient_id)
  THEN RAISE EXCEPTION 'exact dossier lineage required'; END IF;
 ELSIF TG_TABLE_NAME='record_qualification_matrices' THEN
  SELECT * INTO d FROM record_qualification_dossiers WHERE id=NEW.dossier_id;
  IF ROW(d.experiment_id,d.candidate_id,d.organization_id,d.recipient_id,d.recipient_source_id,d.offer_acceptance_id,d.offer_id,d.profile_id,d.policy_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.candidate_id,NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id,NEW.offer_acceptance_id,NEW.offer_id,NEW.profile_id,NEW.policy_id) THEN RAISE EXCEPTION 'exact matrix lineage required'; END IF;
 ELSIF TG_TABLE_NAME='record_qualification_decisions' THEN
  SELECT * INTO m FROM record_qualification_matrices WHERE id=NEW.matrix_id;
  SELECT count(*) INTO result_count FROM record_qualification_criterion_results r WHERE r.matrix_id=NEW.matrix_id AND EXISTS(SELECT 1 FROM record_qualification_result_evidence e WHERE e.matrix_id=r.matrix_id AND e.criterion_code=r.criterion_code);
  SELECT count(*) INTO criterion_count FROM record_qualification_criteria WHERE profile_id=NEW.profile_id;
  IF ROW(m.experiment_id,m.dossier_id,m.candidate_id,m.organization_id,m.recipient_id,m.recipient_source_id,m.offer_acceptance_id,m.offer_id,m.profile_id,m.policy_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.dossier_id,NEW.candidate_id,NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id,NEW.offer_acceptance_id,NEW.offer_id,NEW.profile_id,NEW.policy_id)
   OR result_count<>criterion_count
   OR NEW.offer_acceptance_id IS DISTINCT FROM (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
   OR (NEW.outcome IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE') AND EXISTS(SELECT 1 FROM record_qualification_criterion_results r JOIN record_qualification_criteria c ON c.profile_id=r.profile_id AND c.code=r.criterion_code WHERE r.matrix_id=NEW.matrix_id AND ((c.rule_kind='HARD_GATE' AND r.status<>'SATISFIED') OR (c.rule_kind='FATAL_DISQUALIFIER' AND r.status<>'NOT_SATISFIED'))))
   OR (NEW.outcome='PILOT_FIT_CONTACTABLE' AND NOT EXISTS(SELECT 1 FROM record_qualification_criterion_results r JOIN record_qualification_criteria c ON c.profile_id=r.profile_id AND c.code=r.criterion_code WHERE r.matrix_id=NEW.matrix_id AND c.category='PILOT_FIT' AND r.status='SATISFIED'))
   OR NOT EXISTS(SELECT 1 FROM supply_qualifications sq WHERE sq.candidate_id=NEW.candidate_id AND sq.experiment_id=NEW.experiment_id AND sq.fact_id=NEW.proposal_fact_id AND ((NEW.outcome IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE') AND sq.outcome='QUALIFIED') OR (NEW.outcome NOT IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE') AND sq.outcome<>'QUALIFIED')))
  THEN RAISE EXCEPTION 'complete authoritative qualification required'; END IF;
 ELSIF TG_TABLE_NAME='record_qualification_cohorts' THEN
  SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.offer_acceptance_id;
  IF ROW(acceptance.experiment_id,acceptance.offer_id,acceptance.profile_id,acceptance.policy_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.offer_id,NEW.profile_id,NEW.policy_id)
   OR NEW.offer_acceptance_id IS DISTINCT FROM (SELECT id FROM record_offer_acceptances WHERE experiment_id=NEW.experiment_id ORDER BY accepted_at DESC,id DESC LIMIT 1)
  THEN RAISE EXCEPTION 'exact cohort offer required'; END IF;
 ELSIF TG_TABLE_NAME='record_qualification_cohort_members' THEN
  SELECT * INTO decision FROM record_qualification_decisions WHERE id=NEW.decision_id;
  SELECT * INTO cohort FROM record_qualification_cohorts WHERE id=NEW.cohort_id;
  IF decision.outcome NOT IN ('QUALIFIED_CONTACTABLE','PILOT_FIT_CONTACTABLE') OR decision.valid_until<=record_org_now()
   OR ROW(decision.experiment_id,decision.candidate_id,decision.organization_id,decision.recipient_id,decision.recipient_source_id) IS DISTINCT FROM ROW(NEW.experiment_id,NEW.candidate_id,NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id)
   OR ROW(decision.experiment_id,decision.offer_acceptance_id,decision.offer_id,decision.profile_id,decision.policy_id) IS DISTINCT FROM ROW(cohort.experiment_id,cohort.offer_acceptance_id,cohort.offer_id,cohort.profile_id,cohort.policy_id)
   OR NOT EXISTS(SELECT 1 FROM record_org_reservations r WHERE r.id=NEW.reservation_id AND ROW(r.experiment_id,r.organization_id,r.recipient_id,r.source_id)=ROW(NEW.experiment_id,NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id))
  THEN RAISE EXCEPTION 'invalid cohort member'; END IF;
 END IF;
 RETURN NEW;
END $$;

""")
    op.execute(r"""

CREATE OR REPLACE FUNCTION supply_feedback_payload(batch uuid, gate text) RETURNS jsonb LANGUAGE sql STABLE AS $$
 WITH b AS (SELECT * FROM supply_batches WHERE id=batch), results AS (
  SELECT c.id,c.observations,CASE WHEN gate='EMAIL' THEN coalesce(t.outcome,'PENDING') ELSE coalesce(q.outcome,t.outcome,'PENDING') END reason
  FROM supply_candidates c JOIN b ON b.experiment_id=c.experiment_id LEFT JOIN supply_contacts t ON t.candidate_id=c.id LEFT JOIN supply_qualifications q ON q.candidate_id=c.id
 ), reasons AS (SELECT reason,count(*) n FROM results GROUP BY reason), performance AS (
  SELECT f->>'dimension' dimension,f->>'value' value,reason,count(*) n FROM results CROSS JOIN LATERAL jsonb_array_elements(observations) f GROUP BY 1,2,3
  UNION ALL SELECT dc.filter->>'dimension',dc.filter->>'value','QUERY_YIELD_SHORTFALL',(SELECT count(*) FROM results WHERE observations @> jsonb_build_array(dc.filter)) FROM supply_discovery_completions dc WHERE dc.batch_id=batch AND gate='EMAIL' AND (SELECT count(*) FROM results WHERE reason='SUPPORTED')<50
 )
 SELECT jsonb_build_object('prior_plan',b.plan,'deficit',50-(SELECT count(*) FROM results WHERE reason=CASE WHEN gate='EMAIL' THEN 'SUPPORTED' ELSE 'QUALIFIED' END),
 'reasons',coalesce((SELECT jsonb_agg(jsonb_build_object('reason',reason,'count',n) ORDER BY reason) FROM reasons),'[]'::jsonb),
 'performance',coalesce((SELECT jsonb_agg(jsonb_build_object('dimension',dimension,'value',value,'reason',reason,'count',n) ORDER BY dimension,value,reason) FROM performance),'[]'::jsonb)) FROM b
$$

""")
    op.execute(r"""

CREATE OR REPLACE FUNCTION supply_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p supply_plans; b supply_batches; i supply_identities; f supply_facts; v supply_facts; cl supply_facts; c supply_candidates; fb supply_feedback; op gov_operations; cfg gov_configs; payload jsonb; expected text; total integer; item jsonb; prior jsonb; diff jsonb; dim text;
BEGIN
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF TG_OP='UPDATE' THEN
  IF TG_TABLE_NAME='supply_plans' THEN
   IF (to_jsonb(NEW)-'state')<>(to_jsonb(OLD)-'state') OR OLD.state<>'ACTIVE' OR NOT EXISTS(SELECT 1 FROM supply_outcomes WHERE experiment_id=NEW.experiment_id AND reason=NEW.state) THEN RAISE EXCEPTION 'invalid supply transition'; END IF;
  ELSIF TG_TABLE_NAME='supply_batches' THEN
   IF (to_jsonb(NEW)-ARRAY['stage','completed_at'])<>(to_jsonb(OLD)-ARRAY['stage','completed_at']) OR (OLD.completed_at IS NOT NULL AND NEW.completed_at IS DISTINCT FROM OLD.completed_at) OR NOT ((OLD.stage='CONTACT' AND NEW.stage IN ('EMAIL_RETRY_READY','QUALIFICATION','DONE')) OR (OLD.stage='QUALIFICATION' AND NEW.stage IN ('QUALIFICATION_RETRY_READY','DONE'))) THEN RAISE EXCEPTION 'invalid batch transition'; END IF;
   IF OLD.stage='CONTACT' AND EXISTS(SELECT 1 FROM supply_candidates cand LEFT JOIN supply_contacts t ON t.candidate_id=cand.id WHERE cand.batch_id=NEW.id AND (t.candidate_id IS NULL OR t.outcome='SOURCE_FAILURE')) THEN RAISE EXCEPTION 'unresolved contact gate'; END IF;
   IF NEW.stage='QUALIFICATION' AND (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')<50 THEN RAISE EXCEPTION 'email shortage'; END IF;
   IF NEW.stage IN ('EMAIL_RETRY_READY','QUALIFICATION_RETRY_READY') AND NOT EXISTS(SELECT 1 FROM supply_feedback WHERE batch_id=NEW.id AND gate=CASE WHEN NEW.stage='EMAIL_RETRY_READY' THEN 'EMAIL' ELSE 'QUALIFICATION' END) THEN RAISE EXCEPTION 'missing feedback'; END IF;
  ELSIF TG_TABLE_NAME='supply_candidates' THEN
   IF (to_jsonb(NEW)-ARRAY['deep_started','stopped'])<>(to_jsonb(OLD)-ARRAY['deep_started','stopped']) OR (OLD.deep_started AND NOT NEW.deep_started) OR (OLD.stopped AND NOT NEW.stopped) THEN RAISE EXCEPTION 'immutable candidate intent'; END IF;
   IF NEW.deep_started AND NOT OLD.deep_started THEN
    IF NEW.stopped OR NOT EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE') OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=NEW.id AND outcome='SUPPORTED') OR (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')<50 OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND stage='QUALIFICATION') THEN RAISE EXCEPTION 'deep work denied'; END IF;
   END IF;
  ELSE RAISE EXCEPTION 'immutable supply fact'; END IF;
  RETURN NEW;
 END IF;
 SELECT * INTO p FROM supply_plans WHERE experiment_id=NEW.experiment_id;
 IF TG_TABLE_NAME='supply_plans' THEN
  IF NEW.state<>'ACTIVE' OR NOT supply_plan_valid(NEW.initial_plan,NEW.experiment_id) OR NOT supply_filters_valid(NEW.allowed,NEW.experiment_id) OR NOT NEW.allowed @> (NEW.initial_plan->'filters') OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.verification_policy_id AND kind='VERIFICATION_POLICY') THEN RAISE EXCEPTION 'invalid supply plan'; END IF;
 ELSIF TG_TABLE_NAME='supply_identities' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.provenance_ref AND experiment_id=NEW.experiment_id AND kind='INDEPENDENT_SOURCE' AND mode=NEW.mode) THEN RAISE EXCEPTION 'missing permitted provenance'; END IF;
 ELSIF TG_TABLE_NAME='supply_facts' THEN
  SELECT * INTO i FROM supply_identities WHERE id=NEW.identity_id;
  IF i.mode<>NEW.mode THEN RAISE EXCEPTION 'mixed evidence mode'; END IF;
  IF NEW.kind='SOURCE_EMAIL' AND NEW.contact_ref<>NEW.id THEN RAISE EXCEPTION 'source contact identity'; END IF;
  IF NEW.kind IN ('VERIFIED','VERIFICATION_REJECTED') AND (NOT EXISTS(SELECT 1 FROM supply_facts WHERE id=NEW.contact_ref AND identity_id=NEW.identity_id AND kind='SOURCE_EMAIL' AND observed_at<=NEW.observed_at) OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.policy_ref AND kind='VERIFICATION_POLICY')) THEN RAISE EXCEPTION 'invalid verification lineage'; END IF;
  IF NEW.kind IN ('QUALIFIED','REJECTED_FIT','REJECTED_EVIDENCE') AND NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.policy_ref AND kind='QUALIFICATION_RULE') THEN RAISE EXCEPTION 'invalid qualification rule'; END IF;
 ELSIF TG_TABLE_NAME='supply_batches' THEN
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.stage<>'CONTACT' OR NOT supply_plan_valid(NEW.plan,NEW.experiment_id) OR NOT p.allowed @> (NEW.plan->'filters') OR NEW.plan->>'qualification_rule_id'<>p.initial_plan->>'qualification_rule_id' THEN RAISE EXCEPTION 'invalid batch plan'; END IF;
  IF NEW.slot=1 THEN
   IF EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id) OR NEW.plan<>p.initial_plan THEN RAISE EXCEPTION 'initial batch conflict'; END IF;
  ELSE
   SELECT * INTO b FROM supply_batches WHERE experiment_id=NEW.experiment_id ORDER BY slot DESC LIMIT 1;
   SELECT * INTO fb FROM supply_feedback WHERE id=NEW.feedback_id;
   IF fb.experiment_id IS DISTINCT FROM NEW.experiment_id OR fb.batch_id IS DISTINCT FROM b.id OR fb.payload IS DISTINCT FROM supply_feedback_payload(b.id,fb.gate) OR (NEW.slot=2 AND (b.slot<>1 OR b.stage<>'EMAIL_RETRY_READY' OR fb.gate<>'EMAIL')) OR (NEW.slot=3 AND (b.slot NOT IN (1,2) OR b.stage<>'QUALIFICATION_RETRY_READY' OR fb.gate<>'QUALIFICATION')) THEN RAISE EXCEPTION 'stale or wrong feedback'; END IF;
   prior:=b.plan->'filters'; diff:='[]'::jsonb;
   FOR item IN SELECT value FROM jsonb_array_elements(prior || (NEW.plan->'filters')) LOOP
    IF (prior @> jsonb_build_array(item)) <> ((NEW.plan->'filters') @> jsonb_build_array(item)) THEN diff:=diff || jsonb_build_array(item); END IF;
   END LOOP;
   IF jsonb_array_length(diff)=0 THEN RAISE EXCEPTION 'cosmetic plan change'; END IF;
   FOR item IN SELECT * FROM jsonb_array_elements(diff) LOOP
    dim:=item->>'dimension';
    IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(fb.payload->'performance') x WHERE x->>'dimension'=dim AND x->>'reason' NOT IN ('SUPPORTED','QUALIFIED','PENDING','SOURCE_FAILURE') AND EXISTS(SELECT 1 FROM jsonb_array_elements(prior) y WHERE y->>'dimension'=dim AND y->>'value'=x->>'value')) THEN RAISE EXCEPTION 'unjustified plan change'; END IF;
   END LOOP;
  END IF;
 ELSIF TG_TABLE_NAME='supply_candidates' THEN
  SELECT * INTO b FROM supply_batches WHERE id=NEW.batch_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.clearance_id;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR b.stage<>'CONTACT' OR f.kind NOT IN ('IDENTITY_CLEAR','IDENTITY_EXCLUDED') OR NEW.deep_started OR NEW.stopped OR NOT supply_filters_valid(NEW.observations,NEW.experiment_id) OR NOT (b.plan->'filters') @> NEW.observations OR NEW.ordinal<>(SELECT count(*)+1 FROM supply_candidates WHERE batch_id=NEW.batch_id) THEN RAISE EXCEPTION 'candidate admission denied'; END IF;
 ELSIF TG_TABLE_NAME='supply_contacts' THEN
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO b FROM supply_batches WHERE id=c.batch_id;
  SELECT * INTO i FROM supply_identities WHERE id=c.identity_id;
  SELECT * INTO cl FROM supply_facts WHERE id=c.clearance_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.source_id;
  SELECT * INTO v FROM supply_facts WHERE id=NEW.verification_id;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR b.stage<>'CONTACT' OR f.identity_id<>c.identity_id THEN RAISE EXCEPTION 'contact scope or phase'; END IF;
  expected:=CASE WHEN cl.kind='IDENTITY_EXCLUDED' AND f.id=cl.id THEN 'IDENTITY_EXCLUDED' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='EMAIL_ABSENT' THEN 'EMAIL_NOT_FOUND' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='SOURCE_FAILURE' THEN 'SOURCE_FAILURE' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='SOURCE_EMAIL' AND v.identity_id=c.identity_id AND v.contact_ref=f.id AND v.policy_ref=p.verification_policy_id THEN CASE v.kind WHEN 'VERIFIED' THEN 'SUPPORTED' WHEN 'VERIFICATION_REJECTED' THEN 'VERIFICATION_REJECTED' END END;
  IF expected IS NULL OR NEW.outcome<>expected OR (NEW.verification_id IS NOT NULL)<>(expected IN ('SUPPORTED','VERIFICATION_REJECTED')) OR NEW.resolved_at<greatest(i.observed_at,cl.observed_at,f.observed_at,coalesce(v.observed_at,f.observed_at)) OR NEW.resolved_at>=NEW.valid_until OR NEW.valid_until<>least(i.valid_until,cl.valid_until,f.valid_until,coalesce(v.valid_until,f.valid_until)) THEN RAISE EXCEPTION 'invalid contact evidence'; END IF;
 ELSIF TG_TABLE_NAME='supply_contact_failures' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_candidates cand JOIN supply_facts proof ON proof.id=NEW.source_id AND proof.identity_id=cand.identity_id WHERE cand.id=NEW.candidate_id AND proof.kind='SOURCE_FAILURE') THEN RAISE EXCEPTION 'invalid failure lineage'; END IF;
 ELSIF TG_TABLE_NAME='supply_qualifications' THEN
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.fact_id;
  IF NOT f.observed_at<=NEW.accepted_at OR NEW.accepted_at>=f.valid_until OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=c.id AND resolved_at<=NEW.accepted_at AND valid_until>NEW.accepted_at) OR EXISTS(SELECT 1 FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND accepted_at>NEW.accepted_at) OR EXISTS(SELECT 1 FROM supply_qualifications q JOIN supply_facts proof ON proof.id=q.fact_id JOIN supply_contacts t ON t.candidate_id=q.candidate_id WHERE q.experiment_id=NEW.experiment_id AND q.outcome='QUALIFIED' AND (proof.valid_until<=NEW.accepted_at OR t.valid_until<=NEW.accepted_at)) THEN RAISE EXCEPTION 'expired accepted evidence'; END IF;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NOT c.deep_started OR c.stopped OR f.identity_id<>c.identity_id OR f.kind<>NEW.outcome OR f.policy_ref::text<>p.initial_plan->>'qualification_rule_id' OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=c.id AND outcome='SUPPORTED') OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND stage='QUALIFICATION') OR (NEW.outcome='QUALIFIED' AND (SELECT count(*) FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')>=50) THEN RAISE EXCEPTION 'qualification denied'; END IF;
 ELSIF TG_TABLE_NAME='supply_feedback' THEN
  SELECT * INTO b FROM supply_batches WHERE id=NEW.batch_id;
  payload:=supply_feedback_payload(NEW.batch_id,NEW.gate);
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.payload IS DISTINCT FROM payload OR (payload->>'deficit')::int NOT BETWEEN 1 AND 50 OR b.slot=3 OR (NEW.gate='EMAIL' AND (b.slot<>1 OR b.stage<>'CONTACT')) OR (NEW.gate='QUALIFICATION' AND b.stage<>'QUALIFICATION') OR EXISTS(SELECT 1 FROM jsonb_array_elements(payload->'reasons') x WHERE x->>'reason' IN ('PENDING','SOURCE_FAILURE') OR (NEW.gate='QUALIFICATION' AND x->>'reason'='SUPPORTED')) THEN RAISE EXCEPTION 'incomplete or malformed feedback'; END IF;
 ELSIF TG_TABLE_NAME='supply_operations' THEN
  SELECT * INTO op FROM gov_operations WHERE id=NEW.operation_id;
  SELECT * INTO cfg FROM gov_configs WHERE id=NEW.config_id;
  IF op.gate_kind IS DISTINCT FROM (CASE WHEN NEW.kind='CONTACT' THEN 'CONTACT' ELSE 'SUPPLY' END) OR p.state IS DISTINCT FROM 'ACTIVE' THEN RAISE EXCEPTION 'unbound supply gate'; END IF;
  IF (NEW.kind='DISCOVERY' AND cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','BRAVE_WEB_COVERAGE')) OR (NEW.kind='CONTACT' AND cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT','HUNTER_EMAIL_VERIFICATION','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL')) OR (NEW.kind='DEEP' AND cfg.capability NOT IN ('OPENAI_GENERATE','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL','BRAVE_WEB_COVERAGE')) THEN RAISE EXCEPTION 'work capability mismatch'; END IF;
 ELSIF TG_TABLE_NAME='supply_discovery_completions' THEN
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NOT supply_filters_valid(jsonb_build_array(NEW.filter),NEW.experiment_id) OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE id=NEW.batch_id AND stage='CONTACT' AND plan->'filters' @> jsonb_build_array(NEW.filter)) OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=(NEW.filter->>'value')::uuid AND mode=NEW.mode) THEN RAISE EXCEPTION 'invalid discovery completion'; END IF;
 ELSIF TG_TABLE_NAME='supply_plan_changes' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_batches batch JOIN supply_feedback brief ON brief.id=batch.feedback_id WHERE batch.id=NEW.batch_id AND batch.plan=NEW.new_plan AND brief.id=NEW.feedback_id AND brief.batch_id=NEW.source_batch_id AND brief.payload->'prior_plan'=NEW.prior_plan) THEN RAISE EXCEPTION 'invalid plan change lineage'; END IF;
 ELSIF TG_TABLE_NAME='supply_outcomes' THEN
  SELECT count(*) INTO total FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED';
  IF NEW.reason='EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2' AND (NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND slot=2 AND stage='CONTACT') OR (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')>=50 OR EXISTS(SELECT 1 FROM supply_candidates cand LEFT JOIN supply_contacts t ON t.candidate_id=cand.id WHERE cand.experiment_id=NEW.experiment_id AND (t.candidate_id IS NULL OR t.outcome='SOURCE_FAILURE'))) THEN RAISE EXCEPTION 'invalid email shortage'; END IF;
  IF NEW.reason='QUALIFIED_SUPPLY_INSUFFICIENT_AFTER_BATCH_3' AND (NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND slot=3 AND stage='QUALIFICATION') OR EXISTS(SELECT 1 FROM supply_contacts t LEFT JOIN supply_qualifications q ON q.candidate_id=t.candidate_id WHERE t.experiment_id=NEW.experiment_id AND t.outcome='SUPPORTED' AND q.candidate_id IS NULL)) THEN RAISE EXCEPTION 'invalid qualification shortage'; END IF;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.achieved<>total OR NEW.batches_used<>(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id) OR NEW.businesses_discovered<>(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id) OR NEW.reason='ACTIVE' THEN RAISE EXCEPTION 'invalid outcome facts'; END IF;
 END IF;
 RETURN NEW;
END $$

""")
    op.execute(r"""

CREATE OR REPLACE FUNCTION supply_after_fact() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='supply_batches' THEN
  IF NEW.slot>1 THEN
   INSERT INTO supply_plan_changes SELECT NEW.id,NEW.experiment_id,f.batch_id,f.id,f.payload->'prior_plan',NEW.plan FROM supply_feedback f WHERE f.id=NEW.feedback_id;
  END IF;
 ELSIF TG_TABLE_NAME='supply_outcomes' THEN
  UPDATE supply_plans SET state=NEW.reason WHERE experiment_id=NEW.experiment_id;
  UPDATE supply_candidates SET stopped=true WHERE experiment_id=NEW.experiment_id AND NOT deep_started;
 ELSIF NEW.outcome='QUALIFIED' AND (SELECT count(*) FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')=50 THEN
  INSERT INTO supply_outcomes SELECT NEW.experiment_id,NEW.fact_id,'TARGET_50_REACHED',50,(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id),(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id);
 END IF;
 RETURN NEW;
END $$

""")
    op.execute(r"""
DROP VIEW record_current_supply_qualifications
""")
    op.execute(r"""
ALTER TABLE record_qualification_decisions DROP CONSTRAINT fk_qualification_proposal_fact
""")
    op.execute(r"""
ALTER TABLE record_qualification_decisions ADD CONSTRAINT record_qualification_decision_candidate_id_experiment_id_p_fkey FOREIGN KEY(candidate_id,experiment_id,proposal_fact_id) REFERENCES supply_qualifications(candidate_id,experiment_id,fact_id)
""")
    op.execute(r"""
DROP TABLE record_calibration_completions
""")
    op.execute(r"""
DROP TABLE record_calibration_proposal_evidence
""")
    op.execute(r"""
DROP TABLE record_calibration_obligations
""")
    op.execute(r"""
DROP TABLE record_calibration_accepted_affected
""")
    op.execute(r"""
DROP TABLE record_readiness_evidence_links
""")
    op.execute(r"""
DROP TABLE record_calibration_fulfillments
""")
    op.execute(r"""
DROP TABLE record_readiness_research_runs
""")
    op.execute(r"""
DROP TABLE record_calibration_decisions
""")
    op.execute(r"""
DROP TABLE record_readiness_research_plans
""")
    op.execute(r"""
DROP TABLE record_readiness_discovery_plans
""")
    op.execute(r"""
DROP TABLE record_calibration_proposals
""")
    op.execute(r"""
DROP TABLE record_readiness_contactability_decisions
""")
    op.execute(r"""
DROP TABLE record_readiness_provider_results
""")
    op.execute(r"""
DROP FUNCTION record_lead_readiness_immutable()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_calibration_guard()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_calibration_immutable()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_readiness_provider_guard()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_readiness_contact_guard()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_calibration_immutable()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_calibration_guard()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_readiness_provider_guard()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_readiness_research_plan_guard()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_readiness_research_run_guard()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_readiness_evidence_link_guard()
""")
    op.execute(r"""
DROP FUNCTION IF EXISTS record_readiness_contact_guard()
""")
