# Domain Events, Audit, Policy, Idempotency, Outbox, and Cost Ledger

**Document ID:** DB-05
**Status:** Planned M2 transactional safety substrate
**Milestone:** M2, M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `DB-05-T01 -> DB-05-T02 -> DB-05-T03 -> DB-05-T04 -> DB-05-T05`; cross-document task Inputs `DB-05-T01 <- ARCH-03-T01; DB-05-T05 <- PROVIDER-03-T04,OBS-03-T02`. Descriptive source authorities/resources (not whole-document completion dependencies): [DB-01](01-core-data-model.md), [ARCH-02](../01-architecture/02-module-boundaries.md), and canonical [ARCH-03 event catalog](../01-architecture/03-domain-events-and-state-machines.md)
**Outputs:** Exact event/audit envelopes, command replay, policy facts, outbox delivery, consumer dedupe, provider cost, and correction/reconciliation records
**Unlocks:** Durable application commands and every M2-M9 side-effect audit chain
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

M2 makes each accepted command one atomic PostgreSQL fact: aggregate version, canonical domain event, audit record, idempotency result, and outbox notification cannot diverge. External calls use a separate committed intent/result protocol. Logs and DBOS/Temporal history assist diagnosis but never replace this product audit chain.

## Current repository state

Current structured logs carry request IDs and secret-safe operational failures. There is no persisted domain/audit event, event catalog enforcement, command replay, policy decision, outbox, delivery receipt, consumer dedupe, provider cost ledger, correction event, or reconciliation record.

## Scope and non-goals

The M9 audit/idempotency boundary treats stage admission and barrier recording as authoritative commands. Keys bind experiment version, stage ordinal, exact `SHADOW/REVIEW_20/QUALIFIED_50/SCALE_100_TO_300` increment, `0/20/50/explicitly-authorized-100-to-300` cumulative maximum, membership-set hash, prior decision reference, and expected control/policy versions. Replaying the same key returns the stored result; a different payload conflicts. Concurrent final-slot requests serialize, and no audit/event replay can create Stage 2-4 authority without the immediately prior authoritative `CONTINUE`.

In scope: ARCH-03 envelopes/names, security denials, exact command scope/key replay, transactional outbox, at-least-once consumer dedupe, policy fact hashes, cost reserve/reconcile, supersession, and repair evidence. Non-goals: full event sourcing, global event order, exactly-once network delivery, putting full PII/bodies/secrets in payloads, treating timestamps as dedupe, Kafka, or generic workflow history replication.

## Exact planned implementation surfaces

Create `domain/events.py`, `application/idempotency.py`, `application/policies.py`, `persistence/models/events.py`, outbox dispatcher/consumer registry, and M2 migration tables:

### Exact DDL-equivalent event, outbox, policy, and repair contract

