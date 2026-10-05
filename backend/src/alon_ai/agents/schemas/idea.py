"""Versioned input and native output contracts for the combined Idea agent.

These are advisory in-process results. Persisted records and source grants are
validated by the owning services before any finding is accepted as evidence.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, LiteralString, Self, cast, get_args
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import InitErrorDetails, PydanticCustomError, SchemaValidator
from pydantic_core.core_schema import ErrorType

from alon_ai.agents.idea_discovery import IdeaBriefAdvice, IdeaStage
from alon_ai.integrations.schemas.provider import _native_json_schema

_NATIVE_BRIEF_VALIDATOR = SchemaValidator(
    _native_json_schema(IdeaBriefAdvice.__pydantic_core_schema__)
)
_BRIEF_ERROR_TYPES = frozenset(get_args(ErrorType))
_BRIEF_ERROR_REASONS: dict[str, LiteralString] = {
    "model_type": "Brief must be a JSON object.",
    "string_type": "A string is required.",
    "string_too_short": "Non-empty text is required after trimming whitespace.",
    "string_too_long": "Text exceeds the brief field's allowed length.",
    "bool_type": "A JSON boolean is required.",
    "literal_error": "Use only the literal values permitted by the brief schema.",
    "missing": "A required brief field is missing.",
    "extra_forbidden": "Remove fields not permitted by the brief schema.",
    "dict_type": "A JSON object is required.",
    "tuple_type": "A JSON array is required.",
    "too_short": "The required array must not be empty.",
}


def _safe_brief_errors(error: ValidationError) -> list[InitErrorDetails]:
    """Keep schema-owned feedback only; input and arbitrary mapping keys stay local."""
    errors: list[InitErrorDetails] = []
    pivot_error: LiteralString = (
        "Value error, pivot flag and intent relationship disagree"
    )
    for detail in error.errors(
        include_input=False, include_context=False, include_url=False
    ):
        kind = detail["type"] if detail["type"] in _BRIEF_ERROR_TYPES else "value_error"
        location = detail["loc"]
        safe_location = tuple(
            part
            if type(part) is str
            and (
                index == 0
                and part in IdeaBriefAdvice.model_fields
                or index == 1
                and location[0] == "buyer"
                and part in {"segment", "role"}
            )
            else 0
            for index, part in enumerate(location)
        )
        reason = (
            pivot_error
            if detail["msg"] == pivot_error
            else _BRIEF_ERROR_REASONS.get(kind, "Invalid brief field.")
        )
        errors.append(
            {
                "type": PydanticCustomError(cast(LiteralString, kind), reason),
                "loc": safe_location,
                "input": None,
            }
        )
    return errors


Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
InputText = Annotated[
    str, StringConstraints(min_length=1, max_length=4000, pattern=r"\S")
]
ProfileContext = Annotated[str, StringConstraints(min_length=1, max_length=201000)]

Ref = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class _AdvisoryModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class IdeaOperation(StrEnum):
    DISCOVER = "DISCOVER"
    SELECTED_DEEPEN = "SELECTED_DEEPEN"
    REFINE = "REFINE"


class IdeaAgentInput(_AdvisoryModel):
    """Only service-resolved, version-pinned context enters an agent run."""

    schema_version: Literal[1] = 1
    operation: IdeaOperation
    origin_stage: IdeaStage | None = None
    operator_profile_ref: UUID
    profile_context: ProfileContext
    approved_limits_ref: UUID
    idea_version_ref: UUID | None = None
    idea_text: InputText | None = None
    research_refs: tuple[Ref, ...] = ()
    prior_research_summary: ProfileContext | None = None
    generation_guidance: InputText | None = None
    revision_guidance: InputText | None = None

    @model_validator(mode="after")
    def operation_has_exact_context(self) -> Self:
        if self.operation is IdeaOperation.DISCOVER:
            if self.idea_version_ref is not None or self.idea_text is not None:
                raise ValueError("discovery cannot carry a selected idea")
            if self.revision_guidance is not None:
                raise ValueError("discovery cannot carry revision guidance")
        elif self.idea_version_ref is None or self.idea_text is None:
            raise ValueError("deepening and refinement require an exact idea version")
        if (
            self.operation is not IdeaOperation.REFINE
            and self.revision_guidance is not None
        ):
            raise ValueError("revision guidance requires REFINE")
        if len(self.research_refs) != len(set(self.research_refs)):
            raise ValueError("research references must be unique")
        return self


class ResearchTopic(StrEnum):
    PRODUCT_WORKFLOW = "PRODUCT_WORKFLOW"
    CUSTOMER_PROBLEM = "CUSTOMER_PROBLEM"
    BUYER_AND_GEOGRAPHY = "BUYER_AND_GEOGRAPHY"
    MARKET_STRUCTURE = "MARKET_STRUCTURE"
    DEMAND_AND_SPENDING = "DEMAND_AND_SPENDING"
    ALTERNATIVES = "ALTERNATIVES"
    OBSERVED_PRICING = "OBSERVED_PRICING"
    DISTRIBUTION_AND_ADOPTION = "DISTRIBUTION_AND_ADOPTION"
    DELIVERY_FEASIBILITY = "DELIVERY_FEASIBILITY"
    RISK = "RISK"


class ResearchBasis(StrEnum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class Confidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ResearchFinding(_AdvisoryModel):
    topic: ResearchTopic
    basis: ResearchBasis
    claim: Text
    source_refs: tuple[Ref, ...]
    confidence: Confidence
    limitations: tuple[Text, ...] = Field(min_length=1)
    source_excerpt: Text | None = None
    captured_at: datetime | None = None
    published_on: date | None = None
    rights_ref: Ref | None = None
    idea_version_ref: UUID | None = None
    research_version_ref: UUID | None = None

    @model_validator(mode="after")
    def evidence_basis_is_explicit(self) -> Self:
        if self.basis is ResearchBasis.OBSERVED and not self.source_refs:
            raise ValueError("observed finding requires a source")
        if self.basis is ResearchBasis.UNKNOWN and self.source_refs:
            raise ValueError("unknown finding cannot claim source support")
        if len(self.source_refs) != len(set(self.source_refs)):
            raise ValueError("finding source references must be unique")
        return self


class PriceKind(StrEnum):
    EXACT = "EXACT"
    RANGE = "RANGE"
    STARTING_AT = "STARTING_AT"
    QUOTE_ONLY = "QUOTE_ONLY"
    NOT_FOUND = "NOT_FOUND"


class PriceObservation(_AdvisoryModel):
    subject: Text
    kind: PriceKind
    currency: str | None = None
    amount_low: Decimal | None = None
    amount_high: Decimal | None = None
    unit: Text | None = None
    package: Text | None = None
    observed_date: date | None = None
    source_refs: tuple[Ref, ...] = ()

    @model_validator(mode="after")
    def observed_value_has_source(self) -> Self:
        if self.kind is PriceKind.NOT_FOUND:
            if self.amount_low is not None or self.amount_high is not None:
                raise ValueError("not-found price cannot carry an amount")
        elif not self.source_refs:
            raise ValueError("observed price requires a source")
        if self.kind in {PriceKind.EXACT, PriceKind.RANGE, PriceKind.STARTING_AT} and (
            self.amount_low is None
            or self.amount_low < 0
            or not self.currency
            or not self.unit
        ):
            raise ValueError("numeric price requires amount, currency and unit")
        if (
            self.kind in {PriceKind.EXACT, PriceKind.STARTING_AT}
            and self.amount_high is not None
        ):
            raise ValueError("exact or starting price cannot have an upper bound")
        if self.kind is PriceKind.RANGE and (
            self.amount_high is None or self.amount_high < (self.amount_low or 0)
        ):
            raise ValueError("price range requires ordered bounds")
        if self.kind is PriceKind.QUOTE_ONLY and (
            self.amount_low is not None or self.amount_high is not None
        ):
            raise ValueError("quote-only price cannot have an amount")
        return self


class ResearchedOpportunity(_AdvisoryModel):
    title: Text
    customer: Text
    problem: Text
    approach: Text
    commercial_reasoning: Text
    alternatives: tuple[Text, ...] = Field(min_length=1)
    risks: tuple[Text, ...] = Field(min_length=1)
    source_refs: tuple[Ref, ...] = Field(min_length=1)
    findings: tuple[ResearchFinding, ...] = Field(min_length=1)
    unknowns: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def cited_findings_belong_to_option(self) -> Self:
        if len(self.source_refs) != len(set(self.source_refs)):
            raise ValueError("option source references must be unique")
        if not any(f.basis is ResearchBasis.OBSERVED for f in self.findings):
            raise ValueError("a researched option needs an observed finding")
        if not {ref for f in self.findings for ref in f.source_refs} <= set(
            self.source_refs
        ):
            raise ValueError("finding cites a source outside its option")
        return self


class ResearchedCandidateSet(_AdvisoryModel):
    status: Literal["SUCCEEDED"]
    options: tuple[ResearchedOpportunity, ...] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def distinct_options(self) -> Self:
        if len({(o.title.casefold(), o.problem.casefold()) for o in self.options}) != 3:
            raise ValueError("successful discovery requires three distinct options")
        return self


class IncompleteDiscovery(_AdvisoryModel):
    status: Literal["INCOMPLETE"]
    options: tuple[ResearchedOpportunity, ...] = Field(max_length=2)
    gaps: tuple[Text, ...] = Field(min_length=1)


class MarketRecommendation(StrEnum):
    PROCEED = "PROCEED"
    REFINE = "REFINE"
    PIVOT_REQUIRES_APPROVAL = "PIVOT_REQUIRES_APPROVAL"
    STOP = "STOP"
    INCONCLUSIVE = "INCONCLUSIVE"


class MarketResearchAssessment(_AdvisoryModel):
    """Version-bound market case, with no offer package or lead-filter authority."""

    status: Literal["ASSESSED", "INCOMPLETE"] = Field(
        description=(
            "ASSESSED means a completed evidence-backed assessment, not validated demand or sales. "
            "It may recommend INCONCLUSIVE with named gaps and unavailable optional dimensions. "
            "INCOMPLETE means collected evidence cannot support an assessment. "
            "Preserve supported findings and material uncertainty in either result."
        )
    )
    idea_version_ref: UUID
    brief: IdeaBriefAdvice
    findings: tuple[ResearchFinding, ...] = Field(min_length=1)
    coverage: tuple[ResearchTopic, ...]
    gaps: tuple[Text, ...]
    contradictions: tuple[Text, ...]
    source_refs: tuple[Ref, ...]
    price_observations: tuple[PriceObservation, ...] = ()
    recommendation: MarketRecommendation

    @field_validator("brief", mode="before")
    @classmethod
    def parse_historical_rich_brief(cls, value: object) -> IdeaBriefAdvice:
        if isinstance(value, IdeaBriefAdvice):
            return value
        # The retained StrictDTO intentionally validates JSON arrays into tuples
        # only through its JSON entry point. Native agent output arrives nested.
        # Use the same core schema without its generic error wrappers, retaining
        # all strict field/model validators while exposing safe correction detail.
        try:
            return _NATIVE_BRIEF_VALIDATOR.validate_json(json.dumps(value))
        except ValidationError as error:
            safe_error = ValidationError.from_exception_data(
                "Idea brief", _safe_brief_errors(error), hide_input=True
            )
        # Raise outside the handler so raw inputs cannot survive in __context__.
        raise safe_error from None

    @model_validator(mode="after")
    def assessment_citations_and_status(self) -> Self:
        if len(self.source_refs) != len(set(self.source_refs)):
            raise ValueError("assessment source references must be unique")
        cited = {ref for finding in self.findings for ref in finding.source_refs}
        cited.update(
            ref for price in self.price_observations for ref in price.source_refs
        )
        if not cited <= set(self.source_refs):
            raise ValueError("assessment cites an undeclared source")
        if self.status == "INCOMPLETE" and not self.gaps:
            raise ValueError("incomplete assessment requires named gaps")
        if self.recommendation is MarketRecommendation.INCONCLUSIVE and not self.gaps:
            raise ValueError("inconclusive assessment requires named gaps")
        return self


DiscoveryResult = ResearchedCandidateSet | IncompleteDiscovery
IdeaAgentOutput = DiscoveryResult | MarketResearchAssessment
