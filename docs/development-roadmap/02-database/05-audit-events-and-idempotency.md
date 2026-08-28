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

| Table | Required columns/keys | Required constraints/indexes | Write/delivery rule |
| --- | --- | --- | --- |
| `domain_events` | ARCH-03 envelope fields: `event_id uuid PK`, `event_type`, `schema_version`, aggregate type/id/version, occurred/recorded times, actor type/id, correlation/causation UUIDs, idempotency key, `payload jsonb`, `metadata jsonb`, `supersedes_event_id FK self null` | unique `(aggregate_type,aggregate_id,aggregate_version,event_type)`; catalog/type/version checks; index aggregate/version, correlation, event_type/time; immutable | same transaction as aggregate change |
| `audit_events` | `audit_event_id uuid PK`, `event_type`, observed aggregate refs/version null, actor type/id, `outcome`, reason codes, correlation/causation, idempotency key, safe payload/metadata, timestamps, `supersedes_audit_event_id FK self null` | outcome `ALLOWED/DENIED/FAILED`; event catalog/audit namespace check; indexes actor/time, aggregate/time, correlation; immutable | records accepted and denied security/operational actions |
| `command_idempotency` | `command_scope`, `idempotency_key`, `command_type`, `request_hash`, actor, aggregate refs, `status`, `result_json`, `error_code`, `first_seen_at`, `completed_at`, composite PK | same key + different request hash is conflict; status `IN_PROGRESS/SUCCEEDED/FAILED`; partial index stale in-progress; result size bound | inserted/finished in command transaction; replay returns exact stored result |
| `outbox_messages` | `outbox_message_id uuid PK`, `event_id uuid FK domain_events`, `topic`, `payload_version`, `payload jsonb`, `available_at`, `published_at null`, `attempt_count`, `last_error_code null`, timestamps | unique `(event_id,topic)`; bounded payload; index unpublished `(available_at)`; immutable payload | committed with domain event; dispatcher is at least once; audit-only records are not published without a corresponding canonical domain/control event |
| `outbox_deliveries` | `consumer_name`, `event_id`, `handler_version`, `state`, `attempt_count`, `processed_at`, `result_hash`, composite PK | state `STARTED/SUCCEEDED/FAILED`; one successful outcome per consumer/event; stale-start index | consumer inserts before effect and replays stored result |
| `policy_decisions` | `policy_decision_id uuid PK`, `scope`, aggregate refs, `policy_version`, `allowed bool`, `reason_codes text[]`, `facts_hash`, `facts_ref`, `scope_hash`, `correlation_id uuid`, `idempotency_key text`, `evaluated_at` | unique `(scope,idempotency_key)`; index `(policy_version,scope_hash,facts_hash)` for reproducibility without collapsing distinct evaluations; immutable | policy engine; emits `policy.evaluated.v1` |
| `cost_entries` | `cost_entry_id uuid PK`, provider, operation, experiment/workflow/agent/send refs null, usage JSON, `amount_minor`, `currency`, `reporting_amount_minor_ils null`, `fx_rate_ref null`, `provider_invoice_ref null`, `occurred_at`, `recorded_at`, `idempotency_key` | unique `(provider,idempotency_key)`; nonnegative amounts; ILS conversion fields both present/absent; indexes experiment/provider/time | provider result reconciliation; links DB-01 reservation |
| `repair_actions` | `repair_action_id uuid PK`, incident FK, command type, affected refs, before/after hashes, reason code, operator FK, evidence ref, idempotency key, timestamps | unique `(operator_id,idempotency_key)`; immutable; no raw SQL text | audited recovery service only |

`record_kind` from ARCH-03 is represented by table membership (`DOMAIN` or `AUDIT`) and exposed as a union projection. Every event name retains its `.v1` suffix. Incompatible payloads add a new event name/version and reader/upcaster; old rows are never rewritten.

### Command and side-effect atomicity

For aggregate commands: begin; claim `(command_scope,idempotency_key)`; compare request hash; load expected version; apply pure transition; update aggregate; insert specific event plus `experiment.state_changed.v1` where required; insert audit; insert outbox; store result; commit. For provider work: the first transaction records policy/budget/intent/attempt; the network call occurs without a long transaction; the second records result or `AMBIGUOUS`. A crash in the gap enters reconciliation, never automatic retry.

