# Success Metrics and Evidence Standard

**Document ID:** PRODUCT-02
**Status:** Planned gate definition
**Milestone:** M0
**Owner:** Solo operator
**Prerequisites:** [PRODUCT-01 product scope](01-product-scope.md)
**Outputs:** Metric definitions, hard gates, experiment decision rules, evidence bundle
**Unlocks:** PRODUCT-03 risk gate, M3 evaluations, and M9 decision record
**Risk:** High
**Complexity:** M

## Outcome and timing

This file prevents attractive demos and noisy outreach counts from masquerading as validation. M0 defines how every later gate is measured. The first experiment optimizes for learning per unit of operator attention while holding safety constraints at zero tolerance.

## Current repository state

The foundation has health responses, request duration logs, a worker-ready event, and unit/integration checks. It has no product analytics, workflow metrics, provider-cost ledger, agent evaluation dataset, funnel, Gmail delivery evidence, experiment baseline, or decision record. Current “online” frontend labels only reflect API/database readiness.

## Metric principles

1. Raw numerator and denominator are retained; percentages alone are insufficient.
2. Safety and compliance gates are hard constraints, not tradeable against conversion.
3. Agent quality is measured offline before provider-backed workflows depend on it.
4. Cost includes provider spend and operator review/delivery time.
5. Small samples are reported as uncertain. `INCONCLUSIVE` is a valid decision.
6. A metric without a decision owner, query, evidence source, and failure action is not a product metric.

## Canonical metric record

Every `MetricObservation` must contain `metric_name`, `definition_version`, `experiment_id`, `window_start`, `window_end`, `numerator`, `denominator`, `unit`, `source_event_ids`, `computed_at`, and `query_version`. Currency observations additionally contain `original_currency`, `original_amount`, `fx_rate_to_ils`, `fx_rate_source`, `fx_rate_date`, and `amount_ils`. Never silently mix provider currencies.

## Milestone hard gates

| Gate | Metric and exact threshold | Evidence | Failure behavior |
| --- | --- | --- | --- |
| M0 scope | required `ExperimentBrief` fields complete | signed schema-valid brief | block M1 |
| M1 restart and duplicate safety | uncontrolled duplicate Gmail messages = `0` across every defined crash point and repeated DBOS recovery run | Gmail IDs, RFC message IDs, run IDs, outbound-attempt ledger | disqualify DBOS; migrate to Temporal; outreach stays off |
| M1 ambiguous outcome | reconciled ambiguous outcomes = `100%`; blind retries = `0` | outbound-attempt ledger, provider-result capture, kill-point traces, and Sent-mail queries | disqualify DBOS; migrate to Temporal |
| M1 cancellation/operator control | pause and cancellation stop new provider calls within the tested control bound; post-cancel provider calls = `0` | command/event timeline | disqualify DBOS; migrate to Temporal |
| M1 workflow versioning | every in-flight fixture completes or reaches its documented operator-recovery state across the tested DBOS upgrade | before/after workflow-version traces | disqualify DBOS; migrate to Temporal |
| M1 observability | workflow, policy, attempt, provider, ambiguity, and recovery evidence are correlated and operator-visible = `100%` | retained trace/audit bundle | disqualify DBOS; migrate to Temporal |
| M1 rate-limit recovery | configured queue and send rate limits are never exceeded under worker restart and concurrent fixtures | DBOS queue/admission traces and provider-call timestamps | disqualify DBOS; migrate to Temporal |
| M2 records | invalid state transitions accepted = `0`; duplicate idempotency keys committed = `0`; audit gaps = `0` | migration, constraint, property, and restore tests | block M3 |
| M3 schema quality | valid typed artifacts = `100%` on promotion fixtures | versioned eval report | reject agent/provider version |
| M3 evidence fidelity | unsupported material claims = `0`; citation precision at claim level >= `0.95` | operator-labeled fixtures and captured sources | reject agent/provider version |
| M3 cost | p95 run cost and token/tool counts remain within the pre-registered per-artifact cap | cost ledger replay | reject or simplify version |
| M4 completion | one synthetic experiment reaches `READY_FOR_LEADS` with all required artifacts and zero outreach calls | workflow/event/artifact bundle | block M5 |
| M5 qualification | provenance coverage = `100%`; duplicate eligible leads = `0`; precision for `QUALIFIED` >= `0.80` on at least 50 labeled fixtures | labeled fixture report and dedupe query | revise criteria/model; block M6 |
| M6 send safety | test messages outside approved recipients = `0`; suppression violations = `0`; budget/rate-limit violations = `0`; unresolved ambiguous sends = `0` | test-inbox and audit reconciliation bundle | global kill switch; block M7 |
| M6 reply sync | expected test replies linked to the right thread and experiment = `100%`; cursor replay loss = `0` | Gmail history fixture and replay log | disable sync/send workflow |
| M7 operability | complete synthetic experiment controllable without database/CLI edits; undisclosed error states = `0` in the E2E script | browser video/screenshots, event history, accessibility report | block M8 |
| M8 recovery | encrypted backup restores on a fresh target and integrity checks pass; critical alerts exercised = `100%` | restore manifest and incident drill | block M9 |
| M9 bounded authority | sends, spend, active leads, and provider calls never exceed pre-registered caps | policy and cost queries | stop experiment immediately |

Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues.

