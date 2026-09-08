# Conversation, Negotiation, and Booking Timeline

**Document ID:** FRONTEND-07
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M7
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-07-T01 <- BACKEND-02-T05; FRONTEND-07-T02 <- FRONTEND-07-T01,BACKEND-02-T05; FRONTEND-07-T03 <- FRONTEND-07-T02,BACKEND-05-T03,BACKEND-02-T05; FRONTEND-07-T04 <- FRONTEND-07-T03,BACKEND-04-T04,WF-06-T04,BACKEND-02-T05,BACKEND-01-T08,WF-07-T03`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

getConversation returns the complete ordered sanitized conversation, not a lossy summary masquerading as evidence. Pages pin conversation version/cutoff and use server ordering (ordinal, conversation_message_id). Each message, reply evaluation, proposal/decision, action and booking preserves offer, cohort, agent strategy and activation. Missing/deleted/withheld source content is visibly unavailable; never synthesize it.

Show INTERESTED → NEGOTIATING → COMMITTED → BOOKED as the purchase-acceptance path, including BOOKING_PENDING where canonical state requires it. COMMITTED requires explicit PURCHASE_PROPOSAL acceptance of exact terms. A qualified INTERESTED or NEGOTIATING lead may instead agree to CALL_NEXT_STEP and book without purchase acceptance; this path does not pass through COMMITTED or emit negotiation.accepted.v1. Availability is not confirmation; ambiguous agreement is not a confirmed slot.

Any inbound reply atomically stops the cold sequence. Positive replies, questions and genuine objections can enter the bounded response loop. Display current objective, reply/round/message/frequency/time limits and remaining budget. A clear rejection terminates persuasion; DECLINED, OPTED_OUT and CLOSED cannot be automatically reopened. Durable suppression requires independently evidenced EXPLICIT_OPT_OUT, COMPLAINT, HARD_BOUNCE, SOFT_BOUNCE_LIMIT_REACHED or LEGAL_STOP. An ordinary rejection or negative sentiment alone does not permanently suppress. BOOKED ends sales outreach; scheduling changes have separate authority.

Negotiation proposals remain proposals until explicitly accepted. Display permitted explanation/objection/variant/pilot/discount/timing/bundle/payment/call objective, server-calculated net/tax/gross/fees/cost/contribution/margin and exact rule/FX/rounding versions. Only STATED budget satisfies a stated-budget predicate. INFERRED/UNKNOWN never become stated, and sensitive source spans require the exception inspector. Unsupported claims, false urgency/familiarity, unauthorized legal terms/deliverables and floor violations block the action.

The send timeline distinguishes planned draft, immutable authorization, intent, reserved/attempted send, positive provider acceptance, ambiguity and reconciliation. Writer has no send port; SendGateway alone writes Gmail with fresh policy/evidence/identity/version/generation checks. Zero history/search results never prove non-send. A new reply or kill switch does not rewrite a possibly-called attempt as cancelled.

Calendar views show bounded availability with UTC instant, IANA zone, UTC offset, tzdb version, duration and expiry, plus explicit lead confirmation. BookingGateway alone creates/reschedules/cancels events after fresh availability, identity, offer and conversation checks. Render provider event ID as safe opaque reference, notification mode/count and pending CREATE/RESCHEDULE/CANCEL outcome. requestBookingReschedule consumes existing confirmation/slot/hash; browser slot clicks cannot manufacture confirmation. An ambiguous write must reconcile before another write. Dashboard links preserve business/contact/campaign/conversation/offer/evidence context without leaking attendees or calendar descriptions.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-07-T01 milestone=M7 depends_on=BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Render complete ordered conversation —** Input: getConversation and timeline projections. Operation: display sanitized full thread ordered by server ordinal/ID with pinned version/cutoff. Output: conversation timeline. Test evidence: pagination never drops intervening messages; unavailable bodies remain explicit. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-07-T02 milestone=M7 depends_on=FRONTEND-07-T01,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Explain replies and commercial decisions —** Input: ReplyEvaluation, NegotiationDecision and governing offer. Operation: show objective, classifications, counters, deterministic terms and evidence. Output: negotiation inspector. Test evidence: STATED/INFERRED/UNKNOWN, rejection and unsupported-claim cases. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-07-T03 milestone=M7 depends_on=FRONTEND-07-T02,BACKEND-05-T03,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Explain automatic sending and booking —** Input: ActionAuthorityScopeV1, send blocks and booking projections. Operation: show authorization/intent/attempt/observation/result chain and timezone-labelled slots. Output: action/booking timeline. Test evidence: read-only UI cannot send; call agreement cannot become purchase acceptance. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-07-T04 milestone=M7 depends_on=FRONTEND-07-T03,BACKEND-04-T04,WF-06-T04,BACKEND-02-T05,BACKEND-01-T08,WF-07-T03 mode=serial locks=frontend-client -->
- [ ] **Implement safe timeline recovery —** Input: typed pause/send/calendar reconciliation and scheduling commands. Operation: reconcile unknown outcomes, reschedule only from existing explicit confirmation, cancel with evidence. Output: guarded timeline actions. Test evidence: duplicate callback, DST, ETag, notification and timeout/replay browser cases. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

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
