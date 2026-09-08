# Calendar Availability, Event Writes, and Reconciliation

**Document ID:** PROVIDER-07
**Status:** Planned fixture-first provider; no calendar integration exists
**Milestone:** M3, M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PROVIDER-07-T01 -> PROVIDER-07-T02 -> PROVIDER-07-T03 -> PROVIDER-07-T04`; cross-document task Inputs `PROVIDER-07-T01 <- ARCH-02-T01,ARCH-03-T01; PROVIDER-07-T03 <- SEC-02-T04,SEC-03-T01`. Source authorities: [ARCH-02 ports](../01-architecture/02-module-boundaries.md), [booking states](../01-architecture/03-domain-events-and-state-machines.md#booking-states), [WF-07](../03-workflows/07-booking-workflow.md).
**Outputs:** Separate CalendarReadPort and CalendarWritePort, first Google Calendar adapter, typed fixtures and booking reconciliation evidence
**Unlocks:** WF-07 owned-calendar booking proof
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Google Calendar is the first planned adapter behind product-owned neutral contracts. CalendarReadPort reads bounded availability/events. Only BookingGateway receives CalendarWritePort and creates, reschedules or cancels events. No agent, workflow, API route, generic provider wrapper or frontend receives a calendar client with hidden write methods.

M3 implements neutral ports/recorded fixtures with network and credentials disabled. M6 composes server-owned least-scope credentials and validates the adapter using fake HTTP before isolated live calls. WF-07 owns the later complete test-calendar acceptance gate; real recipients/attendees still require later launch authority.

## Current repository state and implementation surfaces

No calendar provider, availability service, booking gateway, OAuth scope, event record, callback, fixture or integration exists. Plan `providers/calendar/contracts.py`, `providers/calendar/google_calendar.py`, `providers/calendar/fixtures.py` and application-owned booking/availability/reconciliation interfaces. Provider DTOs cannot become business-state writers.

## Exact capability contract

All DTOs are strict/frozen/extra-forbid. Every request carries schema/operation version, call ID, authorized calendar ID, deadline, correlation and governing booking/action refs. Every result has SUCCESS/FAILURE discriminator, provider request ID when present, received/observed timestamps, safe outcome/error, payload/schema/hash on success, and usage/cost/observation refs. Request/result hashes use DB-01 RFC 8785 envelopes. Provider-native types and credentials stay inside the adapter.

| Port/method | Request fields in addition to common context | Result / bound |
| --- | --- | --- |
| CalendarReadPort.get_availability | allowed calendar IDs (1..5), UTC start/end within 30 days, IANA timezone, duration/minimum notice/buffer/policy versions | busy/available intervals, timezone-database version, observed time and expiry; max 100 slots; default/max 10/20 seconds |
| CalendarReadPort.get_event_observation | exact calendar/event ID or one immutable action reconciliation key, expected action kind/version | present/absent/conflicting observation with event ID/version/ETag, slot/attendee/notification hashes and source evidence; default/max 5/15 seconds |
| CalendarWritePort.create_event | BookingIntent ref, CREATE action/attempt IDs/version, ActionAuthorityScopeV1/hash, stable provider event identity, explicitly confirmed slot/hash, permitted attendees/notification mode and offer/strategy/activation/generation refs | accepted event ID/version and matching slot/attendee hash; default/max 15/30 seconds |
| CalendarWritePort.reschedule_event | RESCHEDULE action/attempt/version/key, existing event ID/expected version, new explicit slot confirmation, fresh policy/context and notification hash | accepted new event version/slot or typed conflict/ambiguity; default/max 15/30 seconds |
| CalendarWritePort.cancel_event | CANCEL action/attempt/version/key, event ID/expected version, lead-request or authorized operator/policy reason and notification hash | positive cancellation observation or typed conflict/ambiguity; default/max 15/30 seconds |

Read-only capability requests contain no provider write method. Write DTOs are materialized only from a durable BookingGateway attempt; adapter identity/context mismatch fails before credential access. Availability reads do not reserve a slot. Before every write the gateway freshly rechecks identity, offer/context, conversation/qualification, availability/confirmation, source policy, expiry, counters/budget and all kill switches.

## Timezones, confirmation and event lifecycle

BookingIntent retains qualified buying-intent and explicit CALL_NEXT_STEP agreement independently of optional PURCHASE_PROPOSAL acceptance. INTERESTED/NEGOTIATING leads may book a discussion without purchase commitment. Every actual event create/reschedule requires exact explicit slot confirmation; vague agreement cannot authorize a write.

Store UTC start/end, IANA timezone, local label, UTC offset, duration and timezone-database version. Reject nonexistent DST local times; resolve repeated wall times with explicit instant/offset. Propose a fresh slot when stale/conflicting, never silently choose another time. Cancellation requires a separate explicit request or authorized operator/policy reason; it does not erase history.

Attendee identities and notification behavior are explicit hashed request fields. Default isolated tests use owned attendees and the declared test notification mode. Changing notification mode invalidates prior action authority. An accepted booking never triggers another invitation on duplicate callback or replay. Calendar descriptions contain only minimized authorized business context and never hidden prompts or sensitive budget inferences.

## Idempotency and ambiguity

Serialize mutation under `calendar-side-effects` and expected provider version/ETag. Persist one action kind/version/key and immutable attempt before network; use stable provider event identity and provider-supported conditional/idempotency mechanisms verified by contract tests. Do not promise generic exactly-once provider behavior.

Positive exact provider evidence commits BOOKED/rescheduled/CANCELLED. Timeout, disconnect, malformed response, worker kill, missing result commit or conflicting identity enters AMBIGUOUS/RECONCILING. Preserve CREATE/RESCHEDULE/CANCEL kind and prior state. Missing/negative event observations do not authorize blind retry or a replacement event. Reconciliation must prove the exact action outcome; uncertain deletion/reschedule cannot be confused with create.

Errors are typed AUTH_REQUIRED, SCOPE_DENIED, IDENTITY_CONFLICT, RATE_LIMITED, TEMPORARY_UNAVAILABLE, INVALID_REQUEST, EVENT_CONFLICT, SLOT_UNAVAILABLE, OUTCOME_AMBIGUOUS or CANCELLED. Read retry is at most 3 attempts inside deadline/budget. No write retry is automatic: only BookingGateway can evaluate conclusive rejection/pre-write proof and fresh authority. Cancellation checks before/after calls never rewrite possibly accepted writes.

## Ordered implementation tasks

<!-- roadmap-task id=PROVIDER-07-T01 milestone=M3 depends_on=ARCH-02-T01,ARCH-03-T01 mode=parallel locks=provider-contracts -->
- [ ] **Define neutral split capabilities —** Input: canonical booking states/authority and provider-neutral types. Operation: implement strict requests/results/errors, bounded read and write-only ports and fixture hashes. Output: CalendarReadPort/CalendarWritePort contract. Test evidence: schema/bounds and forbidden write-capability graph. Failure behavior: fail before any credential or network.
<!-- roadmap-task id=PROVIDER-07-T02 milestone=M3 depends_on=PROVIDER-07-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement signed fixtures and replacement adapter —** Input: synthetic availability/event observations. Operation: cover create/reschedule/cancel, explicit confirmation, DST, conflict, notifications, replay and ambiguity with network denied. Output: recorded contract suite and fake replacement proof. Test evidence: exact request/result/ledger hashes and no hidden writes. Failure behavior: fixture rejected; live composition disabled.
<!-- roadmap-task id=PROVIDER-07-T03 milestone=M6 depends_on=PROVIDER-07-T02,SEC-02-T04,SEC-03-T01 mode=serial locks=provider-contracts,security-runtime -->
- [ ] **Implement Google Calendar composition —** Input: neutral ports, scoped credential policy and fake HTTP fixtures. Operation: isolate credential/read/write clients, map Google observations/errors, pin calendar identity and notification behavior. Output: disabled-by-default first adapter. Test evidence: wrong scope/calendar, revoked credential, bounds and safe telemetry tests. Failure behavior: calendar unavailable and booking actions paused.
<!-- roadmap-task id=PROVIDER-07-T04 milestone=M6 depends_on=PROVIDER-07-T03 mode=serial locks=provider-contracts,calendar-side-effects -->
- [ ] **Verify BookingGateway-only mutation and reconciliation —** Input: immutable booking/action fixtures and BookingGateway interface. Operation: prove sole writer, persisted-attempt-before-call, conditional action/version idempotency, positive-evidence reconciliation and cancellation/reschedule handling. Output: adapter acceptance interface for WF-07 live test gate. Test evidence: fake HTTP/PostgreSQL crash matrix, zero duplicate events/notifications and no negative-read retry. Failure behavior: retain AMBIGUOUS/RECONCILING and deny further writes.

## Safety, privacy, observability and acceptance

Credentials are encrypted, least-scope, revocable and server-only. Calendar details/contact fields follow purpose-specific encryption, reader/writer, deletion/backup expiry and legal-hold rules in DB-06. Metrics contain booking/action/version IDs, outcome, latency, conflict/ambiguity counts and cost, never attendees/descriptions or raw slot-confirmation text.

- [ ] Read/write capabilities are independently composed and gateway ownership is proven.
- [ ] Identity, explicit confirmation, timezone/DST, notifications and change operations are deterministic.
- [ ] Every ambiguous create/reschedule/cancel remains quarantined until exact evidence resolves it.
- [ ] Recorded replacement/crash fixtures pass before owned-calendar live gate; no production authority is implied.

Retain capability schemas, signed fixture hashes, credential-scope review, provider mapping, gateway call graph, action/observation traces and recovery/timezone/notification evidence.
