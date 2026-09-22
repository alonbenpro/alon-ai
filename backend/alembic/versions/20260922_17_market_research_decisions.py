"""Bounded market-research verdicts, returns and durable decision bindings.

Revision ID: 20260922_17
Revises: 20260922_16
"""

from alembic import op

revision = "20260922_17"
down_revision = "20260922_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transitions_check;
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transitions_research_attempt_id_key;
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transitions_command_id_key;
ALTER TABLE record_cycle_transitions ADD COLUMN verdict_id UUID;
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transition_verdict_fk FOREIGN KEY(verdict_id,experiment_id) REFERENCES record_verdicts(id,experiment_id);
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transitions_check CHECK (
 idea_kind='IDEA_BRIEF' AND ((ordinal=1 AND from_state='IDEA_REFINEMENT' AND to_state='MARKET_RESEARCH' AND verdict_id IS NULL)
 OR (ordinal=2 AND from_state='MARKET_RESEARCH' AND to_state IN ('PROCEED_TO_OFFER','RETURN_FOR_REFINEMENT','WAITING_FOR_PIVOT_APPROVAL','KILLED','INCONCLUSIVE_REVIEW') AND verdict_id IS NOT NULL)
 OR (ordinal=3 AND from_state IN ('WAITING_FOR_PIVOT_APPROVAL','INCONCLUSIVE_REVIEW') AND to_state='RETURN_FOR_REFINEMENT' AND verdict_id IS NOT NULL)));
CREATE INDEX ix_record_cycle_transitions_verdict ON record_cycle_transitions(verdict_id,experiment_id);
ALTER TABLE record_cycle_states DROP CONSTRAINT record_cycle_states_check;
ALTER TABLE record_cycle_states ADD CONSTRAINT record_cycle_states_check CHECK (
 (state='IDEA_REFINEMENT' AND transition_ordinal=0 AND last_transition_id IS NULL)
 OR (state IN ('MARKET_RESEARCH','PROCEED_TO_OFFER','RETURN_FOR_REFINEMENT','WAITING_FOR_PIVOT_APPROVAL','KILLED','INCONCLUSIVE_REVIEW') AND transition_ordinal BETWEEN 1 AND 3 AND last_transition_id IS NOT NULL));

ALTER TABLE record_pivot_decisions ADD COLUMN decision VARCHAR(16) NOT NULL DEFAULT 'APPROVED';
ALTER TABLE record_pivot_decisions ADD COLUMN decision_ordinal INTEGER NOT NULL DEFAULT 1;
ALTER TABLE record_pivot_decisions ADD COLUMN verdict_id UUID;
ALTER TABLE record_pivot_decisions ADD COLUMN reason_code VARCHAR(64);
ALTER TABLE record_pivot_decisions DISABLE TRIGGER record_pivot_decisions_guard;
WITH ordered AS (SELECT id,row_number() OVER (PARTITION BY cycle_id ORDER BY approved_at,id) AS ordinal FROM record_pivot_decisions)
UPDATE record_pivot_decisions p SET decision_ordinal=o.ordinal FROM ordered o WHERE o.id=p.id;
ALTER TABLE record_pivot_decisions ENABLE TRIGGER record_pivot_decisions_guard;
ALTER TABLE record_pivot_decisions ALTER COLUMN artifact_id DROP NOT NULL;
ALTER TABLE record_pivot_decisions ALTER COLUMN artifact_kind DROP NOT NULL;
ALTER TABLE record_pivot_decisions ALTER COLUMN artifact_version DROP NOT NULL;
ALTER TABLE record_pivot_decisions ALTER COLUMN artifact_hash DROP NOT NULL;
ALTER TABLE record_pivot_decisions ADD CONSTRAINT record_pivot_decision_verdict_fk FOREIGN KEY(verdict_id,experiment_id) REFERENCES record_verdicts(id,experiment_id);
ALTER TABLE record_pivot_decisions ADD CONSTRAINT record_pivot_decision_kind_check CHECK(decision IN ('APPROVED','DENIED') AND decision_ordinal>0);
ALTER TABLE record_pivot_decisions ADD CONSTRAINT record_pivot_decision_shape_check CHECK((decision='APPROVED' AND artifact_id IS NOT NULL AND artifact_kind IS NOT NULL AND artifact_version IS NOT NULL AND artifact_hash IS NOT NULL) OR (decision='DENIED' AND verdict_id IS NOT NULL AND reason_code IS NOT NULL AND artifact_id IS NULL AND artifact_kind IS NULL AND artifact_version IS NULL AND artifact_hash IS NULL));
CREATE UNIQUE INDEX uq_record_pivot_decision_verdict_ordinal ON record_pivot_decisions(verdict_id,decision_ordinal) WHERE verdict_id IS NOT NULL;
CREATE UNIQUE INDEX uq_record_pivot_decision_approved_verdict ON record_pivot_decisions(verdict_id) WHERE verdict_id IS NOT NULL AND decision='APPROVED';
CREATE INDEX ix_record_pivot_decisions_verdict ON record_pivot_decisions(verdict_id,experiment_id);


