# Reporting and Query Services

**Document ID:** BACKEND-06
**Status:** Planned M7 read layer; no product data, projection, or report endpoint exists today
**Milestone:** M7 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `BACKEND-06-T01 -> BACKEND-06-T02 -> BACKEND-06-T03 -> BACKEND-06-T04 -> BACKEND-06-T05`; cross-document task Inputs `BACKEND-06-T01 <- BACKEND-03-T01,SEC-04-T02,DB-05-T02,ARCH-03-T01,OBS-05-T01; BACKEND-06-T03 <- OBS-03-T03; BACKEND-06-T04 <- BACKEND-02-T04; BACKEND-06-T05 <- BACKEND-02-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): DB-01 through DB-06, [BACKEND-01](01-domain-services.md), [BACKEND-02 report routes](02-api-contracts.md#exact-route-and-openapi-operation-manifest), and canonical ARCH-03 states/events
**Outputs:** Stable PostgreSQL projections for overview, funnel, costs, timeline, providers, exceptions and action authority, and recovery with freshness/provenance
**Unlocks:** M7 dashboard diagnosis and evidence-based experiment decision
**Risk:** High
**Complexity:** L

## Outcome and timing

M9 reports expose stage and cumulative truth separately: admitted, attempted, reconciled delivered, bounced, complained, opted out, replied, positively replied, qualified conversations, qualified commitments, spend, operator time, and contribution margin. Every snapshot binds stage ordinal, increment, cumulative maximum, membership hash, observation cutoff, query version, and late-event policy. Reports never add stage denominators together twice or infer `CONTINUE` from incomplete evidence.

One operator can answer what state an experiment is in, why, what was spent, what evidence/providers contributed, which exceptions and action authority or ambiguities need action, and whether funnel/decision rules have enough data. Reports are deterministic read models over authoritative product tables and immutable events. They never infer provider delivery, mutate state, hide unresolved records, or become a second source of truth.

## Current repository state

Only health responses exist. There are no product/report tables, metrics, query services, projections, timelines, costs, exceptions and action authority, provider ledger, pagination, frontend analytics, or authenticated report routes. Every report below is planned after its source tables exist.

## Scope and non-goals

In scope: exact projection schemas/versions, source table/event sets, snapshot cutoff/high-watermark, stable pagination, funnel definitions, original/ILS cost, ambiguity/action authority visibility, redaction, and reproducibility. Non-goals: BI warehouse, mutable materialized truth, event sourcing, model-generated summaries as facts, vanity metrics, inferred opens/delivery, cross-experiment recipient exports, live provider queries, or reports that issue commands.

## Exact planned implementation surfaces

Create `application/reporting.py`, `application/report_contracts.py`, `application/report_snapshots.py`, `persistence/queries/experiments.py`, `funnel.py`, `costs.py`, `timeline.py`, `providers.py`, `exceptions and action authority.py`, `recovery.py`, and BACKEND-02 route adapters. Do not add projection tables in v1. Query helpers for offers/leads/conversations/bookings/checkpoints/strategies/exceptions read the corresponding canonical source tables. Every multi-statement report runs `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY`; its first statement captures one `transaction_timestamp()` and source-event high-watermark inside that same MVCC snapshot. No statement may open a second connection or read after commit. Later materialization requires measured evidence and an ADR.

Every response includes literal `schema_version`, `projection_version`, UTC `as_of`, `source_event_high_watermark` (latest included `(recorded_at,event_id)` or null), `complete` boolean, sorted `warnings`, and `correlation_id`. `complete=false` is allowed only for explicitly non-authoritative optional sections and must list why; a missing/corrupt authoritative source is a typed 503. Query version changes create a new projection version and comparison fixtures.

### Exact query service and projection manifest

| Service / schema | Authoritative reads | Exact output semantics |
| --- | --- | --- |
| `ExperimentOverviewQueryService` / `report.experiment_overview.v1` | `experiments`, active `experiment_briefs`, active/latest `workflow_runs`, `campaigns`, `system_controls`, `incidents`, latest metric snapshot/decision | canonical state/version/paused/failed/retry fields; frozen caps/authority; active finite run; campaign version/state; control values/versions; blocking incident IDs; decision IDs/kind. No runtime-native state replaces application projection. |
| `ExperimentFunnelQueryService` / `report.experiment_funnel.v1` | `businesses`, `leads`, `lead_assessments`, `campaign_members`, `outreach_messages`, `send_intents`, `send_attempts`, `provider_results`, `replies`, accepted `ReplyEvaluation` artifacts/events | counts and exact ID-set hashes for researched leads, qualified, eligible members, intents, direct/reconciled sent, replies, positive replies, suppressed/disqualified/conflicts; denominators and zero-denominator status explicit. |
| `ExperimentCostQueryService` / `report.experiment_costs.v1` | `budget_accounts`, `budget_reservations`, `cost_entries`, experiment brief caps, workflow/agent/provider identities | reserved/released/reconciled/expired; spend grouped by provider/operation/currency; ILS reporting totals only from recorded conversion evidence; cap remaining and discrepancy IDs. Never silently sum unlike currencies. |
| `ExperimentTimelineQueryService` / `report.experiment_timeline.v1` | `domain_events`, `audit_events`, application `workflow_runs`, `policy_decisions`, send intents/attempts/results, incidents/repairs | ordered safe union with record kind, exact event/error/reason, aggregate/version, correlation/causation, authority IDs/hashes, and redacted summary. Final-SEND entries project the dedicated BACKEND-03 compliance/signal denial code and safe evidence artifact ID/version/hash tuples, not a generic jurisdiction/authority/suppression label. Incident/repair entries project exact `incident.catalog.v1` trigger/runbook/alert/resolution/repair values. Logs/runtime history are links, not timeline truth. |
| `ProviderOperationsQueryService` / `report.provider_operations.v1` | `agent_runs`, `cost_entries`, DB-04 evidence metadata, Gmail attempts/results/observations, incidents | capability/operation/provider/config versions, calls/outcomes/errors/time/tokens/cost, evidence counts, ambiguity age, discrepancies; no prompts/content/addresses/credentials. |
| `RecoveryQueryService` / `report.recovery_overview.v1` | nonterminal `workflow_runs`, `IN_PROGRESS` commands, unresolved send attempts, cursor incidents, `repair_actions` plus open incidents | `RecoveryOverviewItemV1` union with kind `WORKFLOW_RUN`, `COMMAND`, `SEND_ATTEMPT`, `CURSOR_INCIDENT`, `REPAIR_ACTION`, `BOOKING_ACTION`, `CHECKPOINT`, or `STRATEGY_ACTIVATION`; stable ID, attention time, state/reason, safe authority/evidence IDs, exact `incident.catalog.v1` catalog/trigger/runbook/alert/resolution/repair values when applicable, and exact next allowed commands. Unknown/mismatched catalog values remain visible as blocked `INCIDENT_CATALOG_MISMATCH`; nothing auto-resolves and no free-text routing occurs. Served only by BACKEND-02 `GET /api/v1/recovery/overview` / `getRecoveryOverview`. |

Sole query owners never write tables or invoke providers/runtime. API serialization converts exact domain values to OpenAPI models and cannot add presentation-derived status. Next.js display labels/colors/actions are exhaustive mappings over canonical enums.


### Autonomous-sales query owners

These read-only projections add no duplicate source tables. They use the same repeatable-read/exported-snapshot protocol and exact BACKEND-02 DTO allowlists.

| Service | Exact authoritative sources | Query result / stable order |
| --- | --- | --- |
| OfferQueryService | ideas, accepted offer_packages/offer_economics/offer_variants/offer_discount_bands, artifact/evidence receipts | idea origin, accepted package and deterministic economics/envelope/version/hash/evidence; order (offer_version,offer_id); never compute independent commercial truth |
| LeadQueryService | lead_sources,lead_discovery_candidates,businesses,people,contact_identities,leads,lead_assessments,accepted dossiers/evidence | approved-source/query/provenance, dedupe disposition, sanitized FACT/ESTIMATE/UNKNOWN, explicit PRELIMINARY/FINAL result and criteria/offer; order (created_at,candidate_id) or (phase,created_at,assessment_id) |
| CampaignQueryService | campaign_cohorts,campaign_members,checkpoints,strategy_activations | cohort/cumulative caps, exact frozen membership/versions/generations and checkpoint ownership; order (stage_ordinal,cohort_id); read-only lead inspection never permits client-chosen admission |
| ActionAuthorizationQueryService | action_authorizations/consumptions,policy_decisions,action_controls,send_intents/attempts,offer/strategy/activation,conversation stops/suppression | automatic action state, expiry/freshness and dedicated blocked reasons; current projection is explanation only; order (created_at,authorization_id); cache bypass |
| ConversationQueryService | conversations,conversation_messages,replies,accepted ReplyEvaluation,negotiation_proposals/decisions,budget_assertions,action_attributions | full ordered redacted thread, current objective/terminal/negative-sentiment states, STATED/INFERRED/UNKNOWN distinction and authoritative negotiated amounts; order (ordinal,conversation_message_id); never promote summaries to body evidence |
| BookingQueryService | booking_intents/slot_sets/slots/confirmations/actions/attempts/provider_results,calendar_accounts/observations,action_attributions | timezone-labelled confirmed slot and buying-intent/call-agreement/purchase separation, provider action/result/ambiguity, notification state and linked dashboard context; order (created_at,booking_intent_id); no raw attendees/descriptions |
| CheckpointQueryService | checkpoints,checkpoint_evidence_members,experiment_decisions,metric_snapshots/observations,cost_entries | exact frozen cohort/cutoff/denominators, evidence mode/completeness, five-way result and next-stage eligibility; order (stage_ordinal,checkpoint_id); late source data remains separately attributed |
| StrategyQueryService | global_learning_runs,agent_learning_results,global_strategy_versions,strategy_agent_versions,strategy_activations,strategy_rollbacks,protected eval summaries,action_attributions | every applicable agent's four-way result/evidence/confidence, global versions, campaign-specific activation and rollback history; order (strategy_version,strategy_version_id) or (effective_at,activation_id); no protected holdout payload/raw PII |
| ExceptionQueryService | exception_cases,incidents,action_authorizations,blocked policy decisions,repair_actions | explicit unresolved cases/reasons/safe evidence/owner/correction commands; order (opened_at,exception_id); no routine approval queue |

### Cohort and strategy metric definitions

The expanded funnel computes distinct candidates -> preliminary-qualified -> deeply researched -> finally qualified -> contacted unique recipients -> replies -> positive replies -> qualified commitments -> confirmed bookings -> attended calls. Additional messages/negotiation rounds do not increase unique-recipient stage/cumulative denominators. Purchase commitment requires exact evidenced acceptance of purchase terms; agreeing to a call alone counts only as call agreement/booking. A booking needs positive provider confirmation, show rate needs verified attendance evidence, and absent evidence stays UNAVAILABLE.

Metrics cover discovery yield/duplicates, research factual coverage, qualification precision, personalization claim coverage, send/delivery/bounce/complaint/reply/positive rates, objection categories/resolution, negotiation discount/margin/scope outcomes, bookings/show rate, cost per qualified lead/commitment/booking, and pre/post activation/transfer/promotion/rollback performance. Each value pins definition/query/evidence transform, numerator/denominator, observation cutoff, cohort and exact action strategy/activation. A report never infers commercial success, guaranteed causality or strategy promotion from correlation.

Global-learning views read only approved minimized checkpoint transforms. No query can hand raw contact identities, full conversation bodies, sensitive budget inference or private calendar details to a global model. Operational full-thread detail is a separate authenticated redacted no-store response and is not copied into metrics/report cache. Sensitive raw inspection requires the separate exception step-up purpose.

### Exact funnel and decision math

All counts are distinct stable IDs at `as_of`, not event-row counts:

- `researched_leads`: lead state at/after `RESEARCHED` with accepted evidence, excluding conflict-only rows;
- `qualified_leads`: canonical `QUALIFIED` with immutable passing assessment, while separately retaining later-suppressed count;
- `eligible_members`: `campaign_members.status='ELIGIBLE'` for exact campaign version;
- `send_intents`: one DB-03 intent per message;
- `sent_messages`: message `SENT` with exactly one accepted or reconciled-sent provider result; split direct (`send.provider_accepted.v1`) and reconciled (`send.reconciled_as_sent.v1`) without double count;
- `replies`: one DB-03 reply/provider observation; no thread/message duplicates;
- `positive_replies`: accepted `ReplyEvaluation` primary `POSITIVE` linked through exact reply artifact/event; unaccepted/abstained classifications do not count;
- suppressions, permanent/retryable/ambiguous/reconciling/conflicts are explicit loss/attention buckets, never dropped.

Each conversion output includes numerator, denominator, value or null, and status `AVAILABLE`, `ZERO_DENOMINATOR`, or `INSUFFICIENT_EVIDENCE`. Missing data is never zero. Definition/rule/query versions and ID-set hashes allow metric snapshot reproduction. BACKEND-06 may display the deterministic DB-02 `MetricSnapshotService` result but does not recompute or record experiment decisions.

### Repeatable-read snapshot and pagination contract

Non-paginated reports execute every source query and serialization precondition in one `REPEATABLE READ READ ONLY` transaction. `as_of=transaction_timestamp()` and `source_event_high_watermark` are selected first; concurrent commits after snapshot creation cannot change any count, row, warning, or completeness result.

Paginated reports/recovery use one exported PostgreSQL snapshot, not a sequence of fresh transactions. Page one starts the same read-only repeatable-read transaction, calls `pg_export_snapshot()`, and retains that exporter connection in bounded `ReportSnapshotLeaseRegistry` for 60 seconds. The signed opaque cursor contains route, normalized filter hash, order, last key, projection version, `as_of`, high-watermark, snapshot lease UUID/hash, and expiry; it never exposes the raw PostgreSQL snapshot identifier. Each subsequent page starts `REPEATABLE READ READ ONLY`, executes `SET TRANSACTION SNAPSHOT` before any query using the server-side lease, then applies keyset `>` to the last tuple. The exporter remains open until final page/expiry/cancel; registry capacity is 4 and rejects excess with 429 `RATE_LIMITED`.

If the process/connection/snapshot lease disappears or expires, return 409 `STATE_TRANSITION_DENIED` with `REPORT_SNAPSHOT_EXPIRED`; the generated client discards its cursor and restarts page one. A PostgreSQL serialization/snapshot-import failure rolls back the whole page/report; the query service may restart from page one at most twice under a new correlation child span, never continue a cursor on a new snapshot, then returns 503 `DEPENDENCY_UNAVAILABLE`. Deployment with multiple API instances must route a cursor to its lease owner or supply an equivalent shared snapshot coordinator before enabling pagination; sticky routing cannot weaken token verification.


### Timeline ordering, pagination, freshness, and privacy

Timeline total order is `(occurred_at,recorded_at,record_kind,event_or_record_id)`; recovery overview order is `(attention_since,record_kind,record_id)`. Both are diagnostic, not cross-aggregate causality. Causation/correlation and aggregate versions establish relationships. All pages import the original exported snapshot and reuse its `as_of`/high-watermark; concurrent events appear only in a new traversal. Other lists use their documented stable keyset order under the same snapshot contract.

Redaction is schema-based. Reports expose only necessary safe internal record IDs and non-recipient content/provider hashes; deterministic recipient/address hashes are pseudonymous and offline enumerable and are never report fields. Aggregate reports never expose ciphertext, decrypted address/body/subject, source text/snippet, OAuth/key, raw provider/error payload, hidden reasoning, or restricted capture ref. Purged evidence remains visible only through allowed state/non-recipient hash/reference. Operator authentication does not justify unnecessary PII.

### Cost, observability, caching, and example

Cost reports retain provider original integer minor amount/currency. ILS total includes only rows with complete DB-05 reporting amount/rate/source/date evidence; missing conversion yields discrepancy and incomplete ILS section, not guessed FX. Reservations are not spend until reconciled. Gmail zero-fee calls may be operationally counted without inventing monetary cost.

V1 query responses may use private in-process/HTTP cache keyed by operator, route, filters, projection version, and high-watermark for at most 15 seconds; controls, exceptions and action authority, ambiguity/recovery, and freshness-critical queries bypass cache. Cache is never authoritative and purge/control events invalidate relevant entries. Metrics include query version, duration, rows, cutoff lag, cache hit, page count, incomplete reasons, and safe error.

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

<!-- roadmap-task id=BACKEND-06-T01 milestone=M7 depends_on=BACKEND-03-T01,SEC-04-T02,DB-05-T02,ARCH-03-T01,OBS-05-T01 mode=serial locks=openapi-contract,backend-domain -->
- [ ] **Encode projection schemas/query versions —** Input: canonical tables/states/events/metrics, BACKEND-03 dedicated final-SEND reasons, exact compliance evidence tuples, and `incident.catalog.v1`. Operation: define strict response unions, cutoff/high-watermark, warnings, pagination, redaction, and exhaustive incident maps. Output: stable report contracts. Test evidence: schema snapshots, every final-SEND denial fixture, and every incident/catalog fixture. Failure behavior: unknown source/state/catalog code blocks the affected authoritative report.
<!-- roadmap-task id=BACKEND-06-T02 milestone=M7 depends_on=BACKEND-06-T01 mode=parallel locks=backend-domain -->
- [ ] **Implement overview/funnel/recovery queries —** Input: one repeatable-read snapshot and exact filters. Operation: implement all autonomous-sales query owners above, compute distinct cohort/strategy ID sets/hashes/counts/statuses and complete typed recovery without writes. Output: operator diagnosis through exact BACKEND-02 routes. Test evidence: real-PostgreSQL boundary/duplicate/ambiguous/suppression/recovery fixtures. Failure behavior: visible incomplete/degraded, never inferred success.
<!-- roadmap-task id=BACKEND-06-T03 milestone=M7 depends_on=BACKEND-06-T02,OBS-03-T03 mode=parallel locks=backend-domain -->
- [ ] **Implement cost/provider queries —** Input: reservations/cost/provider ledgers and conversion evidence. Operation: group original currencies, reconcile ILS/discrepancies, expose safe performance. Output: budget/cost diagnosis. Test evidence: currency/rounding/duplicate/missing-FX/provider parity fixtures. Failure behavior: incomplete ILS total and discrepancy.
<!-- roadmap-task id=BACKEND-06-T04 milestone=M7 depends_on=BACKEND-06-T03,BACKEND-02-T04 mode=serial locks=openapi-contract,backend-domain -->
- [ ] **Implement repeatable-read/exported-snapshot pagination/API routes —** Input: the BACKEND-02 authenticated M7 report/recovery OpenAPI contract plus a frozen MVCC snapshot and event/audit/provider/recovery records. Operation: retain bounded exporter lease, import before every page query, apply stable keyset order, sign cursor, and serialize BACKEND-02 models. Output: replayable report/recovery API. Test evidence: concurrent commits cannot alter report/page, snapshot expiry/restart, serialization retry, cursor tamper, page continuity, and OpenAPI tests. Failure behavior: discard traversal and restart page one or typed dependency error.
<!-- roadmap-task id=BACKEND-06-T05 milestone=M7 depends_on=BACKEND-06-T04,BACKEND-02-T05 mode=serial locks=milestone-gate,backend-domain -->
- [ ] **Prove decision reproducibility, redaction, and UI contract —** Input: metric/report fixtures, retention/redaction states, generated client; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: reproduce snapshot views, scan sensitive fields, and render all states/actions; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: M7 evidence. Test evidence: query/gate comparison, privacy scan, browser E2E/accessibility. Failure behavior: M7 blocked.

## Test strategy

- **Projection `test_report_manifest_reads_only_exact_authoritative_sources`:** no log/runtime/provider live truth.
- **Funnel `test_direct_reconciled_sent_and_reply_counts_are_distinct_and_deduplicated`:** ambiguity visible.
- **Math `test_zero_denominator_missing_and_insufficient_evidence_are_not_conflated`:** exact statuses.
- **Cost `test_original_currency_and_ils_conversion_evidence_never_silently_mix`:** integer rounding vectors.
- **Snapshot `test_multi_statement_report_is_repeatable_read_and_concurrent_commit_cannot_change_result`:** one transaction timestamp/high-watermark.
- **Pagination `test_exported_snapshot_pages_ignore_concurrent_commits_without_duplicates_or_skips`:** same MVCC snapshot/keyset.
- **Snapshot recovery `test_expired_or_lost_snapshot_discards_cursor_and_restarts_page_one`:** no mixed snapshots.
- **Recovery API `test_recovery_overview_all_registered_kinds_match_get_recovery_overview_schema`:** route/client linkage.
- **Compliance `test_reports_project_every_dedicated_final_send_denial_and_safe_evidence_tuple_without_recipient_hash_or_text`:** no generic reason substitution.
- **Incident catalog `test_reports_reject_unknown_or_mismatched_incident_catalog_trigger_runbook_alert_resolution_and_repair_kind`:** no free-text routing.
- **Privacy `test_all_reports_openapi_logs_and_cache_exclude_sensitive_fields`:** allowlist scan.

## Security, privacy, compliance, idempotency, observability, and cost

Queries require the same private operator auth and row ownership. Signed cursors and projection versions prevent filter confusion. Reports are read-only/idempotent; `as_of` and high-watermark make them reproducible. Cache is private, bounded, and content-minimized. Redaction/retention follows DB-06 and holds. Query performance uses exact indexes, statement timeout, row/page caps, and query metrics; expensive analytics cannot starve command/SendGateway transactions.

## Failure, rollback, and operator recovery

Unknown enum/event, impossible provider-result multiplicity, cursor signature failure, stale schema, statement timeout, cost discrepancy, or redaction leak fails the report/section visibly and opens an incident when truth/privacy is at risk. Disable cache/report release, roll back query version, and compare source rows/events with retained fixtures. Reports never repair data; operator follows BACKEND-05 typed commands.

## Acceptance and retained evidence

- [ ] Every report has exact source tables, schema/query version, cutoff/high-watermark, stable order, and redaction.
- [ ] Funnel/cost/timeline preserve canonical event/state meanings, ambiguity, original currency, and missing-data status.
- [ ] Queries are read-only and cannot call providers/runtime or mutate/authorize anything.
- [ ] Generated API/frontend can diagnose exceptions and action authority, controls, costs, failures, and recovery without SQL.

Retain projection schemas/query text/EXPLAIN plans, source/ID-set hash fixtures, funnel/math/cost golden results, timeline pagination/concurrency traces, redaction/cache scans, OpenAPI/client/browser evidence, and report version rollback record.

## Dependencies and next deliverable

BACKEND-06 consumes complete M2-M6 records and BACKEND-02 routes. It unlocks the M7 dashboard and evidence-based decision view; reports remain advisory/read-only and no displayed metric grants send, spend, scale, or repair authority.
