"""Allow precisely settled research failures in a successful combined Idea proof.

Failed research stays failed. Model success, output binding and provider call
lineage remain mandatory; unknown accounting and other denials cannot qualify.
"""

from alembic import op

revision = "20261005_31"
down_revision = "20260928_30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE OR REPLACE FUNCTION record_combined_idea_proof(
 p_run_id uuid,p_experiment_id uuid,p_operation_id uuid,p_task_kind text,p_output_hash text
) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(
   SELECT 1 FROM record_agent_runs parent
   JOIN record_agent_run_steps saved ON saved.run_id=parent.run_id
     AND saved.experiment_id=parent.experiment_id
   WHERE parent.run_id=p_run_id AND parent.experiment_id=p_experiment_id
     AND parent.task_kind=p_task_kind AND parent.provider_mode='live'
     AND parent.status='RUNNING'
     AND saved.kind='ARTIFACT_SAVE' AND saved.status='SUCCEEDED'
     AND saved.operation_id=p_operation_id AND saved.output_hash=p_output_hash
 ) AND EXISTS(
   SELECT 1 FROM record_agent_run_steps model
   JOIN record_agent_runs parent ON parent.run_id=model.run_id
     AND parent.experiment_id=model.experiment_id
   JOIN gov_calls call ON call.id=model.provider_call_id
     AND call.idempotency_key=model.step_key
     AND call.experiment_id=model.experiment_id
     AND call.operation_id=model.operation_id
     AND call.created_at>=parent.started_at
     AND call.state='FINAL'
   WHERE model.run_id=p_run_id AND model.experiment_id=p_experiment_id
     AND model.kind='MODEL_REQUEST' AND model.status='SUCCEEDED'
     AND model.operation_id=p_operation_id
 ) AND NOT EXISTS(
   SELECT 1 FROM record_agent_run_steps child
   JOIN record_agent_runs parent ON parent.run_id=child.run_id
     AND parent.experiment_id=child.experiment_id
   LEFT JOIN gov_calls call ON call.id=child.provider_call_id
     AND call.idempotency_key=child.step_key
     AND call.experiment_id=child.experiment_id
     AND call.operation_id=child.operation_id
     AND call.created_at>=parent.started_at
   WHERE child.run_id=p_run_id AND child.experiment_id=p_experiment_id
     AND child.kind<>'ARTIFACT_SAVE'
     AND (child.operation_id IS DISTINCT FROM p_operation_id OR call.id IS NULL
       OR NOT COALESCE(
         (child.status='SUCCEEDED' AND call.state='FINAL')
         OR (
           child.kind IN ('FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_JS_RETRIEVAL')
           AND child.status='FAILED' AND child.reason_code='MALFORMED_RESPONSE'
           AND call.state='FINAL' AND call.currency='USD'
           AND call.accrued=0 AND call.accrued_ils=0
           AND call.result_metadata->>'capability'=child.kind
           AND call.result_metadata->>'status'='FAILED'
           AND call.result_metadata->>'error_code'='MALFORMED_RESPONSE'
           AND EXISTS(
             SELECT 1 FROM gov_configs cfg
             JOIN gov_config_prices bound ON bound.config_id=cfg.id
             JOIN gov_prices price ON price.id=bound.price_id
             WHERE cfg.id=call.config_id AND cfg.id=child.config_ref
               AND cfg.capability=child.kind AND price.capability=child.kind
               AND price.component='CAPTURE_PAGE' AND price.currency='USD'
               AND price.unit_price=0 AND price.unit_quantity=1 AND bound.max_quantity=1
               AND (SELECT count(*) FROM gov_config_prices WHERE config_id=cfg.id)=1
           )
           AND NOT EXISTS(SELECT 1 FROM gov_retained WHERE call_id=call.id)
         )
         OR (
           child.kind IN ('BRAVE_SEARCH','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE',
             'FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL')
           AND child.status='BLOCKED' AND child.reason_code='CIRCUIT'
           AND call.state='RELEASED' AND call.dispatch_at IS NULL
           AND call.accrued=0 AND call.accrued_ils=0 AND call.result_metadata IS NULL
           AND EXISTS(
             SELECT 1 FROM gov_configs cfg WHERE cfg.id=call.config_id
               AND cfg.id=child.config_ref
               AND cfg.capability=CASE child.kind WHEN 'BRAVE_SEARCH' THEN 'BRAVE_WEB_COVERAGE' ELSE child.kind END
           )
           AND NOT EXISTS(SELECT 1 FROM gov_usage WHERE call_id=call.id)
           AND NOT EXISTS(SELECT 1 FROM gov_retained WHERE call_id=call.id)
         ), false))
 )
$$;
""")


def downgrade() -> None:
    op.execute(r"""
CREATE OR REPLACE FUNCTION record_combined_idea_proof(
 p_run_id uuid,p_experiment_id uuid,p_operation_id uuid,p_task_kind text,p_output_hash text
) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(
   SELECT 1 FROM record_agent_runs parent
   JOIN record_agent_run_steps saved ON saved.run_id=parent.run_id
     AND saved.experiment_id=parent.experiment_id
   WHERE parent.run_id=p_run_id AND parent.experiment_id=p_experiment_id
     AND parent.task_kind=p_task_kind AND parent.provider_mode='live'
     AND parent.status='RUNNING'
     AND saved.kind='ARTIFACT_SAVE' AND saved.status='SUCCEEDED'
     AND saved.operation_id=p_operation_id AND saved.output_hash=p_output_hash
 ) AND EXISTS(
   SELECT 1 FROM record_agent_run_steps model
   JOIN record_agent_runs parent ON parent.run_id=model.run_id
     AND parent.experiment_id=model.experiment_id
   JOIN gov_calls call ON call.id=model.provider_call_id
     AND call.idempotency_key=model.step_key
     AND call.experiment_id=model.experiment_id
     AND call.operation_id=model.operation_id
     AND call.created_at>=parent.started_at
     AND call.state='FINAL'
   WHERE model.run_id=p_run_id AND model.experiment_id=p_experiment_id
     AND model.kind='MODEL_REQUEST' AND model.status='SUCCEEDED'
     AND model.operation_id=p_operation_id
 ) AND NOT EXISTS(
   SELECT 1 FROM record_agent_run_steps child
   JOIN record_agent_runs parent ON parent.run_id=child.run_id
     AND parent.experiment_id=child.experiment_id
   LEFT JOIN gov_calls call ON call.id=child.provider_call_id
     AND call.idempotency_key=child.step_key
     AND call.experiment_id=child.experiment_id
     AND call.operation_id=child.operation_id
     AND call.created_at>=parent.started_at
     AND call.state='FINAL'
   WHERE child.run_id=p_run_id AND child.experiment_id=p_experiment_id
     AND child.kind<>'ARTIFACT_SAVE'
     AND (child.status<>'SUCCEEDED' OR child.operation_id IS DISTINCT FROM p_operation_id
       OR call.id IS NULL)
 )
$$;
""")
