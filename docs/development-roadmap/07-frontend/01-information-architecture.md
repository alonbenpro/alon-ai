# Operator Sales Control Plane

**Document ID:** FRONTEND-01
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M4, M7
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-01-T01 <- BACKEND-02-T02; FRONTEND-01-T02 <- FRONTEND-01-T01,BACKEND-02-T01; FRONTEND-01-T03 <- FRONTEND-01-T02; FRONTEND-01-T04 <- FRONTEND-01-T03; FRONTEND-01-T05 <- FRONTEND-01-T04,BACKEND-02-T05,SEC-02-T04,SEC-02-T05,FRONTEND-02-T04,FRONTEND-03-T01`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

The planned shell has five primary destinations: Experiments, Calendar, Global Strategies, Exceptions and Recovery. The current readiness page and generated health client exist; every product route, private session, query, command and dashboard described here remains planned. M4 exposes synthetic idea/research/offer work; M5 discovery and qualification remain no-send; M6 provider conversations and bookings use isolated owned resources; M7 exposes the full operator dashboard; M9 alone admits controlled real campaigns after all retained gates.

| Planned route | Owner and generated operations |
| --- | --- |
| /experiments and /experiments/new | listExperiments, createExperiment, materializeSuppliedIdea, configureOfferEnvelope |
| /experiments/[experimentId] | getExperiment, getWorkflowRun and existing guarded experiment commands |
| /experiments/[experimentId]/offers/[offerId] | listOfferPackages, getOfferPackage, getOfferEconomics |
| /experiments/[experimentId]/leads | listLeadSources, listLeadCandidates, getLeadDossier, getLeadQualification |
| /experiments/[experimentId]/campaigns/[campaignId] | getCampaignVersion, listCampaignCohorts, listSendBlocks, listConversations, listCheckpoints, listStrategyActivations |
| /conversations/[conversationId] and /messages/[messageId] | getConversation, listNegotiationDecisions, getOutreachMessage, getActionAuthorization, pauseConversation |
| /calendar and /bookings/[bookingIntentId] | listCalendarAccounts, getCalendarAvailability, listBookings, getBooking, requestBookingReschedule, requestBookingCancellation |
| /checkpoints/[checkpointId] | getCheckpoint, getCheckpointEvidence |
| /strategies and /strategies/[strategyVersionId] | listGlobalStrategies, getGlobalStrategy, getStrategyEvidence, requestStrategyRollback |
| /exceptions and /exceptions/[exceptionId] | listExceptions, getExceptionQueueReport, getException, getExceptionSensitivePreview, resolveException |
| /recovery | getRecoveryOverview, existing Gmail/control/incident commands, reconcileBookingAction |

BACKEND-02 is the sole exact operation/schema registry; derive client-coverage set equality from it without copying a fixed operation count. All current and future rows need a route or explicit FastAPI-only owner. Health and signed authentication/OAuth callbacks keep their exact exceptions. The two M9 public unsubscribe operations remain FastAPI-owned scanner-safe HTML/POST with no Next.js consumer, analytics, token cache or operator navigation.

Place planned pages in frontend/src/app/(operator), typed hooks under frontend/src/features, and shared boundary/status components under frontend/src/components. Generate types before implementation. React renders projections only: no Next.js business route handlers, Server Actions, DB queries, provider SDKs, policy math, credentials in browser storage/NEXT_PUBLIC_*, local cohort selection or direct action authorization. GET explanations never grant authority.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-01-T01 milestone=M4 depends_on=BACKEND-02-T02 mode=serial locks=frontend-client -->
- [ ] **Map the private sales shell —** Input: generated BACKEND-02 operations and canonical sales states. Operation: define Experiments, Calendar, Global Strategies, Exceptions and Recovery destinations with experiment-scoped offer/leads/conversations/checkpoints. Output: route-owner and generated-client coverage registry. Test evidence: every operation has one owner; forbidden provider/DB imports fail. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-01-T02 milestone=M4 depends_on=FRONTEND-01-T01,BACKEND-02-T01 mode=serial locks=frontend-client -->
- [ ] **Build server-state plumbing —** Input: generated request/response/error types. Operation: use typed query keys, opaque session credentials, signed snapshot cursors and deterministic command receipts. Output: reusable data/error/loading boundaries. Test evidence: 401/403, expired cursors, partial snapshots and unknown enums remain visible. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-01-T03 milestone=M4 depends_on=FRONTEND-01-T02 mode=serial locks=frontend-client -->
- [ ] **Implement canonical state rendering —** Input: ARCH-03 state projections. Operation: display allowed actions and blocked reasons exactly as returned without inferring transitions. Output: accessible status and action components. Test evidence: forged browser state cannot enable a command. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-01-T04 milestone=M4 depends_on=FRONTEND-01-T03 mode=serial locks=frontend-client -->
- [ ] **Implement resilient navigation —** Input: route registry and server state. Operation: preserve safe opaque deep links, keyboard focus and browser history while clearing sensitive caches on logout. Output: responsive accessible shell. Test evidence: keyboard, screen-reader, mobile, no-store and logout tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-01-T05 milestone=M7 depends_on=FRONTEND-01-T04,BACKEND-02-T05,SEC-02-T04,SEC-02-T05,FRONTEND-02-T04,FRONTEND-03-T01 mode=serial locks=frontend-client,security-runtime -->
- [ ] **Integrate the full control plane —** Input: completed private OpenAPI/client, session and M4 creation/control views. Operation: connect offer, lead, conversation, negotiation, booking, checkpoint, global strategy and exception projections. Output: M7 integrated operator shell. Test evidence: full route/operation coverage and API bypass-denial browser evidence. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

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
