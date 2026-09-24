"""Exact offer design, commercial envelope, and accepted offer records.

Revision ID: 20260913_07
Revises: 20260913_06
"""

from alembic import op

revision = "20260913_07"
down_revision = "20260913_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
ALTER TABLE record_artifacts DROP CONSTRAINT record_artifacts_kind_check;
ALTER TABLE record_artifacts ADD CHECK(kind IN (
 'EXPERIMENT_BRIEF','IDEA_SEED','IDEA_CANDIDATE','IDEA_BRIEF','RESEARCH_PLAN','RESEARCH_EVIDENCE',
 'COMPETITOR_PROFILE','SERVICE_PROFILE','PRICE_OBSERVATION','MARKET_RESEARCH_REPORT',
 'MARKET_RESEARCH_RECOMMENDATION','RESEARCH_FEEDBACK_BRIEF','OFFER_RESEARCH_GAP_BRIEF',
 'DELIVERY_SCOPE_ESTIMATE','OFFER_DESIGN_INPUT_BUNDLE','COMMERCIAL_DESIGN_ENVELOPE',
 'OFFER_DESIGN_PROPOSAL','OFFER_PACKAGE','OFFER_QUALIFICATION_PROFILE','INITIAL_OUTREACH_POLICY',
 'VALIDATION_RESULT','ACCEPTANCE_RECEIPT'));

