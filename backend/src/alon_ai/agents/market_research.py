"""Typed, advisory Market Research synthesis over accepted first-party inputs."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from alon_ai.agents.schemas.openai import OpenAIProfile
from alon_ai.integrations.schemas.provider import (
    Capability,
    ContentField,
    Purpose,
    StrictDTO,
)
from alon_ai.policies.provider_rights import ProviderUsageGrant

MARKET_EVIDENCE_POLICY_VERSION = "market-retained-research-v1"
_MARKET_EVIDENCE_FIELDS = {
    Capability.BRAVE_WEB_COVERAGE: frozenset(
        {ContentField.URL, ContentField.TITLE, ContentField.TEXT}
    ),
    Capability.FIRECRAWL_MAP: frozenset({ContentField.URL}),
    Capability.FIRECRAWL_PAGE_CAPTURE: frozenset(
        {ContentField.URL, ContentField.TITLE, ContentField.TEXT}
    ),
    Capability.FIRECRAWL_PDF_CAPTURE: frozenset(
        {ContentField.URL, ContentField.TITLE, ContentField.TEXT}
    ),
    Capability.FIRECRAWL_JS_RETRIEVAL: frozenset(
        {ContentField.URL, ContentField.TITLE, ContentField.TEXT}
    ),
}


def market_evidence_permitted(grant: ProviderUsageGrant, field: ContentField) -> bool:
    """Application policy for content admitted to Market synthesis.

    Provider retention rights are necessary but do not grant model-input purpose.
    """

    return grant.purpose is Purpose.RESEARCH and field in _MARKET_EVIDENCE_FIELDS.get(
        grant.capability, frozenset()
    )


AdviceText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
ReferenceText = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class MarketDimension(StrEnum):
    CUSTOMER_DEMAND = "CUSTOMER_DEMAND"
    COMPETITION = "COMPETITION"
    PRICING = "PRICING"
    DELIVERY_FEASIBILITY = "DELIVERY_FEASIBILITY"
    RISKS = "RISKS"


class EvidenceStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    MIXED = "MIXED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class FindingBasis(StrEnum):
    RETAINED_EVIDENCE = "RETAINED_EVIDENCE"
    HYPOTHESIS = "HYPOTHESIS"
    ESTIMATE = "ESTIMATE"
    UNKNOWN = "UNKNOWN"


class ProposedRecommendation(StrEnum):
    PROCEED_TO_OFFER = "PROCEED_TO_OFFER"
    REFINE_SAME_IDEA = "REFINE_SAME_IDEA"
    MATERIAL_PIVOT_RECOMMENDED = "MATERIAL_PIVOT_RECOMMENDED"
    KILL_IDEA = "KILL_IDEA"
    INCONCLUSIVE = "INCONCLUSIVE"


class MarketFinding(BaseModel):
    """One material claim with its own evidence basis and caveats."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    dimension: MarketDimension
    status: EvidenceStatus
    basis: FindingBasis
    claim: AdviceText
    source_refs: tuple[ReferenceText, ...]
    limitations: tuple[AdviceText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_basis(self) -> Self:
        refs = self.source_refs
        if any(ref.strip() != ref for ref in refs):
            raise ValueError("finding source references must be exact")
        if len(refs) != len(set(refs)):
            raise ValueError("finding source references must be unique")
        if self.basis is FindingBasis.RETAINED_EVIDENCE:
            if not refs:
                raise ValueError("retained evidence finding requires source references")
        elif refs or self.status is not EvidenceStatus.INSUFFICIENT_EVIDENCE:
            raise ValueError("non-evidence finding must expose insufficient evidence")
        return self


class MarketResearchAdvice(StrictDTO):
    """Synthesis for operator review; no verdict or workflow authority."""

    findings: tuple[MarketFinding, ...] = Field(min_length=1)
    limitations: tuple[AdviceText, ...] = Field(min_length=1)
    proposed_recommendation: ProposedRecommendation


def validate_market_references(
    advice: MarketResearchAdvice, allowed_refs: frozenset[str]
) -> None:
    """Bind model citations to exact retained IDs supplied for this dispatch.

    Membership is an identity check. It does not prove that a cited record
    semantically supports the finding.
    """

    cited = {ref for finding in advice.findings for ref in finding.source_refs}
    if not cited <= allowed_refs:
        raise PermissionError(
            "market finding cites an unknown retained evidence reference"
        )


def _validate_market_output(output: StrictDTO, input_json: str) -> None:
    """Check model citations against exact retained IDs after typed parsing."""

    if not isinstance(output, MarketResearchAdvice):
        raise PermissionError("market advice type is required")
    try:
        payload = json.loads(input_json)
    except (TypeError, ValueError) as exc:
        raise PermissionError("retained evidence input is malformed") from exc
    if not isinstance(payload, dict):
        raise PermissionError("retained evidence input is malformed")
    supplied = payload.get("retained_evidence")
    if not isinstance(supplied, list):
        raise PermissionError("retained evidence input is missing")
    refs: list[str] = []
    for entry in supplied:
        if not isinstance(entry, dict) or not isinstance(entry.get("ref"), str):
            raise PermissionError("retained evidence reference is malformed")
        ref = entry["ref"]
        if not ref or ref.strip() != ref:
            raise PermissionError("retained evidence reference is malformed")
        refs.append(ref)
    if len(refs) != len(set(refs)):
        raise PermissionError("retained evidence references must be unique")
    validate_market_references(output, frozenset(refs))


_STRING = {"type": "string"}
_STRINGS = {"type": "array", "items": _STRING}
_FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "dimension": {
            "type": "string",
            "enum": [item.value for item in MarketDimension],
        },
        "status": {"type": "string", "enum": [item.value for item in EvidenceStatus]},
        "basis": {"type": "string", "enum": [item.value for item in FindingBasis]},
        "claim": _STRING,
        "source_refs": _STRINGS,
        "limitations": _STRINGS,
    },
    "required": [
        "dimension",
        "status",
        "basis",
        "claim",
        "source_refs",
        "limitations",
    ],
    "additionalProperties": False,
}
_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {"type": "array", "items": _FINDING_SCHEMA},
        "limitations": _STRINGS,
        "proposed_recommendation": {
            "type": "string",
            "enum": [item.value for item in ProposedRecommendation],
        },
    },
    "required": ["findings", "limitations", "proposed_recommendation"],
    "additionalProperties": False,
}