```sql
CREATE TABLE domain_events (
    event_id uuid NOT NULL,
    experiment_id uuid NULL,
    event_type text NOT NULL,
    schema_version integer NOT NULL,
    aggregate_type text NOT NULL,
    aggregate_id uuid NOT NULL,
    aggregate_version bigint NOT NULL,
    occurred_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    actor_type text NOT NULL,
    actor_id text NOT NULL,
    correlation_id uuid NOT NULL,
    causation_id uuid NOT NULL,
    idempotency_key text NULL,
    payload jsonb NOT NULL,
    payload_hash char(64) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata_hash char(64) NOT NULL,
    supersedes_event_id uuid NULL,
    CONSTRAINT pk_domain_events PRIMARY KEY (event_id),
    CONSTRAINT fk_domain_events_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_domain_events_supersedes FOREIGN KEY (supersedes_event_id, experiment_id) REFERENCES domain_events (event_id, experiment_id) ON DELETE RESTRICT,
    CONSTRAINT uq_domain_events_scope UNIQUE NULLS NOT DISTINCT (event_id, experiment_id),
    CONSTRAINT uq_domain_events_aggregate_version_type UNIQUE (aggregate_type, aggregate_id, aggregate_version, event_type),
    CONSTRAINT ck_domain_events_schema CHECK (schema_version > 0 AND aggregate_version > 0),
    CONSTRAINT ck_domain_events_type CHECK (event_type ~ '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+\.v[1-9][0-9]*$'),
    CONSTRAINT ck_domain_events_actor CHECK (actor_type IN ('OPERATOR','SYSTEM','WORKFLOW','PROVIDER')),
    CONSTRAINT ck_domain_events_json CHECK (jsonb_typeof(payload) = 'object' AND jsonb_typeof(metadata) = 'object'),
    CONSTRAINT ck_domain_events_hashes CHECK (payload_hash ~ '^[0-9a-f]{64}$' AND metadata_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_domain_events_aggregate ON domain_events (aggregate_type, aggregate_id, aggregate_version);
CREATE INDEX ix_domain_events_correlation ON domain_events (correlation_id, recorded_at);
CREATE INDEX ix_domain_events_type_recorded ON domain_events (event_type, recorded_at);

CREATE TABLE audit_events (
    audit_event_id uuid NOT NULL,
    event_type text NOT NULL,
    schema_version integer NOT NULL,
    aggregate_type text NULL,
    aggregate_id uuid NULL,
    aggregate_version bigint NULL,
    actor_type text NOT NULL,
    actor_id text NOT NULL,
    outcome text NOT NULL,
    reason_codes text[] NOT NULL,
    correlation_id uuid NOT NULL,
    causation_id uuid NOT NULL,
    idempotency_key text NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    payload_hash char(64) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata_hash char(64) NOT NULL,
    occurred_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    supersedes_audit_event_id uuid NULL,
    CONSTRAINT pk_audit_events PRIMARY KEY (audit_event_id),
    CONSTRAINT fk_audit_events_supersedes FOREIGN KEY (supersedes_audit_event_id) REFERENCES audit_events (audit_event_id) ON DELETE RESTRICT,
    CONSTRAINT ck_audit_events_schema CHECK (schema_version > 0),
    CONSTRAINT ck_audit_events_type CHECK (event_type ~ '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+\.v[1-9][0-9]*$'),
    CONSTRAINT ck_audit_events_aggregate CHECK ((aggregate_type IS NULL AND aggregate_id IS NULL AND aggregate_version IS NULL) OR (aggregate_type IS NOT NULL AND aggregate_id IS NOT NULL AND aggregate_version > 0)),
    CONSTRAINT ck_audit_events_actor CHECK (actor_type IN ('OPERATOR','SYSTEM','WORKFLOW','PROVIDER')),
    CONSTRAINT ck_audit_events_outcome CHECK (outcome IN ('ALLOWED','DENIED','FAILED')),
    CONSTRAINT ck_audit_events_reasons CHECK ((outcome = 'ALLOWED') OR cardinality(reason_codes) > 0),
    CONSTRAINT ck_audit_events_json CHECK (jsonb_typeof(payload) = 'object' AND jsonb_typeof(metadata) = 'object'),
    CONSTRAINT ck_audit_events_hashes CHECK (payload_hash ~ '^[0-9a-f]{64}$' AND metadata_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_audit_events_actor ON audit_events (actor_type, actor_id, recorded_at DESC);
CREATE INDEX ix_audit_events_aggregate ON audit_events (aggregate_type, aggregate_id, recorded_at DESC) WHERE aggregate_id IS NOT NULL;
CREATE INDEX ix_audit_events_correlation ON audit_events (correlation_id, recorded_at);

CREATE TABLE command_idempotency (
    command_scope text NOT NULL,
    idempotency_key text NOT NULL,
    command_type text NOT NULL,
    request_schema_version text NOT NULL,
    request_json jsonb NOT NULL,
    request_hash char(64) NOT NULL,
    actor_type text NOT NULL,
    actor_id text NOT NULL,
    aggregate_type text NULL,
    aggregate_id uuid NULL,
    status text NOT NULL DEFAULT 'IN_PROGRESS',
    result_schema_version text NULL,
    result_json jsonb NULL,
    result_hash char(64) NULL,
    error_code text NULL,
    first_seen_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    completed_at timestamptz NULL,
    CONSTRAINT pk_command_idempotency PRIMARY KEY (command_scope, idempotency_key),
    CONSTRAINT ck_command_idempotency_request CHECK (request_schema_version ~ '^[a-z0-9][a-z0-9._-]{0,63}$' AND request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_command_idempotency_actor CHECK (actor_type IN ('OPERATOR','SYSTEM','WORKFLOW','PROVIDER')),
    CONSTRAINT ck_command_idempotency_aggregate CHECK ((aggregate_type IS NULL) = (aggregate_id IS NULL)),
    CONSTRAINT ck_command_idempotency_status CHECK (status IN ('IN_PROGRESS','SUCCEEDED','FAILED')),
    CONSTRAINT ck_command_idempotency_result CHECK ((result_schema_version IS NULL AND result_json IS NULL AND result_hash IS NULL) OR (result_schema_version ~ '^[a-z0-9][a-z0-9._-]{0,63}$' AND result_json IS NOT NULL AND result_hash ~ '^[0-9a-f]{64}$')),
    CONSTRAINT ck_command_idempotency_completion CHECK ((status = 'IN_PROGRESS' AND completed_at IS NULL AND result_hash IS NULL) OR (status = 'SUCCEEDED' AND completed_at IS NOT NULL AND result_schema_version IS NOT NULL AND result_json IS NOT NULL AND result_hash IS NOT NULL AND error_code IS NULL) OR (status = 'FAILED' AND completed_at IS NOT NULL AND result_schema_version IS NULL AND result_json IS NULL AND result_hash IS NULL AND error_code IS NOT NULL))
);
CREATE INDEX ix_command_idempotency_in_progress ON command_idempotency (first_seen_at) WHERE status = 'IN_PROGRESS';
CREATE INDEX ix_command_idempotency_aggregate ON command_idempotency (aggregate_type, aggregate_id, first_seen_at DESC) WHERE aggregate_id IS NOT NULL;

CREATE TABLE outbox_messages (
    outbox_message_id uuid NOT NULL,
    event_id uuid NOT NULL,
    topic text NOT NULL,
    payload_version integer NOT NULL,
    payload jsonb NOT NULL,
    payload_hash char(64) NOT NULL,
    available_at timestamptz NOT NULL,
    lease_owner text NULL,
    lease_expires_at timestamptz NULL,
    published_at timestamptz NULL,
    attempt_count integer NOT NULL DEFAULT 0,
    last_error_code text NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_outbox_messages PRIMARY KEY (outbox_message_id),
    CONSTRAINT fk_outbox_messages_event FOREIGN KEY (event_id) REFERENCES domain_events (event_id) ON DELETE RESTRICT,
    CONSTRAINT uq_outbox_messages_event_topic UNIQUE (event_id, topic),
    CONSTRAINT ck_outbox_messages_payload CHECK (payload_version > 0 AND jsonb_typeof(payload) = 'object' AND payload_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_outbox_messages_attempts CHECK (attempt_count >= 0),
    CONSTRAINT ck_outbox_messages_lease CHECK ((lease_owner IS NULL AND lease_expires_at IS NULL) OR (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)),
    CONSTRAINT ck_outbox_messages_publish CHECK (published_at IS NULL OR published_at >= created_at)
);
CREATE INDEX ix_outbox_messages_available ON outbox_messages (available_at, created_at) WHERE published_at IS NULL;
CREATE INDEX ix_outbox_messages_lease ON outbox_messages (lease_expires_at) WHERE published_at IS NULL AND lease_owner IS NOT NULL;

CREATE TABLE outbox_deliveries (
    consumer_name text NOT NULL,
    event_id uuid NOT NULL,
    handler_version text NOT NULL,
    result_hash char(64) NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_outbox_deliveries PRIMARY KEY (consumer_name, event_id),
    CONSTRAINT fk_outbox_deliveries_event FOREIGN KEY (event_id) REFERENCES domain_events (event_id) ON DELETE RESTRICT,
    CONSTRAINT ck_outbox_deliveries_result_hash CHECK (result_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_outbox_deliveries_event ON outbox_deliveries (event_id, processed_at);

CREATE TABLE policy_decisions (
    policy_decision_id uuid PRIMARY KEY,
    scope text NOT NULL CHECK (scope IN ('EXPERIMENT','CAMPAIGN','ACTION_CREATION','SEND','COMMERCIAL','BOOKING','CHECKPOINT','STRATEGY','PROVIDER','CONTROL')),
    action_id uuid NULL,
    action_kind text NULL,
    experiment_id uuid NULL,
    campaign_id uuid NULL,
    cohort_id uuid NULL,
    campaign_member_id uuid NULL,
    authorization_id uuid NULL,
    scope_hash char(64) NOT NULL,
    policy_version text NOT NULL,
    allowed boolean NOT NULL,
    reason_codes text[] NOT NULL,
    facts_schema_version text NOT NULL,
    facts_ciphertext bytea NOT NULL,
    facts_hash char(64) NOT NULL,
    action_attribution_id uuid NULL,
    control_generation bigint NOT NULL,
    checkpoint_generation bigint NULL,
    evaluated_at timestamptz NOT NULL,
    correlation_id uuid NOT NULL,
    idempotency_key text NOT NULL,
    CONSTRAINT uq_policy_decisions_key UNIQUE (scope, idempotency_key),
    CONSTRAINT uq_policy_decisions_authority UNIQUE (policy_decision_id, scope, action_id, action_kind, cohort_id, campaign_member_id, scope_hash, facts_hash, policy_version, allowed),
    CONSTRAINT ck_policy_decisions_denial CHECK (allowed OR cardinality(reason_codes) > 0),
    CONSTRAINT ck_policy_decisions_hashes CHECK (scope_hash ~ '^[0-9a-f]{64}$' AND facts_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_policy_decisions_generation CHECK (control_generation > 0 AND (checkpoint_generation IS NULL OR checkpoint_generation > 0)),
    CONSTRAINT ck_policy_decisions_action_binding CHECK (scope NOT IN ('SEND','BOOKING') OR (action_id IS NOT NULL AND action_kind IS NOT NULL AND cohort_id IS NOT NULL AND campaign_member_id IS NOT NULL AND authorization_id IS NOT NULL AND action_attribution_id IS NOT NULL))
);
CREATE INDEX ix_policy_decisions_action ON policy_decisions (action_id, evaluated_at);
CREATE INDEX ix_policy_decisions_cohort ON policy_decisions (cohort_id, evaluated_at);

CREATE TABLE cost_entries (
    cost_entry_id uuid NOT NULL,
    provider text NOT NULL,
    operation text NOT NULL,
    provider_call_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    workflow_run_id uuid NULL,
    agent_run_id uuid NULL,
    send_attempt_id uuid NULL,
    provider_result_id uuid NULL,
    booking_attempt_id uuid NULL,
    booking_result_id uuid NULL,
    action_attribution_id uuid NULL,
    usage_schema_version integer NOT NULL,
    usage_json jsonb NOT NULL,
    usage_hash char(64) NOT NULL,
    amount_minor bigint NOT NULL,
    currency char(3) NOT NULL,
    reporting_amount_minor_ils bigint NULL,
    fx_rate numeric NULL,
    fx_rate_source text NULL,
    fx_rate_date date NULL,
    provider_invoice_ref text NULL,
    occurred_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    idempotency_key text NOT NULL,
    CONSTRAINT pk_cost_entries PRIMARY KEY (cost_entry_id),
    CONSTRAINT fk_cost_entries_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_cost_entries_workflow FOREIGN KEY (workflow_run_id, experiment_id) REFERENCES workflow_runs (workflow_run_id, experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_cost_entries_agent_run FOREIGN KEY (agent_run_id, experiment_id, workflow_run_id) REFERENCES agent_runs (agent_run_id, experiment_id, workflow_run_id) ON DELETE RESTRICT,
    CONSTRAINT fk_cost_entries_send_attempt FOREIGN KEY (send_attempt_id, experiment_id) REFERENCES send_attempts (send_attempt_id, experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_cost_entries_provider_result FOREIGN KEY (provider_result_id, send_attempt_id, provider_call_id, provider) REFERENCES provider_results (provider_result_id, send_attempt_id, provider_call_id, provider) ON DELETE RESTRICT,
    CONSTRAINT uq_cost_entries_provider_call UNIQUE (provider, provider_call_id),
    CONSTRAINT uq_cost_entries_provider_key UNIQUE (provider, idempotency_key),
    CONSTRAINT uq_cost_entries_authority UNIQUE (cost_entry_id, experiment_id, currency),
    CONSTRAINT ck_cost_entries_usage CHECK (usage_schema_version > 0 AND jsonb_typeof(usage_json) = 'object' AND usage_hash ~ '^[0-9a-f]{64}$' AND usage_json ? 'provider_call_id' AND usage_json ->> 'provider_call_id' = provider_call_id::text AND idempotency_key = provider_call_id::text),
    CONSTRAINT ck_cost_entries_provenance_shape CHECK (
        (agent_run_id IS NULL AND send_attempt_id IS NULL AND provider_result_id IS NULL AND booking_attempt_id IS NULL AND booking_result_id IS NULL) OR
        (agent_run_id IS NOT NULL AND workflow_run_id IS NOT NULL AND send_attempt_id IS NULL AND provider_result_id IS NULL AND booking_attempt_id IS NULL AND booking_result_id IS NULL) OR
        (agent_run_id IS NULL AND workflow_run_id IS NULL AND send_attempt_id IS NOT NULL AND provider_result_id IS NOT NULL AND booking_attempt_id IS NULL AND booking_result_id IS NULL) OR
        (agent_run_id IS NULL AND workflow_run_id IS NULL AND send_attempt_id IS NULL AND provider_result_id IS NULL AND booking_attempt_id IS NOT NULL AND booking_result_id IS NOT NULL)
    ),
    CONSTRAINT ck_cost_entries_amount CHECK (amount_minor >= 0 AND currency ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_cost_entries_fx CHECK ((currency = 'ILS' AND reporting_amount_minor_ils = amount_minor AND fx_rate IS NULL AND fx_rate_source IS NULL AND fx_rate_date IS NULL) OR (currency <> 'ILS' AND reporting_amount_minor_ils IS NOT NULL AND fx_rate > 0 AND fx_rate_source IS NOT NULL AND fx_rate_date IS NOT NULL))
);
CREATE INDEX ix_cost_entries_experiment_provider ON cost_entries (experiment_id, provider, occurred_at DESC);
CREATE INDEX ix_cost_entries_workflow ON cost_entries (workflow_run_id, occurred_at DESC) WHERE workflow_run_id IS NOT NULL;

CREATE TABLE repair_actions (
    repair_action_id uuid NOT NULL,
    incident_id uuid NOT NULL,
    catalog_version text NOT NULL DEFAULT 'incident.catalog.v1',
    incident_severity text NOT NULL,
    incident_trigger_code text NOT NULL,
    incident_alert_id text NOT NULL,
    incident_runbook_id text NOT NULL,
    repair_kind text NOT NULL,
    command_type text NOT NULL,
    aggregate_type text NOT NULL,
    aggregate_id uuid NOT NULL,
    before_hash char(64) NOT NULL,
    after_hash char(64) NOT NULL,
    reason_code text NOT NULL,
    operator_id uuid NOT NULL,
    evidence_ref text NOT NULL,
    idempotency_key text NOT NULL,
    executed_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_repair_actions PRIMARY KEY (repair_action_id),
    CONSTRAINT fk_repair_actions_incident FOREIGN KEY (incident_id, catalog_version, incident_severity, incident_trigger_code, incident_alert_id, incident_runbook_id) REFERENCES incidents (incident_id, catalog_version, severity, trigger_code, alert_id, runbook_id) ON DELETE RESTRICT,
    CONSTRAINT fk_repair_actions_operator FOREIGN KEY (operator_id) REFERENCES operators (operator_id) ON DELETE RESTRICT,
    CONSTRAINT uq_repair_actions_command UNIQUE (operator_id, idempotency_key),
    CONSTRAINT ck_repair_actions_catalog CHECK (catalog_version = 'incident.catalog.v1'),
    CONSTRAINT ck_repair_actions_kind CHECK (repair_kind IN ('RECONCILE_GMAIL_ATTEMPT','ABORT_OAUTH_SAGA','REVOKE_OPERATOR_SESSIONS','DISABLE_MAILBOX','ROTATE_SECRET_GENERATION','REPAIR_WORKFLOW_PROJECTION','REPAIR_EVENT_OUTBOX_LINK','RESTORE_FROM_VERIFIED_BACKUP','REAPPLY_RECIPIENT_SUPPRESSION','REPLAY_RETENTION_TOMBSTONE','RECONCILE_PROVIDER_COST','IMPORT_OFFLINE_INCIDENT_JOURNAL','ROLLBACK_AGENT_PROMOTION')),
    CONSTRAINT ck_repair_actions_applicability CHECK ((repair_kind = 'RECONCILE_GMAIL_ATTEMPT' AND incident_trigger_code IN ('GMAIL_AMBIGUITY_STALE','SEND_AUTHORITY_VIOLATION')) OR (repair_kind = 'ABORT_OAUTH_SAGA' AND incident_trigger_code IN ('AUTH_OR_SECRET_COMPROMISE','CALLBACK_ABUSE','OPERATOR_OR_RECOVERY_ERROR')) OR (repair_kind = 'REVOKE_OPERATOR_SESSIONS' AND incident_trigger_code IN ('AUTH_OR_SECRET_COMPROMISE','WEB_SESSION_BOUNDARY_ATTACK','AUTHORIZATION_OR_ENUMERATION')) OR (repair_kind = 'DISABLE_MAILBOX' AND incident_trigger_code IN ('PROVIDER_EXFILTRATION','AUTH_OR_SECRET_COMPROMISE','SEND_AUTHORITY_VIOLATION','COMPLIANCE_OR_SUPPRESSION_BREACH','GMAIL_AMBIGUITY_STALE')) OR (repair_kind = 'ROTATE_SECRET_GENERATION' AND incident_trigger_code IN ('PROVIDER_EXFILTRATION','AUTH_OR_SECRET_COMPROMISE','SUPPLY_CHAIN_COMPROMISE')) OR (repair_kind = 'REPAIR_WORKFLOW_PROJECTION' AND incident_trigger_code IN ('WORKFLOW_REPLAY_OR_VERSION_DRIFT','OPERATOR_OR_RECOVERY_ERROR')) OR (repair_kind = 'REPAIR_EVENT_OUTBOX_LINK' AND incident_trigger_code IN ('WORKFLOW_REPLAY_OR_VERSION_DRIFT','DATASTORE_OR_RESTORE_FAILURE','OPERATOR_OR_RECOVERY_ERROR')) OR (repair_kind = 'RESTORE_FROM_VERIFIED_BACKUP' AND incident_trigger_code = 'DATASTORE_OR_RESTORE_FAILURE') OR (repair_kind = 'REAPPLY_RECIPIENT_SUPPRESSION' AND incident_trigger_code = 'COMPLIANCE_OR_SUPPRESSION_BREACH') OR (repair_kind = 'REPLAY_RETENTION_TOMBSTONE' AND incident_trigger_code IN ('DATASTORE_OR_RESTORE_FAILURE','OPERATOR_OR_RECOVERY_ERROR','TELEMETRY_PRIVACY_LEAK','COMPLIANCE_OR_SUPPRESSION_BREACH')) OR (repair_kind = 'RECONCILE_PROVIDER_COST' AND incident_trigger_code = 'COST_OR_QUOTA_RUNAWAY') OR (repair_kind = 'IMPORT_OFFLINE_INCIDENT_JOURNAL' AND incident_trigger_code IN ('DATASTORE_OR_RESTORE_FAILURE','OPERATOR_OR_RECOVERY_ERROR','TELEMETRY_OR_ALERT_BLINDNESS')) OR (repair_kind = 'ROLLBACK_AGENT_PROMOTION' AND incident_trigger_code IN ('AGENT_PROMPT_INJECTION_OR_POISONING','SUPPLY_CHAIN_COMPROMISE','WORKFLOW_REPLAY_OR_VERSION_DRIFT'))),
    CONSTRAINT ck_repair_actions_hashes CHECK (before_hash ~ '^[0-9a-f]{64}$' AND after_hash ~ '^[0-9a-f]{64}$' AND before_hash <> after_hash),
    CONSTRAINT ck_repair_actions_no_sql CHECK (command_type !~* 'sql')
);
CREATE INDEX ix_repair_actions_incident ON repair_actions (incident_id, executed_at);
```

