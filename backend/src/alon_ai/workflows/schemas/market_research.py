from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import computed_field

from alon_ai.integrations.schemas.provider import StrictDTO
from alon_ai.policies.records_requests import (
    inconclusive_supplement_request_hash,
    market_research_outcome_request_hash,
    market_research_request_hash,
    material_pivot_decision_request_hash,
)
from alon_ai.services.schemas.records import ArtifactInput, ResearchCycleBudgetInput

DECISION_WORKFLOW_CONTRACT_VERSION = 1


TRANSITION_KIND = "IDEA_REFINEMENT_TO_MARKET_RESEARCH"


class MarketResearchWorkflowRequest(StrictDTO):
    experiment_id: UUID
    cycle_id: UUID
    accepted_idea: ArtifactInput
    plan: ArtifactInput
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return market_research_request_hash(
            experiment_id=self.experiment_id,
            cycle_id=self.cycle_id,
            accepted_idea=self.accepted_idea,
            plan=self.plan,
        )


class MarketResearchWorkflowBinding(StrictDTO):
    dbos_workflow_id: str
    application_version: str
    request_hash: str
    business_command_key: UUID
    experiment_id: UUID
    cycle_id: UUID
    delivery_state: str


class MarketResearchOutcomeWorkflowRequest(StrictDTO):
    experiment_id: UUID
    cycle_id: UUID
    attempt_id: UUID
    report: ArtifactInput
    recommendation: ArtifactInput
    verdict: Literal[
        "PROCEED_TO_OFFER",
        "REFINE_SAME_IDEA",
        "MATERIAL_PIVOT_RECOMMENDED",
        "KILL_IDEA",
        "INCONCLUSIVE",
    ]
    committed_by: UUID
    command_key: UUID
    feedback: ArtifactInput | None = None
    feedback_validation: ArtifactInput | None = None
    proposed_idea: ArtifactInput | None = None
    plan: ArtifactInput | None = None
    budget: ResearchCycleBudgetInput | None = None
    accepted_by: UUID | None = None

    @computed_field
    @property
    def request_hash(self) -> str:
        return market_research_outcome_request_hash(
            attempt_id=self.attempt_id,
            report=self.report,
            recommendation=self.recommendation,
            verdict=self.verdict,
            committed_by=self.committed_by,
            feedback=self.feedback,
            feedback_validation=self.feedback_validation,
            proposed_idea=self.proposed_idea,
            plan=self.plan,
            budget=self.budget,
            accepted_by=self.accepted_by,
        )


class MarketResearchDecisionWorkflowBinding(StrictDTO):
    dbos_workflow_id: str
    application_version: str
    contract_version: int
    operation_kind: str
    operation_id: UUID
    business_command_key: UUID
    request_hash: str
    request_payload: dict[str, object]
    experiment_id: UUID
    cycle_id: UUID
    delivery_state: str


class MaterialPivotDecisionWorkflowRequest(StrictDTO):
    experiment_id: UUID
    cycle_id: UUID
    verdict_id: UUID
    decision_id: UUID
    decision: Literal["APPROVED", "DENIED"]
    decided_by: UUID
    reason_code: str
    command_key: UUID
    proposed_idea: ArtifactInput | None = None
    feedback: ArtifactInput | None = None
    feedback_validation: ArtifactInput | None = None
    plan: ArtifactInput | None = None
    budget: ResearchCycleBudgetInput | None = None
    accepted_by: UUID | None = None

    @computed_field
    @property
    def request_hash(self) -> str:
        return material_pivot_decision_request_hash(
            verdict_id=self.verdict_id,
            decision_id=self.decision_id,
            decision=self.decision,
            decided_by=self.decided_by,
            reason_code=self.reason_code,
            proposed_idea=self.proposed_idea,
            feedback=self.feedback,
            feedback_validation=self.feedback_validation,
            plan=self.plan,
            budget=self.budget,
            accepted_by=self.accepted_by,
        )


class InconclusiveSupplementWorkflowRequest(StrictDTO):
    experiment_id: UUID
    cycle_id: UUID
    verdict_id: UUID
    feedback: ArtifactInput
    feedback_validation: ArtifactInput
    plan: ArtifactInput
    budget: ResearchCycleBudgetInput
    accepted_by: UUID
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return inconclusive_supplement_request_hash(
            verdict_id=self.verdict_id,
            feedback=self.feedback,
            feedback_validation=self.feedback_validation,
            plan=self.plan,
            budget=self.budget,
            accepted_by=self.accepted_by,
        )


def market_research_workflow_id(cycle_id: UUID, request_hash: str) -> str:
    """Bind the runtime identity to the immutable cycle and complete request."""
    return f"market-research:{cycle_id}:{request_hash}"


def market_research_outcome_workflow_id(attempt_id: UUID, command_key: UUID) -> str:
    return f"market-research-outcome:{attempt_id}:{command_key}"


def material_pivot_decision_workflow_id(verdict_id: UUID, decision_id: UUID) -> str:
    return f"material-pivot-decision:{verdict_id}:{decision_id}"


def inconclusive_supplement_workflow_id(verdict_id: UUID, command_key: UUID) -> str:
    return f"inconclusive-supplement:{verdict_id}:{command_key}"
