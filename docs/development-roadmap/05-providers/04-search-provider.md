# Market Search Provider

**Document ID:** PROVIDER-04
**Status:** Planned M3 provider; no search client, capture service, fixture, or credential exists today
**Milestone:** M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PROVIDER-04-T01 -> PROVIDER-04-T02 -> PROVIDER-04-T03 -> PROVIDER-04-T04 -> PROVIDER-04-T05`; cross-document task Inputs `PROVIDER-04-T01 <- AGENT-01-T01,DB-01-T01; PROVIDER-04-T03 <- OBS-03-T02,DB-04-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): [AGENT-01 capability contracts](../04-agents/01-agent-runtime-and-contracts.md#exact-provider-capability-wire-and-fixture-contracts), [DB-04](../02-database/04-agent-artifacts-and-evidence.md), and [AGENT-04](../04-agents/03-market-research-agent.md)
**Outputs:** Byte-exact `search.query` capability, Brave Web Search adapter, evidence ingestion handoff, fixtures, quotas, and replacement seam
**Unlocks:** Recorded M3 market-research evaluations and M4 evidence capture
**Risk:** High
**Complexity:** M

## Outcome and timing

One bounded allowlisted query returns only captured result metadata and DB-04 evidence identities. Brave Web Search is the initial live raw provider; the agent sees only the frozen AGENT-01 capability union and never the subscription token, provider response, arbitrary browser, or mutable search session.

## Current repository state

There is no search provider/client/key, search port, evidence capture implementation, provider-use ledger, cost entry, fixture, or live search. AGENT-04 names consumer requirements only. Everything here is planned after M2 persistence.

## Scope and non-goals

In scope: exact wire parity, domain allow/block filtering, one raw search call, normalized HTTPS results, evidence ingestion, timeout/cancellation, errors, quota/cost, fixture capture, and provider replacement. Non-goals: unrestricted browsing, crawling, contact harvesting, personal search, provider answers/LLM summaries, login, mutable sessions, pagination beyond the requested bounded result set, or search results directly becoming accepted evidence.

## Exact planned implementation surfaces

Create `providers/search/contracts.py`, `providers/search/brave.py`, `providers/search/fixtures.py`, `providers/search/errors.py`, and application `SearchCapabilityService`. `EvidenceIngestService` remains the sole `evidence_items` writer; the raw adapter cannot mint UUIDs or persist. Exact mapping:

| Python method | Capability | Exact family | Literal payload schema |
| --- | --- | --- | --- |
| `MarketSearchPort.query` -> `SearchCapabilityService.query` -> `BraveWebSearchAdapter.search_raw` | `search.query` | `SearchQueryRequestV1` (`provider.search_query.request.v1`), `SearchQueryResponseV1` (`provider.search_query.response.v1`), `SearchQueryFailureV1` (`provider.search_query.failure.v1`), `SearchQueryFixtureV1` in `provider.capability_fixture.v1` | `SearchQueryPayloadV1`, `payload_schema_version="provider.search_query.payload.v1"` |

No extra field, alias literal, optional success payload/hash, or opaque provider object is permitted. Request fields remain exactly capability/context, `timeout_ms=1..20_000`, query `1..500`, `allowed_domains=1..50`, `blocked_domains=0..50`, `max_results=1..20`, and UTC `as_of`. Default timeout is 8,000ms; earlier provider context deadline wins.

### Raw provider translation and evidence construction

The Brave adapter calls `GET https://api.search.brave.com/res/v1/web/search` with `X-Subscription-Token` held only in composition, `q`, `count=max_results`, `safesearch=strict`, and pinned country/search/UI language from the operation version. Brave documents the endpoint/token and a query maximum of 400 characters/50 words: [Web Search API reference](https://api-dashboard.search.brave.com/api-reference/web/search/get). A valid AGENT-01 request that cannot fit that vendor subset returns `TOOL_RESULT_INVALID` before credential use; the provider-neutral contract is not narrowed.

The raw response is untrusted. Pass each raw locator through DB-04 `CitationUriPolicyV1`: require HTTPS, validate domain/IDNA/port/redirect policy, reject userinfo/sensitive/signed/PII/credential query material, and construct only the canonical sanitized `citation_uri`; block wins. The raw locator is handed directly to restricted evidence ingestion for encryption and never enters an agent/provider result, log, event, or fixture. Normalize title/snippet to NFC, trim, enforce AGENT-01 lengths, discard unsupported/duplicate results, and preserve provider order among eligible results. If this or a replacement provider supplies byte offsets, normalize the referenced source to NFC and convert them to zero-based half-open Unicode code-point indexes before any typed construction; raw byte offsets never escape. Zero eligible results is a successful empty tuple, not fabricated failure.

`SearchCapabilityService` submits each eligible item to `EvidenceIngestService` with source provider `brave.web-search.v1`, retrieval time, restricted raw locator, sanitized citation, source-policy version, restricted capture ref, MIME/language, content hash, and `SENSITIVE_SHORT`. Only after all returned items have valid persisted evidence IDs/hashes does it build `SearchResultItemV1` with `citation_uri`. If any item cannot be captured, discard that item; if the provider result itself is structurally untrustworthy, return failure. The agent never receives raw response fields.

The success `payload_hash` is lowercase SHA-256 over RFC 8785 UTF-8 for `{"schema_version":"provider.search_query.payload.v1","payload":payload}`. Request, complete result branch, usage, ledger, and fixture hashes use AGENT-01's exact DB-01 envelopes. Search result-set hash and every evidence ID/content hash reconcile with one `ProviderUseLedgerEntryV1`; `ProviderCostReconciliationService` creates the matching `cost_entries` row.

Brave results are fresh provider observations, not historical truth at `as_of`; `as_of` freezes the request/evaluation context and future-dated captures are rejected. Publication time is recorded only when the source supplies verifiable metadata. The adapter never claims result completeness, independence, correctness, or acceptance.

### Errors, timeout, quota, cancellation, and retry

The exact allowed failures are `DEPENDENCY_UNAVAILABLE`, `TOOL_TIMEOUT`, `TOOL_RESULT_INVALID`, `TOOL_BUDGET_EXHAUSTED`, `COST_BUDGET_EXHAUSTED`, `CANCELLED`, and `INTERNAL_ERROR`.

| Raw condition | Exact mapping | Retry behavior |
| --- | --- | --- |
| missing key, 401/403, unsupported operation manifest | `DEPENDENCY_UNAVAILABLE` | operator/config repair; none |
| local/request deadline or transport timeout | `TOOL_TIMEOUT` | only AGENT-01 bounded retry and only before accepted billed result |
| 400/422, malformed JSON, invalid/unsafe result shape | `TOOL_RESULT_INVALID` | no automatic retry |
| 429 or exhausted provider plan window | `TOOL_BUDGET_EXHAUSTED` | no adapter retry; respect reset through later workflow admission |
| reservation/cost cap closed | `COST_BUDGET_EXHAUSTED` | no provider call |
| cancellation at any boundary | `CANCELLED` | no further result ingestion/call |
| 5xx/connection unavailable | `DEPENDENCY_UNAVAILABLE` | application-bounded only within deadline/budget |

Disable HTTP-client automatic retries. Every actual provider request must be visible against tool-call/cost ceilings. Brave uses a one-second sliding window, returns 429 when exceeded, and exposes limit/remaining/reset headers; successful requests count toward quota/billing: [rate limiting](https://api-dashboard.search.brave.com/documentation/guides/rate-limiting). A versioned limiter reserves both burst and monthly capacity before the call; provider headers reconcile but never grant authority. Check cancellation before reservation, credential access, HTTP, every evidence ingest, response construction, and persistence handoff.

### Fixtures, live mode, replacement, example, and authority

`LIVE_CAPTURE` is allowed only for promoted M3 capture with frozen domain/source policy, budget reservation, and sanitized raw capture. `RECORDED_FIXTURE` validates exact `SearchQueryFixtureV1`, recomputes request/response/ledger/content hashes, and has no HTTP client/key. Fixtures cover empty/fewer results, domain/IDNA/redirect-like URLs, duplicates, unsafe URI, oversized strings, 429/5xx/timeout/cancel, malformed response, evidence-ingest failure, and Hebrew/emoji/decomposed Unicode NFC.

A replacement adapter must pass the exact union/schema/hash/timeout/error/ledger/cost/evidence/ordering/filter/cancellation fixture suite. Different ranking is provider evidence and requires a new operation/provider version plus evaluation; it cannot silently change an existing fixture.

```json
{
  "schema_version": "provider.search_query.request.v1",
  "capability": "search.query",
  "context": {"provider_call_id":"8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d","operation_version":"brave-web-search.v1","deadline_at":"2026-08-28T00:00:20Z"},
  "timeout_ms": 8000,
  "query": "small business validation Israel",
  "allowed_domains": ["gov.il"],
  "blocked_domains": [],
  "max_results": 5,
  "as_of": "2026-08-28T00:00:00Z"
}
```

```json
{
  "schema_version":"provider.search_query.response.v1",
  "capability":"search.query",
  "result_type":"SUCCESS",
  "meta":{"provider_call_id":"8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d","provider_request_id":"brave-req-01","outcome":"SUCCEEDED","started_at":"2026-08-28T00:00:00Z","finished_at":"2026-08-28T00:00:01Z","input_tokens":0,"output_tokens":0,"cost_minor":1,"currency":"USD"},
  "payload_schema_version":"provider.search_query.payload.v1",
  "payload":{"results":[{"citation_uri":"https://www.gov.il/en/pages/example","title":"Public small-business guidance","snippet":"Official guidance for small businesses.","evidence_item_id":"42d704c7-c01f-4aeb-adb1-e8bc2fb338ce","content_hash":"1111111111111111111111111111111111111111111111111111111111111111"}]},
  "payload_hash":"49fc83e5093360a6634b11e55b1e1ffab29b367615ce42ba38e72504e47cba40"
}
```

Agents receive the capability port, never provider credentials/client. Search cannot mutate state, accept evidence, decide policy/approval/budget/suppression, or call Gmail/`SendGateway`.

Market Research consumes accepted IdeaBrief and produces MarketResearchReport before Offer Design. This market search port does not accept an OfferPackage as upstream research authority or substitute for the approved multi-source LeadDiscoveryProvider in [PROVIDER-08](08-lead-discovery-provider.md).

## Ordered implementation tasks

<!-- roadmap-task id=PROVIDER-04-T01 milestone=M3 depends_on=AGENT-01-T01,DB-01-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement exact capability service —** Input: AGENT-01 models and DB-01 canonicalizer. Operation: preserve schemas/fields/hashes/timeout/error allowlist and method mapping. Output: `MarketSearchPort`. Test evidence: `test_search_capability_wire_and_fixture_are_agent01_exact`. Failure behavior: reject before call.
<!-- roadmap-task id=PROVIDER-04-T02 milestone=M3 depends_on=PROVIDER-04-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement Brave raw adapter and filters —** Input: validated request/credential/operation policy. Operation: reserve limiter, call once, normalize/filter/dedupe strict metadata. Output: bounded raw items or typed error. Test evidence: HTTP/domain/Unicode/status matrix. Failure behavior: no unsafe item escapes.
<!-- roadmap-task id=PROVIDER-04-T03 milestone=M3 depends_on=PROVIDER-04-T02,OBS-03-T02,DB-04-T03 mode=parallel locks=provider-contracts,backend-domain,agent-artifacts -->
- [ ] **Implement evidence/ledger/cost handoff —** Input: eligible raw results, and OBS-03 complete reservation/reconciliation cost chain; implemented EvidenceIngestService sole-writer interface. Operation: ingest captures through sole writer, construct typed success/hash, and reconcile ledger/cost. Output: evidence-backed response. Test evidence: failure injection and total/hash equality. Failure behavior: omit failed item or fail whole invalid set without partial artifact acceptance.
<!-- roadmap-task id=PROVIDER-04-T04 milestone=M3 depends_on=PROVIDER-04-T03 mode=parallel locks=provider-contracts -->
- [ ] **Implement capture and fixture modes —** Input: sanitized live result sets. Operation: sign immutable fixtures and replay with network disabled. Output: M3 evaluation inputs. Test evidence: tamper, extra-field, cross-capability, zero-network tests. Failure behavior: promotion blocked.
<!-- roadmap-task id=PROVIDER-04-T05 milestone=M3 depends_on=PROVIDER-04-T04 mode=parallel locks=provider-contracts -->
- [ ] **Prove replacement/authority boundary —** Input: fake adapter/import graph. Operation: run shared parity and no-credential/state/send checks. Output: replacement evidence. Test evidence: contract suite and secret/PII log scan. Failure behavior: adapter disabled.

## Test strategy

- **Contract `test_search_success_requires_exact_payload_identity_hash_and_evidence`:** no optional evidence/hash.
- **Domain `test_blocked_domain_wins_and_no_non_allowlisted_uri_survives`:** IDNA/subdomain/port/credential vectors.
- **Quota `test_brave_rate_headers_reconcile_without_hidden_retry`:** exact raw call count.
- **Cancellation `test_search_cancel_stops_before_next_ingest_or_handoff`:** no partial accepted artifact.
- **Fixture `test_search_fixture_is_zero_network_and_byte_reproducible`:** signed hashes.
- **Authority `test_search_port_cannot_reach_contacts_repository_commands_or_gmail`:** graph proof.

## Security, privacy, compliance, idempotency, observability, and cost

The key is server-only and logs are body/header allowlisted. Queries are minimized and must not contain addresses, personal identifiers, secrets, or message content. Search captures are hostile `SENSITIVE_SHORT`; evidence links/business artifacts follow DB-06. Request/config hashes prevent accidental repeats but no provider idempotency is claimed. Telemetry records call/request/config IDs, domain hashes, counts, status/error, duration, rate headers, currency cost, and ILS projection—not query text, snippets, URLs with sensitive parameters, or content.

## Failure, rollback, and operator recovery

Disable search on key leak, unsafe URI escape, schema drift, unexplained billing, or provider terms change. Rotate key, quarantine affected captures, revoke dependent artifact acceptances through audited commands, and rerun fixtures/evals. Rollback selects a prior promoted provider operation version for new runs; old evidence remains immutable and provider-labeled.

## Acceptance and retained evidence

- [ ] `search.query` request/result/fixture/hash/error/timeout/ledger semantics are byte-exact with AGENT-01.
- [ ] All successful items have DB-04 evidence IDs/hashes and pass strict allow/block/HTTPS rules.
- [ ] Live and fixture modes are explicit; fixture replay is zero-network.
- [ ] Provider credentials/objects and mutation/contact/send authority are unreachable.

Retain protocol/schema/digest snapshots, provider translation/status/domain fixtures, quota/cost reconciliation, signed captures, zero-network proof, authority graph, telemetry/secret/PII scan, provider terms review, and official-source access date.

## Dependencies and next deliverable

PROVIDER-04 depends on AGENT-01 and DB-04/05. It unlocks [PROVIDER-05](05-page-fetching-and-extraction.md) capture of selected results and the AGENT-04 recorded suite; it does not establish claim truth or M4 acceptance.
