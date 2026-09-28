"""Operator-facing durable Idea run commands and read models."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from alon_ai.services.experiments import OperatorProfileInput

TaskKind = Literal["IDEA_DISCOVERY", "IDEA_REFINEMENT"]
RunStatus = Literal[
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "BLOCKED",
    "FAILED",
    "CANCELLED",
    "OUTCOME_UNKNOWN",
]


class StrictRunDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentRunRequest(StrictRunDTO):
    task_kind: TaskKind
    command_key: UUID


class RunRef(StrictRunDTO):
    run_id: UUID
    experiment_id: UUID
    task_kind: TaskKind
    status: RunStatus
    provider_mode: Literal["live", "fake", "disabled"]
    created_at: datetime


class ResolvedInput(StrictRunDTO):
    artifact_id: UUID
    kind: str
    version: int
    content_hash: str
    role: str
    payload: dict[str, Any] | None


class UsageItem(StrictRunDTO):
    component: str
    quantity: str | None
    cost: str | None
    currency: str
    knowledge: Literal["ESTIMATE", "FINAL", "UNAVAILABLE"]


class OperatorProfileProjection(StrictRunDTO):
    profile_id: UUID
    version: int
    content_hash: str
    capabilities: list[str]
    constraints: list[str]


class RunView(RunRef):
    phase: Literal[
        "ADMITTED",
        "EXECUTING",
        "WAITING_FOR_OPERATOR",
        "ACCEPTED",
        "REJECTED",
        "BLOCKED",
        "CANCELLED",
        "OUTCOME_UNKNOWN",
    ]
    outcome: str | None = None
    blocked_reason: str | None = None
    input_refs: list[ResolvedInput] = Field(default_factory=list)
    resolved_inputs: list[ResolvedInput] = Field(default_factory=list)
    output: dict[str, Any] | None = None
    advice_source: str | None = None
    model_identifier: str | None = None
    profile_id: UUID
    profile_version: int
    operator_profile: OperatorProfileProjection
    receipt_id: UUID | None = None
    pending_cost_usd: str | None = None
    actual_cost_usd: str | None = None
    usage: list[UsageItem] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    review_status: Literal["PENDING", "ACCEPTED", "REJECTED"] = "PENDING"
    cancel_requested: bool = False
    cancel_confirmed: bool = False


class RunResult(StrictRunDTO):
    run_id: UUID
    status: RunStatus
    output: dict[str, Any] | None = None
    advice_source: str | None = None
    receipt_id: UUID | None = None
    actual_cost_usd: str | None = None
    usage: list[UsageItem] = Field(default_factory=list)


class RunEvent(StrictRunDTO):
    sequence: int
    at: datetime
    type: str
    detail: str | None = None


class RunEvents(StrictRunDTO):
    events: list[RunEvent]


class CancelRunRequest(StrictRunDTO):
    command_key: UUID


class CancelRunResult(StrictRunDTO):
    run_id: UUID
    requested: bool
    confirmed: bool
    status: RunStatus


class RejectRunRequest(StrictRunDTO):
    command_key: UUID
    reason: str = Field(min_length=1, max_length=4000)


class SetupIdeaProfileRequest(StrictRunDTO):
    profile: OperatorProfileInput


class SetupIdeaProfileResult(StrictRunDTO):
    profile_id: UUID
    profile_version: int
    budget_usd: str | None