`command_idempotency.request_hash` and present `result_hash` use DB-01's exact UTF-8 RFC 8785 envelope digest with the stored text schema version and JSON payload. `IN_PROGRESS` and `FAILED` have all result columns SQL `NULL`; `SUCCEEDED` has the complete triplet. Replay verifies bytes and schema version before returning a stored result; version migration never mutates an existing command row.

`cost_entries` has exact disjoint provenance shapes: shared operation (all optional owner IDs null), workflow-only, agent (`agent_run_id` plus its exact `experiment_id` and owning `workflow_run_id`), or Gmail send (`send_attempt_id` plus the exact same-attempt/call/provider `provider_result_id`, with workflow/agent null), or calendar booking (booking_attempt_id plus booking_result_id with exact provider_call_id/calendar/action evidence and workflow/agent/send IDs null). `provider_call_id` is mandatory and distinct from aggregate identities; it equals both the provider idempotency key and `usage_json.provider_call_id`. Allocation therefore cannot be duplicated across workflow/agent/send levels: an agent from W1 cannot be attached to W2, a send/result cannot be paired with a workflow, and a result or call from another Gmail operation fails the named four-column composite FK. `ProviderCostReconciliationService` additionally verifies the signed provider ledger/request/result hashes before insert; JSON never substitutes for the relational run/result constraints. Deferred fk_cost_entries_booking_result binds (booking_result_id,booking_attempt_id,provider_call_id) to the exact immutable booking result; agent/Gmail/calendar costs cannot cross branches or be counted twice.

