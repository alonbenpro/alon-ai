# Cost, Funnel, and Decision Analytics

**Document ID:** FRONTEND-08
**Status:** Planned M7 read/decision surface; no product reports, metrics, costs, or decision UI exist today
**Milestone:** M7 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `FRONTEND-08-T01 -> FRONTEND-08-T02 -> FRONTEND-08-T03 -> FRONTEND-08-T04`; cross-document task Inputs `FRONTEND-08-T01 <- BACKEND-06-T04,BACKEND-02-T05; FRONTEND-08-T03 <- BACKEND-06-T03; FRONTEND-08-T04 <- BACKEND-06-T02,BACKEND-02-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [PRODUCT-02](../00-product-strategy/02-success-metrics.md), [DB-02 metrics](../02-database/02-experiment-and-offer-schema.md), [DB-05 cost ledger](../02-database/05-audit-events-and-idempotency.md), [BACKEND-06](../06-backend/06-reporting-and-query-services.md), and [BACKEND-02 report routes](../06-backend/02-api-contracts.md#exact-route-and-openapi-operation-manifest)
**Outputs:** Reproducible overview/funnel/cost/timeline/provider analytics, explicit denominators/freshness/currency evidence, and immutable decision confirmation
**Unlocks:** Evidence-based `SCALE`, `REVISE`, `KILL`, or `INCONCLUSIVE` recording; never automatic scale/spend
**Risk:** High
**Complexity:** XL

## Outcome and timing

At `/experiments/[experimentId]`, the report panels can answer what happened, which exact records counted, what was spent, what remains reserved/discrepant, whether data is complete/fresh, and which immutable metric snapshot/evidence/rule supports an operator decision. Global provider operations render inside `/recovery`. Every number and decision input comes from a server projection; the browser formats but does not calculate authoritative funnel, conversion, cost, ILS, policy, or decision results.

## Current repository state

There are no product metric/cost/provider/event records, query services, report routes, exported snapshots, or charts. The current frontend only calls readiness. BACKEND-06 and all six report operations are planned.

## Scope and non-goals

In scope: experiment overview/funnel/cost/timeline panels, global provider operations link, query provenance, warnings/completeness, exact counts/ID-set hashes/conversions/denominators, original currency and recorded ILS evidence, discrepancy/ambiguity, accessible charts with data tables, and immutable decision command. Non-goals: client aggregation, inferred opens/delivery, guessed FX, vanity charts, hidden zero substitution, BI warehouse, cross-experiment recipient export, materialized frontend truth, or auto-decision.

## Exact planned implementation surfaces

Create report Client Components inside `src/app/(operator)/experiments/[experimentId]/page.tsx` and `src/app/(operator)/recovery/page.tsx`: `src/features/reports/components/{report-provenance,overview-panel,funnel-panel,funnel-chart,funnel-data-table,cost-panel,cost-table,cost-chart,timeline-panel,timeline-table,provider-operations,metric-value,decision-evidence,decision-dialog}.tsx`, `src/features/reports/hooks/{use-experiment-reports,use-paginated-report}.ts`, `src/features/reports/formatters.ts`, and matching unit/browser tests. Data visualizations are progressive enhancement over semantic tables.

### Shared report and freshness contract

Every report renders exact `schema_version`, `projection_version`, UTC `as_of`, `source_event_high_watermark` (`recorded_at,event_id` or null), `complete`, sorted `warnings`, and `correlation_id`. `stale=true` may appear inside 200 only with a complete documented cutoff. `complete=false` is limited to explicitly optional sections and lists why. Missing/corrupt authoritative source is 503 and no chart renders misleading partial truth.

Paginated timeline/provider/approval/recovery pages retain one exported PostgreSQL snapshot. The client treats cursor as opaque, never logs/persists/edits it, and preserves `as_of`/high-watermark across pages. `REPORT_SNAPSHOT_EXPIRED` discards all accumulated pages and restarts page one with an announcement. It never appends a new snapshot.

### Exact report operations and query behavior

| Panel | URL / `operationId` / key | Exact output use and refetch |
| --- | --- | --- |
| overview | `GET /api/v1/reports/experiments/{experiment_id}/overview`, `getExperimentOverviewReport`; `['report','experiment',id,'overview']` | canonical experiment/run/campaign/controls/incidents/decision/caps/authority only; 15 seconds active, 60 terminal/on-focus |
| funnel | `GET /api/v1/reports/experiments/{experiment_id}/funnel`, `getExperimentFunnelReport`; `['report','experiment',id,'funnel']` | server counts, ID-set hashes, conversions, losses/attention; 30 seconds active, 60 terminal/on-focus |
| costs | `GET /api/v1/reports/experiments/{experiment_id}/costs`, `getExperimentCostReport`; `['report','experiment',id,'costs']` | reserved/released/reconciled/expired; provider/operation/original currency; recorded ILS totals/cap remaining/discrepancy IDs; 30/60 seconds |
| timeline | `GET /api/v1/reports/experiments/{experiment_id}/timeline`, `getExperimentTimelineReport`; `['report','experiment',id,'timeline',{cursor,limit}]` | safe total order `(occurred_at,recorded_at,record_kind,event_or_record_id)`; manual/infinite paging under one snapshot, no automatic causality inference |
| providers | `GET /api/v1/reports/providers`, `getProviderOperationsReport`; `['report','providers',{cursor,limit}]` | capability/operation/provider/config, outcomes/errors/time/tokens/cost/evidence/ambiguity/discrepancy; `/recovery`, manual paging/on-focus |
| approvals | `GET /api/v1/reports/approvals`, `getApprovalQueueReport`; `['report','approvals',{cursor,limit}]` | consumed by FRONTEND-06; not recomputed here |

All are authenticated GET queries with no mutation, idempotency key, `If-Match`, or optimistic behavior. Backend cache may be at most 15 seconds except freshness-critical surfaces; the UI always displays returned `as_of`. Report panel errors are isolated by `QueryErrorResetBoundary` so one optional section cannot erase other valid snapshots; shared decision actions require all authoritative inputs complete/current.

### Exact funnel, cost, and metric presentation

Render server counts for researched leads, qualified, eligible members, send intents, direct sent, reconciled sent, replies, positive replies, suppressed, disqualified, conflicts, permanent/retryable/ambiguous/reconciling. Never count event rows or add direct + reconciled when the response already returns deduplicated `sent_messages`.

Every conversion displays `numerator`, `denominator`, returned `value` or null, and exact status `AVAILABLE`, `ZERO_DENOMINATOR`, or `INSUFFICIENT_EVIDENCE`, plus definition/rule/query versions and ID-set hashes when present. A zero denominator is not missing; missing is not zero; insufficient evidence is not failure. Formatting may round visually but accessible text exposes the exact returned value and raw numerator/denominator. The client never divides.

Cost shows integer minor amount and three-letter original currency for every group. Unlike currencies remain separate. ILS reporting total appears only when the response includes complete conversion amount/rate/source/date evidence; otherwise the ILS section is incomplete with discrepancy IDs. Reservations are not spend. Gmail operational calls may be counted with zero fee without inventing a cost. Client-side FX, floats, current exchange-rate lookup, and subtracting cap from mixed currencies are forbidden.

Charts use semantic SVG/canvas only as a visual companion. Each has a visible title, text summary, legend with shape/pattern and text, and adjacent fully equivalent HTML table. Keyboard users can reach data rows without traversing every decorative mark. `prefers-reduced-motion` disables transitions. Color contrast is at least 3:1 for chart marks and 4.5:1 for normal text.

### Immutable decision action

The `DecisionEvidence` panel uses server-returned metric snapshot ID/version/hash, evidence bundle refs, rule/query version, complete/warnings/as-of, counts/denominators, and existing decision status. Before enabling confirmation, it calls `getArtifact` for every evidence-bundle artifact and displays the exact returned accepted status/version/content hash beside the decision request; missing, stale, rejected, superseded, or mismatched evidence blocks the action without calculating acceptance. It does not run PRODUCT-02 thresholds. `recordExperimentDecision` uses `RecordExperimentDecisionRequestV1 -> ResourceResponseV1`, mutation `['experiment',id,'record-decision']`, one key, latest experiment `If-Match`, and exact `SCALE/REVISE/KILL/INCONCLUSIVE` enum plus generated snapshot/evidence/rule/reason fields.

The confirmation repeats immutable inputs and warns: a decision does not create another experiment, change a control, allocate budget, contact a recipient, or scale automatically. Require typing the decision kind. Pending disables repeat paths. On 201, invalidate experiment/list/overview/funnel/cost/timeline and render returned immutable decision. Conflict/stale report refetches everything and requires new confirmation.

Loading keeps units/labels blank rather than zero. Empty timeline/funnel explicitly reports the server snapshot has no records. Stale shows age/as-of and disables decision. Partial shows warnings and prevents decision when an authoritative section is incomplete. Redacted timeline entries remain hash/ID-visible. A decided experiment is terminal and analytics remain readable.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-08-T01 milestone=M7 depends_on=BACKEND-06-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement report provenance/query hooks —** Input: six generated operations and snapshot rules, using BACKEND-02 canonical generated client/types. Operation: render version/as-of/high-watermark/completeness/warnings/correlation, stable paging, and expiry restart. Output: reproducible panels. Test evidence: concurrent-commit, expired/lost cursor, stale/partial/503 fixtures. Failure behavior: discard mixed pages and disable decision.
<!-- roadmap-task id=FRONTEND-08-T02 milestone=M7 depends_on=FRONTEND-08-T01 mode=serial locks=frontend-client -->
- [ ] **Implement funnel and accessible chart/table —** Input: server counts/conversions/hashes. Operation: display exact statuses/numerators/denominators and equivalent visualization without arithmetic. Output: honest funnel. Test evidence: zero denominator, missing, insufficient evidence, direct/reconciled dedupe, suppression/ambiguity fixtures. Failure behavior: no fabricated zero/value.
<!-- roadmap-task id=FRONTEND-08-T03 milestone=M7 depends_on=FRONTEND-08-T02,BACKEND-06-T03 mode=serial locks=frontend-client -->
- [ ] **Implement cost/provider evidence —** Input: server original-currency/reservation/conversion/discrepancy fields. Operation: group/display exactly as returned and expose recorded ILS provenance. Output: cost diagnosis. Test evidence: unlike currencies, rounding vectors, missing FX, reservation lifecycle, provider parity. Failure behavior: incomplete ILS and visible discrepancy.
<!-- roadmap-task id=FRONTEND-08-T04 milestone=M7 depends_on=FRONTEND-08-T03,BACKEND-06-T02,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement immutable decision confirmation —** Input: fresh complete server snapshot/rule references plus refetched accepted artifact versions/hashes, using BACKEND-02 canonical generated client/types. Operation: confirm exact generated request/key/ETag, submit once, invalidate/refetch, and render immutable result. Output: operator-owned decision plus implemented decision-handoff UI surface/action contract. Test evidence: each kind, stale report/ETag, duplicate decision, network unknown, no downstream authority. Failure behavior: remain evaluating and preserve inputs.

## Test strategy

- **Math `test_frontend_never_calculates_conversion_denominator_cost_ils_or_decision`:** AST/runtime spy.
- **Funnel `test_zero_denominator_missing_and_insufficient_evidence_render_distinctly`:** exact values.
- **Cost `test_original_currencies_and_recorded_ils_evidence_never_silently_mix`:** discrepancy visible.
- **Snapshot `test_expired_timeline_cursor_discards_pages_and_restarts_one`:** no mixed snapshot.
- **Decision `test_recorded_decision_uses_fresh_server_refs_and_grants_no_scale_send_or_spend`:** network allowlist.
- **Accessibility `test_every_chart_has_equivalent_table_noncolor_encoding_and_reduced_motion`:** axe/keyboard/contrast.

## Security, privacy, compliance, idempotency, observability, and cost

Reports expose safe IDs/hashes and redacted summaries only. No recipient/content/source text/provider payload/credential/prompt appears. Opaque cursors stay in memory and out of URL/telemetry. Safe telemetry records operation, projection version, freshness/complete status, row/page count, duration, safe error/warning codes, cache indicator as returned, and correlation. The UI itself incurs bounded query/render cost through page limit 50, documented polling, virtualization only with accessible table fallback, and aborts.

## Failure, rollback, and operator recovery

Unknown enum, impossible multiplicity, missing authoritative source, currency discrepancy, cursor loss, timeout, or privacy error fails the affected report visibly and may link returned incident to Recovery. The browser never repairs source rows or saves a corrected number. Roll back report UI/query version; backend immutable source data remains. A decision command with unknown outcome replays exact request/key after refetch checks.

## Acceptance and retained evidence

- [ ] All report provenance/freshness/completeness/warnings and stable snapshot behavior are visible.
- [ ] Counts, hashes, denominators/statuses, currency/ILS evidence, reservations, discrepancies, and ambiguity are server-owned and unmodified.
- [ ] Every chart has a fully equivalent accessible data table and non-color encoding.
- [ ] Decision uses exact generated request/ETag/key and grants no automatic scale/spend/send.
- [ ] Loading/empty/stale/error/partial/redacted/terminal states pass across tested breakpoints.

Retain report fixtures, AST no-math scan, snapshot pagination traces, chart/table parity and contrast evidence, currency/ILS screenshots, decision network traces, and axe/keyboard output.

## Dependencies and next deliverable

FRONTEND-08 consumes BACKEND-06 and message/provider evidence. Discrepancies, ambiguities, snapshot failures, and incidents deep-link to [FRONTEND-09](09-error-recovery-and-accessibility.md). Recording a decision closes the current experiment version; it does not start a new one.
