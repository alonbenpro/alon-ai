# Provider Cost Accounting, Budgets, and ILS Evidence

**Document ID:** OBS-03
**Status:** Planned M3-M8 provider-cost ledger; no live providers, reservations, cost entries, invoices, FX capture, or cost dashboards exist today
**Milestone:** M3 agent/provider gates, M6 Gmail/budget reconciliation, M7 analytics, M8 operations
**Owner:** Solo operator
**Prerequisites:** [DB-01 budgets](../02-database/01-core-data-model.md), [DB-05 `cost_entries`](../02-database/05-audit-events-and-idempotency.md), [AGENT-01 provider meta/ledger](../04-agents/01-agent-runtime-and-contracts.md), [AGENT-10 eval costs](../04-agents/10-agent-evals-and-versioning.md), six provider contracts, BACKEND-03, SEC-05, and OBS-01/02
**Outputs:** Original-currency cost ledger, reservation/reconciliation protocol, immutable pricing/usage evidence, Bank of Israel ILS projection, discrepancy handling, budgets/alerts, and tests
**Unlocks:** Cost-gated provider calls, M7 cost reports, agent promotion/cost rollback, and M8 financial operations
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Every paid provider call reserves a conservative maximum before network access and reconciles exactly once to a DB-05 `cost_entries` row using the provider's original currency and immutable usage/pricing evidence. ILS is a separate reporting projection with dated source evidence; it never replaces original-currency truth or silently mixes amounts. Unknown cost or missing FX evidence keeps reservations held, blocks further paid work at the bound, and becomes visible.