`repair_kind` is the closed recovery action selector; `command_type` is the exact existing typed command it invokes. API, audit, telemetry and UI carry the registered kind, never a caller string. `RecoveryCommandService` rejects unknown catalog/version/kind before command claim, and exact replay requires the original kind, before/after hashes and evidence. Adding a repair kind requires the same additive catalog-version migration protocol as incidents plus a typed inverse/recovery test; removing or silently remapping a retained kind is forbidden.

| Table | Exclusive write owner | Retention class / retention owner |
| --- | --- | --- |
| `domain_events` | application `UnitOfWork` after a valid transition | `SAFETY_LONG` / `RetentionCommandService` |
| `audit_events` | application `AuditRecorder` in the command unit of work | `SAFETY_LONG` / `RetentionCommandService` |
| `command_idempotency` | `IdempotentCommandExecutor` in the same command transaction | `SAFETY_LONG` / `RetentionCommandService` |
| `outbox_messages` | application `UnitOfWork` with its source domain event | `SAFETY_LONG` / `RetentionCommandService` |
| `outbox_deliveries` | `OutboxDeliveryReceiptService` inside the named consumer's PostgreSQL unit of work | `SAFETY_LONG` / `RetentionCommandService` |
| `policy_decisions` | deterministic `PolicyEvaluationService` | `SAFETY_LONG` / `RetentionCommandService` |
| `cost_entries` | `ProviderCostReconciliationService` | `SAFETY_LONG` / `RetentionCommandService` |
| `repair_actions` | authenticated `RecoveryCommandService` | `SAFETY_LONG` / `RetentionCommandService` |