CREATE TABLE record_research_cycle_budgets (
	cycle_id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	workflow_id UUID NOT NULL,
	config_id UUID NOT NULL,
	config_version UUID NOT NULL,
	budget_account_id UUID NOT NULL,
	max_search_results INTEGER NOT NULL,
	max_capture_pages INTEGER NOT NULL,
	max_openai_calls INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (cycle_id),
	FOREIGN KEY(cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(workflow_id, experiment_id) REFERENCES record_workflows (id, experiment_id),
	FOREIGN KEY(config_id, workflow_id, config_version) REFERENCES gov_configs (id, workflow_id, version),
	FOREIGN KEY(budget_account_id) REFERENCES gov_budget_accounts (id),
	UNIQUE (workflow_id),
	CHECK (max_search_results>=0 AND max_capture_pages>=0 AND max_openai_calls>=0)
)

;
CREATE INDEX ix_record_research_cycle_budgets_fk_0 ON record_research_cycle_budgets (budget_account_id);
CREATE INDEX ix_record_research_cycle_budgets_fk_1 ON record_research_cycle_budgets (config_id, workflow_id, config_version);
CREATE INDEX ix_record_research_cycle_budgets_fk_2 ON record_research_cycle_budgets (cycle_id, experiment_id);
CREATE INDEX ix_record_research_cycle_budgets_fk_3 ON record_research_cycle_budgets (workflow_id, experiment_id);

CREATE TABLE record_research_return_blocks (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	cycle_id UUID NOT NULL,
	verdict_id UUID NOT NULL,
	return_kind VARCHAR(32) NOT NULL,
	reason_code VARCHAR(64) NOT NULL,
	decision_ordinal INTEGER,
	command_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(verdict_id, experiment_id) REFERENCES record_verdicts (id, experiment_id),
	FOREIGN KEY(command_id) REFERENCES record_commands (id),
	UNIQUE (command_id),
	CHECK (return_kind IN ('SAME_INTENT','MATERIAL_PIVOT','INCONCLUSIVE_SUPPLEMENT')),
	CHECK (reason_code IN ('BUDGET_EXHAUSTED','UNFINALIZED_USAGE','SAME_INTENT_LIMIT_REACHED','SUPPLEMENT_LIMIT_REACHED','CANCELLED','STALE_INPUT','MISSING_EVIDENCE','REPEATED_BLOCKER')),
	CHECK ((return_kind='MATERIAL_PIVOT' AND decision_ordinal>0) OR (return_kind<>'MATERIAL_PIVOT' AND decision_ordinal IS NULL))
)

;
CREATE INDEX ix_record_research_return_blocks_fk_0 ON record_research_return_blocks (command_id);
CREATE INDEX ix_record_research_return_blocks_fk_1 ON record_research_return_blocks (cycle_id, experiment_id);
CREATE INDEX ix_record_research_return_blocks_fk_2 ON record_research_return_blocks (verdict_id, experiment_id);

CREATE TABLE record_market_research_decision_workflow_bindings (
	dbos_workflow_id VARCHAR(200) NOT NULL,
	application_version VARCHAR(64) NOT NULL,
	contract_version INTEGER NOT NULL,
	operation_kind VARCHAR(32) NOT NULL,
	operation_id UUID NOT NULL,
	business_command_key UUID NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	request_payload JSONB NOT NULL,
	experiment_id UUID NOT NULL,
	cycle_id UUID NOT NULL,
	command_id UUID,
	result_id UUID,
	failure_code VARCHAR(64),
	delivery_state VARCHAR(32) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (dbos_workflow_id),
	FOREIGN KEY(cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(command_id) REFERENCES record_commands (id),
	UNIQUE (business_command_key),
	UNIQUE (operation_kind, operation_id, business_command_key),
	CHECK (request_hash ~ '^[0-9a-f]{64}$' AND contract_version=1 AND jsonb_typeof(request_payload)='object'),
	CHECK (operation_kind IN ('OUTCOME','PIVOT_DECISION','INCONCLUSIVE_SUPPLEMENT')),
	CHECK (delivery_state IN ('PENDING','STARTED','BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED','CANCELLED','REJECTED')),
	CHECK ((delivery_state IN ('PENDING','STARTED','CANCELLED') AND command_id IS NULL AND result_id IS NULL AND failure_code IS NULL) OR (delivery_state='REJECTED' AND command_id IS NULL AND result_id IS NULL AND failure_code ~ '^[A-Z][A-Z0-9_]{0,63}$') OR (delivery_state IN ('BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED') AND command_id IS NOT NULL AND result_id IS NOT NULL AND failure_code IS NULL))
)

;
CREATE INDEX ix_record_market_research_decision_workflow_bindings_fk_0 ON record_market_research_decision_workflow_bindings (command_id);
CREATE INDEX ix_record_market_research_decision_workflow_bindings_fk_1 ON record_market_research_decision_workflow_bindings (cycle_id, experiment_id);
CREATE OR REPLACE FUNCTION record_cycle_transition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE current_state record_cycle_states; acceptance record_idea_acceptances;
 attempt record_research_attempts; accepted_artifact record_artifacts;
 command record_commands; committed record_verdicts; expected_state TEXT;
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
 IF NEW.ordinal=1 THEN
  IF attempt.ordinal<>1 OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
   OR EXISTS(SELECT 1 FROM record_artifacts later WHERE later.logical_id=accepted_artifact.logical_id AND later.version>accepted_artifact.version)
   OR EXISTS(SELECT 1 FROM record_artifact_dispositions disposition WHERE disposition.artifact_id=accepted_artifact.id AND disposition.disposition='SUPERSEDED')
   OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=attempt.plan_artifact_id AND role='ACCEPTED_IDEA')<>1
   OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=attempt.plan_artifact_id AND producer_id=accepted_artifact.id AND role='ACCEPTED_IDEA')
   OR command.kind NOT IN ('START_MARKET_RESEARCH','COMMIT_MARKET_RESEARCH_OUTCOME','DECIDE_MATERIAL_PIVOT','START_INCONCLUSIVE_SUPPLEMENT')
   OR (command.kind='START_MARKET_RESEARCH' AND (command.result_type<>'RESEARCH_ATTEMPT' OR command.result_id IS DISTINCT FROM NEW.research_attempt_id))
  THEN RAISE EXCEPTION 'invalid idea-to-research transition'; END IF;
 ELSE
  SELECT * INTO committed FROM record_verdicts WHERE id=NEW.verdict_id AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id AND attempt_id=NEW.research_attempt_id;
  IF committed.id IS NULL THEN RAISE EXCEPTION 'invalid committed verdict transition'; END IF;
  expected_state := CASE committed.verdict WHEN 'PROCEED_TO_OFFER' THEN 'PROCEED_TO_OFFER' WHEN 'REFINE_SAME_IDEA' THEN 'RETURN_FOR_REFINEMENT' WHEN 'MATERIAL_PIVOT_RECOMMENDED' THEN 'WAITING_FOR_PIVOT_APPROVAL' WHEN 'KILL_IDEA' THEN 'KILLED' WHEN 'INCONCLUSIVE' THEN 'INCONCLUSIVE_REVIEW' END;
  IF NEW.ordinal=2 AND (NEW.to_state IS DISTINCT FROM expected_state
      OR command.kind<>'COMMIT_MARKET_RESEARCH_OUTCOME'
      OR command.result_id IS DISTINCT FROM committed.id)
  THEN RAISE EXCEPTION 'verdict and cycle state disagree'; END IF;
  IF NEW.ordinal=3 AND NOT EXISTS(SELECT 1 FROM record_returns r
      WHERE r.verdict_id=committed.id AND r.experiment_id=NEW.experiment_id
       AND r.from_cycle_id=NEW.cycle_id
       AND ((NEW.from_state='WAITING_FOR_PIVOT_APPROVAL' AND r.kind='MATERIAL_PIVOT' AND command.kind='DECIDE_MATERIAL_PIVOT'
         AND EXISTS(SELECT 1 FROM record_pivot_decisions p WHERE p.verdict_id=committed.id AND p.cycle_id=r.to_cycle_id AND p.decision='APPROVED'))
        OR (NEW.from_state='INCONCLUSIVE_REVIEW' AND r.kind='INCONCLUSIVE_SUPPLEMENT' AND command.kind='START_INCONCLUSIVE_SUPPLEMENT')))
  THEN RAISE EXCEPTION 'return transition requires exact accepted continuation'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION record_cycle_state_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'cycle state projection cannot be deleted';
 ELSIF TG_OP='INSERT' THEN
  IF NEW.state<>'IDEA_REFINEMENT' OR NEW.transition_ordinal<>0 OR NEW.last_transition_id IS NOT NULL
   OR EXISTS(SELECT 1 FROM record_cycle_transitions WHERE cycle_id=NEW.cycle_id)
  THEN RAISE EXCEPTION 'invalid initial cycle state'; END IF;
  RETURN NEW;
 END IF;
 IF (NEW.cycle_id,NEW.experiment_id) IS DISTINCT FROM (OLD.cycle_id,OLD.experiment_id)
  OR NEW.transition_ordinal<>OLD.transition_ordinal+1
  OR NOT EXISTS(SELECT 1 FROM record_cycle_transitions t WHERE t.id=NEW.last_transition_id
    AND t.cycle_id=NEW.cycle_id AND t.experiment_id=NEW.experiment_id
    AND t.ordinal=NEW.transition_ordinal AND t.from_state=OLD.state AND t.to_state=NEW.state)
  OR NEW.transition_ordinal IS DISTINCT FROM (SELECT max(ordinal) FROM record_cycle_transitions WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
 THEN RAISE EXCEPTION 'cycle state must follow transition history'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION record_cycle_transition_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM record_cycle_states s JOIN record_cycle_transitions t ON t.id=s.last_transition_id
  WHERE s.cycle_id=NEW.cycle_id AND s.experiment_id=NEW.experiment_id
    AND t.cycle_id=s.cycle_id AND t.experiment_id=s.experiment_id AND t.ordinal=s.transition_ordinal
    AND t.to_state=s.state AND s.transition_ordinal=(SELECT max(ordinal) FROM record_cycle_transitions WHERE cycle_id=NEW.cycle_id))
 THEN RAISE EXCEPTION 'cycle state projection is inconsistent with history'; END IF;
 IF NOT EXISTS(SELECT 1 FROM record_commands c JOIN record_audit a ON a.command_id=c.id
    JOIN record_outbox o ON o.command_id=c.id
    WHERE c.id=NEW.command_id AND c.experiment_id=NEW.experiment_id
     AND a.experiment_id=c.experiment_id AND a.kind=c.kind AND a.aggregate_id=c.result_id
     AND o.experiment_id=c.experiment_id AND o.aggregate_id=c.result_id AND o.aggregate_type=c.result_type
     AND o.topic='product-record.'||replace(lower(c.kind),'_','-'))
 THEN RAISE EXCEPTION 'missing command audit or outbox'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION record_research_pivot_decision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record_cycles; a record_artifacts; v record_verdicts;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable pivot decision'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO c FROM record_cycles WHERE id=NEW.cycle_id AND experiment_id=NEW.experiment_id;
 IF c.id IS NULL OR record_operator_authorized(NEW.experiment_id,NEW.approved_by) IS NOT TRUE
  OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
 THEN RAISE EXCEPTION 'pivot requires current cycle and authorized operator'; END IF;
 IF NEW.verdict_id IS NOT NULL THEN
  SELECT * INTO v FROM record_verdicts WHERE id=NEW.verdict_id AND experiment_id=NEW.experiment_id;
  IF v.id IS NULL OR v.verdict<>'MATERIAL_PIVOT_RECOMMENDED'
   OR (NEW.decision='DENIED' AND c.id IS DISTINCT FROM v.cycle_id)
   OR (NEW.decision='APPROVED' AND c.parent_cycle_id IS DISTINCT FROM v.cycle_id)
   OR NEW.decision_ordinal<>(SELECT count(*)+1 FROM record_pivot_decisions WHERE verdict_id=NEW.verdict_id)
   OR NOT EXISTS(SELECT 1 FROM record_cycle_states WHERE cycle_id=v.cycle_id AND state='WAITING_FOR_PIVOT_APPROVAL')
  THEN RAISE EXCEPTION 'invalid pivot verdict lineage or ordinal'; END IF;
 ELSE
  IF NEW.decision<>'APPROVED' OR NEW.decision_ordinal<>(SELECT count(*)+1 FROM record_pivot_decisions WHERE cycle_id=NEW.cycle_id AND verdict_id IS NULL)
  THEN RAISE EXCEPTION 'invalid legacy pivot approval'; END IF;
 END IF;
 IF NEW.decision='APPROVED' THEN
  SELECT * INTO a FROM record_artifacts WHERE id=NEW.artifact_id;
  IF a.payload->'material_pivot' IS DISTINCT FROM 'true'::jsonb
  THEN RAISE EXCEPTION 'invalid material pivot approval'; END IF;
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER record_pivot_decisions_guard ON record_pivot_decisions;
CREATE TRIGGER record_pivot_decisions_guard BEFORE INSERT OR UPDATE OR DELETE ON record_pivot_decisions
 FOR EACH ROW EXECUTE FUNCTION record_research_pivot_decision_guard();

