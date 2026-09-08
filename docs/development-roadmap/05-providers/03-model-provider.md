# Structured Model Provider

**Document ID:** PROVIDER-03
**Status:** Planned M3 provider; no model client, prompt registry, live call, or fixture adapter exists today
**Milestone:** M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PROVIDER-03-T01 -> PROVIDER-03-T02 -> PROVIDER-03-T03 -> PROVIDER-03-T04 -> PROVIDER-03-T05 -> PROVIDER-03-T06`; cross-document task Inputs `PROVIDER-03-T01 <- AGENT-01-T01,DB-01-T01; PROVIDER-03-T05 <- AGENT-10-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [AGENT-01 exact capability contracts](../04-agents/01-agent-runtime-and-contracts.md#exact-provider-capability-wire-and-fixture-contracts), DB-01 digest rules, DB-04/05 ledgers, and promoted configuration gates
**Outputs:** Byte-exact `model.complete_structured` protocol, OpenAI Responses adapter, typed failures, live-capture/fixture modes, cost and replacement contract
**Unlocks:** Offline candidate capture and all ten specialist promotions including Lead Discovery and Global Learning
**Risk:** High
**Complexity:** L

## Outcome and timing

One exact immutable configuration authorized by product promotion or the bounded isolated M3 evaluation-only candidate rule makes one bounded structured model request and returns AGENT-01's exact typed union. The initial live adapter uses the OpenAI Responses API with strict JSON Schema; the application contract does not expose OpenAI objects or credentials and can be replaced only by passing byte/semantic parity fixtures.

## Current repository state

Pydantic AI/Pydantic Evals dependencies are locked but unused. There is no model/provider configuration, OpenAI SDK/client, prompt/schema registry, provider ledger, cost entry, fixture capture, or agent execution. Everything below is planned.

## Scope and non-goals

In scope: exact AGENT-01 wire family, deterministic method mapping, model/prompt/schema translation, deadlines/cancellation, provider errors, usage/cost, fixtures, data minimization, quotas, and replacement. Non-goals: provider-native tools, web/file/code/computer tools, conversations, hidden follow-up loops, background responses, free-form output, model-selected models, agent credentials, policy/business decisions, or automatic artifact acceptance.

## Exact planned implementation surfaces

Create `providers/model/contracts.py`, `providers/model/openai_responses.py`, `providers/model/fixtures.py`, `providers/model/errors.py`, and composition from the immutable `AgentConfigurationRefV1` with separately checked product-promotion or isolated M3 evaluation-only candidate authority. Credentials live only in provider composition. The Python-to-wire mapping is exact:

| Python protocol/method | Frozen capability | Exact request / success / failure / fixture | Literal success payload identity |
| --- | --- | --- | --- |
| `StructuredModelProvider.complete_structured` | `model.complete_structured` | `ModelCompleteStructuredRequestV1` (`provider.model_complete.request.v1`) / `ModelCompleteStructuredResponseV1` (`provider.model_complete.response.v1`) / `ModelCompleteStructuredFailureV1` (`provider.model_complete.failure.v1`) / `ModelCompleteStructuredFixtureV1` inside `provider.capability_fixture.v1` | `ModelCompleteStructuredPayloadV1`, `payload_schema_version="provider.model_complete.payload.v1"` |

The request fields, strict types, and semantics are byte-identical to AGENT-01: capability/context, `timeout_ms=1..120_000`, model provider/name/version, prompt version/hash, input schema/payload, output schema version, `max_output_tokens=1..10_000`, decimal temperature `0..2` with three places, and optional seed. Composition default is `45_000 ms`; the earlier of request timeout and `context.deadline_at` wins. No alias capability or optional success hash is legal.

### OpenAI Responses translation and result construction

The selected adapter issues `POST /v1/responses` with the exact authority-validated model identifier; developer instructions reconstructed from the immutable prompt whose RFC 8785 hash equals `prompt_hash`; the canonical input envelope; `text.format={type:"json_schema",name:output_schema_version,schema:registered_schema,strict:true}`; `max_output_tokens`; compatible temperature/seed only when the signed immutable model capability manifest proves support; `store=false`; `background=false`; no conversation/previous response; no tools; and truncation disabled. OpenAI documents Responses JSON output/status/usage and `store`: [create a response](https://developers.openai.com/api/reference/cli/resources/responses/methods/create). JSON Schema structured output is preferred over legacy JSON mode: [Responses formats](https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses).

Only `status=completed`, exactly one non-refusal structured output, exact registered `output_schema_version`, strict Pydantic validation, and no extra output item can succeed. `failed`, `cancelled`, `incomplete`, refusal, missing usage, duplicate output, schema mismatch/coercion, or trailing free text is a typed failure. The adapter never repairs JSON itself; a specialist's separately budgeted second/third model request is a new provider call/ledger row controlled by `AgentExecutionService`.

On success, construct `ModelCompleteStructuredPayloadV1`; compute `payload_hash=hex(SHA-256(RFC8785_UTF8({"schema_version":"provider.model_complete.payload.v1","payload":payload})))`; create exact success meta and response; then compute AGENT-01 request/response/ledger hashes using `provider.request.v1`, `provider.response.v1`, and `provider.usage.v1`. Every hash validates before the result leaves the adapter. Provider request ID, input/output tokens, latency, original provider-currency cost, and response hash are mandatory in `ProviderUseLedgerEntryV1`/`cost_entries` reconciliation.

### Exact errors, retry, quota, cancellation, and offsets

The only non-success `AgentErrorCode` values are: `DEPENDENCY_UNAVAILABLE`, `MODEL_TIMEOUT`, `MODEL_OUTPUT_INVALID`, `MODEL_REFUSAL`, `MODEL_BUDGET_EXHAUSTED`, `COST_BUDGET_EXHAUSTED`, `CANCELLED`, and `INTERNAL_ERROR`. Mapping is deterministic:

| Provider observation | Shared error | Retry classification |
| --- | --- | --- |
| authentication/permission/unknown or execution-mode-ineligible model/configuration, unsupported temperature/seed/schema | `DEPENDENCY_UNAVAILABLE` | no retry; configuration/operator repair |
| deadline/SDK timeout | `MODEL_TIMEOUT` | bounded only when no response/charge acceptance evidence exists and workflow budget permits |
| 429 or provider quota before call admission | `MODEL_BUDGET_EXHAUSTED` | no immediate adapter retry; application rate/budget window owns later attempt |
| refusal output | `MODEL_REFUSAL` | no automatic retry |
| incomplete/malformed/extra/schema-invalid output | `MODEL_OUTPUT_INVALID` | only the specialist's explicit schema-repair request budget may continue |
| cancellation before/after call | `CANCELLED` | terminal for this call; no partial artifact |
| 5xx/transport without a timeout or impossible SDK response | `DEPENDENCY_UNAVAILABLE` or `INTERNAL_ERROR` by frozen mapping | bounded only under AGENT-01 no-accepted-result/cost rule |

Set SDK retries to zero so hidden retries cannot violate model-request/cost ceilings. Application retry is AGENT-01's finite rule: only dependency unavailable/model timeout may be bounded and every actual network request gets a distinct call ID/ledger/cost record. Check cancellation before credential use, immediately before HTTP, after HTTP, after schema validation, and before handoff. A timeout with uncertain provider charge opens a cost discrepancy and is not retried until reconciled.

Provider quotas/rate headers feed a versioned limiter per project/model; `ExecutionCeilingsV1` and reserved budget are stricter. OpenAI response IDs/request IDs/status/usage are evidence, not business authority. Any provider-returned source text is NFC-normalized; any byte offsets are converted to zero-based half-open Unicode code-point indexes over the NFC string before specialist typed construction.

### Modes, fixtures, replacement, example, and authority

`LIVE_CAPTURE` is permitted only for isolated M3 candidate generation with provider credential composition, a prior budget reservation, exact code-bound schema/prompt/model configuration frozen and operator-signed by AGENT-10 for evaluation only, with current provider/legal/cost approval and every original execution ceiling; product promotion is not required for this isolated candidate call, but product composition must reject this context before credential access, and sanitized capture. `RECORDED_FIXTURE` accepts only `ModelCompleteStructuredFixtureV1`, recomputes request/response/expected-ledger/fixture hashes, disables the network client, and drives Pydantic Evals. Fixture output remains immutable `EVALUATION_VERSIONED`.

The fixture contains the exact strict request and result; `response_hash` is present even for failure and covers the exact union branch. A replacement provider must reproduce every schema literal, payload hash, meta/outcome/error allowlist, token/cost ledger, timeout bound, cancellation point, NFC/span behavior, and fixture digest. Model/provider identity remains in the configuration and ledger; semantics cannot widen.

```json
{
  "schema_version": "provider.model_complete.request.v1",
  "capability": "model.complete_structured",
  "context": {"provider_call_id":"8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d","operation_version":"openai-responses.v1","deadline_at":"2026-08-28T00:02:00Z"},
  "timeout_ms": 45000,
  "model_provider": "openai",
  "model_name": "gpt-5.4",
  "model_version": "gpt-5.4",
  "prompt_version": "idea-discovery.v1",
  "prompt_hash": "1111111111111111111111111111111111111111111111111111111111111111",
  "input_schema_version": "idea.discovery.input.v1",
  "input_payload": {"brief_ref":"brief-v1"},
  "output_schema_version": "idea.candidate.output.v1",
  "max_output_tokens": 1800,
  "temperature": 0,
  "seed": null
}
```

```json
{
  "schema_version": "provider.model_complete.response.v1",
  "capability": "model.complete_structured",
  "result_type": "SUCCESS",
  "meta": {"provider_call_id":"8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d","provider_request_id":"resp_01","outcome":"SUCCEEDED","started_at":"2026-08-28T00:00:00Z","finished_at":"2026-08-28T00:00:10Z","input_tokens":100,"output_tokens":10,"cost_minor":1,"currency":"USD"},
  "payload_schema_version": "provider.model_complete.payload.v1",
  "payload": {"output_schema_version":"idea.candidate.output.v1","output_payload":{"candidates":[]}},
  "payload_hash": "c04edfc0e8d61a83346d0234f00427a508e32b1bc095d137a4f747c3db5d2582"
}
```

Agents receive only `StructuredModelProvider`, never the API key/client, and cannot choose policy/approval/budget/suppression, mutate state, call Gmail/`SendGateway`, or turn model text into authority. Telemetry contains safe run/call/request/config/model-version hashes, status/error, duration, tokens, and currency cost—not prompts, inputs, outputs, evidence content, keys, or hidden reasoning.

The configuration registry covers IdeaBrief, MarketResearchReport, OfferPackage, LeadDiscoveryCandidate, LeadResearchDossier, phased qualification proposals, ConversationStrategy/EmailDraft, ReplyEvaluation/negotiation proposals, checkpoint recommendations and AgentLearningProposal. Deterministic services materialize their canonical gate-owned outputs. Each call binds its own input snapshot/hash, governing producer strategy and GlobalStrategyPackage/StrategyActivation. Model access never creates a provider send/calendar capability or a second strategy-learning mechanism.

## Ordered implementation tasks

<!-- roadmap-task id=PROVIDER-03-T01 milestone=M3 depends_on=AGENT-01-T01,DB-01-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement exact model protocol —** Input: AGENT-01 family and DB-01 canonicalizer. Operation: encode/import the same strict models, method mapping, literal schemas, digest validation, timeout/default, and error allowlist. Output: provider-neutral protocol. Test evidence: `test_model_capability_wire_is_byte_exact_with_agent01`. Failure behavior: fail construction before a provider call.
<!-- roadmap-task id=PROVIDER-03-T02 milestone=M3 depends_on=PROVIDER-03-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement OpenAI Responses adapter —** Input: document-local candidate configuration/request fixtures, reservation, isolated candidate credential and strict provider request contract. Operation: translate to one no-tool/no-store strict-schema response and map result/meta/usage/errors; implement the evaluation-only adapter with fake HTTP verification and no product activation; only the bounded AGENT-10 capture runner may make fresh candidate-network calls. Output: executable isolated candidate-model adapter and exact result union; no promoted product activation. Test evidence: fake HTTP status/status-output/refusal/schema/usage matrix; fake-HTTP execution of a fresh unpromoted signed candidate-configuration fixture succeeds under isolated evaluation authority with all ceilings intact; the identical context fails product composition before credential access; missing signature/reservation, drift and non-model/product authority fail closed. Failure behavior: typed failure; no partial artifact.
<!-- roadmap-task id=PROVIDER-03-T03 milestone=M3 depends_on=PROVIDER-03-T02 mode=parallel locks=provider-contracts -->
- [ ] **Implement ceilings and cancellation —** Input: run/provider deadlines and limiter. Operation: disable SDK retry, reserve before call, stop at every boundary, and reconcile actual ledger/cost. Output: bounded call evidence. Test evidence: `test_model_deadline_cancel_rate_token_and_cost_boundaries_have_exact_call_count`. Failure behavior: no next call; discrepancy visible.
<!-- roadmap-task id=PROVIDER-03-T04 milestone=M3 depends_on=PROVIDER-03-T03 mode=parallel locks=provider-contracts -->
- [ ] **Implement signed live-capture/fixture adapters —** Input: sanitized candidate capture. Operation: build fixture, recompute all hashes, replay with network physically unavailable. Output: deterministic evaluation input. Test evidence: tamper/cross-capability/extra-field/zero-network tests. Failure behavior: fixture rejected; version not promoted.
<!-- roadmap-task id=PROVIDER-03-T05 milestone=M3 depends_on=PROVIDER-03-T04,AGENT-10-T05 mode=serial locks=provider-contracts,milestone-gate -->
- [ ] **Bind promoted product model activation —** Input: implemented candidate adapter, recorded fixture compatibility, and AGENT-10 immutable approved PromotionManifestV1/configuration/registry binding; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: compose the product adapter only from the exact eligible promoted configuration and enforce reservation, credential, model/schema and no-tool/no-store boundaries at every call; reject unpromoted or evaluation-only contexts; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: promoted product model-adapter activation contract bound to one immutable eligible configuration, or a retained disabled rejection. Test evidence: unpromoted/stale/spliced configuration, disabled evaluation credential, missing reservation and exact promoted positive fixtures. Failure behavior: product model calls remain disabled; candidate evaluation authority never grants product authority.
<!-- roadmap-task id=PROVIDER-03-T06 milestone=M3 depends_on=PROVIDER-03-T05 mode=parallel locks=provider-contracts -->
- [ ] **Prove replacement and authority seams —** Input: fake second provider and object/import graph. Operation: run shared contract suite and assert no credential/state/send reachability. Output: replaceable least-authority boundary. Test evidence: provider parity and static/runtime graph. Failure behavior: adapter/config promotion blocked.

## Test strategy

- **Contract `test_model_success_requires_literal_payload_schema_and_rfc8785_hash`:** missing/wrong/extra fields fail.
- **Errors `test_openai_status_and_output_matrix_maps_only_model_error_allowlist`:** no provider-native name escapes.
- **Cancellation `test_cancel_after_provider_response_before_persistence_returns_no_artifact`:** ledger remains reconcilable.
- **Cost `test_model_ledger_usage_equals_agent_run_and_cost_entry`:** original currency plus ILS reporting evidence.
- **Fixture `test_model_fixture_request_response_ledger_and_content_hashes_are_byte_exact`:** zero network.
- **Authority `test_model_adapter_cannot_reach_repository_commands_policy_or_gmail`:** dependency proof.

## Security, privacy, compliance, idempotency, observability, and cost

Use a dedicated server-side project key with minimum project permissions and rate/cost caps. `store=false` minimizes API-side state but is not a legal-retention guarantee; approved provider terms/data controls are a promotion gate. Inputs are task-minimized and restricted evidence is excluded unless explicitly allowed. Application command/config/input hashes prevent accidental repeats; the provider is not claimed idempotent. Run/evaluation evidence is `EVALUATION_VERSIONED`, artifacts/links `BUSINESS_ACTIVE`, captures `SENSITIVE_SHORT`, and cost/event evidence `SAFETY_LONG` under DB-06.

## Failure, rollback, and operator recovery

Disable the adapter on key leak, schema drift, impossible usage, unknown output item, repeated timeout, or cost mismatch. Rotate credentials, preserve sanitized ledger/request IDs, reconcile invoice/cost, and rerun fixtures before re-enable. Rollback selects the prior promoted immutable configuration for new runs; existing artifacts/evaluations are never rewritten. Unknown provider behavior becomes `INTERNAL_ERROR` and blocks promotion rather than being guessed.

## Acceptance and retained evidence

- [ ] AGENT-01 request/success/failure/fixture bytes, schema literals, hashes, error allowlist, timeout, ledger, and cancellation semantics are exact.
- [ ] One live call cannot become a hidden loop or gain tools/state/send authority.
- [ ] OpenAI translation, usage/cost, refusal/incomplete handling, and safe telemetry are explicit and fixture-proven.
- [ ] Recorded mode is zero-network and provider replacement cannot widen capability semantics.

Retain protocol/schema snapshots, DB-01 hash vectors, provider translation fixtures, status/error/cancel/budget matrix, signed candidate captures, zero-network evidence, ledger/cost reconciliation, secret/content scan, replacement suite, and official-source access date.

## Dependencies and next deliverable

PROVIDER-03 depends on AGENT-01 and DB-01/04/05. Passing its offline contracts unlocks specialist M3 candidate capture and AGENT-10 evaluation; it does not itself promote a model or authorize any business action.