`record_kind` from ARCH-03 is represented by table membership (`DOMAIN` or `AUDIT`) and exposed as a union projection. Every event name retains its `.v1` suffix. The registry includes the complete `campaign.ready/activated/paused/resumed/completed/cancelled/failed/state_changed.v1` family and distinct `send.provider_accepted.v1`; `send.reconciled_as_sent.v1` is legal only after an ambiguous attempt. Incompatible payloads add a new event name/version and reader/upcaster; old rows are never rewritten.

### Command and side-effect atomicity

For aggregate commands: begin; claim `(command_scope,idempotency_key)`; verify DB-01's RFC 8785 request envelope digest and compare it; load expected version; apply pure transition; update aggregate; insert the specific event plus the aggregate's canonical `*.state_changed.v1` event where defined; insert audit; insert outbox; store result; commit. For provider work: ActionAuthorizationService creates immutable ActionAuthorityScopeV1 from a deterministic ACTION_CREATION decision, then unique consumption binds one intent. The last-mile transaction records a new SEND/BOOKING decision, same immutable scope_hash and independent current facts_hash, exact consumed rate/calendar lease and attempt before network. The result transaction records acceptance, conclusive failure or ambiguity. A crash in the gap enters exact-authority reconciliation, never automatic retry.

An internal outbox consumer starts one PostgreSQL transaction, rechecks absence of `(consumer_name,event_id)`, performs all internal business writes, invokes OutboxDeliveryReceiptService to insert `outbox_deliveries` in that same transaction, and commits once. A crash rolls back both the business writes and delivery receipt; redelivery re-executes the same transaction. External provider effects are forbidden in that transaction and forbidden from any generic “effect once” claim. Gmail/model/search/extraction effects use their explicit intent/result/error or `AMBIGUOUS`/reconciliation contracts.

