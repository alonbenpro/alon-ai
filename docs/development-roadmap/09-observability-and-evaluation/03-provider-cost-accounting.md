# Provider Cost Accounting, Budgets, and ILS Evidence

**Document ID:** OBS-03
**Status:** Planned M3-M8 provider-cost ledger; no live providers, reservations, cost entries, invoices, FX capture, or cost dashboards exist today
**Milestone:** M3, M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `OBS-03-T01 <- PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,PROVIDER-06-T01,PROVIDER-01-T02,PROVIDER-02-T01,PROVIDER-01-T01; OBS-03-T02 <- OBS-03-T01,DB-05-T02; OBS-03-T03 <- OBS-03-T02; OBS-03-T04 <- OBS-03-T03; OBS-03-T05 <- OBS-03-T04,AGENT-10-T01,AGENT-10-T05`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Original-currency cost ledger, reservation/reconciliation protocol, immutable pricing/usage evidence, Bank of Israel ILS projection, discrepancy handling, budgets/alerts, and tests
**Unlocks:** Cost-gated provider calls, M7 cost reports, agent promotion/cost rollback, and M8 financial operations
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Every M9 cost entry carries experiment version and validation-stage attribution. Reservations are bounded independently for the next `100|200|300|400` cohort and cumulatively for the `1,000` ceiling; unused capacity never becomes another stage's silent budget. Barrier snapshots report stage and cumulative provider spend, operator time, cost per positive reply/conversation/paid commitment, and projected contribution margin before continuation.

Every paid provider call reserves a conservative maximum before network access and reconciles exactly once to a DB-05 `cost_entries` row using the provider's original currency and immutable usage/pricing evidence. ILS is a separate reporting projection with dated source evidence; it never replaces original-currency truth or silently mixes amounts. Unknown cost or missing FX evidence keeps reservations held, blocks further paid work at the bound, and becomes visible.

