from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.db.repositories.records import (
    ProductRecordsRepository,
)
from alon_ai.db.repositories.workflow_market_research import (
    MarketResearchDecisionWorkflowRepository,
    MarketResearchWorkflowRepository,
)
from alon_ai.db.repositories.workflow_market_research import (
    assert_compatible_application_version as _assert_compatible_application_version,
)
from alon_ai.db.repositories.workflow_market_research import (
    pending_market_research_decision_workflows as _pending_market_research_decision_workflows,
)
from alon_ai.db.repositories.workflow_market_research import (
    pending_market_research_workflows as _pending_market_research_workflows,
)
from alon_ai.services.schemas.records import (
    CommandReceipt,
    MarketResearchOutcomeReceipt,
    MarketResearchTransitionReceipt,
    MaterialPivotDecisionReceipt,
    ProductRecordsDenied,
    ResearchContinuationReceipt,
)
from alon_ai.workflows.schemas.market_research import (
    InconclusiveSupplementWorkflowRequest,
    MarketResearchDecisionWorkflowBinding,
    MarketResearchOutcomeWorkflowRequest,
    MarketResearchWorkflowBinding,
    MarketResearchWorkflowRequest,
    MaterialPivotDecisionWorkflowRequest,
)


async def assert_compatible_application_version(
    engine: AsyncEngine, application_version: str
):
    return await _assert_compatible_application_version(engine, application_version)


async def pending_market_research_decision_workflows(
    engine: AsyncEngine, application_version: str
):
    return await _pending_market_research_decision_workflows(
        engine, application_version
    )


async def pending_market_research_workflows(
    engine: AsyncEngine, application_version: str
):
    return await _pending_market_research_workflows(engine, application_version)


