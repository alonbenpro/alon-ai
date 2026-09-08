# Sales Funnel, Economics, and Strategy Analytics

**Document ID:** FRONTEND-08
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M7
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-08-T01 <- BACKEND-06-T04,BACKEND-02-T05; FRONTEND-08-T02 <- FRONTEND-08-T01; FRONTEND-08-T03 <- FRONTEND-08-T02,BACKEND-06-T03; FRONTEND-08-T04 <- FRONTEND-08-T03,BACKEND-06-T02,BACKEND-02-T05,BACKEND-01-T09,BACKEND-01-T10`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

Render the funnel from distinct candidates → preliminary-qualified → deeply researched → finally qualified → contacted unique recipients → replies → positive replies → qualified commitments → confirmed bookings → attended calls. Keep proposals, call agreements, purchase commitments and confirmed bookings distinct. A booking requires positive provider evidence, and attendance needs verified evidence. Follow-up messages do not add recipients to the stage denominator.

Every measure carries the server's numerator/denominator, definition/query/evidence-transform version, observation cutoff, cohort, agent strategy version and activation. Show AVAILABLE, ZERO_DENOMINATOR and INSUFFICIENT_EVIDENCE as returned; unavailable inputs are not zero. Unresolved sends/bookings, suppression, missing facts and late observations remain visible attention buckets.

Required panels cover discovery yield/duplicate rate; research coverage/factual accuracy; preliminary/final qualification precision; personalization evidence coverage; delivery/bounce/complaint/reply/positive rates; qualified commitments; objection categories/resolution; negotiation outcomes/discount/margin/scope changes; booking/show rates; cost per qualified lead/commitment/booking; pre/post activation performance; per-agent promotion/rollback rate; and cross-campaign transfer. Use the exact OBS-02/BACKEND-06 formulas and metric definitions, never client arithmetic as authority.

Offer economics and checkpoint success require reconciled provider/research/model/send/calendar/evaluation costs, delivery/fees/taxes/FX/rounding versions and verified OperatorTimeEvidenceV1 where applicable. Display original-currency groups separately from verified ILS projections, reserved/actual/unknown amounts, evidence freshness and missing ledger items. No estimated total can authorize below-floor terms or positive checkpoint economics.

Checkpoint panels display CONTINUE/REVISE/KILL/INCONCLUSIVE/SAFETY_STOP at increments 100/200/300/400 and cumulative 100/300/600/1,000. Global strategy panels display PROMOTE/KEEP/ROLLBACK/INSUFFICIENT_EVIDENCE for every applicable agent, with approved comparison/holdout/transfer/guardrail summaries. The triggering stage is primary evidence; similar campaigns secondary; all relevant history/failures/incidents are guardrails. Comparisons show cohort/selection/definition differences and uncertainty; pre/post correlation is not causal proof. No UI filter modifies a frozen decision or activation.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-08-T01 milestone=M7 depends_on=BACKEND-06-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Render attributed funnel —** Input: BACKEND-06 frozen metric projections. Operation: show distinct recipients, staged qualification, replies/commitments/bookings/attendance with denominators. Output: funnel analytics. Test evidence: zero/missing/unresolved data and call-versus-purchase tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-08-T02 milestone=M7 depends_on=FRONTEND-08-T01 mode=serial locks=frontend-client -->
- [ ] **Render objections and negotiation outcomes —** Input: server aggregate metric definitions and minimized evidence. Operation: display objection/resolution, discount/margin/scope and booking/show outcomes. Output: commercial analytics. Test evidence: unknown cost or outcomes remain unavailable. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-08-T03 milestone=M7 depends_on=FRONTEND-08-T02,BACKEND-06-T03 mode=serial locks=frontend-client -->
- [ ] **Render cost and commercial truth —** Input: OBS-03 reconciled cost/FX/operator-time evidence. Operation: show native currencies and valid ILS totals plus costs per qualified lead/commitment/booking. Output: cost evidence panel. Test evidence: mixed currency, unreconciled cost, missing time and floor boundary cases. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-08-T04 milestone=M7 depends_on=FRONTEND-08-T03,BACKEND-06-T02,BACKEND-02-T05,BACKEND-01-T09,BACKEND-01-T10 mode=serial locks=frontend-client -->
- [ ] **Compare checkpoint and global strategies —** Input: checkpoint bundles and strategy/activation reports. Operation: show frozen decisions, per-agent results, pre/post and cross-campaign transfer with confidence/guardrails. Output: learning analytics. Test evidence: no causal claim from correlation, no mid-cohort mutation or client promotion. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

## Test strategy and acceptance

- [ ] Each displayed state, amount, membership, decision and allowed action comes from an exact generated server DTO and accepted version.
- [ ] Strict unknown-field/schema/version, stale generation, command replay, timeout, auth, privacy and keyboard tests pass against the owning service contract.
- [ ] Automatic sends use fresh ActionAuthorityScopeV1 through SendGateway; calendar writes use BookingGateway. The frontend owns neither capability.
- [ ] Browser fixtures retain safe screenshots/traces, request/response schema hashes, command IDs, server denial evidence and zero unauthorized provider-call counts.
- [ ] This document plans implementation and evidence; it does not claim any product UI or live gate has passed.

## Privacy, failure and recovery

Use redacted no-store projections for conversations/calendar/exception detail and approved minimized learning evidence. Telemetry contains registered outcomes and safe correlation only; no PII/content/credentials, inferred sensitive attributes or provider payloads. Preserve immutable history across refresh, rollback and recovery. Missing contracts block the affected surface until its backend owner supplies them; no browser fallback may invent an operation or bypass policy.

## Dependencies and next deliverable

Consume [canonical sales authority](../00-product-strategy/01-product-scope.md), [API contracts](../06-backend/02-api-contracts.md), [query owners](../06-backend/06-reporting-and-query-services.md), [action authority](../06-backend/05-approval-and-command-handling.md), [booking](../03-workflows/07-booking-workflow.md), [checkpoint evaluation](../03-workflows/08-checkpoint-evaluation-workflow.md) and [global learning](../03-workflows/09-global-learning-workflow.md). Hand retained browser evidence to [TEST-05](../10-testing/05-end-to-end-browser-tests.md); release and live operation remain independently gated.