### Action-level strategy attribution and exceptions

The following normalized records are part of the exact product schema, with DB-02 physical field/type conventions. Both have created_at timestamptz. AuditRecorder writes action_attributions in the owner's transaction; ExceptionCommandService writes exception_cases. RetentionCommandService alone purges eligible payloads.

| Table | Fields and constraints |
| --- | --- |
| action_attributions | action_attribution_id PK; action_kind AGENT_CALL/POLICY_DECISION/DRAFT/SEND/NEGOTIATION_PROPOSAL/NEGOTIATION_DECISION/BOOKING_ACTION/CHECKPOINT/LEARNING_DECISION; action_id; action_version; experiment_id?; campaign_id?; cohort_id?; checkpoint_id?; offer_id/version/hash?; strategy_version_id/hash; activation_id?; producer_strategy_version; input_snapshot_id/hash?; control_generation; checkpoint_generation?; attribution_mode PRODUCT/EVALUATION_ONLY; content_hash. UQ (action_kind,action_id,action_version); deferred typed-target FK/constraint registry rejects wrong target, cross-cohort activation or cross-offer package; product actions require exact governing activation, and a pre-cohort global learning decision pins triggering checkpoint activation; isolated evaluation-only calls require signed candidate manifest and no product scope. Index (strategy_version_id,cohort_id,action_kind). |
| exception_cases | exception_id PK; experiment_id?; campaign_id?; cohort_id?; conversation_id?; booking_intent_id?; action_id?; reason_code; severity; state OPEN/INVESTIGATING/RESOLVED/DISMISSED; expected_control_generation; evidence_ref_set_hash; incident_id?; opened_at; resolved_at?; resolution_command_key?; resolution_reason?. All scope references must agree; index (state,opened_at). Resolution is an authenticated bounded correction/repair, never a waiver of protected bounds or an instruction to send. |

