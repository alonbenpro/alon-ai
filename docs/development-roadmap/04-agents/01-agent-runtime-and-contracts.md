# Agent Runtime, Execution Envelope, and Authority Contracts

**Document ID:** AGENT-01
**Status:** Planned M3 contract; Pydantic AI/Pydantic Evals are locked but unused
**Milestone:** M3
**Owner:** Solo operator
**Prerequisites:** [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [DB-01](../02-database/01-core-data-model.md), [DB-04](../02-database/04-agent-artifacts-and-evidence.md), [DB-05](../02-database/05-audit-events-and-idempotency.md), and accepted M1 runtime evidence
**Outputs:** Versioned Pydantic execution models, dependency/tool authority boundary, reproducible hashes, provider-use ledger, failure taxonomy, finite-run rules, and persistence/event map
**Unlocks:** AGENT-02 through AGENT-10 and M3 offline promotion
**Risk:** Critical
**Complexity:** L

## Outcome and timing

M3 gets one deliberately narrow agent runtime: Pydantic AI executes a single typed request and returns one immutable typed result. Pydantic Evals measures recorded suites. DBOS owns the surrounding finite workflow, while deterministic application services own budgets, validation, artifact acceptance, state transitions, and all provider-side authority.

This is not an autonomous-agent platform. There is no planner loop, recursive delegation, background daemon, mutable memory, or model-authored command. Each run has a frozen input, promoted configuration, explicit tools, attempt/time/token/tool/cost ceilings, cancellation signal, and one terminal result.

## Current repository state

Implemented today: locked `pydantic-ai[dbos]>=2.35.3` and `pydantic-evals>=2.35.3` constraints, an empty `backend/src/alon_ai/agents/__init__.py`, minimal Gmail DTO/protocols, and guarded `SendGateway`. Missing: every model below, Pydantic AI `Agent`, dependency container, tool, prompt registry, artifact registry, execution service, provider ledger, evaluation suite, agent run recorder, and promoted configuration. No current agent can run.

## Scope and non-goals

In scope: exact Pydantic models, frozen version/config records, dependency injection, read-only capability tools, schema/provenance/evidence rules, deterministic hashing, usage/cost accounting, timeouts/cancellation, typed failure, post-validation, persistence/event mapping, offline fixtures, promotion and rollback handoff, observability, and retention.

Non-goals: LangChain, LangGraph, Restate, Prefect, model-selected tools outside an allowlist, direct SQL/ORM sessions, Gmail or `SendGateway`, provider credentials, policy/approval/budget/suppression decisions, automatic retries without workflow ownership, chain-of-thought storage, or business-state mutation.

## Exact planned implementation surfaces

Create `backend/src/alon_ai/agents/contracts.py`, `agents/dependencies.py`, `agents/execution.py`, `agents/registry.py`, `agents/errors.py`, `agents/telemetry.py`, and tests under `backend/tests/unit/agents/` and `backend/tests/contract/agents/`. Agent-specific modules are named in AGENT-02 through AGENT-09. Task 4 must implement provider protocols/adapters matching the capability semantics below; it may reconcile Python protocol names, but cannot silently widen a capability.

The existing persistence targets remain exact: DB-04 `agent_runs`, `artifacts`, `evidence_items`, `artifact_evidence_links`, `artifact_validations`, `artifact_acceptances`, `evaluation_cases`, and `evaluation_results`; DB-01 `workflow_runs`; and DB-05 `cost_entries`, `domain_events`, `audit_events`, and `outbox_messages`. This segment adds no alias table.

### Exact shared Pydantic models

All models use `ConfigDict(extra="forbid", frozen=True, strict=True)`. Strings reject leading/trailing whitespace through validators. UUIDs are UUIDv4. UTC fields require an offset of `+00:00`. `VersionId` matches `^[a-z0-9][a-z0-9._-]{0,63}$`; `Sha256Hex` matches `^[0-9a-f]{64}$`; `JsonPointer` matches `^/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$` and is at most 512 characters.

```python
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

VersionId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
JsonPointer = Annotated[str, Field(min_length=2, max_length=512, pattern=r"^/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$")]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
PayloadT = TypeVar("PayloadT", bound=BaseModel)

class AgentType(StrEnum):
    IDEA_DISCOVERY = "IDEA_DISCOVERY"
    OFFER_DESIGN = "OFFER_DESIGN"
    MARKET_RESEARCH = "MARKET_RESEARCH"
    LEAD_RESEARCH = "LEAD_RESEARCH"
    LEAD_QUALIFICATION = "LEAD_QUALIFICATION"
    OUTREACH_DRAFTING = "OUTREACH_DRAFTING"
    REPLY_CLASSIFICATION = "REPLY_CLASSIFICATION"
    EXPERIMENT_EVALUATION = "EXPERIMENT_EVALUATION"

class ExecutionCeilingsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    timeout_seconds: int = Field(ge=1, le=300)
    max_input_tokens: int = Field(ge=1, le=50_000)
    max_output_tokens: int = Field(ge=1, le=10_000)
    max_tool_calls: int = Field(ge=0, le=32)
    max_model_requests: int = Field(ge=1, le=3)
    max_cost_minor: int = Field(ge=0, le=100_000)
    currency: Currency

class AgentConfigurationRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    agent_type: AgentType
    agent_version: VersionId
    prompt_version: VersionId
    prompt_hash: Sha256Hex
    model_provider: VersionId
    model_name: Annotated[str, Field(min_length=1, max_length=128)]
    model_version: VersionId
    toolset_version: VersionId
    input_schema_version: VersionId
    output_schema_version: VersionId
    post_validator_version: VersionId
    configuration_hash: Sha256Hex

class EvidenceRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    evidence_item_id: UUID
    content_hash: Sha256Hex
    claim_pointer: JsonPointer
    relationship: Literal["SUPPORTS", "CONTRADICTS", "CONTEXT"]
    source_excerpt_hash: Sha256Hex | None = None

class AgentExecutionEnvelopeV1(BaseModel, Generic[PayloadT]):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal["agent.execution.input.v1"]
    agent_run_id: UUID
    experiment_id: UUID
    workflow_run_id: UUID
    workflow_type: VersionId
    workflow_version: VersionId
    workflow_input_schema_version: VersionId
    workflow_input_hash: Sha256Hex
    input_pointer: JsonPointer
    correlation_id: UUID
    causation_id: UUID
    configuration: AgentConfigurationRefV1
    ceilings: ExecutionCeilingsV1
    evidence_refs: tuple[EvidenceRefV1, ...] = Field(max_length=100)
    payload: PayloadT

class ProviderUseLedgerEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal["provider.use.v1"]
    provider_call_id: UUID
    provider: VersionId
    capability: Literal[
        "model.complete_structured", "evidence.read", "search.query",
        "page.extract", "business.search", "business.details"
    ]
    operation_version: VersionId
    request_hash: Sha256Hex
    response_hash: Sha256Hex | None
    evidence_item_ids: tuple[UUID, ...] = Field(max_length=100)
    started_at: datetime
    finished_at: datetime
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_minor: int = Field(ge=0)
    currency: Currency
    outcome: Literal["SUCCEEDED", "FAILED", "CANCELLED", "TIMEOUT"]
    error_code: str | None = Field(default=None, max_length=64)

class AgentUsageV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    tool_call_count: int = Field(ge=0)
    model_request_count: int = Field(ge=0)
    cost_minor: int = Field(ge=0)
    currency: Currency
    duration_ms: int = Field(ge=0)
    provider_uses: tuple[ProviderUseLedgerEntryV1, ...] = Field(max_length=32)

class AgentFailureArtifactV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: Literal["agent.failure.v1"]
    agent_run_id: UUID
    error_code: "AgentErrorCode"
    retry_class: Literal["NO_RETRY", "BOUNDED_RETRY", "OPERATOR_REVIEW"]
    safe_message: Annotated[str, Field(min_length=1, max_length=300)]
    failed_phase: Literal["INPUT", "DEPENDENCY", "TOOL", "MODEL", "VALIDATION", "PERSISTENCE"]
    evidence_refs: tuple[UUID, ...] = Field(max_length=20)
    configuration_hash: Sha256Hex
```

`AgentFailureArtifactV1` is the typed execution failure result, not a DB-04 product `artifacts` row. `AgentRunRecordingService` persists its safe fields to the failed `agent_runs` record. Only if a deterministic application handler fails the owning workflow does it also emit `workflow.run_failed.v1`; otherwise it records safe audit/trace evidence without inventing an agent-failure event. A quality abstention is instead a valid product artifact with `confidence=NULL` and a non-empty `abstention_reason`.

### Canonical digest and version rules

Every digest uses DB-01's exact algorithm: lowercase SHA-256 over UTF-8 RFC 8785 canonical JSON for `{"schema_version":<string>,"payload":<json>}`. Duplicate keys, invalid Unicode, non-I-JSON numbers, NaN, and infinities are rejected before canonicalization.

- `workflow_input_hash` is recomputed from `workflow_runs.input_schema_version/input_snapshot`; `agent_runs.input_snapshot_hash` copies that exact verified hash. It is never an independently invented agent hash.
- The envelope's `input_pointer` selects the specialist payload within the already verified workflow snapshot. The request is rejected if the selected payload is not byte-equivalent to the decoded `payload`.
- Product artifact digest schema strings are `artifact.<artifact_type>.v1`; registry entry `v1 -> artifacts.schema_version=1` is exact. `content_hash` covers only the registered product artifact content, not runtime usage.
- Prompt, configuration, provider request/response, usage, score, and fixture hashes use schema strings `agent.prompt.v1`, `agent.config.v1`, `provider.request.v1`, `provider.response.v1`, `provider.usage.v1`, `evaluation.scores.v1`, and the suite's exact input/expected schema versions.
- Any prompt/model/tool/input/output/post-validator change creates a new `AgentConfigurationRefV1` and immutable evaluation comparison. Upcasters validate old bytes first and transform only in memory.

### Dependency injection and tool authority

`AgentDependenciesV1` contains only `RunContext`, `CancellationSignal`, `UTCClock`, `EvidenceReadPort`, and the exact read-only capability ports selected by the specialist. It never contains a SQLAlchemy session, repository/unit of work, command service, Gmail DTO/port, `SendGateway`, policy/approval/control/budget/suppression service, OAuth/API credential, or unrestricted HTTP client.

Capability semantics are consumer requirements for Task 4:

| Capability | Required semantics | Forbidden widening |
| --- | --- | --- |
| `model.complete_structured` | one promoted model request returning the declared Pydantic result | free-form code execution, hidden follow-up loop, provider credential exposure |
| `evidence.read` | fetch immutable accepted/captured evidence by ID/hash with size/redaction limits | arbitrary DB query, raw restricted capture unless scope explicitly allows |
| `search.query` | bounded allowlisted market query returning result metadata and capture IDs | arbitrary browsing, contact harvesting, mutable search sessions |
| `page.extract` | HTTPS capture by approved URI/ref with scheme/domain/type/size/time limits | browser actions, login, forms, scripts, credential use |
| `business.search` | bounded business candidates with source identity facts | personal-contact discovery or unbounded result pages |
| `business.details` | business-level public facts and provenance for one candidate | personal data guessing, mailbox/contact enrichment, auto-merge |

The execution service registers only named Pydantic AI tools for the selected `toolset_version`. Unknown tool name, capability, or argument fails before a provider call. Tool results are untrusted Pydantic inputs and cannot inject instructions, add tools, change ceilings, or grant authority.

### Exact error taxonomy and finite execution

```python
class AgentErrorCode(StrEnum):
    INPUT_INVALID = "INPUT_INVALID"
    INPUT_DIGEST_MISMATCH = "INPUT_DIGEST_MISMATCH"
    UNSUPPORTED_SCHEMA = "UNSUPPORTED_SCHEMA"
    CONFIG_NOT_PROMOTED = "CONFIG_NOT_PROMOTED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    TOOL_ARGUMENT_INVALID = "TOOL_ARGUMENT_INVALID"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_RESULT_INVALID = "TOOL_RESULT_INVALID"
    TOOL_BUDGET_EXHAUSTED = "TOOL_BUDGET_EXHAUSTED"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    MODEL_REFUSAL = "MODEL_REFUSAL"
    MODEL_BUDGET_EXHAUSTED = "MODEL_BUDGET_EXHAUSTED"
    COST_BUDGET_EXHAUSTED = "COST_BUDGET_EXHAUSTED"
    CANCELLED = "CANCELLED"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    POST_VALIDATION_FAILED = "POST_VALIDATION_FAILED"
    PERSISTENCE_FAILED = "PERSISTENCE_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
```

Only `DEPENDENCY_UNAVAILABLE`, `TOOL_TIMEOUT`, and `MODEL_TIMEOUT` may be `BOUNDED_RETRY`, and only when no paid/provider result was accepted, the workflow's remaining attempt/time/cost budget allows it, and the same command key/config/input is retained. Maximum model requests is `1` by default and `3` only where the specialist document explicitly allows schema-repair attempts. Cancellation is checked before a model/tool call, after each call, and before persistence; provider adapters receive the earlier of run deadline or their shorter operation deadline. Timeout/cancellation never creates an accepted partial artifact.

### Deterministic post-validation and persistence/event map

The agent process returns an in-memory Pydantic result. Deterministic `AgentExecutionService` then checks exact schema/config promotion, digest/pointer equality, evidence existence/hash/redaction, citation pointers/cardinality, no forbidden fields/authority language, ceilings versus ledger, and product-specific invariants. It does not accept artifacts.

On success, `AgentRunRecordingService` closes `agent_runs(SUCCEEDED)` and `ArtifactCommandService` inserts one immutable `artifacts(status=PRODUCED)` row plus links/usage/cost records in application-owned transactions. `artifact.produced.v1` contains exact `artifact_id`, `artifact_type`, integer `schema_version`, and `agent_run_id`. Later `ArtifactValidationService` alone writes `artifact_validations`, links, `VALIDATED/REJECTED`, and `artifact.validated.v1`/`artifact.rejected.v1`; `ArtifactAcceptanceService` or an authenticated operator alone writes acceptance and `artifact.accepted.v1`. Agents are never `actor_type` in `domain_events`/`audit_events`.

Each provider ledger item maps to one idempotent `cost_entries` row (`provider`, capability as `operation`, `agent_run_id`, `usage_json/hash`, provider currency, and ILS reporting conversion evidence). Aggregate totals must equal `agent_runs` usage/cost. Persistence failure leaves no claimed product artifact, marks the run failed only after a safe recovery inspection, and never repeats an accepted paid call blindly.

## Ordered implementation tasks

- [ ] **Implement frozen shared models and registries —** Input: DB-01/04 schemas and the models above. Operation: encode strict types, artifact/config/prompt/tool registries, RFC 8785 digests, and DB-01 golden vectors. Output: importable versioned contracts. Test evidence: `test_agent_contracts_reject_extra_coercion_unknown_versions_and_bad_digest`. Failure behavior: construction/registry lookup fails before run creation.
- [ ] **Implement least-authority dependency composition —** Input: promoted configuration and specialist capability list. Operation: inject only the exact read-only ports/cancellation/context and register only the versioned Pydantic AI tools. Output: immutable `AgentDependenciesV1`. Test evidence: `test_agent_dependency_graph_has_no_repository_command_send_or_credential_edge`. Failure behavior: composition refuses the run.
- [ ] **Implement finite execution and ledger —** Input: verified envelope, reservation, promoted configuration. Operation: enforce deadline/model/tool/token/cost ceilings, collect per-call ledger, and return one typed success/abstention/failure. Output: terminal execution result. Test evidence: fake-model/tool timeout/cancel/budget boundary matrix. Failure behavior: typed `AgentFailureArtifactV1`; no partial accepted output.
- [ ] **Implement deterministic validation/persistence handoff —** Input: terminal result and ledger. Operation: validate schema/provenance/authority, persist run/`PRODUCED` artifact/evidence/cost through application services, and emit canonical events. Output: immutable reviewable artifact or retained failed run. Test evidence: failure injection at every write and event payload snapshot. Failure behavior: atomic rollback or operator-visible recovery; no silent replay.
- [ ] **Prove authority and observability boundary —** Input: import/call graph and adversarial fixtures. Operation: assert no agent imports provider credentials/Gmail/`SendGateway`/repositories/command services and telemetry contains only safe IDs, hashes, versions, counts, timings, reason codes, and costs. Output: M3 boundary evidence. Test evidence: static architecture test and log/trace secret/PII scan. Failure behavior: promotion blocked.

## Test strategy

- **Schema `test_all_agent_models_are_strict_frozen_and_extra_forbid`:** coercion, unknown fields, invalid UUID/time/hash/version fail.
- **Digest `test_agent_envelopes_reproduce_db01_rfc8785_vectors`:** two independent encoders plus JSON-null/SQL-null distinction.
- **Authority `test_no_agent_dependency_can_reach_gmail_sendgateway_state_or_credentials`:** import and runtime object graph.
- **Tools `test_tool_registry_rejects_unknown_capability_and_prompt_injection_result`:** no dynamic expansion.
- **Ceilings `test_execution_stops_before_next_call_at_every_budget_boundary`:** time/token/tool/model/cost.
- **Cancellation `test_cancel_before_after_each_provider_boundary_persists_no_partial_artifact`:** finite termination.
- **Persistence `test_success_run_artifact_event_evidence_and_cost_reconcile`:** IDs, hashes, versions, correlation/causation, counts.
- **Security `test_agent_telemetry_and_failure_artifact_exclude_chain_of_thought_secrets_and_pii`:** allowlist scan.

## Security, privacy, compliance, idempotency, observability, and cost

Prompts and tools treat every source as hostile data, never instructions. Restricted captures are read only when the specialist's declared scope permits and are not copied into telemetry. Correlation uses `experiment_id`, `workflow_run_id`, `agent_run_id`, `artifact_id`, `provider_call_id`, `correlation_id`, and `causation_id`; content, recipient addresses, credentials, and hidden reasoning are excluded. Metrics include run count/outcome/error, duration, tool/model counts, token usage, provider currency cost and ILS projection, evidence/citation counts, post-validation reasons, abstention, and promoted configuration hash.

The workflow reserves cost before execution. The runtime stops before a call that could cross any ceiling, then reconciles every ledger row through `ProviderCostReconciliationService`. The same verified workflow input/config/agent type unique prevents duplicate run creation; per-provider idempotency is Task 4's responsibility and never substitutes for application command replay.

Retention follows DB-04/05/06 exactly: `agent_runs`, `evaluation_cases`, and `evaluation_results` are `EVALUATION_VERSIONED`; `artifacts` and `artifact_evidence_links` are `BUSINESS_ACTIVE`; `evidence_items` are `SENSITIVE_SHORT`; `artifact_validations`, `artifact_acceptances`, `cost_entries`, `domain_events`, `audit_events`, and `outbox_messages` are `SAFETY_LONG`; `RetentionCommandService` owns every purge/redaction.

## Failure, rollback, and operator recovery

Unknown schema/config, digest mismatch, authority leak, invalid provenance, impossible ledger total, or persistence disagreement blocks the artifact and opens an incident when safety/reproducibility is uncertain. Retry is workflow-owned and bounded by the taxonomy above. Rollback selects the prior promoted configuration for new runs; existing runs/artifacts/evaluations remain immutable. Operators compare workflow input, agent run, provider ledger, cost `cost_entries`, `artifact_evidence_links`, and events, then use audited recovery commands rather than SQL edits.

## Acceptance and retained evidence

- [ ] One shared strict execution envelope and failure taxonomy covers every specialist.
- [ ] Every hash is reproducible through the DB-01 RFC 8785/SHA-256 envelope and exact schema string.
- [ ] Every run is finite, ceiling-bound, cancellation-aware, and workflow-owned.
- [ ] Tools are read-only least-authority capabilities; agents cannot mutate state, decide policy/approval/budget/suppression, call Gmail/`SendGateway`, or receive credentials.
- [ ] Successful output persists only as immutable `PRODUCED`; deterministic services own validation/acceptance/events/transitions.
- [ ] Provider ledger, aggregate usage, `cost_entries`, correlation/causation, versions, and retention records reconcile exactly.

Retain contract/schema snapshots, prompt/config/tool manifests and hashes, DB-01 digest vectors, fake-provider boundary traces, cancellation/timeout/cost matrix, static authority proof, sanitized telemetry scan, persistence failure injections, and event/cost reconciliation output under `EVALUATION_VERSIONED` or the owning DB-04/05 retention class.

## Dependencies and next deliverable

AGENT-01 depends on M2's planned artifact/evidence/event schema and accepted finite runtime. It unlocks [AGENT-02](02-idea-discovery-agent.md) through [AGENT-09](09-experiment-evaluation-agent.md); none is promoted until [AGENT-10](10-agent-evals-and-versioning.md) passes.
