# Complete Sales Funnel Browser and Accessibility Tests

**Document ID:** TEST-05
**Status:** Planned roadmap requirements; product implementation and live evidence are not claimed
**Milestone:** M8, M9
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `TEST-05-T01 <- TEST-01-T03,BACKEND-02-T05; TEST-05-T02 <- TEST-05-T01,FRONTEND-01-T04,FRONTEND-02-T04,FRONTEND-03-T01,FRONTEND-03-T02,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-08-T01,FRONTEND-08-T03,FRONTEND-09-T04,FRONTEND-01-T05,FRONTEND-03-T03; TEST-05-T03 <- TEST-05-T02,SEC-02-T06,PROVIDER-01-T06,FRONTEND-09-T05; TEST-05-T04 <- TEST-05-T03; TEST-05-T05 <- TEST-05-T04,SEC-04-T04; TEST-05-T06 <- TEST-05-T05,TEST-01-T01`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Versioned implementation contracts, closed coverage and retained verification evidence
**Unlocks:** Dependent acceptance gates only; never automatic live release or provider authority
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Browser coverage is planned. The current readiness foundation, health client and component tests do not establish private product, calendar, strategy or exception behavior. Use Playwright against isolated real API/PostgreSQL state with deterministic provider fixtures and write spies; do not let page objects reconstruct policy.

## Required browser matrix

| Journey | Pass evidence |
| --- | --- |
| origin/research/offer | DISCOVERED and USER_SUPPLIED both materialize accepted IdeaBrief; market precedes offer; economics/version/hash/claim refs render; stale or active-cohort envelope mutation rejects |
| discovery/qualification/cohort | approved source/dedupe/dossier FACT/ESTIMATE/UNKNOWN and PRELIMINARY/FINAL are distinct; current-stage server membership snapshot/hash/cap; browser cannot select recipients |
| automatic conversation | complete ordered redacted timeline, fresh automatic-send blocks, inbound cold stop, bounded replies/questions/objections, terminal/rejection/opt-out behavior and no routine approval step |
| negotiation/commitment | accepted offer terms and deterministic floor/discount/scope evidence; STATED/INFERRED/UNKNOWN; INTERESTED→NEGOTIATING→COMMITTED→BOOKED purchase path; call-only path never creates COMMITTED |
| calendar | UTC/IANA/offset/tzdb labels, DST ambiguity, expired/unavailable slots, explicit confirmation; independent idempotent create/reschedule/cancel/notification/reconciliation states |
| checkpoint/global strategy | frozen stage evidence and exact five checkpoint decisions; every agent's four learning results; primary/secondary/guardrail evidence, activation/rollback and cross-campaign timing |
| exception/recovery | purpose-bound sensitive preview, correction command and resolution; send/calendar ambiguity remains quarantined; no resolution/retry/resume inferred from UI |
| auth/public/privacy | opaque private session/OIDC/Gmail callbacks, CSRF/Origin/fetch metadata, logout/cache clearing; exact scanner-safe FastAPI GET/POST remains separate |
| unavailable/error | empty/loading/stale/partial/redacted/expired/pending/unknown/terminal states are explicit; 409/412/428 refetch; timeout replays exact logical command |

Directly forge hidden actions, request bodies, local state, ETags/generations, current-stage snapshot, price/margin, recipient/thread/offer/strategy refs, slot confirmation, callback identity, exception resolution and mid-cohort activation. Each server rejects before unauthorized Gmail/calendar writes. Assert SendGateway and BookingGateway sole-writer call graphs with import/network spies and no provider credentials/SDK in the browser bundle. HTTP 202 is not confirmed send/booking.

Simulate one complete four-stage synthetic campaign with accepted versions: both idea origins, multi-source duplicate/conflict, preliminary pass/fail, research/final qualification, initial send, positive/question/objection/rejection/opt-out, allowed and blocked negotiation, call-only and purchase commitment, labelled booking/reschedule/cancel, checkpoint freeze/learning and cross-campaign boundary activation. Verify increments 100/200/300/400 and cumulative 100/300/600/1,000, no fifth cohort or repeated recipient, immutable historical attribution, weak-evidence no mutation and automatic deterioration rollback. Every provider effect is fixture-spied; this is not real demand.

## Accessibility, isolation and command ownership

Keep the exact viewport matrix 320x568, 768x1024, 1280x800 and 200% zoom at 1280 CSS pixels; breakpoints 0–639/640–1023/>=1024; 44x44 touch targets; no horizontal page overflow; labelled scrollable tables/card alternatives; 4.5:1 text and 3:1 large/UI contrast. Run Chromium, Firefox, WebKit and an operator-browser/VoiceOver smoke. Verify axe, keyboard order, focus restoration, live regions, errors, forced colors and reduced motion. Calendar needs a keyboard list alternative and explicit timezone labels.

Per-worker database/schema/session/fixture/provider identities are disjoint, with network denied except loopback test services. Screenshots/traces use synthetic content only and must pass PII/token/body/calendar canary scans. Logout/expiry clears all private/sensitive caches. Parallel contamination, API restart and browser/provider absence cannot become a green test.

