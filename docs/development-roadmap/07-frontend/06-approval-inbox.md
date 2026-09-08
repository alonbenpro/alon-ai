# Exception and Incident Queue

**Document ID:** FRONTEND-06
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M7
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-06-T01 <- BACKEND-02-T05; FRONTEND-06-T02 <- FRONTEND-06-T01,SEC-02-T04,BACKEND-02-T05; FRONTEND-06-T03 <- FRONTEND-06-T02; FRONTEND-06-T04 <- FRONTEND-06-T03`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

The stable FRONTEND-06 ID and historical filename are retained for dependency compatibility; the product surface is /exceptions. Routine in-envelope drafts, replies, negotiations and bookings proceed after deterministic checks without waiting in this queue. There are no routine approve/deny-message buttons or local action-authority construction.

Queue cases include ambiguous/unsafe reply intent, unsupported facts, stale evidence, out-of-envelope price/margin/scope/payment/legal proposals, expired offer, unknown identity/suppression scope, Gmail or calendar uncertainty, incomplete checkpoint costs/evidence, incompatible strategy activation and failed rollback. Display exact server severity/reason, affected safe IDs, current generation, owner, expiry, required correction command and linked incident. The queue does not invent new incident enums.

getException and redacted timeline are ordinary private reads. getExceptionSensitivePreview uses step-up, explicit inspection purpose, exact materialization scope/hash, expiry and receipt. It is no-store, never a share/export/preload target and clears on blur/logout/expiry. Browser caches, URLs, history, analytics, error details, screenshots and traces must exclude raw contact/message/calendar/budget/credential data.

resolveException references the completed authorized correction command and evidence plus expected state. It cannot bypass a deterministic gate, forge consent, remove suppression, lower minimum economics, mutate a running cohort, promote a strategy or mark a provider action successful. Unsupported legal-policy changes use the protected authority; missing approval/evidence remains blocked. Resolution alone neither re-enables controls nor sends a message.

Recovery commands are pauseConversation, permitted system/campaign controls, reconcileSendAttempt, reconcileBookingAction and requestStrategyRollback through their existing owners. Reconciliation is read evidence collection, never an unconditional retry. Re-enable is a separate typed safety decision after fresh eligibility; the UI only renders its result.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-06-T01 milestone=M7 depends_on=BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Render exception queue —** Input: listExceptions/getExceptionQueueReport and exact incident catalog. Operation: display open/blocked/expired/resolved cases with scope, safe reasons, owner and required correction. Output: exception queue replacing legacy approval navigation. Test evidence: pagination, stale generation and severity routing tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-06-T02 milestone=M7 depends_on=FRONTEND-06-T01,SEC-02-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement purpose-bound sensitive inspection —** Input: getExceptionSensitivePreview and SEC-02 step-up session. Operation: request only necessary fields with purpose, expiry and no-store receipt. Output: restricted exception inspector. Test evidence: auth/CSRF/purpose/expiry/cache/logging denial tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-06-T03 milestone=M7 depends_on=FRONTEND-06-T02 mode=serial locks=frontend-client -->
- [ ] **Resolve through deterministic corrections —** Input: resolveException with expected state and correction/evidence refs. Operation: invoke the named correction owner then resolve only when server guards pass. Output: auditable correction workflow. Test evidence: cannot waive suppression/economics/caps or create action authority. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-06-T04 milestone=M7 depends_on=FRONTEND-06-T03 mode=serial locks=frontend-client -->
- [ ] **Verify queue and safety actions —** Input: pause/reconcile/control/incident operations. Operation: link exceptions to conversation, send, booking, checkpoint and strategy recovery. Output: M7 queue acceptance evidence. Test evidence: ambiguous outcomes remain quarantined and resolving never resumes automatically. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

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