Every agent call, policy decision, draft, send, negotiation proposal/decision, booking action, checkpoint and learning result gets its own immutable attribution row. Campaign-level tags alone are insufficient. Global strategy rows are not tied to one experiment; action attribution pins a real activation plus exact global package hash. Rollback affects future actions only and cannot UPDATE attribution.

Event payload schemas consume ARCH-03's complete action, conversation, cohort, booking, checkpoint, learning and strategy catalogs, including action.authorization_created.v1, booking.confirmed.v1, checkpoint.evidence_frozen.v1 and checkpoint.decision_recorded.v1. No fixed historical event count limits this catalog. Unknown names/versions/actors fail before insert. Raw email/calendar/contact/budget text belongs in encrypted purpose-scoped data, never event/audit/outbox/idempotent safe responses.

The deferred FK/trigger stage verifies action_authorizations creation decision, exact single consumption target, intent/action scope, fresh SEND/BOOKING decision plus immutable attribution, and checkpoint/strategy source links. Historical immutable tuple references do not include mutable status/generation pointers as parent keys; fresh-gate checks read current status under lock.

## Ordered implementation tasks

<!-- roadmap-task id=DB-05-T01 milestone=M2 depends_on=ARCH-03-T01 mode=parallel locks=architecture-contracts,backend-domain -->
- [ ] **Encode event schemas/catalog —** Input: every ARCH-03 `.v1` name/payload. Operation: register typed payload, aggregate applicability, actor rules, redaction, and upcast policy. Output: executable catalog. Test evidence: `test_arch03_event_catalog_is_exact_and_complete`. Failure behavior: unknown/malformed event aborts transaction.
<!-- roadmap-task id=DB-05-T02 milestone=M2 depends_on=DB-05-T01 mode=serial locks=database-schema,migration-head -->
- [ ] **Migrate append-only safety tables —** Input: table contract. Operation: create constraints/indexes/immutable protections and FKs. Output: M2 event/audit/idempotency/outbox/policy/cost schema. Test evidence: migration introspection and mutation-denial tests. Failure behavior: rollback revision.
<!-- roadmap-task id=DB-05-T03 milestone=M2 depends_on=DB-05-T02 mode=parallel locks=database-schema,backend-domain -->
- [ ] **Implement idempotent command middleware —** Input: authenticated command, scope/key, canonical request hash. Operation: implement the shared UnitOfWork/IdempotentCommandExecutor middleware to claim or replay the exact result inside one atomic transaction with audit/event writes; later product command composition delegates to this sole implementation. Output: implemented versioned IdempotentCommandExecutor atomic claim/replay/UnitOfWork interface plus one command effect. Test evidence: concurrent duplicate and hash-conflict tests. Failure behavior: typed conflict; no second effect.
<!-- roadmap-task id=DB-05-T04 milestone=M2 depends_on=DB-05-T03 mode=parallel locks=database-schema,workflow-runtime,backend-domain -->
- [ ] **Implement outbox and internal consumer atomicity —** Input: committed outbox rows. Operation: lease a bounded batch, publish at least once, implement OutboxDeliveryReceiptService as the exclusive receipt writer, and make each internal consumer commit its business writes plus that service's `outbox_deliveries` receipt in one PostgreSQL transaction. Output: eventually delivered internal events with atomic consumer effects. Test evidence: crash before business write, between business write and receipt, before commit, and after commit. Failure behavior: rollback/redeliver for internal writes; bounded backoff/dead-letter incident for poison events; external effects are rejected from this path.
<!-- roadmap-task id=DB-05-T05 milestone=M3 depends_on=DB-05-T04,PROVIDER-03-T04,OBS-03-T02 mode=parallel locks=database-schema,provider-contracts,backend-domain,telemetry-catalog -->
- [ ] **Implement policy/cost reconciliation —** Input: frozen facts/provider usage. Operation: persist decision before authority and reconcile reservation to cost afterward. Output: explainable gate and cost ledger. Test evidence: overspend, duplicate invoice, currency, and missing-result tests. Failure behavior: deny/disable paid call and open discrepancy.

