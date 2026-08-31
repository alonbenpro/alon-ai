# Domain Events, Audit, Policy, Idempotency, Outbox, and Cost Ledger

**Document ID:** DB-05
**Status:** Planned M2 transactional safety substrate
**Milestone:** M2
**Owner:** Solo operator
**Prerequisites:** [DB-01](01-core-data-model.md), [ARCH-02](../01-architecture/02-module-boundaries.md), and canonical [ARCH-03 event catalog](../01-architecture/03-domain-events-and-state-machines.md)
**Outputs:** Exact event/audit envelopes, command replay, policy facts, outbox delivery, consumer dedupe, provider cost, and correction/reconciliation records
**Unlocks:** Durable application commands and every M2-M9 side-effect audit chain
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

M2 makes each accepted command one atomic PostgreSQL fact: aggregate version, canonical domain event, audit record, idempotency result, and outbox notification cannot diverge. External calls use a separate committed intent/result protocol. Logs and DBOS/Temporal history assist diagnosis but never replace this product audit chain.

## Current repository state

Current structured logs carry request IDs and secret-safe operational failures. There is no persisted domain/audit event, event catalog enforcement, command replay, policy decision, outbox, delivery receipt, consumer dedupe, provider cost ledger, correction event, or reconciliation record.

## Scope and non-goals

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
    policy_decision_id uuid NOT NULL,
    scope text NOT NULL,
    experiment_id uuid NULL,
    campaign_id uuid NULL,
    campaign_version integer NULL,
    campaign_member_id uuid NULL,
    lead_id uuid NULL,
    message_id uuid NULL,
    message_version bigint NULL,
    message_content_hash char(64) NULL,
    mailbox_id uuid NULL,
    approval_id uuid NULL,
    approval_preview_materialization_hash char(64) NULL,
    artifact_version_refs_hash char(64) NULL,
    evidence_artifact_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    policy_version text NOT NULL,
    allowed boolean NOT NULL,
    reason_codes text[] NOT NULL,
    facts_schema_version integer NOT NULL,
    facts_json jsonb NOT NULL,
    facts_hash char(64) NOT NULL,
    scope_hash char(64) NOT NULL,
    correlation_id uuid NOT NULL,
    idempotency_key text NOT NULL,
    evaluated_at timestamptz NOT NULL,
    CONSTRAINT pk_policy_decisions PRIMARY KEY (policy_decision_id),
    CONSTRAINT fk_policy_decisions_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_policy_decisions_campaign_authority FOREIGN KEY (campaign_id, campaign_version, experiment_id) REFERENCES campaigns (campaign_id, campaign_version, experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_policy_decisions_message_authority FOREIGN KEY (message_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, mailbox_id, message_version, message_content_hash) REFERENCES outreach_messages (message_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, mailbox_id, version, content_hash) ON DELETE RESTRICT,
    CONSTRAINT fk_policy_decisions_send_approval FOREIGN KEY (approval_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, message_version, message_content_hash, scope_hash, artifact_version_refs_hash, approval_preview_materialization_hash) REFERENCES approvals (approval_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, message_version, message_content_hash, scope_hash, artifact_version_refs_hash, preview_materialization_hash) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT uq_policy_decisions_command UNIQUE (scope, idempotency_key),
    CONSTRAINT uq_policy_decisions_mailbox_identity UNIQUE (policy_decision_id, mailbox_id),
    CONSTRAINT uq_policy_decisions_approval_basis UNIQUE NULLS NOT DISTINCT (policy_decision_id, scope, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, message_version, message_content_hash, mailbox_id, policy_version, scope_hash, artifact_version_refs_hash, facts_hash, allowed),
    CONSTRAINT uq_policy_decisions_send_authority UNIQUE NULLS NOT DISTINCT (policy_decision_id, scope, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, message_version, message_content_hash, mailbox_id, approval_id, approval_preview_materialization_hash, policy_version, scope_hash, artifact_version_refs_hash, facts_hash, allowed),
    CONSTRAINT ck_policy_decisions_scope CHECK (scope IN ('EXPERIMENT','CAMPAIGN','APPROVAL_ELIGIBILITY','SEND','PROVIDER','CONTROL')),
    CONSTRAINT ck_policy_decisions_campaign_pair CHECK ((campaign_id IS NULL) = (campaign_version IS NULL)),
    CONSTRAINT ck_policy_decisions_approval_send_binding CHECK (
        (scope = 'APPROVAL_ELIGIBILITY' AND experiment_id IS NOT NULL AND campaign_id IS NOT NULL AND campaign_version IS NOT NULL AND campaign_member_id IS NOT NULL AND lead_id IS NOT NULL AND message_id IS NOT NULL AND message_version > 0 AND message_content_hash ~ '^[0-9a-f]{64}$' AND mailbox_id IS NOT NULL AND approval_id IS NULL AND approval_preview_materialization_hash IS NULL AND artifact_version_refs_hash ~ '^[0-9a-f]{64}$') OR
        (scope = 'SEND' AND experiment_id IS NOT NULL AND campaign_id IS NOT NULL AND campaign_version IS NOT NULL AND campaign_member_id IS NOT NULL AND lead_id IS NOT NULL AND message_id IS NOT NULL AND message_version > 0 AND message_content_hash ~ '^[0-9a-f]{64}$' AND mailbox_id IS NOT NULL AND approval_id IS NOT NULL AND approval_preview_materialization_hash ~ '^[0-9a-f]{64}$' AND artifact_version_refs_hash ~ '^[0-9a-f]{64}$') OR
        scope NOT IN ('APPROVAL_ELIGIBILITY','SEND')
    ),
    CONSTRAINT ck_policy_decisions_reasons CHECK ((allowed AND cardinality(reason_codes) >= 0) OR (NOT allowed AND cardinality(reason_codes) > 0)),
    CONSTRAINT ck_policy_decisions_facts CHECK (facts_schema_version > 0 AND jsonb_typeof(facts_json) = 'object' AND jsonb_typeof(evidence_artifact_refs) = 'array' AND facts_hash ~ '^[0-9a-f]{64}$' AND scope_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_policy_decisions_reproducibility ON policy_decisions (policy_version, scope_hash, facts_hash);
CREATE INDEX ix_policy_decisions_mailbox ON policy_decisions (mailbox_id, evaluated_at DESC) WHERE mailbox_id IS NOT NULL;
CREATE INDEX ix_policy_decisions_approval ON policy_decisions (approval_id, evaluated_at DESC) WHERE approval_id IS NOT NULL;

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
        (agent_run_id IS NULL AND send_attempt_id IS NULL AND provider_result_id IS NULL) OR
        (agent_run_id IS NOT NULL AND workflow_run_id IS NOT NULL AND send_attempt_id IS NULL AND provider_result_id IS NULL) OR
        (agent_run_id IS NULL AND workflow_run_id IS NULL AND send_attempt_id IS NOT NULL AND provider_result_id IS NOT NULL)
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

`cost_entries` has four closed provenance shapes: shared operation (all optional owner IDs null), workflow-only, agent (`agent_run_id` plus its exact `experiment_id` and owning `workflow_run_id`), or Gmail send (`send_attempt_id` plus the exact same-attempt/call/provider `provider_result_id`, with workflow/agent null). `provider_call_id` is mandatory and distinct from aggregate identities; it equals both the provider idempotency key and `usage_json.provider_call_id`. Allocation therefore cannot be duplicated across workflow/agent/send levels: an agent from W1 cannot be attached to W2, a send/result cannot be paired with a workflow, and a result or call from another Gmail operation fails the named four-column composite FK. `ProviderCostReconciliationService` additionally verifies the signed provider ledger/request/result hashes before insert; JSON never substitutes for the relational run/result constraints.

`repair_kind` is the closed recovery action selector; `command_type` is the exact existing typed command it invokes. API, audit, telemetry and UI carry the registered kind, never a caller string. `RecoveryCommandService` rejects unknown catalog/version/kind before command claim, and exact replay requires the original kind, before/after hashes and evidence. Adding a repair kind requires the same additive catalog-version migration protocol as incidents plus a typed inverse/recovery test; removing or silently remapping a retained kind is forbidden.

| Table | Exclusive write owner | Retention class / retention owner |
| --- | --- | --- |
| `domain_events` | application `UnitOfWork` after a valid transition | `SAFETY_LONG` / `RetentionCommandService` |
| `audit_events` | application `AuditRecorder` in the command unit of work | `SAFETY_LONG` / `RetentionCommandService` |
| `command_idempotency` | `IdempotentCommandExecutor` in the same command transaction | `SAFETY_LONG` / `RetentionCommandService` |
| `outbox_messages` | application `UnitOfWork` with its source domain event | `SAFETY_LONG` / `RetentionCommandService` |
| `outbox_deliveries` | each named internal consumer's PostgreSQL unit of work | `SAFETY_LONG` / `RetentionCommandService` |
| `policy_decisions` | deterministic `PolicyEvaluationService` | `SAFETY_LONG` / `RetentionCommandService` |
| `cost_entries` | `ProviderCostReconciliationService` | `SAFETY_LONG` / `RetentionCommandService` |
| `repair_actions` | authenticated `RecoveryCommandService` | `SAFETY_LONG` / `RetentionCommandService` |

`record_kind` from ARCH-03 is represented by table membership (`DOMAIN` or `AUDIT`) and exposed as a union projection. Every event name retains its `.v1` suffix. The registry includes the complete `campaign.ready/activated/paused/resumed/completed/cancelled/failed/state_changed.v1` family and distinct `send.provider_accepted.v1`; `send.reconciled_as_sent.v1` is legal only after an ambiguous attempt. Incompatible payloads add a new event name/version and reader/upcaster; old rows are never rewritten.

### Command and side-effect atomicity

For aggregate commands: begin; claim `(command_scope,idempotency_key)`; verify DB-01's RFC 8785 request envelope digest and compare it; load expected version; apply pure transition; update aggregate; insert the specific event plus the aggregate's canonical `*.state_changed.v1` event where defined; insert audit; insert outbox; store result; commit. For provider work: `RequestApproval` first records one `APPROVAL_ELIGIBILITY` decision and approval basis without ApprovalRule; an approved row never inherits send authority. The last-mile transaction records a new `SEND` decision with `approval_id`, the same immutable `scope_hash`, an independent current `facts_hash`, the exact rate reservation, and the attempt before the network call. The result transaction records `send.provider_accepted.v1`, conclusive failure, or `AMBIGUOUS`. A crash in the gap enters exact-authority reconciliation, never automatic retry.

An internal outbox consumer starts one PostgreSQL transaction, rechecks absence of `(consumer_name,event_id)`, performs all internal business writes, inserts `outbox_deliveries`, and commits once. A crash rolls back both the business writes and delivery receipt; redelivery re-executes the same transaction. External provider effects are forbidden in that transaction and forbidden from any generic “effect once” claim. Gmail/model/search/extraction effects use their explicit intent/result/error or `AMBIGUOUS`/reconciliation contracts.

## Ordered implementation tasks

- [ ] **Encode event schemas/catalog —** Input: every ARCH-03 `.v1` name/payload. Operation: register typed payload, aggregate applicability, actor rules, redaction, and upcast policy. Output: executable catalog. Test evidence: `test_arch03_event_catalog_is_exact_and_complete`. Failure behavior: unknown/malformed event aborts transaction.
- [ ] **Migrate append-only safety tables —** Input: table contract. Operation: create constraints/indexes/immutable protections and FKs. Output: M2 event/audit/idempotency/outbox/policy/cost schema. Test evidence: migration introspection and mutation-denial tests. Failure behavior: rollback revision.
- [ ] **Implement idempotent command middleware —** Input: authenticated command, scope/key, canonical request hash. Operation: claim or replay exact result inside unit of work. Output: one command effect. Test evidence: concurrent duplicate and hash-conflict tests. Failure behavior: typed conflict; no second effect.
- [ ] **Implement outbox and internal consumer atomicity —** Input: committed outbox rows. Operation: lease a bounded batch, publish at least once, and make each internal consumer commit its business writes plus `outbox_deliveries` in one PostgreSQL transaction. Output: eventually delivered internal events with atomic consumer effects. Test evidence: crash before business write, between business write and receipt, before commit, and after commit. Failure behavior: rollback/redeliver for internal writes; bounded backoff/dead-letter incident for poison events; external effects are rejected from this path.
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

Payload schemas are allowlists and prefer references/hashes. Actor/authority, denials, approvals, controls, ambiguous results, repairs, and credential actions are audited. Correlation/causation spans HTTP, workflow, agent, policy, provider, and outbox. Metrics expose lag, retries, stuck commands, unresolved ambiguity, policy denials, budget variance, and safe error codes. Cost entries preserve provider currency and conversion evidence.

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
