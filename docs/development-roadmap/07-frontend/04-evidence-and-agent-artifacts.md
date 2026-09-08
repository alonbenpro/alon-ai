# Offer, Lead, and Global-Learning Evidence

**Document ID:** FRONTEND-04
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M7
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-04-T01 <- BACKEND-02-T05; FRONTEND-04-T02 <- FRONTEND-04-T01,BACKEND-06-T04; FRONTEND-04-T03 <- FRONTEND-04-T02,BACKEND-02-T05; FRONTEND-04-T04 <- FRONTEND-04-T03,BACKEND-02-T05`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

The renderer set equals IdeaBrief, MarketResearchReport, OfferPackage, LeadDiscoveryCandidate, LeadResearchDossier, QualificationDecision, ConversationStrategy, EmailDraft, ReplyEvaluation, NegotiationDecision, BookingIntent, CheckpointEvidenceBundle, AgentLearningProposal, GlobalStrategyPackage and StrategyActivation. QualificationDecision renders explicit PRELIMINARY and FINAL phases without inventing two artifact names.

Every view shows immutable ID/schema, producer/kind/strategy, input snapshot ID/hash, output hash, minimized evidence refs, timestamp, disposition, supersession and acceptance receipt. ArtifactRefV1 identifies candidate bytes before acceptance; AcceptedRefV1 additionally proves acceptance. The UI cannot relabel a candidate as accepted. Global scope and explicit non-product BOOTSTRAP/EVALUATION_ONLY modes render distinctly; null product attribution is invalid. Independent per-agent snapshots are expected to have different hashes.

Idea/research/offer lineage is ordered and immutable. OfferPackage alone governs downstream economics, permitted claims and qualification filters. ConversationStrategy selects only permitted objectives. A dossier shows source adapter/scope/query/time/review, dedupe linkage and supported business/person facts marked FACT, ESTIMATE or UNKNOWN with confidence; unknown identity/contact/role stays unknown.

CheckpointEvidenceBundle displays frozen stage cutoff/member set, denominators, costs/completeness, unresolved safety flags and real versus fixture mode. Global learning exposes only approved minimized transforms and protected evaluation summaries. Original thread bodies, budget source spans, private calendar details and protected holdout payloads never appear in global learning. Sensitive raw inspection, when justified, belongs to the separate purpose-bound exception preview.

Sanitize source markup and inbound text as untrusted data. Do not execute source links automatically or fetch them from the browser. Expired/deleted/withheld evidence retains its typed disposition and cannot be replaced by a model summary as factual proof. Preserve deterministic unavailable/stale explanations and content-free telemetry.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-04-T01 milestone=M7 depends_on=BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Build artifact renderer registry —** Input: canonical fifteen-artifact contract and generated DTOs. Operation: render strict typed envelope, producer, version, hashes, acceptance and supersession. Output: complete artifact registry. Test evidence: exact name set and unknown schema fallback tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-04-T02 milestone=M7 depends_on=FRONTEND-04-T01,BACKEND-06-T04 mode=serial locks=frontend-client -->
- [ ] **Trace provider-before-consumer lineage —** Input: accepted artifact refs and normalized input snapshots. Operation: link each input to its accepted provider version and phase without equating distinct workflow/agent hashes. Output: navigable evidence chain. Test evidence: hash splice, stale acceptance and missing phase fail visibly. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-04-T03 milestone=M7 depends_on=FRONTEND-04-T02,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Inspect minimized business/commercial evidence —** Input: offer/dossier/qualification responses. Operation: render FACT/ESTIMATE/UNKNOWN and claim mappings, economics proof and missing evidence. Output: sanitized evidence inspector. Test evidence: invented identity/claims, inference-as-fact and unsafe markup tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-04-T04 milestone=M7 depends_on=FRONTEND-04-T03,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Inspect checkpoint and strategy evidence —** Input: checkpoint/global-strategy protected summaries. Operation: show frozen primary/secondary/guardrail evidence and per-agent comparison/activation/rollback history. Output: M7 evidence browser. Test evidence: no protected holdout payload, raw PII or mutable cohort evidence. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

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
