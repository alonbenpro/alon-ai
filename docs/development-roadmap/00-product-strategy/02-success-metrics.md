# Success Metrics and Evidence Standard

**Document ID:** PRODUCT-02
**Status:** Planned gate definition
**Milestone:** M0, M3, M9 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PRODUCT-02-T01 -> PRODUCT-02-T02 -> PRODUCT-02-T03 -> PRODUCT-02-T04`; cross-document task Inputs `PRODUCT-02-T01 <- PRODUCT-01-T02; PRODUCT-02-T03 <- DB-05-T05; PRODUCT-02-T04 <- SEC-01-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [PRODUCT-01 product scope](01-product-scope.md)
**Outputs:** Metric definitions, hard gates, cost-first experiment decision rules, evidence bundle
**Unlocks:** PRODUCT-03 risk gate, M3 evaluations, and M9 decision record
**Risk:** High
**Complexity:** M

## Outcome and timing

This file prevents attractive demos, model quality scores, or raw outreach counts from masquerading as validation. The experiment measures qualified prospects, truthful conversations, meetings, purchase/revenue evidence, contribution economics, provider/model cost, and operator attention. Safety remains a hard constraint.

## Metric principles

1. Preserve raw numerator/denominator and exact population query; percentages alone are insufficient.
2. Safety/compliance gates cannot be traded for conversion.
3. Use deterministic logic when possible; AI spend must have a recorded routing reason.
4. Cost includes provider spend, discovery/search spend, model tier, batch mode, and operator time.
5. Small samples are explicitly uncertain. `INCONCLUSIVE` and `INSUFFICIENT_EVIDENCE` are valid outcomes.
6. A metric without owner, versioned query, evidence source, and failure action is not authoritative.
7. Scale requires meetings/revenue/economic evidence and explicit operator authorization; reaching a sample size never auto-expands the campaign.

## Canonical metric attribution

Every metric observation carries experiment/campaign/stage/tranche identity; exact membership/evidence cutoff; offer package/version/hash; applicable agent/configuration; model-routing tier and batch/urgent mode when relevant; global strategy/version/activation; raw numerator/denominator; query/definition version; window; cost currency and ILS reconciliation where applicable.

Every provider/model cost observation retains original provider currency, original amount, exchange rate source/date, ILS amount, call/request IDs, routing tier (`NO_AI|NANO|MINI|PREMIUM` where applicable), and whether an eligible batch path was used.

## Milestone hard gates

| Gate | Exact requirement | Failure behavior |
| --- | --- | --- |
| M0 scope | complete signed ExperimentBrief including Brave source policy, model-routing policy, cost-first launch stages and caps | block M1 |
| M1 durable effects | uncontrolled duplicate Gmail messages = 0; blind ambiguous retries = 0; restart/cancel/versioning/observability/rate controls pass | disqualify DBOS and require Temporal fallback |
| M2 records | invalid state transitions = 0; duplicate idempotency keys = 0; audit/restore gaps = 0 | block M3 |
| M3 artifact quality | schema-valid promoted artifacts = 100%; unsupported material claims = 0; evidence/cost thresholds pass | reject version |
| M3 routing economy | deterministic/no-AI opportunities do not call a model; initial extraction/scoring uses Nano; Mini has shortlist evidence; Premium has exact explicit approval; batch-eligible non-urgent work uses batch unless a retained reason explains why not | reject routing/configuration |
| M4 synthetic completion | one full idea→research→offer pipeline reaches READY_FOR_LEADS with zero outreach | block M5 |
| M5 discovery/qualification | automated place/business discovery source is Brave Place Search; provenance = 100%; duplicate eligible leads = 0; final qualification precision target >=0.80 on labeled fixtures | block M6 |
| M6 send/negotiation/booking | unauthorized recipients/terms/claims/floor breaches/unconfirmed or duplicate bookings/unresolved ambiguous sends = 0 | disable affected capability |
| M7 learning/operability | weak-evidence mutation = 0; mid-stage activation = 0; full operator flow works without DB/CLI edits | block M8 |
| M8 recovery | 2-vCPU/4-GB target or smaller proven envelope operates within limits; encrypted local storage and encrypted R2 restore from fresh target pass; private ingress is fail-closed | block M9 |
| M9 bounded authority | stage/tranche membership, sends, spend, active leads, provider calls and model-tier approvals never exceed exact signed scope | stop immediately |

## Cost-first product metrics