CREATE TABLE record_offer_bundles (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, artifact_id uuid NOT NULL,
 artifact_kind varchar(64) NOT NULL CHECK(artifact_kind='OFFER_DESIGN_INPUT_BUNDLE'),
 artifact_version integer NOT NULL, artifact_hash varchar(64) NOT NULL,
 idea_acceptance_id uuid NOT NULL, idea_artifact_id uuid NOT NULL, verdict_id uuid NOT NULL,
 report_artifact_id uuid NOT NULL, created_at timestamptz NOT NULL,
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(idea_acceptance_id) REFERENCES record_idea_acceptances(id),
 FOREIGN KEY(verdict_id) REFERENCES record_verdicts(id),
 UNIQUE(id,experiment_id), UNIQUE(artifact_id), UNIQUE(verdict_id)
);
CREATE TABLE record_offer_bundle_inputs (
 bundle_id uuid NOT NULL, experiment_id uuid NOT NULL, role varchar(64) NOT NULL,
 artifact_id uuid NOT NULL, artifact_kind varchar(64) NOT NULL, artifact_version integer NOT NULL,
 artifact_hash varchar(64) NOT NULL, PRIMARY KEY(bundle_id,role,artifact_id),
 FOREIGN KEY(bundle_id,experiment_id) REFERENCES record_offer_bundles(id,experiment_id),
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 CHECK(role ~ '^[A-Z][A-Z0-9_]{0,63}$')
);
CREATE TABLE record_commercial_envelopes (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, artifact_id uuid NOT NULL,
 artifact_kind varchar(64) NOT NULL CHECK(artifact_kind='COMMERCIAL_DESIGN_ENVELOPE'),
 artifact_version integer NOT NULL, artifact_hash varchar(64) NOT NULL, bundle_id uuid NOT NULL,
 operator_profile_id uuid NOT NULL, operator_profile_version integer NOT NULL, scope_artifact_id uuid NOT NULL,
 status varchar(32) NOT NULL CHECK(status IN ('READY','IMPOSSIBLE_ECONOMICS','CURRENCY_MISMATCH','DELIVERY_CAPACITY_EXCEEDED')),
 currency varchar(3) NOT NULL, service_hours numeric(18,2) NOT NULL,
 delivery_cost numeric(18,2), minimum_price numeric(18,2), minimum_margin_rate numeric(8,6) NOT NULL,
 maximum_discount_rate numeric(8,6) NOT NULL, minimum_deposit_rate numeric(8,6) NOT NULL,
 created_at timestamptz NOT NULL,
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(bundle_id,experiment_id) REFERENCES record_offer_bundles(id,experiment_id),
 FOREIGN KEY(operator_profile_id,operator_profile_version) REFERENCES record_operator_profiles(id,version),
 UNIQUE(id,experiment_id), UNIQUE(artifact_id), UNIQUE(bundle_id),
 CHECK((status='READY' AND delivery_cost IS NOT NULL AND minimum_price IS NOT NULL) OR (status<>'READY' AND delivery_cost IS NULL AND minimum_price IS NULL))
);
CREATE TABLE record_offer_proposals (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, artifact_id uuid NOT NULL,
 artifact_kind varchar(64) NOT NULL CHECK(artifact_kind='OFFER_DESIGN_PROPOSAL'),
 artifact_version integer NOT NULL, artifact_hash varchar(64) NOT NULL,
 bundle_id uuid NOT NULL, envelope_id uuid NOT NULL, created_at timestamptz NOT NULL,
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(bundle_id,experiment_id) REFERENCES record_offer_bundles(id,experiment_id),
 FOREIGN KEY(envelope_id,experiment_id) REFERENCES record_commercial_envelopes(id,experiment_id),
 UNIQUE(id,experiment_id), UNIQUE(artifact_id)
);
CREATE TABLE record_offer_proposal_invalidations (
 proposal_id uuid PRIMARY KEY, experiment_id uuid NOT NULL, superseding_bundle_id uuid NOT NULL,
 reason varchar(64) NOT NULL CHECK(reason='SUPERSEDED_RESEARCH'), created_at timestamptz NOT NULL,
 FOREIGN KEY(proposal_id,experiment_id) REFERENCES record_offer_proposals(id,experiment_id),
 FOREIGN KEY(superseding_bundle_id,experiment_id) REFERENCES record_offer_bundles(id,experiment_id)
);
CREATE TABLE record_offer_packages (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, artifact_id uuid NOT NULL,
 artifact_kind varchar(64) NOT NULL CHECK(artifact_kind='OFFER_PACKAGE'), artifact_version integer NOT NULL,
 artifact_hash varchar(64) NOT NULL, proposal_id uuid NOT NULL, bundle_id uuid NOT NULL,
 envelope_id uuid NOT NULL, currency varchar(3) NOT NULL, base_price numeric(18,2) NOT NULL,
 created_at timestamptz NOT NULL,
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(proposal_id,experiment_id) REFERENCES record_offer_proposals(id,experiment_id),
 UNIQUE(id,experiment_id), UNIQUE(artifact_id), UNIQUE(proposal_id), UNIQUE(bundle_id)
);
CREATE TABLE record_offer_field_sources (
 offer_id uuid NOT NULL, experiment_id uuid NOT NULL, bundle_id uuid NOT NULL, field_path varchar(64) NOT NULL,
 source_artifact_id uuid, source_kind varchar(64), source_role varchar(64), source_version integer, source_hash varchar(64),
 operator_constraint varchar(32), PRIMARY KEY(offer_id,field_path),
 FOREIGN KEY(offer_id,experiment_id) REFERENCES record_offer_packages(id,experiment_id),
 FOREIGN KEY(bundle_id,experiment_id) REFERENCES record_offer_bundles(id,experiment_id),
 FOREIGN KEY(bundle_id,source_role,source_artifact_id) REFERENCES record_offer_bundle_inputs(bundle_id,role,artifact_id),
 FOREIGN KEY(source_artifact_id,experiment_id,source_kind,source_version,source_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 CHECK((source_artifact_id IS NOT NULL AND source_kind IS NOT NULL AND source_role IS NOT NULL AND source_version IS NOT NULL AND source_hash IS NOT NULL AND operator_constraint IS NULL) OR
       (source_artifact_id IS NULL AND source_kind IS NULL AND source_role IS NULL AND source_version IS NULL AND source_hash IS NULL AND operator_constraint IS NOT NULL)),
 CHECK(field_path IN ('target_customer','buyer','problem','solution_mechanism','credible_outcome','positioning','scope','deliverables','exclusions','prerequisites','timeline','customer_responsibilities','currency','base_price','pilot_terms','third_party_costs','payment_terms','validity','claims','ideal_fit','disqualifiers','negotiation_variables')),
 CHECK(operator_constraint IS NULL OR operator_constraint IN ('CURRENCY','DELIVERY_CAPACITY','HOURLY_COST','MINIMUM_PRICE','MINIMUM_MARGIN_RATE','MAXIMUM_DISCOUNT_RATE','MINIMUM_DEPOSIT_RATE'))
);
CREATE TABLE record_offer_qualification_profiles (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, artifact_id uuid NOT NULL,
 artifact_kind varchar(64) NOT NULL CHECK(artifact_kind='OFFER_QUALIFICATION_PROFILE'),
 artifact_version integer NOT NULL, artifact_hash varchar(64) NOT NULL, offer_id uuid NOT NULL,
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(offer_id,experiment_id) REFERENCES record_offer_packages(id,experiment_id),
 UNIQUE(id,experiment_id), UNIQUE(artifact_id), UNIQUE(offer_id)
);
CREATE TABLE record_qualification_criteria (
 profile_id uuid NOT NULL REFERENCES record_offer_qualification_profiles(id), code varchar(32) NOT NULL,
 category varchar(40) NOT NULL, requirement varchar(1000) NOT NULL, question varchar(1000) NOT NULL,
 rule_kind varchar(24) NOT NULL, comparison varchar(16) NOT NULL, threshold varchar(200),
 required_evidence_kind varchar(32) NOT NULL, unknown_behavior varchar(16) NOT NULL, PRIMARY KEY(profile_id,code),
 CHECK(rule_kind IN ('HARD_GATE','SOFT_SIGNAL','FATAL_DISQUALIFIER') AND comparison IN ('PRESENT','BOOLEAN_TRUE','GTE','LTE','EQUALS','ASSESSMENT') AND required_evidence_kind IN ('RESEARCH_EVIDENCE','PRICE_OBSERVATION','DELIVERY_SCOPE_ESTIMATE','OPERATOR_CONSTRAINT') AND unknown_behavior IN ('BLOCK','NOT_APPLICABLE')),
 CHECK(category IN ('REQUIRED_FIT','POSITIVE_SIGNAL','FATAL_DISQUALIFIER','EVIDENCE_QUESTION','TECHNICAL_FIT','ECONOMIC_FIT','BUYER_FIT','CONTACT_FIT','PILOT_FIT','OFFER_SPECIFIC_ASSESSMENT')),
 CHECK((comparison IN ('GTE','LTE','EQUALS'))=(threshold IS NOT NULL)),
 CHECK(rule_kind='SOFT_SIGNAL' OR unknown_behavior='BLOCK'),
 CHECK((category='FATAL_DISQUALIFIER')=(rule_kind='FATAL_DISQUALIFIER'))
);
CREATE TABLE record_initial_outreach_policies (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, artifact_id uuid NOT NULL,
 artifact_kind varchar(64) NOT NULL CHECK(artifact_kind='INITIAL_OUTREACH_POLICY'),
 artifact_version integer NOT NULL, artifact_hash varchar(64) NOT NULL, offer_id uuid NOT NULL,
 pricing varchar(16) NOT NULL, formal_proposal varchar(16) NOT NULL, detailed_scope varchar(16) NOT NULL,
 budget_question varchar(16) NOT NULL, primary_goal varchar(40) NOT NULL,
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(offer_id,experiment_id) REFERENCES record_offer_packages(id,experiment_id),
 UNIQUE(id,experiment_id), UNIQUE(artifact_id), UNIQUE(offer_id),
 CHECK(pricing='OMIT' AND formal_proposal='FORBIDDEN' AND detailed_scope='OMIT' AND budget_question='FORBIDDEN' AND primary_goal='START_RELEVANT_CONVERSATION')
);
CREATE TABLE record_offer_acceptances (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, offer_id uuid NOT NULL, offer_artifact_id uuid NOT NULL,
 profile_id uuid NOT NULL REFERENCES record_offer_qualification_profiles(id), profile_artifact_id uuid NOT NULL,
 policy_id uuid NOT NULL REFERENCES record_initial_outreach_policies(id), policy_artifact_id uuid NOT NULL,
 accepted_by uuid NOT NULL, accepted_at timestamptz NOT NULL,
 FOREIGN KEY(offer_id,experiment_id) REFERENCES record_offer_packages(id,experiment_id),
 UNIQUE(id,experiment_id), UNIQUE(offer_id)
);
CREATE TABLE record_offer_gap_briefs (
 id uuid PRIMARY KEY, experiment_id uuid NOT NULL, artifact_id uuid NOT NULL,
 artifact_kind varchar(64) NOT NULL CHECK(artifact_kind='OFFER_RESEARCH_GAP_BRIEF'),
 artifact_version integer NOT NULL, artifact_hash varchar(64) NOT NULL, proposal_id uuid NOT NULL,
 bundle_id uuid NOT NULL, missing_fields varchar(64)[] NOT NULL, contradictory_fields varchar(64)[] NOT NULL,
 required_source_types varchar(64)[] NOT NULL, targeted_questions varchar(1000)[] NOT NULL,
 created_at timestamptz NOT NULL,
 FOREIGN KEY(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash) REFERENCES record_artifacts(id,experiment_id,kind,version,content_hash),
 FOREIGN KEY(proposal_id,experiment_id) REFERENCES record_offer_proposals(id,experiment_id),
 FOREIGN KEY(bundle_id,experiment_id) REFERENCES record_offer_bundles(id,experiment_id),
 UNIQUE(id,experiment_id), UNIQUE(artifact_id),
 CHECK(cardinality(missing_fields)+cardinality(contradictory_fields)>0),
 CHECK(cardinality(required_source_types)>0 AND cardinality(targeted_questions)>0)
);

CREATE INDEX ix_record_offer_bundles_artifact ON record_offer_bundles(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash);
CREATE INDEX ix_record_offer_bundles_idea ON record_offer_bundles(idea_acceptance_id,experiment_id);
CREATE INDEX ix_record_offer_bundles_verdict ON record_offer_bundles(verdict_id,experiment_id);
CREATE INDEX ix_record_offer_bundle_inputs_artifact ON record_offer_bundle_inputs(artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash);
CREATE INDEX ix_record_commercial_envelopes_profile ON record_commercial_envelopes(operator_profile_id,operator_profile_version);
CREATE INDEX ix_record_offer_proposals_bundle ON record_offer_proposals(bundle_id,experiment_id);
CREATE INDEX ix_record_offer_proposals_envelope ON record_offer_proposals(envelope_id,experiment_id);
CREATE INDEX ix_record_offer_invalidations_bundle ON record_offer_proposal_invalidations(superseding_bundle_id,experiment_id);
CREATE INDEX ix_record_offer_packages_proposal ON record_offer_packages(proposal_id,experiment_id);
CREATE INDEX ix_record_offer_field_sources_source ON record_offer_field_sources(source_artifact_id,experiment_id,source_kind,source_version,source_hash);
CREATE INDEX ix_record_offer_qualification_profiles_offer ON record_offer_qualification_profiles(offer_id,experiment_id);
CREATE INDEX ix_record_initial_outreach_policies_offer ON record_initial_outreach_policies(offer_id,experiment_id);
CREATE INDEX ix_record_offer_gap_briefs_proposal ON record_offer_gap_briefs(proposal_id,experiment_id);
CREATE INDEX ix_record_offer_gap_briefs_bundle ON record_offer_gap_briefs(bundle_id,experiment_id);
""")
    _install_guards()
    _replace_payload_validator()
    _replace_return_and_lineage_guards()


def _replace_payload_validator() -> None:
    op.execute(r"""
CREATE OR REPLACE FUNCTION record_payload_valid(kind text, value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE kind
  WHEN 'EXPERIMENT_BRIEF' THEN record_json_exact(value,ARRAY['objective']) AND record_nonempty_text(value->'objective')
  WHEN 'IDEA_SEED' THEN record_json_exact(value,ARRAY['origin','statement']) AND value->>'origin'='USER_SUPPLIED' AND record_nonempty_text(value->'statement')
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
  WHEN 'DELIVERY_SCOPE_ESTIMATE' THEN record_json_exact(value,ARRAY['hours','basis']) AND value->>'hours' ~ '^[0-9]+(\.[0-9]{1,2})?$' AND (value->>'hours')::numeric>0 AND (value->>'hours')::numeric<=100000 AND record_nonempty_text(value->'basis')
  WHEN 'OFFER_DESIGN_INPUT_BUNDLE' THEN record_json_exact(value,ARRAY['status']) AND value->>'status'='FROZEN'
  WHEN 'COMMERCIAL_DESIGN_ENVELOPE' THEN record_json_exact(value,ARRAY['status','reason']) AND value->>'status' IN ('READY','IMPOSSIBLE_ECONOMICS','CURRENCY_MISMATCH','DELIVERY_CAPACITY_EXCEEDED') AND record_nonempty_text(value->'reason')
  WHEN 'OFFER_DESIGN_PROPOSAL' THEN record_offer_payload_valid(value)
  WHEN 'OFFER_PACKAGE' THEN record_offer_payload_valid(value)
  WHEN 'OFFER_QUALIFICATION_PROFILE' THEN record_json_exact(value,ARRAY['summary']) AND record_nonempty_text(value->'summary')
  WHEN 'INITIAL_OUTREACH_POLICY' THEN value='{"pricing":"OMIT","formal_proposal":"FORBIDDEN","detailed_scope":"OMIT","budget_question":"FORBIDDEN","primary_goal":"START_RELEVANT_CONVERSATION"}'::jsonb
  WHEN 'VALIDATION_RESULT' THEN record_json_exact(value,ARRAY['validator','disposition','reason']) AND record_nonempty_text(value->'validator') AND value->>'disposition' IN ('PASS','FAIL') AND record_nonempty_text(value->'reason')
  WHEN 'ACCEPTANCE_RECEIPT' THEN record_json_exact(value,ARRAY['disposition','reason']) AND value->>'disposition' IN ('ACCEPTED','REJECTED','SUPERSEDED') AND record_nonempty_text(value->'reason')
  ELSE false END
$$;
""")


def _install_guards() -> None:
    op.execute(r"""
CREATE FUNCTION record_offer_payload_valid(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT record_json_exact(value,ARRAY['target_customer','buyer','problem','solution_mechanism','credible_outcome','positioning','scope','deliverables','exclusions','prerequisites','timeline','customer_responsibilities','currency','base_price','pilot_terms','third_party_costs','payment_terms','validity','claims','ideal_fit','disqualifiers','negotiation_variables'])
 AND record_nonempty_text(value->'target_customer') AND record_nonempty_text(value->'buyer')
 AND record_nonempty_text(value->'problem') AND record_nonempty_text(value->'solution_mechanism')
 AND record_nonempty_text(value->'credible_outcome') AND record_nonempty_text(value->'positioning')
 AND record_nonempty_text(value->'scope') AND record_nonempty_text_array(value->'deliverables')
 AND record_nonempty_text_array(value->'exclusions') AND record_nonempty_text_array(value->'prerequisites')
 AND record_nonempty_text(value->'timeline') AND record_nonempty_text_array(value->'customer_responsibilities')
 AND value->>'currency' ~ '^[A-Z]{3}$' AND value->>'base_price' ~ '^[0-9]+(\.[0-9]{1,2})?$' AND (value->>'base_price')::numeric>0
 AND record_nonempty_text(value->'pilot_terms') AND record_nonempty_text(value->'third_party_costs')
 AND record_nonempty_text(value->'payment_terms') AND record_nonempty_text(value->'validity')
 AND record_nonempty_text_array(value->'claims') AND record_nonempty_text_array(value->'ideal_fit')
 AND record_nonempty_text_array(value->'disqualifiers') AND record_nonempty_text_array(value->'negotiation_variables')
$$;

CREATE FUNCTION record_offer_field_role_valid(field_name text, role_name text) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE field_name
  WHEN 'target_customer' THEN role_name='CUSTOMER_EVIDENCE'
  WHEN 'buyer' THEN role_name='BUYER_EVIDENCE'
  WHEN 'problem' THEN role_name='PROBLEM_EVIDENCE'
  WHEN 'solution_mechanism' THEN role_name IN ('FEASIBILITY','INTEGRATION')
  WHEN 'credible_outcome' THEN role_name IN ('PROBLEM_EVIDENCE','DIFFERENTIATION')
  WHEN 'positioning' THEN role_name IN ('COMPETITOR_PROFILE','DIFFERENTIATION')
  WHEN 'scope' THEN role_name IN ('SCOPE_ESTIMATE','FEASIBILITY')
  WHEN 'deliverables' THEN role_name IN ('SCOPE_ESTIMATE','FEASIBILITY')
  WHEN 'exclusions' THEN role_name IN ('FEASIBILITY','INTEGRATION')
  WHEN 'prerequisites' THEN role_name IN ('INTEGRATION','TRUST_COMPLIANCE')
  WHEN 'timeline' THEN role_name='SCOPE_ESTIMATE'
  WHEN 'customer_responsibilities' THEN role_name='INTEGRATION'
  WHEN 'pilot_terms' THEN role_name IN ('PRICE_OBSERVATION','FEASIBILITY')
  WHEN 'third_party_costs' THEN role_name IN ('PRICE_OBSERVATION','INTEGRATION')
  WHEN 'validity' THEN role_name='PRICE_OBSERVATION'
  WHEN 'claims' THEN role_name IN ('CUSTOMER_EVIDENCE','PROBLEM_EVIDENCE','RESEARCH_EVIDENCE')
  WHEN 'ideal_fit' THEN role_name IN ('CUSTOMER_EVIDENCE','BUYER_EVIDENCE')
  WHEN 'disqualifiers' THEN role_name IN ('OBJECTIONS','TRUST_COMPLIANCE')
  WHEN 'negotiation_variables' THEN role_name IN ('OBJECTIONS','PRICE_OBSERVATION')
  ELSE false END
$$;

CREATE FUNCTION record_offer_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE artifact record_artifacts; proposal record_offer_proposals; envelope record_commercial_envelopes;
 bundle record_offer_bundles; profile record_operator_profiles; commercial jsonb; expected_cost numeric; expected_floor numeric;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable offer record'; END IF;
 IF TG_TABLE_NAME<>'record_qualification_criteria' THEN
  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 END IF;
 IF TG_TABLE_NAME='record_offer_bundles' THEN
  SELECT * INTO artifact FROM record_artifacts WHERE id=NEW.artifact_id;
  IF artifact.kind<>'OFFER_DESIGN_INPUT_BUNDLE' OR artifact.payload->>'status'<>'FROZEN'
   OR NOT EXISTS(SELECT 1 FROM record_verdicts v JOIN record_idea_acceptances i ON i.cycle_id=v.cycle_id WHERE v.id=NEW.verdict_id AND v.experiment_id=NEW.experiment_id AND v.verdict='PROCEED_TO_OFFER' AND i.id=NEW.idea_acceptance_id AND i.artifact_id=NEW.idea_artifact_id AND v.report_artifact_id=NEW.report_artifact_id)
  THEN RAISE EXCEPTION 'invalid accepted offer bundle'; END IF;
 ELSIF TG_TABLE_NAME='record_commercial_envelopes' THEN
  SELECT * INTO bundle FROM record_offer_bundles WHERE id=NEW.bundle_id;
  SELECT * INTO profile FROM record_operator_profiles WHERE id=NEW.operator_profile_id AND version=NEW.operator_profile_version;
  commercial:=profile.commercial;
  IF bundle.experiment_id IS DISTINCT FROM NEW.experiment_id OR NOT EXISTS(SELECT 1 FROM record_offer_bundle_inputs WHERE bundle_id=NEW.bundle_id AND role='SCOPE_ESTIMATE' AND artifact_id=NEW.scope_artifact_id)
   OR NEW.currency IS DISTINCT FROM commercial->>'currency' OR NEW.service_hours<>(SELECT (payload->>'hours')::numeric FROM record_artifacts WHERE id=NEW.scope_artifact_id)
  THEN RAISE EXCEPTION 'invalid envelope inputs'; END IF;
  IF NEW.status='READY' THEN
   expected_cost:=ceil(NEW.service_hours*(commercial->>'hourly_cost')::numeric*100)/100;
   expected_floor:=greatest((commercial->>'minimum_project_price')::numeric,ceil(expected_cost/(1-(commercial->>'minimum_margin_rate')::numeric)*100)/100);
   IF NEW.service_hours>(profile.delivery->>'max_project_hours')::numeric OR (commercial->>'minimum_margin_rate')::numeric>=1 OR NEW.delivery_cost<>expected_cost OR NEW.minimum_price<>expected_floor THEN RAISE EXCEPTION 'invalid commercial envelope'; END IF;
  ELSIF NEW.status='DELIVERY_CAPACITY_EXCEEDED' THEN
   IF NEW.service_hours<=(profile.delivery->>'max_project_hours')::numeric THEN RAISE EXCEPTION 'invalid delivery classification'; END IF;
  ELSIF NEW.status='IMPOSSIBLE_ECONOMICS' THEN
   IF NEW.service_hours>(profile.delivery->>'max_project_hours')::numeric OR (commercial->>'minimum_margin_rate')::numeric<1 THEN RAISE EXCEPTION 'invalid economics classification'; END IF;
  ELSIF NEW.status='CURRENCY_MISMATCH' THEN
   IF NEW.service_hours>(profile.delivery->>'max_project_hours')::numeric OR (commercial->>'minimum_margin_rate')::numeric>=1
    OR NOT EXISTS(SELECT 1 FROM record_offer_bundle_inputs input JOIN record_artifacts price ON price.id=input.artifact_id WHERE input.bundle_id=NEW.bundle_id AND input.role='PRICE_OBSERVATION' AND price.payload->>'currency' IS DISTINCT FROM NEW.currency)
   THEN RAISE EXCEPTION 'invalid currency classification'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_offer_proposals' THEN
  SELECT * INTO envelope FROM record_commercial_envelopes WHERE id=NEW.envelope_id;
  SELECT * INTO artifact FROM record_artifacts WHERE id=NEW.artifact_id;
  IF envelope.status<>'READY' OR envelope.bundle_id IS DISTINCT FROM NEW.bundle_id
   OR artifact.payload->>'currency' IS DISTINCT FROM envelope.currency
   OR (artifact.payload->>'base_price')::numeric<envelope.minimum_price
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.artifact_id AND producer_id=(SELECT artifact_id FROM record_offer_bundles WHERE id=NEW.bundle_id) AND role='INPUT_BUNDLE')
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.artifact_id AND producer_id=envelope.artifact_id AND role='ENVELOPE')
  THEN RAISE EXCEPTION 'invalid offer proposal'; END IF;
 ELSIF TG_TABLE_NAME='record_offer_packages' THEN
  SELECT * INTO proposal FROM record_offer_proposals WHERE id=NEW.proposal_id;
  SELECT * INTO artifact FROM record_artifacts WHERE id=NEW.artifact_id;
  SELECT * INTO envelope FROM record_commercial_envelopes WHERE id=proposal.envelope_id;
  IF proposal.bundle_id IS DISTINCT FROM NEW.bundle_id OR proposal.envelope_id IS DISTINCT FROM NEW.envelope_id
   OR EXISTS(SELECT 1 FROM record_offer_proposal_invalidations WHERE proposal_id=NEW.proposal_id)
   OR artifact.payload IS DISTINCT FROM (SELECT payload FROM record_artifacts WHERE id=proposal.artifact_id)
   OR NEW.currency IS DISTINCT FROM envelope.currency OR NEW.base_price<envelope.minimum_price
  THEN RAISE EXCEPTION 'invalid offer package'; END IF;
 ELSIF TG_TABLE_NAME='record_offer_field_sources' THEN
  IF NOT EXISTS(SELECT 1 FROM record_offer_packages package WHERE package.id=NEW.offer_id AND package.bundle_id=NEW.bundle_id)
   OR (NEW.source_artifact_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM record_offer_bundle_inputs input WHERE input.bundle_id=NEW.bundle_id AND input.role=NEW.source_role AND input.artifact_id=NEW.source_artifact_id AND input.artifact_kind=NEW.source_kind AND input.artifact_version=NEW.source_version AND input.artifact_hash=NEW.source_hash))
   OR (NEW.source_artifact_id IS NOT NULL AND record_offer_field_role_valid(NEW.field_path,NEW.source_role) IS NOT TRUE)
   OR (NEW.operator_constraint IS NOT NULL AND NEW.operator_constraint IS DISTINCT FROM CASE NEW.field_path WHEN 'currency' THEN 'CURRENCY' WHEN 'base_price' THEN 'MINIMUM_PRICE' WHEN 'payment_terms' THEN 'MINIMUM_DEPOSIT_RATE' END)
  THEN RAISE EXCEPTION 'offer field source outside bundle'; END IF;
 ELSIF TG_TABLE_NAME='record_offer_gap_briefs' THEN
  SELECT * INTO proposal FROM record_offer_proposals WHERE id=NEW.proposal_id;
  IF proposal.bundle_id IS DISTINCT FROM NEW.bundle_id
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.artifact_id AND producer_id=proposal.artifact_id AND role='ORIGINATING_PROPOSAL')
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.artifact_id AND producer_id=(SELECT artifact_id FROM record_offer_bundles WHERE id=NEW.bundle_id) AND role='OFFER_INPUT_BUNDLE')
  THEN RAISE EXCEPTION 'invalid offer gap lineage'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION record_offer_acceptance_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE package record_offer_packages; qualification record_offer_qualification_profiles; policy record_initial_outreach_policies;
