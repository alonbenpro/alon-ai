"""Keep incomplete and cancelled Responses classifications in the ledger.

Revision ID: 20260924_24
Revises: 20260924_23
"""

from alembic import op

revision = "20260924_24"
down_revision = "20260924_23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE OR REPLACE FUNCTION gov_validate_call_json(item gov_calls) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE operation gov_operations; config gov_configs; a jsonb; r jsonb; m jsonb; u jsonb; actor jsonb;
BEGIN
 SELECT * INTO operation FROM gov_operations WHERE id=item.operation_id;
 SELECT * INTO config FROM gov_configs WHERE id=item.config_id;
 a:=item.attribution; r:=item.request; m:=item.result_metadata;
 IF operation.agent_id IS NOT NULL THEN
  actor:=jsonb_build_object('schema_version',1,'kind','agent','agent_run_id',operation.agent_id::text);
 ELSE
  actor:=jsonb_build_object('schema_version',1,'kind','system','service',operation.service);
 END IF;
 IF NOT gov_json_object(a,ARRAY['schema_version','experiment_id','workflow_run_id','operation_run_id',
   'operation_run_kind','actor','correlation_id','logical_operation_id','config_version','deadline'])
   OR NOT (a->>'experiment_id'=item.experiment_id::text AND a->>'workflow_run_id'=item.workflow_id::text
    AND a->>'operation_run_id'=item.operation_id::text AND a->>'config_version'=item.config_version::text
    AND a->>'logical_operation_id'=item.logical_operation_id::text AND a->>'operation_run_kind'=operation.kind
    AND a->'actor'=actor AND a->'actor'->>'schema_version'='1') IS TRUE
   OR NOT gov_json_uuid(a->'correlation_id') OR NOT gov_json_time(a->'deadline') THEN
  RAISE EXCEPTION 'invalid governance attribution' USING ERRCODE='23514';
 END IF;
 IF NOT gov_json_object(r,ARRAY['schema_version','config_ref','requested_count'])
   OR NOT (r->>'config_ref'=item.config_id::text AND jsonb_typeof(r->'requested_count')='number'
    AND r->>'requested_count' ~ '^[1-9][0-9]*$' AND (r->>'requested_count')::integer BETWEEN 1 AND 100
    AND r->'requested_count'=config.data->'requested_count') IS TRUE THEN
  RAISE EXCEPTION 'invalid governance request metadata' USING ERRCODE='23514';
 END IF;
 IF m IS NULL THEN RETURN; END IF;
 IF NOT gov_json_object(m,ARRAY['schema_version','capability','external_request_id','started_at','finished_at','status','error_code','usage'])
   OR NOT (m->>'capability'=config.capability AND item.state IN ('DISPATCHED','RECONCILING','FINAL')
    AND item.token IS NOT NULL AND item.finished_at IS NOT NULL
    AND m->>'status' IN ('SUCCEEDED','REFUSED','FAILED')
    AND ((m->>'status'='SUCCEEDED' AND m->'error_code'='null'::jsonb)
     OR (m->>'status'<>'SUCCEEDED' AND m->>'error_code' IN ('DENIED','CAPABILITY_MISMATCH','TIMEOUT','UNAVAILABLE','MALFORMED_RESPONSE','REFUSED','WRITE_AUTHORITY_REQUIRED','INCOMPLETE_RESULT','CANCELLED_RESULT')))
    AND (m->'external_request_id'='null'::jsonb OR (jsonb_typeof(m->'external_request_id')='string' AND m->>'external_request_id' ~ '^[A-Za-z0-9_-]{1,100}$'))
    AND jsonb_typeof(m->'usage')='array') IS TRUE
   OR NOT gov_json_time(m->'started_at') OR NOT gov_json_time(m->'finished_at') THEN
  RAISE EXCEPTION 'invalid governance result metadata' USING ERRCODE='23514';
 END IF;
 IF (m->>'finished_at')::timestamptz < (m->>'started_at')::timestamptz THEN
  RAISE EXCEPTION 'invalid governance result timing' USING ERRCODE='23514';
 END IF;
 FOR u IN SELECT value FROM jsonb_array_elements(m->'usage') LOOP
  IF NOT gov_json_object(u,ARRAY['schema_version','component','quantity','currency','cost','knowledge','observation_key'])
    OR NOT gov_json_uuid(u->'observation_key') OR NOT gov_json_quantity(u->'quantity') OR NOT gov_json_quantity(u->'cost')
    OR NOT (u->>'currency'=item.currency AND u->>'knowledge' IN ('ESTIMATE','FINAL','UNAVAILABLE')
      AND ((u->>'knowledge'='UNAVAILABLE' AND u->'cost'='null'::jsonb)
       OR (u->>'knowledge'<>'UNAVAILABLE' AND u->'cost'<>'null'::jsonb))) IS TRUE THEN
   RAISE EXCEPTION 'invalid governance usage metadata' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM gov_usage existing WHERE existing.call_id=item.id
    AND existing.observation_key::text=u->>'observation_key' AND existing.component=u->>'component'
    AND existing.currency=u->>'currency' AND existing.knowledge=u->>'knowledge'
    AND existing.quantity IS NOT DISTINCT FROM (u->>'quantity')::numeric
    AND existing.cost IS NOT DISTINCT FROM (u->>'cost')::numeric) THEN
   RAISE EXCEPTION 'governance usage metadata binding' USING ERRCODE='23514';
  END IF;
 END LOOP;
