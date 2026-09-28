"""Minimum persisted intake context and operator commands."""

from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntakePolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intake_policy: Literal["R01A_UX_V1"] = "R01A_UX_V1"
    budget_usd: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    launch_stage: Literal["SHADOW"] = "SHADOW"
    guidance: str = Field(default="", max_length=4000)


class IntakeCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_key: UUID


class GenerateIdeaRequest(IntakeCommand):
    generation_guidance: str | None = Field(default=None, max_length=4000)

    @field_validator("generation_guidance")
    @classmethod
    def meaningful_guidance(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("generation guidance is blank")
        return value


class RegenerateIdeaRequest(GenerateIdeaRequest):
    candidate_artifact_id: UUID | None = None


class StartProposalRequest(IntakeCommand):
    candidate_artifact_id: UUID


class ReviseProposalRequest(StartProposalRequest):
    idea_seed: str = Field(min_length=1, max_length=4000)

    @field_validator("idea_seed")
    @classmethod
    def meaningful(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("idea is blank")
        return value


class ProposalSnapshot(BaseModel):
    artifact_id: UUID
    title: str
    hypothesis: str
    demand_status: Literal["UNVERIFIED"]
    uncertainties: list[str]


class ProposalRevisionSnapshot(BaseModel):
    artifact_id: UUID
    version: int
    parent_artifact_id: UUID | None
    title: str
    hypothesis: str
    idea_seed: str
    origin: Literal["GENERATED", "OPERATOR_EDIT"]
    run_id: UUID | None


class ExperimentSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")
    experiment_id: UUID
    name: str
    mode: Literal["USER_SEEDED_REFINEMENT", "SYSTEM_DISCOVERY"]
    state: str
    brief: dict[str, Any]
    idea_seed: str | None
    cycle_id: UUID | None
    latest_run_id: UUID | None
    latest_outcome: str | None
    advice_source: str | None
    advice: dict[str, Any] | None
    accepted_brief: dict[str, Any] | None
    candidates: list[ProposalSnapshot]
    selected_candidate_artifact_id: UUID | None
    retry_safe: bool
    draft: bool
    provider_mode: Literal["disabled", "fake", "live"]
    stage: Literal["IDEA_DISCOVERY", "IDEA_REFINEMENT"]
    stage_status: Literal["RUNNING", "WAITING_FOR_INPUT", "BLOCKED", "COMPLETE"]
    blocked_reason: str | None
    proposal_history: list[ProposalRevisionSnapshot]


class IdeaOperatorContext(BaseModel):
    """Allowlisted Idea-stage profile projection; financial terms stay private."""

    model_config = ConfigDict(extra="forbid")
    ref: UUID
    version: int = Field(ge=1)
    schema_version: int
    hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    capabilities: list[str]
    constraints: list[str]
