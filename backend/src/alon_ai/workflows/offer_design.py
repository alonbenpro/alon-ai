from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dbos import DBOS, SetWorkflowID

from alon_ai.services import workflow_offer_design as service
from alon_ai.workflows.schemas.offer_design import _command_receipt
from alon_ai.workflows.schemas.runtime import DBOS_APPLICATION_VERSION


async def _at_test_barrier(phase: str) -> None:
    if os.environ.get("ALON_AI_OFFER_DBOS_TEST_BARRIER") != phase:
        return
    ready = os.environ.get("ALON_AI_OFFER_DBOS_TEST_READY")
    release = os.environ.get("ALON_AI_OFFER_DBOS_TEST_RELEASE")
    if not ready or not release:
        raise RuntimeError("DBOS_TEST_BARRIER_PATH_MISSING")
    Path(ready).touch()
    while not Path(release).exists():
        await asyncio.sleep(0.01)


async def _business_step(payload_json: str, workflow_id: str) -> str:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._business_step(
            engine,
            payload_json,
            workflow_id,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.step(
    name="offer_design_business_command", retries_allowed=False, preemptible=True
)
async def _offer_design_business_step(payload_json: str, workflow_id: str) -> str:
    return await _business_step(payload_json, workflow_id)


@DBOS.step(name="deliver_offer_design_receipt", retries_allowed=False)
async def _deliver_offer_design_receipt(workflow_id: str, receipt_json: str) -> None:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._deliver_offer_design_receipt(
            engine,
            workflow_id,
            receipt_json,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.workflow(name="offer_design_command")
async def offer_design_command_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, object]:
    receipt_json = await _offer_design_business_step(payload_json, workflow_id)
    await _deliver_offer_design_receipt(workflow_id, receipt_json)
    return json.loads(receipt_json)


async def start_offer_design_workflow(
    engine, request, *, application_version: str = DBOS_APPLICATION_VERSION
):
    binding = await service.start_binding(
        engine, request, application_version=application_version
    )
    payload = request.model_dump(mode="json", exclude_computed_fields=True)
    payload["operation_kind"] = binding.operation_kind
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            offer_design_command_workflow,
            json.dumps(payload, sort_keys=True),
            binding.dbos_workflow_id,
        )


async def finalize_offer_design_workflow(
    engine, workflow_id: str, result: dict[str, object]
) -> None:
    await service.advance_delivery(
        engine, workflow_id, _command_receipt(result), "RUNTIME_COMPLETED"
    )


async def assert_offer_design_compatible_application_version(
    engine, application_version: str
) -> None:
    await service.assert_offer_design_compatible_application_version(
        engine, application_version
    )


async def recover_offer_design_workflows(
    engine, application_version: str = DBOS_APPLICATION_VERSION
) -> dict[str, dict[str, object]]:
    await assert_offer_design_compatible_application_version(
        engine, application_version
    )
    rows = await service.pending_offer_design_workflows(engine, application_version)
    recovered: dict[str, dict[str, object]] = {}
    for workflow_id in rows:
        handle = await DBOS.retrieve_workflow_async(workflow_id, existing_workflow=True)
        result = await handle.get_result(polling_interval_sec=0.05)
        if not isinstance(result, dict):
            raise TypeError(f"DBOS_WORKFLOW_RESULT_INVALID: {workflow_id}")
        await finalize_offer_design_workflow(engine, workflow_id, result)
        recovered[workflow_id] = result
    return recovered
