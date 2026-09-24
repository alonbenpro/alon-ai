"""Durable supply bindings and immutable terminal accounting snapshots.

Revision ID: 20260923_20
Revises: 20260923_19
"""

from alembic import op

revision = "20260923_20"
down_revision = "20260923_19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE TABLE supply_workflow_bindings (
 dbos_workflow_id VARCHAR(220) PRIMARY KEY,
 application_version VARCHAR(64) NOT NULL,
 contract_version INTEGER NOT NULL,
 operation_kind VARCHAR(40) NOT NULL,
 experiment_id UUID NOT NULL REFERENCES gov_experiments(id),
 slot INTEGER,
 batch_id UUID,
 candidate_id UUID,
 subject_id UUID NOT NULL,
 request_hash VARCHAR(64) NOT NULL,
 request_payload JSONB NOT NULL,
 business_command_key UUID NOT NULL UNIQUE,
 command_id UUID UNIQUE REFERENCES record_commands(id),
 result_id UUID,
 delivery_state VARCHAR(32) NOT NULL,
 cancellation_outcome VARCHAR(40),
 created_at TIMESTAMPTZ NOT NULL,
 updated_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(batch_id,experiment_id) REFERENCES supply_batches(id,experiment_id),
 FOREIGN KEY(candidate_id,experiment_id) REFERENCES supply_candidates(id,experiment_id),
 CHECK(contract_version=1 AND request_hash ~ '^[0-9a-f]{64}$' AND jsonb_typeof(request_payload)='object'),
 CHECK(operation_kind IN ('CREATE','BEGIN_BATCH','ADMIT_CANDIDATE','RESOLVE_CONTACT','CLOSE_CONTACTABILITY','CLOSE_QUALIFICATION','STOP')),
 CHECK(slot IS NULL OR slot BETWEEN 1 AND 3),
 CHECK(delivery_state IN ('PENDING','STARTED','BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED','CANCELLED')),
 CHECK(cancellation_outcome IS NULL OR cancellation_outcome IN ('EFFECTIVE','INEFFECTIVE_ALREADY_COMMITTED')),
 CHECK((delivery_state IN ('PENDING','STARTED','CANCELLED') AND command_id IS NULL AND result_id IS NULL)
    OR (delivery_state IN ('BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED') AND command_id IS NOT NULL AND result_id IS NOT NULL))
);
CREATE INDEX ix_supply_workflow_bindings_recovery ON supply_workflow_bindings(application_version,delivery_state);
CREATE INDEX ix_supply_workflow_bindings_experiment ON supply_workflow_bindings(experiment_id,operation_kind);
CREATE FUNCTION supply_workflow_binding_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable supply workflow binding'; END IF;
 IF (to_jsonb(NEW)-ARRAY['command_id','result_id','delivery_state','cancellation_outcome','updated_at'])
    IS DISTINCT FROM
    (to_jsonb(OLD)-ARRAY['command_id','result_id','delivery_state','cancellation_outcome','updated_at'])
 THEN RAISE EXCEPTION 'immutable supply workflow identity'; END IF;
 IF NOT (
  (OLD.delivery_state='PENDING' AND NEW.delivery_state IN ('PENDING','STARTED','CANCELLED')) OR
  (OLD.delivery_state='STARTED' AND NEW.delivery_state IN ('STARTED','BUSINESS_COMMITTED','CANCELLED')) OR
  (OLD.delivery_state='BUSINESS_COMMITTED' AND NEW.delivery_state IN ('BUSINESS_COMMITTED','RECEIPT_DELIVERED')) OR
  (OLD.delivery_state='RECEIPT_DELIVERED' AND NEW.delivery_state IN ('RECEIPT_DELIVERED','RUNTIME_COMPLETED')) OR
  (OLD.delivery_state='RUNTIME_COMPLETED' AND NEW.delivery_state='RUNTIME_COMPLETED') OR
  (OLD.delivery_state='CANCELLED' AND NEW.delivery_state='CANCELLED')
 ) THEN RAISE EXCEPTION 'invalid supply workflow delivery transition'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER supply_workflow_binding_immutable BEFORE UPDATE OR DELETE ON supply_workflow_bindings
 FOR EACH ROW EXECUTE FUNCTION supply_workflow_binding_guard();

ALTER TABLE supply_outcomes
 ADD COLUMN classification VARCHAR(40),
 ADD COLUMN finalized_cost_ils NUMERIC,
 ADD COLUMN in_flight_call_count INTEGER,
 ADD COLUMN batch_yields JSONB,
 ADD COLUMN feedback_lineage JSONB,
 ADD COLUMN rejection_breakdown JSONB;
ALTER TABLE supply_outcomes ADD CONSTRAINT supply_outcome_snapshot_shape CHECK (
 (classification IS NULL AND finalized_cost_ils IS NULL AND in_flight_call_count IS NULL
  AND batch_yields IS NULL AND feedback_lineage IS NULL AND rejection_breakdown IS NULL)
 OR (classification IN ('TARGET_50_REACHED','CAMPAIGN_SUPPLY_INSUFFICIENT','CANCELLED','SAFETY_STOP')
  AND finalized_cost_ils>=0 AND in_flight_call_count>=0
  AND jsonb_typeof(batch_yields)='object' AND jsonb_typeof(feedback_lineage)='array'
  AND jsonb_typeof(rejection_breakdown)='object')
);