async def _start_market_research_business_step(
    engine: AsyncEngine,
    payload_json: str,
    workflow_id: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> str:
    request = MarketResearchWorkflowRequest.model_validate_json(payload_json)
    repository = MarketResearchWorkflowRepository(engine)
    await repository.require_started(
        workflow_id,
        application_version=application_version,
        request_hash=request.request_hash,
    )
    await barrier("before-business")
    await repository.require_started(
        workflow_id,
        application_version=application_version,
        request_hash=request.request_hash,
    )
    receipt = await ProductRecordsRepository(engine).start_market_research(
        request.experiment_id,
        request.cycle_id,
        accepted_idea=request.accepted_idea,
        plan=request.plan,
        command_key=request.command_key,
        runtime_workflow_id=workflow_id,
    )
    await barrier("after-business")
    await repository.record_business_commit(workflow_id, receipt)
    await barrier("after-binding-commit")
    return receipt.model_dump_json()


async def _deliver_market_research_receipt_step(
    engine: AsyncEngine,
    workflow_id: str,
    receipt_json: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> None:
    receipt = MarketResearchTransitionReceipt.model_validate_json(receipt_json)
    await MarketResearchWorkflowRepository(engine).record_receipt_delivery(
        workflow_id, receipt
    )
    await barrier("after-receipt-delivery")


async def start_transition_binding(
    engine: AsyncEngine,
    request: MarketResearchWorkflowRequest,
    *,
    application_version: str,
) -> MarketResearchWorkflowBinding:
    return await MarketResearchWorkflowRepository(engine).start(
        request, application_version=application_version
    )


async def complete_transition_delivery(
    engine: AsyncEngine, workflow_id: str, receipt: MarketResearchTransitionReceipt
) -> None:
    return await MarketResearchWorkflowRepository(engine).record_runtime_completion(
        workflow_id, receipt
    )


async def _commit_market_research_outcome_business_step(
    engine: AsyncEngine,
    payload_json: str,
    workflow_id: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> str:
    request = MarketResearchOutcomeWorkflowRequest.model_validate_json(payload_json)
    runtime = MarketResearchDecisionWorkflowRepository(engine)
    await runtime.require_started(
        workflow_id,
        application_version=application_version,
        request_hash=request.request_hash,
    )
    await barrier("before-outcome-business")
    try:
        receipt = await ProductRecordsRepository(engine).commit_market_research_outcome(
            request.attempt_id,
            report=request.report,
            recommendation=request.recommendation,
            verdict=request.verdict,
            committed_by=request.committed_by,
            command_key=request.command_key,
            runtime_workflow_id=workflow_id,
            feedback=request.feedback,
            feedback_validation=request.feedback_validation,
            proposed_idea=request.proposed_idea,
            plan=request.plan,
            budget=request.budget,
            accepted_by=request.accepted_by,
        )
    except ProductRecordsDenied as exc:
        await runtime.record_rejection(workflow_id, exc.reason)
        raise
    await barrier("after-outcome-business")
    await runtime.record_business_commit(workflow_id, receipt)
    await barrier("after-outcome-binding-commit")
    return receipt.model_dump_json()


async def _deliver_market_research_outcome_receipt_step(
    engine: AsyncEngine,
    workflow_id: str,
    receipt_json: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> None:
    receipt = MarketResearchOutcomeReceipt.model_validate_json(receipt_json)
    await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
        workflow_id, receipt, expected="BUSINESS_COMMITTED", target="RECEIPT_DELIVERED"
    )
    await barrier("after-outcome-receipt-delivery")


async def _decide_material_pivot_business_step(
    engine: AsyncEngine,
    payload_json: str,
    workflow_id: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> str:
    request = MaterialPivotDecisionWorkflowRequest.model_validate_json(payload_json)
    runtime = MarketResearchDecisionWorkflowRepository(engine)
    await runtime.require_started(
        workflow_id,
        application_version=application_version,
        request_hash=request.request_hash,
    )
    try:
        receipt = await ProductRecordsRepository(engine).decide_material_pivot(
            request.verdict_id,
            decision_id=request.decision_id,
            decision=request.decision,
            decided_by=request.decided_by,
            reason_code=request.reason_code,
            command_key=request.command_key,
            proposed_idea=request.proposed_idea,
            feedback=request.feedback,
            feedback_validation=request.feedback_validation,
            plan=request.plan,
            budget=request.budget,
            accepted_by=request.accepted_by,
            runtime_workflow_id=workflow_id,
        )
    except ProductRecordsDenied as exc:
        await runtime.record_rejection(workflow_id, exc.reason)
        raise
    await runtime.record_business_commit(workflow_id, receipt)
    return receipt.model_dump_json()


async def _start_inconclusive_supplement_business_step(
    engine: AsyncEngine,
    payload_json: str,
    workflow_id: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> str:
    request = InconclusiveSupplementWorkflowRequest.model_validate_json(payload_json)
    runtime = MarketResearchDecisionWorkflowRepository(engine)
    await runtime.require_started(
        workflow_id,
        application_version=application_version,
        request_hash=request.request_hash,
    )
    try:
        receipt = await ProductRecordsRepository(engine).start_inconclusive_supplement(
            request.verdict_id,
            feedback=request.feedback,
            feedback_validation=request.feedback_validation,
            plan=request.plan,
            budget=request.budget,
            accepted_by=request.accepted_by,
            command_key=request.command_key,
            runtime_workflow_id=workflow_id,
        )
    except ProductRecordsDenied as exc:
        await runtime.record_rejection(workflow_id, exc.reason)
        raise
    await runtime.record_business_commit(workflow_id, receipt)
    return receipt.model_dump_json()


async def _deliver_material_pivot_receipt_step(
    engine: AsyncEngine,
    workflow_id: str,
    receipt_json: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> None:
    receipt = MaterialPivotDecisionReceipt.model_validate_json(receipt_json)
    await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
        workflow_id, receipt, expected="BUSINESS_COMMITTED", target="RECEIPT_DELIVERED"
    )


async def _deliver_inconclusive_supplement_receipt_step(
    engine: AsyncEngine,
    workflow_id: str,
    receipt_json: str,
    *,
    application_version: str,
    barrier: Callable[[str], Awaitable[None]],
) -> None:
    receipt = ResearchContinuationReceipt.model_validate_json(receipt_json)
    await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
        workflow_id, receipt, expected="BUSINESS_COMMITTED", target="RECEIPT_DELIVERED"
    )


async def start_outcome_binding(
    engine: AsyncEngine,
    request: MarketResearchOutcomeWorkflowRequest,
    *,
    application_version: str,
) -> MarketResearchDecisionWorkflowBinding:
    return await MarketResearchDecisionWorkflowRepository(engine).start_outcome(
        request, application_version=application_version
    )


async def start_pivot_binding(
    engine: AsyncEngine,
    request: MaterialPivotDecisionWorkflowRequest,
    *,
    application_version: str,
) -> MarketResearchDecisionWorkflowBinding:
    return await MarketResearchDecisionWorkflowRepository(engine).start_pivot(
        request, application_version=application_version
    )


async def start_supplement_binding(
    engine: AsyncEngine,
    request: InconclusiveSupplementWorkflowRequest,
    *,
    application_version: str,
) -> MarketResearchDecisionWorkflowBinding:
    return await MarketResearchDecisionWorkflowRepository(engine).start_supplement(
        request, application_version=application_version
    )


async def advance_decision_delivery(
    engine: AsyncEngine,
    workflow_id: str,
    receipt: CommandReceipt,
    *,
    expected: str,
    target: str,
) -> None:
    return await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
        workflow_id, receipt, expected=expected, target=target
    )