CREATE FUNCTION record_research_budget_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE account gov_budget_accounts;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable research cycle budget'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO account FROM gov_budget_accounts WHERE id=NEW.budget_account_id;
 IF account.id IS NULL OR account.scope<>'WORKFLOW' OR account.experiment_id IS DISTINCT FROM NEW.experiment_id
  OR account.workflow_id IS DISTINCT FROM NEW.workflow_id OR account.frozen
  OR account.effective_at>NEW.created_at OR account.expires_at<=NEW.created_at
 THEN RAISE EXCEPTION 'invalid research workflow budget'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_research_cycle_budgets_guard BEFORE INSERT OR UPDATE OR DELETE ON record_research_cycle_budgets FOR EACH ROW EXECUTE FUNCTION record_research_budget_guard();

CREATE FUNCTION record_research_return_block_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable research return block'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF NOT EXISTS(SELECT 1 FROM record_verdicts v WHERE v.id=NEW.verdict_id AND v.cycle_id=NEW.cycle_id AND v.experiment_id=NEW.experiment_id
  AND ((v.verdict='REFINE_SAME_IDEA' AND NEW.return_kind='SAME_INTENT') OR (v.verdict='MATERIAL_PIVOT_RECOMMENDED' AND NEW.return_kind='MATERIAL_PIVOT') OR (v.verdict='INCONCLUSIVE' AND NEW.return_kind='INCONCLUSIVE_SUPPLEMENT')))
 THEN RAISE EXCEPTION 'invalid return block verdict lineage'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_research_return_blocks_guard BEFORE INSERT OR UPDATE OR DELETE ON record_research_return_blocks FOR EACH ROW EXECUTE FUNCTION record_research_return_block_guard();
