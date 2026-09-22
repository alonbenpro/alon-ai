"""DBOS control plane for the first L04 business transition."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Literal
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
    CommandReceipt,
    MarketResearchOutcomeReceipt,
    MarketResearchTransitionReceipt,
    MaterialPivotDecisionReceipt,
    ProductRecordsDenied,
    ResearchContinuationReceipt,
    ResearchCycleBudgetInput,
)
from alon_ai.records.repository import (
    ProductRecordsRepository,
    inconclusive_supplement_request_hash,
    market_research_outcome_request_hash,
    market_research_request_hash,
    material_pivot_decision_request_hash,
)

DBOS_APPLICATION_NAME = "alon-ai-worker"
DBOS_APPLICATION_VERSION = "l04-market-research-v1"
DBOS_SYSTEM_SCHEMA = "dbos"
DECISION_WORKFLOW_CONTRACT_VERSION = 1
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


def market_research_outcome_workflow_id(
    attempt_id: UUID, command_key: UUID
) -> str:
    return f"market-research-outcome:{attempt_id}:{command_key}"


def material_pivot_decision_workflow_id(
    verdict_id: UUID, decision_id: UUID
) -> str:
    return f"material-pivot-decision:{verdict_id}:{decision_id}"


def inconclusive_supplement_workflow_id(
    verdict_id: UUID, command_key: UUID
) -> str:
    return f"inconclusive-supplement:{verdict_id}:{command_key}"


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
                        select(records.market_research_decision_workflow_bindings).where(
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
                        select(records.market_research_decision_workflow_bindings).where(
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
            await self.bind_supplement(
                request, application_version=application_version
            )
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


@DBOS.step(
    name="commit_market_research_outcome_business_command",
    retries_allowed=False,
    preemptible=True,
)
async def _commit_market_research_outcome_business_step(
    payload_json: str, workflow_id: str
) -> str:
    request = MarketResearchOutcomeWorkflowRequest.model_validate_json(payload_json)
    engine = create_engine(get_settings())
    try:
        runtime = MarketResearchDecisionWorkflowRepository(engine)
        await runtime.require_started(
            workflow_id,
            application_version=DBOS.application_version,
            request_hash=request.request_hash,
        )
        await _at_test_barrier("before-outcome-business")
        try:
            receipt = await ProductRecordsRepository(
                engine
            ).commit_market_research_outcome(
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
        await _at_test_barrier("after-outcome-business")
        await runtime.record_business_commit(workflow_id, receipt)
        await _at_test_barrier("after-outcome-binding-commit")
        return receipt.model_dump_json()
    finally:
        await engine.dispose()


@DBOS.step(name="deliver_market_research_outcome_receipt", retries_allowed=False)
async def _deliver_market_research_outcome_receipt_step(
    workflow_id: str, receipt_json: str
) -> None:
    engine = create_engine(get_settings())
    try:
        receipt = MarketResearchOutcomeReceipt.model_validate_json(receipt_json)
        await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
            workflow_id,
            receipt,
            expected="BUSINESS_COMMITTED",
            target="RECEIPT_DELIVERED",
        )
        await _at_test_barrier("after-outcome-receipt-delivery")
    finally:
        await engine.dispose()


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
    request = MaterialPivotDecisionWorkflowRequest.model_validate_json(payload_json)
    engine = create_engine(get_settings())
    try:
        runtime = MarketResearchDecisionWorkflowRepository(engine)
        await runtime.require_started(
            workflow_id,
            application_version=DBOS.application_version,
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
    finally:
        await engine.dispose()


@DBOS.step(
    name="start_inconclusive_supplement_business_command",
    retries_allowed=False,
    preemptible=True,
)
async def _start_inconclusive_supplement_business_step(
    payload_json: str, workflow_id: str
) -> str:
    request = InconclusiveSupplementWorkflowRequest.model_validate_json(payload_json)
    engine = create_engine(get_settings())
    try:
        runtime = MarketResearchDecisionWorkflowRepository(engine)
        await runtime.require_started(
            workflow_id,
            application_version=DBOS.application_version,
            request_hash=request.request_hash,
        )
        try:
            receipt = await ProductRecordsRepository(
                engine
            ).start_inconclusive_supplement(
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
    finally:
        await engine.dispose()


@DBOS.step(name="deliver_material_pivot_receipt", retries_allowed=False)
async def _deliver_material_pivot_receipt_step(
    workflow_id: str, receipt_json: str
) -> None:
    engine = create_engine(get_settings())
    try:
        receipt = MaterialPivotDecisionReceipt.model_validate_json(receipt_json)
        await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
            workflow_id,
            receipt,
            expected="BUSINESS_COMMITTED",
            target="RECEIPT_DELIVERED",
        )
    finally:
        await engine.dispose()


@DBOS.step(name="deliver_inconclusive_supplement_receipt", retries_allowed=False)
async def _deliver_inconclusive_supplement_receipt_step(
    workflow_id: str, receipt_json: str
) -> None:
    engine = create_engine(get_settings())
    try:
        receipt = ResearchContinuationReceipt.model_validate_json(receipt_json)
        await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
            workflow_id,
            receipt,
            expected="BUSINESS_COMMITTED",
            target="RECEIPT_DELIVERED",
        )
    finally:
        await engine.dispose()


@DBOS.workflow(name="material_pivot_decision")
async def material_pivot_decision_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, object]:
    receipt_json = await _decide_material_pivot_business_step(
        payload_json, workflow_id
    )
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
    engine: AsyncEngine,
    request: MarketResearchOutcomeWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await MarketResearchDecisionWorkflowRepository(engine).start_outcome(
        request, application_version=application_version
    )
    payload_json = request.model_dump_json(exclude_computed_fields=True)
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            market_research_outcome_workflow,
            payload_json,
            binding.dbos_workflow_id,
        )


async def start_material_pivot_decision_workflow(
    engine: AsyncEngine,
    request: MaterialPivotDecisionWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await MarketResearchDecisionWorkflowRepository(engine).start_pivot(
        request, application_version=application_version
    )
    payload_json = request.model_dump_json(exclude_computed_fields=True)
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            material_pivot_decision_workflow,
            payload_json,
            binding.dbos_workflow_id,
        )


async def start_inconclusive_supplement_workflow(
    engine: AsyncEngine,
    request: InconclusiveSupplementWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await MarketResearchDecisionWorkflowRepository(engine).start_supplement(
        request, application_version=application_version
    )
    payload_json = request.model_dump_json(exclude_computed_fields=True)
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            inconclusive_supplement_workflow,
            payload_json,
            binding.dbos_workflow_id,
        )


async def finalize_market_research_outcome_workflow(
    engine: AsyncEngine, workflow_id: str, result: dict[str, object]
) -> None:
    receipt = MarketResearchOutcomeReceipt.model_validate(result)
    await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
        workflow_id,
        receipt,
        expected="RECEIPT_DELIVERED",
        target="RUNTIME_COMPLETED",
    )


async def finalize_market_research_decision_workflow(
    engine: AsyncEngine, workflow_id: str, result: dict[str, object]
) -> None:
    receipt = CommandReceipt(
        command_id=UUID(str(result["command_id"])),
        result_id=UUID(str(result["result_id"])),
    )
    await MarketResearchDecisionWorkflowRepository(engine).advance_delivery(
        workflow_id,
        receipt,
        expected="RECEIPT_DELIVERED",
        target="RUNTIME_COMPLETED",
    )


async def recover_market_research_decision_workflows(
    engine: AsyncEngine, application_version: str = DBOS_APPLICATION_VERSION
) -> dict[str, dict[str, object]]:
    """Dispatch or retrieve each compatible decision workflow from pinned input."""
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
    recovered: dict[str, dict[str, object]] = {}
    repository = MarketResearchDecisionWorkflowRepository(engine)
    for row in rows:
        operation_kind = row["operation_kind"]
        if operation_kind == "OUTCOME":
            request = MarketResearchOutcomeWorkflowRequest.model_validate_json(
                json.dumps(row["request_payload"])
            )
            binding = await repository.start_outcome(
                request, application_version=application_version
            )
            workflow = market_research_outcome_workflow
        elif operation_kind == "PIVOT_DECISION":
            request = MaterialPivotDecisionWorkflowRequest.model_validate_json(
                json.dumps(row["request_payload"])
            )
            binding = await repository.start_pivot(
                request, application_version=application_version
            )
            workflow = material_pivot_decision_workflow
        elif operation_kind == "INCONCLUSIVE_SUPPLEMENT":
            request = InconclusiveSupplementWorkflowRequest.model_validate_json(
                json.dumps(row["request_payload"])
            )
            binding = await repository.start_supplement(
                request, application_version=application_version
            )
            workflow = inconclusive_supplement_workflow
        else:
            raise RuntimeError(
                "DBOS_WORKFLOW_CONTRACT_UNSUPPORTED: "
                f"{operation_kind} contract {row['contract_version']}"
            )
        payload_json = request.model_dump_json(exclude_computed_fields=True)
        with SetWorkflowID(binding.dbos_workflow_id):
            handle = await DBOS.start_workflow_async(
                workflow,
                payload_json,
                binding.dbos_workflow_id,
            )
        result = await handle.get_result(polling_interval_sec=0.05)
        if not isinstance(result, dict):
            raise TypeError(
                f"DBOS_WORKFLOW_RESULT_INVALID: {binding.dbos_workflow_id} returned "
                f"{type(result).__name__}"
            )
        await finalize_market_research_decision_workflow(
            engine, binding.dbos_workflow_id, result
        )
        recovered[binding.dbos_workflow_id] = result
    return recovered
