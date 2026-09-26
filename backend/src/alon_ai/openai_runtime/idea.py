"""Bounded, advisory Idea Discovery and Refinement Responses profiles."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, StringConstraints, model_validator
from sqlalchemy import select

from alon_ai.openai_runtime.contract import (
    OpenAIProfile,
    RoutingFacts,
    canonical_json,
)
from alon_ai.openai_runtime.runtime import (
    AcceptedArtifact,
    AcceptedOperatorProfile,
    OpenAIExecution,
    OpenAIRuntime,
)
from alon_ai.providers.contracts import CallAttribution, StrictDTO
from alon_ai.records import ArtifactInput, ArtifactKind, ProductRecordsRepository
from alon_ai.records import schema as records


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


class IdeaRuntime:
    """Choose the application profile from durable cycle mode, never model output."""

    def __init__(
        self,
        records_repository: ProductRecordsRepository,
        runtimes: Mapping[IdeaStage, OpenAIRuntime],
    ) -> None:
        if set(runtimes) != set(IdeaStage):
            raise ValueError("Idea runtime requires all three stages")
        for stage, runtime in runtimes.items():
            settings = _STAGE_SETTINGS[stage]
            if len(runtime.profiles) != 1:
                raise ValueError("Idea runtime profile does not match its stage")
            profile = next(iter(runtime.profiles.values()))
            if (
                profile.prompt_version != settings[0]
                or profile.schema_version != settings[1]
                or profile.instructions != settings[2]
                or profile.schema_json != canonical_json(settings[3])
                or profile.output_model is not settings[4]
                or runtime.routes.cheap != profile.config_id
            ):
                raise ValueError("Idea runtime profile does not match its stage")
        self.records = records_repository
        self.runtimes = MappingProxyType(dict(runtimes))

    async def _operator_profile(self, experiment_id: UUID) -> AcceptedOperatorProfile:
        async with self.records.engine.connect() as connection:
            profile = (
                (
                    await connection.execute(
                        select(
                            records.operator_profiles.c.id,
                            records.operator_profiles.c.version,
                            records.operator_profiles.c.content_hash,
                        )
                        .select_from(
                            records.experiments.join(
                                records.operator_profiles,
                                (
                                    records.experiments.c.operator_profile_id
                                    == records.operator_profiles.c.id
                                )
                                & (
                                    records.experiments.c.operator_profile_version
                                    == records.operator_profiles.c.version
                                ),
                            )
                        )
                        .where(records.experiments.c.id == experiment_id)
                    )
                )
                .mappings()
                .one_or_none()
            )
        if profile is None:
            raise PermissionError("Idea run requires an exact operator profile")
        return AcceptedOperatorProfile(
            profile_id=profile["id"],
            version=profile["version"],
            content_hash=profile["content_hash"],
            experiment_id=experiment_id,
            profile_schema_version=2,
        )

    async def discover_system(
        self,
        attribution: CallAttribution,
        *,
        facts: RoutingFacts,
        idempotency_key: UUID,
    ) -> OpenAIExecution:
        operator_profile = await self._operator_profile(attribution.experiment_id)
        async with self.records.engine.connect() as connection:
            brief = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.experiment_id
                            == attribution.experiment_id,
                            records.artifacts.c.kind == ArtifactKind.EXPERIMENT_BRIEF,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        if brief is None:
            raise PermissionError("Discovery requires exact ExperimentBrief")
        return await self.runtimes[IdeaStage.SYSTEM_DISCOVERY].run(
            attribution,
            facts=facts,
            sources=(),
            artifacts=(
                AcceptedArtifact(
                    artifact=ArtifactInput(
                        artifact_id=brief["id"],
                        kind=ArtifactKind.EXPERIMENT_BRIEF,
                        version=brief["version"],
                        content_hash=brief["content_hash"],
                        role="EXPERIMENT_BRIEF",
                    ),
                    experiment_id=attribution.experiment_id,
                    schema_version=brief["schema_version"],
                ),
            ),
            operator_profiles=(operator_profile,),
            idempotency_key=idempotency_key,
        )

    async def refine_cycle(
        self,
        attribution: CallAttribution,
        *,
        cycle_id: UUID,
        facts: RoutingFacts,
        idempotency_key: UUID,
    ) -> OpenAIExecution:
        async with self.records.engine.connect() as connection:
            cycle = (
                (
                    await connection.execute(
                        select(records.cycles).where(
                            records.cycles.c.id == cycle_id,
                            records.cycles.c.experiment_id == attribution.experiment_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if cycle is None:
                raise PermissionError("Idea cycle is not in the attributed experiment")
            returned = None
            if cycle["purpose"] not in {"INITIAL", "SAME_INTENT_RETURN"}:
                raise PermissionError(
                    "Idea profile is limited to initial and same-intent cycles"
                )
            schema_version = await connection.scalar(
                select(records.artifacts.c.schema_version).where(
                    records.artifacts.c.id == cycle["seed_artifact_id"],
                    records.artifacts.c.experiment_id == attribution.experiment_id,
                    records.artifacts.c.kind == cycle["seed_kind"],
                    records.artifacts.c.version == cycle["seed_version"],
                    records.artifacts.c.content_hash == cycle["seed_hash"],
                )
            )
        if schema_version is None:
            raise PermissionError("Idea cycle origin is no longer exact")
        if cycle["purpose"] == "SAME_INTENT_RETURN":
            async with self.records.engine.connect() as connection:
                returned = (
                    (
                        await connection.execute(
                            select(records.returns).where(
                                records.returns.c.to_cycle_id == cycle_id,
                                records.returns.c.experiment_id
                                == attribution.experiment_id,
                                records.returns.c.kind == "SAME_INTENT",
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if returned is None:
                    raise PermissionError("same-intent cycle lacks return evidence")
                prior = (
                    (
                        await connection.execute(
                            select(records.artifacts).where(
                                records.artifacts.c.id == returned["idea_artifact_id"],
                                records.artifacts.c.experiment_id
                                == attribution.experiment_id,
                                records.artifacts.c.kind == ArtifactKind.IDEA_BRIEF,
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                feedback = (
                    (
                        await connection.execute(
                            select(records.artifacts).where(
                                records.artifacts.c.id
                                == returned["feedback_artifact_id"],
                                records.artifacts.c.experiment_id
                                == attribution.experiment_id,
                                records.artifacts.c.kind
                                == ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
            if prior is None or feedback is None:
                raise PermissionError("same-intent inputs are no longer exact")
            stage = IdeaStage.RESEARCH_FEEDBACK_REFINEMENT
            operator_profile = await self._operator_profile(attribution.experiment_id)
            return await self.runtimes[stage].run(
                attribution,
                facts=facts,
                sources=(),
                artifacts=(
                    AcceptedArtifact(
                        artifact=ArtifactInput(
                            artifact_id=prior["id"],
                            kind=ArtifactKind.IDEA_BRIEF,
                            version=prior["version"],
                            content_hash=prior["content_hash"],
                            role="PRIOR_IDEA_BRIEF",
                        ),
                        experiment_id=attribution.experiment_id,
                        schema_version=prior["schema_version"],
                        cycle_id=cycle_id,
                        return_id=returned["id"],
                    ),
                    AcceptedArtifact(
                        artifact=ArtifactInput(
                            artifact_id=feedback["id"],
                            kind=ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
                            version=feedback["version"],
                            content_hash=feedback["content_hash"],
                            role="RESEARCH_FEEDBACK",
                        ),
                        experiment_id=attribution.experiment_id,
                        schema_version=feedback["schema_version"],
                        cycle_id=cycle_id,
                        return_id=returned["id"],
                    ),
                ),
                operator_profiles=(operator_profile,),
                idempotency_key=idempotency_key,
            )
        if cycle["idea_mode"] == IdeaStage.USER_SEEDED_REFINEMENT:
            stage = IdeaStage.USER_SEEDED_REFINEMENT
            kind = ArtifactKind.IDEA_SEED
            role = "SEED"
            selection_id = None
        elif cycle["idea_mode"] == IdeaStage.SYSTEM_DISCOVERY:
            if cycle["selection_id"] is None:
                raise PermissionError("System idea cycle lacks candidate selection")
            stage = IdeaStage.SYSTEM_CANDIDATE_REFINEMENT
            kind = ArtifactKind.IDEA_CANDIDATE
            role = "SELECTED_CANDIDATE"
            selection_id = cycle["selection_id"]
        else:
            raise PermissionError("Unknown idea cycle mode")
        if cycle["seed_kind"] != kind:
            raise PermissionError("Idea cycle mode and origin disagree")
        operator_profile = await self._operator_profile(attribution.experiment_id)
        origin = ArtifactInput(
            artifact_id=cycle["seed_artifact_id"],
            kind=kind,
            version=cycle["seed_version"],
            content_hash=cycle["seed_hash"],
            role=role,
        )
        return await self.runtimes[stage].run(
            attribution,
            facts=facts,
            sources=(),
            artifacts=(
                AcceptedArtifact(
                    artifact=origin,
                    experiment_id=attribution.experiment_id,
                    schema_version=schema_version,
                    selection_id=selection_id,
                    cycle_id=cycle_id,
                ),
            ),
            operator_profiles=(operator_profile,),
            idempotency_key=idempotency_key,
        )
