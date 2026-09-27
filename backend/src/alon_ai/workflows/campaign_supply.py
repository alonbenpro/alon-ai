from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dbos import DBOS, SetWorkflowID

from alon_ai.services import workflow_campaign_supply as service
from alon_ai.workflows.schemas.campaign_supply import CampaignSupplyWorkflowRequest
from alon_ai.workflows.schemas.runtime import DBOS_APPLICATION_VERSION


async def _test_barrier(phase: str) -> None:
    if os.environ.get("ALON_AI_SUPPLY_DBOS_TEST_BARRIER") != phase:
        return
    ready = os.environ.get("ALON_AI_SUPPLY_DBOS_TEST_READY")
    release = os.environ.get("ALON_AI_SUPPLY_DBOS_TEST_RELEASE")
    if not ready or not release:
        raise RuntimeError("SUPPLY_DBOS_TEST_BARRIER_PATH_MISSING")
    Path(ready).touch()
    while not Path(release).exists():
        await asyncio.sleep(0.01)


@DBOS.step(
    name="campaign_supply_business_command", retries_allowed=False, preemptible=True
)
async def _business_step(payload_json: str, workflow_id: str) -> str:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._business_step(
            engine,
            payload_json,
            workflow_id,
            application_version=DBOS.application_version,
            barrier=_test_barrier,
        )


@DBOS.step(name="deliver_campaign_supply_receipt", retries_allowed=False)
async def _delivery_step(workflow_id: str, receipt_json: str) -> None:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._delivery_step(
            engine,
            workflow_id,
            receipt_json,
            application_version=DBOS.application_version,
            barrier=_test_barrier,
        )


@DBOS.workflow(name="campaign_supply_command")
async def campaign_supply_command_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, str]:
    receipt_json = await _business_step(payload_json, workflow_id)
    await _delivery_step(workflow_id, receipt_json)
    return json.loads(receipt_json)


async def start_campaign_supply_workflow(
    engine,
    request: CampaignSupplyWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await service.start_binding(
        engine, request, application_version=application_version
    )
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            campaign_supply_command_workflow,
            request.model_dump_json(exclude_computed_fields=True),
            binding.dbos_workflow_id,
        )


async def finalize_campaign_supply_workflow(
    engine, workflow_id: str, receipt: dict[str, str]
) -> None:
    await service.advance_delivery(engine, workflow_id, receipt, "RUNTIME_COMPLETED")


async def assert_campaign_supply_compatible_application_version(
    engine, application_version: str
) -> None:
    await service.assert_campaign_supply_compatible_application_version(
        engine, application_version
    )


async def recover_campaign_supply_workflows(
    engine, application_version: str = DBOS_APPLICATION_VERSION
) -> dict[str, dict[str, str]]:
    await assert_campaign_supply_compatible_application_version(
        engine, application_version
    )
    workflow_ids = await service.pending_campaign_supply_workflows(
        engine, application_version
    )
    recovered: dict[str, dict[str, str]] = {}
    for workflow_id in workflow_ids:
        handle = await DBOS.retrieve_workflow_async(workflow_id, existing_workflow=True)
        result = await handle.get_result(polling_interval_sec=0.05)
        if not isinstance(result, dict):
            raise TypeError("SUPPLY_WORKFLOW_RESULT_INVALID")
        receipt = {
            "command_id": str(result["command_id"]),
            "result_id": str(result["result_id"]),
        }
        await finalize_campaign_supply_workflow(engine, workflow_id, receipt)
        recovered[workflow_id] = receipt
    return recovered