| Metric | Definition / use |
| --- | --- |
| `discovery_cost_per_accepted_candidate_ils` | Brave discovery spend / unique accepted discovery candidates |
| `discovery_yield` | unique accepted candidates / Brave observations |
| `discovery_duplicate_rate` | deduped observations / Brave observations |
| `preliminary_qualification_yield` | PRELIMINARY passes / unique candidates |
| `final_qualification_precision` | true qualified / final-qualified labeled cases |
| `research_coverage` | evidenced required facts / required facts |
| `research_factual_accuracy` | independently correct assertions / checked assertions |
| `personalization_evidence_coverage` | supported personalization claims / material personalization claims |
| `no_ai_resolution_rate` | eligible deterministic decisions completed without a model / all routing decisions |
| `nano_share` | Nano calls / all model calls |
| `mini_shortlist_compliance` | Mini calls with valid shortlist evidence / Mini calls; target 100% |
| `premium_approval_compliance` | Premium calls with current exact approval / Premium calls; target 100% |
| `batch_eligible_usage_rate` | eligible non-urgent model work executed via batch / eligible non-urgent model work |
| `model_cost_per_final_qualified_lead_ils` | attributed model cost / final-qualified leads |
| `provider_cost_per_qualified_conversation_ils` | all attributable provider spend / qualified conversations |
| `cost_per_booking_ils` | provider + registered operator cost / confirmed bookings |
| `delivered_message_rate` | reconciled delivered / reconciled sent |
| `bounce_rate` / `complaint_rate` | corresponding unique recipients / applicable sent population |
| `positive_reply_rate` | positive human replies / delivered unique recipients |
| `qualified_conversation_rate` | qualified buying/discovery conversations / delivered unique recipients |
| `qualified_commitment_count` | explicit call-next-step or purchase-proposal commitments, kept distinct |
| `confirmed_booking_count` | explicit confirmed reconciled bookings |
| `show_rate` | evidenced attendance / elapsed eligible bookings |
| `verified_revenue_or_paid_commitment_ils` | externally evidenced paid/deposit/signed commercial evidence; payment collection remains outside product |
| `projected_contribution_margin_ils` | accepted offer economics less delivery/provider/operator variable costs |
| `operator_minutes_per_qualified_lead` | registered operator time / final-qualified leads |
| `strategy_pre_post_performance` | comparable stage outcomes before/after boundary activation |
| `cross_campaign_transfer_performance` | comparable outcomes after other campaigns adopt at their own checkpoints |

## Cost-first launch decision rule

The old automatic `100/200/300/400` increments and `100/300/600/1,000` cumulative maxima are superseded. One pre-revenue program uses these exact stages:

| Stage | Maximum real businesses | Required evidence before exit |
| --- | ---: | --- |
| `SHADOW` | `0` | full provider/model/policy/cost/booking/checkpoint simulation with no real sends; establishes technical/economic baseline only |
| `REVIEW_20` | `20` | every admitted business manually reviewed; complete outcome/cost/incident evidence; stage closes before any additional admission |
| `QUALIFIED_50` | `50` | only final-qualified businesses; complete meetings/conversation/booking/revenue/cost evidence; stage closes before scale |
| `SCALE_100_TO_300` | one explicitly authorized tranche from `100` through `300` | exact tranche size and population pre-registered by operator only after meetings plus revenue/paid-commitment or sufficiently strong contribution-economic evidence justify scale; all safety/reputation/cost gates green |

The numeric bound is a ceiling, never a requirement to exhaust the market. A smaller legal/provider/reputation/budget cap wins.

### Stage decisions

Every real stage/tranche closes to exactly `CONTINUE`, `REVISE`, `KILL`, `INCONCLUSIVE`, or `SAFETY_STOP`.

- `CONTINUE`: current evidence and every safety/economic gate pass. At `REVIEW_20`, only `QUALIFIED_50` becomes eligible. At `QUALIFIED_50`, scale still requires a separate explicit operator authorization for the exact `100..300` tranche. At `SCALE_100_TO_300`, CONTINUE is terminal for the current pre-revenue program and grants no larger automatic population.
- `REVISE`: close current program version and change a bounded hypothesis/source filter/offer/message/economic assumption under a new version.
- `KILL`: demand or contribution economics fail the pre-registered kill rule.
- `INCONCLUSIVE`: sample/window ends without sufficient evidence; do not enlarge population.
- `SAFETY_STOP`: safety/compliance/provider ambiguity/budget/reputation/recovery trigger fires; stop regardless of demand.

