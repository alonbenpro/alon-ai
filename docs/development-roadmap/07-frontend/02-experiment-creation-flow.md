# Idea Origin, Research, and Offer Setup

**Document ID:** FRONTEND-02
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M4
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-02-T01 <- FRONTEND-01-T01,DB-02-T01; FRONTEND-02-T02 <- FRONTEND-02-T01; FRONTEND-02-T03 <- FRONTEND-02-T02; FRONTEND-02-T04 <- FRONTEND-02-T03`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

An experiment has exactly one idea origin: DISCOVERED invokes Idea Discovery; USER_SUPPLIED uses IdeaBriefMaterializer to produce the same immutable IdeaBrief with user provenance and bypass evidence. This is the only normal pipeline bypass. The UI cannot skip Market Research, Offer Design, preliminary qualification or final qualification. The server establishes approved EXPERIMENT_BASELINE strategy attribution before research; product calls never use a future checkpoint activation.

Render the provider order IdeaBrief → MarketResearchReport → OfferPackage and acceptance status, version/hash, source evidence and stale/superseded reasons. Offer Design consumes both prior artifacts and supplies nothing upstream. Candidate validation and commercial validation precede acceptance; browser intent is not an acceptance receipt.

Before execution the operator can configure or tighten economics, source allowlist, legal-policy facts, budgets, conversation/booking limits and kill switches through the existing typed owners. configureOfferEnvelope returns a new brief version only outside an active frozen cohort. Protected legal evidence stays with its existing deterministic authority and cannot be authored as free-form model output.

The offer view shows target customer, problem, solution, positioning, scope/deliverables/exclusions, approved evidence-backed claims, qualification filters, base/minimum price, margin floor, cost assumptions, currency/FX/rounding/tax/fee versions, allowed discount bands, pilots, variants, payment schedules, validity and booking constraints. Show server_calculated_examples and cost_evidence_status; never calculate permissible discounts or margin in the client. A missing/expired offer or cost evidence blocks its dependent action.

Create/retry/resume preserves the returned experiment/brief version, command identity and idempotency key. After timeout refetch the canonical resource or replay the same command; never create a second experiment to escape ambiguity. Draft text stays in memory, is cleared on logout, and never enters telemetry or URLs.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-02-T01 milestone=M4 depends_on=FRONTEND-01-T01,DB-02-T01 mode=serial locks=frontend-client -->
- [ ] **Render exact pre-run brief —** Input: createExperiment DTO and PRODUCT-01 constraints. Operation: capture exactly one DISCOVERED or USER_SUPPLIED origin and server-owned registered stage plan. Output: strict creation form and canonical request. Test evidence: unknown fields/origin, duplicate submission and invalid budgets fail. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-02-T02 milestone=M4 depends_on=FRONTEND-02-T01 mode=serial locks=frontend-client -->
- [ ] **Materialize user ideas and baseline —** Input: server creation receipt and optional idea text. Operation: call materializeSuppliedIdea only for USER_SUPPLIED and inspect the identical accepted IdeaBrief contract with provenance. Output: idempotent creation continuation. Test evidence: no upstream OfferPackage input, no research before accepted IdeaBrief. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-02-T03 milestone=M4 depends_on=FRONTEND-02-T02 mode=serial locks=frontend-client -->
- [ ] **Inspect research and commercial envelope —** Input: accepted IdeaBrief/MarketResearchReport and pre-run configuration. Operation: render offer/economics constraints and configureOfferEnvelope before cohort freeze using expected brief version. Output: versioned setup and accepted-offer inspection. Test evidence: stale ETag, unsupported terms and active-cohort mutation deny. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-02-T04 milestone=M4 depends_on=FRONTEND-02-T03 mode=serial locks=frontend-client -->
- [ ] **Verify creation journey —** Input: generated client and accepted artifact projections. Operation: cover discovered/manual origins, resume, version conflict, errors and budget visibility. Output: M4 no-send browser evidence. Test evidence: same key replays one experiment; no provider side effect or invented acceptance. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

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