BEGIN
 SELECT * INTO package FROM record_offer_packages WHERE id=NEW.offer_id;
 SELECT * INTO qualification FROM record_offer_qualification_profiles WHERE id=NEW.profile_id;
 SELECT * INTO policy FROM record_initial_outreach_policies WHERE id=NEW.policy_id;
 IF record_operator_authorized(NEW.experiment_id,NEW.accepted_by) IS NOT TRUE
  OR package.experiment_id IS DISTINCT FROM NEW.experiment_id
  OR qualification.offer_id IS DISTINCT FROM package.id OR policy.offer_id IS DISTINCT FROM package.id
  OR NEW.offer_artifact_id IS DISTINCT FROM package.artifact_id
  OR NEW.profile_artifact_id IS DISTINCT FROM qualification.artifact_id
  OR NEW.policy_artifact_id IS DISTINCT FROM policy.artifact_id
  OR (SELECT array_agg(field_path ORDER BY field_path)::text[] FROM record_offer_field_sources WHERE offer_id=package.id) IS DISTINCT FROM ARRAY['base_price','buyer','claims','credible_outcome','currency','customer_responsibilities','deliverables','disqualifiers','exclusions','ideal_fit','negotiation_variables','payment_terms','pilot_terms','positioning','prerequisites','problem','scope','solution_mechanism','target_customer','third_party_costs','timeline','validity']
  OR (SELECT array_agg(DISTINCT category ORDER BY category)::text[] FROM record_qualification_criteria WHERE profile_id=qualification.id) IS DISTINCT FROM ARRAY['BUYER_FIT','CONTACT_FIT','ECONOMIC_FIT','EVIDENCE_QUESTION','FATAL_DISQUALIFIER','OFFER_SPECIFIC_ASSESSMENT','PILOT_FIT','POSITIVE_SIGNAL','REQUIRED_FIT','TECHNICAL_FIT']
 THEN RAISE EXCEPTION 'incomplete accepted offer set'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION record_offer_bundle_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE required text[]:=ARRAY['ALTERNATIVES','BUYER_EVIDENCE','COMPETITOR_PROFILE','CONTRADICTIONS_UNCERTAINTIES','CUSTOMER_EVIDENCE','DIFFERENTIATION','FEASIBILITY','INTEGRATION','OBJECTIONS','PRICE_OBSERVATION','PROBLEM_EVIDENCE','REACHABILITY','SCOPE_ESTIMATE','SERVICE_PROFILE','TRUST_COMPLIANCE'];
