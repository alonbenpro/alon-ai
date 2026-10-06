"""Durable, operator-safe summaries of agent-run failures.

The diagnostic surface records classifications only. Validation messages are
compared to exact owned constants; arbitrary text, inputs and context are never retained.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, get_args
from uuid import UUID

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_core.core_schema import ErrorType

from alon_ai.agents.tools.research import ResearchToolError
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.integrations.schemas.provider import ProviderFailure
from alon_ai.provider_usage.schemas.accounting import AccountingDenied

if TYPE_CHECKING:
    from alon_ai.db.repositories.agent_runs import AgentRunRepository


class RunDiagnostic(BaseModel):
    """A stable error projection that is safe to retain and show to an operator."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    error_type: str
    code: str
    message: str
    frames: list[str]


_MESSAGES = {
    "BUDGET": "The approved budget denied this request.",
    "CONFIG": "The approved provider configuration could not be used.",
    "SECRET": "A required provider credential could not be used.",
    "SCOPE": "This request exceeded the approved provider scope.",
    "RIGHTS": "The provider permission for this request was not active.",
    "PRICE": "The approved price configuration could not be used.",
    "QUOTA": (
        "The app's local request allowance is exhausted. This request was blocked "
        "before contacting the provider. Renew the approved allowance before retrying."
    ),
    "MODEL_ALLOWANCE_EXHAUSTED": (
        "The local OpenAI allowance cannot cover research and synthesis. "
        "Renew the approved allowance before starting another run."
    ),
    "MODEL_REQUEST_LIMIT_TOO_LOW": (
        "The approved per-run model request limit cannot cover research and synthesis. "
        "Configure at least two model requests before starting another run."
    ),
    "CAPTURE_ALLOWANCE_EXHAUSTED": (
        "The local Firecrawl capture allowance is exhausted. "
        "Renew the approved allowance before starting another run."
    ),
    "CONCURRENCY": "The provider concurrency limit denied this request.",
    "CIRCUIT": "The provider is temporarily unavailable.",
    "DEADLINE": "The approved request deadline was reached.",
    "CONFLICT": "A conflicting operation prevented this request.",
    "UNCERTAIN": "A previous provider outcome must be reconciled first.",
    "STATE": "The saved run state did not allow this request.",
    "USAGE": "The provider usage record could not be reconciled.",
    "RETENTION": "The approved retention rules denied this request.",
    "WRITE": "The approved write authority denied this request.",
    "GATE": "An approval gate denied this request.",
    "DENIED": "The provider denied this request.",
    "CAPABILITY_MISMATCH": "The requested provider capability was unavailable.",
    "TIMEOUT": "The provider request timed out.",
    "UNAVAILABLE": "The provider is temporarily unavailable.",
    "MALFORMED_RESPONSE": "The provider returned an unusable response.",
    "INCOMPLETE_RESULT": "The provider returned an incomplete result.",
    "CANCELLED_RESULT": "The provider cancelled the result.",
    "REFUSED": "The provider refused the request.",
    "WRITE_AUTHORITY_REQUIRED": "The provider requires approved write authority.",
    "RESEARCH_TOOL_UNAVAILABLE": "A research tool was unavailable for this request.",
    "EVIDENCE_READ_INPUT_INVALID": (
        "The evidence read requires a valid saved reference and 1–4,000 characters."
    ),
    "EVIDENCE_READ_RESULT_INVALID": "The saved evidence reader returned an invalid excerpt.",
    "EVIDENCE_READ_FAILED": "The service could not read the saved evidence.",
    "VALIDATION_ERROR": "The returned data did not match the approved format.",
    "HTTP_REQUEST_FAILED": "The provider request failed.",
    "MODEL_RESPONSE_UNEXPECTED": "The model response could not be used.",
    "USAGE_LIMIT_EXCEEDED": "The approved model usage limit was reached.",
    "UNEXPECTED_ERROR": "The service stopped before it could complete this run.",
}
_SAFE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,99}$")
_VALIDATION_TYPES = frozenset(get_args(ErrorType))
_OUTPUT_FIELDS = frozenset(
    [
        "result",
        "data",
        "kind",
        "status",
        "options",
        "gaps",
        "title",
        "customer",
        "problem",
        "approach",
        "commercial_reasoning",
        "alternatives",
        "risks",
        "source_refs",
        "findings",
        "unknowns",
        "topic",
        "basis",
        "claim",
        "confidence",
        "limitations",
        "source_excerpt",
        "captured_at",
        "published_on",
        "rights_ref",
        "idea_version_ref",
        "research_version_ref",
        "subject",
        "currency",
        "amount_low",
        "amount_high",
        "unit",
        "package",
        "observed_date",
        "brief",
        "coverage",
        "contradictions",
        "price_observations",
        "recommendation",
        "core_intent",
        "intent_relationship",
        "material_pivot",
        "buyer",
        "segment",
        "role",
        "service_hypothesis",
        "value_hypothesis",
        "assumptions",
        "exclusions",
        "research_questions",
        "grounding_refs",
        "uncertainties",
        "candidates",
        "hypothesis",
        "demand_status",
    ]
)
# Exact owned validator messages only; no substring matching or arbitrary rendering.
_VALIDATION_INVARIANTS = {
    "Value error, " + message: code
    for message, code in (
        ("invalid provider contract", "PROVIDER_CONTRACT_INVALID"),
        ("observed finding requires a source", "OBSERVED_FINDING_SOURCE_REQUIRED"),
        (
            "unknown finding cannot claim source support",
            "UNKNOWN_FINDING_CANNOT_CITE_SOURCE",
        ),
        ("finding source references must be unique", "FINDING_DUPLICATE_SOURCES"),
        ("not-found price cannot carry an amount", "NOT_FOUND_PRICE_HAS_AMOUNT"),
        ("observed price requires a source", "OBSERVED_PRICE_SOURCE_REQUIRED"),
        (
            "numeric price requires amount, currency and unit",
            "NUMERIC_PRICE_FIELDS_REQUIRED",
        ),
        (
            "exact or starting price cannot have an upper bound",
            "PRICE_UPPER_BOUND_FORBIDDEN",
        ),
        ("price range requires ordered bounds", "PRICE_RANGE_BOUNDS_INVALID"),
        ("quote-only price cannot have an amount", "QUOTE_ONLY_PRICE_HAS_AMOUNT"),
        ("option source references must be unique", "OPTION_DUPLICATE_SOURCES"),
        (
            "a researched option needs an observed finding",
            "OPTION_OBSERVATION_REQUIRED",
        ),
        ("finding cites a source outside its option", "OPTION_UNDECLARED_SOURCE"),
        (
            "successful discovery requires three distinct options",
            "DISCOVERY_OPTIONS_NOT_DISTINCT",
        ),
        ("assessment source references must be unique", "ASSESSMENT_DUPLICATE_SOURCES"),
        ("assessment cites an undeclared source", "ASSESSMENT_UNDECLARED_SOURCE"),
        (
            "incomplete assessment requires named gaps",
            "INCOMPLETE_ASSESSMENT_GAPS_REQUIRED",
        ),
        (
            "inconclusive assessment requires named gaps",
            "INCONCLUSIVE_ASSESSMENT_GAPS_REQUIRED",
        ),
        (
            "pivot flag and intent relationship disagree",
            "PIVOT_CLASSIFICATION_MISMATCH",
        ),
        (
            "discovery grounding must cite the operator profile",
            "DISCOVERY_PROFILE_GROUNDING_REQUIRED",
        ),
        ("discovery candidates must be distinct", "DISCOVERY_CANDIDATES_NOT_DISTINCT"),
        ("seeded brief grounding must cite the seed", "BRIEF_SEED_GROUNDING_REQUIRED"),
        (
            "selected brief grounding must cite the candidate",
            "BRIEF_CANDIDATE_GROUNDING_REQUIRED",
        ),
        (
            "returned brief must cite prior brief and feedback",
            "BRIEF_RETURN_GROUNDING_REQUIRED",
        ),
    )
}


