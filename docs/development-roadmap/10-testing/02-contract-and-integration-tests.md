# Contract and PostgreSQL Integration Tests

**Document ID:** TEST-02
**Status:** Planned M2-M8 contract/integration suite; current repository proves only foundation migrations, health/readiness, generated health types, and minimal send-gateway unit contracts
**Milestone:** M2 persistence, M3 provider/agent contracts, M6 policy/Gmail integration, M8 API release gate
**Owner:** Solo operator
**Prerequisites:** [DB-01 through DB-06](../02-database/01-core-data-model.md), [AGENT-01](../04-agents/01-agent-runtime-and-contracts.md), provider contracts, [BACKEND-02 exact API manifest](../06-backend/02-api-contracts.md#exact-route-and-openapi-operation-manifest), BACKEND-03/04/05/06, SEC-01/05, and TEST-01
**Outputs:** Strict schema/digest vectors, real-PostgreSQL DDL and transaction proof, provider/API/policy contract matrices, and cross-owner set-equality evidence
**Unlocks:** TEST-03/04 recovery execution, generated frontend client eligibility, and M8 release candidate construction
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Byte-level contracts, named PostgreSQL invariants, sole-writer transactions, and HTTP/provider partitions fail before orchestration or browser work can consume them. Tests use canonical upstream manifests as authority and compare independent fixtures by exact set equality; they do not maintain a weaker alias contract.

## Current repository state

Alembic currently has only the foundation schema, OpenAPI exposes health operations, and the generated TypeScript client covers that surface. PostgreSQL 18 integration runs in CI. The 46 product tables, deferred FKs/triggers/retention commands, 66-operation API, 64+2 release partition, provider result families, full policy engine, incident catalog, agent schemas/evals, and product transactions remain planned.

## Scope and non-goals

In scope: Pydantic strict/extra-forbid/frozen models, RFC 8785, all 46 product tables and named DDL, migrations/seeds/retention, domain states/events, atomic bundles, outbox delivery, six provider capabilities, Gmail read/send unions, agent terminal unions, 66 operations, named response/problem schemas, 14 dedicated final-SEND denials, incident tuple/resolution/repair applicability, sole writers, and generated clients. Non-goals: SQLite substitutes, snapshot approval without semantic review, ORM-only constraint tests, route-count-only assertions, provider SDK objects, or network-backed provider calls.

## Exact planned implementation surfaces

Create `backend/tests/contract/`, `backend/tests/integration/`, `tests/manifests/{tables,api,states_events,policies,incidents,providers}.v1.json`, strict schema snapshots, and `scripts/verify_contract_sets.py`. Use a PostgreSQL role matrix: migration owner, API writer, worker writer, read projection, retention owner, and recipient-lookup owner; unauthorized SQL must fail by role before application checks.

The canonical 46-table set is exactly: `operators`, `experiments`, `workflow_runs`, `system_controls`, `budget_accounts`, `budget_reservations`, `incidents`; `experiment_briefs`, `ideas`, `offer_hypotheses`, `metric_definitions`, `metric_observations`, `metric_snapshots`, `experiment_decisions`; `businesses`, `leads`, `lead_assessments`, `gmail_mailboxes`, `campaigns`, `campaign_members`, `outreach_messages`, `approvals`, `suppression_entries`, `send_intents`, `send_rate_reservations`, `send_attempts`, `provider_results`, `provider_observations`, `replies`, `gmail_history_cursors`; `agent_runs`, `artifacts`, `evidence_items`, `artifact_evidence_links`, `artifact_validations`, `artifact_acceptances`, `evaluation_cases`, `evaluation_results`; `domain_events`, `audit_events`, `command_idempotency`, `outbox_messages`, `outbox_deliveries`, `policy_decisions`, `cost_entries`, `repair_actions`. The test derives DDL names from PostgreSQL catalogs and requires exact equality with this signed manifest.

| Contract family | Required positives | Required negatives | Evidence |
| --- | --- | --- | --- |
| strict models | every schema/version/discriminator branch round-trips | extra/missing/cross-branch fields, wrong literal/type, invalid time/UUID/hash/decimal | JSON Schema hashes and rejection corpus |
| RFC 8785 | DB-01 three normative bytes/SHA-256 reproduced by two implementations | duplicate keys, non-I-JSON numbers, invalid Unicode, whitespace/key-order/escape/schema-type, SQL NULL vs JSON null | byte and digest vectors |
| DDL/migrations | empty/prior/backup schema reaches exactly 46 tables; every named FK/check/unique/index/trigger/owner; seed twice no diff | one-column composite splices, immutable mutation, unsafe downgrade/backfill, secret/real-recipient seed | catalog dump, revision graph, counts/hashes |
| transactions/outbox | aggregate+event+audit+idempotency+outbox atomic; delivery receipt dedupe | failure after every write, duplicate command, poison delivery, direct external effect | row-set hashes and call count zero |
| providers/agents | six capability `SUCCESS|FAILURE`, Gmail `ACCEPTED|CONCLUSIVE_REJECTION|UNKNOWN`, agent `SUCCESS|ABSTAIN|FAILED` | cross-capability result, payload on failure, missing payload digest, provider-native error, usage/ledger mismatch, forbidden authority | schema/ledger fixture hashes |
| agent evaluations | exact eight suites/552 cases/three fresh captures per case (1,656), signed capture sets, two offline scorers and exact AGENT-10 golden/threshold/regression/cost gates | missing/replayed capture, live non-model network, scorer disagreement, hard failure, privacy/authority edge, threshold one unit below | dataset/capture/signature/scorer/promotion hashes |
| API | exact 66 method/path/operationId triples, exact 64 `PRIVATE_DEPLOYMENT` + 2 `PUBLIC_UNSUBSCRIBE`, strict responses/errors/ETags/cursors | duplicate/unclassified route, webhook/general public route, auth/CSRF/idempotency/version bypass, recipient hash in any schema | OpenAPI diff and route registry hash |
| policy | approval eligibility plus final SEND fixed rule order and exact reason registry; all 14 dedicated compliance/signal denials reach zero credential/call | stale/cross-recipient evidence, generic reason substitution, reused queued facts, equalized facts hashes, unknown fact/version | decision/facts/scope hashes and call spies |
| incident | all 18 positive severity/trigger/alert/runbook tuples and exact resolution/repair applicability | every cross-pair, all 72 wrong-severity permutations, unknown catalog/code, inapplicable resolution/repair, forbidden residual-risk acceptance | DB/application/OpenAPI set equality |

The 14 dedicated denial fixtures are exactly `RECIPIENT_IDENTITY_UNVERIFIED`, `RECIPIENT_JURISDICTION_UNKNOWN`, `RECIPIENT_CONSENT_MISSING`, `RECIPIENT_CONSENT_EXPIRED`, `COUNSEL_EXCEPTION_MISSING`, `LEGAL_REVIEW_MISSING`, `LEGAL_REVIEW_STALE`, `DISCLOSURE_TEMPLATE_INVALID`, `GOOGLE_POLICY_DENIED`, `RECIPIENT_REPLIED`, `RECIPIENT_OPTED_OUT`, `RECIPIENT_HARD_BOUNCED`, `RECIPIENT_COMPLAINT`, and `RECIPIENT_SOFT_BOUNCE_LIMIT`.

### Permanent rollback-only residual authority fixtures

The following two scripts are normative TEST-02 fixtures, not illustrative pseudocode. The first compiles only after DB-01..06, creates synthetic parents inside its transaction, switches back to normal trigger enforcement before every target row, verifies exact SQLSTATE plus constraint name, proves the valid adjacent campaign/agent/Gmail cost shapes, and rolls everything back. Seed-only `session_replication_role=replica` is permitted solely in the disposable superuser fixture to avoid duplicating unrelated artifact/send chains; every asserted target INSERT executes as `origin`. Any unexpected earlier constraint, escaped row, changed count, or COMMIT is a test failure.

```sql
\set ON_ERROR_STOP on
\pset pager off

BEGIN;

CREATE FUNCTION pg_temp.expect_constraint(
    p_label text, p_statement text, p_sqlstate text,
    p_constraint text, p_force_campaign_fk boolean DEFAULT false
) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    actual_state text;
    actual_constraint text;
    escaped boolean := true;
BEGIN
    BEGIN
        EXECUTE p_statement;
        IF p_force_campaign_fk THEN
            SET CONSTRAINTS fk_campaigns_supersedes IMMEDIATE;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS
            actual_state = RETURNED_SQLSTATE,
            actual_constraint = CONSTRAINT_NAME;
        escaped := false;
    END;
    SET CONSTRAINTS fk_campaigns_supersedes DEFERRED;
    IF escaped THEN
        RAISE EXCEPTION '% escaped its expected rejection', p_label;
    END IF;
    IF actual_state <> p_sqlstate OR actual_constraint <> p_constraint THEN
        RAISE EXCEPTION '% failed via %/% rather than %/%',
            p_label, actual_state, actual_constraint, p_sqlstate, p_constraint;
    END IF;
    RAISE NOTICE 'GREEN_REJECTED label=% sqlstate=% constraint=%',
        p_label, actual_state, actual_constraint;
END $$;

INSERT INTO operators (operator_id, subject, display_name)
VALUES ('10000000-0000-4000-8000-000000000001', 'exceptional-green-operator', 'Exceptional GREEN');
INSERT INTO experiments (experiment_id, owner_operator_id, state, retry_limit, correlation_id)
VALUES
 ('10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000001','DRAFT',0,'10000000-0000-4000-8000-000000000021'),
 ('10000000-0000-4000-8000-000000000012','10000000-0000-4000-8000-000000000001','DRAFT',0,'10000000-0000-4000-8000-000000000022');
INSERT INTO workflow_runs (
 workflow_run_id,experiment_id,workflow_type,workflow_version,runtime,runtime_workflow_id,
 state,attempt_no,max_attempts,max_runtime_seconds,max_cost_minor,currency,
 input_schema_version,input_snapshot,input_hash,correlation_id
) VALUES
 ('10000000-0000-4000-8000-000000000101','10000000-0000-4000-8000-000000000011','RED_W1','v1','DBOS','exceptional-green-w1','PENDING',1,1,60,100,'ILS','workflow.input.v1','{}',repeat('1',64),'10000000-0000-4000-8000-000000000201'),
 ('10000000-0000-4000-8000-000000000102','10000000-0000-4000-8000-000000000011','RED_W2','v1','DBOS','exceptional-green-w2','PENDING',1,1,60,100,'ILS','workflow.input.v1','{}',repeat('2',64),'10000000-0000-4000-8000-000000000202');
INSERT INTO agent_runs (
 agent_run_id,experiment_id,workflow_run_id,agent_type,agent_version,produced_artifact_type,
 prompt_version,model_provider,model_name,model_version,toolset_version,input_snapshot_hash,
 state,currency,correlation_id
) VALUES (
 '10000000-0000-4000-8000-000000000111','10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000101',
 'IDEA_DISCOVERY','agent.v1','IdeaCandidate','prompt.v1','fixture','fixture','fixture.v1','tools.v1',repeat('1',64),'PENDING','ILS','10000000-0000-4000-8000-000000000211'
);

SELECT pg_temp.expect_constraint(
 'cost_w2_agent_w1_splice',
 $sql$INSERT INTO cost_entries (
  cost_entry_id,provider,operation,provider_call_id,experiment_id,workflow_run_id,agent_run_id,
  usage_schema_version,usage_json,usage_hash,amount_minor,currency,reporting_amount_minor_ils,
  occurred_at,idempotency_key
 ) VALUES (
  '10000000-0000-4000-8000-000000000121','FIXTURE','COST_SPLICE','10000000-0000-4000-8000-000000000121',
  '10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000102','10000000-0000-4000-8000-000000000111',
  1,jsonb_build_object('provider_call_id','10000000-0000-4000-8000-000000000121'),repeat('3',64),1,'ILS',1,
  statement_timestamp(),'10000000-0000-4000-8000-000000000121'
 )$sql$, '23503', 'fk_cost_entries_agent_run');

SELECT pg_temp.expect_constraint(
 'cost_agent_without_workflow',
 $sql$INSERT INTO cost_entries (
  cost_entry_id,provider,operation,provider_call_id,experiment_id,agent_run_id,
  usage_schema_version,usage_json,usage_hash,amount_minor,currency,reporting_amount_minor_ils,
  occurred_at,idempotency_key
 ) VALUES (
  '10000000-0000-4000-8000-000000000122','FIXTURE','MISSING_WORKFLOW','10000000-0000-4000-8000-000000000122',
  '10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000111',
  1,jsonb_build_object('provider_call_id','10000000-0000-4000-8000-000000000122'),repeat('4',64),1,'ILS',1,
  statement_timestamp(),'10000000-0000-4000-8000-000000000122'
 )$sql$, '23514', 'ck_cost_entries_provenance_shape');

-- Canonical positive agent allocation.
INSERT INTO cost_entries (
 cost_entry_id,provider,operation,provider_call_id,experiment_id,workflow_run_id,agent_run_id,
 usage_schema_version,usage_json,usage_hash,amount_minor,currency,reporting_amount_minor_ils,
 occurred_at,idempotency_key
) VALUES (
 '10000000-0000-4000-8000-000000000123','FIXTURE','AGENT_POSITIVE','10000000-0000-4000-8000-000000000123',
 '10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000101','10000000-0000-4000-8000-000000000111',
 1,jsonb_build_object('provider_call_id','10000000-0000-4000-8000-000000000123'),repeat('5',64),1,'ILS',1,
 statement_timestamp(),'10000000-0000-4000-8000-000000000123'
);

SET LOCAL session_replication_role = replica;
INSERT INTO offer_hypotheses (
 offer_id,experiment_id,idea_id,idea_version,idea_content_hash,offer_version,name,promise,
 deliverables_schema_version,deliverables,price_minor,currency,assumptions_schema_version,
 assumptions,risk_reversals_schema_version,risk_reversals,source_artifact_id,
 source_artifact_version,source_artifact_hash,content_hash
) VALUES
 ('10000000-0000-4000-8000-000000000301','10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000311',1,repeat('4',64),1,'offer-a','promise-a',1,'[]',1,'ILS',1,'[]',1,'[]','10000000-0000-4000-8000-000000000321',1,repeat('5',64),repeat('6',64)),
 ('10000000-0000-4000-8000-000000000302','10000000-0000-4000-8000-000000000012','10000000-0000-4000-8000-000000000312',1,repeat('7',64),1,'offer-b','promise-b',1,'[]',1,'ILS',1,'[]',1,'[]','10000000-0000-4000-8000-000000000322',1,repeat('8',64),repeat('9',64));
INSERT INTO campaigns (
 campaign_version_id,campaign_id,campaign_version,experiment_id,supersedes_campaign_version_id,
 offer_id,offer_version,offer_content_hash,policy_version,eligibility_snapshot_version,
 eligibility_snapshot_at,eligibility_query_version,eligible_set_hash,eligible_member_count,
 member_cap,send_window_start,send_window_end,reply_window_end,daily_cap,total_cap
) VALUES
 ('10000000-0000-4000-8000-000000000401','10000000-0000-4000-8000-000000000411',1,'10000000-0000-4000-8000-000000000011',NULL,'10000000-0000-4000-8000-000000000301',1,repeat('6',64),'policy.v1',1,statement_timestamp(),'eligibility.v1',repeat('a',64),1,1,statement_timestamp(),statement_timestamp()+interval '1 hour',statement_timestamp()+interval '2 hours',1,1),
 ('10000000-0000-4000-8000-000000000402','10000000-0000-4000-8000-000000000412',1,'10000000-0000-4000-8000-000000000011',NULL,'10000000-0000-4000-8000-000000000301',1,repeat('6',64),'policy.v1',1,statement_timestamp(),'eligibility.v1',repeat('b',64),1,1,statement_timestamp(),statement_timestamp()+interval '1 hour',statement_timestamp()+interval '2 hours',1,1),
 ('10000000-0000-4000-8000-000000000403','10000000-0000-4000-8000-000000000413',3,'10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000401','10000000-0000-4000-8000-000000000301',1,repeat('6',64),'policy.v1',1,statement_timestamp(),'eligibility.v1',repeat('c',64),1,1,statement_timestamp(),statement_timestamp()+interval '1 hour',statement_timestamp()+interval '2 hours',1,1);

INSERT INTO send_attempts (
 send_attempt_id,send_intent_id,experiment_id,campaign_id,campaign_version,campaign_member_id,
 lead_id,message_id,message_version,message_content_hash,mailbox_id,approval_id,
 approval_preview_materialization_hash,approval_artifact_version_refs_hash,
 eligibility_policy_decision_id,eligibility_policy_scope,eligibility_policy_version,
 eligibility_facts_hash,eligibility_policy_allowed,send_policy_decision_id,send_policy_scope,
 send_policy_version,scope_hash,send_policy_facts_hash,send_policy_allowed,rate_reservation_id,
 rate_policy_version,rate_window_start,rate_slot_number,rate_concurrency_lease_token,
 rate_consumed_at,rfc_message_id,intent_open_for_attempt,attempt_number,state,started_at
) VALUES
 ('10000000-0000-4000-8000-000000000601','10000000-0000-4000-8000-000000000611','10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000411',1,'10000000-0000-4000-8000-000000000621','10000000-0000-4000-8000-000000000631','10000000-0000-4000-8000-000000000641',1,repeat('1',64),'10000000-0000-4000-8000-000000000651','10000000-0000-4000-8000-000000000661',repeat('2',64),repeat('3',64),'10000000-0000-4000-8000-000000000671','APPROVAL_ELIGIBILITY','policy.v1',repeat('4',64),true,'10000000-0000-4000-8000-000000000681','SEND','policy.v1',repeat('5',64),repeat('6',64),true,'10000000-0000-4000-8000-000000000691','rate.v1',statement_timestamp()-interval '1 minute',1,repeat('7',64),statement_timestamp()-interval '1 second','<fixture-1@example.invalid>',true,1,'STARTED',statement_timestamp()),
 ('10000000-0000-4000-8000-000000000602','10000000-0000-4000-8000-000000000612','10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000411',1,'10000000-0000-4000-8000-000000000622','10000000-0000-4000-8000-000000000632','10000000-0000-4000-8000-000000000642',1,repeat('8',64),'10000000-0000-4000-8000-000000000652','10000000-0000-4000-8000-000000000662',repeat('9',64),repeat('a',64),'10000000-0000-4000-8000-000000000672','APPROVAL_ELIGIBILITY','policy.v1',repeat('b',64),true,'10000000-0000-4000-8000-000000000682','SEND','policy.v1',repeat('c',64),repeat('d',64),true,'10000000-0000-4000-8000-000000000692','rate.v1',statement_timestamp()-interval '1 minute',2,repeat('e',64),statement_timestamp()-interval '1 second','<fixture-2@example.invalid>',true,1,'STARTED',statement_timestamp());
INSERT INTO provider_results (
 provider_result_id,send_attempt_id,provider_call_id,mailbox_id,provider,outcome,rfc_message_id,response_fingerprint
) VALUES (
 '10000000-0000-4000-8000-000000000701','10000000-0000-4000-8000-000000000601','10000000-0000-4000-8000-000000000751','10000000-0000-4000-8000-000000000651','GMAIL','UNKNOWN','<fixture-1@example.invalid>',repeat('f',64)
);
SET LOCAL session_replication_role = origin;

SELECT pg_temp.expect_constraint(
 'cost_send_with_workflow',
 $sql$INSERT INTO cost_entries (
  cost_entry_id,provider,operation,provider_call_id,experiment_id,workflow_run_id,
  send_attempt_id,provider_result_id,usage_schema_version,usage_json,usage_hash,
  amount_minor,currency,reporting_amount_minor_ils,occurred_at,idempotency_key
 ) VALUES (
  '10000000-0000-4000-8000-000000000711','GMAIL','SEND','10000000-0000-4000-8000-000000000751',
  '10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000101',
  '10000000-0000-4000-8000-000000000601','10000000-0000-4000-8000-000000000701',1,
  jsonb_build_object('provider_call_id','10000000-0000-4000-8000-000000000751'),repeat('1',64),1,'ILS',1,statement_timestamp(),'10000000-0000-4000-8000-000000000751'
 )$sql$, '23514', 'ck_cost_entries_provenance_shape');

SELECT pg_temp.expect_constraint(
 'cost_cross_attempt_provider_result',
 $sql$INSERT INTO cost_entries (
  cost_entry_id,provider,operation,provider_call_id,experiment_id,send_attempt_id,
  provider_result_id,usage_schema_version,usage_json,usage_hash,amount_minor,currency,
  reporting_amount_minor_ils,occurred_at,idempotency_key
 ) VALUES (
  '10000000-0000-4000-8000-000000000712','GMAIL','SEND','10000000-0000-4000-8000-000000000751',
  '10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000602',
  '10000000-0000-4000-8000-000000000701',1,
  jsonb_build_object('provider_call_id','10000000-0000-4000-8000-000000000751'),repeat('2',64),1,'ILS',1,statement_timestamp(),'10000000-0000-4000-8000-000000000751'
 )$sql$, '23503', 'fk_cost_entries_provider_result');

SELECT pg_temp.expect_constraint(
 'cost_provider_result_call_splice',
 $sql$INSERT INTO cost_entries (
  cost_entry_id,provider,operation,provider_call_id,experiment_id,send_attempt_id,
  provider_result_id,usage_schema_version,usage_json,usage_hash,amount_minor,currency,
  reporting_amount_minor_ils,occurred_at,idempotency_key
 ) VALUES (
  '10000000-0000-4000-8000-000000000713','GMAIL','SEND','10000000-0000-4000-8000-000000000799',
  '10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000601',
  '10000000-0000-4000-8000-000000000701',1,
  jsonb_build_object('provider_call_id','10000000-0000-4000-8000-000000000799'),repeat('3',64),1,'ILS',1,statement_timestamp(),'10000000-0000-4000-8000-000000000799'
 )$sql$, '23503', 'fk_cost_entries_provider_result');

INSERT INTO cost_entries (
 cost_entry_id,provider,operation,provider_call_id,experiment_id,send_attempt_id,
 provider_result_id,usage_schema_version,usage_json,usage_hash,amount_minor,currency,
 reporting_amount_minor_ils,occurred_at,idempotency_key
) VALUES (
 '10000000-0000-4000-8000-000000000714','GMAIL','SEND','10000000-0000-4000-8000-000000000751',
 '10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000601',
 '10000000-0000-4000-8000-000000000701',1,
 jsonb_build_object('provider_call_id','10000000-0000-4000-8000-000000000751'),repeat('4',64),1,'ILS',1,statement_timestamp(),'10000000-0000-4000-8000-000000000751'
);

CREATE FUNCTION pg_temp.add_campaign(
 p_version_id uuid,p_campaign_id uuid,p_version integer,p_experiment_id uuid,
 p_supersedes uuid,p_offer_id uuid,p_offer_hash char(64),p_set_hash char(64)
) RETURNS void LANGUAGE sql AS $$
 INSERT INTO campaigns (
  campaign_version_id,campaign_id,campaign_version,experiment_id,supersedes_campaign_version_id,
  offer_id,offer_version,offer_content_hash,policy_version,eligibility_snapshot_version,
  eligibility_snapshot_at,eligibility_query_version,eligible_set_hash,eligible_member_count,
  member_cap,send_window_start,send_window_end,reply_window_end,daily_cap,total_cap
 ) VALUES (
  p_version_id,p_campaign_id,p_version,p_experiment_id,p_supersedes,p_offer_id,1,p_offer_hash,
  'policy.v1',p_version,statement_timestamp(),'eligibility.v1',p_set_hash,1,1,
  statement_timestamp(),statement_timestamp()+interval '1 hour',statement_timestamp()+interval '2 hours',1,1
 )
$$;

SELECT pg_temp.expect_constraint('campaign_cross_campaign',
 $$SELECT pg_temp.add_campaign('10000000-0000-4000-8000-000000000421','10000000-0000-4000-8000-000000000412',2,'10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000401','10000000-0000-4000-8000-000000000301',repeat('6',64),repeat('d',64))$$,
 '23503','fk_campaigns_supersedes',true);
SELECT pg_temp.expect_constraint('campaign_skipped_previous',
 $$SELECT pg_temp.add_campaign('10000000-0000-4000-8000-000000000422','10000000-0000-4000-8000-000000000411',3,'10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000401','10000000-0000-4000-8000-000000000301',repeat('6',64),repeat('e',64))$$,
 '23503','fk_campaigns_supersedes',true);
SELECT pg_temp.expect_constraint('campaign_self',
 $$SELECT pg_temp.add_campaign('10000000-0000-4000-8000-000000000423','10000000-0000-4000-8000-000000000414',2,'10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000423','10000000-0000-4000-8000-000000000301',repeat('6',64),repeat('f',64))$$,
 '23503','fk_campaigns_supersedes',true);
SELECT pg_temp.expect_constraint('campaign_future',
 $$SELECT pg_temp.add_campaign('10000000-0000-4000-8000-000000000424','10000000-0000-4000-8000-000000000413',2,'10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000403','10000000-0000-4000-8000-000000000301',repeat('6',64),repeat('0',64))$$,
 '23503','fk_campaigns_supersedes',true);
SELECT pg_temp.expect_constraint('campaign_cross_experiment',
 $$SELECT pg_temp.add_campaign('10000000-0000-4000-8000-000000000425','10000000-0000-4000-8000-000000000415',2,'10000000-0000-4000-8000-000000000012','10000000-0000-4000-8000-000000000401','10000000-0000-4000-8000-000000000302',repeat('9',64),repeat('1',64))$$,
 '23503','fk_campaigns_supersedes',true);

-- Canonical immediate predecessor positive.
SELECT pg_temp.add_campaign('10000000-0000-4000-8000-000000000426','10000000-0000-4000-8000-000000000412',2,'10000000-0000-4000-8000-000000000011','10000000-0000-4000-8000-000000000402','10000000-0000-4000-8000-000000000301',repeat('6',64),repeat('2',64));
SET CONSTRAINTS fk_campaigns_supersedes IMMEDIATE;
SET CONSTRAINTS fk_campaigns_supersedes DEFERRED;

SELECT pg_temp.expect_constraint(
 'incident_info_send_route',
 $$INSERT INTO incidents (incident_id,severity,trigger_code,runbook_id,alert_id,opened_by_actor_type,opened_by_actor_id)
   VALUES ('10000000-0000-4000-8000-000000000501','INFO','SEND_AUTHORITY_VIOLATION','IR-01','ALERT_SEND_AUTHORITY_VIOLATION','SYSTEM','fixture')$$,
 '23514','ck_incidents_route_tuple');

DO $$ BEGIN RAISE NOTICE 'GREEN_PRODUCT_SUMMARY negatives=11 positives=3'; END $$;
ROLLBACK;
```

The second script is the exhaustive four-field incident-route fixture. It inserts all 18 canonical positives, tries the other four severities for every route, requires exactly 72 `23514/ck_incidents_route_tuple` rejections, and rolls back:

```sql
\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
    routes jsonb := '[
      ["CRITICAL","AGENT_PROMPT_INJECTION_OR_POISONING","ALERT_AGENT_INJECTION","IR-06"],
      ["CRITICAL","PROVIDER_EXFILTRATION","ALERT_PROVIDER_EXFILTRATION","IR-06"],
      ["CRITICAL","AUTH_OR_SECRET_COMPROMISE","ALERT_CREDENTIAL_OR_SESSION","IR-03"],
      ["CRITICAL","WEB_SESSION_BOUNDARY_ATTACK","ALERT_WEB_BOUNDARY","IR-05"],
      ["CRITICAL","SSRF_OR_DNS_REBINDING","ALERT_EGRESS_SSRF","IR-05"],
      ["CRITICAL","CALLBACK_ABUSE","ALERT_CALLBACK_ABUSE","IR-05"],
      ["CRITICAL","SEND_AUTHORITY_VIOLATION","ALERT_SEND_AUTHORITY_VIOLATION","IR-01"],
      ["CRITICAL","SUPPLY_CHAIN_COMPROMISE","ALERT_SUPPLY_CHAIN","IR-09"],
      ["CRITICAL","WORKFLOW_REPLAY_OR_VERSION_DRIFT","ALERT_WORKFLOW_REPLAY","IR-07"],
      ["CRITICAL","DATASTORE_OR_RESTORE_FAILURE","ALERT_BACKUP_RESTORE","IR-08"],
      ["CRITICAL","OPERATOR_OR_RECOVERY_ERROR","ALERT_OPERATOR_REPAIR","IR-13"],
      ["CRITICAL","AUTHORIZATION_OR_ENUMERATION","ALERT_AUTHORIZATION_ENUMERATION","IR-05"],
      ["CRITICAL","COST_OR_QUOTA_RUNAWAY","ALERT_COST_QUOTA","IR-10"],
      ["CRITICAL","TELEMETRY_PRIVACY_LEAK","ALERT_TELEMETRY_PRIVACY","IR-04"],
      ["CRITICAL","COMPLIANCE_OR_SUPPRESSION_BREACH","ALERT_COMPLIANCE_SUPPRESSION","IR-12"],
      ["CRITICAL","TELEMETRY_OR_ALERT_BLINDNESS","ALERT_TELEMETRY_BLINDNESS","IR-11"],
      ["HIGH","GMAIL_AMBIGUITY_STALE","ALERT_GMAIL_AMBIGUITY","IR-02"],
      ["CRITICAL","RECIPIENT_HASH_ENUMERATION","ALERT_RECIPIENT_HASH_ENUMERATION","IR-04"]
    ]'::jsonb;
    severities text[] := ARRAY['INFO','LOW','MEDIUM','HIGH','CRITICAL'];
    route jsonb;
    severity text;
    actual_state text;
    actual_constraint text;
    positives integer := 0;
    negatives integer := 0;
BEGIN
    FOR route IN SELECT value FROM jsonb_array_elements(routes) LOOP
        INSERT INTO incidents (
            incident_id,severity,trigger_code,alert_id,runbook_id,
            opened_by_actor_type,opened_by_actor_id
        ) VALUES (
            md5('positive:' || route::text)::uuid,
            route->>0,route->>1,route->>2,route->>3,'SYSTEM','incident-matrix'
        );
        positives := positives + 1;
        FOREACH severity IN ARRAY severities LOOP
            CONTINUE WHEN severity = route->>0;
            BEGIN
                INSERT INTO incidents (
                    incident_id,severity,trigger_code,alert_id,runbook_id,
                    opened_by_actor_type,opened_by_actor_id
                ) VALUES (
                    md5('negative:' || severity || route::text)::uuid,
                    severity,route->>1,route->>2,route->>3,'SYSTEM','incident-matrix'
                );
                RAISE EXCEPTION 'wrong severity escaped: % %', severity, route;
            EXCEPTION WHEN check_violation THEN
                GET STACKED DIAGNOSTICS
                    actual_state = RETURNED_SQLSTATE,
                    actual_constraint = CONSTRAINT_NAME;
                IF actual_state <> '23514' OR actual_constraint <> 'ck_incidents_route_tuple' THEN
                    RAISE EXCEPTION 'wrong target for % %: %/%', severity, route, actual_state, actual_constraint;
                END IF;
                negatives := negatives + 1;
            END;
        END LOOP;
    END LOOP;
    IF positives <> 18 OR negatives <> 72 THEN
        RAISE EXCEPTION 'incident matrix count mismatch positives=% negatives=%', positives, negatives;
    END IF;
    RAISE NOTICE 'INCIDENT_FOUR_FIELD_GREEN positives=% wrong_severity_rejections=% sqlstate=23514 constraint=ck_incidents_route_tuple', positives, negatives;
END $$;
ROLLBACK;
```

The complete TEST-02 requirement set maps only to `T7-CONTRACT-INTEGRATION` in the [TEST-01 closed command manifest](01-testing-strategy.md#closed-command-manifest). `scripts/task7/run` performs the one nonrecursive dispatch defined there; the exact planned handler `scripts/task7/handlers/contract-integration` independently derives trust from its own file location, never caller cwd or a root environment variable:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
readonly handler_invoked="${BASH_SOURCE[0]}"
[[ "$handler_invoked" == /* && -f "$handler_invoked" && -x "$handler_invoked" && ! -L "$handler_invoked" ]] || exit 20
readonly handler_dir_lexical="${handler_invoked%/*}"
readonly handler_basename="${handler_invoked##*/}"
handler_dir_physical="$(cd -P -- "$handler_dir_lexical" && pwd -P)" || exit 20
readonly handler_dir_physical
readonly handler_real="$handler_dir_physical/$handler_basename"
[[ "$handler_invoked" == "$handler_real" ]] || exit 20
repo_root="$(cd -P -- "$handler_dir_physical/../../.." && pwd -P)" || exit 20
readonly repo_root
[[ "$handler_real" == "$repo_root/scripts/task7/handlers/contract-integration" && ! "$handler_real" -ef "$repo_root/scripts/task7/run" ]] || exit 20
unset TASK7_REPO_ROOT REPO_ROOT GIT_DIR GIT_WORK_TREE
git_root="$(git -C "$repo_root" rev-parse --show-toplevel)" || exit 20
readonly git_root
[[ "$(cd -P -- "$git_root" && pwd -P)" == "$repo_root" ]] || exit 20

[[ "$#" -eq 10 ]] || exit 20
[[ "$1" == --command && "$2" == T7-CONTRACT-INTEGRATION ]] || exit 20
[[ "$3" == --run-id && "$5" == --evidence-root ]] || exit 20
[[ "$7" == --profile && "$8" == PG_EPHEMERAL ]] || exit 20
[[ "$9" == --target-manifest ]] || exit 20
readonly run_id="$4" evidence_root="$6" profile="$8" target_manifest="${10}"
actual_commit="$(git -C "$repo_root" rev-parse --verify HEAD)" || exit 20
readonly actual_commit
expected_pg_system_id="$(
  "$repo_root/scripts/task7/verify-static-contract" \
    --repository-identity "$repo_root/tests/manifests/repository-identity.v1.json" \
    --command-manifest "$repo_root/tests/manifests/task7-commands.v1.json" \
    --profile "$repo_root/tests/profiles/task7/PG_EPHEMERAL.v1.json" \
    --fixture "$repo_root/tests/fixtures/task7/PG_EPHEMERAL.v1.json" \
    --command T7-CONTRACT-INTEGRATION --actual-root "$repo_root" \
    --actual-commit "$actual_commit" --run-id "$run_id" \
    --evidence-root "$evidence_root" --emit expected_pg_system_id
)" || exit 20
readonly expected_pg_system_id

"$repo_root/scripts/task7/assert-target" --kind postgres --target-manifest "$target_manifest" --expected-environment TEST_EPHEMERAL --expected-database "alon_ai_test_${run_id}" --expected-system-id "$expected_pg_system_id" --require-outreach-disabled --require-zero-writers
(
  cd "$repo_root/backend"
  uv run alembic upgrade head
  uv run pytest tests/contract tests/integration -q --strict-markers
)
(
  cd "$repo_root"
  uv run python scripts/verify_contract_sets.py --database-ref task7-target-manifest --openapi frontend/openapi.json --manifests tests/manifests
  npm --prefix frontend run api:generate
  git diff --exit-code -- frontend/openapi.json frontend/src/lib/api/schema.d.ts
)
```

The last command uses only readonly `target_manifest`, `run_id`, and `expected_pg_system_id` values sourced from the normalized handler argv and verified profile; it accepts no caller replacements after verification. Every positional parameter above 9 uses braces (`${10}`), and `bash -n` plus the executable stub fixture guards that syntax. `verify-static-contract` reads only files beneath the script-derived root, verifies signatures, literal repository identity `alon-ai`, exact expected commit/profile/fixture/command and clean checkout, then emits one schema-validated system ID; it cannot open a target. Only afterward does `assert-target` resolve the scoped database secret without printing it and query `current_database()`, `pg_control_system().system_identifier`, environment marker, outreach controls and writer sessions.

The signed command manifest materializes `entry_argv[0]` as the absolute canonical runner path and binds this distinct handler path/hash. `bash -n` parses both. Positive fixtures invoke the runner from repository root, `backend/`, `frontend/` and `/tmp`, then require exactly one handler exec with the normalized ten arguments above and zero runner recursion. Negatives cover relative/symlink/equal-inode/hash-changed handler, a runner copied under another Git root, symlinked parent directory, wrong repository identity/commit/profile and hostile root/Git environment variables; each exits `20` or `40` and a target-access spy stays zero. Wrong database/system ID/environment, missing/invalid target manifest or active writer exits `50` before Alembic. Root-safe subshells prevent `backend/backend`. The external entry tail remains `--manifest tests/manifests/task7-commands.v1.json --command T7-CONTRACT-INTEGRATION --run-id "$TASK7_RUN_ID" --evidence-root "$TASK7_EVIDENCE_ROOT" --profile PG_EPHEMERAL --target-manifest "$TASK7_TARGET_MANIFEST"`, preceded by the signed checkout's canonical absolute runner path.

## Ordered implementation tasks

- [ ] **Freeze schema and digest manifests —** Input: DB-01, AGENT-01 and provider exact models. Operation: build independent strict-schema and RFC 8785 vectors and compare schema/version/discriminator sets. Output: signed contract manifests. Test evidence: positive/negative corpus and two-implementation digests. Failure behavior: no consumer generation or migration.
- [ ] **Prove the complete PostgreSQL contract —** Input: DB-01..06 DDL, owners and retention manifest. Operation: migrate clean/prior/restored databases, introspect exact 46 tables/FKs/checks/indexes/triggers/privileges, inject transaction failures and exercise holds/purge. Output: catalog/invariant evidence. Test evidence: set equality plus every composite one-field splice and all-table retention ownership. Failure behavior: rollback current revision; keep workers/API writers stopped.
- [ ] **Prove provider, agent, evaluation and cost contracts —** Input: six capability fixtures, Gmail unions, terminal agent results, exact eight-suite/552-case evaluation manifests and cost ledgers. Operation: validate every allowed branch/error/timeout/budget/cancel and cross-family denial, then prove 1,656 fresh capture completeness/signatures and two offline scorers against all AGENT-10 goldens/gates. Output: byte-compatible adapter and reproducible evaluation acceptance. Test evidence: request/result/ledger/payload/capture/scorer hashes, network isolation and usage/cost reconciliation matrix. Failure behavior: adapter/config cannot be promoted.
- [ ] **Prove API and generated-client partition —** Input: BACKEND-02 exact manifest. Operation: compare OpenAPI, runtime router metadata, Caddy/WAF route manifest fixture and generated client operation sets. Output: exact 66/64+2 evidence. Test evidence: public pair unavailable pre-M9, GET write spy zero, POST-only suppression, and no webhook/general public route. Failure behavior: startup/release rejected.
- [ ] **Prove policy and incident closure —** Input: fixed rules/reasons and `incident.catalog.v1`. Operation: evaluate all positive/applicable and exhaustive negative cross-pairs on real PostgreSQL. Output: matching domain/DB/API registries. Test evidence: 14 no-call denial fixtures, 18 route tuples and resolution/repair applicability. Failure behavior: sending/public ingress/recovery commands disabled.
- [ ] **Validate the script-derived lane —** Input: canonical absolute runner, distinct hashed contract-integration handler, signed repository/commit/profile/fixture/target manifests and cwd/path attack corpus. Operation: `bash -n` both files; invoke the runner from four starting directories; prove one normalized handler exec/zero runner recursion and independent script-derived physical root before target access; then inject self/equal-inode/hash/relative/symlink/copied-root/env/commit/profile and target mismatches. Output: one immutable command/handler/root/target evidence record. Test evidence: `/tmp` positive, `${10}` target argument equality, malicious path exit-`20|40` with target spy zero, and database mismatch exit-`50` before Alembic. Failure behavior: no target connection/migration starts and TEST-02 is failed.

## Test strategy

- **DDL `test_catalog_exactly_matches_46_table_constraint_index_trigger_and_owner_manifest`.**
- **Digest `test_two_rfc8785_encoders_match_three_normative_vectors_and_reject_invalid_ijson`.**
- **Atomicity `test_command_event_audit_idempotency_outbox_and_delivery_are_failure_atomic`.**
- **Provider `test_capability_gmail_and_agent_discriminated_unions_reject_cross_branch_fields`.**
- **Evaluation `test_eight_suites_552_cases_1656_fresh_captures_and_two_offline_scorers_match_agent10`.**
- **API `test_openapi_router_client_and_edge_manifests_equal_exact_66_and_64_plus_2_partition`.**
- **Policy `test_fourteen_dedicated_final_send_denials_have_zero_credential_and_provider_calls`.**
- **Incident `test_incident_four_field_routes_all_wrong_severities_resolution_and_repair_applicability_match_database`.**
- **Privileges `test_only_canonical_service_roles_can_write_each_product_or_security_runtime_record`.**
- **Entrypoint `test_absolute_runner_execs_distinct_hashed_contract_handler_once_from_tmp_and_refuses_recursion_symlink_wrong_root_env_commit_profile_or_database_before_access`.**

## Security, privacy, compliance, idempotency, observability, and cost

Database fixtures use synthetic identities and restricted roles; recipient SHA-256 is treated as pseudonymous and offline-enumerable, never exported/logged/API-visible. Contract telemetry contains safe schema/operation/reason/version only. Provider cases have zero network and zero cost. Public/legal fixtures prove enforcement shape, not legal approval. Commands and fixture captures are replay-safe by canonical hash and signed manifest.

## Failure, rollback, and operator recovery

On schema drift, irreversible migration, route widening, catalog mismatch, provider-union ambiguity, policy no-call breach, or privilege failure: stop release, disable affected adapter and both send controls, preserve catalog/OpenAPI/row/call evidence, restore the last clean test database only after resolving its identity, and fix the canonical owner rather than weakening the manifest. Never stamp Alembic head, edit rows, or update a golden snapshot merely to turn the suite green.

## Acceptance and retained evidence

- [ ] Exact strict schemas/RFC 8785 vectors and provider/agent/Gmail unions are independently reproducible.
- [ ] PostgreSQL proves all 46 tables, declared DDL/privileges/transactions/retention behavior.
- [ ] API/router/client/edge sets equal 66 operations with the exact private/public partition.
- [ ] Policy 14-denial and incident catalog/applicability matrices are closed and no-call/DB-enforced.
- [ ] `T7-CONTRACT-INTEGRATION` parses and derives the same signed root from every simulated cwd; path/root/repository/commit/profile checks precede target access and exact PostgreSQL identity precedes migration.

Retain signed manifests, schema/catalog/OpenAPI/client diffs, revision and seed hashes, JUnit/failure-injection results, provider/agent/cost fixture hashes, route/call/privilege traces and exact command output.

## Dependencies and next deliverable

TEST-02 supplies immutable boundary evidence to [TEST-03](03-workflow-recovery-tests.md), [TEST-04](04-gmail-side-effect-tests.md), [TEST-05](05-end-to-end-browser-tests.md), and INFRA-02. A passing contract suite permits those suites to execute; it does not authorize a provider call, public route, deployment, or send.