BEGIN
 IF (SELECT array_agg(DISTINCT role ORDER BY role)::text[] FROM record_offer_bundle_inputs WHERE bundle_id=NEW.id AND role=ANY(required)) IS DISTINCT FROM required
  OR (SELECT count(*) FROM record_offer_bundle_inputs WHERE bundle_id=NEW.id AND role=ANY(required))<>cardinality(required)
  OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.artifact_id AND role='ACCEPTED_IDEA' AND producer_id=NEW.idea_artifact_id)
  OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.artifact_id AND role='REPORT' AND producer_id=NEW.report_artifact_id)
  OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.artifact_id AND role='RECOMMENDATION' AND producer_id=(SELECT recommendation_artifact_id FROM record_verdicts WHERE id=NEW.verdict_id))
  OR EXISTS(
   SELECT 1 FROM record_offer_bundle_inputs input
   WHERE input.bundle_id=NEW.id AND input.role=ANY(required)
    AND (NOT EXISTS(SELECT 1 FROM record_artifact_links link WHERE link.consumer_id=NEW.report_artifact_id AND link.role=input.role AND link.producer_id=input.artifact_id AND link.producer_kind=input.artifact_kind AND link.producer_version=input.artifact_version AND link.producer_hash=input.artifact_hash)
      OR NOT EXISTS(SELECT 1 FROM record_source_refs source WHERE source.artifact_id=input.artifact_id))
  )
  OR EXISTS(SELECT 1 FROM record_offer_bundle_inputs input JOIN record_artifacts price ON price.id=input.artifact_id WHERE input.bundle_id=NEW.id AND input.role='PRICE_OBSERVATION' AND price.payload->>'status'<>'QUOTED')
 THEN RAISE EXCEPTION 'incomplete offer research bundle'; END IF;
 RETURN NEW;