The FX source is the Bank of Israel [representative exchange-rate service](https://www.boi.org.il/en/economic-roles/financial-markets/exchange-rates/) and [series/API extraction guidance](https://www.boi.org.il/information/bank-paymnts/guide/api-guide/), accessed 2026-08-29. The Bank states representative rates are indicative and not legally binding; Alon AI uses them only as a documented product reporting policy. Counsel/accountant decides accounting/tax books and any different statutory rate.

## Current repository state

No provider is called. `ProviderResultMetaV1` plans tokens, original `cost_minor`, and currency; DB-01/05 plans accounts/reservations/cost rows; AGENT-10 defines per-suite native cost thresholds. None is implemented. There is no price catalog, usage capture, FX client/cache/evidence, invoice reconciliation, budget dashboard, cost alert, or ILS calculation. Gmail sends currently do not occur and Gmail API fee must not be assumed to represent the full mailbox/reputation/hosting cost.

## Scope and non-goals

In scope: model/search/page/business/Gmail/calendar/OIDC/monitoring/storage/KMS provider operation cost where attributable; original currency/minor-unit registries; estimates/reservations/actuals; pricing versions; usage; retries/cancelled/failed/ambiguous calls; FX/ILS evidence; invoice discrepancy; experiment/workflow/agent/send/booking/action-attribution linkage; dashboards/alerts; and retention.

Non-goals: browser FX lookup, floating-point money, adding unlike currencies, retroactively rewriting usage to match an invoice, ignoring failed-call charges, counting reservations as spend, assuming free-tier permanence, optimizing cost by weakening quality/safety, or treating ILS representative rate as transaction/accounting truth.

## Exact planned implementation surfaces

Create `costs/contracts.py`, `costs/currency.py`, `costs/pricing.py`, `costs/fx.py`, `application/provider_costs.py`, provider usage adapters, reconciliation jobs, and tests. `BudgetService` exclusively writes `budget_accounts`/`budget_reservations`; `ProviderCostReconciliationService` exclusively writes/updates `cost_entries` under the DB-05 contract. Reports use BACKEND-06; frontend never calculates.

### Exact ledger and evidence contract

The exact `cost_entries` column set is imported from [DB-05's authoritative ledger](../02-database/05-audit-events-and-idempotency.md): `cost_entry_id`, `provider`, `operation`, `provider_call_id`, `experiment_id`, `workflow_run_id`, `agent_run_id`, `send_attempt_id`, `provider_result_id`, `booking_attempt_id`, `booking_result_id`, `action_attribution_id`, `usage_schema_version`, `usage_json`, `usage_hash`, `amount_minor`, `currency`, `reporting_amount_minor_ils`, `fx_rate`, `fx_rate_source`, `fx_rate_date`, `provider_invoice_ref`, `occurred_at`, `recorded_at`, `idempotency_key`. Preserve DB-05's exact types, nullability, checks, composite references and uniqueness; do not add an alias ledger. The optional workflow/agent/send/booking fields form the five disjoint allocation cases below. The nullable physical `action_attribution_id` does not permit an unattributed product action: the reconciliation service requires its exact existing typed attribution before accepting a product cost allocation.

`ProviderUsageEvidenceV1` stored in `usage_json` is strict and capability-specific but always includes: `schema_version`; provider/capability/operation; the same UUID `provider_call_id` as the relational column and provider idempotency key; safe request ID where permitted; request/result schema versions and hashes; price-catalog ID/version/hash/effective time; usage units as nonnegative integers with unit enums; original-currency exponent; estimated/reserved/actual calculation components; outcome; started/finished UTC; retry/fixture mode; and source capture/invoice reference hashes. No prompt, query, URL, recipient, content, token, provider payload, secret, or raw invoice enters the row.

`usage_hash` is DB-01 lowercase SHA-256 of RFC 8785 UTF-8 `{"schema_version":version,"payload":payload}` and is verified against provider ledger before insert/use. `idempotency_key` is the lowercase canonical UUID text of `provider_call_id`; the same provider/call can create one cost row. Agent allocation requires the exact DB-04 agent/experiment/workflow composite. Gmail allocation preserves distinct call and attempt UUIDs, requires the same experiment, and targets the exact DB-03 `(provider_result_id,send_attempt_id,provider_call_id,provider)` tuple with workflow/agent/booking IDs null. Calendar booking allocation requires both `booking_attempt_id` and `booking_result_id`, the exact `(booking_result_id,booking_attempt_id,provider_call_id)` tuple enforced by deferred `fk_cost_entries_booking_result`, and matching calendar/action/experiment evidence; workflow/agent/send IDs are null. Verify provider identity and signed request/result/ledger hashes in addition to the relational tuple. JSON never replaces either branch's FK or supplies missing attribution. Cancelled, failed, timed-out, refused, ambiguous, and retried calls with billed usage remain costs. A zero amount is recorded only when a versioned price catalog/provider invoice proves zero; absence is not zero.

Price catalogs are immutable signed manifests captured from official provider pricing/contract sources with access/effective date, currency, unit/exponent, tiers, rounding/minimum, taxes/credits treatment, model/operation region, and expiry/review. A price change creates a new version; provider calls are denied when no current catalog covers the exact operation. Provider-reported charged amount wins only when its semantics/currency/call identity are verified; otherwise compute from immutable usage and catalog and mark invoice reconciliation pending.

### Reservation and reconciliation sequence

1. Freeze provider request, exact price version, max tokens/results/bytes/time/calls, original currency and worst-case amount using integer/Decimal arithmetic.
2. In a serializable transaction, `BudgetService` locks the exact account/currency and open reservations, denies insufficient capacity, and inserts one `RESERVED` row keyed to the provider call. Do not convert another currency to create capacity.
3. Execute the provider call outside the transaction. Capture exact typed result and provider ledger even on failure/cancel/timeout where any charge is possible.
4. Obtain dated FX evidence required by DB-05. `ProviderCostReconciliationService` verifies request/result/usage/price hashes, the exact allocation branch and its relational references, and the governing `action_attribution_id` when required; then inserts one cost row, links the reservation as `RECONCILED`, and releases unused reservation capacity atomically. A missing/mixed branch or missing/mismatched product attribution rejects reconciliation and holds the reservation. Actual over reservation is inserted honestly, opens `COST_CAP_EXCEEDED` incident/alert, and blocks new calls; never clamp.
5. If conclusive no-call and zero charge, insert a proven zero cost entry when the provider/cost contract requires full call identity, or release with explicit no-call evidence according to the owning provider contract. Possible call/unknown charge keeps the reservation held and enters reconciliation.
6. Invoice review attaches a safe invoice reference only after provider/account/period/currency/call aggregates match. Mismatch is retained as restricted discrepancy evidence and incident; original call usage/cost row is not silently rewritten or offset by an unsupported negative entry.

Reservations expire only with conclusive no-call/no-charge evidence or a registered reconciliation decision; wall clock alone does not release possible cost. Retry receives a new provider call/idempotency/reservation/cost entry. Offline fixture/scoring operations record zero provider cost separately and cannot substitute historical price for fresh candidate capture.

### Currency registry and deterministic ILS projection

Maintain a signed ISO-4217 exponent registry version. `amount_minor` means `amount_major × 10^exponent`, integer. Original-currency aggregates group by currency; never sum them. For ILS, DB-05 requires `reporting_amount_minor_ils=amount_minor` and null FX fields when original currency is ILS.

For non-ILS:

- Use Bank of Israel representative series `DATA_TYPE=OF00` for the exact currency and normalize published units (for example a rate quoted per 100 units) to `fx_rate` = ILS per one major currency unit.
- `fx_rate_date` is the rate published for the provider `occurred_at` date when available; otherwise the most recent prior published foreign-currency business day. Never use a later rate. Fetch/capture after the Bank publication is available and store source series code, retrieval UTC, source unit, normalized Decimal rate, response hash and signed capture reference in `fx_rate_source`/restricted evidence.
- Calculate `reporting_amount_minor_ils = round_half_even((amount_minor / 10^currency_exponent) × fx_rate × 100)` using Decimal with sufficient precision; store the unrounded normalized rate and golden-vector evidence. Display/report uses stored integer only.
- If Bank of Israel does not publish that currency or evidence is unavailable/tampered, the provider/currency is ineligible before call unless a counsel/accountant-approved versioned alternative official source is added. After an already incurred call, keep reservation held and cost reconciliation pending; do not guess or use a live browser rate.

ILS panels always show “reporting projection,” source/date and completeness. Accounting/tax reports use the accountant-approved policy, which may differ and must not overwrite these rows.

### Cost allocation, caps, metrics, and alerts

Import the exact agent capability set from [AGENT-01](../04-agents/01-agent-runtime-and-contracts.md) and its `lead.discover` provider contract; do not freeze a historical capability count. [PROVIDER-07](../05-providers/07-calendar-provider.md) independently owns calendar read/write operations, which are not agent tools. Each entry has exactly one narrowest DB-05 allocation case; these table labels are explanatory and introduce no serialized enum:

| Allocation case | Required non-null owner IDs | Required null owner IDs | Attribution and evidence |
| --- | --- | --- | --- |
| shared operation | none | workflow_run_id, agent_run_id, send_attempt_id, provider_result_id, booking_attempt_id, booking_result_id | action_attribution_id null only for a genuinely non-action shared allocation under an explicit policy; never invent experiment/cohort/action scope |
| workflow-only | workflow_run_id | agent_run_id, send_attempt_id, provider_result_id, booking_attempt_id, booking_result_id | exact workflow/experiment composite; product-context read costs additionally require an existing governing action_attribution_id |
| agent | workflow_run_id, agent_run_id | send_attempt_id, provider_result_id, booking_attempt_id, booking_result_id | exact agent/workflow/experiment composite and AGENT_CALL attribution matching the call's governing configuration |
| Gmail send | send_attempt_id, provider_result_id | workflow_run_id, agent_run_id, booking_attempt_id, booking_result_id | exact same-attempt/call/provider result tuple and SEND action attribution |
| calendar booking | booking_attempt_id, booking_result_id | workflow_run_id, agent_run_id, send_attempt_id, provider_result_id | exact same-attempt/call/calendar/action result tuple and BOOKING_ACTION attribution |

For product costs, resolve `action_attribution_id` through DB-05's typed-target registry and the immutable provider request/result to the exact action kind/ID/version, experiment, campaign/cohort, offer, producer strategy version, GlobalStrategyPackage and StrategyActivation. A booking cost must match its attempt's booking_action_id and action version; an arbitrary attribution from the same campaign is insufficient. Existing pre-cohort baseline and EVALUATION_ONLY rules remain applicable; no future action/cohort or fabricated activation may fill a missing reference. AuditRecorder remains the sole attribution writer; ProviderCostReconciliationService consumes its record and never creates a competing attribution. Reject missing product attribution, wrong kind/action/offer/cohort/activation, and cross-branch IDs before cost reconciliation or reservation release.

CalendarReadPort.get_availability and CalendarReadPort.get_event_observation each have a distinct provider_call_id, reservation, typed read result/observation and operation-specific usage/pricing evidence. For experiment/campaign allocation they use workflow-only provenance with a real owning workflow and the existing governing product action attribution accepted by DB-05, traceable through the signed request and booking-intent context. These reads keep booking_attempt_id/booking_result_id and Gmail IDs null; they do not fabricate a BOOKING_ACTION, reserve a slot, or count as create/reschedule/cancel. A standalone calendar read with no authoritative experiment/action context is not allocated to a campaign until the existing versioned allocation policy provides truthful scope; it cannot borrow another action's IDs.

CalendarWritePort.create_event, reschedule_event and cancel_event costs use the calendar booking branch. Each write call binds the exact durable booking attempt, immutable booking provider result and BOOKING_ACTION attribution, including its CREATE/RESCHEDULE/CANCEL kind. A subsequent reconciliation read is a separate read call/cost and cannot reuse the original write's provider_call_id or turn a negative observation into a new write. Positive reconciliation of the original outcome does not insert a second cost for the original call. Reconcile billed failed/ambiguous writes and paid reads independently; unknown usage or missing result/attribution keeps its reservation held. Cost reconciliation does not resolve provider-effect ambiguity or authorize a retry.

Reports aggregate the same cost_entry_id sets and retain count/hash evidence. They can distinguish availability, event-observation/reconciliation reads, and each booking write kind without putting calendar IDs, attendee identities, descriptions, slots, source spans, raw calendar payloads or recipient-derived hashes into metric labels or usage JSON. Required canonical request/result/usage hashes remain the restricted evidence fields defined above. Cohort/action/strategy/activation attribution stays in restricted relational joins with safe references; shared monthly infrastructure/legal costs may remain outside product cost entries unless a versioned allocation policy is approved, and are never arbitrarily divided per lead.

Hard caps exist by provider call, agent config/suite, workflow run, experiment/campaign, provider/currency daily/monthly, and deployment month. Native AGENT-10 per-case mean/p95/max ceilings remain exact. Alert: one max-cost breach immediately; reservation/cost mismatch or unknown charge at once; 80% account/campaign threshold warning; 100% denies; invoice discrepancy; FX evidence older/missing; daily spend anomaly versus fixed cap—not a learned model. `alon_ai.cost.amount` labels provider/operation/currency only; ILS is derived in reports and not emitted as a second spend metric that could be double summed.

## Commercial and checkpoint cost truth

Attribute each immutable cost and reservation to the authoritative provider/action/run plus experiment, campaign, cohort, agent strategy, GlobalStrategyPackage and StrategyActivation. Before cohorts exist, use EXPERIMENT_BASELINE attribution and retain experiment-level discovery/research/offer costs separately. Never invent a cohort or silently redistribute costs after seeing results. Shared checkpoint/global-evaluation costs retain their triggering checkpoint and frozen allocation rule; cross-campaign reports disclose separately allocated transfer costs and never count the same ledger entry twice.

Include discovery/search/page/business evidence, preliminary qualification, deep research, final qualification, writing, reply evaluation, commercial evaluation, Gmail reads/writes, calendar availability/create/reschedule/cancel/reconciliation, checkpoint evaluation and global-learning model/evaluation costs. Deterministic operations with no provider charge record actual zero only with evidence; unknown provider usage remains reserved/unreconciled. Billed failures/cancellations and ambiguity polling count. Pricing/currency/fee/tax/FX/rounding versions and timestamps remain immutable.

CommercialPolicyEngine alone calculates revenue net of tax, provider/payment fees, delivery costs and contribution margin using the accepted OfferPackage versions. A negotiated discount/scope/pilot/payment schedule must satisfy both minimum net price and margin floor. Inferred budget cannot fill missing cost evidence. Unknown or stale economics makes the affected proposal ineligible; missing reconciliation or OperatorTimeEvidenceV1 verification blocks positive commercial/checkpoint economics rather than imputing zero.

Cost per qualified lead is allocated reconciled experiment/cohort acquisition cost divided by distinct FINAL-qualified leads in the same frozen population. Cost per qualified commitment and per confirmed booking use complete allocated experiment/cohort spend through the same cutoff, divided respectively by distinct evidenced PURCHASE_PROPOSAL commitments and positive confirmed BookingIntents. Count one lead/commitment/booking identity once; reschedules, repeated replies, cancellations and provider retries retain their cost without adding a conversion. Zero denominators return ZERO_DENOMINATOR; missing cost/FX/time or incomplete outcome evidence returns INSUFFICIENT_EVIDENCE with null value.

Reports expose native-currency groups and a separately complete verified ILS projection. Recompute independently from cost-entry ID sets and stored allocation/FX rules. Test split campaigns, pre-cohort costs, promotion/rollback boundaries, cross-campaign reuse, duplicate events, billed failure, cancellation, unavailable pricing and one-minor-unit floor crossings. Cash reservations, provider ceilings and operator time are separate constraints; no checkpoint CONTINUE or strategy PROMOTE increases any budget.

## Ordered implementation tasks

<!-- roadmap-task id=OBS-03-T01 milestone=M3 depends_on=PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,PROVIDER-06-T01,PROVIDER-01-T02,PROVIDER-02-T01,PROVIDER-01-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement currency/price/usage contracts —** Input: exact provider contracts and official price manifests. Operation: freeze integer units/exponents/rounding/effective versions and RFC 8785 evidence. Output: reproducible maximum/actual cost. Test evidence: tier/minimum/cancel/failure/version boundary golden vectors. Failure behavior: provider call denied.
<!-- roadmap-task id=OBS-03-T02 milestone=M3 depends_on=OBS-03-T01,DB-05-T02 mode=parallel locks=backend-domain -->
- [ ] **Implement reservation/reconciliation —** Input: budget account, provider call/result/ledger/price, DB-05's exact allocation branches and existing action attribution. Operation: reserve serially, call, validate same-branch relational/provider/action references, insert one cost and reconcile/release atomically. Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains. Test evidence: concurrency/replay/crash/unknown/overage/zero/retry matrix plus calendar positive allocations, cross-branch splices and missing/wrong attribution negatives. Failure behavior: hold capacity, stop paid work, incident.
<!-- roadmap-task id=OBS-03-T03 milestone=M3 depends_on=OBS-03-T02 mode=parallel locks=backend-domain -->
- [ ] **Implement Bank of Israel FX capture —** Input: original currency/occurred date. Operation: fetch allowlisted official API, verify/capture/normalize/round, store source/date/hash. Output: DB-05 valid ILS evidence. Test evidence: weekend/holiday/100-unit/currency-exponent/rounding/missing/tamper vectors. Failure behavior: no guessed ILS; provider ineligible or reconciliation pending.
<!-- roadmap-task id=OBS-03-T04 milestone=M8 depends_on=OBS-03-T03 mode=serial locks=live-environment,telemetry-catalog -->
- [ ] **Implement reports/alerts/invoice review —** Input: reservations/costs/FX/invoice refs and verified cohort/action/strategy activation joins. Operation: group original currencies, distinguish calendar availability/observation reads from booking write kinds, present separate ILS completeness, compare invoice, and fire hard caps. Output: operator cost control with exact action attribution and no PII leakage. Test evidence: read/write/result/cost ID-set dedupe, cross-cohort/activation denial, unlike currency/discrepancy/80-100% thresholds and calendar-content canaries. Failure behavior: visible incomplete state and no budget increase.
<!-- roadmap-task id=OBS-03-T05 milestone=M8 depends_on=OBS-03-T04,AGENT-10-T01,AGENT-10-T05 mode=serial locks=milestone-gate,telemetry-catalog -->
- [ ] **Reconcile eval and runtime windows —** Input: exact AGENT-10 populations and active config; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: compute native mean/p95/max and rolling triggers from cost rows/provider ledgers; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: promotion/rollback evidence. Test evidence: failed/cancelled billed calls and boundary rounding. Failure behavior: candidate rejects or active config rolls back/pauses.

## Test strategy

- **Money `test_minor_units_decimal_rounding_and_unlike_currency_aggregation_are_exact`.**
- **Atomicity `test_provider_call_has_one_reservation_typed_result_ledger_cost_and_reconciliation`.**
- **Provenance `test_cost_agent_workflow_gmail_and_calendar_shapes_reject_every_cross_branch_splice`:** enumerate all owner-ID null/non-null combinations against DB-05 ck_cost_entries_provenance_shape; positively verify shared/workflow/agent/Gmail/calendar cases, then enforce their exact composite references and governing action attribution.
- **Calendar `test_calendar_read_and_create_reschedule_cancel_costs_have_distinct_calls_and_exact_attribution`:** availability/event-observation reads use the genuine workflow and no send/booking-result IDs; each CREATE/RESCHEDULE/CANCEL positive uses booking_attempt_id, booking_result_id, the same provider_call_id/calendar/action and BOOKING_ACTION attribution; a reconciliation read never duplicates the original write cost.
- **Calendar denial `test_calendar_cost_rejects_cross_branch_partial_result_and_missing_action_attribution`:** splice Gmail or agent/workflow IDs into booking allocation, omit either booking ID, swap result/call/calendar/action, omit action_attribution_id on a product cost, or substitute another action/cohort/offer/activation. Every case rejects before cost insert/reservation release; JSON evidence alone cannot satisfy a missing relational reference.
- **Failure `test_cancel_timeout_ambiguous_retry_and_overage_never_lose_or_clamp_cost`.**
- **FX `test_boi_rate_date_prior_business_day_unit_normalization_and_half_even_ils_match_goldens`.**
- **Invoice `test_invoice_mismatch_opens_discrepancy_without_rewriting_or_negative_alias_entry`.**
- **Evaluation `test_agent10_native_mean_p95_max_and_rolling_windows_use_all_billed_terminal_calls`.**
- **Privacy `test_cost_usage_fx_and_metrics_exclude_prompt_recipient_content_credentials_and_invoice_body`.**

## Security, privacy, compliance, idempotency, observability, and cost

Pricing/FX sources are SSRF-allowlisted, bounded, hashed and signed; invoices are restricted objects. Cost idempotency is provider/call exact. Original currency is authority; stored ILS is evidence-backed reporting. Metric labels are bounded; entry IDs remain logs/report references only. Finance/legal retention is SEC-06 plus accountant/counsel decision and does not extend raw personal data.

## Failure, rollback, and operator recovery

On missing/tampered price/usage/FX, duplicate key, reconciliation split, overage, or invoice mismatch: stop affected paid provider work, retain reservation and provider evidence, open incident, and compare official records. Roll back pricing/config for future calls; never edit usage to lower cost, change FX date after seeing outcome, or raise a cap to clear an incident. Recover with the same idempotent key or registered repair based on exact before/after hashes.

## Acceptance and retained evidence

- [ ] Every paid/possibly billed call has pre-reservation, typed result/ledger, exact original-currency cost, the correct DB-05 allocation branch and required action attribution, and reconciliation.
- [ ] Calendar availability/observation reads and CREATE/RESCHEDULE/CANCEL writes reconcile as distinct provider calls; exact booking-result/action/activation provenance, mixed-branch/missing-attribution rejection and no-PII reporting evidence pass.
- [ ] ILS projection uses normalized dated Bank of Israel evidence and deterministic rounding; missing evidence is visible/denied.
- [ ] Unlike currencies, reservations, actuals, credits/discrepancies and shared costs are never silently mixed.
- [ ] AGENT-10 promotion/runtime cost gates and SEC-05 hard caps reproduce exactly.

Retain price/currency/FX registry versions, official source captures/access dates/hashes, calculation goldens, provider request/result/ledger/cost chains, reservation concurrency/crash traces, invoice reconciliation/discrepancies, dashboards/alerts, eval cost reports, and accountant policy reference.

## Dependencies and next deliverable

OBS-03 supplies cost evidence to [OBS-04](04-agent-and-workflow-evaluations.md), SEC-05 and reports. Passing it unlocks bounded provider use only; budget availability never overrides quality, privacy, compliance, suppression, action authorization or SEND authority.
