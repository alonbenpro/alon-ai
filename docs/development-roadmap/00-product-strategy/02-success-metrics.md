# Success Metrics and Evidence Standard

**Document ID:** PRODUCT-02
**Status:** Planned gate definition
**Milestone:** M0, M3, M9 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PRODUCT-02-T01 -> PRODUCT-02-T02 -> PRODUCT-02-T03 -> PRODUCT-02-T04`; cross-document task Inputs `PRODUCT-02-T01 <- PRODUCT-01-T02; PRODUCT-02-T03 <- DB-05-T05; PRODUCT-02-T04 <- SEC-01-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [PRODUCT-01 product scope](01-product-scope.md)
**Outputs:** Metric definitions, hard gates, experiment decision rules, evidence bundle
**Unlocks:** PRODUCT-03 risk gate, M3 evaluations, and M9 decision record
**Risk:** High
**Complexity:** M

## Outcome and timing

This file prevents attractive demos and noisy outreach counts from masquerading as validation. M0 defines how every later gate is measured. The experiment measures qualified prospects, truthful conversations, qualified commitments, confirmed bookings, and useful global strategy changes per unit of cost and operator attention. Safety retains zero tolerance.

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

Every `MetricObservation` must contain `metric_name`, `definition_version`, `experiment_id`, `window_start`, `window_end`, `numerator`, `denominator`, `unit`, `source_event_ids`, `computed_at`, and `query_version`, `campaign_id`, `cohort_id`, `stage_ordinal`, governing `offer_package_id/version/hash`, applicable `agent_id`, `producer_strategy_version`, `global_strategy_package_id/version`, and `strategy_activation_id`. Attribution is stored at action level and never inferred from the currently active strategy. Currency observations additionally contain `original_currency`, `original_amount`, `fx_rate_to_ils`, `fx_rate_source`, `fx_rate_date`, and `amount_ils`. Never silently mix provider currencies.

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
| M6 reply sync | correct thread/experiment linkage = `100%`; cursor replay loss = `0`; every reply stops cold sequence; false durable suppression of eligible replies = `0` | Gmail thread/replay evidence | disable affected conversation/send workflow |
| M6 negotiation | unauthorized terms/claims or below-floor price/margin actions = `0`; inferred budget accepted as stated = `0` | deterministic commercial vectors and simulated objections | stop action; open exception/incident |
| M6 booking | unconfirmed, duplicate, wrong-recipient/timezone, or post-stop event writes = `0`; blind retries = `0` | test calendar, DST, conflict, reschedule/cancel and replay evidence | disable booking writes and reconcile |
| M7 checkpoint learning | applicable agents evaluated = `100%`; weak-evidence mutation, unguarded promotion, mid-cohort activation and history rewriting = `0` | checkpoint/global-learning simulation and cross-campaign rollback fixtures | block promotion/activation and pause affected actions |
| M7 operability | complete synthetic experiment controllable without database/CLI edits; undisclosed error states = `0` in the E2E script | browser video/screenshots, event history, accessibility report | block M8 |
| M8 recovery | encrypted backup restores on a fresh target and integrity checks pass; critical alerts exercised = `100%` | restore manifest and incident drill | block M9 |
| M9 bounded authority | sends, spend, active leads, and provider calls never exceed pre-registered caps | policy and cost queries | stop experiment immediately |

Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues.

Only the isolated disposable M1 harness may send before M6, and only to operator-owned test inboxes. Product outreach remains disabled until both M1 and M6 evidence gates pass. Later documents may make a threshold stricter; they may not weaken these hard gates without an approved architecture decision and updated risk acceptance.

## Product-learning metrics

These metrics inform exactly `CONTINUE`, `REVISE`, `KILL`, `INCONCLUSIVE`, or `SAFETY_STOP`; they never override hard safety gates.

