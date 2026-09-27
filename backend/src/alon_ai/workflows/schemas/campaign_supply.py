from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, computed_field, model_validator

from alon_ai.integrations.schemas.provider import StrictDTO
from alon_ai.policies.campaign_supply import DiscoveryPlan, Filter, StopReason
from alon_ai.policies.records_requests import _request_hash

SUPPLY_WORKFLOW_CONTRACT_VERSION = 1


OperationKind = Literal[
    "CREATE",
    "BEGIN_BATCH",
    "ADMIT_CANDIDATE",
    "RESOLVE_CONTACT",
    "CLOSE_CONTACTABILITY",
    "CLOSE_QUALIFICATION",
    "STOP",
]


class CampaignSupplyWorkflowRequest(StrictDTO):
    operation_kind: OperationKind
    experiment_id: UUID
    command_key: UUID
    batch_id: UUID | None = None
    candidate_id: UUID | None = None
    slot: int | None = None
    plan: DiscoveryPlan | None = None
    allowed: tuple[Filter, ...] = ()
    verification_policy_id: UUID | None = None
    deadline: AwareDatetime | None = None
    feedback_id: UUID | None = None
    identity_id: UUID | None = None
    clearance_id: UUID | None = None
    observations: tuple[Filter, ...] = ()
    source_id: UUID | None = None
    verification_id: UUID | None = None
    reason: StopReason | None = None

    @model_validator(mode="after")
    def valid_shape(self):
        required = {
            "CREATE": (
                self.plan,
                self.allowed,
                self.verification_policy_id,
                self.deadline,
            ),
            "BEGIN_BATCH": (self.slot, self.plan),
            "ADMIT_CANDIDATE": (self.batch_id, self.identity_id, self.clearance_id),
            "RESOLVE_CONTACT": (self.candidate_id, self.source_id),
            "CLOSE_CONTACTABILITY": (self.batch_id,),
            "CLOSE_QUALIFICATION": (self.batch_id,),
            "STOP": (self.reason,),
        }[self.operation_kind]
        if any(value is None or value == () for value in required):
            raise ValueError("missing campaign-supply operation input")
        if self.operation_kind == "BEGIN_BATCH" and self.slot not in (1, 2, 3):
            raise ValueError("invalid supply batch slot")
        return self

    @property
    def subject_id(self) -> UUID:
        if self.operation_kind == "BEGIN_BATCH":
            return UUID(int=self.slot or 0)
        if self.operation_kind == "ADMIT_CANDIDATE":
            return self.identity_id or UUID(int=0)
        if self.operation_kind == "RESOLVE_CONTACT":
            return self.candidate_id or UUID(int=0)
        if self.operation_kind in {"CLOSE_CONTACTABILITY", "CLOSE_QUALIFICATION"}:
            return self.batch_id or UUID(int=0)
        return self.experiment_id

    @computed_field
    @property
    def request_hash(self) -> str:
        if self.operation_kind == "CREATE":
            return _request_hash(
                experiment_id=self.experiment_id,
                initial_plan=self.plan.model_dump(mode="json") if self.plan else None,
                allowed=[item.model_dump(mode="json") for item in self.allowed],
                verification_policy_id=self.verification_policy_id,
                deadline=self.deadline,
            )
        if self.operation_kind == "BEGIN_BATCH":
            return _request_hash(
                experiment_id=self.experiment_id,
                slot=self.slot,
                plan=self.plan,
                feedback_id=self.feedback_id,
            )
        if self.operation_kind == "ADMIT_CANDIDATE":
            return _request_hash(
                batch_id=self.batch_id,
                identity_id=self.identity_id,
                clearance_id=self.clearance_id,
                observations=self.observations,
            )
        if self.operation_kind == "RESOLVE_CONTACT":
            return _request_hash(
                candidate_id=self.candidate_id,
                source_id=self.source_id,
                verification_id=self.verification_id,
            )
        if self.operation_kind in {"CLOSE_CONTACTABILITY", "CLOSE_QUALIFICATION"}:
            return _request_hash(
                batch_id=self.batch_id,
                gate="EMAIL"
                if self.operation_kind == "CLOSE_CONTACTABILITY"
                else "QUALIFICATION",
            )
        return _request_hash(experiment_id=self.experiment_id, reason=self.reason)


class CampaignSupplyWorkflowBinding(StrictDTO):
    dbos_workflow_id: str
    application_version: str
    contract_version: int
    operation_kind: OperationKind
    experiment_id: UUID
    batch_id: UUID | None
    candidate_id: UUID | None
    subject_id: UUID
    request_hash: str
    business_command_key: UUID
    delivery_state: str


class CampaignSupplyNextAction(StrictDTO):
    kind: str
    batch_id: UUID | None = None
    feedback_id: UUID | None = None


def campaign_supply_workflow_id(request: CampaignSupplyWorkflowRequest) -> str:
    suffix = f":{request.slot}" if request.operation_kind == "BEGIN_BATCH" else ""
    return f"campaign-supply:{request.experiment_id}:{request.operation_kind}:{request.subject_id}{suffix}:{request.command_key}"
