from __future__ import annotations

import json
from uuid import UUID

from pydantic import computed_field

from alon_ai.integrations.schemas.provider import StrictDTO
from alon_ai.policies.records_requests import _request_hash
from alon_ai.services.schemas.records import CommandReceipt
from alon_ai.services.schemas.records_offer import (
    OfferDesignDecisionRequest,
    OfferDesignStartRequest,
    OfferIdeaRefinementReturnRequest,
    OfferTargetedResearchReturnRequest,
)

OFFER_DESIGN_WORKFLOW_CONTRACT_VERSION = 1


def _command_receipt(payload: str | dict[str, object]) -> CommandReceipt:
    value = json.loads(payload) if isinstance(payload, str) else payload
    return CommandReceipt(
        command_id=UUID(str(value["command_id"])),
        result_id=UUID(str(value["result_id"])),
    )


class OfferDesignStartWorkflowRequest(StrictDTO):
    request: OfferDesignStartRequest
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return _request_hash(request=self.request)


class OfferDesignDecisionWorkflowRequest(StrictDTO):
    request: OfferDesignDecisionRequest
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return _request_hash(request=self.request)


class OfferTargetedResearchWorkflowRequest(StrictDTO):
    request: OfferTargetedResearchReturnRequest
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return _request_hash(request=self.request)


class OfferIdeaRefinementWorkflowRequest(StrictDTO):
    request: OfferIdeaRefinementReturnRequest
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return _request_hash(request=self.request)


class OfferDesignWorkflowBinding(StrictDTO):
    dbos_workflow_id: str
    application_version: str
    contract_version: int
    operation_kind: str
    request_hash: str
    business_command_key: UUID
    experiment_id: UUID
    cycle_id: UUID
    verdict_id: UUID
    run_id: UUID | None
    delivery_state: str


def offer_design_start_workflow_id(verdict_id: UUID, command_key: UUID) -> str:
    return f"offer-design-start:{verdict_id}:{command_key}"


def offer_design_decision_workflow_id(run_id: UUID, command_key: UUID) -> str:
    return f"offer-design-decision:{run_id}:{command_key}"


def offer_idea_refinement_workflow_id(decision_id: UUID, command_key: UUID) -> str:
    return f"offer-idea-refinement:{decision_id}:{command_key}"
