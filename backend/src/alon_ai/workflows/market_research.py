from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from uuid import UUID

from dbos import DBOS, SetWorkflowID

from alon_ai.services import workflow_market_research as service
from alon_ai.services.schemas.records import (
    CommandReceipt,
    MarketResearchOutcomeReceipt,
    MarketResearchTransitionReceipt,
)
from alon_ai.workflows.schemas.market_research import (
    InconclusiveSupplementWorkflowRequest,
    MarketResearchOutcomeWorkflowRequest,
    MarketResearchWorkflowRequest,
    MaterialPivotDecisionWorkflowRequest,
)
from alon_ai.workflows.schemas.runtime import DBOS_APPLICATION_VERSION

_test_barrier: Callable[[str], Awaitable[None]] | None = None


def _set_test_barrier_for_testing(
    barrier: Callable[[str], Awaitable[None]] | None,
) -> None:
    global _test_barrier
    _test_barrier = barrier


async def _at_test_barrier(phase: str) -> None:
    if _test_barrier is not None:
        await _test_barrier(phase)


async def assert_compatible_application_version(
    engine, application_version: str
) -> None:
    await service.assert_compatible_application_version(engine, application_version)


@DBOS.step(
    name="start_market_research_business_command",
    retries_allowed=False,
    preemptible=True,
)
async def _start_market_research_business_step(
    payload_json: str, workflow_id: str
) -> str:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._start_market_research_business_step(
            engine,
            payload_json,
            workflow_id,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.step(name="deliver_market_research_receipt", retries_allowed=False)
async def _deliver_market_research_receipt_step(
    workflow_id: str, receipt_json: str
) -> None:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._deliver_market_research_receipt_step(
            engine,
            workflow_id,
            receipt_json,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.workflow(name="idea_refinement_to_market_research")
async def idea_refinement_to_market_research_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, object]:
    receipt_json = await _start_market_research_business_step(payload_json, workflow_id)
    await _deliver_market_research_receipt_step(workflow_id, receipt_json)
    return json.loads(receipt_json)


async def start_market_research_workflow(
    engine,
    request: MarketResearchWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await service.start_transition_binding(
        engine, request, application_version=application_version
    )
    payload_json = request.model_dump_json(exclude_computed_fields=True)
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            idea_refinement_to_market_research_workflow,
            payload_json,
            binding.dbos_workflow_id,
        )


async def finalize_market_research_workflow(
    engine, workflow_id: str, result: dict[str, object]
) -> None:
    receipt = MarketResearchTransitionReceipt.model_validate_json(json.dumps(result))
    await service.complete_transition_delivery(engine, workflow_id, receipt)


async def recover_market_research_workflows(
    engine, application_version: str = DBOS_APPLICATION_VERSION
) -> dict[str, dict[str, object]]:
    """Await and finalize every incomplete workflow owned by this code version."""
    workflow_ids = await service.pending_market_research_workflows(
        engine, application_version
    )
    recovered: dict[str, dict[str, object]] = {}
    for workflow_id in workflow_ids:
        handle = await DBOS.retrieve_workflow_async(workflow_id, existing_workflow=True)
        result = await handle.get_result(polling_interval_sec=0.05)
        if not isinstance(result, dict):
            raise TypeError(
                f"DBOS_WORKFLOW_RESULT_INVALID: {workflow_id} returned {type(result).__name__}"
            )
        await finalize_market_research_workflow(engine, workflow_id, result)
        recovered[workflow_id] = result
    return recovered


@DBOS.step(
    name="commit_market_research_outcome_business_command",
    retries_allowed=False,
    preemptible=True,
)
async def _commit_market_research_outcome_business_step(
    payload_json: str, workflow_id: str
) -> str:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._commit_market_research_outcome_business_step(
            engine,
            payload_json,
            workflow_id,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.step(name="deliver_market_research_outcome_receipt", retries_allowed=False)
async def _deliver_market_research_outcome_receipt_step(
    workflow_id: str, receipt_json: str
) -> None:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._deliver_market_research_outcome_receipt_step(
            engine,
            workflow_id,
            receipt_json,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.workflow(name="market_research_outcome")
async def market_research_outcome_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, object]:
    receipt_json = await _commit_market_research_outcome_business_step(
        payload_json, workflow_id
    )
    await _deliver_market_research_outcome_receipt_step(workflow_id, receipt_json)
    return json.loads(receipt_json)


@DBOS.step(
    name="decide_material_pivot_business_command",
    retries_allowed=False,
    preemptible=True,
)
async def _decide_material_pivot_business_step(
    payload_json: str, workflow_id: str
) -> str:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._decide_material_pivot_business_step(
            engine,
            payload_json,
            workflow_id,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.step(
    name="start_inconclusive_supplement_business_command",
    retries_allowed=False,
    preemptible=True,
)
async def _start_inconclusive_supplement_business_step(
    payload_json: str, workflow_id: str
) -> str:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._start_inconclusive_supplement_business_step(
            engine,
            payload_json,
            workflow_id,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.step(name="deliver_material_pivot_receipt", retries_allowed=False)
async def _deliver_material_pivot_receipt_step(
    workflow_id: str, receipt_json: str
) -> None:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._deliver_material_pivot_receipt_step(
            engine,
            workflow_id,
            receipt_json,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.step(name="deliver_inconclusive_supplement_receipt", retries_allowed=False)
async def _deliver_inconclusive_supplement_receipt_step(
    workflow_id: str, receipt_json: str
) -> None:
    from alon_ai.bootstrap import workflow_engine_scope

    async with workflow_engine_scope() as engine:
        return await service._deliver_inconclusive_supplement_receipt_step(
            engine,
            workflow_id,
            receipt_json,
            application_version=DBOS.application_version,
            barrier=_at_test_barrier,
        )


@DBOS.workflow(name="material_pivot_decision")
async def material_pivot_decision_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, object]:
    receipt_json = await _decide_material_pivot_business_step(payload_json, workflow_id)
    await _deliver_material_pivot_receipt_step(workflow_id, receipt_json)
    return json.loads(receipt_json)


@DBOS.workflow(name="inconclusive_supplement")
async def inconclusive_supplement_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, object]:
    receipt_json = await _start_inconclusive_supplement_business_step(
        payload_json, workflow_id
    )
    await _deliver_inconclusive_supplement_receipt_step(workflow_id, receipt_json)
    return json.loads(receipt_json)


async def start_market_research_outcome_workflow(
    engine,
    request: MarketResearchOutcomeWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await service.start_outcome_binding(
        engine, request, application_version=application_version
    )
    payload_json = request.model_dump_json(exclude_computed_fields=True)
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            market_research_outcome_workflow, payload_json, binding.dbos_workflow_id
        )


async def start_material_pivot_decision_workflow(
    engine,
    request: MaterialPivotDecisionWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await service.start_pivot_binding(
        engine, request, application_version=application_version
    )
    payload_json = request.model_dump_json(exclude_computed_fields=True)
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            material_pivot_decision_workflow, payload_json, binding.dbos_workflow_id
        )


async def start_inconclusive_supplement_workflow(
    engine,
    request: InconclusiveSupplementWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await service.start_supplement_binding(
        engine, request, application_version=application_version
    )
    payload_json = request.model_dump_json(exclude_computed_fields=True)
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            inconclusive_supplement_workflow, payload_json, binding.dbos_workflow_id
        )


async def finalize_market_research_outcome_workflow(
    engine, workflow_id: str, result: dict[str, object]
) -> None:
    receipt = MarketResearchOutcomeReceipt.model_validate(result)
    await service.advance_decision_delivery(
        engine,
        workflow_id,
        receipt,
        expected="RECEIPT_DELIVERED",
        target="RUNTIME_COMPLETED",
    )


async def finalize_market_research_decision_workflow(
    engine, workflow_id: str, result: dict[str, object]
) -> None:
    receipt = CommandReceipt(
        command_id=UUID(str(result["command_id"])),
        result_id=UUID(str(result["result_id"])),
    )
    await service.advance_decision_delivery(
        engine,
        workflow_id,
        receipt,
        expected="RECEIPT_DELIVERED",
        target="RUNTIME_COMPLETED",
    )


async def recover_market_research_decision_workflows(
    engine, application_version: str = DBOS_APPLICATION_VERSION
) -> dict[str, dict[str, object]]:
    """Dispatch or retrieve each compatible decision workflow from pinned input."""
    rows = await service.pending_market_research_decision_workflows(
        engine, application_version
    )
    recovered: dict[str, dict[str, object]] = {}
    for row in rows:
        operation_kind = row["operation_kind"]
        if operation_kind == "OUTCOME":
            request = MarketResearchOutcomeWorkflowRequest.model_validate_json(
                json.dumps(row["request_payload"])
            )
            binding = await service.start_outcome_binding(
                engine, request, application_version=application_version
            )
            workflow = market_research_outcome_workflow
        elif operation_kind == "PIVOT_DECISION":
            request = MaterialPivotDecisionWorkflowRequest.model_validate_json(
                json.dumps(row["request_payload"])
            )
            binding = await service.start_pivot_binding(
                engine, request, application_version=application_version
            )
            workflow = material_pivot_decision_workflow
        elif operation_kind == "INCONCLUSIVE_SUPPLEMENT":
            request = InconclusiveSupplementWorkflowRequest.model_validate_json(
                json.dumps(row["request_payload"])
            )
            binding = await service.start_supplement_binding(
                engine, request, application_version=application_version
            )
            workflow = inconclusive_supplement_workflow
        else:
            raise RuntimeError(
                f"DBOS_WORKFLOW_CONTRACT_UNSUPPORTED: {operation_kind} contract {row['contract_version']}"
            )
        payload_json = request.model_dump_json(exclude_computed_fields=True)
        with SetWorkflowID(binding.dbos_workflow_id):
            handle = await DBOS.start_workflow_async(
                workflow, payload_json, binding.dbos_workflow_id
            )
        result = await handle.get_result(polling_interval_sec=0.05)
        if not isinstance(result, dict):
            raise TypeError(
                f"DBOS_WORKFLOW_RESULT_INVALID: {binding.dbos_workflow_id} returned {type(result).__name__}"
            )
        await finalize_market_research_decision_workflow(
            engine, binding.dbos_workflow_id, result
        )
        recovered[binding.dbos_workflow_id] = result
    return recovered
