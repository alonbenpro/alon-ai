from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.db.repositories.supply import CampaignSupplyRepository
from alon_ai.db.repositories.workflow_campaign_supply import (
    CampaignSupplyWorkflowRepository,
)
from alon_ai.db.repositories.workflow_campaign_supply import (
    assert_campaign_supply_compatible_application_version as _assert_campaign_supply_compatible_application_version,
)
from alon_ai.db.repositories.workflow_campaign_supply import (
    pending_campaign_supply_workflows as _pending_campaign_supply_workflows,
)
from alon_ai.workflows.schemas.campaign_supply import (
    CampaignSupplyWorkflowBinding,
    CampaignSupplyWorkflowRequest,
)


async def assert_campaign_supply_compatible_application_version(
    engine: AsyncEngine, application_version: str
):
    return await _assert_campaign_supply_compatible_application_version(
        engine, application_version
    )


async def pending_campaign_supply_workflows(
    engine: AsyncEngine, application_version: str
):
    return await _pending_campaign_supply_workflows(engine, application_version)


async def _business_step(
    engine: AsyncEngine,
    payload_json: str,
    workflow_id: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> str:
    request = CampaignSupplyWorkflowRequest.model_validate_json(payload_json)
    runtime = CampaignSupplyWorkflowRepository(engine)
    await runtime.require_started(
        workflow_id, request.request_hash, application_version=application_version
    )
    await barrier("before-business")
    await runtime.require_started(
        workflow_id, request.request_hash, application_version=application_version
    )
    repository = CampaignSupplyRepository(engine)
    if request.operation_kind == "CREATE":
        assert request.plan and request.verification_policy_id and request.deadline
        await repository.create(
            request.experiment_id,
            request.plan,
            request.allowed,
            request.verification_policy_id,
            request.deadline,
            command_key=request.command_key,
            workflow_id=workflow_id,
        )
    elif request.operation_kind == "BEGIN_BATCH":
        assert request.slot and request.plan
        await repository.begin_batch(
            request.experiment_id,
            request.slot,
            request.plan,
            request.command_key,
            request.feedback_id,
            workflow_id=workflow_id,
        )
    elif request.operation_kind == "ADMIT_CANDIDATE":
        assert request.batch_id and request.identity_id and request.clearance_id
        await repository.admit_candidate(
            request.batch_id,
            request.identity_id,
            request.clearance_id,
            request.command_key,
            observations=request.observations,
            workflow_id=workflow_id,
        )
    elif request.operation_kind == "RESOLVE_CONTACT":
        assert request.candidate_id and request.source_id
        await repository.resolve_contact(
            request.candidate_id,
            request.source_id,
            request.verification_id,
            command_key=request.command_key,
            workflow_id=workflow_id,
        )
    elif request.operation_kind == "CLOSE_CONTACTABILITY":
        assert request.batch_id
        await repository.close_contactability(
            request.batch_id, request.command_key, workflow_id=workflow_id
        )
    elif request.operation_kind == "CLOSE_QUALIFICATION":
        assert request.batch_id
        await repository.close_qualification(
            request.batch_id, request.command_key, workflow_id=workflow_id
        )
    else:
        assert request.reason
        await repository.stop(
            request.experiment_id,
            request.reason,
            request.command_key,
            workflow_id=workflow_id,
        )
    await barrier("after-business")
    receipt = await runtime.record_business_commit(workflow_id)
    await barrier("after-binding-commit")
    return json.dumps(receipt, sort_keys=True)


async def _delivery_step(
    engine: AsyncEngine,
    workflow_id: str,
    receipt_json: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> None:
    await CampaignSupplyWorkflowRepository(engine).advance_delivery(
        workflow_id, json.loads(receipt_json), "RECEIPT_DELIVERED"
    )


async def start_binding(
    engine: AsyncEngine,
    request: CampaignSupplyWorkflowRequest,
    *,
    application_version: str,
) -> CampaignSupplyWorkflowBinding:
    return await CampaignSupplyWorkflowRepository(engine).start(
        request, application_version=application_version
    )


async def advance_delivery(
    engine: AsyncEngine, workflow_id: str, receipt: dict[str, str], state: str
) -> None:
    return await CampaignSupplyWorkflowRepository(engine).advance_delivery(
        workflow_id, receipt, state
    )
