from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.db.repositories.accounting import lock_experiment
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables import records, supply
from alon_ai.policies.campaign_supply import (
    SupplyDenied,
)
from alon_ai.workflows.schemas.campaign_supply import (
    SUPPLY_WORKFLOW_CONTRACT_VERSION,
    CampaignSupplyNextAction,
    CampaignSupplyWorkflowBinding,
    CampaignSupplyWorkflowRequest,
    campaign_supply_workflow_id,
)
from alon_ai.workflows.schemas.runtime import (
    DBOS_APPLICATION_VERSION,
)


class CampaignSupplyWorkflowRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.engine = engine
        self.clock = clock

    async def bind(
        self, request: CampaignSupplyWorkflowRequest, *, application_version: str
    ) -> CampaignSupplyWorkflowBinding:
        workflow_id = campaign_supply_workflow_id(request)
        expected = {
            "dbos_workflow_id": workflow_id,
            "application_version": application_version,
            "contract_version": SUPPLY_WORKFLOW_CONTRACT_VERSION,
            "operation_kind": request.operation_kind,
            "experiment_id": request.experiment_id,
            "batch_id": request.batch_id,
            "candidate_id": request.candidate_id,
            "subject_id": request.subject_id,
            "request_hash": request.request_hash,
            "business_command_key": request.command_key,
        }
        payload = request.model_dump(mode="json", exclude_computed_fields=True)
        async with self.engine.begin() as connection:
            await lock_experiment(connection, request.experiment_id)
            if request.batch_id is not None and not await connection.scalar(
                select(supply.batches.c.id).where(
                    supply.batches.c.id == request.batch_id,
                    supply.batches.c.experiment_id == request.experiment_id,
                )
            ):
                raise SupplyDenied("WORKFLOW_SCOPE")
            if request.candidate_id is not None and not await connection.scalar(
                select(supply.candidates.c.id).where(
                    supply.candidates.c.id == request.candidate_id,
                    supply.candidates.c.experiment_id == request.experiment_id,
                )
            ):
                raise SupplyDenied("WORKFLOW_SCOPE")
            current = (
                (
                    await connection.execute(
                        select(supply.workflow_bindings)
                        .where(
                            or_(
                                supply.workflow_bindings.c.dbos_workflow_id
                                == workflow_id,
                                supply.workflow_bindings.c.business_command_key
                                == request.command_key,
                            )
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .one_or_none()
            )
            if current is not None:
                if (
                    any(current[key] != value for key, value in expected.items())
                    or current["request_payload"] != payload
                ):
                    raise SupplyDenied("WORKFLOW_BINDING_CONFLICT")
                return CampaignSupplyWorkflowBinding(
                    **expected, delivery_state=current["delivery_state"]
                )
            now = datetime.now(UTC)
            await connection.execute(
                insert(supply.workflow_bindings).values(
                    **expected,
                    slot=request.slot,
                    request_payload=payload,
                    command_id=None,
                    result_id=None,
                    delivery_state="PENDING",
                    cancellation_outcome=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        return CampaignSupplyWorkflowBinding(**expected, delivery_state="PENDING")

    async def _locked(self, connection, workflow_id: str):
        experiment_id = await connection.scalar(
            select(supply.workflow_bindings.c.experiment_id).where(
                supply.workflow_bindings.c.dbos_workflow_id == workflow_id
            )
        )
        if experiment_id is None:
            raise SupplyDenied("WORKFLOW_BINDING_MISSING")
        await lock_experiment(connection, experiment_id)
        row = (
            (
                await connection.execute(
                    select(supply.workflow_bindings)
                    .where(supply.workflow_bindings.c.dbos_workflow_id == workflow_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one()
        )
        return row

    async def start(
        self, request: CampaignSupplyWorkflowRequest, *, application_version: str
    ) -> CampaignSupplyWorkflowBinding:
        binding = await self.bind(request, application_version=application_version)
        async with self.engine.begin() as connection:
            row = await self._locked(connection, binding.dbos_workflow_id)
            if row["delivery_state"] == "CANCELLED":
                raise SupplyDenied("WORKFLOW_CANCELLED")
            if (
                row["application_version"] != application_version
                or row["request_hash"] != request.request_hash
            ):
                raise SupplyDenied("WORKFLOW_BINDING_CONFLICT")
            if row["delivery_state"] == "PENDING":
                await connection.execute(
                    update(supply.workflow_bindings)
                    .where(
                        supply.workflow_bindings.c.dbos_workflow_id
                        == binding.dbos_workflow_id
                    )
                    .values(delivery_state="STARTED", updated_at=datetime.now(UTC))
                )
                return binding.model_copy(update={"delivery_state": "STARTED"})
        return binding

    async def require_started(
        self,
        workflow_id: str,
        request_hash: str,
        *,
        application_version: str = DBOS_APPLICATION_VERSION,
    ) -> None:
        async with self.engine.begin() as connection:
            row = await self._locked(connection, workflow_id)
            if (
                row["application_version"] != application_version
                or row["contract_version"] != SUPPLY_WORKFLOW_CONTRACT_VERSION
            ):
                raise RuntimeError("SUPPLY_WORKFLOW_VERSION_MISMATCH")
            if row["request_hash"] != request_hash:
                raise SupplyDenied("WORKFLOW_BINDING_CONFLICT")
            if row["delivery_state"] not in {
                "STARTED",
                "BUSINESS_COMMITTED",
                "RECEIPT_DELIVERED",
                "RUNTIME_COMPLETED",
            }:
                raise SupplyDenied("WORKFLOW_NOT_STARTED")

    async def record_business_commit(self, workflow_id: str) -> dict[str, str]:
        async with self.engine.begin() as connection:
            row = await self._locked(connection, workflow_id)
            command = (
                (
                    await connection.execute(
                        select(records.commands).where(
                            records.commands.c.command_key
                            == row["business_command_key"]
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                command is None
                or command["request_hash"] != row["request_hash"]
                or command["experiment_id"] != row["experiment_id"]
            ):
                raise SupplyDenied("WORKFLOW_COMMAND_MISMATCH")
            if row["delivery_state"] == "CANCELLED":
                raise SupplyDenied("WORKFLOW_CANCELLED")
            if row["delivery_state"] in {"STARTED", "BUSINESS_COMMITTED"}:
                await connection.execute(
                    update(supply.workflow_bindings)
                    .where(supply.workflow_bindings.c.dbos_workflow_id == workflow_id)
                    .values(
                        command_id=command["id"],
                        result_id=command["result_id"],
                        delivery_state="BUSINESS_COMMITTED",
                        updated_at=datetime.now(UTC),
                    )
                )
            return {
                "command_id": str(command["id"]),
                "result_id": str(command["result_id"]),
            }

    async def advance_delivery(
        self, workflow_id: str, receipt: dict[str, str], state: str
    ) -> None:
        if state not in {"RECEIPT_DELIVERED", "RUNTIME_COMPLETED"}:
            raise SupplyDenied("WORKFLOW_DELIVERY_STATE")
        async with self.engine.begin() as connection:
            row = await self._locked(connection, workflow_id)
            if (
                str(row["command_id"]) != receipt["command_id"]
                or str(row["result_id"]) != receipt["result_id"]
            ):
                raise SupplyDenied("WORKFLOW_RECEIPT_MISMATCH")
            if row["delivery_state"] == "RUNTIME_COMPLETED":
                return
            if (
                state == "RUNTIME_COMPLETED"
                and row["delivery_state"] != "RECEIPT_DELIVERED"
            ):
                raise SupplyDenied("WORKFLOW_DELIVERY_STATE")
            await connection.execute(
                update(supply.workflow_bindings)
                .where(supply.workflow_bindings.c.dbos_workflow_id == workflow_id)
                .values(delivery_state=state, updated_at=datetime.now(UTC))
            )

    async def cancel(self, workflow_id: str) -> str:
        async with self.engine.begin() as connection:
            row = await self._locked(connection, workflow_id)
            command = (
                (
                    await connection.execute(
                        select(records.commands).where(
                            records.commands.c.command_key
                            == row["business_command_key"]
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            now = datetime.now(UTC)
            if command is not None:
                if command["request_hash"] != row["request_hash"]:
                    raise SupplyDenied("WORKFLOW_BINDING_CONFLICT")
                await connection.execute(
                    update(supply.workflow_bindings)
                    .where(supply.workflow_bindings.c.dbos_workflow_id == workflow_id)
                    .values(
                        command_id=command["id"],
                        result_id=command["result_id"],
                        delivery_state=(
                            row["delivery_state"]
                            if row["delivery_state"]
                            in {"RECEIPT_DELIVERED", "RUNTIME_COMPLETED"}
                            else "BUSINESS_COMMITTED"
                        ),
                        cancellation_outcome="INEFFECTIVE_ALREADY_COMMITTED",
                        updated_at=now,
                    )
                )
                return "INEFFECTIVE_ALREADY_COMMITTED"
            if row["delivery_state"] in {"PENDING", "STARTED"}:
                await connection.execute(
                    update(supply.workflow_bindings)
                    .where(supply.workflow_bindings.c.dbos_workflow_id == workflow_id)
                    .values(
                        delivery_state="CANCELLED",
                        cancellation_outcome="EFFECTIVE",
                        updated_at=now,
                    )
                )
                return "EFFECTIVE"
            return "INEFFECTIVE_ALREADY_COMMITTED"

    async def next_action(self, experiment_id: UUID) -> CampaignSupplyNextAction:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, experiment_id)
            plan = (
                (
                    await connection.execute(
                        select(supply.plans).where(
                            supply.plans.c.experiment_id == experiment_id
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if plan is None:
                raise SupplyDenied("MISSING_REFERENCE")
            if plan["state"] != "ACTIVE":
                outcome = await connection.scalar(
                    select(supply.outcomes.c.classification).where(
                        supply.outcomes.c.experiment_id == experiment_id
                    )
                )
                return CampaignSupplyNextAction(kind=outcome or plan["state"])
            in_flight_batch = await connection.scalar(
                select(supply.operations.c.batch_id)
                .join(
                    gov.calls,
                    gov.calls.c.operation_id == supply.operations.c.operation_id,
                )
                .where(
                    supply.operations.c.experiment_id == experiment_id,
                    gov.calls.c.state.in_(("RESERVED", "DISPATCHED", "RECONCILING")),
                )
                .limit(1)
            )
            if in_flight_batch is not None:
                return CampaignSupplyNextAction(
                    kind="RECONCILE_IN_FLIGHT", batch_id=in_flight_batch
                )
            if self.clock() >= plan["deadline"]:
                return CampaignSupplyNextAction(kind="DEADLINE_EXHAUSTED")
            exhausted_budget = await connection.scalar(
                select(gov.budget_accounts.c.id)
                .where(
                    gov.budget_accounts.c.scope == "EXPERIMENT",
                    gov.budget_accounts.c.experiment_id == experiment_id,
                    gov.budget_accounts.c.effective_at <= self.clock(),
                    gov.budget_accounts.c.expires_at > self.clock(),
                    or_(
                        gov.budget_accounts.c.frozen.is_(True),
                        gov.budget_accounts.c.reserved + gov.budget_accounts.c.accrued
                        >= gov.budget_accounts.c.limit,
                    ),
                )
                .limit(1)
            )
            if exhausted_budget is not None:
                return CampaignSupplyNextAction(kind="BUDGET_EXHAUSTED")
            batch = (
                (
                    await connection.execute(
                        select(supply.batches)
                        .where(supply.batches.c.experiment_id == experiment_id)
                        .order_by(supply.batches.c.slot.desc())
                        .limit(1)
                    )
                )
                .mappings()
                .one_or_none()
            )
            if batch is None:
                return CampaignSupplyNextAction(kind="BEGIN_BATCH_1")
            if batch["stage"] == "EMAIL_RETRY_READY":
                return CampaignSupplyNextAction(
                    kind="BEGIN_BATCH_2",
                    batch_id=batch["id"],
                    feedback_id=await connection.scalar(
                        select(supply.closures.c.feedback_id).where(
                            supply.closures.c.batch_id == batch["id"],
                            supply.closures.c.gate == "EMAIL",
                        )
                    ),
                )
            if batch["stage"] == "QUALIFICATION_RETRY_READY":
                return CampaignSupplyNextAction(
                    kind="BEGIN_BATCH_3",
                    batch_id=batch["id"],
                    feedback_id=await connection.scalar(
                        select(supply.closures.c.feedback_id).where(
                            supply.closures.c.batch_id == batch["id"],
                            supply.closures.c.gate == "QUALIFICATION",
                        )
                    ),
                )
            if batch["stage"] == "CONTACT":
                discovered = await connection.scalar(
                    select(supply.candidates.c.id)
                    .where(supply.candidates.c.batch_id == batch["id"])
                    .limit(1)
                )
                completion = await connection.scalar(
                    select(supply.discovery_completions.c.id)
                    .where(supply.discovery_completions.c.batch_id == batch["id"])
                    .limit(1)
                )
                if discovered is None and completion is None:
                    return CampaignSupplyNextAction(
                        kind="WAIT_DISCOVERY", batch_id=batch["id"]
                    )
                unresolved = await connection.scalar(
                    select(supply.candidates.c.id)
                    .outerjoin(
                        supply.contacts,
                        supply.contacts.c.candidate_id == supply.candidates.c.id,
                    )
                    .where(
                        supply.candidates.c.batch_id == batch["id"],
                        or_(
                            supply.contacts.c.candidate_id.is_(None),
                            supply.contacts.c.outcome == "SOURCE_FAILURE",
                        ),
                    )
                    .limit(1)
                )
                if unresolved:
                    return CampaignSupplyNextAction(
                        kind="WAIT_CONTACTABILITY", batch_id=batch["id"]
                    )
                return CampaignSupplyNextAction(
                    kind="CLOSE_CONTACTABILITY", batch_id=batch["id"]
                )
            if batch["stage"] == "QUALIFICATION":
                unresolved = await connection.scalar(
                    select(supply.contacts.c.candidate_id)
                    .join(
                        supply.candidates,
                        supply.candidates.c.id == supply.contacts.c.candidate_id,
                    )
                    .outerjoin(
                        supply.current_qualifications,
                        supply.current_qualifications.c.candidate_id
                        == supply.contacts.c.candidate_id,
                    )
                    .where(
                        supply.candidates.c.experiment_id == experiment_id,
                        supply.contacts.c.outcome == "SUPPORTED",
                        supply.current_qualifications.c.candidate_id.is_(None),
                    )
                    .limit(1)
                )
                return CampaignSupplyNextAction(
                    kind="WAIT_QUALIFICATION" if unresolved else "CLOSE_QUALIFICATION",
                    batch_id=batch["id"],
                )
            return CampaignSupplyNextAction(kind="WAIT_PROVIDER", batch_id=batch["id"])


async def assert_campaign_supply_compatible_application_version(
    engine: AsyncEngine, application_version: str
) -> None:
    async with engine.connect() as connection:
        incompatible = await connection.scalar(
            select(supply.workflow_bindings.c.dbos_workflow_id)
            .where(
                supply.workflow_bindings.c.delivery_state.in_(
                    ("PENDING", "STARTED", "BUSINESS_COMMITTED", "RECEIPT_DELIVERED")
                ),
                or_(
                    supply.workflow_bindings.c.application_version
                    != application_version,
                    supply.workflow_bindings.c.contract_version
                    != SUPPLY_WORKFLOW_CONTRACT_VERSION,
                ),
            )
            .limit(1)
        )
    if incompatible:
        raise RuntimeError(f"SUPPLY_WORKFLOW_VERSION_MISMATCH: {incompatible}")


async def pending_campaign_supply_workflows(
    engine: AsyncEngine, application_version: str = DBOS_APPLICATION_VERSION
):
    async with engine.connect() as connection:
        workflow_ids = list(
            (
                await connection.execute(
                    select(supply.workflow_bindings.c.dbos_workflow_id).where(
                        supply.workflow_bindings.c.application_version
                        == application_version,
                        supply.workflow_bindings.c.delivery_state.in_(
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