CREATE FUNCTION record_research_block_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM record_commands c JOIN record_audit a ON a.command_id=c.id JOIN record_outbox o ON o.command_id=c.id
   WHERE c.id=NEW.command_id AND c.experiment_id=NEW.experiment_id
   AND a.experiment_id=c.experiment_id AND a.aggregate_id=c.result_id AND a.kind=c.kind
   AND o.experiment_id=c.experiment_id AND o.aggregate_id=c.result_id AND o.aggregate_type=c.result_type)
 THEN RAISE EXCEPTION 'missing blocked continuation receipt audit or outbox'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER record_research_block_consistency AFTER INSERT ON record_research_return_blocks DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION record_research_block_consistency();

CREATE FUNCTION record_research_decision_binding_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prefix TEXT; c record_commands;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable research decision workflow binding'; END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF TG_OP='INSERT' THEN
  prefix:=CASE NEW.operation_kind WHEN 'OUTCOME' THEN 'market-research-outcome' WHEN 'PIVOT_DECISION' THEN 'material-pivot-decision' WHEN 'INCONCLUSIVE_SUPPLEMENT' THEN 'inconclusive-supplement' END;
  IF NEW.dbos_workflow_id IS DISTINCT FROM prefix||':'||NEW.operation_id::text||':'||
    (CASE WHEN NEW.operation_kind='PIVOT_DECISION' THEN NEW.request_payload->>'decision_id'
          ELSE NEW.business_command_key::text END)
    OR NEW.delivery_state<>'PENDING' THEN RAISE EXCEPTION 'invalid research decision workflow identity'; END IF;
  IF (NEW.operation_kind='OUTCOME' AND NOT EXISTS(SELECT 1 FROM record_research_attempts WHERE id=NEW.operation_id AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id))
    OR (NEW.operation_kind<>'OUTCOME' AND NOT EXISTS(SELECT 1 FROM record_verdicts WHERE id=NEW.operation_id AND cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id))
  THEN RAISE EXCEPTION 'invalid research decision workflow operation'; END IF;
  RETURN NEW;
 END IF;
 IF (to_jsonb(NEW)-ARRAY['command_id','result_id','failure_code','delivery_state','updated_at']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['command_id','result_id','failure_code','delivery_state','updated_at'])
 THEN RAISE EXCEPTION 'immutable research decision workflow identity'; END IF;
 IF NOT ((OLD.delivery_state='PENDING' AND NEW.delivery_state IN ('STARTED','CANCELLED'))
   OR (OLD.delivery_state='STARTED' AND NEW.delivery_state IN ('BUSINESS_COMMITTED','CANCELLED','REJECTED'))
   OR (OLD.delivery_state='BUSINESS_COMMITTED' AND NEW.delivery_state='RECEIPT_DELIVERED')
   OR (OLD.delivery_state='RECEIPT_DELIVERED' AND NEW.delivery_state='RUNTIME_COMPLETED'))
 THEN RAISE EXCEPTION 'invalid research decision workflow delivery transition'; END IF;
 IF OLD.command_id IS NOT NULL AND (NEW.command_id,NEW.result_id) IS DISTINCT FROM (OLD.command_id,OLD.result_id)
 THEN RAISE EXCEPTION 'immutable research decision workflow receipt'; END IF;
 IF NEW.delivery_state='CANCELLED' AND EXISTS(SELECT 1 FROM record_commands WHERE command_key=NEW.business_command_key)
 THEN RAISE EXCEPTION 'committed research decision workflow cannot be cancelled'; END IF;
 IF NEW.command_id IS NOT NULL THEN
  SELECT * INTO c FROM record_commands WHERE id=NEW.command_id;
  IF c.id IS NULL OR c.command_key IS DISTINCT FROM NEW.business_command_key OR c.request_hash IS DISTINCT FROM NEW.request_hash
   OR c.experiment_id IS DISTINCT FROM NEW.experiment_id OR c.result_id IS DISTINCT FROM NEW.result_id
   OR c.kind IS DISTINCT FROM (CASE NEW.operation_kind WHEN 'OUTCOME' THEN 'COMMIT_MARKET_RESEARCH_OUTCOME' WHEN 'PIVOT_DECISION' THEN 'DECIDE_MATERIAL_PIVOT' WHEN 'INCONCLUSIVE_SUPPLEMENT' THEN 'START_INCONCLUSIVE_SUPPLEMENT' END)
  THEN RAISE EXCEPTION 'invalid research decision workflow receipt lineage'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_market_research_decision_workflow_bindings_guard BEFORE INSERT OR UPDATE OR DELETE ON record_market_research_decision_workflow_bindings FOR EACH ROW EXECUTE FUNCTION record_research_decision_binding_guard();