END $$;

DO $$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['record_offer_bundles','record_offer_bundle_inputs','record_commercial_envelopes','record_offer_proposals','record_offer_proposal_invalidations','record_offer_packages','record_offer_field_sources','record_offer_qualification_profiles','record_qualification_criteria','record_initial_outreach_policies','record_offer_acceptances','record_offer_gap_briefs'] LOOP
  EXECUTE format('CREATE TRIGGER %I_guard BEFORE INSERT OR UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION record_offer_guard()',name,name);
 END LOOP;
END $$;
CREATE CONSTRAINT TRIGGER record_offer_bundle_complete AFTER INSERT ON record_offer_bundles DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION record_offer_bundle_guard();
CREATE CONSTRAINT TRIGGER record_offer_acceptance_complete AFTER INSERT ON record_offer_acceptances DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION record_offer_acceptance_guard();
""")


def _replace_return_and_lineage_guards() -> None:
    op.execute(r"""
CREATE OR REPLACE FUNCTION record_lineage_closed(target uuid, scope uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
 WITH RECURSIVE authoritative(id) AS (
  SELECT artifact_id FROM record_artifact_dispositions WHERE experiment_id=scope AND disposition IN ('ACCEPTED','VALIDATED')
  UNION SELECT validation_artifact_id FROM record_artifact_dispositions WHERE experiment_id=scope AND validation_artifact_id IS NOT NULL
  UNION SELECT artifact_id FROM record_candidate_selections WHERE experiment_id=scope
  UNION SELECT seed_artifact_id FROM record_cycles WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_idea_acceptances WHERE experiment_id=scope
  UNION SELECT plan_artifact_id FROM record_research_attempts WHERE experiment_id=scope
  UNION SELECT report_artifact_id FROM record_verdicts WHERE experiment_id=scope
  UNION SELECT recommendation_artifact_id FROM record_verdicts WHERE experiment_id=scope
  UNION SELECT feedback_artifact_id FROM record_returns WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_offer_bundles WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_commercial_envelopes WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_offer_proposals WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_offer_packages WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_offer_qualification_profiles WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_initial_outreach_policies WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_offer_gap_briefs WHERE experiment_id=scope
 ), closed(id) AS (
  SELECT id FROM authoritative WHERE id IS NOT NULL
  UNION SELECT link.producer_id FROM record_artifact_links link JOIN closed ON link.consumer_id=closed.id WHERE link.experiment_id=scope
 ) SELECT EXISTS(SELECT 1 FROM closed WHERE id=target)
$$;

CREATE OR REPLACE FUNCTION record_origin_return_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE artifact_row record_artifacts; parent record_cycles; root_cycle record_cycles; child record_cycles;
 verdict_row record_verdicts; idea_row record_idea_acceptances; selection_row record_candidate_selections;
 scope_id uuid; expected_verdict text; expected_purpose text;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable product record'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF TG_TABLE_NAME='record_candidate_selections' THEN
  SELECT * INTO artifact_row FROM record_artifacts WHERE id=NEW.artifact_id;
  IF record_operator_authorized(NEW.experiment_id,NEW.selected_by) IS NOT TRUE
    OR ROW(artifact_row.workflow_id,artifact_row.agent_id) IS DISTINCT FROM ROW(NEW.workflow_id,NEW.agent_id)
    OR NOT EXISTS(SELECT 1 FROM record_experiments e WHERE e.id=NEW.experiment_id AND e.operator_profile_id=NEW.profile_id AND e.operator_profile_version=NEW.profile_version)
    OR EXISTS(SELECT 1 FROM record_cycles WHERE experiment_id=NEW.experiment_id)
  THEN RAISE EXCEPTION 'invalid candidate selection'; END IF;
 ELSIF TG_TABLE_NAME='record_cycles' THEN
  IF record_operator_authorized(NEW.experiment_id,(SELECT profile.operator_id FROM record_experiments experiment JOIN record_operator_profiles profile ON profile.id=experiment.operator_profile_id AND profile.version=experiment.operator_profile_version WHERE experiment.id=NEW.experiment_id)) IS NOT TRUE
  THEN RAISE EXCEPTION 'inactive experiment owner'; END IF;
  IF NEW.ordinal=1 THEN
   IF NEW.purpose IS DISTINCT FROM 'INITIAL' OR NEW.episode_id IS DISTINCT FROM NEW.id THEN RAISE EXCEPTION 'invalid initial episode'; END IF;
   SELECT * INTO artifact_row FROM record_artifacts WHERE id=NEW.seed_artifact_id;
   IF NEW.idea_mode='SYSTEM_DISCOVERY' THEN
    SELECT * INTO selection_row FROM record_candidate_selections WHERE id=NEW.selection_id;
    IF ROW(selection_row.artifact_id,selection_row.artifact_kind,selection_row.artifact_version,selection_row.artifact_hash,selection_row.experiment_id)
      IS DISTINCT FROM ROW(NEW.seed_artifact_id,NEW.seed_kind,NEW.seed_version,NEW.seed_hash,NEW.experiment_id)
    THEN RAISE EXCEPTION 'exact selection required'; END IF;
   ELSIF artifact_row.payload->>'origin' IS DISTINCT FROM 'USER_SUPPLIED' OR EXISTS(SELECT 1 FROM record_candidate_selections WHERE experiment_id=NEW.experiment_id)
   THEN RAISE EXCEPTION 'original user seed required'; END IF;
  ELSE
   SELECT * INTO parent FROM record_cycles WHERE id=NEW.parent_cycle_id;
   IF ROW(NEW.idea_mode,NEW.selection_id,NEW.episode_id) IS DISTINCT FROM ROW(parent.idea_mode,parent.selection_id,parent.episode_id) OR NEW.purpose='INITIAL'
   THEN RAISE EXCEPTION 'immutable origin and episode required'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_returns' THEN
  SELECT * INTO verdict_row FROM record_verdicts WHERE id=NEW.verdict_id;
  SELECT * INTO parent FROM record_cycles WHERE id=NEW.from_cycle_id;
  SELECT * INTO child FROM record_cycles WHERE id=NEW.to_cycle_id;
  SELECT * INTO root_cycle FROM record_cycles WHERE experiment_id=NEW.experiment_id AND ordinal=1;
  SELECT * INTO idea_row FROM record_idea_acceptances WHERE cycle_id=NEW.from_cycle_id;
  expected_verdict:=CASE NEW.kind WHEN 'SAME_INTENT' THEN 'REFINE_SAME_IDEA' WHEN 'MATERIAL_PIVOT' THEN 'MATERIAL_PIVOT_RECOMMENDED' WHEN 'INCONCLUSIVE_SUPPLEMENT' THEN 'INCONCLUSIVE' WHEN 'OFFER_GAP' THEN 'PROCEED_TO_OFFER' END;
  expected_purpose:=CASE NEW.kind WHEN 'SAME_INTENT' THEN 'SAME_INTENT_RETURN' WHEN 'MATERIAL_PIVOT' THEN 'MATERIAL_PIVOT_RETURN' WHEN 'INCONCLUSIVE_SUPPLEMENT' THEN 'INCONCLUSIVE_SUPPLEMENT' WHEN 'OFFER_GAP' THEN 'OFFER_GAP_RETURN' END;
  scope_id:=CASE NEW.kind WHEN 'SAME_INTENT' THEN CASE WHEN parent.idea_mode='USER_SEEDED_REFINEMENT' THEN parent.seed_artifact_id ELSE (SELECT artifact_id FROM record_idea_acceptances WHERE cycle_id=root_cycle.id) END WHEN 'OFFER_GAP' THEN idea_row.artifact_id ELSE parent.episode_id END;
  IF verdict_row.id IS NULL OR child.id IS NULL OR parent.id IS NULL OR idea_row.id IS NULL OR expected_verdict IS NULL
   OR verdict_row.cycle_id IS DISTINCT FROM parent.id OR verdict_row.verdict IS DISTINCT FROM expected_verdict
   OR child.parent_cycle_id IS DISTINCT FROM parent.id OR child.ordinal<>parent.ordinal+1 OR child.purpose IS DISTINCT FROM expected_purpose
   OR child.id IS DISTINCT FROM (SELECT cycle_row.id FROM record_cycles cycle_row WHERE cycle_row.experiment_id=NEW.experiment_id ORDER BY cycle_row.ordinal DESC LIMIT 1)
   OR NEW.applicable_scope_id IS DISTINCT FROM scope_id OR NEW.idea_artifact_id IS DISTINCT FROM idea_row.artifact_id
   OR NEW.ordinal<>(SELECT count(*)+1 FROM record_returns return_row WHERE return_row.experiment_id=NEW.experiment_id AND return_row.kind=NEW.kind AND return_row.applicable_scope_id=scope_id)
  THEN RAISE EXCEPTION 'invalid scoped research return'; END IF;
  IF NEW.kind='OFFER_GAP' THEN
   IF NOT EXISTS(
      SELECT 1 FROM record_offer_bundles bundle_row
      JOIN record_offer_gap_briefs gap_row ON gap_row.bundle_id=bundle_row.id
      JOIN record_offer_proposals proposal_row ON proposal_row.id=gap_row.proposal_id AND proposal_row.bundle_id=bundle_row.id
      WHERE bundle_row.artifact_id=NEW.offer_input_bundle_id AND bundle_row.experiment_id=NEW.experiment_id
        AND gap_row.artifact_id=NEW.feedback_artifact_id AND bundle_row.verdict_id=NEW.verdict_id
    ) OR NOT EXISTS(SELECT 1 FROM record_artifact_links link_row WHERE link_row.consumer_id=NEW.feedback_artifact_id AND link_row.producer_id=NEW.offer_input_bundle_id AND link_row.role='OFFER_INPUT_BUNDLE')
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links link_row WHERE link_row.consumer_id=NEW.feedback_artifact_id AND link_row.role='REPORT' AND link_row.producer_id=verdict_row.report_artifact_id)
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links link_row WHERE link_row.consumer_id=NEW.feedback_artifact_id AND link_row.role='RECOMMENDATION' AND link_row.producer_id=verdict_row.recommendation_artifact_id)
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links link_row WHERE link_row.consumer_id=NEW.feedback_artifact_id AND link_row.role='ACCEPTED_IDEA' AND link_row.producer_id=idea_row.artifact_id)
   THEN RAISE EXCEPTION 'accepted offer gap lineage required'; END IF;
  ELSIF NOT EXISTS(SELECT 1 FROM record_artifact_dispositions disposition_row WHERE disposition_row.artifact_id=NEW.feedback_artifact_id AND disposition_row.disposition='ACCEPTED')
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links link_row WHERE link_row.consumer_id=NEW.feedback_artifact_id AND link_row.role='REPORT' AND link_row.producer_id=verdict_row.report_artifact_id)
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links link_row WHERE link_row.consumer_id=NEW.feedback_artifact_id AND link_row.role='RECOMMENDATION' AND link_row.producer_id=verdict_row.recommendation_artifact_id)
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links link_row WHERE link_row.consumer_id=NEW.feedback_artifact_id AND link_row.role='ACCEPTED_IDEA' AND link_row.producer_id=idea_row.artifact_id)
  THEN RAISE EXCEPTION 'accepted exact return evidence required'; END IF;
 ELSIF TG_TABLE_NAME='record_artifacts' THEN
  IF record_operator_authorized(NEW.experiment_id,NEW.created_by) IS NOT TRUE THEN RAISE EXCEPTION 'inactive artifact owner'; END IF;
 ELSIF TG_TABLE_NAME='record_research_attempts' THEN
  IF record_operator_authorized(NEW.experiment_id,(SELECT profile.operator_id FROM record_experiments experiment JOIN record_operator_profiles profile ON profile.id=experiment.operator_profile_id AND profile.version=experiment.operator_profile_version WHERE experiment.id=NEW.experiment_id)) IS NOT TRUE THEN RAISE EXCEPTION 'inactive experiment owner'; END IF;
  SELECT * INTO child FROM record_cycles WHERE id=NEW.cycle_id;
  IF child.ordinal>1 AND NOT EXISTS(SELECT 1 FROM record_returns return_row JOIN record_artifact_links link_row ON link_row.producer_id=return_row.feedback_artifact_id AND link_row.consumer_id=NEW.plan_artifact_id AND link_row.role='RETURN_FEEDBACK' WHERE return_row.to_cycle_id=child.id)
  THEN RAISE EXCEPTION 'research plan requires exact return feedback'; END IF;
 ELSIF TG_TABLE_NAME='record_artifact_dispositions' THEN
  IF record_operator_authorized(NEW.experiment_id,NEW.decided_by) IS NOT TRUE THEN RAISE EXCEPTION 'inactive decision owner'; END IF;
 END IF;
 RETURN NEW;
