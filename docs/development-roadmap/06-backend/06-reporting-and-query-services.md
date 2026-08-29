# Reporting and Query Services

**Document ID:** BACKEND-06
**Status:** Planned M7 read layer; no product data, projection, or report endpoint exists today
**Milestone:** M7, with internal gate queries used from M2
**Owner:** Solo operator
**Prerequisites:** DB-01 through DB-06, [BACKEND-01](01-domain-services.md), [BACKEND-02 report routes](02-api-contracts.md#exact-route-and-openapi-operation-manifest), and canonical ARCH-03 states/events
**Outputs:** Stable PostgreSQL projections for overview, funnel, costs, timeline, providers, approvals, and recovery with freshness/provenance
**Unlocks:** M7 dashboard diagnosis and evidence-based experiment decision
**Risk:** High
**Complexity:** L

## Outcome and timing

One operator can answer what state an experiment is in, why, what was spent, what evidence/providers contributed, which approvals or ambiguities need action, and whether funnel/decision rules have enough data. Reports are deterministic read models over authoritative product tables and immutable events. They never infer provider delivery, mutate state, hide unresolved records, or become a second source of truth.

## Current repository state

Only health responses exist. There are no product/report tables, metrics, query services, projections, timelines, costs, approvals, provider ledger, pagination, frontend analytics, or authenticated report routes. Every report below is planned after its source tables exist.

## Scope and non-goals

In scope: exact projection schemas/versions, source table/event sets, snapshot cutoff/high-watermark, stable pagination, funnel definitions, original/ILS cost, ambiguity/approval visibility, redaction, and reproducibility. Non-goals: BI warehouse, mutable materialized truth, event sourcing, model-generated summaries as facts, vanity metrics, inferred opens/delivery, cross-experiment recipient exports, live provider queries, or reports that issue commands.

## Exact planned implementation surfaces

Create `application/reporting.py`, `application/report_contracts.py`, `application/report_snapshots.py`, `persistence/queries/experiments.py`, `funnel.py`, `costs.py`, `timeline.py`, `providers.py`, `approvals.py`, `recovery.py`, and BACKEND-02 route adapters. Do not add projection tables in v1. Every multi-statement report runs `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY`; its first statement captures one `transaction_timestamp()` and source-event high-watermark inside that same MVCC snapshot. No statement may open a second connection or read after commit. Later materialization requires measured evidence and an ADR.

Every response includes literal `schema_version`, `projection_version`, UTC `as_of`, `source_event_high_watermark` (latest included `(recorded_at,event_id)` or null), `complete` boolean, sorted `warnings`, and `correlation_id`. `complete=false` is allowed only for explicitly non-authoritative optional sections and must list why; a missing/corrupt authoritative source is a typed 503. Query version changes create a new projection version and comparison fixtures.

### Exact query service and projection manifest

| Service / schema | Authoritative reads | Exact output semantics |
| --- | --- | --- |
| `ExperimentOverviewQueryService` / `report.experiment_overview.v1` | `experiments`, active `experiment_briefs`, active/latest `workflow_runs`, `campaigns`, `system_controls`, `incidents`, latest metric snapshot/decision | canonical state/version/paused/failed/retry fields; frozen caps/authority; active finite run; campaign version/state; control values/versions; blocking incident IDs; decision IDs/kind. No runtime-native state replaces application projection. |
| `ExperimentFunnelQueryService` / `report.experiment_funnel.v1` | `businesses`, `leads`, `lead_assessments`, `campaign_members`, `outreach_messages`, `send_intents`, `send_attempts`, `provider_results`, `replies`, accepted `ReplyClassification` artifacts/events | counts and exact ID-set hashes for researched leads, qualified, eligible members, intents, direct/reconciled sent, replies, positive replies, suppressed/disqualified/conflicts; denominators and zero-denominator status explicit. |
| `ExperimentCostQueryService` / `report.experiment_costs.v1` | `budget_accounts`, `budget_reservations`, `cost_entries`, experiment brief caps, workflow/agent/provider identities | reserved/released/reconciled/expired; spend grouped by provider/operation/currency; ILS reporting totals only from recorded conversion evidence; cap remaining and discrepancy IDs. Never silently sum unlike currencies. |
| `ExperimentTimelineQueryService` / `report.experiment_timeline.v1` | `domain_events`, `audit_events`, application `workflow_runs`, `policy_decisions`, send intents/attempts/results, incidents/repairs | ordered safe union with record kind, exact event/error/reason, aggregate/version, correlation/causation, authority IDs/hashes, and redacted summary. Logs/runtime history are links, not timeline truth. |
| `ProviderOperationsQueryService` / `report.provider_operations.v1` | `agent_runs`, `cost_entries`, DB-04 evidence metadata, Gmail attempts/results/observations, incidents | capability/operation/provider/config versions, calls/outcomes/errors/time/tokens/cost, evidence counts, ambiguity age, discrepancies; no prompts/content/addresses/credentials. |
| `ApprovalQueueQueryService` / `report.approval_queue.v1` | `approvals`, message/campaign/lead/mailbox safe metadata, current suppression/control/policy facts | exact approval state/scope/version/expiry/reason and `current_authority_valid`; changed facts show invalidation reasons and disable actions. It does not approve automatically. |
| `RecoveryQueryService` / `report.recovery_overview.v1` | nonterminal `workflow_runs`, `IN_PROGRESS` commands, unresolved send attempts, cursor incidents, `repair_actions` plus open incidents | `RecoveryOverviewItemV1` union with kind `WORKFLOW_RUN`, `COMMAND`, `SEND_ATTEMPT`, `CURSOR_INCIDENT`, or `REPAIR_ACTION`; stable ID, attention time, state/reason, safe authority/evidence IDs, and exact next allowed commands. Served only by BACKEND-02 `GET /api/v1/recovery/overview` / `getRecoveryOverview`; unknown remains visible and nothing auto-resolves. |

Sole query owners never write tables or invoke providers/runtime. API serialization converts exact domain values to OpenAPI models and cannot add presentation-derived status. Next.js display labels/colors/actions are exhaustive mappings over canonical enums.

### Exact funnel and decision math

All counts are distinct stable IDs at `as_of`, not event-row counts:

- `researched_leads`: lead state at/after `RESEARCHED` with accepted evidence, excluding conflict-only rows;
- `qualified_leads`: canonical `QUALIFIED` with immutable passing assessment, while separately retaining later-suppressed count;
- `eligible_members`: `campaign_members.status='ELIGIBLE'` for exact campaign version;
- `send_intents`: one DB-03 intent per message;
- `sent_messages`: message `SENT` with exactly one accepted or reconciled-sent provider result; split direct (`send.provider_accepted.v1`) and reconciled (`send.reconciled_as_sent.v1`) without double count;
- `replies`: one DB-03 reply/provider observation; no thread/message duplicates;
- `positive_replies`: accepted `ReplyClassification` primary `POSITIVE` linked through exact reply artifact/event; unaccepted/abstained classifications do not count;
- suppressions, permanent/retryable/ambiguous/reconciling/conflicts are explicit loss/attention buckets, never dropped.

Each conversion output includes numerator, denominator, value or null, and status `AVAILABLE`, `ZERO_DENOMINATOR`, or `INSUFFICIENT_EVIDENCE`. Missing data is never zero. Definition/rule/query versions and ID-set hashes allow metric snapshot reproduction. BACKEND-06 may display the deterministic DB-02 `MetricSnapshotService` result but does not recompute or record experiment decisions.

### Repeatable-read snapshot and pagination contract

Non-paginated reports execute every source query and serialization precondition in one `REPEATABLE READ READ ONLY` transaction. `as_of=transaction_timestamp()` and `source_event_high_watermark` are selected first; concurrent commits after snapshot creation cannot change any count, row, warning, or completeness result.

Paginated reports/recovery use one exported PostgreSQL snapshot, not a sequence of fresh transactions. Page one starts the same read-only repeatable-read transaction, calls `pg_export_snapshot()`, and retains that exporter connection in bounded `ReportSnapshotLeaseRegistry` for 60 seconds. The signed opaque cursor contains route, normalized filter hash, order, last key, projection version, `as_of`, high-watermark, snapshot lease UUID/hash, and expiry; it never exposes the raw PostgreSQL snapshot identifier. Each subsequent page starts `REPEATABLE READ READ ONLY`, executes `SET TRANSACTION SNAPSHOT` before any query using the server-side lease, then applies keyset `>` to the last tuple. The exporter remains open until final page/expiry/cancel; registry capacity is 4 and rejects excess with 429 `RATE_LIMITED`.

If the process/connection/snapshot lease disappears or expires, return 409 `STATE_TRANSITION_DENIED` with `REPORT_SNAPSHOT_EXPIRED`; the generated client discards its cursor and restarts page one. A PostgreSQL serialization/snapshot-import failure rolls back the whole page/report; the query service may restart from page one at most twice under a new correlation child span, never continue a cursor on a new snapshot, then returns 503 `DEPENDENCY_UNAVAILABLE`. Deployment with multiple API instances must route a cursor to its lease owner or supply an equivalent shared snapshot coordinator before enabling pagination; sticky routing cannot weaken token verification.


### Timeline ordering, pagination, freshness, and privacy

Timeline total order is `(occurred_at,recorded_at,record_kind,event_or_record_id)`; recovery overview order is `(attention_since,record_kind,record_id)`. Both are diagnostic, not cross-aggregate causality. Causation/correlation and aggregate versions establish relationships. All pages import the original exported snapshot and reuse its `as_of`/high-watermark; concurrent events appear only in a new traversal. Other lists use their documented stable keyset order under the same snapshot contract.

Redaction is schema-based. Reports expose recipient/domain/message/provider IDs only as safe internal IDs or non-reversible hashes; never ciphertext, decrypted address/body/subject, source text/snippet, OAuth/key, raw provider/error payload, hidden reasoning, or restricted capture ref. Purged evidence remains visible as hash/state. Operator authentication does not justify unnecessary PII.

### Cost, observability, caching, and example

Cost reports retain provider original integer minor amount/currency. ILS total includes only rows with complete DB-05 reporting amount/rate/source/date evidence; missing conversion yields discrepancy and incomplete ILS section, not guessed FX. Reservations are not spend until reconciled. Gmail zero-fee calls may be operationally counted without inventing monetary cost.

V1 query responses may use private in-process/HTTP cache keyed by operator, route, filters, projection version, and high-watermark for at most 15 seconds; controls, approvals, ambiguity/recovery, and freshness-critical queries bypass cache. Cache is never authoritative and purge/control events invalidate relevant entries. Metrics include query version, duration, rows, cutoff lag, cache hit, page count, incomplete reasons, and safe error.

```json
{
  "schema_version":"report.experiment_funnel.v1",
  "projection_version":"experiment-funnel.v1",
  "as_of":"2026-08-28T00:00:00Z",
  "source_event_high_watermark":{"recorded_at":"2026-08-27T23:59:59Z","event_id":"42d704c7-c01f-4aeb-adb1-e8bc2fb338ce"},
  "complete":true,
  "warnings":["PRODUCT_OUTREACH_DISABLED"],
  "correlation_id":"862f761d-a83b-4e8a-a98b-d5edbbe79074",
  "counts":{"qualified_leads":12,"send_intents":0,"sent_messages":0},
  "contact_rate":{"numerator":0,"denominator":12,"value":0,"status":"AVAILABLE"}
}
```

## Ordered implementation tasks

- [ ] **Encode projection schemas/query versions —** Input: canonical tables/states/events/metrics and manifest above. Operation: define strict response unions, cutoff/high-watermark, warnings, pagination, and redaction. Output: stable report contracts. Test evidence: schema snapshots and every-state fixtures. Failure behavior: unknown source/state blocks the affected authoritative report.
- [ ] **Implement overview/funnel/recovery queries —** Input: one repeatable-read snapshot and exact filters. Operation: compute distinct ID sets/hashes/counts/statuses and the five-kind recovery overview without writes. Output: operator diagnosis through exact BACKEND-02 routes. Test evidence: real-PostgreSQL boundary/duplicate/ambiguous/suppression/recovery fixtures. Failure behavior: visible incomplete/degraded, never inferred success.
- [ ] **Implement cost/provider queries —** Input: reservations/cost/provider ledgers and conversion evidence. Operation: group original currencies, reconcile ILS/discrepancies, expose safe performance. Output: budget/cost diagnosis. Test evidence: currency/rounding/duplicate/missing-FX/provider parity fixtures. Failure behavior: incomplete ILS total and discrepancy.
- [ ] **Implement repeatable-read/exported-snapshot pagination/API routes —** Input: frozen MVCC snapshot and event/audit/provider/recovery records. Operation: retain bounded exporter lease, import before every page query, apply stable keyset order, sign cursor, and serialize BACKEND-02 models. Output: replayable report/recovery API. Test evidence: concurrent commits cannot alter report/page, snapshot expiry/restart, serialization retry, cursor tamper, page continuity, and OpenAPI tests. Failure behavior: discard traversal and restart page one or typed dependency error.
- [ ] **Prove decision reproducibility, redaction, and UI contract —** Input: metric/report fixtures, retention/redaction states, generated client. Operation: reproduce snapshot views, scan sensitive fields, and render all states/actions. Output: M7 evidence. Test evidence: query/gate comparison, privacy scan, browser E2E/accessibility. Failure behavior: M7 blocked.

## Test strategy

- **Projection `test_report_manifest_reads_only_exact_authoritative_sources`:** no log/runtime/provider live truth.
- **Funnel `test_direct_reconciled_sent_and_reply_counts_are_distinct_and_deduplicated`:** ambiguity visible.
- **Math `test_zero_denominator_missing_and_insufficient_evidence_are_not_conflated`:** exact statuses.
- **Cost `test_original_currency_and_ils_conversion_evidence_never_silently_mix`:** integer rounding vectors.
- **Snapshot `test_multi_statement_report_is_repeatable_read_and_concurrent_commit_cannot_change_result`:** one transaction timestamp/high-watermark.
- **Pagination `test_exported_snapshot_pages_ignore_concurrent_commits_without_duplicates_or_skips`:** same MVCC snapshot/keyset.
- **Snapshot recovery `test_expired_or_lost_snapshot_discards_cursor_and_restarts_page_one`:** no mixed snapshots.
- **Recovery API `test_recovery_overview_five_kinds_match_get_recovery_overview_schema`:** route/client linkage.
- **Privacy `test_all_reports_openapi_logs_and_cache_exclude_sensitive_fields`:** allowlist scan.

## Security, privacy, compliance, idempotency, observability, and cost

Queries require the same private operator auth and row ownership. Signed cursors and projection versions prevent filter confusion. Reports are read-only/idempotent; `as_of` and high-watermark make them reproducible. Cache is private, bounded, and content-minimized. Redaction/retention follows DB-06 and holds. Query performance uses exact indexes, statement timeout, row/page caps, and query metrics; expensive analytics cannot starve command/SendGateway transactions.

## Failure, rollback, and operator recovery

Unknown enum/event, impossible provider-result multiplicity, cursor signature failure, stale schema, statement timeout, cost discrepancy, or redaction leak fails the report/section visibly and opens an incident when truth/privacy is at risk. Disable cache/report release, roll back query version, and compare source rows/events with retained fixtures. Reports never repair data; operator follows BACKEND-05 typed commands.

## Acceptance and retained evidence

- [ ] Every report has exact source tables, schema/query version, cutoff/high-watermark, stable order, and redaction.
- [ ] Funnel/cost/timeline preserve canonical event/state meanings, ambiguity, original currency, and missing-data status.
- [ ] Queries are read-only and cannot call providers/runtime or mutate/authorize anything.
- [ ] Generated API/frontend can diagnose approvals, controls, costs, failures, and recovery without SQL.

Retain projection schemas/query text/EXPLAIN plans, source/ID-set hash fixtures, funnel/math/cost golden results, timeline pagination/concurrency traces, redaction/cache scans, OpenAPI/client/browser evidence, and report version rollback record.

## Dependencies and next deliverable

BACKEND-06 consumes complete M2-M6 records and BACKEND-02 routes. It unlocks the M7 dashboard and evidence-based decision view; reports remain advisory/read-only and no displayed metric grants send, spend, scale, or repair authority.
