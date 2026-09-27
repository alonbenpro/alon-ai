"""Bounded, advisory Idea Discovery and Refinement Responses profiles."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator

from alon_ai.agents.schemas.openai import (
    OpenAIProfile,
)
from alon_ai.integrations.schemas.provider import StrictDTO


class IdeaStage(StrEnum):
    USER_SEEDED_REFINEMENT = "USER_SEEDED_REFINEMENT"
    SYSTEM_DISCOVERY = "SYSTEM_DISCOVERY"
    SYSTEM_CANDIDATE_REFINEMENT = "SYSTEM_CANDIDATE_REFINEMENT"
    RESEARCH_FEEDBACK_REFINEMENT = "RESEARCH_FEEDBACK_REFINEMENT"


AdviceText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class IdeaCandidateAdvice(StrictDTO):
    """A hypothesis for an operator to review, not an IDEA_CANDIDATE command."""

    schema_version: Literal[1] = Field(default=1, exclude=True)
    title: AdviceText
    hypothesis: AdviceText
    demand_status: Literal["UNVERIFIED"]
    grounding_refs: tuple[str, ...]
    uncertainties: tuple[AdviceText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def grounded_in_operator_profile(self) -> Self:
        if self.grounding_refs != ("OPERATOR_PROFILE",):
            raise ValueError("discovery grounding must cite the operator profile")
        return self


class IdeaCandidateSetAdvice(StrictDTO):
    candidates: tuple[IdeaCandidateAdvice, ...] = Field(min_length=3, max_length=5)

    @model_validator(mode="after")
    def distinct_candidates(self) -> Self:
        if len(
            {
                (item.title.casefold(), item.hypothesis.casefold())
                for item in self.candidates
            }
        ) != len(self.candidates):
            raise ValueError("discovery candidates must be distinct")
        return self


class IdeaBriefAdvice(StrictDTO):
    """An advisory brief; existing record commands own all state changes."""

    title: AdviceText
    customer: AdviceText
    problem: AdviceText
    core_intent: AdviceText
    intent_relationship: Literal[
        "PRESERVES_CORE_INTENT",
        "CLARIFIES_CORE_INTENT",
        "NARROWS_CORE_INTENT",
        "MATERIAL_PIVOT",
        "UNRELATED",
    ]
    material_pivot: bool
    buyer: dict[Literal["segment", "role"], AdviceText]
    service_hypothesis: AdviceText
    value_hypothesis: AdviceText
    assumptions: tuple[AdviceText, ...] = Field(min_length=1)
    exclusions: tuple[AdviceText, ...] = Field(min_length=1)
    research_questions: tuple[AdviceText, ...] = Field(min_length=1)
    grounding_refs: tuple[str, ...]
    uncertainties: tuple[AdviceText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def pivot_classification_agrees(self) -> Self:
        if self.material_pivot != (self.intent_relationship == "MATERIAL_PIVOT"):
            raise ValueError("pivot flag and intent relationship disagree")
        return self


def _brief_grounding(refs: tuple[str, ...], required: str) -> bool:
    return (
        required in refs
        and len(refs) == len(set(refs))
        and set(refs)
        <= {
            required,
            "OPERATOR_PROFILE",
        }
    )


class SeededIdeaBriefAdvice(IdeaBriefAdvice):
    @model_validator(mode="after")
    def grounded_in_seed(self) -> Self:
        if not _brief_grounding(self.grounding_refs, "SEED"):
            raise ValueError("seeded brief grounding must cite the seed")
        return self


class SelectedCandidateIdeaBriefAdvice(IdeaBriefAdvice):
    @model_validator(mode="after")
    def grounded_in_selection(self) -> Self:
        if not _brief_grounding(self.grounding_refs, "SELECTED_CANDIDATE"):
            raise ValueError("selected brief grounding must cite the candidate")
        return self


class ReturnedIdeaBriefAdvice(IdeaBriefAdvice):
    @model_validator(mode="after")
    def grounded_in_return(self) -> Self:
        if set(self.grounding_refs) != {"PRIOR_IDEA_BRIEF", "RESEARCH_FEEDBACK"}:
            raise ValueError("returned brief must cite prior brief and feedback")
        return self


class LegacyIdeaBriefAdvice(StrictDTO):
    """Read-only shape for immutable advice written before L07's rich contract."""

    title: AdviceText
    customer: AdviceText
    problem: AdviceText
    core_intent: AdviceText
    intent_relationship: Literal[
        "PRESERVES_CORE_INTENT",
        "CLARIFIES_CORE_INTENT",
        "NARROWS_CORE_INTENT",
        "MATERIAL_PIVOT",
        "UNRELATED",
    ]
    material_pivot: bool
    grounding_refs: tuple[str, ...]
    uncertainties: tuple[AdviceText, ...] = Field(min_length=1)