END $$;
""")


def downgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM gov_calls
   WHERE result_metadata->>'error_code' IN ('INCOMPLETE_RESULT','CANCELLED_RESULT')) THEN
  RAISE EXCEPTION 'cannot discard classified OpenAI response evidence';
 END IF;
END $$;
CREATE OR REPLACE FUNCTION gov_validate_call_json(item gov_calls) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE operation gov_operations; config gov_configs; a jsonb; r jsonb; m jsonb; u jsonb; actor jsonb;
BEGIN
 SELECT * INTO operation FROM gov_operations WHERE id=item.operation_id;
 SELECT * INTO config FROM gov_configs WHERE id=item.config_id;
 a:=item.attribution; r:=item.request; m:=item.result_metadata;
 IF operation.agent_id IS NOT NULL THEN
  actor:=jsonb_build_object('schema_version',1,'kind','agent','agent_run_id',operation.agent_id::text);
 ELSE
  actor:=jsonb_build_object('schema_version',1,'kind','system','service',operation.service);
 END IF;
 IF NOT gov_json_object(a,ARRAY['schema_version','experiment_id','workflow_run_id','operation_run_id',
   'operation_run_kind','actor','correlation_id','logical_operation_id','config_version','deadline'])
   OR NOT (a->>'experiment_id'=item.experiment_id::text AND a->>'workflow_run_id'=item.workflow_id::text
    AND a->>'operation_run_id'=item.operation_id::text AND a->>'config_version'=item.config_version::text
    AND a->>'logical_operation_id'=item.logical_operation_id::text AND a->>'operation_run_kind'=operation.kind
    AND a->'actor'=actor AND a->'actor'->>'schema_version'='1') IS TRUE
   OR NOT gov_json_uuid(a->'correlation_id') OR NOT gov_json_time(a->'deadline') THEN
  RAISE EXCEPTION 'invalid governance attribution' USING ERRCODE='23514';
 END IF;
 IF NOT gov_json_object(r,ARRAY['schema_version','config_ref','requested_count'])
   OR NOT (r->>'config_ref'=item.config_id::text AND jsonb_typeof(r->'requested_count')='number'
    AND r->>'requested_count' ~ '^[1-9][0-9]*$' AND (r->>'requested_count')::integer BETWEEN 1 AND 100
    AND r->'requested_count'=config.data->'requested_count') IS TRUE THEN
  RAISE EXCEPTION 'invalid governance request metadata' USING ERRCODE='23514';
 END IF;
 IF m IS NULL THEN RETURN; END IF;
 IF NOT gov_json_object(m,ARRAY['schema_version','capability','external_request_id','started_at','finished_at','status','error_code','usage'])
   OR NOT (m->>'capability'=config.capability AND item.state IN ('DISPATCHED','RECONCILING','FINAL')
    AND item.token IS NOT NULL AND item.finished_at IS NOT NULL
    AND m->>'status' IN ('SUCCEEDED','REFUSED','FAILED')
    AND ((m->>'status'='SUCCEEDED' AND m->'error_code'='null'::jsonb)
     OR (m->>'status'<>'SUCCEEDED' AND m->>'error_code' IN ('DENIED','CAPABILITY_MISMATCH','TIMEOUT','UNAVAILABLE','MALFORMED_RESPONSE','REFUSED','WRITE_AUTHORITY_REQUIRED')))
    AND (m->'external_request_id'='null'::jsonb OR (jsonb_typeof(m->'external_request_id')='string' AND m->>'external_request_id' ~ '^[A-Za-z0-9_-]{1,100}$'))
    AND jsonb_typeof(m->'usage')='array') IS TRUE
   OR NOT gov_json_time(m->'started_at') OR NOT gov_json_time(m->'finished_at') THEN
  RAISE EXCEPTION 'invalid governance result metadata' USING ERRCODE='23514';
 END IF;
 IF (m->>'finished_at')::timestamptz < (m->>'started_at')::timestamptz THEN
  RAISE EXCEPTION 'invalid governance result timing' USING ERRCODE='23514';
 END IF;
 FOR u IN SELECT value FROM jsonb_array_elements(m->'usage') LOOP
  IF NOT gov_json_object(u,ARRAY['schema_version','component','quantity','currency','cost','knowledge','observation_key'])
    OR NOT gov_json_uuid(u->'observation_key') OR NOT gov_json_quantity(u->'quantity') OR NOT gov_json_quantity(u->'cost')
    OR NOT (u->>'currency'=item.currency AND u->>'knowledge' IN ('ESTIMATE','FINAL','UNAVAILABLE')
      AND ((u->>'knowledge'='UNAVAILABLE' AND u->'cost'='null'::jsonb)
       OR (u->>'knowledge'<>'UNAVAILABLE' AND u->'cost'<>'null'::jsonb))) IS TRUE THEN
   RAISE EXCEPTION 'invalid governance usage metadata' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM gov_usage existing WHERE existing.call_id=item.id
    AND existing.observation_key::text=u->>'observation_key' AND existing.component=u->>'component'
    AND existing.currency=u->>'currency' AND existing.knowledge=u->>'knowledge'
    AND existing.quantity IS NOT DISTINCT FROM (u->>'quantity')::numeric
    AND existing.cost IS NOT DISTINCT FROM (u->>'cost')::numeric) THEN
   RAISE EXCEPTION 'governance usage metadata binding' USING ERRCODE='23514';
  END IF;
 END LOOP;
END $$;
""")
