# Qualified Call Booking Workflow

**Document ID:** WF-07
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-07-T01 -> WF-07-T02 -> WF-07-T03 -> WF-07-T04`; cross-document task Inputs `WF-07-T01 <- WF-05-T04,PROVIDER-07-T02,ARCH-03-T01,BACKEND-01-T08; WF-07-T02 <- PROVIDER-07-T03; WF-07-T03 <- PROVIDER-07-T04; WF-07-T04 <- LAUNCH-01-T03`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [runtime selection](00-dbos-selection-and-temporal-fallback.md).
**Outputs:** Finite typed inputs/results, immutable artifact/state handoffs, idempotency and recovery evidence
**Unlocks:** Confirmed booking projection and M6/M9 booking evidence
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Booking is a deterministic application/provider boundary, not an agent with calendar credentials. A finally qualified INTERESTED or NEGOTIATING lead may agree to a call without accepting purchase terms. Event writing requires explicit confirmation of one exact timezone-aware slot.

## Current repository state and planned surfaces

No product workflow, persistent artifact/aggregate or provider implementation described here exists. Plan `backend/src/alon_ai/workflows/booking.py` and application-owned command interfaces, fixture/contract tests and durable recovery simulations. Workflows never mutate ORM rows, call concrete adapters or own Gmail/calendar credentials.

## Exact workflow contract

### Booking state and durable action protocol

| Boundary | Input / guard | Result and event |
| --- | --- | --- |
| record intent | accepted OfferPackage, ReplyEvaluation, NegotiationDecision, FINAL qualification, evidenced buying intent and CALL_NEXT_STEP agreement | BookingGateway accepts BookingIntent; booking.intent_recorded.v1; optional purchase reference remains null when absent |
| offer slots | permitted calendar/policy, bounded CalendarReadPort availability | INTENT_RECORDED -> SLOTS_PROPOSED -> CONFIRMATION_PENDING; slot-set hash, IANA timezone/UTC instant/local label, availability expiry |
| confirm | explicit lead source span accepting an exact slot with timezone | CONFIRMED; booking.slot_confirmed.v1; ambiguous agreement cannot confirm |
| create attempt | fresh identity, current offer/context/conversation, availability, slot expiry, notification policy, limits/kill/generation and ActionAuthorityScopeV1 | durable action/attempt with stable calendar/action identity before provider call; CONFIRMED -> CREATING |
| provider truth | positive create result or exact reconciled observation | BOOKED; booking.confirmed.v1 and conversation BOOKED; attach business/contact/campaign/conversation/offer/evidence refs to dashboard |
| uncertainty | timeout/disconnect/malformed success/conflict | AMBIGUOUS -> RECONCILING; retain action kind, prior state and expected event identity; no blind retry |
| reschedule | explicit new slot confirmation plus fresh availability/policy | independent RESCHEDULE action/version/key; RESCHEDULE_PENDING -> BOOKED only with positive event evidence |
| cancel | explicit lead request or authorized operator/policy reason | independent CANCEL action/version/key; CANCEL_PENDING -> CANCELLED only with positive provider evidence |

Google Calendar is the first adapter behind separate CalendarReadPort/CalendarWritePort. Only BookingGateway receives CalendarWritePort and may create/reschedule/cancel. Availability is a read observation, never a reservation or confirmation. A conflicting/stale slot causes a new bounded proposal through the writer and guarded send flow; it cannot silently pick another time.

IANA timezone ID, local wall time, UTC instant, offset, duration and timezone-database version are persisted. DST nonexistent or repeated local times require unambiguous offset/instant confirmation. Notification mode/attendees are part of action/content hash; replay must not issue duplicate invitations. Sales outreach ends at BOOKED; explicit scheduling changes do not reopen persuasion.

### Idempotency, pause and reconciliation

Keys bind booking intent, action kind/version, calendar and deterministic provider event identity. One durable attempt precedes each write; duplicate callbacks deduplicate on calendar/provider event/change identity. Serialize writes with calendar-side-effects and expected event version/ETag. A provider conflict pauses into exception and refreshes only through read reconciliation.

Pause/cancel first denies new writes and invalidates stale authority. It cannot treat a started CREATE as absent or send an unchecked compensating CANCEL. Any unresolved write remains AMBIGUOUS/RECONCILING; absence or conflicting observations cannot authorize retry. EXPIRED/FAILED require proof no unresolved write exists. Reconciliation records whether CREATE, RESCHEDULE or CANCEL succeeded and preserves historical accepted slots. BookingGateway owns transitions; workflow timers can only request commands.

## Ordered implementation tasks

<!-- roadmap-task id=WF-07-T01 milestone=M6 depends_on=WF-05-T04,PROVIDER-07-T02,ARCH-03-T01,BACKEND-01-T08 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Encode booking intent and state guards —** Input: canonical BookingIntent/BookingState and fixture-backed BookingGateway interface. Operation: bind qualification, buying intent, call agreement, offer/strategy/activation and optional purchase acceptance separately. Output: finite booking coordinator contract. Test evidence: call without purchase succeeds; no qualification/agreement fails. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-07-T02 milestone=M6 depends_on=WF-07-T01,PROVIDER-07-T03 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Implement slot proposal and confirmation —** Input: bounded availability and booking policy. Operation: persist labelled slot-set/expiry and require exact explicit confirmation. Output: confirmed intent with immutable evidence. Test evidence: timezone/DST/ambiguous agreement/stale availability tests. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-07-T03 milestone=M6 depends_on=WF-07-T02,PROVIDER-07-T04 mode=serial locks=calendar-side-effects,workflow-runtime -->
- [ ] **Implement guarded create/change recovery —** Input: BookingGateway action authorization and provider fixtures. Operation: request idempotent CREATE/RESCHEDULE/CANCEL and reconcile accepted/ambiguous outcomes. Output: booking state and provider evidence chain. Test evidence: crash every boundary, duplicate callback, notification and ETag conflict. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-07-T04 milestone=M6 depends_on=WF-07-T03,LAUNCH-01-T03 mode=serial locks=calendar-side-effects,workflow-runtime,milestone-gate,live-environment -->
- [ ] **Retain owned-calendar M6 proof —** Input: complete isolated pilot entry and dedicated test calendar/attendees. Operation: execute explicitly confirmed test booking, reschedule and cancel. Output: signed booking gate evidence. Test evidence: one event/change per action with exact timezone and no real demand claim. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.

## Test strategy

Contract tests cover exact accepted-artifact version/hash lineage and state ownership. Real isolated PostgreSQL tests inject failure before/after each aggregate/artifact/event/audit/outbox/idempotency transaction. Recorded providers and owned-resource gates cover duplicate/out-of-order delivery, cancellation, stale generation and ambiguity. Required scenarios appear per task; no fake/synthetic evidence counts as real demand.

## Safety, privacy, compliance, observability and cost

Every run pins schema/configuration, producer strategy, GlobalStrategyPackage/StrategyActivation, deadline and finite attempt/tool/token/cost ceilings. Application services reserve paid-call budgets before execution and reconcile all usage. Retention follows DB-06 per record/field purpose and sensitivity; minimized evidence is required before learning reuse.

Telemetry includes safe IDs, hashes, versions, counts, durations, outcomes and costs. It excludes raw recipients, message/calendar content, sensitive budget spans, credentials and hidden reasoning. Source and email content are untrusted data; deterministic legal/provider/suppression/commercial gates and scoped write ports remain mandatory.

## Failure, rollback, recovery and acceptance

Pause closes admission before acknowledgement and retains the exact resume target, accepted inputs, counters/capacity and control generation. Cancel drains only provably uncalled work; uncertain external outcomes remain quarantined with durable evidence. Terminal runs never resume. A valid failed-stage retry creates a new linked finite run; changed inputs create superseding artifacts outside active cohorts.

- [ ] Every boundary has a named deterministic owner and accepted version/hash input.
- [ ] No workflow has direct Gmail/calendar write authority or routine per-message approval.
- [ ] Every replay, pause, terminal stop and ambiguous outcome has a finite coordinator outcome with no blind retry.
- [ ] Cohort and strategy boundaries preserve capacity, immutable evidence and historical attribution.
- [ ] Required contract/recovery/gate evidence is retained before later product use.

Retain schema/transition snapshots, command/artifact/activation lineage, source/provider fixture hashes, full crash matrices, safe audit/event traces, cost reconciliation and gate results.