_STRING = {"type": "string"}
_STRINGS = {"type": "array", "items": _STRING}
_BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "title": _STRING,
        "customer": _STRING,
        "problem": _STRING,
        "core_intent": _STRING,
        "intent_relationship": {
            "type": "string",
            "enum": [
                "PRESERVES_CORE_INTENT",
                "CLARIFIES_CORE_INTENT",
                "NARROWS_CORE_INTENT",
                "MATERIAL_PIVOT",
                "UNRELATED",
            ],
        },
        "material_pivot": {"type": "boolean"},
        "buyer": {
            "type": "object",
            "properties": {"segment": _STRING, "role": _STRING},
            "required": ["segment", "role"],
            "additionalProperties": False,
        },
        "service_hypothesis": _STRING,
        "value_hypothesis": _STRING,
        "assumptions": _STRINGS,
        "exclusions": _STRINGS,
        "research_questions": _STRINGS,
        "grounding_refs": _STRINGS,
        "uncertainties": _STRINGS,
    },
    "required": [
        "title",
        "customer",
        "problem",
        "core_intent",
        "intent_relationship",
        "material_pivot",
        "buyer",
        "service_hypothesis",
        "value_hypothesis",
        "assumptions",
        "exclusions",
        "research_questions",
        "grounding_refs",
        "uncertainties",
    ],
    "additionalProperties": False,
}
_CANDIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": _STRING,
        "hypothesis": _STRING,
        "demand_status": {"type": "string", "enum": ["UNVERIFIED"]},
        "grounding_refs": _STRINGS,
        "uncertainties": _STRINGS,
    },
    "required": [
        "title",
        "hypothesis",
        "demand_status",
        "grounding_refs",
        "uncertainties",
    ],
    "additionalProperties": False,
}
_CANDIDATE_SET_SCHEMA = {
    "type": "object",
    "properties": {"candidates": {"type": "array", "items": _CANDIDATE_SCHEMA}},
    "required": ["candidates"],
    "additionalProperties": False,
}

_STAGE_SETTINGS = {
    IdeaStage.USER_SEEDED_REFINEMENT: (
        "idea-seeded-refinement-v1",
        "idea-brief-advice-v2",
        (
            "Refine only the operator's exact IDEA_SEED. Preserve its core intent; "
            "classify the intent relationship as PRESERVES_CORE_INTENT, "
            "CLARIFIES_CORE_INTENT, NARROWS_CORE_INTENT, MATERIAL_PIVOT, or "
            "UNRELATED; set material_pivot true exactly for MATERIAL_PIVOT. "
            "This classification is advisory and needs operator review. "
            "Cite SEED in grounding_refs only for "
            "claims supported by that input. Identify unknowns. Return advisory JSON "
            "only. Never issue record commands, select candidates, accept ideas, "
            "send messages, or invent market evidence."
        ),
        _BRIEF_SCHEMA,
        SeededIdeaBriefAdvice,
    ),
    IdeaStage.SYSTEM_DISCOVERY: (
        "idea-system-discovery-v1",
        "idea-candidate-set-advice-v3",
        (
            "Suggest 3 to 5 distinct business idea hypotheses grounded in the exact "
            "operator profile and ExperimentBrief constraints. Cite OPERATOR_PROFILE "
            "only for capability and constraint facts; no external market evidence has "
            "been supplied, so demand must be identified as unverified. Return an "
            "object with a candidates array of advisory JSON only. Never "
            "issue record commands, select a candidate, accept an idea, send "
            "messages, or invent observed market evidence."
        ),
        _CANDIDATE_SET_SCHEMA,
        IdeaCandidateSetAdvice,
    ),
    IdeaStage.SYSTEM_CANDIDATE_REFINEMENT: (
        "idea-system-candidate-refinement-v1",
        "idea-brief-advice-v2",
        (
            "Refine only the selected IDEA_CANDIDATE from the existing "
            "SYSTEM_DISCOVERY cycle. Cite SELECTED_CANDIDATE in grounding_refs "
            "only for claims supported by that candidate. Classify the intent "
            "relationship with the same five categories and set material_pivot "
            "true exactly for MATERIAL_PIVOT. Identify unknowns. "
            "Return advisory JSON only. Never issue record commands, select "
            "candidates, accept ideas, send messages, or invent market evidence."
        ),
        _BRIEF_SCHEMA,
        SelectedCandidateIdeaBriefAdvice,
    ),
    IdeaStage.RESEARCH_FEEDBACK_REFINEMENT: (
        "idea-research-feedback-refinement-v1",
        "idea-brief-advice-v3",
        (
            "Refine only the exact current accepted IDEA_BRIEF using the exact "
            "accepted RESEARCH_FEEDBACK_BRIEF. Preserve the same core intent; "
            "classify the relationship and set material_pivot true exactly for "
            "MATERIAL_PIVOT. Cite both PRIOR_IDEA_BRIEF and RESEARCH_FEEDBACK. "
            "Keep research claims unverified unless present in the feedback. Return "
            "advisory JSON only; never accept an idea, create a cycle, or act."
        ),
        _BRIEF_SCHEMA,
        ReturnedIdeaBriefAdvice,
    ),
}


def idea_profile(
    stage: IdeaStage,
    *,
    config_id: UUID,
    config_version: UUID,
    adapter_version: UUID,
    model_identifier: str,
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"],
    max_output_tokens: int,
    timeout_seconds: int = 60,
) -> OpenAIProfile:
    """Bind a reviewed role prompt/schema to an immutable capability config."""

    prompt_version, schema_version, instructions, json_schema, output_model = (
        _STAGE_SETTINGS[stage]
    )
    return OpenAIProfile(
        config_id=config_id,
        config_version=config_version,
        adapter_version=adapter_version,
        prompt_version=prompt_version,
        instructions=instructions,
        schema_version=schema_version,
        json_schema=json_schema,
        output_model=output_model,
        model_identifier=model_identifier,
        reasoning_effort=reasoning_effort,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
    )