| Metric | Definition | Decision use |
| --- | --- | --- |
| `evidence_qualified_lead_rate` | leads passing deterministic evidence completeness and qualification / unique researched businesses | Shows whether the segment can be targeted economically |
| `operator_minutes_per_qualified_lead` | configuration/exception/recovery minutes / finally qualified leads | Measures attention saved without requiring routine review |
| `delivered_message_rate` | sent messages without bounce indication / reconciled sent messages | Separates deliverability failure from offer failure |
| `positive_reply_rate` | unique positive human replies / delivered unique recipients | Demand signal; automated replies excluded |
| `negative_or_opt_out_rate` | unique negative or opt-out replies / delivered unique recipients | Offer/targeting and reputation signal |
| `qualified_conversation_rate` | recipients agreeing to a relevant discovery or buying conversation / delivered unique recipients | Stronger signal than generic replies |
| `qualified_commitment_count` | unique finally qualified leads explicitly accepting the commercial next step or buying commitment with source evidence | Separates willingness to act from positive sentiment |
| `paid_commitment_count` | externally verified accepted paid pilot, deposit evidence, or signed purchase commitment linked to exact offer terms | Preserves stronger demand floors; the product does not collect payment |
| `provider_cost_per_qualified_conversation_ils` | attributed provider spend in ILS / qualified conversations | Tests acquisition economics before delivery cost |
| `operator_hours_per_experiment` | captured research, review, operations, and delivery-prep hours | Tests solopreneur viability |
| `projected_contribution_margin_ils` | price less direct delivery labor at registered hourly cost, provider cost, and variable expenses | Prevents revenue-only decisions |
| `decision_latency_hours` | experiment activation to decision-ready evidence, excluding pre-registered reply window | Measures learning speed without rewarding premature decisions |
| `discovery_yield` / `discovery_duplicate_rate` | unique accepted candidates / source candidates; duplicates / source candidates | Detects weak sources and repeated reach |
| `research_coverage` / `research_factual_accuracy` | evidenced required facts / required facts; independently correct assertions / checked assertions | Gates research reliability |
| `preliminary_qualification_yield` / `final_qualification_precision` | preliminary passes / unique candidates; true qualified fixtures / final-qualified fixtures | Separates inexpensive admission from final quality |
| `personalization_evidence_coverage` | supported personalization claims / material personalization claims | Blocks fabricated familiarity and proof |
| `bounce_rate` / `complaint_rate` / `human_reply_rate` | unique bounced, complaining, or human-replying recipients / corresponding unique reconciled-send or delivered population | Owns deliverability/reputation/response stops |
| `objection_category_count` / `objection_resolution_rate` | finite redacted category counts; evidenced resolved objections / eligible objections | Improves truthful response objectives |
| `negotiation_outcome_count` / `negotiation_discount_rate` | finite accepted/rejected/expired/exception counts; accepted discount / offer base price | Measures bounded negotiation outcomes |
| `negotiated_contribution_margin` / `negotiated_scope_change_count` | exact margin using cost/FX/rounding versions; accepted approved scope variants | Enforces offer economics |
| `booking_rate` / `show_rate` | unique confirmed reconciled bookings / qualified commitments; evidenced attendees / elapsed eligible bookings | Separates confirmation, creation and attendance |
| `cost_per_qualified_lead_ils` / `cost_per_qualified_commitment_ils` / `cost_per_booking_ils` | attributed provider plus registered operator cost / unique final-qualified leads, qualified commitments, or confirmed bookings | Tests complete acquisition economics |
| `strategy_pre_post_performance` | comparable frozen-cohort outcomes and uncertainty before/after activation | Detects improvement and deterioration |
| `learning_promotion_rate` / `learning_rollback_rate` | promoted or rolled-back agent strategies / eligible closed-checkpoint evaluations | Exposes churn and failed promotions |
| `cross_campaign_transfer_performance` | outcome/guardrail deltas on other campaigns after their own checkpoint activation | Detects harmful transfer |

Every metric definition includes an owner, versioned query, raw denominator, exclusions, uncertainty, and failure action. Booking counts require explicit confirmation and positive reconciled provider evidence. Pending, ambiguous, cancelled, duplicate, and merely proposed bookings are excluded; rescheduling preserves booking identity. Show rate uses elapsed meetings with attendance evidence. Inferred budget and agent confidence never become observed commitments.

Pre/post comparison freezes hypothesis, source/evidence definitions, window, eligibility, and attribution. Report sample sizes, late outcomes, selection differences, and uncertainty; incomparable cohorts cannot establish causality. `KEEP` and `INSUFFICIENT_EVIDENCE` perform no strategy mutation and remain distinct results.

## M0 baseline

The operator records either a manual baseline for the same product job or `zero-history baseline`. A manual baseline must include the number of ideas reviewed, source collection time, leads researched, qualified leads, drafts produced, provider spend, and operator minutes. Reconstructed estimates are labeled `estimated` and never compared as if observed.

M9 compares the automated run to the baseline only where definitions and scope match. No percentage-improvement claim is allowed when the baseline is zero-history or reconstructed.

## Staged first-real-experiment decision rule

Before M9, the operator freezes one immutable `100/200/300/400` incremental cohort program with `100/300/600/1,000` cumulative maxima and a separate observation window after each stage. These are new unique delivered recipients per stage, never cumulative batch sizes. The same business, person, normalized recipient identity, or suppression identity cannot be counted in multiple stages of one experiment version. The `1,000` value is a hard ceiling, not a requirement to exhaust the reachable market.

