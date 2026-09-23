"""DBOS control-plane bindings for the immutable Offer Design commands."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from dbos import DBOS, SetWorkflowID
from pydantic import computed_field
from sqlalchemy import insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.config import get_settings
from alon_ai.db.engine import create_engine
from alon_ai.providers.contracts import StrictDTO
from alon_ai.records import offer_schema as offers
from alon_ai.records import schema as records
from alon_ai.records.models import CommandReceipt, ProductRecordsDenied
from alon_ai.records.offer_models import (
    OfferDesignDecisionRequest,
    OfferDesignStartRequest,
    OfferIdeaRefinementReturnRequest,
    OfferTargetedResearchReturnRequest,
)
from alon_ai.records.offers import OfferRecordsRepository
from alon_ai.records.repository import _request_hash
from alon_ai.workflows.market_research import DBOS_APPLICATION_VERSION

OFFER_DESIGN_WORKFLOW_CONTRACT_VERSION = 1


def _command_receipt(payload: str | dict[str, object]) -> CommandReceipt:
    value = json.loads(payload) if isinstance(payload, str) else payload
    return CommandReceipt(
        command_id=UUID(str(value["command_id"])),
        result_id=UUID(str(value["result_id"])),
    )


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


class OfferDesignStartWorkflowRequest(StrictDTO):
    request: OfferDesignStartRequest
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return _request_hash(request=self.request)


class OfferDesignDecisionWorkflowRequest(StrictDTO):
    request: OfferDesignDecisionRequest
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return _request_hash(request=self.request)


class OfferTargetedResearchWorkflowRequest(StrictDTO):
    request: OfferTargetedResearchReturnRequest
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return _request_hash(request=self.request)


class OfferIdeaRefinementWorkflowRequest(StrictDTO):
    request: OfferIdeaRefinementReturnRequest
    command_key: UUID

    @computed_field
    @property
    def request_hash(self) -> str:
        return _request_hash(request=self.request)


class OfferDesignWorkflowBinding(StrictDTO):
    dbos_workflow_id: str
    application_version: str
    contract_version: int
    operation_kind: str
    request_hash: str
    business_command_key: UUID
    experiment_id: UUID
    cycle_id: UUID
    verdict_id: UUID
    run_id: UUID | None
    delivery_state: str


def offer_design_start_workflow_id(verdict_id: UUID, command_key: UUID) -> str:
    return f"offer-design-start:{verdict_id}:{command_key}"


def offer_design_decision_workflow_id(run_id: UUID, command_key: UUID) -> str:
    return f"offer-design-decision:{run_id}:{command_key}"


def offer_idea_refinement_workflow_id(decision_id: UUID, command_key: UUID) -> str:
    return f"offer-idea-refinement:{decision_id}:{command_key}"


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


async def _business_step(payload_json: str, workflow_id: str) -> str:
    payload = json.loads(payload_json)
    kind = payload["operation_kind"]
    raw = payload["request"]
    command_key = UUID(payload["command_key"])
    if kind == "START":
        request = OfferDesignStartRequest.model_validate_json(json.dumps(raw))
        wrapper = OfferDesignStartWorkflowRequest(
            request=request, command_key=command_key
        )
    elif kind == "DECISION" and "gap" not in raw:
        request = OfferDesignDecisionRequest.model_validate_json(json.dumps(raw))
        wrapper = OfferDesignDecisionWorkflowRequest(
            request=request, command_key=command_key
        )
    elif kind == "DECISION":
        request = OfferTargetedResearchReturnRequest.model_validate_json(
            json.dumps(raw)
        )
        wrapper = OfferTargetedResearchWorkflowRequest(
            request=request, command_key=command_key
        )
    else:
        request = OfferIdeaRefinementReturnRequest.model_validate_json(json.dumps(raw))
        wrapper = OfferIdeaRefinementWorkflowRequest(
            request=request, command_key=command_key
        )
    engine = create_engine(get_settings())
    try:
        runtime = OfferDesignWorkflowRepository(engine)
        await runtime.require_started(
            workflow_id,
            application_version=DBOS.application_version,
            request_hash=wrapper.request_hash,
        )
        await _at_test_barrier("before-business")
        repository = OfferRecordsRepository(engine)
        if kind == "START":
            receipt = await repository.start_offer_design(
                cast(OfferDesignStartRequest, request),
                command_key=command_key,
                workflow_id=workflow_id,
            )
        elif kind == "DECISION" and isinstance(request, OfferDesignDecisionRequest):
            receipt = await repository.decide_offer_design(
                cast(OfferDesignDecisionRequest, request),
                command_key=command_key,
                workflow_id=workflow_id,
            )
        elif kind == "DECISION":
            receipt = await repository.return_for_targeted_research(
                cast(OfferTargetedResearchReturnRequest, request),
                command_key=command_key,
                workflow_id=workflow_id,
            )
        else:
            receipt = await repository.confirm_offer_idea_refinement(
                cast(OfferIdeaRefinementReturnRequest, request),
                command_key=command_key,
                workflow_id=workflow_id,
            )
        await _at_test_barrier("after-business")
        await runtime.record_business_commit(workflow_id, receipt)
        await _at_test_barrier("after-binding-commit")
        return receipt.model_dump_json()
    finally:
        await engine.dispose()


@DBOS.step(
    name="offer_design_business_command", retries_allowed=False, preemptible=True
)
async def _offer_design_business_step(payload_json: str, workflow_id: str) -> str:
    return await _business_step(payload_json, workflow_id)


@DBOS.step(name="deliver_offer_design_receipt", retries_allowed=False)
async def _deliver_offer_design_receipt(workflow_id: str, receipt_json: str) -> None:
    receipt = _command_receipt(receipt_json)
    engine = create_engine(get_settings())
    try:
        await OfferDesignWorkflowRepository(engine).advance_delivery(
            workflow_id, receipt, "RECEIPT_DELIVERED"
        )
        await _at_test_barrier("after-receipt-delivery")
    finally:
        await engine.dispose()


@DBOS.workflow(name="offer_design_command")
async def offer_design_command_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, object]:
    receipt_json = await _offer_design_business_step(payload_json, workflow_id)
    await _deliver_offer_design_receipt(workflow_id, receipt_json)
    return json.loads(receipt_json)


async def start_offer_design_workflow(
    engine: AsyncEngine, request, *, application_version: str = DBOS_APPLICATION_VERSION
):
    binding = await OfferDesignWorkflowRepository(engine).start(
        request, application_version=application_version
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
    engine: AsyncEngine, workflow_id: str, result: dict[str, object]
) -> None:
    await OfferDesignWorkflowRepository(engine).advance_delivery(
        workflow_id, _command_receipt(result), "RUNTIME_COMPLETED"
    )


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


async def recover_offer_design_workflows(
    engine: AsyncEngine, application_version: str = DBOS_APPLICATION_VERSION
) -> dict[str, dict[str, object]]:
    await assert_offer_design_compatible_application_version(
        engine, application_version
    )
    async with engine.connect() as connection:
        rows = list(
            (
                await connection.execute(
                    select(
                        offers.offer_design_workflow_bindings.c.dbos_workflow_id,
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
    recovered: dict[str, dict[str, object]] = {}
    for workflow_id in rows:
        handle = await DBOS.retrieve_workflow_async(workflow_id, existing_workflow=True)
        result = await handle.get_result(polling_interval_sec=0.05)
        if not isinstance(result, dict):
            raise TypeError(f"DBOS_WORKFLOW_RESULT_INVALID: {workflow_id}")
        await finalize_offer_design_workflow(engine, workflow_id, result)
        recovered[workflow_id] = result
    return recovered
