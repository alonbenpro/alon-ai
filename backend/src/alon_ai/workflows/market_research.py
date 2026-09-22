"""DBOS control plane for the first L04 business transition."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from dbos import DBOS, DBOSConfig, SetWorkflowID
from pydantic import computed_field
from sqlalchemy import insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.config import Settings, get_settings
from alon_ai.db.engine import create_engine
from alon_ai.providers.contracts import StrictDTO
from alon_ai.records import schema as records
from alon_ai.records.models import (
    ArtifactInput,
    MarketResearchTransitionReceipt,
    ProductRecordsDenied,
)
from alon_ai.records.repository import (
    ProductRecordsRepository,
    market_research_request_hash,
)

DBOS_APPLICATION_NAME = "alon-ai-worker"
DBOS_APPLICATION_VERSION = "l04-market-research-v1"
DBOS_SYSTEM_SCHEMA = "dbos"
TRANSITION_KIND = "IDEA_REFINEMENT_TO_MARKET_RESEARCH"
_test_barrier: Callable[[str], Awaitable[None]] | None = None


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


def market_research_workflow_id(cycle_id: UUID, request_hash: str) -> str:
    """Bind the runtime identity to the immutable cycle and complete request."""
    return f"market-research:{cycle_id}:{request_hash}"


def build_dbos_config(
    settings: Settings,
    *,
    executor_id: str,
    application_version: str = DBOS_APPLICATION_VERSION,
) -> DBOSConfig:
    """Build production-style DBOS configuration without schema mutation authority."""
    return DBOSConfig(
        name=DBOS_APPLICATION_NAME,
        system_database_url=settings.dbos_system_database_url.get_secret_value(),
        application_version=application_version,
        executor_id=executor_id,
        dbos_system_schema=DBOS_SYSTEM_SCHEMA,
        run_migrations=False,
        run_admin_server=False,
        enable_otlp=False,
    )


class MarketResearchWorkflowRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def bind(
        self, request: MarketResearchWorkflowRequest, *, application_version: str
    ) -> MarketResearchWorkflowBinding:
        workflow_id = market_research_workflow_id(
            request.cycle_id, request.request_hash
        )
        expected = {
            "dbos_workflow_id": workflow_id,
            "application_version": application_version,
            "request_hash": request.request_hash,
            "business_command_key": request.command_key,
            "experiment_id": request.experiment_id,
            "cycle_id": request.cycle_id,
        }
        async with self.engine.begin() as connection:
            await lock_experiment(connection, request.experiment_id)
            existing = (
                (
                    await connection.execute(
                        select(records.market_research_workflow_bindings).where(
                            or_(
                                records.market_research_workflow_bindings.c.dbos_workflow_id
                                == workflow_id,
                                records.market_research_workflow_bindings.c.business_command_key
                                == request.command_key,
                                records.market_research_workflow_bindings.c.cycle_id
                                == request.cycle_id,
                            )
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                if any(existing[name] != value for name, value in expected.items()):
                    raise ProductRecordsDenied("WORKFLOW_BINDING_CONFLICT")
                return MarketResearchWorkflowBinding(
                    **{name: existing[name] for name in expected},
                    delivery_state=existing["delivery_state"],
                )
            now = datetime.now(UTC)
            await connection.execute(
                insert(records.market_research_workflow_bindings).values(
                    **expected,
                    transition_kind=TRANSITION_KIND,
                    from_state="IDEA_REFINEMENT",
                    to_state="MARKET_RESEARCH",
                    transition_id=None,
                    command_id=None,
                    delivery_state="PENDING",
                    created_at=now,
                    updated_at=now,
                )
            )
            return MarketResearchWorkflowBinding(**expected, delivery_state="PENDING")

    async def _locked(self, connection: AsyncConnection, workflow_id: str):
        experiment_id = await connection.scalar(
            select(records.market_research_workflow_bindings.c.experiment_id).where(
                records.market_research_workflow_bindings.c.dbos_workflow_id
                == workflow_id
            )
        )
        if experiment_id is None:
            raise ProductRecordsDenied("WORKFLOW_BINDING_MISSING")
        await lock_experiment(connection, experiment_id)
        return (
            (
                await connection.execute(
                    select(records.market_research_workflow_bindings)
                    .where(
                        records.market_research_workflow_bindings.c.dbos_workflow_id
                        == workflow_id
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one()
        )

    async def start(
        self, request: MarketResearchWorkflowRequest, *, application_version: str
    ) -> MarketResearchWorkflowBinding:
        binding = await self.bind(request, application_version=application_version)
        async with self.engine.begin() as connection:
            current = await self._locked(connection, binding.dbos_workflow_id)
            if current["delivery_state"] == "PENDING":
                await connection.execute(
                    update(records.market_research_workflow_bindings)
                    .where(
                        records.market_research_workflow_bindings.c.dbos_workflow_id
                        == binding.dbos_workflow_id
                    )
                    .values(delivery_state="STARTED", updated_at=datetime.now(UTC))
                )
                state = "STARTED"
            elif current["delivery_state"] in {
                "STARTED",
                "BUSINESS_COMMITTED",
                "RECEIPT_DELIVERED",
                "RUNTIME_COMPLETED",
            }:
                state = current["delivery_state"]
            else:
                raise ProductRecordsDenied("WORKFLOW_CANCELLED")
        return binding.model_copy(update={"delivery_state": state})

    async def require_started(
        self, workflow_id: str, *, application_version: str, request_hash: str
    ) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if (
                current["application_version"] != application_version
                or current["request_hash"] != request_hash
                or current["delivery_state"]
                not in {
                    "STARTED",
                    "BUSINESS_COMMITTED",
                    "RECEIPT_DELIVERED",
                    "RUNTIME_COMPLETED",
                }
            ):
                raise ProductRecordsDenied("WORKFLOW_NOT_EXECUTABLE")

    async def record_business_commit(
        self,
        workflow_id: str,
        receipt: MarketResearchTransitionReceipt,
    ) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if current["delivery_state"] in {
                "BUSINESS_COMMITTED",
                "RECEIPT_DELIVERED",
            }:
                if (
                    current["transition_id"] != receipt.transition_id
                    or current["command_id"] != receipt.command_id
                ):
                    raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
                return
            if current["delivery_state"] != "STARTED":
                raise ProductRecordsDenied("WORKFLOW_NOT_EXECUTABLE")
            await connection.execute(
                update(records.market_research_workflow_bindings)
                .where(
                    records.market_research_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(
                    transition_id=receipt.transition_id,
                    command_id=receipt.command_id,
                    delivery_state="BUSINESS_COMMITTED",
                    updated_at=datetime.now(UTC),
                )
            )

    async def record_receipt_delivery(
        self, workflow_id: str, receipt: MarketResearchTransitionReceipt
    ) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if current["delivery_state"] == "RECEIPT_DELIVERED":
                if (
                    current["transition_id"] != receipt.transition_id
                    or current["command_id"] != receipt.command_id
                ):
                    raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
                return
            if (
                current["delivery_state"] != "BUSINESS_COMMITTED"
                or current["transition_id"] != receipt.transition_id
                or current["command_id"] != receipt.command_id
            ):
                raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
            await connection.execute(
                update(records.market_research_workflow_bindings)
                .where(
                    records.market_research_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(
                    delivery_state="RECEIPT_DELIVERED",
                    updated_at=datetime.now(UTC),
                )
            )

    async def cancel(self, workflow_id: str) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if current["delivery_state"] == "CANCELLED":
                return
            if current["delivery_state"] not in {"PENDING", "STARTED"}:
                raise ProductRecordsDenied("WORKFLOW_ALREADY_COMMITTED")
            await connection.execute(
                update(records.market_research_workflow_bindings)
                .where(
                    records.market_research_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(delivery_state="CANCELLED", updated_at=datetime.now(UTC))
            )

    async def record_runtime_completion(
        self, workflow_id: str, receipt: MarketResearchTransitionReceipt
    ) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if current["delivery_state"] == "RUNTIME_COMPLETED":
                if (
                    current["transition_id"] != receipt.transition_id
                    or current["command_id"] != receipt.command_id
                ):
                    raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
                return
            if (
                current["delivery_state"] != "RECEIPT_DELIVERED"
                or current["transition_id"] != receipt.transition_id
                or current["command_id"] != receipt.command_id
            ):
                raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
            await connection.execute(
                update(records.market_research_workflow_bindings)
                .where(
                    records.market_research_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(
                    delivery_state="RUNTIME_COMPLETED",
                    updated_at=datetime.now(UTC),
                )
            )


def _set_test_barrier_for_testing(
    barrier: Callable[[str], Awaitable[None]] | None,
) -> None:
    global _test_barrier
    _test_barrier = barrier


async def _at_test_barrier(phase: str) -> None:
    if _test_barrier is not None:
        await _test_barrier(phase)


async def assert_compatible_application_version(
    engine: AsyncEngine, application_version: str
) -> None:
    async with engine.connect() as connection:
        incompatible = (
            (
                await connection.execute(
                    select(
                        records.market_research_workflow_bindings.c.dbos_workflow_id,
                        records.market_research_workflow_bindings.c.application_version,
                    ).where(
                        records.market_research_workflow_bindings.c.delivery_state.in_(
                            (
                                "PENDING",
                                "STARTED",
                                "BUSINESS_COMMITTED",
                                "RECEIPT_DELIVERED",
                            )
                        ),
                        records.market_research_workflow_bindings.c.application_version
                        != application_version,
                    )
                )
            )
            .mappings()
            .first()
        )
    if incompatible is not None:
        raise RuntimeError(
            "DBOS_APPLICATION_VERSION_MISMATCH: "
            f"workflow {incompatible['dbos_workflow_id']} requires "
            f"{incompatible['application_version']}, not {application_version}"
        )


def configure_dbos(
    settings: Settings,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
    executor_id: str,
) -> None:
    DBOS(
        config=build_dbos_config(
            settings,
            executor_id=executor_id,
            application_version=application_version,
        )
    )


@DBOS.step(
    name="start_market_research_business_command",
    retries_allowed=False,
    preemptible=True,
)
async def _start_market_research_business_step(
    payload_json: str, workflow_id: str
) -> str:
    request = MarketResearchWorkflowRequest.model_validate_json(payload_json)
    settings = get_settings()
    engine = create_engine(settings)
    try:
        repository = MarketResearchWorkflowRepository(engine)
        await repository.require_started(
            workflow_id,
            application_version=DBOS.application_version,
            request_hash=request.request_hash,
        )
        await _at_test_barrier("before-business")
        await repository.require_started(
            workflow_id,
            application_version=DBOS.application_version,
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
        await _at_test_barrier("after-business")
        await repository.record_business_commit(workflow_id, receipt)
        await _at_test_barrier("after-binding-commit")
        return receipt.model_dump_json()
    finally:
        await engine.dispose()


@DBOS.step(name="deliver_market_research_receipt", retries_allowed=False)
async def _deliver_market_research_receipt_step(
    workflow_id: str, receipt_json: str
) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        receipt = MarketResearchTransitionReceipt.model_validate_json(receipt_json)
        await MarketResearchWorkflowRepository(engine).record_receipt_delivery(
            workflow_id, receipt
        )
        await _at_test_barrier("after-receipt-delivery")
    finally:
        await engine.dispose()


@DBOS.workflow(name="idea_refinement_to_market_research")
async def idea_refinement_to_market_research_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, object]:
    receipt_json = await _start_market_research_business_step(payload_json, workflow_id)
    await _deliver_market_research_receipt_step(workflow_id, receipt_json)
    return json.loads(receipt_json)


async def start_market_research_workflow(
    engine: AsyncEngine,
    request: MarketResearchWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await MarketResearchWorkflowRepository(engine).start(
        request, application_version=application_version
    )
    payload_json = request.model_dump_json(exclude_computed_fields=True)
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            idea_refinement_to_market_research_workflow,
            payload_json,
            binding.dbos_workflow_id,
        )


async def finalize_market_research_workflow(
    engine: AsyncEngine,
    workflow_id: str,
    result: dict[str, object],
) -> None:
    receipt = MarketResearchTransitionReceipt.model_validate_json(json.dumps(result))
    await MarketResearchWorkflowRepository(engine).record_runtime_completion(
        workflow_id, receipt
    )


async def recover_market_research_workflows(
    engine: AsyncEngine, application_version: str = DBOS_APPLICATION_VERSION
) -> dict[str, dict[str, object]]:
    """Await and finalize every incomplete workflow owned by this code version."""
    async with engine.connect() as connection:
        workflow_ids = list(
            (
                await connection.execute(
                    select(
                        records.market_research_workflow_bindings.c.dbos_workflow_id
                    ).where(
                        records.market_research_workflow_bindings.c.application_version
                        == application_version,
                        records.market_research_workflow_bindings.c.delivery_state.in_(
                            (
                                "PENDING",
                                "STARTED",
                                "BUSINESS_COMMITTED",
                                "RECEIPT_DELIVERED",
                            )
                        ),
                    )
                )
            ).scalars()
        )
    recovered: dict[str, dict[str, object]] = {}
    for workflow_id in workflow_ids:
        handle = await DBOS.retrieve_workflow_async(workflow_id, existing_workflow=True)
        result = await handle.get_result(polling_interval_sec=0.05)
        if not isinstance(result, dict):
            raise TypeError(
                f"DBOS_WORKFLOW_RESULT_INVALID: {workflow_id} returned "
                f"{type(result).__name__}"
            )
        await finalize_market_research_workflow(engine, workflow_id, result)
        recovered[workflow_id] = result
    return recovered
