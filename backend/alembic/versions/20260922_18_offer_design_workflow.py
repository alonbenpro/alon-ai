"""Durable L04 Offer Design workflow and bounded return lineage."""

from alembic import op

revision = "20260922_18"
down_revision = "20260922_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE TABLE record_offer_design_runs (
 id UUID PRIMARY KEY,
 experiment_id UUID NOT NULL REFERENCES gov_experiments(id),
 cycle_id UUID NOT NULL,
 verdict_id UUID NOT NULL,
 bundle_id UUID NOT NULL,
 envelope_id UUID NOT NULL,
 prompt_artifact_id UUID NOT NULL REFERENCES record_artifacts(id),
 prompt_version INTEGER NOT NULL,
 prompt_hash VARCHAR(64) NOT NULL,
 model_config_id UUID NOT NULL,
 model_config_workflow_id UUID NOT NULL,
 model_config_version UUID NOT NULL,
 started_by UUID NOT NULL REFERENCES record_operators(id),
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(cycle_id, experiment_id) REFERENCES record_cycles(id, experiment_id),
 FOREIGN KEY(verdict_id, experiment_id) REFERENCES record_verdicts(id, experiment_id),
 FOREIGN KEY(bundle_id, experiment_id) REFERENCES record_offer_bundles(id, experiment_id),
 FOREIGN KEY(envelope_id, experiment_id) REFERENCES record_commercial_envelopes(id, experiment_id),
 FOREIGN KEY(model_config_id, model_config_workflow_id, model_config_version) REFERENCES gov_configs(id, workflow_id, version),
 UNIQUE(id, experiment_id),
 UNIQUE(cycle_id, verdict_id, bundle_id, envelope_id),
 CHECK(prompt_version>0 AND prompt_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_offer_design_decisions (
 id UUID PRIMARY KEY,
 experiment_id UUID NOT NULL REFERENCES gov_experiments(id),
 run_id UUID NOT NULL,
 artifact_id UUID NOT NULL,
 artifact_kind VARCHAR(64) NOT NULL,
 artifact_version INTEGER NOT NULL,
 artifact_hash VARCHAR(64) NOT NULL,
 outcome VARCHAR(40) NOT NULL,
 operator_id UUID NOT NULL REFERENCES record_operators(id),
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(run_id, experiment_id) REFERENCES record_offer_design_runs(id, experiment_id),
 FOREIGN KEY(artifact_id, experiment_id, artifact_kind, artifact_version, artifact_hash) REFERENCES record_artifacts(id, experiment_id, kind, version, content_hash),
 UNIQUE(run_id),
 CHECK(outcome IN ('ACCEPT','TARGETED_RESEARCH_REQUIRED','IDEA_REFINEMENT_RECOMMENDED','WAITING_FOR_OPERATOR_INPUT'))
);
CREATE TABLE record_offer_design_workflow_bindings (
 dbos_workflow_id VARCHAR(200) PRIMARY KEY,
 application_version VARCHAR(64) NOT NULL,
 contract_version INTEGER NOT NULL,
 operation_kind VARCHAR(48) NOT NULL,
 request_hash VARCHAR(64) NOT NULL,
 request_payload JSONB NOT NULL,
 business_command_key UUID NOT NULL UNIQUE,
 experiment_id UUID NOT NULL REFERENCES gov_experiments(id),
 cycle_id UUID NOT NULL,
 verdict_id UUID NOT NULL,
 run_id UUID,
 command_id UUID REFERENCES record_commands(id),
 result_id UUID,
 delivery_state VARCHAR(32) NOT NULL,
 cancellation_outcome VARCHAR(40),
 created_at TIMESTAMPTZ NOT NULL,
 updated_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(cycle_id, experiment_id) REFERENCES record_cycles(id, experiment_id),
 FOREIGN KEY(verdict_id, experiment_id) REFERENCES record_verdicts(id, experiment_id),
 FOREIGN KEY(run_id, experiment_id) REFERENCES record_offer_design_runs(id, experiment_id),
 CHECK(contract_version=1 AND operation_kind IN ('START','DECISION','IDEA_REFINEMENT_RETURN') AND request_hash ~ '^[0-9a-f]{64}$' AND jsonb_typeof(request_payload)='object'),
 CHECK(delivery_state IN ('PENDING','STARTED','BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED','CANCELLED')),
 CHECK(cancellation_outcome IS NULL OR cancellation_outcome IN ('EFFECTIVE','INEFFECTIVE_ALREADY_COMMITTED')),
 CHECK((delivery_state IN ('PENDING','STARTED','CANCELLED') AND command_id IS NULL AND result_id IS NULL) OR (delivery_state IN ('BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED') AND command_id IS NOT NULL AND result_id IS NOT NULL))
);
-- A targeted return invalidates a proposal before a fresh bundle exists.  The
-- immutable gap brief is the truthful superseding lineage in that case.
ALTER TABLE record_offer_proposal_invalidations
 ALTER COLUMN superseding_bundle_id DROP NOT NULL,
 ADD COLUMN offer_gap_brief_id UUID REFERENCES record_offer_gap_briefs(id);
DO $$ DECLARE name TEXT;
BEGIN
 SELECT conname INTO name FROM pg_constraint
 WHERE conrelid='record_offer_proposal_invalidations'::regclass AND contype='c'
   AND pg_get_constraintdef(oid) LIKE '%SUPERSEDED_RESEARCH%';
 IF name IS NOT NULL THEN EXECUTE format('ALTER TABLE record_offer_proposal_invalidations DROP CONSTRAINT %I', name); END IF;
END $$;
ALTER TABLE record_offer_proposal_invalidations ADD CONSTRAINT record_offer_proposal_invalidations_reason_check CHECK (
  (reason='SUPERSEDED_RESEARCH' AND superseding_bundle_id IS NOT NULL AND offer_gap_brief_id IS NULL)
  OR (reason='OFFER_GAP_RETURN' AND superseding_bundle_id IS NULL AND offer_gap_brief_id IS NOT NULL)
 );
ALTER TABLE record_offer_proposals ADD COLUMN offer_design_run_id UUID REFERENCES record_offer_design_runs(id);
ALTER TABLE record_offer_packages ADD COLUMN offer_design_run_id UUID UNIQUE REFERENCES record_offer_design_runs(id);
ALTER TABLE record_cycle_transitions ADD COLUMN offer_design_run_id UUID;
ALTER TABLE record_cycle_transitions ADD COLUMN offer_design_decision_id UUID;
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transition_offer_run_fk FOREIGN KEY(offer_design_run_id) REFERENCES record_offer_design_runs(id);
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transition_offer_decision_fk FOREIGN KEY(offer_design_decision_id) REFERENCES record_offer_design_decisions(id);
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transitions_check;
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transitions_check CHECK (
 idea_kind='IDEA_BRIEF' AND (
  (ordinal=1 AND from_state='IDEA_REFINEMENT' AND to_state='MARKET_RESEARCH' AND verdict_id IS NULL AND offer_design_run_id IS NULL AND offer_design_decision_id IS NULL)
  OR (ordinal=2 AND from_state='MARKET_RESEARCH' AND to_state IN ('PROCEED_TO_OFFER','RETURN_FOR_REFINEMENT','WAITING_FOR_PIVOT_APPROVAL','KILLED','INCONCLUSIVE_REVIEW') AND verdict_id IS NOT NULL AND offer_design_run_id IS NULL AND offer_design_decision_id IS NULL)
  OR (ordinal=3 AND from_state IN ('WAITING_FOR_PIVOT_APPROVAL','INCONCLUSIVE_REVIEW') AND to_state='RETURN_FOR_REFINEMENT' AND verdict_id IS NOT NULL AND offer_design_run_id IS NULL AND offer_design_decision_id IS NULL)
  OR (from_state='PROCEED_TO_OFFER' AND to_state='OFFER_DESIGN' AND verdict_id IS NOT NULL AND offer_design_run_id IS NOT NULL AND offer_design_decision_id IS NULL)
  OR (from_state='OFFER_DESIGN' AND to_state IN ('OFFER_ACCEPTED','RETURN_FOR_TARGETED_RESEARCH','WAITING_FOR_OPERATOR_INPUT') AND verdict_id IS NOT NULL AND offer_design_run_id IS NOT NULL AND offer_design_decision_id IS NOT NULL)
  OR (from_state='WAITING_FOR_OPERATOR_INPUT' AND to_state='RETURN_FOR_IDEA_REFINEMENT' AND verdict_id IS NOT NULL AND offer_design_run_id IS NOT NULL AND offer_design_decision_id IS NOT NULL)
 )
);
ALTER TABLE record_cycle_states DROP CONSTRAINT record_cycle_states_check;
ALTER TABLE record_cycle_states ADD CONSTRAINT record_cycle_states_check CHECK (
 (state='IDEA_REFINEMENT' AND transition_ordinal=0 AND last_transition_id IS NULL)
 OR (state IN ('MARKET_RESEARCH','PROCEED_TO_OFFER','RETURN_FOR_REFINEMENT','WAITING_FOR_PIVOT_APPROVAL','KILLED','INCONCLUSIVE_REVIEW','OFFER_DESIGN','OFFER_ACCEPTED','RETURN_FOR_TARGETED_RESEARCH','RETURN_FOR_IDEA_REFINEMENT','WAITING_FOR_OPERATOR_INPUT') AND transition_ordinal BETWEEN 1 AND 5 AND last_transition_id IS NOT NULL)
);
CREATE UNIQUE INDEX uq_record_offer_design_accepted_run ON record_offer_design_decisions(run_id) WHERE outcome='ACCEPT';
CREATE UNIQUE INDEX uq_record_offer_acceptance_run ON record_offer_packages(proposal_id);
CREATE INDEX ix_record_offer_design_runs_cycle ON record_offer_design_runs(cycle_id, experiment_id);
CREATE INDEX ix_record_offer_design_decisions_run ON record_offer_design_decisions(run_id, experiment_id);
CREATE FUNCTION record_offer_design_run_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE verdict record_verdicts; bundle record_offer_bundles; envelope record_commercial_envelopes; state record_cycle_states;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable offer design run'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO verdict FROM record_verdicts WHERE id=NEW.verdict_id AND experiment_id=NEW.experiment_id;
 SELECT * INTO bundle FROM record_offer_bundles WHERE id=NEW.bundle_id AND experiment_id=NEW.experiment_id;
 SELECT * INTO envelope FROM record_commercial_envelopes WHERE id=NEW.envelope_id AND experiment_id=NEW.experiment_id;
 SELECT * INTO state FROM record_cycle_states WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id FOR UPDATE;
 IF verdict.id IS NULL OR verdict.verdict IS DISTINCT FROM 'PROCEED_TO_OFFER' OR verdict.cycle_id IS DISTINCT FROM NEW.cycle_id
  OR bundle.id IS NULL OR bundle.verdict_id IS DISTINCT FROM NEW.verdict_id OR envelope.id IS NULL OR envelope.bundle_id IS DISTINCT FROM NEW.bundle_id OR envelope.status IS DISTINCT FROM 'READY'
  OR state.cycle_id IS NULL OR state.state IS DISTINCT FROM 'PROCEED_TO_OFFER'
  OR NOT EXISTS(SELECT 1 FROM record_artifacts a WHERE a.id=envelope.artifact_id AND a.experiment_id=NEW.experiment_id AND a.kind='COMMERCIAL_DESIGN_ENVELOPE' AND a.version=envelope.artifact_version AND a.content_hash=envelope.artifact_hash)
  OR EXISTS(SELECT 1 FROM record_artifacts a JOIN record_artifacts later ON later.logical_id=a.logical_id AND later.version>a.version WHERE a.id=envelope.artifact_id)
  OR EXISTS(SELECT 1 FROM record_artifact_dispositions d WHERE d.artifact_id=envelope.artifact_id AND d.disposition='SUPERSEDED')
  OR NOT EXISTS(SELECT 1 FROM record_artifacts a WHERE a.id=NEW.prompt_artifact_id AND a.experiment_id=NEW.experiment_id AND a.kind='OUTREACH_PROMPT_CONFIGURATION' AND a.version=NEW.prompt_version AND a.content_hash=NEW.prompt_hash)
  OR NOT EXISTS(SELECT 1 FROM gov_configs c WHERE c.id=NEW.model_config_id AND c.workflow_id=NEW.model_config_workflow_id AND c.version=NEW.model_config_version)
 THEN RAISE EXCEPTION 'invalid offer design run lineage'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_offer_design_runs_guard BEFORE INSERT OR UPDATE OR DELETE ON record_offer_design_runs FOR EACH ROW EXECUTE FUNCTION record_offer_design_run_guard();
CREATE FUNCTION record_offer_design_decision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE run record_offer_design_runs; state record_cycle_states;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable offer design decision'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO run FROM record_offer_design_runs WHERE id=NEW.run_id AND experiment_id=NEW.experiment_id;
 SELECT * INTO state FROM record_cycle_states WHERE cycle_id=run.cycle_id AND experiment_id=NEW.experiment_id FOR UPDATE;
 IF run.id IS NULL OR state.cycle_id IS NULL OR state.state IS DISTINCT FROM 'OFFER_DESIGN'
  OR NOT EXISTS(SELECT 1 FROM record_artifacts a WHERE a.id=NEW.artifact_id AND a.experiment_id=NEW.experiment_id AND a.kind=NEW.artifact_kind AND a.version=NEW.artifact_version AND a.content_hash=NEW.artifact_hash)
  OR (NEW.outcome='ACCEPT' AND (
    NOT EXISTS(SELECT 1 FROM record_artifacts a WHERE a.id=NEW.artifact_id AND a.kind='VALIDATION_RESULT' AND a.payload->>'disposition'='PASS')
    OR (SELECT count(*) FROM record_artifact_links l WHERE l.consumer_id=NEW.artifact_id AND l.role='OFFER_DESIGN_PROPOSAL')<>1
    OR (SELECT count(*) FROM record_artifact_links l WHERE l.consumer_id=NEW.artifact_id AND l.role='OFFER_PACKAGE')<>1
    OR (SELECT count(*) FROM record_artifact_links l WHERE l.consumer_id=NEW.artifact_id AND l.role='OFFER_QUALIFICATION_PROFILE')<>1
    OR (SELECT count(*) FROM record_artifact_links l WHERE l.consumer_id=NEW.artifact_id AND l.role='INITIAL_OUTREACH_POLICY')<>1
    OR NOT EXISTS(
      SELECT 1 FROM record_offer_proposals proposal
      JOIN record_offer_packages package ON package.proposal_id=proposal.id AND package.offer_design_run_id=NEW.run_id
      JOIN record_offer_qualification_profiles profile ON profile.offer_id=package.id
      JOIN record_initial_outreach_policies policy ON policy.offer_id=package.id
      JOIN record_offer_acceptances acceptance ON acceptance.offer_id=package.id AND acceptance.profile_id=profile.id AND acceptance.policy_id=policy.id
      JOIN record_artifact_links proposal_link ON proposal_link.consumer_id=NEW.artifact_id AND proposal_link.role='OFFER_DESIGN_PROPOSAL' AND proposal_link.producer_id=proposal.artifact_id
      JOIN record_artifact_links package_link ON package_link.consumer_id=NEW.artifact_id AND package_link.role='OFFER_PACKAGE' AND package_link.producer_id=package.artifact_id
      JOIN record_artifact_links profile_link ON profile_link.consumer_id=NEW.artifact_id AND profile_link.role='OFFER_QUALIFICATION_PROFILE' AND profile_link.producer_id=profile.artifact_id
      JOIN record_artifact_links policy_link ON policy_link.consumer_id=NEW.artifact_id AND policy_link.role='INITIAL_OUTREACH_POLICY' AND policy_link.producer_id=policy.artifact_id
      WHERE proposal.offer_design_run_id=NEW.run_id
    )
  ))
 THEN RAISE EXCEPTION 'invalid offer design decision lineage'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_offer_design_decisions_guard BEFORE INSERT OR UPDATE OR DELETE ON record_offer_design_decisions FOR EACH ROW EXECUTE FUNCTION record_offer_design_decision_guard();
CREATE OR REPLACE FUNCTION record_cycle_transition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE current_state record_cycle_states; acceptance record_idea_acceptances;
 attempt record_research_attempts; accepted_artifact record_artifacts;
 command record_commands; committed record_verdicts; expected_state TEXT;
 offer_run record_offer_design_runs; offer_decision record_offer_design_decisions;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable cycle transition'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO current_state FROM record_cycle_states WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO acceptance FROM record_idea_acceptances WHERE id=NEW.idea_acceptance_id
  AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id
  AND artifact_id=NEW.idea_artifact_id AND artifact_kind=NEW.idea_kind
  AND artifact_version=NEW.idea_version AND artifact_hash=NEW.idea_hash;
 SELECT * INTO attempt FROM record_research_attempts WHERE id=NEW.research_attempt_id AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id;
 SELECT * INTO accepted_artifact FROM record_artifacts WHERE id=NEW.idea_artifact_id AND experiment_id=NEW.experiment_id AND kind=NEW.idea_kind AND version=NEW.idea_version AND content_hash=NEW.idea_hash;
 SELECT * INTO command FROM record_commands WHERE id=NEW.command_id;
 IF current_state.cycle_id IS NULL OR current_state.state IS DISTINCT FROM NEW.from_state
  OR current_state.transition_ordinal+1 IS DISTINCT FROM NEW.ordinal
  OR acceptance.id IS NULL OR attempt.id IS NULL OR accepted_artifact.id IS NULL
  OR command.id IS NULL OR command.experiment_id IS DISTINCT FROM NEW.experiment_id
 THEN RAISE EXCEPTION 'invalid cycle transition lineage'; END IF;
 IF NEW.from_state='PROCEED_TO_OFFER' THEN
  SELECT * INTO offer_run FROM record_offer_design_runs WHERE id=NEW.offer_design_run_id AND experiment_id=NEW.experiment_id;
  SELECT * INTO committed FROM record_verdicts WHERE id=NEW.verdict_id AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id AND attempt_id=NEW.research_attempt_id;
  IF NEW.to_state<>'OFFER_DESIGN' OR NEW.offer_design_decision_id IS NOT NULL
   OR offer_run.id IS NULL OR offer_run.cycle_id IS DISTINCT FROM NEW.cycle_id OR offer_run.verdict_id IS DISTINCT FROM NEW.verdict_id
   OR committed.id IS NULL OR committed.verdict<>'PROCEED_TO_OFFER'
   OR command.kind<>'START_OFFER_DESIGN' OR command.result_id IS DISTINCT FROM offer_run.id
  THEN RAISE EXCEPTION 'invalid offer design start transition'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.from_state='OFFER_DESIGN' THEN
  SELECT * INTO offer_run FROM record_offer_design_runs WHERE id=NEW.offer_design_run_id AND experiment_id=NEW.experiment_id;
  SELECT * INTO offer_decision FROM record_offer_design_decisions WHERE id=NEW.offer_design_decision_id AND run_id=NEW.offer_design_run_id AND experiment_id=NEW.experiment_id;
  SELECT * INTO committed FROM record_verdicts WHERE id=NEW.verdict_id AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id AND attempt_id=NEW.research_attempt_id;
  expected_state:=CASE offer_decision.outcome WHEN 'ACCEPT' THEN 'OFFER_ACCEPTED' WHEN 'TARGETED_RESEARCH_REQUIRED' THEN 'RETURN_FOR_TARGETED_RESEARCH' WHEN 'IDEA_REFINEMENT_RECOMMENDED' THEN 'WAITING_FOR_OPERATOR_INPUT' WHEN 'WAITING_FOR_OPERATOR_INPUT' THEN 'WAITING_FOR_OPERATOR_INPUT' END;
  IF offer_run.id IS NULL OR offer_run.cycle_id IS DISTINCT FROM NEW.cycle_id OR offer_run.verdict_id IS DISTINCT FROM NEW.verdict_id
   OR offer_decision.id IS NULL OR committed.id IS NULL OR committed.verdict<>'PROCEED_TO_OFFER'
   OR NEW.to_state IS DISTINCT FROM expected_state
   OR (offer_decision.outcome='ACCEPT' AND (
      command.kind<>'ACCEPT_OFFER' OR NOT EXISTS(
        SELECT 1 FROM record_offer_acceptances offer_acceptance
        JOIN record_offer_packages package ON package.id=offer_acceptance.offer_id
        JOIN record_offer_qualification_profiles profile ON profile.id=offer_acceptance.profile_id AND profile.offer_id=package.id
        JOIN record_initial_outreach_policies policy ON policy.id=offer_acceptance.policy_id AND policy.offer_id=package.id
        WHERE offer_acceptance.id=command.result_id AND package.offer_design_run_id=offer_run.id
      )
   ))
   OR (offer_decision.outcome='TARGETED_RESEARCH_REQUIRED' AND command.kind<>'RETURN_FOR_TARGETED_RESEARCH')
   OR (offer_decision.outcome IN ('IDEA_REFINEMENT_RECOMMENDED','WAITING_FOR_OPERATOR_INPUT') AND command.kind<>'DECIDE_OFFER_DESIGN')
  THEN RAISE EXCEPTION 'invalid offer design decision transition'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.from_state='WAITING_FOR_OPERATOR_INPUT' THEN
  SELECT * INTO offer_run FROM record_offer_design_runs WHERE id=NEW.offer_design_run_id AND experiment_id=NEW.experiment_id;
  SELECT * INTO offer_decision FROM record_offer_design_decisions WHERE id=NEW.offer_design_decision_id AND run_id=NEW.offer_design_run_id AND experiment_id=NEW.experiment_id;
  SELECT * INTO committed FROM record_verdicts WHERE id=NEW.verdict_id AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id AND attempt_id=NEW.research_attempt_id;
  IF NEW.to_state<>'RETURN_FOR_IDEA_REFINEMENT' OR offer_run.id IS NULL OR offer_decision.id IS NULL
   OR offer_decision.outcome<>'IDEA_REFINEMENT_RECOMMENDED' OR committed.verdict<>'PROCEED_TO_OFFER'
   OR command.kind<>'CONFIRM_OFFER_IDEA_REFINEMENT' OR command.result_id IS DISTINCT FROM NEW.offer_design_decision_id
  THEN RAISE EXCEPTION 'invalid offer idea-refinement return'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.ordinal=1 THEN
  IF attempt.ordinal<>1 OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
   OR EXISTS(SELECT 1 FROM record_artifacts later WHERE later.logical_id=accepted_artifact.logical_id AND later.version>accepted_artifact.version)
   OR EXISTS(SELECT 1 FROM record_artifact_dispositions disposition WHERE disposition.artifact_id=accepted_artifact.id AND disposition.disposition='SUPERSEDED')
   OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=attempt.plan_artifact_id AND role='ACCEPTED_IDEA')<>1
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=attempt.plan_artifact_id AND producer_id=accepted_artifact.id AND role='ACCEPTED_IDEA')
   OR command.kind NOT IN ('START_MARKET_RESEARCH','COMMIT_MARKET_RESEARCH_OUTCOME','DECIDE_MATERIAL_PIVOT','START_INCONCLUSIVE_SUPPLEMENT','RETURN_FOR_TARGETED_RESEARCH')
   OR (command.kind='START_MARKET_RESEARCH' AND (command.result_type<>'RESEARCH_ATTEMPT' OR command.result_id IS DISTINCT FROM NEW.research_attempt_id))
  THEN RAISE EXCEPTION 'invalid idea-to-research transition'; END IF;
 ELSE
  SELECT * INTO committed FROM record_verdicts WHERE id=NEW.verdict_id AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id AND attempt_id=NEW.research_attempt_id;
  IF committed.id IS NULL THEN RAISE EXCEPTION 'invalid committed verdict transition'; END IF;
  expected_state := CASE committed.verdict WHEN 'PROCEED_TO_OFFER' THEN 'PROCEED_TO_OFFER' WHEN 'REFINE_SAME_IDEA' THEN 'RETURN_FOR_REFINEMENT' WHEN 'MATERIAL_PIVOT_RECOMMENDED' THEN 'WAITING_FOR_PIVOT_APPROVAL' WHEN 'KILL_IDEA' THEN 'KILLED' WHEN 'INCONCLUSIVE' THEN 'INCONCLUSIVE_REVIEW' END;
  IF NEW.ordinal=2 AND (NEW.to_state IS DISTINCT FROM expected_state OR command.kind<>'COMMIT_MARKET_RESEARCH_OUTCOME' OR command.result_id IS DISTINCT FROM committed.id)
  THEN RAISE EXCEPTION 'verdict and cycle state disagree'; END IF;
  IF NEW.ordinal=3 AND NOT EXISTS(SELECT 1 FROM record_returns r WHERE r.verdict_id=committed.id AND r.experiment_id=NEW.experiment_id AND r.from_cycle_id=NEW.cycle_id AND ((NEW.from_state='WAITING_FOR_PIVOT_APPROVAL' AND r.kind='MATERIAL_PIVOT' AND command.kind='DECIDE_MATERIAL_PIVOT' AND EXISTS(SELECT 1 FROM record_pivot_decisions p WHERE p.verdict_id=committed.id AND p.cycle_id=r.to_cycle_id AND p.decision='APPROVED')) OR (NEW.from_state='INCONCLUSIVE_REVIEW' AND r.kind='INCONCLUSIVE_SUPPLEMENT' AND command.kind='START_INCONCLUSIVE_SUPPLEMENT')))
  THEN RAISE EXCEPTION 'return transition requires exact accepted continuation'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_cycle_return_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.ordinal>1 AND NOT EXISTS(
  SELECT 1 FROM record_returns r JOIN record_verdicts v ON v.id=r.verdict_id
  WHERE r.to_cycle_id=NEW.id AND r.from_cycle_id=NEW.parent_cycle_id
    AND r.experiment_id=NEW.experiment_id
    AND v.cycle_id=NEW.parent_cycle_id
    AND ((r.kind IN ('SAME_INTENT','MATERIAL_PIVOT') AND v.verdict IN ('REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED'))
      OR (r.kind='INCONCLUSIVE_SUPPLEMENT' AND v.verdict='INCONCLUSIVE')
      OR (r.kind='OFFER_GAP' AND v.verdict='PROCEED_TO_OFFER'))
 ) AND NOT EXISTS(
  SELECT 1 FROM record_cycle_transitions t
  JOIN record_offer_design_decisions d ON d.id=t.offer_design_decision_id
  JOIN record_commands c ON c.id=t.command_id
  JOIN record_idea_acceptances child_idea ON child_idea.cycle_id=NEW.id
  WHERE NEW.purpose='SAME_INTENT_RETURN'
    AND t.cycle_id=NEW.parent_cycle_id
    AND t.from_state='WAITING_FOR_OPERATOR_INPUT'
    AND t.to_state='RETURN_FOR_IDEA_REFINEMENT'
    AND d.outcome='IDEA_REFINEMENT_RECOMMENDED'
    AND c.kind='CONFIRM_OFFER_IDEA_REFINEMENT'
    AND c.result_id=d.id
    AND child_idea.experiment_id=NEW.experiment_id
 )
 THEN RAISE EXCEPTION 'research cycle requires exact committed return'; END IF;
 RETURN NULL;
