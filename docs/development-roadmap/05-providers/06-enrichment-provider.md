# Optional Business Enrichment Provider

**Document ID:** PROVIDER-06
**Status:** Planned fixture-first M3 boundary; live enrichment disabled until M5 evidence and provider-terms approval
**Milestone:** M3 contract, optional M5 live activation
**Owner:** Solo operator
**Prerequisites:** [AGENT-01 capability contracts](../04-agents/01-agent-runtime-and-contracts.md#exact-provider-capability-wire-and-fixture-contracts), [DB-03](../02-database/03-leads-campaigns-and-messages.md), DB-04/05, and [AGENT-05](../04-agents/05-lead-research-agent.md)
**Outputs:** Exact `business.search`/`business.details` protocols, disabled/fixture/live Google Places adapters, business-only minimization, evidence/cost/terms gates, and replacement seam
**Unlocks:** Optional M5 business-evidence improvement after simpler primary evidence fails a retained gate
**Risk:** High
**Complexity:** L

## Outcome and timing

The default is ruthless restraint: M4 does not need enrichment, and M5 must first prove that primary search/page evidence cannot meet qualification gates. M3 implements exact offline contracts and a disabled adapter. A live Google Places (New) adapter is eligible only after an explicit provider-terms, attribution, privacy, EEA/billing-region, cost, and measured-need decision. It returns public business facts, never personal contacts or send targets.

## Current repository state

No business provider, locator, field policy, API key, terms review, evidence capture, identity service, fixture, or live enrichment exists. `businesses`/`leads` are planned M2 tables; AGENT-05 names only consumer contracts. Broad provider portfolios remain deferred by ROADMAP-ROOT.

## Scope and non-goals

In scope: two exact capability families, deterministic business identity, bounded candidates/facts, frozen locator snapshot, Google Places translation, field masks, evidence, contradictions, errors, quota/cost, fixtures, and disabled/replacement modes. Non-goals: contact/email/phone/person discovery, guessed facts, lead qualification, identity auto-merge, bulk list building, reviews/photos, wildcard fields, indefinite provider-data caching, or using enrichment as outreach authority.

## Exact planned implementation surfaces

Create `providers/business/contracts.py`, `providers/business/disabled.py`, `providers/business/google_places.py`, `providers/business/fixtures.py`, `application/business_capabilities.py`, and a versioned provider field/terms manifest. `BusinessIdentityService` exclusively materializes `businesses`; `EvidenceIngestService` exclusively writes `evidence_items`.

| Python method | Frozen capability | Exact family | Literal payload identity | Default/max |
| --- | --- | --- | --- | --- |
| `BusinessEnrichmentPort.search_businesses` | `business.search` | `BusinessSearchRequestV1` (`provider.business_search.request.v1`) / `BusinessSearchResponseV1` (`provider.business_search.response.v1`) / `BusinessSearchFailureV1` (`provider.business_search.failure.v1`) / `BusinessSearchFixtureV1` (`provider.capability_fixture.v1`) | `BusinessSearchPayloadV1`, `provider.business_search.payload.v1` | 8,000/20,000ms |
| `BusinessEnrichmentPort.get_business_details` | `business.details` | `BusinessDetailsRequestV1` (`provider.business_details.request.v1`) / `BusinessDetailsResponseV1` (`provider.business_details.response.v1`) / `BusinessDetailsFailureV1` (`provider.business_details.failure.v1`) / `BusinessDetailsFixtureV1` (`provider.capability_fixture.v1`) | `BusinessDetailsPayloadV1`, `provider.business_details.payload.v1` | 6,000/15,000ms |

Every Task 3 field/bound is exact. Search accepts canonical name/domain/country and max 1..10; result candidates contain canonical name, optional domain, ISO country, 64-hex business identity, and 1..10 evidence IDs. Details accepts identity key, 1..20 fact keys and allowed domains; returns the same identity, at most 20 evidence-backed facts, and at most 10 contradictions. Each success requires its literal `payload_schema_version` and RFC 8785/SHA-256 `payload_hash`; failure cannot carry either. Request/result/fixture hashes and `expected_ledger_hash` follow DB-01, and each call produces one exact `ProviderUseLedgerEntryV1`.

### Deterministic identity and provider translation

Normalize provider text to NFC before construction. Canonical name collapses Unicode whitespace and casefolds only for the identity preimage while preserving a display form. Domain is HTTPS-origin-derived, IDNA ASCII, lowercase, registrable, without `www.`/port/path; country is ISO 3166-1 alpha-2. `business_identity_key` is lowercase SHA-256 over RFC 8785 UTF-8 envelope `{"schema_version":"business.identity.v1","payload":{"canonical_domain":domain_or_null,"canonical_name":NFC_casefolded_name,"country_code":country}}`. Conflicting domain/name/country facts create candidates/evidence but `BusinessIdentityService` quarantines DB-03 `identity_status='CONFLICT'`; the adapter never merges.

Live search maps to Google Places Text Search (New) `POST https://places.googleapis.com/v1/places:searchText` with `textQuery`, `maxResultCount<=10`, language/region pinned by operation version, and an explicit minimum field mask. Google requires `textQuery` and a field mask, bills by selected fields, and does not guarantee identical result lists: [Text Search (New)](https://developers.google.com/maps/documentation/places/web-service/text-search). Live details maps to Place Details (New) by provider place ID with an exact non-wildcard field mask: [Place Details (New)](https://developers.google.com/maps/documentation/places/web-service/place-details).

Permitted raw fields are only provider place ID, display name, website URI, postal country/limited business address, business status, and primary type. Phone numbers, reviews, people, opening-hours telemetry, photos, generative summaries, and contact fields are never requested or retained. Field masks are versioned cost/privacy API and wildcard `*` is forbidden.

Task 3 `BusinessDetailsRequestV1` deliberately contains no provider ID. Before agent execution, `BusinessCapabilityCompositionService` freezes `BusinessLocatorSnapshotV1`, an in-memory immutable mapping from `business_identity_key` to prior search evidence IDs/capture refs/provider locator and hashes it into the toolset configuration. `get_business_details` must resolve exactly one locator whose candidate identity/evidence still match and whose provider/source domains are in `allowed_domains`; zero/many/mismatch returns `EVIDENCE_CONFLICT`. The snapshot is not a mutable session, is not persisted as a new table, and is invisible to the agent/provider request wire.

Each candidate/fact is constructed only after `EvidenceIngestService` records a provider capture. `BusinessFactResponseV1.fact_key` must be one requested key from the operation manifest; `value` is business-level text; evidence IDs are nonempty; observed time is provider/capture time or null. Missing facts are omitted and disclosed in `contradictions`; they are never guessed. Provider offsets follow PROVIDER-05: source NFC, then zero-based half-open Unicode code-point conversion before typed construction.

### Errors, quota, cost, retry, fixtures, and authority

Search allows exactly `DEPENDENCY_UNAVAILABLE`, `TOOL_TIMEOUT`, `TOOL_RESULT_INVALID`, `TOOL_BUDGET_EXHAUSTED`, `COST_BUDGET_EXHAUSTED`, `CANCELLED`, `INTERNAL_ERROR`. Details allows the same plus `EVIDENCE_CONFLICT`. Authentication/terms-disabled/unsupported region is dependency unavailable; deadline is tool timeout; malformed/unsafe/personal fields are result invalid; 429/quota is tool budget exhausted; reservation denial is cost budget exhausted; locator/identity contradiction is evidence conflict.

The HTTP client has zero hidden retries. A read-only transient may be retried only by AGENT-01's bounded caller within time/tool/cost budgets, producing a distinct call/ledger row. Google recommends exponential backoff and avoiding synchronized requests, but provider advice cannot override agent ceilings: [Places web-service practices](https://developers.google.com/maps/documentation/places/web-service/web-services-best-practices). Field-mask SKU, quota, response IDs, duration, and provider-currency cost reconcile to `cost_entries`; quota/cost never grants qualification or send authority.

Modes are `DISABLED`, `RECORDED_FIXTURE`, and `LIVE_CAPTURE`. `DISABLED` deterministically returns `DEPENDENCY_UNAVAILABLE` without key/client. `RECORDED_FIXTURE` validates exact Task 3 fixtures and is the only M3 promotion mode. `LIVE_CAPTURE` requires the retained measured-need decision, current provider terms/attribution/data-retention approval, server-only restricted key, field manifest, budget, and M5 gate; removing any gate reverts to disabled.

Fixtures cover zero/duplicate/contradictory candidates, identity normalization, country/domain conflicts, provider-place-ID changes, missing locator, unrequested/personal fields, stale evidence, 429/5xx/timeout/cancel, field-mask drift, terms-disable, Unicode/span conversion, evidence failure, and zero-network replay. Google notes place IDs may change and recommends refresh after 12 months: [Place IDs](https://developers.google.com/maps/documentation/places/web-service/place-id); provider locator is evidence, never the DB-03 identity key.

```json
{
  "schema_version":"provider.business_search.request.v1","capability":"business.search",
  "context":{"provider_call_id":"8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d","operation_version":"google-places.v1","deadline_at":"2026-08-28T00:00:20Z"},
  "timeout_ms":8000,"canonical_name":"Acme Israel","canonical_domain":"acme.invalid","country_code":"IL","max_results":5
}
```

```json
{
  "schema_version":"provider.business_search.response.v1","capability":"business.search","result_type":"SUCCESS",
  "meta":{"provider_call_id":"8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d","provider_request_id":"places-req-01","outcome":"SUCCEEDED","started_at":"2026-08-28T00:00:00Z","finished_at":"2026-08-28T00:00:01Z","input_tokens":0,"output_tokens":0,"cost_minor":1,"currency":"USD"},
  "payload_schema_version":"provider.business_search.payload.v1",
  "payload":{"candidates":[{"canonical_name":"Acme Israel","canonical_domain":"acme.invalid","country_code":"IL","business_identity_key":"2222222222222222222222222222222222222222222222222222222222222222","evidence_item_ids":["42d704c7-c01f-4aeb-adb1-e8bc2fb338ce"]}]},
  "payload_hash":"321503c8ce9264e677baa79032ba20359d0554b332abd303c4bdca2bab5c8b73"
}
```

```json
{
  "schema_version":"provider.business_details.request.v1","capability":"business.details",
  "context":{"provider_call_id":"9b85bc7c-cf60-45a9-9925-6c8b82b88e0d","operation_version":"google-places.v1","deadline_at":"2026-08-28T00:00:15Z"},
  "timeout_ms":6000,"business_identity_key":"2222222222222222222222222222222222222222222222222222222222222222","requested_fact_keys":["business_status"],"allowed_domains":["acme.invalid"]
}
```

```json
{
  "schema_version":"provider.business_details.response.v1","capability":"business.details","result_type":"SUCCESS",
  "meta":{"provider_call_id":"9b85bc7c-cf60-45a9-9925-6c8b82b88e0d","provider_request_id":"places-req-02","outcome":"SUCCEEDED","started_at":"2026-08-28T00:00:00Z","finished_at":"2026-08-28T00:00:01Z","input_tokens":0,"output_tokens":0,"cost_minor":1,"currency":"USD"},
  "payload_schema_version":"provider.business_details.payload.v1",
  "payload":{"business_identity_key":"2222222222222222222222222222222222222222222222222222222222222222","facts":[{"fact_key":"business_status","value":"OPERATIONAL","evidence_item_ids":["42d704c7-c01f-4aeb-adb1-e8bc2fb338ce"],"observed_at":"2026-08-28T00:00:00Z"}],"contradictions":[]},
  "payload_hash":"fbd7d94b1ac4ea30b80b4c6ddfbab35df5defe1ba7ffcfe3ed75bbf05359b00e"
}
```

`UnresolvedInterpolationValidatorV1` scans the UTF-8 source bytes before parsing and then every JSON property name and string value after strict schema validation. Its closed pattern registry rejects a hash, dollar sign, or doubled opening brace followed by a template identifier and closing brace, as well as angle-bracket placeholder tokens and whole-value generator sentinels such as `MARKER`, `PLACEHOLDER`, `TBD`, or `TODO`. A match fails fixture loading before signature/hash comparison; the matched source text is never copied into the error. The validator runs over every checked-in provider fixture and this document's fenced examples so deleting a stray token without retaining the guard cannot pass `T7-DOC-CONTRACT`.

## Ordered implementation tasks

- [ ] **Implement exact two-family contracts —** Input: Task 3 models and DB-01 canonicalizer. Operation: preserve methods/literals/fields/unions/hashes/timeouts/error allowlists/fixtures/ledgers. Output: provider-neutral port plus disabled adapter. Test evidence: `test_business_capabilities_are_wire_exact_with_agent01`. Failure behavior: zero provider access.
- [ ] **Implement deterministic identity/locator composition —** Input: frozen candidate evidence. Operation: normalize/hash identity, build immutable locator snapshot, reject zero/many/conflict, and preserve DB-03 conflict quarantine. Output: bounded business identity context. Test evidence: Unicode/domain/country/concurrency/conflict vectors. Failure behavior: no auto-merge/details.
- [ ] **Implement terms-gated Google Places adapter —** Input: approved live gate, field mask, key, request, reservation. Operation: call Text Search/Details once, discard forbidden fields, ingest evidence, and construct exact results. Output: public business facts. Test evidence: fake HTTP/field/terms/quota/cost matrix. Failure behavior: disabled or typed failure.
- [ ] **Implement signed fixtures and replacement suite —** Input: sanitized captures. Operation: recompute all request/result/ledger/content hashes and replay with network disabled; run fake second provider. Output: reproducible M3/M5 evidence. Test evidence: tamper/cross-capability/zero-network/parity tests. Failure behavior: no promotion/activation.
- [ ] **Prove minimization and authority —** Input: provider fields/logs/import graph. Operation: scan for contacts/credentials/content and assert no merge/qualification/state/send path. Output: safety/terms evidence. Test evidence: forbidden-field and call-graph tests. Failure behavior: live adapter revoked.

## Test strategy

- **Contract `test_business_successes_require_exact_payload_schema_hash_and_evidence`:** no partial success.
- **Identity `test_business_identity_is_nfc_rfc8785_stable_and_conflict_visible`:** no provider-ID identity.
- **Privacy `test_google_field_masks_and_outputs_exclude_people_phone_email_and_reviews`:** fail closed.
- **Details `test_details_requires_one_frozen_matching_locator_and_requested_fact_keys`:** no mutable session.
- **Cost `test_field_mask_quota_and_cost_reconcile_before_another_call`:** no hidden retry.
- **Fixture `test_business_fixtures_are_signed_zero_network_and_replaceable`:** exact parity.
- **Interpolation `test_provider06_source_and_fixtures_reject_unresolved_interpolation_artifacts`:** each closed sentinel family fails before fixture hashing and reports only file/field location plus reason code.

## Security, privacy, compliance, idempotency, observability, and cost

The API key is server-only, IP/API restricted where supported, rotated, and never enters fixtures/logs. Provider terms, attribution, purpose, retention, and regional/billing rules are release gates, not prose assumptions. Store minimum business evidence as `SENSITIVE_SHORT`; safety/cost/evaluation records follow DB-06. Request/identity/locator hashes support reproducibility; provider results are observations, not idempotent truth. Telemetry uses safe call/business/domain/evidence hashes, field-mask version, counts, outcome/error, latency, quota and cost—never personal/contact data or key.

## Failure, rollback, and operator recovery

Any terms change, forbidden-field leak, identity merge, key exposure, quota surprise, or schema drift immediately selects `DISABLED`, revokes/rotates key as needed, quarantines captures, pauses affected lead work, and opens an incident. Revoke dependent acceptances through audited commands. Rollback uses the prior fixture/provider operation for new runs; provider observations remain immutable and labeled.

## Acceptance and retained evidence

- [ ] Both Task 3 families preserve exact bytes, schema literals, hashes, timeout/error/ledger/fixture semantics.
- [ ] M3 is fixture-only and live M5 activation has measured need plus current terms/privacy/cost approval.
- [ ] Every fact/candidate is public-business-only, evidence-backed, identity-stable, and conflict-visible.
- [ ] Agents cannot access contacts, credentials, merge/qualification/state/send authority.

Retain protocol/schema/hash snapshots, disabled/fixture/live manifests, provider terms/attribution/access date, identity/locator vectors, field-mask/status/quota fixtures, evidence/cost reconciliation, zero-network/replacement proof, forbidden-field/secret/PII scan, and activation/revocation decision.

## Dependencies and next deliverable

PROVIDER-06 depends on AGENT-01 and DB-03/04/05. Its fixture contract can support M3; live enrichment is optional after M5 evidence and never blocks simpler primary-evidence qualification or grants outreach authority.