CREATE FUNCTION supply_outcome_snapshot_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 NEW.classification:=CASE NEW.reason
  WHEN 'TARGET_50_REACHED' THEN 'TARGET_50_REACHED'
  WHEN 'CANCELLED' THEN 'CANCELLED'
  WHEN 'SAFETY_STOP' THEN 'SAFETY_STOP'
  ELSE 'CAMPAIGN_SUPPLY_INSUFFICIENT' END;
 SELECT coalesce(sum(c.accrued_ils) FILTER (WHERE c.state='FINAL'),0),
        count(*) FILTER (WHERE c.state IN ('RESERVED','DISPATCHED','RECONCILING'))
 INTO NEW.finalized_cost_ils,NEW.in_flight_call_count
 FROM gov_calls c JOIN supply_operations o ON o.operation_id=c.operation_id
 WHERE o.experiment_id=NEW.experiment_id;
 SELECT coalesce(jsonb_object_agg(slot::text, yield ORDER BY slot),'{}'::jsonb)
 INTO NEW.batch_yields FROM (
  SELECT b.slot,jsonb_build_object(
   'candidates',(SELECT count(*) FROM supply_candidates x WHERE x.batch_id=b.id),
   'supported',(SELECT count(*) FROM supply_candidates x JOIN supply_contacts t ON t.candidate_id=x.id WHERE x.batch_id=b.id AND t.outcome='SUPPORTED'),
   'qualified',(SELECT count(*) FROM supply_candidates x JOIN record_current_supply_qualifications q ON q.candidate_id=x.id WHERE x.batch_id=b.id AND q.outcome='QUALIFIED')
  ) yield FROM supply_batches b WHERE b.experiment_id=NEW.experiment_id
 ) per_batch;
 SELECT coalesce(jsonb_agg(jsonb_build_object('id',f.id,'batch_id',f.batch_id,'gate',f.gate) ORDER BY b.slot),'[]'::jsonb)
 INTO NEW.feedback_lineage
 FROM supply_feedback f JOIN supply_batches b ON b.id=f.batch_id
 WHERE f.experiment_id=NEW.experiment_id;
 SELECT coalesce(jsonb_object_agg(reason,n ORDER BY reason),'{}'::jsonb)
 INTO NEW.rejection_breakdown FROM (
  SELECT coalesce(q.outcome,t.outcome,'UNTOUCHED') reason,count(*) n
  FROM supply_candidates x
  LEFT JOIN supply_contacts t ON t.candidate_id=x.id
  LEFT JOIN record_current_supply_qualifications q ON q.candidate_id=x.id
  WHERE x.experiment_id=NEW.experiment_id
  GROUP BY 1
 ) reasons;
 RETURN NEW;
END $$;
CREATE TRIGGER supply_outcome_snapshot BEFORE INSERT ON supply_outcomes FOR EACH ROW EXECUTE FUNCTION supply_outcome_snapshot_guard();

CREATE OR REPLACE FUNCTION record_readiness_target() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE')
 AND (SELECT count(*) FROM record_current_supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')=50 THEN
  INSERT INTO supply_outcomes(experiment_id,command_key,reason,achieved,batches_used,businesses_discovered)
  SELECT NEW.experiment_id,NEW.proposal_fact_id,'TARGET_50_REACHED',50,
   (SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id),
   (SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id);
 END IF;
 RETURN NEW;
END $$;
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
  INSERT INTO supply_outcomes(experiment_id,command_key,reason,achieved,batches_used,businesses_discovered)
  SELECT NEW.experiment_id,NEW.fact_id,'TARGET_50_REACHED',50,(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id),(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id);
 END IF;
 RETURN NEW;
END $$;
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM supply_workflow_bindings)
    OR EXISTS(SELECT 1 FROM supply_outcomes WHERE classification IS NOT NULL)
 THEN RAISE EXCEPTION 'cannot discard durable campaign-supply history'; END IF;
END $$;
CREATE OR REPLACE FUNCTION record_readiness_target() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE')
 AND (SELECT count(*) FROM record_current_supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')=50 THEN
  INSERT INTO supply_outcomes SELECT NEW.experiment_id,NEW.proposal_fact_id,'TARGET_50_REACHED',50,
   (SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id),
   (SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id);
 END IF;
 RETURN NEW;
END $$;
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
END $$;
DROP TRIGGER supply_outcome_snapshot ON supply_outcomes;
DROP FUNCTION supply_outcome_snapshot_guard();
ALTER TABLE supply_outcomes DROP CONSTRAINT supply_outcome_snapshot_shape;
ALTER TABLE supply_outcomes DROP COLUMN rejection_breakdown,DROP COLUMN feedback_lineage,DROP COLUMN batch_yields,
 DROP COLUMN in_flight_call_count,DROP COLUMN finalized_cost_ils,DROP COLUMN classification;
DROP TABLE supply_workflow_bindings;
DROP FUNCTION supply_workflow_binding_guard();
""")
