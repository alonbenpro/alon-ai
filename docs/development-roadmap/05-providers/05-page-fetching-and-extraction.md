# Evidence Read and Safe Page Extraction Providers

**Document ID:** PROVIDER-05
**Status:** Planned M3 capabilities; no evidence reader, safe fetcher, extractor, or fixture adapter exists today
**Milestone:** M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PROVIDER-05-T01 -> PROVIDER-05-T02 -> PROVIDER-05-T03 -> PROVIDER-05-T04 -> PROVIDER-05-T05`; cross-document task Inputs `PROVIDER-05-T01 <- AGENT-01-T01,DB-01-T01; PROVIDER-05-T03 <- OBS-03-T02,DB-04-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): [AGENT-01 capability contracts](../04-agents/01-agent-runtime-and-contracts.md#exact-provider-capability-wire-and-fixture-contracts), [DB-04](../02-database/04-agent-artifacts-and-evidence.md), and PROVIDER-04 search captures
**Outputs:** Byte-exact `evidence.read` and `page.extract`, SSRF-safe HTTP extraction, NFC/code-point normalization, capture lifecycle, fixtures, and replacement seams
**Unlocks:** Evidence-backed AGENT-02/04/05/09 evaluations and M4/M5 source capture
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Agents may read one immutable accepted/captured evidence item or request one bounded HTTPS extraction. They cannot fetch arbitrary networks, follow instructions in content, log in, click, submit forms, execute scripts, or receive raw restricted data without explicit scope. The application returns AGENT-01's exact typed unions only after evidence/capture integrity is established.

## Current repository state

DB-04 tables and services are planned but absent; there is no fetch/extraction library, capture store, URL policy, SSRF defense, sanitizer, NFC/span conversion, evidence read port, provider ledger, or fixture. Current `httpx` is used by no product provider.

## Scope and non-goals

In scope: two exact capability families, local immutable evidence access, public HTTPS GET, DNS/redirect controls, MIME/size/time limits, deterministic text extraction/hash, prompt-injection signal, redaction, fixtures, and cost/telemetry. Non-goals: general browser automation, JavaScript rendering, authentication/cookies, robots/terms bypass, file/upload protocols, recursive crawl, attachments, bulk personal/contact harvesting, guessing identities/linkages, or content directly becoming trusted/accepted.

## Exact planned implementation surfaces

Create `providers/evidence/contracts.py`, `providers/evidence/reader.py`, `providers/page/contracts.py`, `providers/page/http_extractor.py`, shared capture/fixture modules, and `PageExtractionCapabilityService`. `EvidenceIngestService` is the only `evidence_items` writer; `RetentionCommandService` alone purges/redacts.

| Python method | Capability | Exact request / success / failure / fixture | Literal payload identity | Default/max |
| --- | --- | --- | --- | --- |
| `EvidenceReadPort.read` | `evidence.read` | `EvidenceReadRequestV1` (`provider.evidence_read.request.v1`) / `EvidenceReadResponseV1` (`provider.evidence_read.response.v1`) / `EvidenceReadFailureV1` (`provider.evidence_read.failure.v1`) / `EvidenceReadFixtureV1` (`provider.capability_fixture.v1`) | `EvidenceReadPayloadV1`, `provider.evidence_read.payload.v1` | 5,000/10,000ms |
| `PageExtractionPort.extract` | `page.extract` | `PageExtractRequestV1` (`provider.page_extract.request.v1`) / `PageExtractResponseV1` (`provider.page_extract.response.v1`) / `PageExtractFailureV1` (`provider.page_extract.failure.v1`) / `PageExtractFixtureV1` (`provider.capability_fixture.v1`) | `PageExtractPayloadV1`, `provider.page_extract.payload.v1` | 12,000/30,000ms |

All AGENT-01 fields/bounds are exact: evidence ID/hash, `max_bytes=1..1_000_000`, restricted flag; or restricted `source_locator` up to 8,192 bytes, nonempty allowed domains, `max_response_bytes=1..5_000_000`, allowed MIME types; both include context and `timeout_ms=1..max`. Success returns only DB-04's sanitized `citation_uri`. Success `payload_schema_version` and `payload_hash` are mandatory and use the literal table identities; failure has no payload/hash. Complete request/result/fixture hashes use the DB-01 RFC 8785 envelopes, and each capability reconciles one exact `ProviderUseLedgerEntryV1`.

### `evidence.read` operation

`EvidenceReadService` verifies the DB-04 row exists, exact content hash matches, redaction state is `RAW_RESTRICTED` or `REDACTED` (never `PURGED`), capture reference resolves inside the protected store, caller scope permits restricted access when requested, decompressed serialized `content_payload` is within `max_bytes`, and capture hash still matches. It returns only the registered allowlisted representation; no ORM/provider object or neighboring evidence is reachable. `allow_restricted=false` rejects `RAW_RESTRICTED`. Reads do not mutate last-access fields; safe access audit is separate.

Allowed errors are exactly `DEPENDENCY_UNAVAILABLE`, `TOOL_TIMEOUT`, `TOOL_RESULT_INVALID`, `EVIDENCE_MISSING`, `CANCELLED`, and `INTERNAL_ERROR`. Hash mismatch/purged/missing/unauthorized restricted content maps to `EVIDENCE_MISSING` with safe detail; corrupt payload maps to `TOOL_RESULT_INVALID`; storage outage to dependency unavailable. No automatic retry occurs inside the capability.

### `page.extract` safe fetch and extraction

1. Parse the URI once; require absolute `https`, port 443/default, no userinfo/fragment, normalized IDNA host, allowed-domain match, and no blocked/private/special literal.
2. Resolve all A/AAAA/CNAME results and reject loopback, private, link-local, multicast, broadcast, documentation, carrier-grade NAT, unspecified, and cloud-metadata ranges. Pin the validated address for the connection and verify TLS hostname. Egress policy independently blocks internal destinations.
3. Use GET with no cookies/auth/referer, explicit safe User-Agent/Accept, connect/read/write/pool budgets within `timeout_ms`, streaming byte count, decompression ratio/byte cap, and no client auto-retry.
4. Do not auto-follow redirects. At most three 301/302/303/307/308 hops may be followed only after repeating full URI/domain/DNS/TLS validation; redirect loops/cross-policy targets fail.
5. Require 2xx and an allowed exact MIME essence; do not content-sniff an absent/unsafe type. Enforce raw and decoded size, charset validation, nesting/node/text limits, and reject binary/polyglot/active payload.
6. Preserve restricted raw capture bytes by hash/reference, extract only visible semantic text with a versioned deterministic extractor, normalize text to NFC, sanitize control characters, identify language, and scan prompt-injection indicators. Detection returns `PROMPT_INJECTION_DETECTED`; it never asks a model whether content is safe.
7. `EvidenceIngestService` encrypts the raw locator, applies `citation.uri.v1`, writes DB-04 evidence, and the capability builds `PageExtractPayloadV1` with exact evidence/sanitized-citation/content/capture/MIME/language/extracted-text hashes. It does not return the raw locator or text body in the capability response.

OWASP recommends allowlisting, validating redirects/DNS destinations, and disabling unsafe automatic redirects for SSRF: [SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html). HTTP URI, media type, and redirect semantics follow [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html).

`content_hash=hex(SHA-256(decoded entity bytes))`. `extracted_text_hash` is the DB-01 envelope digest for schema `provider.page_extracted_text.v1` and payload `{"text": NFC_text}`. Capability `payload_hash` and complete request/response/usage/fixture hashes use their frozen AGENT-01 schema envelopes. If a parser/provider supplies byte offsets, convert against decoded source to zero-based half-open Unicode code-point indexes over exact NFC text before typed construction; offsets that split a scalar, change under normalization without deterministic mapping, overlap, or leave bounds cause `TOOL_RESULT_INVALID`.

Allowed page failures are exactly `DEPENDENCY_UNAVAILABLE`, `TOOL_TIMEOUT`, `TOOL_RESULT_INVALID`, `TOOL_BUDGET_EXHAUSTED`, `COST_BUDGET_EXHAUSTED`, `CANCELLED`, `INTERNAL_ERROR`, and `PROMPT_INJECTION_DETECTED`. HTTP 408/429/5xx/transport maps to timeout/budget/dependency by the frozen matrix but has no hidden retry; unsafe URI/MIME/redirect/DNS/content/parser output maps to result invalid. Cancellation is checked before DNS, connect, every redirect, every stream chunk, parse, ingest, and handoff.

### Modes, fixtures, replacement, examples, and authority

`LIVE_CAPTURE` for `evidence.read` is a protected local-store read; for `page.extract` it is the controlled fetch above with prior source-policy/cost admission. `RECORDED_FIXTURE` accepts exact `EvidenceReadFixtureV1` or `PageExtractFixtureV1`, verifies all hashes, and instantiates no object-store/network client. Fixture captures are immutable and sensitivity-scoped.

Fixtures cover DNS rebinding, IPv4/IPv6 encodings, metadata endpoints, userinfo, IDNA, redirect chains, MIME lies, compression bombs, charset errors, oversized/slow streams, malformed DOM, injection text, cancellation, NFC decomposed accents/Hebrew/emoji, byte-offset conversion, purged/restricted/hash-mismatched evidence, and zero-network replay. A replacement extractor/provider must reproduce exact union schemas, byte/hash definitions, URL security, bounds, errors, cancellation, evidence identity, and NFC spans; changing extraction text requires a new operation version and evaluation.

```json
{
  "schema_version":"provider.evidence_read.request.v1","capability":"evidence.read",
  "context":{"provider_call_id":"8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d","operation_version":"evidence-read.v1","deadline_at":"2026-08-28T00:00:10Z"},
  "timeout_ms":5000,"evidence_item_id":"42d704c7-c01f-4aeb-adb1-e8bc2fb338ce","expected_content_hash":"1111111111111111111111111111111111111111111111111111111111111111","max_bytes":10000,"allow_restricted":false
}
```

```json
{
  "schema_version":"provider.evidence_read.response.v1","capability":"evidence.read","result_type":"SUCCESS",
  "meta":{"provider_call_id":"8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d","provider_request_id":null,"outcome":"SUCCEEDED","started_at":"2026-08-28T00:00:00Z","finished_at":"2026-08-28T00:00:01Z","input_tokens":0,"output_tokens":0,"cost_minor":0,"currency":"USD"},
  "payload_schema_version":"provider.evidence_read.payload.v1",
  "payload":{"evidence_item_id":"42d704c7-c01f-4aeb-adb1-e8bc2fb338ce","content_hash":"1111111111111111111111111111111111111111111111111111111111111111","capture_ref":"captures/evidence/42d704c7","redaction_state":"REDACTED","content_payload":{"text":"Public guidance."}},
  "payload_hash":"f08f74d51b7136e9d6a1c81cd6d3f02ef3d39cca4e86d3be4052e7aef371262e"
}
```

```json
{
  "schema_version":"provider.page_extract.request.v1","capability":"page.extract",
  "context":{"provider_call_id":"9b85bc7c-cf60-45a9-9925-6c8b82b88e0d","operation_version":"safe-http-extract.v1","deadline_at":"2026-08-28T00:00:30Z"},
  "timeout_ms":12000,"source_locator":"https://www.gov.il/en/pages/example","allowed_domains":["gov.il"],"max_response_bytes":1000000,"allowed_mime_types":["text/html"]
}
```

```json
{
  "schema_version":"provider.page_extract.failure.v1","capability":"page.extract","result_type":"FAILURE",
  "meta":{"provider_call_id":"9b85bc7c-cf60-45a9-9925-6c8b82b88e0d","provider_request_id":null,"outcome":"FAILED","started_at":"2026-08-28T00:00:00Z","finished_at":"2026-08-28T00:00:01Z","input_tokens":0,"output_tokens":0,"cost_minor":0,"currency":"USD"},
  "safe_error_detail":"deterministic content-safety rule rejected the extraction","error_fingerprint":"3333333333333333333333333333333333333333333333333333333333333333","error_code":"PROMPT_INJECTION_DETECTED"
}
```

Agents cannot access the HTTP/object-store client, credentials, repositories, command services, Gmail/`SendGateway`, or mutation/policy/approval/budget/suppression authority.

### Canonical research and source-field scope

MarketResearchReport, LeadResearchDossier, CheckpointEvidenceBundle and AgentLearningProposal consume captured evidence only by accepted ID/version/hash and permitted scope. A reviewed public source may support a named business owner/decision-maker or role only under an explicit source/field/privacy policy and matching business-person linkage evidence. Extraction never guesses contacts or treats any scraped person as a lead. The deterministic provider field allowlist/redaction policy is server-owned and pinned to source/terms version; agent arguments cannot widen it. FACT/ESTIMATE/UNKNOWN labels and source time/confidence remain with downstream fields. Global learning gets only approved minimized evidence from closed checkpoints.

## Ordered implementation tasks

<!-- roadmap-task id=PROVIDER-05-T01 milestone=M3 depends_on=AGENT-01-T01,DB-01-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement exact evidence/page contracts —** Input: AGENT-01 families and DB-01 canonicalizer. Operation: preserve fields/literals/unions/timeouts/error allowlists/hash/fixture/ledger semantics. Output: two read-only ports. Test evidence: `test_evidence_and_page_wire_parity_with_agent01`. Failure behavior: reject before storage/network.
<!-- roadmap-task id=PROVIDER-05-T02 milestone=M3 depends_on=PROVIDER-05-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement scoped evidence reader —** Input: strict request and immutable capture. Operation: verify identity/hash/redaction/scope/size and return allowlisted payload. Output: exact success/failure. Test evidence: missing/purged/restricted/corrupt/cancel matrix. Failure behavior: no content leakage.
<!-- roadmap-task id=PROVIDER-05-T03 milestone=M3 depends_on=PROVIDER-05-T02,OBS-03-T02,DB-04-T03 mode=parallel locks=provider-contracts,backend-domain,agent-artifacts -->
- [ ] **Implement safe HTTP extractor —** Input: strict URI/source policy/reservation; implemented EvidenceIngestService sole-writer interface. Operation: enforce DNS/TLS/redirect/MIME/stream/parse/injection/NFC bounds and ingest through sole writer. Output: capture-backed page payload. Test evidence: SSRF and hostile-content suite. Failure behavior: abort/quarantine; no dependent artifact acceptance.
<!-- roadmap-task id=PROVIDER-05-T04 milestone=M3 depends_on=PROVIDER-05-T03 mode=parallel locks=provider-contracts -->
- [ ] **Implement hash/span and fixture gates —** Input: Unicode/raw/text fixtures and sanitized captures. Operation: reproduce digests, convert offsets, sign fixtures, and replay without network. Output: deterministic evaluation data. Test evidence: independent hash encoders and Unicode boundary suite. Failure behavior: reject fixture/result.
<!-- roadmap-task id=PROVIDER-05-T05 milestone=M3 depends_on=PROVIDER-05-T04 mode=parallel locks=provider-contracts -->
- [ ] **Prove replacement/authority and retention —** Input: fake extractor, object/import graph, purge holds. Operation: run parity, no-credential/state/send reachability, and retention closure tests. Output: least-authority provider evidence. Test evidence: graph, log/PII scan, purge/incident fixtures. Failure behavior: provider disabled.

## Test strategy

- **SSRF `test_page_fetch_rejects_private_dns_rebinding_and_unsafe_redirects`:** application plus egress defenses.
- **Contract `test_both_successes_require_literal_payload_schema_and_hash`:** opposite/extra branch fields fail.
- **Unicode `test_extract_offsets_are_nfc_code_point_half_open_before_typed_models`:** exact conversion vectors.
- **Evidence `test_restricted_purged_or_hash_mismatched_capture_never_returns_payload`:** safe failure.
- **Cancellation `test_cancel_at_each_fetch_ingest_boundary_leaves_no_partial_success`:** ledger reconciles.
- **Fixture `test_page_and_evidence_fixtures_are_zero_network_byte_exact`:** tamper proof.

## Security, privacy, compliance, idempotency, observability, and cost

Outbound access is allowlisted at application and network layers. Source content is hostile and never instructions. Captures use `SENSITIVE_SHORT`; access/validation/cost/event evidence follows DB-06. URI/capture/request hashes prevent accidental duplicate ingestion, not source idempotency. Telemetry includes safe call/evidence/domain hashes, MIME/language, byte/text counts, redirect count, duration, status/error, and cost—never query parameters, source text, raw bytes, credentials, or restricted refs. Self-operated fetch has zero provider fee but storage/network/CPU cost remains budgeted and recorded where material.

## Failure, rollback, and operator recovery

Disable fetch on any SSRF escape, parser compromise, unexplained hash drift, content leak, or operation-version mismatch. Quarantine captures, revoke dependent acceptances through audited commands, rotate compromised infrastructure secrets, and rerun security/fixture gates before re-enable. Rollback selects the prior extractor version; old evidence retains its exact provider/operation/hash identity.

## Acceptance and retained evidence

- [ ] Both AGENT-01 capability families are byte/semantic exact, including error/time/hash/fixture/ledger rules.
- [ ] Fetch cannot reach internal networks, unsafe redirects/MIME/content, credentials, or browser actions.
- [ ] Every page success has one DB-04 evidence identity and reproducible raw/text/payload hashes.
- [ ] All source text/spans are NFC/code-point normalized before typed construction.
- [ ] Fixture mode is zero-network and agents have no mutation/send/credential authority.

Retain schema/digest vectors, SSRF/DNS/redirect/MIME/parser fixtures, Unicode/span vectors, signed live captures, zero-network proof, ledger/cost/retention evidence, authority graph, safe telemetry scan, and source-access date.

## Dependencies and next deliverable

PROVIDER-05 depends on DB-04/05 and AGENT-01 contracts. It unlocks evidence-backed M3 suites and M4/M5 capture, but only deterministic validation/acceptance services may make captures workflow-eligible.