END $$;
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM record_offer_design_runs) OR EXISTS(SELECT 1 FROM record_offer_design_decisions)
 THEN RAISE EXCEPTION 'cannot discard immutable offer design workflow history'; END IF;
END $$;
CREATE OR REPLACE FUNCTION record_cycle_return_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.ordinal>1 AND NOT EXISTS(
  SELECT 1 FROM record_returns r JOIN record_verdicts v ON v.id=r.verdict_id
  WHERE r.to_cycle_id=NEW.id AND r.from_cycle_id=NEW.parent_cycle_id
    AND r.experiment_id=NEW.experiment_id
    AND v.cycle_id=NEW.parent_cycle_id AND v.verdict IN ('REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED')
 )
 THEN RAISE EXCEPTION 'research cycle requires exact committed return'; END IF;
 RETURN NULL;
END $$;
DROP INDEX uq_record_offer_acceptance_run;
DROP INDEX uq_record_offer_design_accepted_run;
ALTER TABLE record_offer_packages DROP COLUMN offer_design_run_id;
ALTER TABLE record_offer_proposals DROP COLUMN offer_design_run_id;
ALTER TABLE record_offer_proposal_invalidations DROP CONSTRAINT record_offer_proposal_invalidations_reason_check;
ALTER TABLE record_offer_proposal_invalidations DROP COLUMN offer_gap_brief_id;
ALTER TABLE record_offer_proposal_invalidations ALTER COLUMN superseding_bundle_id SET NOT NULL;
ALTER TABLE record_offer_proposal_invalidations ADD CONSTRAINT record_offer_proposal_invalidations_reason_check CHECK (reason='SUPERSEDED_RESEARCH');
ALTER TABLE record_cycle_states DROP CONSTRAINT record_cycle_states_check;
ALTER TABLE record_cycle_states ADD CONSTRAINT record_cycle_states_check CHECK (
 (state='IDEA_REFINEMENT' AND transition_ordinal=0 AND last_transition_id IS NULL)
 OR (state IN ('MARKET_RESEARCH','PROCEED_TO_OFFER','RETURN_FOR_REFINEMENT','WAITING_FOR_PIVOT_APPROVAL','KILLED','INCONCLUSIVE_REVIEW') AND transition_ordinal BETWEEN 1 AND 3 AND last_transition_id IS NOT NULL)
);
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transitions_check;
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transitions_check CHECK (
 idea_kind='IDEA_BRIEF' AND ((ordinal=1 AND from_state='IDEA_REFINEMENT' AND to_state='MARKET_RESEARCH' AND verdict_id IS NULL) OR (ordinal=2 AND from_state='MARKET_RESEARCH' AND to_state IN ('PROCEED_TO_OFFER','RETURN_FOR_REFINEMENT','WAITING_FOR_PIVOT_APPROVAL','KILLED','INCONCLUSIVE_REVIEW') AND verdict_id IS NOT NULL) OR (ordinal=3 AND from_state IN ('WAITING_FOR_PIVOT_APPROVAL','INCONCLUSIVE_REVIEW') AND to_state='RETURN_FOR_REFINEMENT' AND verdict_id IS NOT NULL))
);
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transition_offer_decision_fk;
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transition_offer_run_fk;
ALTER TABLE record_cycle_transitions DROP COLUMN offer_design_decision_id;
ALTER TABLE record_cycle_transitions DROP COLUMN offer_design_run_id;
DROP TABLE record_offer_design_workflow_bindings;
DROP TABLE record_offer_design_decisions;
DROP FUNCTION record_offer_design_decision_guard();
DROP TABLE record_offer_design_runs;
DROP FUNCTION record_offer_design_run_guard();
""")