## Test strategy

- **Contract `test_arch03_event_names_and_payload_ids_are_exact`:** no alias or missing suffix.
- **Integration `test_command_bundle_rolls_back_at_every_write`:** aggregate/event/audit/idempotency/outbox are indivisible.
- **Concurrency `test_same_command_key_different_hash_conflicts`:** no confused replay.
- **Recovery `test_internal_consumer_business_writes_and_delivery_receipt_commit_together`:** every injected crash rolls back both or commits both; redelivery is safe.
- **Contract `test_external_side_effects_cannot_run_in_outbox_consumer_transaction`:** provider effects require intent/result/ambiguity/reconciliation instead of a generic effect-once assertion.
- **Security `test_event_payload_allowlist_excludes_secrets_pii_and_message_body`:** fixture scan.
- **Cost `test_reservation_reconciles_original_and_ils_reporting_currency`:** no silent mixing.
- **Registry `test_repair_action_catalog_version_and_kind_are_closed_and_replay_exact`:** every v1 kind maps to one typed handler; unknown or remapped kinds fail application validation and the DB check.

## Security, privacy, compliance, idempotency, observability, and cost

Payload schemas are allowlists and prefer references/hashes. Actor/authority, denials, action authorizations, controls, ambiguous results, repairs, and credential actions are audited. Correlation/causation spans HTTP, workflow, agent, policy, provider, and outbox. Metrics expose lag, retries, stuck commands, unresolved ambiguity, policy denials, budget variance, and safe error codes. Cost entries preserve provider currency and conversion evidence.

## Failure, rollback, and operator recovery

Unknown schema, version gap, idempotency hash mismatch, impossible actor, or partial write aborts the command. Stuck `IN_PROGRESS` commands are inspected against aggregate/events before an audited recovery claim. Poison outbox messages are quarantined with incident evidence; they do not roll back committed business state. Corrections append superseding events/audits. Repair commands record before/after hashes and never execute user-supplied SQL.

## Acceptance and retained evidence

- [ ] Every canonical event maps to a typed schema and exact payload identifiers.
- [ ] Every mutation/denial has actor, authority, correlation, causation, idempotency, and audit evidence.
- [ ] Command replay cannot duplicate command effects; internal outbox consumer writes and delivery receipt are atomic; external provider effects never rely on generic outbox effect-once semantics.
- [ ] Logs/runtime history are explicitly non-authoritative.
- [ ] Cost and policy decisions are reproducible and linked to side effects.

Retain event registry snapshots, constraint output, rollback injection traces, concurrency/replay results, outbox crash matrix, payload scans, policy fixtures, and budget/cost reconciliations.

## Dependencies and next deliverable

DB-05 depends on DB-01 and ARCH-03, and supplies FKs/transaction rules to DB-02 through DB-04. It unlocks [DB-06](06-migrations-seeding-and-retention.md) and all product workflows beginning with [WF-02](../03-workflows/02-experiment-lifecycle.md).