Only the isolated disposable M1 harness may send before M6, and only to operator-owned test inboxes. Product outreach remains disabled until both M1 and M6 evidence gates pass. Later documents may make a threshold stricter; they may not weaken these hard gates without an approved architecture decision and updated risk acceptance.

## Product-learning metrics

These metrics inform `SCALE`, `REVISE`, `KILL`, or `INCONCLUSIVE`; they never override hard safety gates.

| Metric | Definition | Decision use |
| --- | --- | --- |
| `evidence_qualified_lead_rate` | leads passing deterministic evidence completeness and qualification / unique researched businesses | Shows whether the segment can be targeted economically |
| `operator_review_minutes_per_qualified_lead` | review minutes / approved qualified leads | Tests whether automation saves attention |
| `delivered_message_rate` | sent messages without bounce indication / reconciled sent messages | Separates deliverability failure from offer failure |
| `positive_reply_rate` | unique positive human replies / delivered unique recipients | Demand signal; automated replies excluded |
| `negative_or_opt_out_rate` | unique negative or opt-out replies / delivered unique recipients | Offer/targeting and reputation signal |
| `qualified_conversation_rate` | recipients agreeing to a relevant discovery or buying conversation / delivered unique recipients | Stronger signal than generic replies |
| `paid_commitment_count` | explicit paid pilot, deposit, or signed purchase commitment | Strongest initial demand evidence |
| `provider_cost_per_qualified_conversation_ils` | attributed provider spend in ILS / qualified conversations | Tests acquisition economics before delivery cost |
| `operator_hours_per_experiment` | captured research, review, operations, and delivery-prep hours | Tests solopreneur viability |
| `projected_contribution_margin_ils` | price less direct delivery labor at registered hourly cost, provider cost, and variable expenses | Prevents revenue-only decisions |
| `decision_latency_hours` | experiment activation to decision-ready evidence, excluding pre-registered reply window | Measures learning speed without rewarding premature decisions |

## M0 baseline

The operator records either a manual baseline for the same product job or `zero-history baseline`. A manual baseline must include the number of ideas reviewed, source collection time, leads researched, qualified leads, drafts produced, provider spend, and operator minutes. Reconstructed estimates are labeled `estimated` and never compared as if observed.

M9 compares the automated run to the baseline only where definitions and scope match. No percentage-improvement claim is allowed when the baseline is zero-history or reconstructed.

## First-real-experiment decision rule

Before M9, the operator registers a sample cap and one of these decision conditions. Default condition: `50` delivered unique recipients and a `14`-day reply window after the last delivery. A smaller lawful/reputational cap is allowed, but the demand result remains `INCONCLUSIVE` unless the strong-positive condition occurs.

| Decision | Exact condition after all hard gates remain green | Required operator action |
| --- | --- | --- |
| `SCALE` candidate | at least `5` positive replies, at least `2` qualified conversations, and at least `1` explicit paid commitment within the cap | perform delivery feasibility review; scaling is a separate approved experiment |
| `REVISE` | some positive signal exists but no paid commitment, or evidence shows a specific correctable segment/offer/delivery defect | change exactly one major hypothesis and create a new brief version |
| `KILL` | `0` positive replies after `50` delivered recipients and the reply window, with deliverability >= `0.90`; or projected contribution margin <= `0` at the tested price | close the experiment and record reusable evidence |
| `INCONCLUSIVE` | cap/window ends without meeting another condition, including underpowered samples or deliverability < `0.90` | do not claim validation; decide whether a tightly scoped follow-up is affordable |

Any safety kill trigger in PRODUCT-03 overrides this table and stops activity regardless of demand.

## Scope and non-goals