END $$;
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM record_offer_bundles) THEN RAISE EXCEPTION 'offer history cannot be represented by previous schema'; END IF;
END $$;
""")
    _restore_prior_payload_and_lineage()
    op.execute(r"""
DROP TRIGGER record_offer_acceptance_complete ON record_offer_acceptances;
DROP TRIGGER record_offer_bundle_complete ON record_offer_bundles;
DO $$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['record_offer_bundles','record_offer_bundle_inputs','record_commercial_envelopes','record_offer_proposals','record_offer_proposal_invalidations','record_offer_packages','record_offer_field_sources','record_offer_qualification_profiles','record_qualification_criteria','record_initial_outreach_policies','record_offer_acceptances','record_offer_gap_briefs'] LOOP
  EXECUTE format('DROP TRIGGER %I_guard ON %I',name,name);
 END LOOP;
END $$;
DROP FUNCTION record_offer_bundle_guard();
DROP FUNCTION record_offer_acceptance_guard();
DROP FUNCTION record_offer_guard();
DROP FUNCTION record_offer_payload_valid(jsonb);
DROP FUNCTION record_offer_field_role_valid(text,text);
DROP TABLE record_offer_gap_briefs,record_offer_acceptances,record_initial_outreach_policies,record_qualification_criteria,record_offer_qualification_profiles,record_offer_field_sources,record_offer_packages,record_offer_proposal_invalidations,record_offer_proposals,record_commercial_envelopes,record_offer_bundle_inputs,record_offer_bundles;
ALTER TABLE record_artifacts DROP CONSTRAINT record_artifacts_kind_check;
ALTER TABLE record_artifacts ADD CHECK(kind IN ('EXPERIMENT_BRIEF','IDEA_SEED','IDEA_CANDIDATE','IDEA_BRIEF','RESEARCH_PLAN','RESEARCH_EVIDENCE','COMPETITOR_PROFILE','SERVICE_PROFILE','PRICE_OBSERVATION','MARKET_RESEARCH_REPORT','MARKET_RESEARCH_RECOMMENDATION','RESEARCH_FEEDBACK_BRIEF','OFFER_RESEARCH_GAP_BRIEF','VALIDATION_RESULT','ACCEPTANCE_RECEIPT'));
""")
    # Migration 06 restores its own frozen payload validator during a full downgrade.


def _restore_prior_payload_and_lineage() -> None:
    op.execute(r"""
CREATE OR REPLACE FUNCTION record_payload_valid(kind text, value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE kind
  WHEN 'EXPERIMENT_BRIEF' THEN record_json_exact(value,ARRAY['objective']) AND record_nonempty_text(value->'objective')
  WHEN 'IDEA_SEED' THEN record_json_exact(value,ARRAY['origin','statement']) AND value->>'origin'='USER_SUPPLIED' AND record_nonempty_text(value->'statement')
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
  UNION SELECT link.producer_id FROM record_artifact_links link JOIN lineage ON lineage.id=link.consumer_id WHERE link.experiment_id=scope
 ) SELECT EXISTS(SELECT 1 FROM lineage WHERE id=target)
$$;
""")