| Stage | New delivered recipients | Cumulative maximum | Default demand floor after the complete observation window |
| --- | ---: | ---: | --- |
| `STAGE_1_SIGNAL` | `100` | `100` | at least `3` positive human replies or at least `1` qualified conversation |
| `STAGE_2_CONFIRM` | `200` | `300` | cumulative at least `6` positive human replies and `2` qualified conversations, or at least `1` verified paid commitment |
| `STAGE_3_REPEAT` | `300` | `600` | cumulative at least `12` positive human replies, `4` qualified conversations, and `1` verified paid commitment |
| `STAGE_4_ESTIMATE` | `400` | `1,000` | cumulative at least `20` positive human replies, `8` qualified conversations, `2` verified paid commitments, and projected contribution margin `> 0` |

A pre-registered rule may be stricter, never weaker. Every continuation also requires deliverability `>=0.90`, zero complaints, zero unresolved ambiguous sends, all safety gates green, and no registered economic kill. Every stage ends in exactly `CONTINUE`, `REVISE`, `KILL`, `INCONCLUSIVE`, or `SAFETY_STOP`. `CheckpointEvaluationService` records the immutable authenticated decision after deterministic evidence, safety, metric, cost, and capacity checks; in-envelope transitions do not await an operator signature per checkpoint. Only `CONTINUE` makes the next registered cohort eligible. At Stage 4 it is a positive terminal checkpoint and cannot admit a fifth cohort or exceed 1,000.

| Decision | Exact effect | Required deterministic action |
| --- | --- | --- |
| `CONTINUE` | the current stage demand floor and every safety/economic gate pass | at Stages 1-3 make only the next immutable cohort eligible after fresh checks; at Stage 4 close positively with no further admission |
| `REVISE` | evidence identifies one correctable segment, offer, message, price, or delivery hypothesis | close this program version, change exactly one major hypothesis, and create a new version |
| `KILL` | the registered demand or contribution-margin kill fires | close the experiment and retain reusable evidence |
| `INCONCLUSIVE` | a stage window or eligible denominator ends without another decision | do not open the next stage or claim validation; require a separately justified experiment |
| `SAFETY_STOP` | any PRODUCT-03, compliance, suppression, provider-ambiguity, budget, credential, audit, telemetry, backup, bounce, or complaint trigger fires | stop immediately regardless of demand and execute the owning recovery/incident contract |

Agent research, citations, contradiction checks, confidence, and offline evaluation establish only that an idea is test-worthy. They never substitute for observed delivered-recipient, conversation, or paid-commitment evidence. Any safety kill trigger in PRODUCT-03 overrides this table and stops activity regardless of demand.

## Scope and non-goals

In scope: milestone exit evidence, offline quality/cost promotion, raw funnel counts, provider/operator cost, hard caps, and the first real experiment's decision rule. Non-goals: public growth dashboards, investor metrics, statistical claims unsupported by the sample, attribution across multiple concurrent channels, revenue forecasts presented as observed demand, or optimizing conversion at the expense of safety and compliance.

## Exact implementation surfaces

The database roadmap owns metric definitions/observations/snapshots, cost entries, checkpoint decisions/evidence, and action-level strategy/activation references. Signed `OperatorTimeEvidenceV1` remains non-product evidence. Backend reporting exposes discovery → qualification → conversation → negotiation → commitment → booking → checkpoint → learning through server-authoritative dashboard projections.

`CheckpointEvaluationService` owns checkpoint decisions; `StrategyActivationService` owns promotion, activation, and rollback after guarded evaluation. Agents recommend. API/route/table catalogs must include these surfaces atomically without stale fixed counts. These implementations remain planned.

## Ordered implementation tasks