def _experiment_code(error: ExperimentError) -> str:
    return error.detail if _SAFE_CODE.fullmatch(error.detail) else "EXPERIMENT_ERROR"


def _chain(error: Exception) -> Iterable[Exception]:
    """Follow both explicit and suppressed context without rendering exceptions."""

    seen: set[int] = set()
    current: Exception | None = error
    while current is not None and id(current) not in seen and len(seen) < 8:
        seen.add(id(current))
        yield current
        next_error = current.__cause__ or current.__context__
        current = next_error if isinstance(next_error, Exception) else None


def _frame(error: Exception) -> str:
    if isinstance(error, AccountingDenied):
        return f"AccountingDenied:{error.reason.value}"
    if isinstance(error, ProviderFailure):
        return f"ProviderFailure:{error.code.value}"
    if isinstance(error, ExperimentError):
        return f"ExperimentError:{_experiment_code(error)}"
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTPStatusError:HTTP_{error.response.status_code}"
    return type(error).__name__


def _validation_frames(error: ValidationError) -> list[str]:
    frames = []
    for item in error.errors(
        include_input=False, include_url=False, include_context=False
    )[:4]:
        # Custom error types and mapping keys can both contain arbitrary input.
        kind = item["type"] if item["type"] in _VALIDATION_TYPES else "validation_error"
        parts = [kind]
        location = item["loc"][:8]
        if any(type(value) is str and value in _OUTPUT_FIELDS for value in location):
            parts.append(
                ".".join(
                    value
                    if type(value) is str and value in _OUTPUT_FIELDS
                    else "[]"
                    if type(value) is int
                    else "?"
                    for value in location
                )
            )
        if kind == "value_error" and (
            invariant := _VALIDATION_INVARIANTS.get(item["msg"])
        ):
            parts.append(invariant)
        frames.append(":".join(parts))
    return frames


