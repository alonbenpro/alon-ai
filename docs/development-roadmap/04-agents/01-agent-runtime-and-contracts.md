# Agent Runtime, Execution Envelope, and Authority Contracts

**Document ID:** AGENT-01
**Status:** Planned M3 contract; Pydantic AI/Pydantic Evals are locked but unused
**Milestone:** M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `AGENT-01-T01 -> AGENT-01-T02 -> AGENT-01-T03 -> AGENT-01-T04 -> AGENT-01-T05`; cross-document task Inputs `AGENT-01-T01 <- DB-01-T02,DB-04-T02; AGENT-01-T02 <- AGENT-10-T01; AGENT-01-T03 <- OBS-03-T02; AGENT-01-T04 <- BACKEND-01-T01,DB-04-T04,OBS-03-T02`. Descriptive source authorities/resources (not whole-document completion dependencies): [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [DB-01](../02-database/01-core-data-model.md), [DB-04](../02-database/04-agent-artifacts-and-evidence.md), [DB-05](../02-database/05-audit-events-and-idempotency.md), and accepted M1 runtime evidence
**Outputs:** Versioned Pydantic execution models, dependency/tool authority boundary, reproducible hashes, provider-use ledger, failure taxonomy, finite-run rules, and persistence/event map
**Unlocks:** AGENT-02 through AGENT-10 and M3 offline promotion
**Risk:** Critical
**Complexity:** L

## Outcome and timing

M3 gets one deliberately narrow agent runtime: Pydantic AI executes a single typed request and returns one immutable typed result. Pydantic Evals measures recorded suites. DBOS owns the surrounding finite workflow, while deterministic application services own budgets, validation, artifact acceptance, state transitions, and all provider-side authority.

This is not an autonomous-agent platform. There is no planner loop, recursive delegation, background daemon, mutable memory, or model-authored command. Each run has a frozen input, an exact immutable configuration authorized either by a current product PromotionManifestV1 or, only for isolated M3 LIVE_CAPTURE, by the signed AGENT-10 evaluation-only candidate manifest with reserved budget and no product authority, explicit tools, attempt/time/token/tool/cost ceilings, cancellation signal, and one terminal result.

## Current repository state

Implemented today: locked `pydantic-ai[dbos]>=2.35.3` and `pydantic-evals>=2.35.3` constraints, an empty `backend/src/alon_ai/agents/__init__.py`, minimal Gmail DTO/protocols, and guarded `SendGateway`. Missing: every model below, Pydantic AI `Agent`, dependency container, tool, prompt registry, artifact registry, execution service, provider ledger, evaluation suite, agent run recorder, and promoted configuration. No current agent can run.

## Scope and non-goals

In scope: exact Pydantic models, frozen version/config records, dependency injection, read-only capability tools, schema/provenance/evidence rules, deterministic hashing, usage/cost accounting, timeouts/cancellation, typed failure, post-validation, persistence/event mapping, offline fixtures, promotion and rollback handoff, observability, and retention.

Non-goals: LangChain, LangGraph, Restate, Prefect, model-selected tools outside an allowlist, direct SQL/ORM sessions, Gmail or `SendGateway`, provider credentials, policy/approval/budget/suppression decisions, automatic retries without workflow ownership, chain-of-thought storage, or business-state mutation.

## Exact planned implementation surfaces

Create `backend/src/alon_ai/agents/contracts.py`, `agents/dependencies.py`, `agents/execution.py`, `agents/registry.py`, `agents/errors.py`, `agents/telemetry.py`, and tests under `backend/tests/unit/agents/` and `backend/tests/contract/agents/`. Agent-specific modules are named in AGENT-02 through AGENT-09. Task 4 must implement provider protocols/adapters matching the capability semantics below; it may reconcile Python protocol names, but cannot silently widen a capability.

The existing persistence targets remain exact: DB-04 `agent_runs`, `artifacts`, `evidence_items`, `artifact_evidence_links`, `artifact_validations`, `artifact_acceptances`, `evaluation_cases`, and `evaluation_results`; DB-01 `workflow_runs`; and DB-05 `cost_entries`, `domain_events`, `audit_events`, and `outbox_messages`. This segment adds no alias table.

### Exact shared Pydantic models

Every displayed shared and specialist model inherits executable `StrictAgentModel`. It freezes instances, forbids extra fields and coercion, recursively trims strings, rejects whitespace-only strings, requires UUIDv4 for every UUID, and requires aware UTC (`utcoffset() == 0`) for every datetime. The aliases below are also used where a scalar has tighter syntax. `VersionId` matches `^[a-z0-9][a-z0-9._-]{0,63}$`; `Sha256Hex` matches `^[0-9a-f]{64}$`; `JsonPointer` matches `^/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$` and is at most 512 characters.

```python
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Generic, Literal, TypeAlias, TypeVar
from uuid import UUID

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

def _trim_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    trimmed = value.strip()
    if value != "" and trimmed == "":
        raise ValueError("whitespace-only strings are forbidden")
    return trimmed

def _normalize_strings(value: Any) -> Any:
    if isinstance(value, str):
        return _trim_string(value)
    if isinstance(value, dict):
        return {key: _normalize_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_strings(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_strings(item) for item in value)
    return value

def _require_uuid4(value: UUID) -> UUID:
    if value.version != 4:
        raise ValueError("UUIDv4 required")
    return value

def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("aware UTC datetime required")
    return value

TrimmedStr = Annotated[str, BeforeValidator(_trim_string)]
Uuid4 = Annotated[UUID, AfterValidator(_require_uuid4)]
UtcDateTime = Annotated[datetime, AfterValidator(_require_utc)]
VersionId = Annotated[str, BeforeValidator(_trim_string), Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")]
Sha256Hex = Annotated[str, BeforeValidator(_trim_string), Field(pattern=r"^[0-9a-f]{64}$")]
JsonPointer = Annotated[str, BeforeValidator(_trim_string), Field(min_length=2, max_length=512, pattern=r"^/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$")]
Currency = Annotated[str, BeforeValidator(_trim_string), Field(pattern=r"^[A-Z]{3}$")]

class StrictAgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_all_strings(cls, value: Any) -> Any:
        return _normalize_strings(value)

    @model_validator(mode="after")
    def require_uuid4_and_utc(self) -> "StrictAgentModel":
        def inspect(value: Any) -> None:
            if isinstance(value, UUID):
                _require_uuid4(value)
            elif isinstance(value, datetime):
                _require_utc(value)
            elif isinstance(value, BaseModel):
                for nested in value.__dict__.values():
                    inspect(nested)
            elif isinstance(value, dict):
                for nested in value.values():
                    inspect(nested)
            elif isinstance(value, (list, tuple, set)):
                for nested in value:
                    inspect(nested)
        for field_value in self.__dict__.values():
            inspect(field_value)
        return self

PayloadT = TypeVar("PayloadT", bound=StrictAgentModel)
SuccessT = TypeVar("SuccessT", bound=StrictAgentModel)
AbstentionT = TypeVar("AbstentionT", bound=StrictAgentModel)

class AgentType(StrEnum):
    IDEA_DISCOVERY = "IDEA_DISCOVERY"
    OFFER_DESIGN = "OFFER_DESIGN"
    MARKET_RESEARCH = "MARKET_RESEARCH"
    LEAD_RESEARCH = "LEAD_RESEARCH"
    LEAD_QUALIFICATION = "LEAD_QUALIFICATION"
    OUTREACH_DRAFTING = "OUTREACH_DRAFTING"
    REPLY_CLASSIFICATION = "REPLY_CLASSIFICATION"
    EXPERIMENT_EVALUATION = "EXPERIMENT_EVALUATION"

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

class ExecutionCeilingsV1(StrictAgentModel):
    timeout_seconds: int = Field(ge=1, le=300)
    max_input_tokens: int = Field(ge=1, le=50_000)
    max_output_tokens: int = Field(ge=1, le=10_000)
    max_tool_calls: int = Field(ge=0, le=32)
    max_model_requests: int = Field(ge=1, le=3)
    max_cost_minor: int = Field(ge=0, le=100_000)
    currency: Currency

class AgentConfigurationRefV1(StrictAgentModel):
    agent_type: AgentType
    agent_version: VersionId
    prompt_version: VersionId
    prompt_hash: Sha256Hex
    model_provider: VersionId
    model_name: Annotated[str, BeforeValidator(_trim_string), Field(min_length=1, max_length=128)]
    model_version: VersionId
    toolset_version: VersionId
    input_schema_version: VersionId
    output_schema_version: VersionId
    post_validator_version: VersionId
    configuration_hash: Sha256Hex

class EvidenceRefV1(StrictAgentModel):
    evidence_item_id: Uuid4
    content_hash: Sha256Hex
    claim_pointer: JsonPointer
    relationship: Literal["SUPPORTS", "CONTRADICTS", "CONTEXT"]
    source_excerpt_hash: Sha256Hex | None = None

class AgentExecutionEnvelopeV1(StrictAgentModel, Generic[PayloadT]):
    schema_version: Literal["agent.execution.input.v1"]
    agent_run_id: Uuid4
    experiment_id: Uuid4
    workflow_run_id: Uuid4
    workflow_type: VersionId
    workflow_version: VersionId
    workflow_input_schema_version: VersionId
    workflow_input_hash: Sha256Hex
    input_pointer: JsonPointer
    correlation_id: Uuid4
    causation_id: Uuid4
    configuration: AgentConfigurationRefV1
    ceilings: ExecutionCeilingsV1
    evidence_refs: tuple[EvidenceRefV1, ...] = Field(max_length=100)
    payload: PayloadT

class ProviderUseLedgerEntryV1(StrictAgentModel):
    schema_version: Literal["provider.use.v1"]
    provider_call_id: Uuid4
    provider: VersionId
    capability: Literal[
        "model.complete_structured", "evidence.read", "search.query",
        "page.extract", "business.search", "business.details"
    ]
    operation_version: VersionId
    request_hash: Sha256Hex
    response_hash: Sha256Hex | None
    evidence_item_ids: tuple[Uuid4, ...] = Field(max_length=100)
    started_at: UtcDateTime
    finished_at: UtcDateTime
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_minor: int = Field(ge=0)
    currency: Currency
    outcome: Literal["SUCCEEDED", "FAILED", "CANCELLED", "TIMEOUT"]
    error_code: AgentErrorCode | None = None

    @model_validator(mode="after")
    def error_matches_outcome(self) -> "ProviderUseLedgerEntryV1":
        if self.finished_at < self.started_at:
            raise ValueError("provider finish precedes start")
        if (self.outcome == "SUCCEEDED") != (self.error_code is None):
            raise ValueError("success requires no error; non-success requires error")
        return self

class AgentUsageV1(StrictAgentModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    tool_call_count: int = Field(ge=0)
    model_request_count: int = Field(ge=0)
    cost_minor: int = Field(ge=0)
    currency: Currency
    duration_ms: int = Field(ge=0)

class AgentFailureArtifactV1(StrictAgentModel):
    schema_version: Literal["agent.failure.v1"]
    agent_run_id: Uuid4
    error_code: AgentErrorCode
    retry_class: Literal["NO_RETRY", "BOUNDED_RETRY", "OPERATOR_REVIEW"]
    safe_message: Annotated[str, BeforeValidator(_trim_string), Field(min_length=1, max_length=300)]
    failed_phase: Literal["INPUT", "DEPENDENCY", "TOOL", "MODEL", "VALIDATION", "PERSISTENCE"]
    evidence_refs: tuple[Uuid4, ...] = Field(max_length=20)
    configuration_hash: Sha256Hex

class AgentSuccessTerminalV1(StrictAgentModel, Generic[SuccessT]):
    outcome: Literal["SUCCESS"]
    artifact: SuccessT
    configuration: AgentConfigurationRefV1
    usage: AgentUsageV1
    provider_ledger: tuple[ProviderUseLedgerEntryV1, ...] = Field(max_length=32)

class AgentAbstainedTerminalV1(StrictAgentModel, Generic[AbstentionT]):
    outcome: Literal["ABSTAIN"]
    abstention: AbstentionT
    configuration: AgentConfigurationRefV1
    usage: AgentUsageV1
    provider_ledger: tuple[ProviderUseLedgerEntryV1, ...] = Field(max_length=32)

class AgentFailedTerminalV1(StrictAgentModel):
    outcome: Literal["FAILED"]
    failure: AgentFailureArtifactV1
    configuration: AgentConfigurationRefV1
    usage: AgentUsageV1
    provider_ledger: tuple[ProviderUseLedgerEntryV1, ...] = Field(max_length=32)

type AgentTerminalResultV1[
    SuccessT: StrictAgentModel,
    AbstentionT: StrictAgentModel,
] = Annotated[
    AgentSuccessTerminalV1[SuccessT]
    | AgentAbstainedTerminalV1[AbstentionT]
    | AgentFailedTerminalV1,
    Field(discriminator="outcome"),
]
```
Every specialist binds its exact success and abstention schemas into `AgentTerminalResultV1[Success, Abstention]`; therefore every execution returns exactly one discriminated `SUCCESS`, `ABSTAIN`, or `FAILED` branch with the exact configuration, aggregate usage, and per-call provider ledger. The execution service rejects a branch/configuration mismatch or ledger totals that do not equal `AgentUsageV1`. `AgentFailureArtifactV1` remains a typed execution failure record, not a DB-04 product `artifacts` row. `AgentRunRecordingService` persists its safe fields to the failed `agent_runs` record. Only if a deterministic application handler fails the owning workflow does it also emit `workflow.run_failed.v1`; otherwise it records safe audit/trace evidence without inventing an agent-failure event. A specialist abstention schema records the allowed reason and supporting evidence; the application records `agent_runs.abstained=true` and may store the specialist's immutable `PRODUCED` abstention artifact with DB confidence `NULL`, but it cannot become accepted workflow evidence without normal validation.

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
| `model.complete_structured` | one bounded model request under the product-promotion or isolated evaluation-only candidate authority defined above returning the declared Pydantic result | free-form code execution, hidden follow-up loop, provider credential exposure |
| `evidence.read` | fetch immutable accepted/captured evidence by ID/hash with size/redaction limits | arbitrary DB query, raw restricted capture unless scope explicitly allows |
| `search.query` | bounded allowlisted market query returning result metadata and capture IDs | arbitrary browsing, contact harvesting, mutable search sessions |
| `page.extract` | HTTPS capture by approved URI/ref with scheme/domain/type/size/time limits | browser actions, login, forms, scripts, credential use |
| `business.search` | bounded business candidates with source identity facts | personal-contact discovery or unbounded result pages |
| `business.details` | business-level public facts and provenance for one candidate | personal data guessing, mailbox/contact enrichment, auto-merge |

The execution service registers only named Pydantic AI tools for the selected `toolset_version`. Unknown tool name, capability, or argument fails before a provider call. Tool results are untrusted Pydantic inputs and cannot inject instructions, add tools, change ceilings, or grant authority.

### Exact provider capability wire and fixture contracts

Task 4 must implement byte-compatible equivalents of these six strict request/response/fixture families. It may rename Python methods only; capability literals, field semantics, schema strings, canonical hashes, timeout ceilings, errors, evidence/usage fields, and read-only authority are frozen.

```python
RequestT = TypeVar("RequestT", bound=StrictAgentModel)
ResultT = TypeVar("ResultT", bound=StrictAgentModel)

class ProviderCallContextV1(StrictAgentModel):
    provider_call_id: Uuid4
    operation_version: VersionId
    deadline_at: UtcDateTime

class ProviderResultMetaV1(StrictAgentModel):
    provider_call_id: Uuid4
    provider_request_id: Annotated[TrimmedStr, Field(min_length=1, max_length=200)] | None = None
    outcome: Literal["SUCCEEDED", "FAILED", "CANCELLED", "TIMEOUT"]
    started_at: UtcDateTime
    finished_at: UtcDateTime
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_minor: int = Field(ge=0)
    currency: Currency

    @model_validator(mode="after")
    def validate_time(self) -> "ProviderResultMetaV1":
        if self.finished_at < self.started_at:
            raise ValueError("provider finish precedes start")
        return self

class ProviderSuccessResponseV1(StrictAgentModel):
    result_type: Literal["SUCCESS"]
    meta: ProviderResultMetaV1

    @model_validator(mode="after")
    def require_success(self) -> "ProviderSuccessResponseV1":
        if self.meta.outcome != "SUCCEEDED":
            raise ValueError("typed success response requires SUCCEEDED")
        return self

class ProviderCapabilityFailureV1(StrictAgentModel):
    result_type: Literal["FAILURE"]
    meta: ProviderResultMetaV1
    safe_error_detail: Annotated[TrimmedStr, Field(min_length=1, max_length=300)]
    error_fingerprint: Sha256Hex

    @model_validator(mode="after")
    def require_matching_failure(self) -> "ProviderCapabilityFailureV1":
        error_code = getattr(self, "error_code", None)
        if error_code is None:
            raise ValueError("generic provider failure is abstract; use a capability-specific failure")
        expected = (
            "CANCELLED" if error_code == AgentErrorCode.CANCELLED
            else "TIMEOUT" if error_code in {AgentErrorCode.MODEL_TIMEOUT, AgentErrorCode.TOOL_TIMEOUT}
            else "FAILED"
        )
        if self.meta.outcome != expected:
            raise ValueError("failure error_code and provider outcome disagree")
        return self

class ModelCompleteStructuredRequestV1(StrictAgentModel):
    schema_version: Literal["provider.model_complete.request.v1"]
    capability: Literal["model.complete_structured"]
    context: ProviderCallContextV1
    timeout_ms: int = Field(ge=1, le=120_000)
    model_provider: VersionId
    model_name: Annotated[TrimmedStr, Field(min_length=1, max_length=128)]
    model_version: VersionId
    prompt_version: VersionId
    prompt_hash: Sha256Hex
    input_schema_version: VersionId
    input_payload: dict[str, object]
    output_schema_version: VersionId
    max_output_tokens: int = Field(ge=1, le=10_000)
    temperature: Decimal = Field(ge=0, le=2, decimal_places=3)
    seed: int | None = None

class ModelCompleteStructuredPayloadV1(StrictAgentModel):
    output_schema_version: VersionId
    output_payload: dict[str, object]

class ModelCompleteStructuredResponseV1(ProviderSuccessResponseV1):
    schema_version: Literal["provider.model_complete.response.v1"]
    capability: Literal["model.complete_structured"]
    payload_schema_version: Literal["provider.model_complete.payload.v1"]
    payload: ModelCompleteStructuredPayloadV1
    payload_hash: Sha256Hex

class ModelCompleteStructuredFailureV1(ProviderCapabilityFailureV1):
    schema_version: Literal["provider.model_complete.failure.v1"]
    capability: Literal["model.complete_structured"]
    error_code: Literal[
        AgentErrorCode.DEPENDENCY_UNAVAILABLE, AgentErrorCode.MODEL_TIMEOUT,
        AgentErrorCode.MODEL_OUTPUT_INVALID, AgentErrorCode.MODEL_REFUSAL,
        AgentErrorCode.MODEL_BUDGET_EXHAUSTED, AgentErrorCode.COST_BUDGET_EXHAUSTED,
        AgentErrorCode.CANCELLED, AgentErrorCode.INTERNAL_ERROR,
    ]

type ModelCompleteStructuredResultV1 = Annotated[
    ModelCompleteStructuredResponseV1 | ModelCompleteStructuredFailureV1,
    Field(discriminator="result_type"),
]

class EvidenceReadRequestV1(StrictAgentModel):
    schema_version: Literal["provider.evidence_read.request.v1"]
    capability: Literal["evidence.read"]
    context: ProviderCallContextV1
    timeout_ms: int = Field(ge=1, le=10_000)
    evidence_item_id: Uuid4
    expected_content_hash: Sha256Hex
    max_bytes: int = Field(ge=1, le=1_000_000)
    allow_restricted: bool = False

class EvidenceReadPayloadV1(StrictAgentModel):
    evidence_item_id: Uuid4
    content_hash: Sha256Hex
    capture_ref: Annotated[TrimmedStr, Field(min_length=1, max_length=500)]
    redaction_state: Literal["RAW_RESTRICTED", "REDACTED"]
    content_payload: dict[str, object]

class EvidenceReadResponseV1(ProviderSuccessResponseV1):
    schema_version: Literal["provider.evidence_read.response.v1"]
    capability: Literal["evidence.read"]
    payload_schema_version: Literal["provider.evidence_read.payload.v1"]
    payload: EvidenceReadPayloadV1
    payload_hash: Sha256Hex

class EvidenceReadFailureV1(ProviderCapabilityFailureV1):
    schema_version: Literal["provider.evidence_read.failure.v1"]
    capability: Literal["evidence.read"]
    error_code: Literal[
        AgentErrorCode.DEPENDENCY_UNAVAILABLE, AgentErrorCode.TOOL_TIMEOUT,
        AgentErrorCode.TOOL_RESULT_INVALID, AgentErrorCode.EVIDENCE_MISSING,
        AgentErrorCode.CANCELLED, AgentErrorCode.INTERNAL_ERROR,
    ]

type EvidenceReadResultV1 = Annotated[
    EvidenceReadResponseV1 | EvidenceReadFailureV1,
    Field(discriminator="result_type"),
]

class SearchResultItemV1(StrictAgentModel):
    citation_uri: Annotated[TrimmedStr, Field(min_length=1, max_length=2_000)]
    title: Annotated[TrimmedStr, Field(min_length=1, max_length=500)]
    snippet: Annotated[TrimmedStr, Field(min_length=1, max_length=2_000)]
    evidence_item_id: Uuid4
    content_hash: Sha256Hex

class SearchQueryRequestV1(StrictAgentModel):
    schema_version: Literal["provider.search_query.request.v1"]
    capability: Literal["search.query"]
    context: ProviderCallContextV1
    timeout_ms: int = Field(ge=1, le=20_000)
    query: Annotated[TrimmedStr, Field(min_length=1, max_length=500)]
    allowed_domains: tuple[TrimmedStr, ...] = Field(min_length=1, max_length=50)
    blocked_domains: tuple[TrimmedStr, ...] = Field(max_length=50)
    max_results: int = Field(ge=1, le=20)
    as_of: UtcDateTime

class SearchQueryPayloadV1(StrictAgentModel):
    results: tuple[SearchResultItemV1, ...] = Field(max_length=20)

class SearchQueryResponseV1(ProviderSuccessResponseV1):
    schema_version: Literal["provider.search_query.response.v1"]
    capability: Literal["search.query"]
    payload_schema_version: Literal["provider.search_query.payload.v1"]
    payload: SearchQueryPayloadV1
    payload_hash: Sha256Hex

class SearchQueryFailureV1(ProviderCapabilityFailureV1):
    schema_version: Literal["provider.search_query.failure.v1"]
    capability: Literal["search.query"]
    error_code: Literal[
        AgentErrorCode.DEPENDENCY_UNAVAILABLE, AgentErrorCode.TOOL_TIMEOUT,
        AgentErrorCode.TOOL_RESULT_INVALID, AgentErrorCode.TOOL_BUDGET_EXHAUSTED,
        AgentErrorCode.COST_BUDGET_EXHAUSTED, AgentErrorCode.CANCELLED,
        AgentErrorCode.INTERNAL_ERROR,
    ]

type SearchQueryResultV1 = Annotated[
    SearchQueryResponseV1 | SearchQueryFailureV1,
    Field(discriminator="result_type"),
]

class PageExtractRequestV1(StrictAgentModel):
    schema_version: Literal["provider.page_extract.request.v1"]
    capability: Literal["page.extract"]
    context: ProviderCallContextV1
    timeout_ms: int = Field(ge=1, le=30_000)
    source_locator: Annotated[TrimmedStr, Field(min_length=1, max_length=8_192)]
    allowed_domains: tuple[TrimmedStr, ...] = Field(min_length=1, max_length=50)
    max_response_bytes: int = Field(ge=1, le=5_000_000)
    allowed_mime_types: tuple[TrimmedStr, ...] = Field(min_length=1, max_length=20)

class PageExtractPayloadV1(StrictAgentModel):
    evidence_item_id: Uuid4
    citation_uri: Annotated[TrimmedStr, Field(min_length=1, max_length=2_000)]
    content_hash: Sha256Hex
    capture_ref: Annotated[TrimmedStr, Field(min_length=1, max_length=500)]
    mime_type: Annotated[TrimmedStr, Field(min_length=1, max_length=200)]
    language: Annotated[TrimmedStr, Field(min_length=2, max_length=35)]
    extracted_text_hash: Sha256Hex

class PageExtractResponseV1(ProviderSuccessResponseV1):
    schema_version: Literal["provider.page_extract.response.v1"]
    capability: Literal["page.extract"]
    payload_schema_version: Literal["provider.page_extract.payload.v1"]
    payload: PageExtractPayloadV1
    payload_hash: Sha256Hex

class PageExtractFailureV1(ProviderCapabilityFailureV1):
    schema_version: Literal["provider.page_extract.failure.v1"]
    capability: Literal["page.extract"]
    error_code: Literal[
        AgentErrorCode.DEPENDENCY_UNAVAILABLE, AgentErrorCode.TOOL_TIMEOUT,
        AgentErrorCode.TOOL_RESULT_INVALID, AgentErrorCode.TOOL_BUDGET_EXHAUSTED,
        AgentErrorCode.COST_BUDGET_EXHAUSTED, AgentErrorCode.CANCELLED,
        AgentErrorCode.INTERNAL_ERROR, AgentErrorCode.PROMPT_INJECTION_DETECTED,
    ]

type PageExtractResultV1 = Annotated[
    PageExtractResponseV1 | PageExtractFailureV1,
    Field(discriminator="result_type"),
]

class BusinessCandidateV1(StrictAgentModel):
    canonical_name: Annotated[TrimmedStr, Field(min_length=1, max_length=300)]
    canonical_domain: Annotated[TrimmedStr, Field(min_length=1, max_length=253)] | None
    country_code: Annotated[str, BeforeValidator(_trim_string), Field(pattern=r"^[A-Z]{2}$")]
    business_identity_key: Sha256Hex
    evidence_item_ids: tuple[Uuid4, ...] = Field(min_length=1, max_length=10)

class BusinessSearchRequestV1(StrictAgentModel):
    schema_version: Literal["provider.business_search.request.v1"]
    capability: Literal["business.search"]
    context: ProviderCallContextV1
    timeout_ms: int = Field(ge=1, le=20_000)
    canonical_name: Annotated[TrimmedStr, Field(min_length=1, max_length=300)]
    canonical_domain: Annotated[TrimmedStr, Field(min_length=1, max_length=253)] | None
    country_code: Annotated[str, BeforeValidator(_trim_string), Field(pattern=r"^[A-Z]{2}$")]
    max_results: int = Field(ge=1, le=10)

class BusinessSearchPayloadV1(StrictAgentModel):
    candidates: tuple[BusinessCandidateV1, ...] = Field(max_length=10)

class BusinessSearchResponseV1(ProviderSuccessResponseV1):
    schema_version: Literal["provider.business_search.response.v1"]
    capability: Literal["business.search"]
    payload_schema_version: Literal["provider.business_search.payload.v1"]
    payload: BusinessSearchPayloadV1
    payload_hash: Sha256Hex

class BusinessSearchFailureV1(ProviderCapabilityFailureV1):
    schema_version: Literal["provider.business_search.failure.v1"]
    capability: Literal["business.search"]
    error_code: Literal[
        AgentErrorCode.DEPENDENCY_UNAVAILABLE, AgentErrorCode.TOOL_TIMEOUT,
        AgentErrorCode.TOOL_RESULT_INVALID, AgentErrorCode.TOOL_BUDGET_EXHAUSTED,
        AgentErrorCode.COST_BUDGET_EXHAUSTED, AgentErrorCode.CANCELLED,
        AgentErrorCode.INTERNAL_ERROR,
    ]

type BusinessSearchResultV1 = Annotated[
    BusinessSearchResponseV1 | BusinessSearchFailureV1,
    Field(discriminator="result_type"),
]

class BusinessFactResponseV1(StrictAgentModel):
    fact_key: VersionId
    value: Annotated[TrimmedStr, Field(min_length=1, max_length=2_000)]
    evidence_item_ids: tuple[Uuid4, ...] = Field(min_length=1, max_length=10)
    observed_at: UtcDateTime | None = None

class BusinessDetailsRequestV1(StrictAgentModel):
    schema_version: Literal["provider.business_details.request.v1"]
    capability: Literal["business.details"]
    context: ProviderCallContextV1
    timeout_ms: int = Field(ge=1, le=15_000)
    business_identity_key: Sha256Hex
    requested_fact_keys: tuple[VersionId, ...] = Field(min_length=1, max_length=20)
    allowed_domains: tuple[TrimmedStr, ...] = Field(min_length=1, max_length=20)

class BusinessDetailsPayloadV1(StrictAgentModel):
    business_identity_key: Sha256Hex
    facts: tuple[BusinessFactResponseV1, ...] = Field(max_length=20)
    contradictions: tuple[Annotated[TrimmedStr, Field(min_length=1, max_length=500)], ...] = Field(max_length=10)

class BusinessDetailsResponseV1(ProviderSuccessResponseV1):
    schema_version: Literal["provider.business_details.response.v1"]
    capability: Literal["business.details"]
    payload_schema_version: Literal["provider.business_details.payload.v1"]
    payload: BusinessDetailsPayloadV1
    payload_hash: Sha256Hex

class BusinessDetailsFailureV1(ProviderCapabilityFailureV1):
    schema_version: Literal["provider.business_details.failure.v1"]
    capability: Literal["business.details"]
    error_code: Literal[
        AgentErrorCode.DEPENDENCY_UNAVAILABLE, AgentErrorCode.TOOL_TIMEOUT,
        AgentErrorCode.TOOL_RESULT_INVALID, AgentErrorCode.TOOL_BUDGET_EXHAUSTED,
        AgentErrorCode.COST_BUDGET_EXHAUSTED, AgentErrorCode.CANCELLED,
        AgentErrorCode.INTERNAL_ERROR, AgentErrorCode.EVIDENCE_CONFLICT,
    ]

type BusinessDetailsResultV1 = Annotated[
    BusinessDetailsResponseV1 | BusinessDetailsFailureV1,
    Field(discriminator="result_type"),
]

class CapabilityFixtureV1(StrictAgentModel, Generic[RequestT, ResultT]):
    schema_version: Literal["provider.capability_fixture.v1"]
    fixture_id: Uuid4
    capability: Literal[
        "model.complete_structured", "evidence.read", "search.query",
        "page.extract", "business.search", "business.details"
    ]
    request: RequestT
    request_hash: Sha256Hex
    response: ResultT
    response_hash: Sha256Hex
    expected_ledger_hash: Sha256Hex
    captured_at: UtcDateTime
    fixture_content_hash: Sha256Hex

class ModelCompleteStructuredFixtureV1(CapabilityFixtureV1[ModelCompleteStructuredRequestV1, ModelCompleteStructuredResultV1]):
    capability: Literal["model.complete_structured"]

class EvidenceReadFixtureV1(CapabilityFixtureV1[EvidenceReadRequestV1, EvidenceReadResultV1]):
    capability: Literal["evidence.read"]

class SearchQueryFixtureV1(CapabilityFixtureV1[SearchQueryRequestV1, SearchQueryResultV1]):
    capability: Literal["search.query"]

class PageExtractFixtureV1(CapabilityFixtureV1[PageExtractRequestV1, PageExtractResultV1]):
    capability: Literal["page.extract"]

class BusinessSearchFixtureV1(CapabilityFixtureV1[BusinessSearchRequestV1, BusinessSearchResultV1]):
    capability: Literal["business.search"]

class BusinessDetailsFixtureV1(CapabilityFixtureV1[BusinessDetailsRequestV1, BusinessDetailsResultV1]):
    capability: Literal["business.details"]
```

| Capability | Default/max timeout | Allowed non-success `AgentErrorCode` values | Ledger/evidence requirement |
| --- | --- | --- | --- |
| `model.complete_structured` | `45_000/120_000 ms` | `DEPENDENCY_UNAVAILABLE`, `MODEL_TIMEOUT`, `MODEL_OUTPUT_INVALID`, `MODEL_REFUSAL`, `MODEL_BUDGET_EXHAUSTED`, `COST_BUDGET_EXHAUSTED`, `CANCELLED`, `INTERNAL_ERROR` | provider request ID when supplied, tokens, latency, currency cost, response hash |
| `evidence.read` | `5_000/10_000 ms` | `DEPENDENCY_UNAVAILABLE`, `TOOL_TIMEOUT`, `TOOL_RESULT_INVALID`, `EVIDENCE_MISSING`, `CANCELLED`, `INTERNAL_ERROR` | exact evidence ID/content hash/capture ref/redaction state |
| `search.query` | `8_000/20_000 ms` | `DEPENDENCY_UNAVAILABLE`, `TOOL_TIMEOUT`, `TOOL_RESULT_INVALID`, `TOOL_BUDGET_EXHAUSTED`, `COST_BUDGET_EXHAUSTED`, `CANCELLED`, `INTERNAL_ERROR` | result-set hash plus every returned evidence ID/hash |
| `page.extract` | `12_000/30_000 ms` | same tool/budget errors as search plus `PROMPT_INJECTION_DETECTED` | URI, capture/evidence ID, content/extracted-text hashes, MIME/language |
| `business.search` | `8_000/20_000 ms` | same tool/budget errors as search | candidate-set hash and business/evidence identities; no contacts |
| `business.details` | `6_000/15_000 ms` | same tool/budget errors as search plus `EVIDENCE_CONFLICT` | exact business identity, requested fact keys and evidence IDs/hashes |

Each required request `timeout_ms` field encodes the `[1,max]` bound in its Pydantic schema; the table default is selected by deterministic dependency composition but never widens the typed maximum. Each `*ResultV1` is an exact `result_type`-discriminated union. `SUCCESS` requires the capability-specific typed `payload`, its literal `payload_schema_version`, and `payload_hash`, computed with the DB-01 RFC 8785/SHA-256 envelope over that exact payload; no success payload/hash is optional. `FAILURE` has no payload/hash fields, carries only that capability’s typed `AgentErrorCode` allowlist, and its provider outcome must match failure, timeout, or cancellation. Strict extra-forbid plus the union discriminator rejects success fields on failures, failure fields on successes, and cross-capability results. `ProviderUseLedgerEntryV1` must byte-match the request/result hashes, failure code, and `ProviderResultMetaV1`; fixture validation recomputes all three DB-01 envelopes. Task 4 cannot substitute provider-native strings for the shared taxonomy, return opaque SDK objects, omit cost/usage, or expose mutation/credential authority.

### Exact error taxonomy and finite execution

The single `AgentErrorCode` enum in the shared model block is normative for execution, capability responses, fixtures, ledgers, failure artifacts, persistence reason codes, and Task 4 adapters. Provider-native error strings are mapped at the adapter boundary and retained only as restricted fingerprints; they never replace the enum.


Only `DEPENDENCY_UNAVAILABLE`, `TOOL_TIMEOUT`, and `MODEL_TIMEOUT` may be `BOUNDED_RETRY`, and only when no paid/provider result was accepted, the workflow's remaining attempt/time/cost budget allows it, and the same command key/config/input is retained. Maximum model requests is `1` by default and `3` only where the specialist document explicitly allows schema-repair attempts. Cancellation is checked before a model/tool call, after each call, and before persistence; provider adapters receive the earlier of run deadline or their shorter operation deadline. Timeout/cancellation never creates an accepted partial artifact.

### Deterministic post-validation and persistence/event map

The agent process returns an in-memory Pydantic result. Deterministic `AgentExecutionService` then checks exact schema/config identity and execution authority: product composition requires current promotion; isolated M3 candidate capture instead requires the signed code-bound evaluation-only manifest, reservation and disabled product/non-model authority, and that same context must fail product composition before credential access, digest/pointer equality, evidence existence/hash/redaction, citation pointers/cardinality, no forbidden fields/authority language, ceilings versus ledger, and product-specific invariants. It does not accept artifacts.

Ownership follows DB-04 exactly. `AgentRunRecordingService` alone starts/closes `agent_runs` and reconciles aggregate usage. `EvidenceIngestService` alone stores `evidence_items`. `ArtifactCommandService` inserts only the immutable `artifacts(status=PRODUCED)` row and its atomic `artifact.produced.v1`; it never writes `artifact_evidence_links` or `artifact_validations`. In a later validation command, `ArtifactValidationService` verifies the produced artifact and captured evidence, writes every `artifact_evidence_links` row plus `artifact_validations`, then atomically records `VALIDATED` or `REJECTED` and emits `artifact.validated.v1` or `artifact.rejected.v1`. `ProviderCostReconciliationService` owns `cost_entries`. `ArtifactAcceptanceService` or an authenticated operator alone writes `artifact_acceptances`, `ACCEPTED`, and `artifact.accepted.v1`. Agents are never `actor_type` in `domain_events`/`audit_events`.

Each provider ledger item maps to one idempotent `cost_entries` row (`provider`, capability as `operation`, `agent_run_id`, `usage_json/hash`, provider currency, and ILS reporting conversion evidence). Aggregate totals must equal `agent_runs` usage/cost. Persistence failure leaves no claimed product artifact, marks the run failed only after a safe recovery inspection, and never repeats an accepted paid call blindly.

## Ordered implementation tasks

<!-- roadmap-task id=AGENT-01-T01 milestone=M3 depends_on=DB-01-T02,DB-04-T02 mode=parallel locks=agent-runtime -->
- [ ] **Implement frozen shared models and registries —** Input: DB-01/04 schemas and the models above. Operation: encode strict types, artifact/config/prompt/tool registries, RFC 8785 digests, and DB-01 golden vectors. Output: importable versioned contracts. Test evidence: `test_agent_contracts_reject_extra_coercion_unknown_versions_and_bad_digest`. Failure behavior: construction/registry lookup fails before run creation.
<!-- roadmap-task id=AGENT-01-T02 milestone=M3 depends_on=AGENT-01-T01,AGENT-10-T01 mode=parallel locks=agent-runtime -->
- [ ] **Implement least-authority dependency composition —** Input: AGENT-10 signed static candidate parameter templates and the document-local specialist capability list; exact code-bound configurations are frozen before later capture. Operation: inject only the exact read-only ports/cancellation/context and register only the versioned Pydantic AI tools; evaluation-only composition permits no product authority, and product composition requires a later immutable AGENT-10 promotion binding. Output: immutable `AgentDependenciesV1`. Test evidence: `test_agent_dependency_graph_has_no_repository_command_send_or_credential_edge`; fake-HTTP execution of a fresh unpromoted signed candidate-configuration fixture succeeds under isolated evaluation authority with all ceilings intact; the identical context fails product composition before credential access; missing signature/reservation, drift and non-model/product authority fail closed. Failure behavior: composition refuses the run.
<!-- roadmap-task id=AGENT-01-T03 milestone=M3 depends_on=AGENT-01-T02,OBS-03-T02 mode=parallel locks=agent-runtime -->
- [ ] **Implement finite execution and ledger —** Input: verified typed envelope fixtures, reserved cost-chain fixture and static candidate parameter fixture in an evaluation-only authority context; product invocation later requires an immutable promotion binding. Operation: enforce deadline/model/tool/token/cost ceilings, collect per-call ledger, and return one typed success/abstention/failure; evaluation-only composition permits no product authority, and product composition requires a later immutable AGENT-10 promotion binding. Output: terminal execution result. Test evidence: fake-model/tool timeout/cancel/budget boundary matrix; fake-HTTP execution of a fresh unpromoted signed candidate-configuration fixture succeeds under isolated evaluation authority with all ceilings intact; the identical context fails product composition before credential access; missing signature/reservation, drift and non-model/product authority fail closed. Failure behavior: typed `AgentFailureArtifactV1`; no partial accepted output.
<!-- roadmap-task id=AGENT-01-T04 milestone=M3 depends_on=AGENT-01-T03,BACKEND-01-T01,DB-04-T04,OBS-03-T02 mode=parallel locks=agent-artifacts,backend-domain -->
- [ ] **Implement deterministic validation/persistence handoff —** Input: terminal result and ledger; implemented recording/PRODUCED-insertion, artifact-validation/acceptance and cost-reconciliation service interfaces. Operation: validate schema/authority, let `AgentRunRecordingService` and `ArtifactCommandService` persist only their run/`PRODUCED` artifact records, then invoke the separate `ArtifactValidationService` evidence-link/validation transaction and `ProviderCostReconciliationService`. Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence. Test evidence: failure injection at every write and event payload snapshot. Failure behavior: atomic rollback or operator-visible recovery; no silent replay.
<!-- roadmap-task id=AGENT-01-T05 milestone=M3 depends_on=AGENT-01-T04 mode=parallel locks=agent-runtime -->
- [ ] **Prove authority and observability boundary —** Input: import/call graph and adversarial fixtures. Operation: assert no agent imports provider credentials/Gmail/`SendGateway`/repositories/command services and telemetry contains only safe IDs, hashes, versions, counts, timings, reason codes, and costs. Output: M3 boundary evidence. Test evidence: static architecture test and log/trace secret/PII scan. Failure behavior: promotion blocked.

## Test strategy

- **Schema `test_all_agent_models_are_strict_frozen_and_extra_forbid`:** UUIDv1/v3/v5, naive/non-UTC datetimes, whitespace-only strings, coercion, mutation, extra fields, and invalid hashes/versions all fail; trimmed valid strings normalize deterministically.
- **Digest `test_agent_envelopes_reproduce_db01_rfc8785_vectors`:** two independent encoders plus JSON-null/SQL-null distinction.
- **Authority `test_no_agent_dependency_can_reach_gmail_sendgateway_state_or_credentials`:** import and runtime object graph.
- **Tools `test_tool_registry_rejects_unknown_capability_and_prompt_injection_result`:** no dynamic expansion.
- **Ceilings `test_execution_stops_before_next_call_at_every_budget_boundary`:** time/token/tool/model/cost.
- **Cancellation `test_cancel_before_after_each_provider_boundary_persists_no_partial_artifact`:** finite termination.
- **Persistence `test_success_run_artifact_event_evidence_and_cost_reconcile`:** IDs, hashes, versions, correlation/causation, counts.
- **Ownership `test_artifact_command_service_cannot_write_evidence_links_or_validations`:** DB-04 owner boundaries and atomic validator link/validation/event transaction.
- **Run ownership `test_agent_run_recording_service_is_the_only_agent_runs_writer_including_evaluations`:** static imports/service spies and start/close failure injection prove every runtime/evaluation caller delegates and never writes the table.
- **Terminal union `test_every_specialist_result_is_exactly_success_abstain_or_failed`:** discriminator, config, usage, ledger, and branch payload reconcile.
- **Capability contracts `test_six_provider_result_unions_are_wire_exact_and_reject_invalid_branches`:** for all six families, construct success/failure and reject missing payload/hash/schema identity, extra or opposite-branch fields, illegal capability error, mismatched discriminator/outcome, and `timeout_ms=0`/one above the typed maximum; also prove fixture/request/result/ledger digest parity.
- **Security `test_agent_telemetry_and_failure_artifact_exclude_chain_of_thought_secrets_and_pii`:** allowlist scan.

## Security, privacy, compliance, idempotency, observability, and cost

Prompts and tools treat every source as hostile data, never instructions. Restricted captures are read only when the specialist's declared scope permits and are not copied into telemetry. Correlation uses `experiment_id`, `workflow_run_id`, `agent_run_id`, `artifact_id`, `provider_call_id`, `correlation_id`, and `causation_id`; content, recipient addresses, credentials, and hidden reasoning are excluded. Metrics include run count/outcome/error, duration, tool/model counts, token usage, provider currency cost and ILS projection, evidence/citation counts, post-validation reasons, abstention, and promoted configuration hash.

The workflow reserves cost before execution. The runtime stops before a call that could cross any ceiling, then reconciles every ledger row through `ProviderCostReconciliationService`. The same verified workflow input/config/agent type unique prevents duplicate run creation; per-provider idempotency is Task 4's responsibility and never substitutes for application command replay.

Retention follows DB-04/05/06 exactly: `agent_runs`, `evaluation_cases`, and `evaluation_results` are `EVALUATION_VERSIONED`; `artifacts` and `artifact_evidence_links` are `BUSINESS_ACTIVE`; `evidence_items` are `SENSITIVE_SHORT`; `artifact_validations`, `artifact_acceptances`, `cost_entries`, `domain_events`, `audit_events`, and `outbox_messages` are `SAFETY_LONG`; `RetentionCommandService` owns every purge/redaction.

## Failure, rollback, and operator recovery

Unknown schema/config, digest mismatch, authority leak, invalid provenance, impossible ledger total, or persistence disagreement blocks the artifact and opens an incident when safety/reproducibility is uncertain. Retry is workflow-owned and bounded by the taxonomy above. Rollback selects the prior promoted configuration for new runs; existing runs/artifacts/evaluations remain immutable. Operators compare workflow input, agent run, provider ledger, `cost_entries`, `artifact_evidence_links`, and events, then use audited recovery commands rather than SQL edits.

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