## Ordered implementation tasks

- [ ] **Encode event schemas/catalog —** Input: every ARCH-03 `.v1` name/payload. Operation: register typed payload, aggregate applicability, actor rules, redaction, and upcast policy. Output: executable catalog. Test evidence: `test_arch03_event_catalog_is_exact_and_complete`. Failure behavior: unknown/malformed event aborts transaction.
- [ ] **Migrate append-only safety tables —** Input: table contract. Operation: create constraints/indexes/immutable protections and FKs. Output: M2 event/audit/idempotency/outbox/policy/cost schema. Test evidence: migration introspection and mutation-denial tests. Failure behavior: rollback revision.
- [ ] **Implement idempotent command middleware —** Input: authenticated command, scope/key, canonical request hash. Operation: claim or replay exact result inside unit of work. Output: one command effect. Test evidence: concurrent duplicate and hash-conflict tests. Failure behavior: typed conflict; no second effect.
- [ ] **Implement outbox and consumer dedupe —** Input: committed outbox rows. Operation: lease bounded batch, publish at least once, and require consumer delivery record. Output: eventually delivered observable events. Test evidence: crash before/after publish and handler commit. Failure behavior: bounded backoff/dead-letter incident; aggregate remains committed.
- [ ] **Implement policy/cost reconciliation —** Input: frozen facts/provider usage. Operation: persist decision before authority and reconcile reservation to cost afterward. Output: explainable gate and cost ledger. Test evidence: overspend, duplicate invoice, currency, and missing-result tests. Failure behavior: deny/disable paid call and open discrepancy.

## Test strategy

- **Contract `test_arch03_event_names_and_payload_ids_are_exact`:** no alias or missing suffix.
- **Integration `test_command_bundle_rolls_back_at_every_write`:** aggregate/event/audit/idempotency/outbox are indivisible.
- **Concurrency `test_same_command_key_different_hash_conflicts`:** no confused replay.
- **Recovery `test_outbox_crash_is_at_least_once_but_consumer_effect_once`:** delivery dedupe works.
- **Security `test_event_payload_allowlist_excludes_secrets_pii_and_message_body`:** fixture scan.
- **Cost `test_reservation_reconciles_original_and_ils_reporting_currency`:** no silent mixing.

## Security, privacy, compliance, idempotency, observability, and cost

Payload schemas are allowlists and prefer references/hashes. Actor/authority, denials, approvals, controls, ambiguous results, repairs, and credential actions are audited. Correlation/causation spans HTTP, workflow, agent, policy, provider, and outbox. Metrics expose lag, retries, stuck commands, unresolved ambiguity, policy denials, budget variance, and safe error codes. Cost entries preserve provider currency and conversion evidence.

## Failure, rollback, and operator recovery

Unknown schema, version gap, idempotency hash mismatch, impossible actor, or partial write aborts the command. Stuck `IN_PROGRESS` commands are inspected against aggregate/events before an audited recovery claim. Poison outbox messages are quarantined with incident evidence; they do not roll back committed business state. Corrections append superseding events/audits. Repair commands record before/after hashes and never execute user-supplied SQL.

## Acceptance and retained evidence

- [ ] Every canonical event maps to a typed schema and exact payload identifiers.
- [ ] Every mutation/denial has actor, authority, correlation, causation, idempotency, and audit evidence.
- [ ] Command replay and outbox/consumer retry cannot duplicate business or provider effects.
- [ ] Logs/runtime history are explicitly non-authoritative.
- [ ] Cost and policy decisions are reproducible and linked to side effects.

Retain event registry snapshots, constraint output, rollback injection traces, concurrency/replay results, outbox crash matrix, payload scans, policy fixtures, and budget/cost reconciliations.

## Dependencies and next deliverable

DB-05 depends on DB-01 and ARCH-03, and supplies FKs/transaction rules to DB-02 through DB-04. It unlocks [DB-06](06-migrations-seeding-and-retention.md) and all product workflows beginning with [WF-02](../03-workflows/02-experiment-lifecycle.md).