The FX source is the Bank of Israel [representative exchange-rate service](https://www.boi.org.il/en/economic-roles/financial-markets/exchange-rates/) and [series/API extraction guidance](https://www.boi.org.il/information/bank-paymnts/guide/api-guide/), accessed 2026-08-29. The Bank states representative rates are indicative and not legally binding; Alon AI uses them only as a documented product reporting policy. Counsel/accountant decides accounting/tax books and any different statutory rate.

## Current repository state

No provider is called. `ProviderResultMetaV1` plans tokens, original `cost_minor`, and currency; DB-01/05 plans accounts/reservations/cost rows; AGENT-10 defines per-suite native cost thresholds. None is implemented. There is no price catalog, usage capture, FX client/cache/evidence, invoice reconciliation, budget dashboard, cost alert, or ILS calculation. Gmail sends currently do not occur and Gmail API fee must not be assumed to represent the full mailbox/reputation/hosting cost.

## Scope and non-goals

In scope: model/search/page/business/Gmail/OIDC/monitoring/storage/KMS provider operation cost where attributable; original currency/minor-unit registries; estimates/reservations/actuals; pricing versions; usage; retries/cancelled/failed/ambiguous calls; FX/ILS evidence; invoice discrepancy; experiment/workflow/agent/send linkage; dashboards/alerts; and retention.

Non-goals: browser FX lookup, floating-point money, adding unlike currencies, retroactively rewriting usage to match an invoice, ignoring failed-call charges, counting reservations as spend, assuming free-tier permanence, optimizing cost by weakening quality/safety, or treating ILS representative rate as transaction/accounting truth.

## Exact planned implementation surfaces

Create `costs/contracts.py`, `costs/currency.py`, `costs/pricing.py`, `costs/fx.py`, `application/provider_costs.py`, provider usage adapters, reconciliation jobs, and tests. `BudgetService` exclusively writes `budget_accounts`/`budget_reservations`; `ProviderCostReconciliationService` exclusively writes/updates `cost_entries` under the DB-05 contract. Reports use BACKEND-06; frontend never calculates.

### Exact ledger and evidence contract

`cost_entries` remains byte-for-byte DB-05: `cost_entry_id`; provider/operation and mandatory UUID `provider_call_id`; experiment plus optional workflow/agent/send-attempt/provider-result IDs under the four closed provenance shapes; usage schema/JSON/hash; nonnegative `amount_minor`; ISO currency; ILS reporting amount/rate/source/date; invoice ref; occurred/recorded UTC; and provider/call/idempotency uniqueness. Do not add an alias ledger.

`ProviderUsageEvidenceV1` stored in `usage_json` is strict and capability-specific but always includes: `schema_version`; provider/capability/operation; the same UUID `provider_call_id` as the relational column and provider idempotency key; safe request ID where permitted; request/result schema versions and hashes; price-catalog ID/version/hash/effective time; usage units as nonnegative integers with unit enums; original-currency exponent; estimated/reserved/actual calculation components; outcome; started/finished UTC; retry/fixture mode; and source capture/invoice reference hashes. No prompt, query, URL, recipient, content, token, provider payload, secret, or raw invoice enters the row.

`usage_hash` is DB-01 lowercase SHA-256 of RFC 8785 UTF-8 `{"schema_version":version,"payload":payload}` and is verified against provider ledger before insert/use. `idempotency_key` is the lowercase canonical UUID text of `provider_call_id`; same provider/call can create one cost row. Agent allocation requires the exact DB-04 agent/experiment/workflow composite. Gmail allocation preserves the distinct call and attempt UUIDs from its frozen request/result contract, requires the same experiment, and targets the exact DB-03 `(provider_result_id,send_attempt_id,provider_call_id,provider)` tuple while forbidding workflow/agent duplication. Cancelled, failed, timed-out, refused, ambiguous, and retried calls with billed usage remain costs. A zero amount is recorded only when a versioned price catalog/provider invoice proves zero; absence is not zero.

Price catalogs are immutable signed manifests captured from official provider pricing/contract sources with access/effective date, currency, unit/exponent, tiers, rounding/minimum, taxes/credits treatment, model/operation region, and expiry/review. A price change creates a new version; provider calls are denied when no current catalog covers the exact operation. Provider-reported charged amount wins only when its semantics/currency/call identity are verified; otherwise compute from immutable usage and catalog and mark invoice reconciliation pending.

### Reservation and reconciliation sequence

1. Freeze provider request, exact price version, max tokens/results/bytes/time/calls, original currency and worst-case amount using integer/Decimal arithmetic.
2. In a serializable transaction, `BudgetService` locks the exact account/currency and open reservations, denies insufficient capacity, and inserts one `RESERVED` row keyed to the provider call. Do not convert another currency to create capacity.
3. Execute the provider call outside the transaction. Capture exact typed result and provider ledger even on failure/cancel/timeout where any charge is possible.
4. Obtain dated FX evidence required by DB-05. `ProviderCostReconciliationService` verifies request/result/usage/price hashes and inserts one cost row; links the reservation as `RECONCILED`; releases unused reservation capacity atomically. Actual over reservation is inserted honestly, opens `COST_CAP_EXCEEDED` incident/alert, and blocks new calls; never clamp.
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

Every entry links to exactly one narrowest authoritative shape: agent run plus its workflow/experiment for six capabilities; send attempt plus exact provider result for attributable Gmail/send fees; workflow-only when no agent owns the call; or operation-only for shared infrastructure. Workflow and agent are deliberately null on the send shape, and send/result are null on the agent shape, so same-experiment rows cannot manufacture cross-run attribution. Reports aggregate the same entry IDs and include ID-set/count/hash evidence. Shared monthly infrastructure/legal costs may remain outside product cost entries unless a versioned allocation policy is approved; they are never arbitrarily divided per lead.

Hard caps exist by provider call, agent config/suite, workflow run, experiment/campaign, provider/currency daily/monthly, and deployment month. Native AGENT-10 per-case mean/p95/max ceilings remain exact. Alert: one max-cost breach immediately; reservation/cost mismatch or unknown charge at once; 80% account/campaign threshold warning; 100% denies; invoice discrepancy; FX evidence older/missing; daily spend anomaly versus fixed cap—not a learned model. `alon_ai.cost.amount` labels provider/operation/currency only; ILS is derived in reports and not emitted as a second spend metric that could be double summed.

## Ordered implementation tasks

- [ ] **Implement currency/price/usage contracts —** Input: exact provider contracts and official price manifests. Operation: freeze integer units/exponents/rounding/effective versions and RFC 8785 evidence. Output: reproducible maximum/actual cost. Test evidence: tier/minimum/cancel/failure/version boundary golden vectors. Failure behavior: provider call denied.
- [ ] **Implement reservation/reconciliation —** Input: budget account, provider call/result/ledger and price. Operation: reserve serially, call, insert one cost and reconcile/release atomically. Output: complete cost chain. Test evidence: concurrency/replay/crash/unknown/overage/zero/retry matrix. Failure behavior: hold capacity, stop paid work, incident.
- [ ] **Implement Bank of Israel FX capture —** Input: original currency/occurred date. Operation: fetch allowlisted official API, verify/capture/normalize/round, store source/date/hash. Output: DB-05 valid ILS evidence. Test evidence: weekend/holiday/100-unit/currency-exponent/rounding/missing/tamper vectors. Failure behavior: no guessed ILS; provider ineligible or reconciliation pending.
- [ ] **Implement reports/alerts/invoice review —** Input: reservations/costs/FX/invoice refs. Operation: group original currencies, present separate ILS completeness, compare invoice, and fire hard caps. Output: operator cost control. Test evidence: ID-set dedupe/unlike currency/discrepancy/80-100% thresholds. Failure behavior: visible incomplete state and no budget increase.
- [ ] **Reconcile eval and runtime windows —** Input: exact AGENT-10 populations and active config. Operation: compute native mean/p95/max and rolling triggers from cost rows/provider ledgers. Output: promotion/rollback evidence. Test evidence: failed/cancelled billed calls and boundary rounding. Failure behavior: candidate rejects or active config rolls back/pauses.

## Test strategy

- **Money `test_minor_units_decimal_rounding_and_unlike_currency_aggregation_are_exact`.**
- **Atomicity `test_provider_call_has_one_reservation_typed_result_ledger_cost_and_reconciliation`.**
- **Provenance `test_cost_agent_workflow_and_send_result_call_shapes_reject_every_cross_run_splice`.**
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

- [ ] Every paid/possibly billed call has pre-reservation, typed result/ledger, exact original-currency cost, linkage and reconciliation.
- [ ] ILS projection uses normalized dated Bank of Israel evidence and deterministic rounding; missing evidence is visible/denied.
- [ ] Unlike currencies, reservations, actuals, credits/discrepancies and shared costs are never silently mixed.
- [ ] AGENT-10 promotion/runtime cost gates and SEC-05 hard caps reproduce exactly.

Retain price/currency/FX registry versions, official source captures/access dates/hashes, calculation goldens, provider request/result/ledger/cost chains, reservation concurrency/crash traces, invoice reconciliation/discrepancies, dashboards/alerts, eval cost reports, and accountant policy reference.

## Dependencies and next deliverable

OBS-03 supplies cost evidence to [OBS-04](04-agent-and-workflow-evaluations.md), SEC-05 and reports. Passing it unlocks bounded provider use only; budget availability never overrides quality, privacy, compliance, suppression, approval or SEND authority.