`SHADOW` is not real demand and does not trigger demand-derived global learning. It may contribute offline evaluation evidence. `REVIEW_20`, `QUALIFIED_50`, and each explicitly authorized scale tranche freeze a CheckpointEvidenceBundle. Weak evidence cannot promote a global strategy. Strategy activation never occurs mid-stage/tranche.

## Scale justification at 50

A `QUALIFIED_50` CONTINUE recommendation is insufficient by itself to open `SCALE_100_TO_300`. The operator must sign a `ScaleAuthorization` binding the exact next tranche size, market/segment/source/offer/strategy versions, maximum provider/model spend, window, and expiry. The authorization requires retained evidence showing:

- at least one meaningful meeting/qualified call signal and no safety/reputation stop;
- revenue/paid-commitment evidence when available, otherwise an explicit reason why observed bookings/commitments plus contribution economics are sufficient for the next bounded tranche;
- current projected contribution margin and acquisition cost assumptions are non-negative/within the pre-registered budget rule;
- the model-routing mix does not show unjustified Mini/Premium spend;
- Brave discovery yield and duplicate rates remain economically acceptable; and
- restore/kill/suppression/provider-ambiguity evidence remains current.

This is evidence-gated scope authorization, not routine per-message approval.

## M0 baseline

Record either an observed manual baseline or `zero-history baseline`: source collection time, businesses reviewed, leads researched, final-qualified leads, drafts/messages, provider/model spend by tier, operator minutes, meetings/bookings, and any verified revenue/paid commitment. Estimated history is labeled `estimated` and never compared as observed truth.

## Ordered implementation tasks

<!-- roadmap-task id=PRODUCT-02-T01 milestone=M0 depends_on=PRODUCT-01-T02 mode=parallel locks=product-contracts -->
- [ ] **Register metric and staged-decision definitions —** Input: PRODUCT-01 contract and ExperimentBrief. Operation: create versioned metrics plus exact `SHADOW|REVIEW_20|QUALIFIED_50|SCALE_100_TO_300` stage rules, cost/model-routing metrics and ScaleAuthorization requirements. Output: immutable metric/stage registry. Test evidence: exact stage/order/bounds, decision enums, removal of legacy 600/1,000 semantics, premium-approval and batch/no-AI attribution tests. Failure behavior: block M1/M9 authority.
<!-- roadmap-task id=PRODUCT-02-T02 milestone=M0 depends_on=PRODUCT-02-T01 mode=parallel locks=product-contracts -->
- [ ] **Capture baseline evidence —** Input: observed manual records or explicit zero-history baseline. Operation: retain counts/time/cost by provider/model tier and demand outcomes without reconstruction as fact. Output: signed baseline. Test evidence: source/time/currency/tier completeness. Failure behavior: comparisons remain unavailable rather than imputed.
<!-- roadmap-task id=PRODUCT-02-T03 milestone=M3 depends_on=PRODUCT-02-T02,DB-05-T05 mode=parallel locks=product-contracts,observability -->
- [ ] **Implement gate queries in milestone order —** Input: immutable event/cost/artifact/strategy/provider data. Operation: implement reproducible queries for every hard gate and cost-first metric with exact denominators and routing/stage attribution. Output: replayable gate snapshots. Test evidence: late/missing/currency/tier/selection-bias cases. Failure behavior: unavailable metric cannot become pass.
<!-- roadmap-task id=PRODUCT-02-T04 milestone=M9 depends_on=PRODUCT-02-T03,SEC-01-T05 mode=serial locks=product-contracts,milestone-gate -->
- [ ] **Pre-register the staged M9 decision —** Input: current risk/legal/provider/economic evidence. Operation: sign the exact cost-first stage program and caps before real admission, including manual-review 20, qualified 50, and scale authorization semantics. Output: immutable M9 decision definition. Test evidence: legacy cohort schedule, scale without explicit 100..300 authorization, or shadow-as-demand evidence rejected. Failure behavior: PRODUCT_OUTREACH remains false.

## Acceptance

- [ ] Raw counts, uncertainty, cost, routing tier and stage attribution are reproducible.
- [ ] Safety hard gates remain zero-tolerance.
- [ ] Automated expansion beyond the signed stage/tranche is impossible.
- [ ] Shadow evidence cannot masquerade as real demand.
- [ ] Scale requires meetings/economic evidence plus explicit bounded operator authorization.

Retain metric definitions/query versions, baseline, stage authorizations, checkpoint bundles/decisions, model-routing/cost records, ScaleAuthorization, and supporting economic evidence.