def _source_frames(chain: list[Exception]) -> list[str]:
    """Render only project source locations, never traceback text, code, or locals."""

    frames: list[str] = []
    for error in chain:
        traceback = error.__traceback__
        while traceback is not None:
            code = traceback.tb_frame.f_code
            marker = "/alon_ai/"
            if marker in code.co_filename:
                frame = (
                    "alon_ai/"
                    + code.co_filename.rsplit(marker, 1)[1]
                    + f":{traceback.tb_lineno}:{code.co_name}"
                )
                if frame not in frames:
                    frames.append(frame)
            traceback = traceback.tb_next
    return frames[-8:]


def diagnostic_for_error(stage: str, error: Exception) -> RunDiagnostic:
    """Classify an exception without ever serializing its text or provider content."""

    chain = list(_chain(error))
    frames = [_frame(item) for item in chain]
    validation = next(
        (item for item in reversed(chain) if isinstance(item, ValidationError)), None
    )
    classified = next(
        (
            item
            for item in reversed(chain)
            if isinstance(
                item,
                (
                    AccountingDenied,
                    ProviderFailure,
                    ExperimentError,
                    ResearchToolError,
                    httpx.HTTPStatusError,
                    UnexpectedModelBehavior,
                    UsageLimitExceeded,
                ),
            )
        ),
        None,
    )
    if validation is not None:
        code = "VALIDATION_ERROR"
        frames.extend(_validation_frames(validation))
        classified = validation
    elif isinstance(classified, AccountingDenied):
        code = classified.reason.value
    elif isinstance(classified, ProviderFailure):
        code = (
            f"HTTP_{classified.http_status}"
            if classified.http_status is not None
            else classified.code.value
        )
    elif isinstance(classified, ExperimentError):
        code = _experiment_code(classified)
    elif isinstance(classified, ResearchToolError):
        code = (
            f"HTTP_{classified.http_status}"
            if classified.http_status is not None
            else classified.code
        )
    elif isinstance(classified, httpx.HTTPStatusError):
        status = classified.response.status_code
        code = f"HTTP_{status}" if 100 <= status <= 599 else "HTTP_REQUEST_FAILED"
    elif isinstance(classified, UnexpectedModelBehavior):
        code = "MODEL_RESPONSE_UNEXPECTED"
    elif isinstance(classified, UsageLimitExceeded):
        code = "USAGE_LIMIT_EXCEEDED"
    else:
        code = "UNEXPECTED_ERROR"
    return RunDiagnostic(
        stage=stage,
        error_type=type(classified or error).__name__,
        code=code,
        message=_MESSAGES.get(
            code,
            f"The provider returned HTTP {code[5:]}."
            if code.startswith("HTTP_") and code[5:].isdigit()
            else _MESSAGES["UNEXPECTED_ERROR"],
        ),
        frames=[*frames, *_source_frames(chain)][:16],
    )


async def record_diagnostic(
    store: AgentRunRepository, run_id: UUID, stage: str, error: Exception
) -> RunDiagnostic:
    """Append a safe diagnostic event and emit the same safe fields to local logs."""

    diagnostic = diagnostic_for_error(stage, error)
    logger = structlog.get_logger(__name__)
    try:
        await store.append_diagnostic(run_id, diagnostic.model_dump(mode="json"))
    except Exception:  # noqa: BLE001 - diagnostics must not replace the root failure
        logger.error(
            "agent_run_diagnostic_persistence_failed",
            run_id=str(run_id),
            stage=diagnostic.stage,
        )
    logger.error(
        "agent_run_failure",
        run_id=str(run_id),
        stage=diagnostic.stage,
        error_type=diagnostic.error_type,
        code=diagnostic.code,
        frames=diagnostic.frames,
    )
    return diagnostic