In scope: milestone exit evidence, offline quality/cost promotion, raw funnel counts, provider/operator cost, hard caps, and the first real experiment's decision rule. Non-goals: public growth dashboards, investor metrics, statistical claims unsupported by the sample, attribution across multiple concurrent channels, revenue forecasts presented as observed demand, or optimizing conversion at the expense of safety and compliance.

## Exact implementation surfaces

Planned records are the frozen DB catalog names `metric_definitions`, `metric_observations`, `metric_snapshots`, `cost_entries`, and `experiment_decisions`; signed `OperatorTimeEvidenceV1` remains non-product release/experiment evidence through PRODUCT-01's existing evidence path. Planned deterministic reporting is BACKEND-06's `getExperimentOverviewReport`, `getExperimentFunnelReport`, and `getExperimentCostReport`; the authoritative decision command is BACKEND-02/05 `recordExperimentDecision`. Their exact paths are the frozen BACKEND-02 rows. The consumer is FRONTEND-01's existing experiment detail route and its overview/funnel/cost/decision modules—there are no standalone metric, cost, or decision pages or generic nested endpoints.

These records, operations, and consumers are planned and absent from the current repository. Any alias not present in the frozen catalogs fails the M0 vocabulary gate.

## Ordered implementation tasks

- [ ] **Register metric definitions —** Input: this file and the approved `ExperimentBrief`. Operation: create versioned definitions with exact numerator, denominator, exclusions, owner, query version, and decision action. Output: immutable metric registry. Test evidence: schema and duplicate-name/version tests. Failure behavior: refuse observations for unknown definitions.
- [ ] **Capture baseline evidence —** Input: manual records or zero-history declaration. Operation: record scope-matched counts, time, spend, source, and confidence. Output: baseline bundle. Test evidence: completeness query and operator signature. Failure behavior: prohibit improvement claims when evidence is absent.
- [ ] **Implement gate queries in milestone order —** Input: event/audit/cost records introduced from M2 onward. Operation: compute raw counts and derived rates deterministically. Output: versioned `MetricObservation` rows. Test evidence: golden datasets including zero denominators, duplicates, late replies, bounces, and FX conversion. Failure behavior: return unavailable with reason; never coerce missing data to zero.
- [ ] **Pre-register the M9 decision —** Input: safety gates, sample cap, reply window, price, delivery-cost assumptions. Operation: freeze the rule before contacting a real recipient. Output: signed decision-rule version. Test evidence: audit query proves it predates the first send intent. Failure behavior: block real-recipient authority.

## Test strategy

- **Unit `test_metric_queries_preserve_raw_counts`:** derived rates match retained numerator and denominator.
- **Unit `test_zero_denominator_is_unavailable_not_zero`:** absent eligible population does not report a false zero rate.
- **Unit `test_fx_conversion_retains_original_amount`:** ILS reporting never loses original currency evidence.
- **Integration `test_decision_rule_uses_reconciled_delivery_and_unique_recipients`:** retries and duplicate provider observations do not inflate the funnel.
- **Recovery `test_late_reply_recomputes_snapshot_without_rewriting_history`:** a new snapshot supersedes the earlier one.
- **Contract `test_hard_gate_cannot_be_overridden_by_demand_metric`:** safety failure yields stopped status even with positive replies.

## Safety, privacy, compliance, idempotency, observability, and cost

Metric computation uses identifiers and derived facts; dashboard projections redact message content and personal data unless the operator opens the underlying authorized record. Recomputations are idempotent by `(experiment_id, definition_version, window_end, query_version)`. Every observation links to source event IDs. Provider cost budgets fail closed when usage is missing or delayed. Outreach-law interpretations are never encoded as a conversion metric.

## Failure, rollback, and recovery

If a query version is wrong, mark its observations superseded, deploy a corrected version, recompute from immutable events, and preserve both outputs. If evidence is incomplete, pause the decision and repair ingestion; do not patch counts manually. Rollback restores the prior query version and recalculates a new snapshot.

## Acceptance and retained evidence

- [ ] Every milestone gate has an exact threshold, query owner, evidence source, and failure action.
- [ ] Safety metrics have zero-tolerance thresholds and cannot be traded for business results.
- [ ] The real-experiment rule can return `INCONCLUSIVE`.
- [ ] Cost includes ILS-normalized provider spend and operator time without losing original amounts.

Retain metric definitions, labeled evaluation datasets, query versions, raw counts, cost and time ledgers, gate snapshots, and signed decisions. Passing this definition unlocks [risk and kill criteria](03-risk-register-and-kill-criteria.md), not M1 by itself.
