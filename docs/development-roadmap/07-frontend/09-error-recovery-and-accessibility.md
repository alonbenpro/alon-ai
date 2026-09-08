# Accessible Recovery, Calendar, and Safety Boundaries

**Document ID:** FRONTEND-09
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M7, M8
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-09-T01 <- BACKEND-06-T04,BACKEND-02-T05; FRONTEND-09-T02 <- FRONTEND-09-T01,BACKEND-04-T04,BACKEND-02-T05; FRONTEND-09-T03 <- FRONTEND-09-T02,SEC-05-T04; FRONTEND-09-T04 <- FRONTEND-09-T03,BACKEND-02-T05; FRONTEND-09-T05 <- FRONTEND-09-T04,FRONTEND-01-T04,FRONTEND-02-T04,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-03-T01,FRONTEND-03-T02,FRONTEND-03-T04,FRONTEND-08-T01,FRONTEND-08-T02,FRONTEND-08-T03,FRONTEND-03-T05,FRONTEND-08-T04,FRONTEND-01-T05,FRONTEND-03-T03,WF-07-T04,WF-08-T04,WF-09-T04`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

RecoveryOverviewItemV1 includes WORKFLOW_RUN, COMMAND, SEND_ATTEMPT, CURSOR_INCIDENT, REPAIR_ACTION, BOOKING_ACTION, CHECKPOINT and STRATEGY_ACTIVATION. Render each exact safe record/state/reason/attention time, offer/cohort/strategy/activation attribution and only its permitted typed next command. There is no generic CRUD repair panel, raw SQL console or direct Gmail/calendar write control.

On a command timeout, preserve the logical idempotency key, expected version and request hash; query or replay through the same handler. A 409/412/428 conflict requires fresh canonical state and a separately authorized intent, never auto-retargeting. Unresolved provider acceptance stays AMBIGUOUS/RECONCILING; zero Gmail or calendar observations do not prove absence. Restored data, stale control generations and lost cursors cannot reopen admission.

A disable/pause acknowledgement reflects committed fencing across SendGateway and BookingGateway call entry. The UI distinguishes requested, effective, and unresolved results; it never claims a send/event was stopped after provider call entry. Re-enable, exception resolution, booking reconciliation and strategy rollback are separate server operations. Rollback blocks future actions, closes the affected checkpoint, and activates only at a compatible boundary; it never rewrites history or refreshes a running cohort.

Use semantic headings/tables/forms, labelled controls, visible focus, error summaries connected to fields, live regions for meaningful state changes, sufficient contrast, reduced motion and keyboard-complete dialogs. Status is not color alone. Calendar has a keyboard list alternative; timezone, offset, DST ambiguity, duration, expiry, confirmation and notification state are textual. Keep focus stable during polling and return it on dialog closure.

All product data requires the opaque FastAPI operator session. Unknown auth/session state suspends queries; logout/expiry clears caches and sensitive previews. Public unsubscribe stays the isolated FastAPI two-operation boundary. Do not cache raw threads, exception previews or calendar detail; safe query keys contain opaque IDs and registered filters only. Routes, errors, screenshots, browser traces and telemetry exclude recipient identities, message bodies, budget spans, tokens and calendar descriptions.

Browser tests must directly forge hidden buttons, local state, DTO fields, expected generation, campaign membership, price, slot confirmation and strategy activation requests. Server rejection, zero bypassed provider writes and retained audit evidence are the pass condition. Responsive visual checks alone cannot establish safety.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-09-T01 milestone=M7 depends_on=BACKEND-06-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Render expanded recovery union —** Input: getRecoveryOverview and safe generated discriminated unions. Operation: support workflow/command/send/cursor/repair/booking/checkpoint/strategy cases. Output: typed recovery view. Test evidence: unknown kinds and stale snapshots fail visibly. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-09-T02 milestone=M7 depends_on=FRONTEND-09-T01,BACKEND-04-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement provider recovery commands —** Input: existing send/calendar reconciliation and repair owners. Operation: submit one logical command then refetch canonical outcome on timeout. Output: recovery command adapter. Test evidence: zero search result, duplicate callback and ambiguous write cannot retry. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-09-T03 milestone=M7 depends_on=FRONTEND-09-T02,SEC-05-T04 mode=serial locks=frontend-client -->
- [ ] **Implement kill and boundary rollback UX —** Input: server controls/generations and stored rollback rules. Operation: show effective admission fence and pending pause/closure/rollback until server acknowledgment. Output: safety-control view. Test evidence: kill races, terminal state and active-cohort rollback tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-09-T04 milestone=M7 depends_on=FRONTEND-09-T03,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement auth/privacy/error boundaries —** Input: BACKEND-02 errors and private-session contracts. Operation: handle session expiry, 409/412/428, unavailable dependencies, safe retry and no-store data. Output: accessible failure states. Test evidence: browser bypass, cache/logout, redaction and hostile text tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-09-T05 milestone=M8 depends_on=FRONTEND-09-T04,FRONTEND-01-T04,FRONTEND-02-T04,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-03-T01,FRONTEND-03-T02,FRONTEND-03-T04,FRONTEND-08-T01,FRONTEND-08-T02,FRONTEND-08-T03,FRONTEND-03-T05,FRONTEND-08-T04,FRONTEND-01-T05,FRONTEND-03-T03,WF-07-T04,WF-08-T04,WF-09-T04 mode=serial locks=frontend-client -->
- [ ] **Verify every operator journey —** Input: all frontend views plus implemented booking/checkpoint/learning owners. Operation: exercise desktop/mobile keyboard/screen-reader and full synthetic campaign across routes. Output: M8 accessible browser evidence bundle. Test evidence: full simulation, timezone/DST, exception correction and no provider-write capability. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

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