CREATE FUNCTION record_managed_return_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE outcome_command UUID; child_kind TEXT;
BEGIN
 SELECT transition.command_id INTO outcome_command
 FROM record_cycle_transitions transition
 JOIN record_commands command ON command.id=transition.command_id
 WHERE transition.verdict_id=NEW.verdict_id
   AND command.kind='COMMIT_MARKET_RESEARCH_OUTCOME';
 IF outcome_command IS NULL THEN RETURN NULL; END IF;
 SELECT command.kind INTO child_kind
 FROM record_cycle_transitions transition
 JOIN record_commands command ON command.id=transition.command_id
 WHERE transition.cycle_id=NEW.to_cycle_id AND transition.ordinal=1;
 IF (NEW.kind='SAME_INTENT' AND NOT EXISTS(
       SELECT 1 FROM record_cycle_transitions WHERE cycle_id=NEW.to_cycle_id
        AND ordinal=1 AND command_id=outcome_command))
    OR (NEW.kind='MATERIAL_PIVOT' AND child_kind IS DISTINCT FROM 'DECIDE_MATERIAL_PIVOT')
    OR (NEW.kind='INCONCLUSIVE_SUPPLEMENT' AND child_kind IS DISTINCT FROM 'START_INCONCLUSIVE_SUPPLEMENT')
 THEN RAISE EXCEPTION 'managed verdict requires managed continuation command'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER record_managed_return_consistency
 AFTER INSERT ON record_returns DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION record_managed_return_consistency();

