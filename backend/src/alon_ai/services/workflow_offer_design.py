from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.db.repositories.records_offers import OfferRecordsRepository
from alon_ai.db.repositories.workflow_offer_design import OfferDesignWorkflowRepository
from alon_ai.db.repositories.workflow_offer_design import (
    assert_offer_design_compatible_application_version as _assert_offer_design_compatible_application_version,
)
from alon_ai.db.repositories.workflow_offer_design import (
    pending_offer_design_workflows as _pending_offer_design_workflows,
)
from alon_ai.services.schemas.records import CommandReceipt
from alon_ai.services.schemas.records_offer import (
    OfferDesignDecisionRequest,
    OfferDesignStartRequest,
    OfferIdeaRefinementReturnRequest,
    OfferTargetedResearchReturnRequest,
)
from alon_ai.workflows.schemas.offer_design import (
    OfferDesignDecisionWorkflowRequest,
    OfferDesignStartWorkflowRequest,
    OfferDesignWorkflowBinding,
    OfferIdeaRefinementWorkflowRequest,
    OfferTargetedResearchWorkflowRequest,
    _command_receipt,
)


async def assert_offer_design_compatible_application_version(
    engine: AsyncEngine, application_version: str
):
    return await _assert_offer_design_compatible_application_version(
        engine, application_version
    )


async def pending_offer_design_workflows(engine: AsyncEngine, application_version: str):
    return await _pending_offer_design_workflows(engine, application_version)


async def _business_step(
    engine: AsyncEngine,
    payload_json: str,
    workflow_id: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> str:
    payload = json.loads(payload_json)
    kind = payload["operation_kind"]
    raw = payload["request"]
    command_key = UUID(payload["command_key"])
    if kind == "START":
        request = OfferDesignStartRequest.model_validate_json(json.dumps(raw))
        wrapper = OfferDesignStartWorkflowRequest(
            request=request, command_key=command_key
        )
    elif kind == "DECISION" and "gap" not in raw:
        request = OfferDesignDecisionRequest.model_validate_json(json.dumps(raw))
        wrapper = OfferDesignDecisionWorkflowRequest(
            request=request, command_key=command_key
        )
    elif kind == "DECISION":
        request = OfferTargetedResearchReturnRequest.model_validate_json(
            json.dumps(raw)
        )
        wrapper = OfferTargetedResearchWorkflowRequest(
            request=request, command_key=command_key
        )
    else:
        request = OfferIdeaRefinementReturnRequest.model_validate_json(json.dumps(raw))
        wrapper = OfferIdeaRefinementWorkflowRequest(
            request=request, command_key=command_key
        )
    runtime = OfferDesignWorkflowRepository(engine)
    await runtime.require_started(
        workflow_id,
        application_version=application_version,
        request_hash=wrapper.request_hash,
    )
    await barrier("before-business")
    repository = OfferRecordsRepository(engine)
    if kind == "START":
        receipt = await repository.start_offer_design(
            cast(OfferDesignStartRequest, request),
            command_key=command_key,
            workflow_id=workflow_id,
        )
    elif kind == "DECISION" and isinstance(request, OfferDesignDecisionRequest):
        receipt = await repository.decide_offer_design(
            cast(OfferDesignDecisionRequest, request),
            command_key=command_key,
            workflow_id=workflow_id,
        )
    elif kind == "DECISION":
        receipt = await repository.return_for_targeted_research(
            cast(OfferTargetedResearchReturnRequest, request),
            command_key=command_key,
            workflow_id=workflow_id,
        )
    else:
        receipt = await repository.confirm_offer_idea_refinement(
            cast(OfferIdeaRefinementReturnRequest, request),
            command_key=command_key,
            workflow_id=workflow_id,
        )
    await barrier("after-business")
    await runtime.record_business_commit(workflow_id, receipt)
    await barrier("after-binding-commit")
    return receipt.model_dump_json()


async def _deliver_offer_design_receipt(
    engine: AsyncEngine,
    workflow_id: str,
    receipt_json: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> None:
    receipt = _command_receipt(receipt_json)
    await OfferDesignWorkflowRepository(engine).advance_delivery(
        workflow_id, receipt, "RECEIPT_DELIVERED"
    )
    await barrier("after-receipt-delivery")


async def start_binding(
    engine: AsyncEngine, request, *, application_version: str
) -> OfferDesignWorkflowBinding:
    return await OfferDesignWorkflowRepository(engine).start(
        request, application_version=application_version
    )


async def advance_delivery(
    engine: AsyncEngine, workflow_id: str, receipt: CommandReceipt, state: str
) -> None:
    return await OfferDesignWorkflowRepository(engine).advance_delivery(
        workflow_id, receipt, state
    )
