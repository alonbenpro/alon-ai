# Lead Sources, Phased Qualification, and Frozen Cohorts

**Document ID:** FRONTEND-05
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M7
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-05-T01 <- BACKEND-02-T05,BACKEND-02-T02; FRONTEND-05-T02 <- FRONTEND-05-T01,BACKEND-01-T07; FRONTEND-05-T03 <- FRONTEND-05-T02,BACKEND-05-T06; FRONTEND-05-T04 <- FRONTEND-05-T03,BACKEND-02-T05; FRONTEND-05-T05 <- FRONTEND-05-T04,BACKEND-02-T05`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

Discovery uses Google Maps and other reviewed public business sources only through approved adapters and exact scopes. The UI exposes source time, query/filter version, provenance, preliminary facts/unknowns, dedupe disposition and review validity. Social/directory sources are unavailable until their own adapter/terms/evidence gate exists; an input URL is not permission to crawl.

BusinessIdentityService owns accepted identity/deduplication across sources; QualificationService consumes that result. Render PRELIMINARY qualification before costly LeadResearchDossier work, and FINAL qualification against the accepted immutable OfferPackage afterward. Every fact is FACT, ESTIMATE or UNKNOWN with supported provenance. Identity, suppression, legal-policy, provider, frequency and capacity gates are separately displayed; agent qualification cannot waive them.

Membership is a current-stage server-owned eligibility snapshot/query and immutable member hash. The browser supplies no recipient list and does not preselect future stages. createCampaignVersion consumes the exact BACKEND-02 current-stage scope and expected versions; the deterministic owner chooses/fixes admitted members. Lead browsing/filtering is inspection only and cannot change membership. A stale snapshot must be refreshed and re-evaluated; optimistic additions are forbidden.

Registered increments are SHADOW/REVIEW_20/QUALIFIED_50/SCALE_100_TO_300 with cumulative maxima 0/20/50/explicitly-authorized-100-to-300. Show the effective smaller cap, admitted unique recipients, reservations and remaining capacity. Replies and follow-up messages consume their message/frequency/budget allowances but never inflate unique-recipient denominators. Frozen cohorts keep offer/strategy/activation/filter/causal/evidence/metric versions through completion. New source evidence cannot silently replace them mid-cohort.

listSendBlocks and getActionAuthorization explain fresh deterministic blocks and immutable ActionAuthorityScopeV1 lineage. These reads do not authorize sending. SendGateway is the only Gmail writer. The conversation view distinguishes purchase commitment from qualified call agreement; booking without purchase acceptance cannot inflate COMMITTED.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-05-T01 milestone=M7 depends_on=BACKEND-02-T05,BACKEND-02-T02 mode=serial locks=frontend-client -->
- [ ] **Render discovery and sources —** Input: lead source/candidate/dossier/qualification and cohort DTOs. Operation: show approved adapters, scope/query/filter/provenance and dedupe results. Output: lead exploration view. Test evidence: unknown adapter, unsupported social source and invented linkage cases. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-05-T02 milestone=M7 depends_on=FRONTEND-05-T01,BACKEND-01-T07 mode=serial locks=frontend-client -->
- [ ] **Render phased qualification —** Input: accepted offer, candidates, dossier and both decisions. Operation: separate preliminary-qualified from finally qualified and deterministic admission eligibility. Output: phase-aware lead view. Test evidence: no deep research before preliminary pass; no send before final pass. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-05-T03 milestone=M7 depends_on=FRONTEND-05-T02,BACKEND-05-T06 mode=serial locks=frontend-client -->
- [ ] **Create server-owned stage membership —** Input: campaign creation API and current-stage eligibility snapshot. Operation: submit exact allowed snapshot/version, then render frozen cohort members/caps/hash. Output: cohort inspection and creation continuation. Test evidence: client-selected additions, stale snapshot, duplicate identity and cap races deny. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-05-T04 milestone=M7 depends_on=FRONTEND-05-T03,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Operate campaign safety controls —** Input: campaign commands and fresh automatic-send block projections. Operation: show pause/resume/cancel and policy/suppression/capacity reasons. Output: guarded campaign operations. Test evidence: stale generation, stop races and browser bypass evidence. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-05-T05 milestone=M7 depends_on=FRONTEND-05-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Verify full lead-to-conversation view —** Input: accepted membership and conversation/booking projections. Operation: link lead evidence to INTERESTED/NEGOTIATING/COMMITTED/BOOKED and checkpoint attribution. Output: M7 campaign evidence. Test evidence: stable pagination, dedupe, cross-campaign activation and unavailable-data cases. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

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