""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM record_cycle_transitions WHERE ordinal>1)
  OR EXISTS(SELECT 1 FROM record_pivot_decisions WHERE verdict_id IS NOT NULL OR decision<>'APPROVED')
  OR EXISTS(SELECT 1 FROM record_research_cycle_budgets)
  OR EXISTS(SELECT 1 FROM record_research_return_blocks)
  OR EXISTS(SELECT 1 FROM record_market_research_decision_workflow_bindings)
 THEN RAISE EXCEPTION 'cannot discard immutable market research decision history'; END IF;
END $$;
DROP TRIGGER record_managed_return_consistency ON record_returns;
DROP FUNCTION record_managed_return_consistency();
DROP TABLE record_market_research_decision_workflow_bindings;
DROP FUNCTION record_research_decision_binding_guard();
DROP TABLE record_research_return_blocks;
DROP FUNCTION record_research_block_consistency();
DROP FUNCTION record_research_return_block_guard();
DROP TABLE record_research_cycle_budgets;
DROP FUNCTION record_research_budget_guard();
DROP TRIGGER record_pivot_decisions_guard ON record_pivot_decisions;
DROP FUNCTION record_research_pivot_decision_guard();
CREATE TRIGGER record_pivot_decisions_guard BEFORE INSERT OR UPDATE OR DELETE ON record_pivot_decisions FOR EACH ROW EXECUTE FUNCTION record_guard();
DROP INDEX uq_record_pivot_decision_verdict_ordinal;
DROP INDEX uq_record_pivot_decision_approved_verdict;
DROP INDEX ix_record_pivot_decisions_verdict;
ALTER TABLE record_pivot_decisions DROP CONSTRAINT record_pivot_decision_verdict_fk;
ALTER TABLE record_pivot_decisions DROP CONSTRAINT record_pivot_decision_kind_check;
ALTER TABLE record_pivot_decisions DROP CONSTRAINT record_pivot_decision_shape_check;
ALTER TABLE record_pivot_decisions DROP COLUMN decision;
ALTER TABLE record_pivot_decisions DROP COLUMN decision_ordinal;
ALTER TABLE record_pivot_decisions DROP COLUMN verdict_id;
ALTER TABLE record_pivot_decisions DROP COLUMN reason_code;
ALTER TABLE record_pivot_decisions ALTER COLUMN artifact_id SET NOT NULL;
ALTER TABLE record_pivot_decisions ALTER COLUMN artifact_kind SET NOT NULL;
ALTER TABLE record_pivot_decisions ALTER COLUMN artifact_version SET NOT NULL;
ALTER TABLE record_pivot_decisions ALTER COLUMN artifact_hash SET NOT NULL;
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transitions_check;
ALTER TABLE record_cycle_transitions DROP CONSTRAINT record_cycle_transition_verdict_fk;
ALTER TABLE record_cycle_transitions DROP COLUMN verdict_id;
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transitions_research_attempt_id_key UNIQUE(research_attempt_id);
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transitions_command_id_key UNIQUE(command_id);
ALTER TABLE record_cycle_transitions ADD CONSTRAINT record_cycle_transitions_check CHECK(ordinal=1 AND from_state='IDEA_REFINEMENT' AND to_state='MARKET_RESEARCH' AND idea_kind='IDEA_BRIEF');
ALTER TABLE record_cycle_states DROP CONSTRAINT record_cycle_states_check;
ALTER TABLE record_cycle_states ADD CONSTRAINT record_cycle_states_check CHECK((state='IDEA_REFINEMENT' AND transition_ordinal=0 AND last_transition_id IS NULL) OR (state='MARKET_RESEARCH' AND transition_ordinal=1 AND last_transition_id IS NOT NULL));