<!-- roadmap-task id=PRODUCT-02-T01 milestone=M0 depends_on=PRODUCT-01-T02 mode=parallel locks=product-contracts -->
- [ ] **Register metric and staged-decision definitions —** Input: this file and the approved `ExperimentBrief`. Operation: create versioned metric definitions plus the canonical stage names, `100/200/300/400` increments, `100/300/600/1,000` cumulative maxima, default demand floors, barrier enums, exact numerator/denominator exclusions, owner, query version, and decision action. Output: immutable metric registry and `StagedValidationRuleV1` contract for M2 consumers. Test evidence: schema, tuple/set equality, demand-floor boundary, and duplicate-name/version tests. Failure behavior: refuse unknown metrics, ambiguous schedules, weaker thresholds, or observations for unknown definitions.
<!-- roadmap-task id=PRODUCT-02-T02 milestone=M0 depends_on=PRODUCT-02-T01 mode=parallel locks=product-contracts -->
- [ ] **Capture baseline evidence —** Input: manual records or zero-history declaration. Operation: record scope-matched counts, time, spend, source, and confidence. Output: baseline bundle. Test evidence: completeness query and operator signature. Failure behavior: prohibit improvement claims when evidence is absent.
<!-- roadmap-task id=PRODUCT-02-T03 milestone=M3 depends_on=PRODUCT-02-T02,DB-05-T05 mode=parallel locks=backend-domain,telemetry-catalog -->
- [ ] **Implement gate queries in milestone order —** Input: event/audit/cost records introduced from M2 onward. Operation: compute raw counts and derived rates deterministically. Output: versioned `MetricObservation` rows. Test evidence: golden datasets including zero denominators, duplicates, late replies, bounces, FX conversion, negotiated margins, cancelled/rescheduled bookings, and cross-campaign strategy attribution. Failure behavior: return unavailable with reason; never coerce missing data to zero.
<!-- roadmap-task id=PRODUCT-02-T04 milestone=M9 depends_on=PRODUCT-02-T03,SEC-01-T05 mode=serial locks=product-contracts,compliance-policy,milestone-gate -->
- [ ] **Pre-register the staged M9 decision —** Input: safety gates, exact `100/200/300/400` increments, `100/300/600/1,000` cumulative maxima, stage reply windows, subsegment allocation, price, delivery-cost assumptions, and the default-or-stricter demand floors; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: freeze one versioned rule before contacting a real recipient, require an authoritative `CONTINUE` before each later cohort, and retain the exact `CONTINUE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP` decision at every checkpoint. Output: signed staged decision-rule version. Test evidence: audit query proves it predates the first send intent and boundary/race fixtures prove no later-stage admission without the prior authoritative `CONTINUE`. Failure behavior: block real-recipient authority or the next cohort.

## Test strategy

- **Unit `test_metric_queries_preserve_raw_counts`:** derived rates match retained numerator and denominator.
- **Unit `test_zero_denominator_is_unavailable_not_zero`:** absent eligible population does not report a false zero rate.
- **Unit `test_fx_conversion_retains_original_amount`:** ILS reporting never loses original currency evidence.
- **Integration `test_decision_rule_uses_reconciled_delivery_and_unique_recipients`:** retries and duplicate provider observations do not inflate the funnel.
- **Recovery `test_late_reply_recomputes_snapshot_without_rewriting_history`:** a new snapshot supersedes the earlier one.
- **Contract `test_hard_gate_cannot_be_overridden_by_demand_metric`:** safety failure yields stopped status even with positive replies.
- **Contract `test_staged_rule_uses_exact_incremental_and_cumulative_caps`:** `100/200/300/400` maps only to `100/300/600/1,000` and rejects legacy or ambiguous schedules.
- **Concurrency `test_only_authoritative_continue_can_admit_the_next_unique_cohort`:** duplicate identities, stale barriers, and concurrent final-slot admissions fail closed.

## Safety, privacy, compliance, idempotency, observability, and cost

Metric storage retains exact safe ID/version attribution; telemetry uses bounded low-cardinality dimensions and excludes recipient identities, message bodies, calendar descriptions, credentials, and sensitive inferred attributes. Metric computation uses identifiers and derived facts; dashboard projections redact message content and personal data unless the operator opens the underlying authorized record. Recomputations are idempotent by `(experiment_id, cohort_id, definition_version, window_end, query_version, attribution_snapshot_hash)`. Every observation links to source event IDs. Provider cost budgets fail closed when usage is missing or delayed. Outreach-law interpretations are never encoded as a conversion metric.

## Failure, rollback, and recovery

If a query version is wrong, mark its observations superseded, deploy a corrected version, recompute from immutable events, and preserve both outputs. If evidence is incomplete, pause the decision and repair ingestion; do not patch counts manually. Rollback restores the prior query version and recalculates a new snapshot.

## Acceptance and retained evidence

- [ ] Every milestone gate has an exact threshold, query owner, evidence source, and failure action.
- [ ] Safety metrics have zero-tolerance thresholds and cannot be traded for business results.
- [ ] Every checkpoint uses the exact five-result set; terminal `CONTINUE` cannot exceed 1,000.
- [ ] Negotiation, booking, and learning have evidence-backed denominators and exact strategy/cohort attribution.
- [ ] Weak evidence cannot promote a strategy; rollback preserves history.
- [ ] Cost includes ILS-normalized provider spend and operator time without losing original amounts.

Retain metric definitions, labeled evaluation datasets, query versions, raw counts, cost and time ledgers, gate snapshots, and signed decisions. Passing this definition unlocks [risk and kill criteria](03-risk-register-and-kill-criteria.md), not M1 by itself.
