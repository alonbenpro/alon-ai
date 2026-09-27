from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.db.repositories.accounting import lock_experiment
from alon_ai.db.tables import records
from alon_ai.services.schemas.records import (
    CommandReceipt,
    MarketResearchTransitionReceipt,
    ProductRecordsDenied,
)
from alon_ai.workflows.schemas.market_research import (
    DECISION_WORKFLOW_CONTRACT_VERSION,
    TRANSITION_KIND,
    InconclusiveSupplementWorkflowRequest,
    MarketResearchDecisionWorkflowBinding,
    MarketResearchOutcomeWorkflowRequest,
    MarketResearchWorkflowBinding,
    MarketResearchWorkflowRequest,
    MaterialPivotDecisionWorkflowRequest,
    inconclusive_supplement_workflow_id,
    market_research_outcome_workflow_id,
    market_research_workflow_id,
    material_pivot_decision_workflow_id,
)
from alon_ai.workflows.schemas.runtime import (
    DBOS_APPLICATION_VERSION,
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


class MarketResearchDecisionWorkflowRepository:
    """Durable runtime binding for verdict commands."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def bind_outcome(
        self,
        request: MarketResearchOutcomeWorkflowRequest,
        *,
        application_version: str,
    ) -> MarketResearchDecisionWorkflowBinding:
        workflow_id = market_research_outcome_workflow_id(
            request.attempt_id, request.command_key
        )
        payload = request.model_dump(mode="json", exclude_computed_fields=True)
        expected = {
            "dbos_workflow_id": workflow_id,
            "application_version": application_version,
            "contract_version": DECISION_WORKFLOW_CONTRACT_VERSION,
            "operation_kind": "OUTCOME",
            "operation_id": request.attempt_id,
            "business_command_key": request.command_key,
            "request_hash": request.request_hash,
            "request_payload": payload,
            "experiment_id": request.experiment_id,
            "cycle_id": request.cycle_id,
        }
        async with self.engine.begin() as connection:
            await lock_experiment(connection, request.experiment_id)
            existing = (
                (
                    await connection.execute(
                        select(
                            records.market_research_decision_workflow_bindings
                        ).where(
                            or_(
                                records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                                == workflow_id,
                                records.market_research_decision_workflow_bindings.c.business_command_key
                                == request.command_key,
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
                return MarketResearchDecisionWorkflowBinding.model_validate(
                    {**expected, "delivery_state": existing["delivery_state"]}
                )
            now = datetime.now(UTC)
            await connection.execute(
                insert(records.market_research_decision_workflow_bindings).values(
                    **expected,
                    command_id=None,
                    result_id=None,
                    delivery_state="PENDING",
                    created_at=now,
                    updated_at=now,
                )
            )
            return MarketResearchDecisionWorkflowBinding.model_validate(
                {**expected, "delivery_state": "PENDING"}
            )

    async def _bind_values(
        self, expected: dict[str, object]
    ) -> MarketResearchDecisionWorkflowBinding:
        workflow_id = str(expected["dbos_workflow_id"])
        command_key = expected["business_command_key"]
        experiment_id = expected["experiment_id"]
        assert isinstance(command_key, UUID)
        assert isinstance(experiment_id, UUID)
        async with self.engine.begin() as connection:
            await lock_experiment(connection, experiment_id)
            existing = (
                (
                    await connection.execute(
                        select(
                            records.market_research_decision_workflow_bindings
                        ).where(
                            or_(
                                records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                                == workflow_id,
                                records.market_research_decision_workflow_bindings.c.business_command_key
                                == command_key,
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
                return MarketResearchDecisionWorkflowBinding.model_validate(
                    {**expected, "delivery_state": existing["delivery_state"]}
                )
            now = datetime.now(UTC)
            await connection.execute(
                insert(records.market_research_decision_workflow_bindings).values(
                    **expected,
                    command_id=None,
                    result_id=None,
                    delivery_state="PENDING",
                    created_at=now,
                    updated_at=now,
                )
            )
            return MarketResearchDecisionWorkflowBinding.model_validate(
                {**expected, "delivery_state": "PENDING"}
            )

    async def bind_pivot(
        self,
        request: MaterialPivotDecisionWorkflowRequest,
        *,
        application_version: str,
    ) -> MarketResearchDecisionWorkflowBinding:
        return await self._bind_values(
            {
                "dbos_workflow_id": material_pivot_decision_workflow_id(
                    request.verdict_id, request.decision_id
                ),
                "application_version": application_version,
                "contract_version": DECISION_WORKFLOW_CONTRACT_VERSION,
                "operation_kind": "PIVOT_DECISION",
                "operation_id": request.verdict_id,
                "business_command_key": request.command_key,
                "request_hash": request.request_hash,
                "request_payload": request.model_dump(
                    mode="json", exclude_computed_fields=True
                ),
                "experiment_id": request.experiment_id,
                "cycle_id": request.cycle_id,
            }
        )

    async def bind_supplement(
        self,
        request: InconclusiveSupplementWorkflowRequest,
        *,
        application_version: str,
    ) -> MarketResearchDecisionWorkflowBinding:
        return await self._bind_values(
            {
                "dbos_workflow_id": inconclusive_supplement_workflow_id(
                    request.verdict_id, request.command_key
                ),
                "application_version": application_version,
                "contract_version": DECISION_WORKFLOW_CONTRACT_VERSION,
                "operation_kind": "INCONCLUSIVE_SUPPLEMENT",
                "operation_id": request.verdict_id,
                "business_command_key": request.command_key,
                "request_hash": request.request_hash,
                "request_payload": request.model_dump(
                    mode="json", exclude_computed_fields=True
                ),
                "experiment_id": request.experiment_id,
                "cycle_id": request.cycle_id,
            }
        )

    async def _locked(self, connection: AsyncConnection, workflow_id: str):
        experiment_id = await connection.scalar(
            select(
                records.market_research_decision_workflow_bindings.c.experiment_id
            ).where(
                records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                == workflow_id
            )
        )
        if experiment_id is None:
            raise ProductRecordsDenied("WORKFLOW_BINDING_MISSING")
        await lock_experiment(connection, experiment_id)
        return (
            (
                await connection.execute(
                    select(records.market_research_decision_workflow_bindings)
                    .where(
                        records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                        == workflow_id
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one()
        )

    async def start_outcome(
        self,
        request: MarketResearchOutcomeWorkflowRequest,
        *,
        application_version: str,
    ) -> MarketResearchDecisionWorkflowBinding:
        binding = await self.bind_outcome(
            request, application_version=application_version
        )
        async with self.engine.begin() as connection:
            current = await self._locked(connection, binding.dbos_workflow_id)
            if current["delivery_state"] == "PENDING":
                await connection.execute(
                    update(records.market_research_decision_workflow_bindings)
                    .where(
                        records.market_research_decision_workflow_bindings.c.dbos_workflow_id
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

    async def _start_bound(
        self, binding: MarketResearchDecisionWorkflowBinding
    ) -> MarketResearchDecisionWorkflowBinding:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, binding.dbos_workflow_id)
            if current["delivery_state"] == "PENDING":
                await connection.execute(
                    update(records.market_research_decision_workflow_bindings)
                    .where(
                        records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                        == binding.dbos_workflow_id
                    )
                    .values(delivery_state="STARTED", updated_at=datetime.now(UTC))
                )
                return binding.model_copy(update={"delivery_state": "STARTED"})
            if current["delivery_state"] in {
                "STARTED",
                "BUSINESS_COMMITTED",
                "RECEIPT_DELIVERED",
                "RUNTIME_COMPLETED",
            }:
                return binding.model_copy(
                    update={"delivery_state": current["delivery_state"]}
                )
            raise ProductRecordsDenied("WORKFLOW_CANCELLED")

    async def start_pivot(
        self,
        request: MaterialPivotDecisionWorkflowRequest,
        *,
        application_version: str,
    ) -> MarketResearchDecisionWorkflowBinding:
        return await self._start_bound(
            await self.bind_pivot(request, application_version=application_version)
        )

    async def start_supplement(
        self,
        request: InconclusiveSupplementWorkflowRequest,
        *,
        application_version: str,
    ) -> MarketResearchDecisionWorkflowBinding:
        return await self._start_bound(
            await self.bind_supplement(request, application_version=application_version)
        )

    async def require_started(
        self, workflow_id: str, *, application_version: str, request_hash: str
    ) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if (
                current["application_version"] != application_version
                or current["contract_version"] != DECISION_WORKFLOW_CONTRACT_VERSION
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
        self, workflow_id: str, receipt: CommandReceipt
    ) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if current["delivery_state"] in {
                "BUSINESS_COMMITTED",
                "RECEIPT_DELIVERED",
                "RUNTIME_COMPLETED",
            }:
                if (
                    current["command_id"] != receipt.command_id
                    or current["result_id"] != receipt.result_id
                ):
                    raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
                return
            if current["delivery_state"] != "STARTED":
                raise ProductRecordsDenied("WORKFLOW_NOT_EXECUTABLE")
            await connection.execute(
                update(records.market_research_decision_workflow_bindings)
                .where(
                    records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(
                    command_id=receipt.command_id,
                    result_id=receipt.result_id,
                    delivery_state="BUSINESS_COMMITTED",
                    updated_at=datetime.now(UTC),
                )
            )

    async def advance_delivery(
        self,
        workflow_id: str,
        receipt: CommandReceipt,
        *,
        expected: str,
        target: str,
    ) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if current["delivery_state"] == target:
                if (
                    current["command_id"] != receipt.command_id
                    or current["result_id"] != receipt.result_id
                ):
                    raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
                return
            if (
                current["delivery_state"] != expected
                or current["command_id"] != receipt.command_id
                or current["result_id"] != receipt.result_id
            ):
                raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
            await connection.execute(
                update(records.market_research_decision_workflow_bindings)
                .where(
                    records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(delivery_state=target, updated_at=datetime.now(UTC))
            )

    async def cancel(self, workflow_id: str) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if current["delivery_state"] == "CANCELLED":
                return
            if current["delivery_state"] not in {"PENDING", "STARTED"}:
                raise ProductRecordsDenied("WORKFLOW_ALREADY_COMMITTED")
            await connection.execute(
                update(records.market_research_decision_workflow_bindings)
                .where(
                    records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(delivery_state="CANCELLED", updated_at=datetime.now(UTC))
            )

    async def record_rejection(self, workflow_id: str, reason: str) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            if current["delivery_state"] == "REJECTED":
                if current["failure_code"] != reason:
                    raise ProductRecordsDenied("WORKFLOW_REJECTION_CONFLICT")
                return
            if current["delivery_state"] != "STARTED":
                raise ProductRecordsDenied("WORKFLOW_ALREADY_COMMITTED")
            await connection.execute(
                update(records.market_research_decision_workflow_bindings)
                .where(
                    records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(
                    delivery_state="REJECTED",
                    failure_code=reason,
                    updated_at=datetime.now(UTC),
                )
            )


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
        incompatible_decision = (
            (
                await connection.execute(
                    select(
                        records.market_research_decision_workflow_bindings.c.dbos_workflow_id,
                        records.market_research_decision_workflow_bindings.c.application_version,
                        records.market_research_decision_workflow_bindings.c.contract_version,
                    ).where(
                        records.market_research_decision_workflow_bindings.c.delivery_state.in_(
                            (
                                "PENDING",
                                "STARTED",
                                "BUSINESS_COMMITTED",
                                "RECEIPT_DELIVERED",
                            )
                        ),
                        or_(
                            records.market_research_decision_workflow_bindings.c.application_version
                            != application_version,
                            records.market_research_decision_workflow_bindings.c.contract_version
                            != DECISION_WORKFLOW_CONTRACT_VERSION,
                        ),
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
    if incompatible_decision is not None:
        raise RuntimeError(
            "DBOS_APPLICATION_VERSION_MISMATCH: "
            f"workflow {incompatible_decision['dbos_workflow_id']} requires "
            f"{incompatible_decision['application_version']} contract "
            f"{incompatible_decision['contract_version']}, not "
            f"{application_version} contract {DECISION_WORKFLOW_CONTRACT_VERSION}"
        )


async def pending_market_research_workflows(
    engine: AsyncEngine, application_version: str = DBOS_APPLICATION_VERSION
):
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
    return workflow_ids


async def pending_market_research_decision_workflows(
    engine: AsyncEngine, application_version: str = DBOS_APPLICATION_VERSION
):
    async with engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    select(records.market_research_decision_workflow_bindings).where(
                        records.market_research_decision_workflow_bindings.c.application_version
                        == application_version,
                        records.market_research_decision_workflow_bindings.c.contract_version
                        == DECISION_WORKFLOW_CONTRACT_VERSION,
                        records.market_research_decision_workflow_bindings.c.delivery_state.in_(
                            (
                                "PENDING",
                                "STARTED",
                                "BUSINESS_COMMITTED",
                                "RECEIPT_DELIVERED",
                            )
                        ),
                    )
                )
            )
            .mappings()
            .all()
        )
    return rows