CREATE OR REPLACE FUNCTION record_cycle_transition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
 current_state record_cycle_states;
 acceptance record_idea_acceptances;
 attempt record_research_attempts;
 accepted_artifact record_artifacts;
 command record_commands;
BEGIN
 IF TG_OP<>'INSERT' THEN
  RAISE EXCEPTION 'immutable cycle transition';
 END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO current_state FROM record_cycle_states
  WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO acceptance FROM record_idea_acceptances
  WHERE id=NEW.idea_acceptance_id AND cycle_id=NEW.cycle_id
   AND experiment_id=NEW.experiment_id AND artifact_id=NEW.idea_artifact_id
   AND artifact_kind=NEW.idea_kind AND artifact_version=NEW.idea_version
   AND artifact_hash=NEW.idea_hash;
 SELECT * INTO attempt FROM record_research_attempts
  WHERE id=NEW.research_attempt_id AND cycle_id=NEW.cycle_id
   AND experiment_id=NEW.experiment_id;
 SELECT * INTO accepted_artifact FROM record_artifacts
  WHERE id=NEW.idea_artifact_id AND experiment_id=NEW.experiment_id
   AND kind=NEW.idea_kind AND version=NEW.idea_version
   AND content_hash=NEW.idea_hash;
 SELECT * INTO command FROM record_commands WHERE id=NEW.command_id;
 IF current_state.cycle_id IS NULL
    OR current_state.state IS DISTINCT FROM NEW.from_state
    OR current_state.transition_ordinal+1 IS DISTINCT FROM NEW.ordinal
    OR acceptance.id IS NULL OR attempt.id IS NULL OR accepted_artifact.id IS NULL
    OR attempt.ordinal<>1
    OR NEW.cycle_id IS DISTINCT FROM (
       SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id
       ORDER BY ordinal DESC LIMIT 1)
    OR EXISTS(SELECT 1 FROM record_artifacts later
       WHERE later.logical_id=accepted_artifact.logical_id
        AND later.version>accepted_artifact.version)
    OR EXISTS(SELECT 1 FROM record_artifact_dispositions disposition
       WHERE disposition.artifact_id=accepted_artifact.id
        AND disposition.disposition='SUPERSEDED')
    OR (SELECT count(*) FROM record_artifact_links
        WHERE consumer_id=attempt.plan_artifact_id AND role='ACCEPTED_IDEA')<>1
    OR NOT EXISTS(SELECT 1 FROM record_artifact_links
        WHERE consumer_id=attempt.plan_artifact_id
         AND producer_id=accepted_artifact.id AND role='ACCEPTED_IDEA')
    OR command.id IS NULL OR command.experiment_id IS DISTINCT FROM NEW.experiment_id
    OR command.kind<>'START_MARKET_RESEARCH'
    OR command.result_type<>'RESEARCH_ATTEMPT'
    OR command.result_id IS DISTINCT FROM NEW.research_attempt_id
 THEN RAISE EXCEPTION 'invalid idea-to-research transition'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_cycle_state_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'cycle state projection cannot be deleted';
 ELSIF TG_OP='INSERT' THEN
  IF NEW.state<>'IDEA_REFINEMENT' OR NEW.transition_ordinal<>0
     OR NEW.last_transition_id IS NOT NULL
     OR EXISTS(SELECT 1 FROM record_cycle_transitions WHERE cycle_id=NEW.cycle_id)
  THEN RAISE EXCEPTION 'invalid initial cycle state'; END IF;
  RETURN NEW;
 END IF;
 IF OLD.state<>'IDEA_REFINEMENT' OR OLD.transition_ordinal<>0
    OR OLD.last_transition_id IS NOT NULL
    OR NEW.state<>'MARKET_RESEARCH' OR NEW.transition_ordinal<>1
    OR NEW.last_transition_id IS NULL
    OR NOT EXISTS(SELECT 1 FROM record_cycle_transitions transition
       WHERE transition.id=NEW.last_transition_id
        AND transition.cycle_id=NEW.cycle_id
        AND transition.experiment_id=NEW.experiment_id
        AND transition.ordinal=NEW.transition_ordinal
        AND transition.from_state=OLD.state
        AND transition.to_state=NEW.state)
    OR NEW.transition_ordinal IS DISTINCT FROM (
       SELECT max(ordinal) FROM record_cycle_transitions
        WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
 THEN RAISE EXCEPTION 'cycle state must follow transition history'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_cycle_transition_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM record_cycle_states state
  WHERE state.cycle_id=NEW.cycle_id AND state.experiment_id=NEW.experiment_id
   AND state.state=NEW.to_state AND state.transition_ordinal=NEW.ordinal
   AND state.last_transition_id=NEW.id)
 THEN RAISE EXCEPTION 'cycle state projection is inconsistent with history';
 ELSIF NOT EXISTS(SELECT 1 FROM record_audit audit
   WHERE audit.command_id=NEW.command_id
    AND audit.experiment_id=NEW.experiment_id
    AND audit.kind='START_MARKET_RESEARCH'
    AND audit.aggregate_id=NEW.research_attempt_id)
   OR NOT EXISTS(SELECT 1 FROM record_outbox outbox
   WHERE outbox.command_id=NEW.command_id
    AND outbox.experiment_id=NEW.experiment_id
    AND outbox.topic='product-record.start-market-research'
    AND outbox.aggregate_type='RESEARCH_ATTEMPT'
    AND outbox.aggregate_id=NEW.research_attempt_id)
 THEN RAISE EXCEPTION 'missing command audit or outbox'; END IF;
 RETURN NULL;
END $$;
""")
