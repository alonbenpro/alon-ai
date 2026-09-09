# Brave Place Search Lead Discovery Provider

**Document ID:** PROVIDER-08
**Status:** Planned M3 fixtures and M5 source activation; no adapter exists
**Milestone:** M3, M5 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PROVIDER-08-T01 -> PROVIDER-08-T02 -> PROVIDER-08-T03 -> PROVIDER-08-T04`; cross-document task Inputs `PROVIDER-08-T01 <- AGENT-01-T01,DB-01-T01; PROVIDER-08-T03 <- PROVIDER-05-T03; PROVIDER-08-T04 <- OBS-03-T02`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [AGENT-11](../04-agents/05-lead-discovery-agent.md), [source/evidence rules](05-page-fetching-and-extraction.md).
**Outputs:** LeadDiscoveryProvider, `lead.discover` capability, Brave Place Search adapter, provenance/deduplication fixtures and live source activation gate
**Unlocks:** AGENT-11 M3 acceptance and WF-04 M5 discovery
**Risk:** Critical
**Complexity:** M

## Outcome and timing

Automated v1 place/business discovery uses **Brave Place Search only**. It returns source observations with exact provenance; it never creates accepted candidates, identities, or qualification decisions.

Google Maps is not an automated discovery adapter in v1. Instagram, TikTok, other social networks, directories, and arbitrary crawling are not automated discovery targets. Social profiles and other public pages may be attached later only as **manually reviewed evidence** under the evidence/privacy contract; a human review never grants an automated scraper capability.

LeadDiscoveryAgent proposes `LeadDiscoveryCandidate`; deterministic BusinessIdentityService/QualificationService own dedupe, accepted identity, and PRELIMINARY `QualificationDecision`. Expensive research remains downstream of accepted preliminary qualification.

## Exact automated source contract

The automated source registry is exact:

```json
{
  "schema_version": "lead.discovery.source_registry.v2",
  "automated_sources": ["BRAVE_PLACE_SEARCH"],
  "manual_evidence_sources": ["SOCIAL_PROFILE", "PUBLIC_BUSINESS_PAGE"],
  "arbitrary_crawling": false
}
```

A live Brave adapter requires current provider terms/field/retention/attribution review, bounded query/result/cost limits, source activation receipt, and fail-closed revocation. The roadmap does not authorize scraping.

## Wire contract

`LeadDiscoverRequestV1` includes provider-call context, timeout, accepted OfferPackage/version/hash, exact `source_id=BRAVE_PLACE_SEARCH`, adapter/terms/allowlist version, query/filter version/hash, country/geography, as-of time, and bounded max results/cursor.

`LeadDiscoveryObservationV1` contains only evidenced business/place fields: provider place/business ID, name/location/domain/website when observed, source/capture URI/reference/hash, query/filter version, retrieved/observed times, identity/dedupe keys, and typed `FACT|ESTIMATE|UNKNOWN` observations with evidence pointers and contradictions.

It must not fabricate or infer an owner/person/role/email/phone/linkage. Missing values remain UNKNOWN.

`LeadDiscoverResponseV1` is a strict success/failure union with provider request ID, usage/cost, payload hash and typed errors. SDK/provider objects do not escape the adapter. Cursor identity binds source/query/filter/offer scope; changed scope starts a new run.

## Manual social/public evidence

A manually reviewed social profile/public page can enter evidence only through the existing EvidenceIngestService with:

- source URL/capture and content hash;
- reviewer identity and review time;
- explicit permitted purpose/fields;
- factual spans and `FACT|ESTIMATE|UNKNOWN` labels;
- retention/redaction/access policy; and
- no automated pagination, scraping, account traversal, follower extraction, or contact guessing.

Manual evidence may support deep research/personalization if permitted; it is not another discovery source and cannot silently enlarge source scope.

## Provenance, dedupe, minimization, and cost

Dedupe uses Brave place IDs, canonical domain, normalized business/location, and accepted identity keys while retaining contributing evidence. Similar names alone cannot merge records; conflicts are quarantined.

Every call records request/result hashes, source/terms/adapter versions, result counts, latency, provider cost, accepted-candidate yield, duplicate/conflict/unknown rate, and governing offer/strategy/stage. Query/page/result caps and cost reservation apply before calls. Zero-result or truncated responses do not authorize fabricated candidates or fallback crawling.

M3 uses recorded fixtures with network physically unavailable. M5 live activation is separately scoped/revocable and only for Brave Place Search.

## Ordered implementation tasks

<!-- roadmap-task id=PROVIDER-08-T01 milestone=M3 depends_on=AGENT-01-T01,DB-01-T01 mode=parallel locks=provider-contracts -->
- [ ] **Encode Brave discovery capability and exact source registry —** Input: shared strict provider contracts and canonical source policy. Operation: implement request/result/fixture models, source-bound cursors and default-off registry with exact automated set `{BRAVE_PLACE_SEARCH}`. Output: LeadDiscoveryProvider plus disabled Brave adapter. Test evidence: schema/hash/timeout/unknown-source/social-source/cursor-splice negatives. Failure behavior: no credential/network access.
<!-- roadmap-task id=PROVIDER-08-T02 milestone=M3 depends_on=PROVIDER-08-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement recorded Brave Place Search adapter —** Input: synthetic/sanitized Brave place observations. Operation: map provider fields into provenance/identity facts and unknowns with no qualification authority. Output: fixture-backed adapter. Test evidence: duplicates, conflicting names/locations, missing identities, injection text, unsupported contact fields and zero network. Failure behavior: typed conflict/unavailable; no invented candidate.
<!-- roadmap-task id=PROVIDER-08-T03 milestone=M3 depends_on=PROVIDER-08-T02,PROVIDER-05-T03 mode=parallel locks=provider-contracts,agent-artifacts -->
- [ ] **Prove evidence, cost, manual-source separation and replacement handoff —** Input: Brave fixtures plus manual social/public evidence fixtures and EvidenceIngestService interface. Operation: verify hashes/usage/citations/costs and prove manual evidence cannot call `lead.discover` or create source expansion. Output: signed discovery fixtures for AGENT-11/AGENT-10. Test evidence: ledger parity, redaction, dedupe conflicts, manual-source isolation and no qualification writes. Failure behavior: fixture rejected.
<!-- roadmap-task id=PROVIDER-08-T04 milestone=M5 depends_on=PROVIDER-08-T03,OBS-03-T02 mode=serial locks=provider-contracts,live-environment -->
- [ ] **Gate Brave live discovery —** Input: current Brave terms/fields/privacy/attribution/retention review, operator source allowlist and bounded cost/query/result plan. Operation: validate exact Brave source before bounded calls and revoke on stale/failed gate. Output: source activation receipt and captured observations. Test evidence: Google Maps/social/directory automation denial, caps, revocation, provenance and zero-result cases. Failure behavior: adapter disabled; no automated fallback source.

## Acceptance

- [ ] Automated source set is exactly Brave Place Search.
- [ ] Social/public profiles are manual evidence only.
- [ ] Every observation retains exact source/query/filter/time/hash evidence.
- [ ] Identity fabrication, silent merging, fallback crawling and unapproved source expansion fail closed.
- [ ] M3 is offline and M5 live activation is bounded/revocable.

Retain Brave terms/activation receipts, fixture/evidence hashes, cost/yield metrics, dedupe/conflict cases, manual-evidence separation proof, and source privacy/retention review.
