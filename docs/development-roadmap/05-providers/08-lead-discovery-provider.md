# Approved Multi-Source Lead Discovery Provider

**Document ID:** PROVIDER-08
**Status:** Planned M3 fixtures and M5 source activation; no adapter exists
**Milestone:** M3, M5 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PROVIDER-08-T01 -> PROVIDER-08-T02 -> PROVIDER-08-T03 -> PROVIDER-08-T04`; cross-document task Inputs `PROVIDER-08-T01 <- AGENT-01-T01,DB-01-T01; PROVIDER-08-T03 <- PROVIDER-05-T03; PROVIDER-08-T04 <- OBS-03-T02`. Source authorities: [AGENT-11](../04-agents/05-lead-discovery-agent.md), [ARCH-02](../01-architecture/02-module-boundaries.md), [source/evidence rules](05-page-fetching-and-extraction.md).
**Outputs:** LeadDiscoveryProvider, exact lead.discover capability, approved source registry, provenance/deduplication fixtures and source activation gate
**Unlocks:** AGENT-11 M3 acceptance and WF-04 M5 discovery
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Discovery searches approved source-specific adapters, initially Google Maps and reviewed public business sources. Each source needs an implemented adapter, current terms/field/retention/attribution review, evidence tests and bounded activation. Instagram, TikTok, social networks, directories and arbitrary crawling are not promised or enabled by this contract.

The provider returns observations, never an accepted LeadDiscoveryCandidate or qualification decision. LeadDiscoveryAgent proposes candidates; deterministic identity/admission and QualificationService own acceptance and PRELIMINARY QualificationDecision. Optional business enrichment remains the separate PROVIDER-06 capability.

## Current repository state and surfaces

No discovery adapter, source registry, search run, candidate, source evidence, dedupe or approval exists. Plan `providers/discovery/contracts.py`, `providers/discovery/registry.py`, `providers/discovery/google_maps.py`, approved public-source adapters and `providers/discovery/fixtures.py`. Review actual provider API terms and behavior at implementation; the roadmap is not permission to scrape.

## Exact lead.discover wire and fixture contract

This is the seventh AGENT-01 provider capability. All types inherit StrictAgentModel. Requests/results are strict/frozen/extra-forbid, UTC timestamps and UUIDv4 IDs, hashes are lowercase SHA-256 of DB-01 RFC 8785 schema/payload bytes, and usage/cost reconciles through ProviderUseLedgerEntryV1.

| Type / literal schema | Required fields and bounds |
| --- | --- |
| LeadDiscoverRequestV1 / provider.lead_discover.request.v1 | capability=lead.discover; ProviderCallContextV1; timeout_ms 1..20,000 (default 8,000); accepted OfferPackage ID/version/hash; source_id/source_adapter_version/allowlist_version/terms_version; query 1..500 chars; query_version/filter_version/filter_hash; country/geography; as_of; max_results 1..20; optional source-bound cursor max 2,000 chars |
| LeadDiscoveryObservationV1 | source business ID; observed name/location/domain when evidenced; identity/deduplication keys; source URI/capture ref/evidence ID/content hash; retrieved_at/observed_at; query/filter versions; fields with FACT/ESTIMATE/UNKNOWN, confidence and evidence pointers; explicit contradictions/unknowns |
| LeadDiscoverPayloadV1 / provider.lead_discover.payload.v1 | observations tuple max 20; optional next source-bound cursor; query/result-set hash; source completeness and truncation flags |
| LeadDiscoverResponseV1 / provider.lead_discover.response.v1 | result_type=SUCCESS; capability=lead.discover; ProviderResultMetaV1 with outcome=SUCCEEDED; literal payload_schema_version and typed payload; mandatory payload_hash |
| LeadDiscoverFailureV1 / provider.lead_discover.failure.v1 | result_type=FAILURE; capability=lead.discover; ProviderResultMetaV1; typed AgentErrorCode; safe_error_detail/error_fingerprint; no payload/hash |
| LeadDiscoverFixtureV1 / provider.capability_fixture.v1 | fixture/capture identity and time; capability=lead.discover; exact request/result unions and request/response/ledger/fixture hashes |

LeadDiscoverResultV1 is exactly the discriminated success/failure union. Errors are DEPENDENCY_UNAVAILABLE, TOOL_TIMEOUT, TOOL_RESULT_INVALID, TOOL_BUDGET_EXHAUSTED, COST_BUDGET_EXHAUSTED, CANCELLED, INTERNAL_ERROR or EVIDENCE_CONFLICT. Outcome/code mapping follows AGENT-01. Unauthorized source/tool/request is rejected by deterministic composition before a provider call. No arbitrary HTTP client, opaque SDK result, accepted-artifact mutation, person/email/phone guess or command capability is exposed.

Cursor identity binds source/query/filter/offer scope; a changed scope starts a new discovery run. M3 recorded mode never networks. M5 live mode requires current source review, pre-run allowlist, budget/reservation, query/page/candidate/deadline caps and legal/source restrictions. Default-off adapter returns typed unavailable without loading credentials.

## Source provenance, identity and minimization

Record source adapter/version, terms/allowlist receipt, source-specific query/filter, observed/retrieved timestamps, raw captured evidence encrypted as required, sanitized citation URI, evidence/content hash and provider request ID when present. Business name, owner/person role and business-contact linkage require direct evidence; absence remains UNKNOWN. No email pattern generation or inferred person-to-business match is allowed.

Dedupe considers source business IDs, canonical domain, normalized business/location and accepted identity keys, retaining all contributing source evidence. Similar names alone cannot merge businesses; conflicts are quarantined for deterministic resolution. Adapter observations never decide final identity. Expensive research is downstream of accepted PRELIMINARY qualification, not a hidden enrichment request during discovery.

Untrusted page/provider content cannot expand source scope or tool capability. Reviewed public-person/role evidence for later research is captured only under explicit source/field/privacy scope; this provider does not add a contact database by inference. Every sensitive field has purpose, access, retention and deletion rules. Global learning receives only approved minimized source/yield/factual-quality evidence.

## Ordered implementation tasks

<!-- roadmap-task id=PROVIDER-08-T01 milestone=M3 depends_on=AGENT-01-T01,DB-01-T01 mode=parallel locks=provider-contracts -->
- [ ] **Encode discovery capability and source registry —** Input: shared strict provider contracts and canonical discovery scope. Operation: implement exact request/result/fixture models, source-bound cursors and default-off registry. Output: LeadDiscoveryProvider and disabled adapter. Test evidence: schema/hash/timeout/unknown-source/cursor-splice negatives. Failure behavior: no credential/network access.
<!-- roadmap-task id=PROVIDER-08-T02 milestone=M3 depends_on=PROVIDER-08-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement multiple recorded source adapters —** Input: synthetic/sanitized Google Maps and reviewed public-business observations. Operation: map both sources into identical provenance/identity facts and unknowns with no authority. Output: interchangeable fixture-backed adapters. Test evidence: duplicates, conflicting names/locations, missing identities, prompt injection and zero network. Failure behavior: typed conflict/unavailable; no invented candidate.
<!-- roadmap-task id=PROVIDER-08-T03 milestone=M3 depends_on=PROVIDER-08-T02,PROVIDER-05-T03 mode=parallel locks=provider-contracts,agent-artifacts -->
- [ ] **Prove evidence/cost and replacement handoff —** Input: source fixtures and EvidenceIngestService interface. Operation: verify captured evidence/hash/usage, safe citations and source-specific limits through sole writers. Output: signed discovery capability fixtures for AGENT-11 and AGENT-10. Test evidence: request/result/ledger parity, redaction, cross-source identity conflicts and no qualification/merge writes. Failure behavior: reject fixture and keep live adapters disabled.
<!-- roadmap-task id=PROVIDER-08-T04 milestone=M5 depends_on=PROVIDER-08-T03,OBS-03-T02 mode=serial locks=provider-contracts,live-environment -->
- [ ] **Gate source-specific live discovery —** Input: current adapter/terms/fields/privacy/attribution/retention review, pre-run operator source allowlist and bounded cost/query/page plan. Operation: validate each source independently before a bounded call; revoke availability when any gate expires. Output: source activation receipt and captured observations. Test evidence: unreviewed social/directory source denial, cap/cursor/revocation and factual-provenance cases. Failure behavior: affected adapter disabled; no fallback to arbitrary crawling.

## Recovery, testing and acceptance

Reads may retry at most three attempts inside deadline/budget under typed retry policy. A captured paid result is recovered by request/call hash; duplicate page replay does not recapture or bill by default. Cancellation stops before next page and preserves existing observations; no partial or truncated state is represented as complete. Scope changes create new versioned runs, never mutate a frozen cohort.

Required metrics are source discovery yield, duplicate/conflict/unknown rate, preliminary pass rate, evidence coverage, latency and cost with offer/strategy/cohort attribution. Logs contain safe IDs/hashes/counts, not contact details, raw source text or credentials.

- [ ] At least two approved source fixture adapters satisfy the identical contract.
- [ ] Every observation retains exact source/query/filter/time/hash evidence.
- [ ] Identity fabrication, silent merging and unapproved source expansion fail closed.
- [ ] M3 is offline and M5 activation is separately scoped and revocable.

Retain source registry/terms receipts, fixture/evidence hashes, identity/dedupe cases, replacement proof, source privacy/retention review and cap/cancellation/cost traces.