T7-BROWSER-PRIVATE / BROWSER_PRIVATE owns all private-operation journeys, accessibility, calendar/checkpoint/strategy and synthetic funnel cases. T7-BROWSER-PUBLIC / BROWSER_PUBLIC_M9 owns only the exact FastAPI public unsubscribe pair. Derive private operation set from BACKEND-02, public set equals getUnsubscribeConfirmation/confirmUnsubscribe, intersection is empty and union equals the complete API manifest. Invoke TEST-01's signed absolute runner form, not a new child-command entry.

Public tests run with Next.js absent: scanner/prefetch/GET performs zero DB mutation, no private cookie/asset/analytics is used; only focused same-origin explicit POST commits idempotent suppression. Cover malformed/expired tokens, opaque uniform responses, exact CSP/cache/referrer headers, Origin/content type/rate/WAF limits, dependency failure, SUPPRESSION_ONLY/DISABLED_UNSAFE recovery, backlog replay and no private-route exposure. Missing browser/M9 fixture is unavailable exit 30.

## Ordered implementation tasks

<!-- roadmap-task id=TEST-05-T01 milestone=M8 depends_on=TEST-01-T03,BACKEND-02-T05 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Compose isolated browser fixtures —** Input: signed canonical API/database/provider manifests. Operation: start disjoint per-worker contexts and network spies. Output: deterministic browser environment. Test evidence: cross-worker pollution, restart and forbidden egress fail. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=TEST-05-T02 milestone=M8 depends_on=TEST-05-T01,FRONTEND-01-T04,FRONTEND-02-T04,FRONTEND-03-T01,FRONTEND-03-T02,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-08-T01,FRONTEND-08-T03,FRONTEND-09-T04,FRONTEND-01-T05,FRONTEND-03-T03 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Execute complete private sales journeys —** Input: all FRONTEND views and backend owners. Operation: run origin-to-booking/checkpoint/global-strategy/exception flows and full campaign simulation. Output: private-route coverage and server receipts. Test evidence: all exact state/error modes and no client authority. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=TEST-05-T03 milestone=M8 depends_on=TEST-05-T02,SEC-02-T06,PROVIDER-01-T06,FRONTEND-09-T05 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Attack auth and provider-action boundaries —** Input: session/OAuth/control/booking/checkpoint/strategy handlers. Operation: forge direct requests and race state while exercising recovery. Output: zero bypassed provider writes and privacy evidence. Test evidence: CSRF, stale generation, slot, cohort and activation denials. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=TEST-05-T04 milestone=M8 depends_on=TEST-05-T03 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Verify accessible responsive behavior —** Input: all registered routes/states and viewport matrix. Operation: run automated and manual keyboard/calendar/screen-reader checks. Output: safe screenshots/traces/manual evidence. Test evidence: every action usable without pointer/color or hidden timezone context. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=TEST-05-T05 milestone=M9 depends_on=TEST-05-T04,SEC-04-T04 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Verify scanner-safe public unsubscribe —** Input: M9 synthetic token and FastAPI two-operation fixture. Operation: exercise GET write-zero and explicit POST plus abort/recovery modes. Output: public edge/browser evidence. Test evidence: no Next.js dependency or private data/route leakage. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=TEST-05-T06 milestone=M9 depends_on=TEST-05-T05,TEST-01-T01 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Close browser command mapping —** Input: all private/public journeys and exact operations. Operation: prove disjoint complete command/profile/target/requirement sets. Output: signed browser coverage report. Test evidence: missing journey, swapped profile or unavailable environment denies gate. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.

## Test strategy, acceptance and recovery

- [ ] Every required positive/negative/concurrent case has a fixture identity, versioned owner, command, evidence hash and fail action; missing or unavailable evidence is not passing.
- [ ] Only SendGateway invokes Gmail writes and only BookingGateway invokes calendar create/reschedule/cancel. Crash/replay cannot duplicate effects.
- [ ] Cohorts remain 100/200/300/400 with cumulative 100/300/600/1,000 and no active-cohort mutation or fifth cohort.
- [ ] Decision sets remain CONTINUE/REVISE/KILL/INCONCLUSIVE/SAFETY_STOP and PROMOTE/KEEP/ROLLBACK/INSUFFICIENT_EVIDENCE; weak evidence cannot promote or continue.
- [ ] Retain signed case/result/command/fixture/schema/provider/strategy/activation hashes, call counts, costs, immutable action history and safe failure traces. Raw PII, message/calendar content, sensitive inferred attributes and credentials are excluded from ordinary telemetry/global learning.

Preserve first failures and resolve root cause; never average away safety failures or rewrite labels/history. Restore/rollback keeps admission off, applies current suppression/tombstones and reconciles possibly-called effects before any separately authorized re-entry. Use [canonical product authority](../00-product-strategy/01-product-scope.md), [booking](../03-workflows/07-booking-workflow.md), [checkpoints](../03-workflows/08-checkpoint-evaluation-workflow.md), [global learning](../03-workflows/09-global-learning-workflow.md), [shared evaluation](../04-agents/12-agent-evals-and-versioning.md), [API](../06-backend/02-api-contracts.md) and [privacy](../08-security-and-compliance/06-data-privacy-and-retention.md) as exact contracts.
