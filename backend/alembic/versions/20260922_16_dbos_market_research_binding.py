"""DBOS binding for the first durable market-research transition.

Revision ID: 20260922_16
Revises: 20260922_15
"""

from alembic import op

revision = "20260922_16"
down_revision = "20260922_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE TABLE record_market_research_workflow_bindings (
 dbos_workflow_id VARCHAR(200) PRIMARY KEY,
 application_version VARCHAR(64) NOT NULL,
 request_hash VARCHAR(64) NOT NULL,
 business_command_key UUID NOT NULL UNIQUE,
 experiment_id UUID NOT NULL,
 cycle_id UUID NOT NULL,
 transition_kind VARCHAR(64) NOT NULL,
 from_state VARCHAR(32) NOT NULL,
 to_state VARCHAR(32) NOT NULL,
 transition_id UUID,
 command_id UUID,
 delivery_state VARCHAR(32) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL,
 updated_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(cycle_id,experiment_id) REFERENCES record_cycles(id,experiment_id),
 FOREIGN KEY(transition_id) REFERENCES record_cycle_transitions(id),
 FOREIGN KEY(command_id) REFERENCES record_commands(id),
 UNIQUE(cycle_id,experiment_id,transition_kind),
 CHECK(request_hash ~ '^[0-9a-f]{64}$'),
 CHECK(transition_kind='IDEA_REFINEMENT_TO_MARKET_RESEARCH'
  AND from_state='IDEA_REFINEMENT' AND to_state='MARKET_RESEARCH'),
 CHECK(delivery_state IN
  ('PENDING','STARTED','BUSINESS_COMMITTED','RECEIPT_DELIVERED',
   'RUNTIME_COMPLETED','CANCELLED')),
 CHECK((delivery_state IN ('PENDING','STARTED','CANCELLED')
         AND transition_id IS NULL AND command_id IS NULL)
    OR (delivery_state IN
         ('BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED')
         AND transition_id IS NOT NULL AND command_id IS NOT NULL))
);
CREATE INDEX ix_record_market_research_workflow_bindings_pending
 ON record_market_research_workflow_bindings(application_version,delivery_state);
CREATE INDEX ix_record_market_research_workflow_bindings_cycle
 ON record_market_research_workflow_bindings(cycle_id,experiment_id);

CREATE FUNCTION record_market_research_workflow_binding_guard()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'immutable market research workflow binding';
 ELSIF TG_OP='INSERT' THEN
  IF NEW.delivery_state<>'PENDING' OR NEW.transition_id IS NOT NULL
     OR NEW.command_id IS NOT NULL THEN
   RAISE EXCEPTION 'invalid initial market research workflow binding';
  END IF;
  RETURN NEW;
 END IF;
 IF (NEW.dbos_workflow_id,NEW.application_version,NEW.request_hash,
     NEW.business_command_key,NEW.experiment_id,NEW.cycle_id,
     NEW.transition_kind,NEW.from_state,NEW.to_state,NEW.created_at)
    IS DISTINCT FROM
    (OLD.dbos_workflow_id,OLD.application_version,OLD.request_hash,
     OLD.business_command_key,OLD.experiment_id,OLD.cycle_id,
     OLD.transition_kind,OLD.from_state,OLD.to_state,OLD.created_at)
 THEN RAISE EXCEPTION 'immutable market research workflow identity'; END IF;
 IF NOT ((OLD.delivery_state='PENDING' AND NEW.delivery_state IN ('STARTED','CANCELLED'))
      OR (OLD.delivery_state='STARTED' AND NEW.delivery_state IN ('BUSINESS_COMMITTED','CANCELLED'))
      OR (OLD.delivery_state='BUSINESS_COMMITTED' AND NEW.delivery_state='RECEIPT_DELIVERED')
      OR (OLD.delivery_state='RECEIPT_DELIVERED' AND NEW.delivery_state='RUNTIME_COMPLETED'))
 THEN RAISE EXCEPTION 'invalid market research workflow delivery transition'; END IF;
 IF NEW.delivery_state='CANCELLED' AND EXISTS(
    SELECT 1 FROM record_cycle_transitions transition
     WHERE transition.cycle_id=NEW.cycle_id
       AND transition.experiment_id=NEW.experiment_id)
 THEN RAISE EXCEPTION 'committed market research workflow cannot be cancelled'; END IF;
 IF NEW.delivery_state IN
    ('BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED')
    AND NOT EXISTS(
      SELECT 1 FROM record_cycle_transitions transition
      JOIN record_commands command ON command.id=transition.command_id
      WHERE transition.id=NEW.transition_id
        AND transition.cycle_id=NEW.cycle_id
        AND transition.experiment_id=NEW.experiment_id
        AND transition.from_state=NEW.from_state
        AND transition.to_state=NEW.to_state
        AND command.id=NEW.command_id
        AND command.command_key=NEW.business_command_key
        AND command.request_hash=NEW.request_hash)
 THEN RAISE EXCEPTION 'invalid market research workflow receipt lineage'; END IF;
 RETURN NEW;
END $$;

CREATE TRIGGER record_market_research_workflow_bindings_guard
 BEFORE INSERT OR UPDATE OR DELETE ON record_market_research_workflow_bindings
 FOR EACH ROW EXECUTE FUNCTION record_market_research_workflow_binding_guard();
""")


def downgrade() -> None:
    op.execute(r"""
DROP TRIGGER record_market_research_workflow_bindings_guard
 ON record_market_research_workflow_bindings;
DROP FUNCTION record_market_research_workflow_binding_guard();
DROP TABLE record_market_research_workflow_bindings;
""")