_INSTRUCTIONS = (
    "Synthesize only the supplied exact, accepted IDEA_BRIEF and governed retained "
    "evidence. Treat the idea brief as first-party intent, not proof of market "
    "demand. Every material finding must have its own basis, evidence status, "
    "claim, source_refs, and limitations. Use exact retained evidence IDs from "
    "the input only when their content supports the claim. Show contradictory "
    "evidence and stale or missing evidence in the findings or limitations; do "
    "not claim that stale material is current. Label unsupported hypotheses, "
    "estimates, and unknowns explicitly and give them no source_refs. Return one "
    "proposed recommendation for operator review. This is advisory synthesis "
    "only: do not issue record commands, commit a verdict, transition workflow "
    "state, acquire new research, send messages, or book meetings."
)


def market_profile(
    *,
    config_id: UUID,
    config_version: UUID,
    adapter_version: UUID,
    model_identifier: str,
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"],
    max_output_tokens: int,
    timeout_seconds: int = 60,
) -> OpenAIProfile:
    return OpenAIProfile(
        config_id=config_id,
        config_version=config_version,
        adapter_version=adapter_version,
        prompt_version="market-synthesis-v1",
        instructions=_INSTRUCTIONS,
        schema_version="market-advice-v1",
        json_schema=_SCHEMA,
        output_model=MarketResearchAdvice,
        model_identifier=model_identifier,
        reasoning_effort=reasoning_effort,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        output_validator=_validate_market_output,
    )
