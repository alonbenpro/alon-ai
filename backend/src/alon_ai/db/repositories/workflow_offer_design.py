from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.db.repositories.accounting import lock_experiment
from alon_ai.db.tables import records
from alon_ai.db.tables import records_offer as offers
from alon_ai.services.schemas.records import CommandReceipt, ProductRecordsDenied
from alon_ai.workflows.schemas.offer_design import (
    OFFER_DESIGN_WORKFLOW_CONTRACT_VERSION,
    OfferDesignDecisionWorkflowRequest,
    OfferDesignStartWorkflowRequest,
    OfferDesignWorkflowBinding,
    OfferIdeaRefinementWorkflowRequest,
    OfferTargetedResearchWorkflowRequest,
    offer_design_decision_workflow_id,
    offer_design_start_workflow_id,
    offer_idea_refinement_workflow_id,
)
from alon_ai.workflows.schemas.runtime import (
    DBOS_APPLICATION_VERSION,
)


class OfferDesignWorkflowRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def _context(
        self, *, run_id: UUID | None, verdict_id: UUID | None
    ) -> tuple[UUID, UUID, UUID, UUID | None]:
        async with self.engine.connect() as connection:
            if run_id is not None:
                run = (
                    (
                        await connection.execute(
                            select(offers.offer_design_runs).where(
                                offers.offer_design_runs.c.id == run_id
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return (
                    run["experiment_id"],
                    run["cycle_id"],
                    run["verdict_id"],
                    run["id"],
                )
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == verdict_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            return verdict["experiment_id"], verdict["cycle_id"], verdict["id"], None

    async def bind(
        self,
        request: OfferDesignStartWorkflowRequest
        | OfferDesignDecisionWorkflowRequest
        | OfferTargetedResearchWorkflowRequest
        | OfferIdeaRefinementWorkflowRequest,
        *,
        application_version: str,
    ) -> OfferDesignWorkflowBinding:
        if isinstance(request, OfferDesignStartWorkflowRequest):
            kind: Literal["START", "DECISION", "IDEA_REFINEMENT_RETURN"] = "START"
            experiment_id, cycle_id, verdict_id, run_id = await self._context(
                run_id=None, verdict_id=request.request.verdict_id
            )
            workflow_id = offer_design_start_workflow_id(
                verdict_id, request.command_key
            )
        elif isinstance(
            request,
            OfferDesignDecisionWorkflowRequest | OfferTargetedResearchWorkflowRequest,
        ):
            kind = "DECISION"
            experiment_id, cycle_id, verdict_id, run_id = await self._context(
                run_id=request.request.run_id, verdict_id=None
            )
            if run_id is None:
                raise ProductRecordsDenied("WORKFLOW_BINDING_CONTEXT")
            workflow_id = offer_design_decision_workflow_id(run_id, request.command_key)
        else:
            kind = "IDEA_REFINEMENT_RETURN"
            experiment_id, cycle_id, verdict_id, run_id = await self._context(
                run_id=request.request.run_id, verdict_id=None
            )
            workflow_id = offer_idea_refinement_workflow_id(
                request.request.decision_id, request.command_key
            )
        payload = request.model_dump(mode="json", exclude_computed_fields=True)
        expected = {
            "dbos_workflow_id": workflow_id,
            "application_version": application_version,
            "contract_version": OFFER_DESIGN_WORKFLOW_CONTRACT_VERSION,
            "operation_kind": kind,
            "request_hash": request.request_hash,
            "business_command_key": request.command_key,
            "experiment_id": experiment_id,
            "cycle_id": cycle_id,
            "verdict_id": verdict_id,
            "run_id": run_id,
        }
        async with self.engine.begin() as connection:
            await lock_experiment(connection, experiment_id)
            current = (
                (
                    await connection.execute(
                        select(offers.offer_design_workflow_bindings)
                        .where(
                            or_(
                                offers.offer_design_workflow_bindings.c.dbos_workflow_id
                                == workflow_id,
                                offers.offer_design_workflow_bindings.c.business_command_key
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
                    raise ProductRecordsDenied("WORKFLOW_BINDING_CONFLICT")
                return OfferDesignWorkflowBinding(
                    **expected, delivery_state=current["delivery_state"]
                )
            now = datetime.now(UTC)
            await connection.execute(
                insert(offers.offer_design_workflow_bindings).values(
                    **expected,
                    request_payload=payload,
                    command_id=None,
                    result_id=None,
                    delivery_state="PENDING",
                    cancellation_outcome=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        return OfferDesignWorkflowBinding(**expected, delivery_state="PENDING")

    async def _locked(self, connection: AsyncConnection, workflow_id: str):
        experiment_id = await connection.scalar(
            select(offers.offer_design_workflow_bindings.c.experiment_id).where(
                offers.offer_design_workflow_bindings.c.dbos_workflow_id == workflow_id
            )
        )
        if experiment_id is None:
            raise ProductRecordsDenied("WORKFLOW_BINDING_MISSING")
        await lock_experiment(connection, experiment_id)
        return (
            (
                await connection.execute(
                    select(offers.offer_design_workflow_bindings)
                    .where(
                        offers.offer_design_workflow_bindings.c.dbos_workflow_id
                        == workflow_id
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one()
        )

    async def start(
        self, request, *, application_version: str
    ) -> OfferDesignWorkflowBinding:
        binding = await self.bind(request, application_version=application_version)
        async with self.engine.begin() as connection:
            current = await self._locked(connection, binding.dbos_workflow_id)
            if current["delivery_state"] == "PENDING":
                await connection.execute(
                    update(offers.offer_design_workflow_bindings)
                    .where(
                        offers.offer_design_workflow_bindings.c.dbos_workflow_id
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
                or current["contract_version"] != OFFER_DESIGN_WORKFLOW_CONTRACT_VERSION
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
                update(offers.offer_design_workflow_bindings)
                .where(
                    offers.offer_design_workflow_bindings.c.dbos_workflow_id
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
        self, workflow_id: str, receipt: CommandReceipt, state: str
    ) -> None:
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            expected = (
                "BUSINESS_COMMITTED"
                if state == "RECEIPT_DELIVERED"
                else "RECEIPT_DELIVERED"
            )
            if current["delivery_state"] == state:
                return
            if (
                current["delivery_state"] != expected
                or current["command_id"] != receipt.command_id
                or current["result_id"] != receipt.result_id
            ):
                raise ProductRecordsDenied("WORKFLOW_RECEIPT_CONFLICT")
            await connection.execute(
                update(offers.offer_design_workflow_bindings)
                .where(
                    offers.offer_design_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(delivery_state=state, updated_at=datetime.now(UTC))
            )

    async def cancel(self, workflow_id: str) -> str:
        """Cancel only when the authoritative business command has not committed."""
        async with self.engine.begin() as connection:
            current = await self._locked(connection, workflow_id)
            command = (
                (
                    await connection.execute(
                        select(records.commands).where(
                            records.commands.c.command_key
                            == current["business_command_key"]
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            now = datetime.now(UTC)
            if command is not None:
                if command["request_hash"] != current["request_hash"]:
                    raise ProductRecordsDenied("WORKFLOW_BINDING_CONFLICT")
                await connection.execute(
                    update(offers.offer_design_workflow_bindings)
                    .where(
                        offers.offer_design_workflow_bindings.c.dbos_workflow_id
                        == workflow_id
                    )
                    .values(
                        command_id=command["id"],
                        result_id=command["result_id"],
                        delivery_state="BUSINESS_COMMITTED",
                        cancellation_outcome="INEFFECTIVE_ALREADY_COMMITTED",
                        updated_at=now,
                    )
                )
                return "INEFFECTIVE_ALREADY_COMMITTED"
            if current["delivery_state"] in {"PENDING", "STARTED"}:
                await connection.execute(
                    update(offers.offer_design_workflow_bindings)
                    .where(
                        offers.offer_design_workflow_bindings.c.dbos_workflow_id
                        == workflow_id
                    )
                    .values(
                        delivery_state="CANCELLED",
                        cancellation_outcome="EFFECTIVE",
                        updated_at=now,
                    )
                )
                return "EFFECTIVE"
            await connection.execute(
                update(offers.offer_design_workflow_bindings)
                .where(
                    offers.offer_design_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
                .values(
                    cancellation_outcome="INEFFECTIVE_ALREADY_COMMITTED",
                    updated_at=now,
                )
            )
            return "INEFFECTIVE_ALREADY_COMMITTED"


async def assert_offer_design_compatible_application_version(
    engine: AsyncEngine, application_version: str
) -> None:
    async with engine.connect() as connection:
        incompatible = (
            await connection.execute(
                select(offers.offer_design_workflow_bindings.c.dbos_workflow_id).where(
                    (
                        offers.offer_design_workflow_bindings.c.application_version
                        != application_version
                    )
                    | (
                        offers.offer_design_workflow_bindings.c.contract_version
                        != OFFER_DESIGN_WORKFLOW_CONTRACT_VERSION
                    ),
                    offers.offer_design_workflow_bindings.c.delivery_state.in_(
                        (
                            "PENDING",
                            "STARTED",
                            "BUSINESS_COMMITTED",
                            "RECEIPT_DELIVERED",
                        )
                    ),
                )
            )
        ).scalar_one_or_none()
    if incompatible is not None:
        raise RuntimeError(
            f"DBOS_APPLICATION_VERSION_MISMATCH: workflow {incompatible}"
        )


async def pending_offer_design_workflows(
    engine: AsyncEngine, application_version: str = DBOS_APPLICATION_VERSION
):
    async with engine.connect() as connection:
        rows = list(
            (
                await connection.execute(
                    select(
                        offers.offer_design_workflow_bindings.c.dbos_workflow_id
                    ).where(
                        offers.offer_design_workflow_bindings.c.application_version
                        == application_version,
                        offers.offer_design_workflow_bindings.c.contract_version
                        == OFFER_DESIGN_WORKFLOW_CONTRACT_VERSION,
                        offers.offer_design_workflow_bindings.c.delivery_state.in_(
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
    return rows
