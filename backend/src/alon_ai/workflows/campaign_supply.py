"""DBOS delivery of existing PostgreSQL campaign-supply commands."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from dbos import DBOS, SetWorkflowID
from pydantic import AwareDatetime, computed_field, model_validator
from sqlalchemy import insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting import schema as gov
from alon_ai.accounting.repository import lock_experiment
from alon_ai.config import get_settings
from alon_ai.db.engine import create_engine
from alon_ai.policies.campaign_supply import (
    DiscoveryPlan,
    Filter,
    StopReason,
    SupplyDenied,
)
from alon_ai.providers.contracts import StrictDTO
from alon_ai.records import schema as records
from alon_ai.records.repository import _request_hash
from alon_ai.supply import schema as supply
from alon_ai.supply.repository import CampaignSupplyRepository
from alon_ai.workflows.market_research import DBOS_APPLICATION_VERSION

SUPPLY_WORKFLOW_CONTRACT_VERSION = 1
OperationKind = Literal[
    "CREATE",
    "BEGIN_BATCH",
    "ADMIT_CANDIDATE",
    "RESOLVE_CONTACT",
    "CLOSE_CONTACTABILITY",
    "CLOSE_QUALIFICATION",
    "STOP",
]


class CampaignSupplyWorkflowRequest(StrictDTO):
    operation_kind: OperationKind
    experiment_id: UUID
    command_key: UUID
    batch_id: UUID | None = None
    candidate_id: UUID | None = None
    slot: int | None = None
    plan: DiscoveryPlan | None = None
    allowed: tuple[Filter, ...] = ()
    verification_policy_id: UUID | None = None
    deadline: AwareDatetime | None = None
    feedback_id: UUID | None = None
    identity_id: UUID | None = None
    clearance_id: UUID | None = None
    observations: tuple[Filter, ...] = ()
    source_id: UUID | None = None
    verification_id: UUID | None = None
    reason: StopReason | None = None

    @model_validator(mode="after")
    def valid_shape(self):
        required = {
            "CREATE": (
                self.plan,
                self.allowed,
                self.verification_policy_id,
                self.deadline,
            ),
            "BEGIN_BATCH": (self.slot, self.plan),
            "ADMIT_CANDIDATE": (self.batch_id, self.identity_id, self.clearance_id),
            "RESOLVE_CONTACT": (self.candidate_id, self.source_id),
            "CLOSE_CONTACTABILITY": (self.batch_id,),
            "CLOSE_QUALIFICATION": (self.batch_id,),
            "STOP": (self.reason,),
        }[self.operation_kind]
        if any(value is None or value == () for value in required):
            raise ValueError("missing campaign-supply operation input")
        if self.operation_kind == "BEGIN_BATCH" and self.slot not in (1, 2, 3):
            raise ValueError("invalid supply batch slot")
        return self

    @property
    def subject_id(self) -> UUID:
        if self.operation_kind == "BEGIN_BATCH":
            return UUID(int=self.slot or 0)
        if self.operation_kind == "ADMIT_CANDIDATE":
            return self.identity_id or UUID(int=0)
        if self.operation_kind == "RESOLVE_CONTACT":
            return self.candidate_id or UUID(int=0)
        if self.operation_kind in {"CLOSE_CONTACTABILITY", "CLOSE_QUALIFICATION"}:
            return self.batch_id or UUID(int=0)
        return self.experiment_id

    @computed_field
    @property
    def request_hash(self) -> str:
        if self.operation_kind == "CREATE":
            return _request_hash(
                experiment_id=self.experiment_id,
                initial_plan=self.plan.model_dump(mode="json") if self.plan else None,
                allowed=[item.model_dump(mode="json") for item in self.allowed],
                verification_policy_id=self.verification_policy_id,
                deadline=self.deadline,
            )
        if self.operation_kind == "BEGIN_BATCH":
            return _request_hash(
                experiment_id=self.experiment_id,
                slot=self.slot,
                plan=self.plan,
                feedback_id=self.feedback_id,
            )
        if self.operation_kind == "ADMIT_CANDIDATE":
            return _request_hash(
                batch_id=self.batch_id,
                identity_id=self.identity_id,
                clearance_id=self.clearance_id,
                observations=self.observations,
            )
        if self.operation_kind == "RESOLVE_CONTACT":
            return _request_hash(
                candidate_id=self.candidate_id,
                source_id=self.source_id,
                verification_id=self.verification_id,
            )
        if self.operation_kind in {"CLOSE_CONTACTABILITY", "CLOSE_QUALIFICATION"}:
            return _request_hash(
                batch_id=self.batch_id,
                gate="EMAIL"
                if self.operation_kind == "CLOSE_CONTACTABILITY"
                else "QUALIFICATION",
            )
        return _request_hash(experiment_id=self.experiment_id, reason=self.reason)


class CampaignSupplyWorkflowBinding(StrictDTO):
    dbos_workflow_id: str
    application_version: str
    contract_version: int
    operation_kind: OperationKind
    experiment_id: UUID
    batch_id: UUID | None
    candidate_id: UUID | None
    subject_id: UUID
    request_hash: str
    business_command_key: UUID
    delivery_state: str


class CampaignSupplyNextAction(StrictDTO):
    kind: str
    batch_id: UUID | None = None
    feedback_id: UUID | None = None


def campaign_supply_workflow_id(request: CampaignSupplyWorkflowRequest) -> str:
    suffix = f":{request.slot}" if request.operation_kind == "BEGIN_BATCH" else ""
    return f"campaign-supply:{request.experiment_id}:{request.operation_kind}:{request.subject_id}{suffix}:{request.command_key}"


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

    async def require_started(self, workflow_id: str, request_hash: str) -> None:
        async with self.engine.begin() as connection:
            row = await self._locked(connection, workflow_id)
            if (
                row["application_version"] != DBOS.application_version
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
    request = CampaignSupplyWorkflowRequest.model_validate_json(payload_json)
    engine = create_engine(get_settings())
    try:
        runtime = CampaignSupplyWorkflowRepository(engine)
        await runtime.require_started(workflow_id, request.request_hash)
        await _test_barrier("before-business")
        await runtime.require_started(workflow_id, request.request_hash)
        repository = CampaignSupplyRepository(engine)
        if request.operation_kind == "CREATE":
            assert request.plan and request.verification_policy_id and request.deadline
            await repository.create(
                request.experiment_id,
                request.plan,
                request.allowed,
                request.verification_policy_id,
                request.deadline,
                command_key=request.command_key,
                workflow_id=workflow_id,
            )
        elif request.operation_kind == "BEGIN_BATCH":
            assert request.slot and request.plan
            await repository.begin_batch(
                request.experiment_id,
                request.slot,
                request.plan,
                request.command_key,
                request.feedback_id,
                workflow_id=workflow_id,
            )
        elif request.operation_kind == "ADMIT_CANDIDATE":
            assert request.batch_id and request.identity_id and request.clearance_id
            await repository.admit_candidate(
                request.batch_id,
                request.identity_id,
                request.clearance_id,
                request.command_key,
                observations=request.observations,
                workflow_id=workflow_id,
            )
        elif request.operation_kind == "RESOLVE_CONTACT":
            assert request.candidate_id and request.source_id
            await repository.resolve_contact(
                request.candidate_id,
                request.source_id,
                request.verification_id,
                command_key=request.command_key,
                workflow_id=workflow_id,
            )
        elif request.operation_kind == "CLOSE_CONTACTABILITY":
            assert request.batch_id
            await repository.close_contactability(
                request.batch_id, request.command_key, workflow_id=workflow_id
            )
        elif request.operation_kind == "CLOSE_QUALIFICATION":
            assert request.batch_id
            await repository.close_qualification(
                request.batch_id, request.command_key, workflow_id=workflow_id
            )
        else:
            assert request.reason
            await repository.stop(
                request.experiment_id,
                request.reason,
                request.command_key,
                workflow_id=workflow_id,
            )
        await _test_barrier("after-business")
        receipt = await runtime.record_business_commit(workflow_id)
        await _test_barrier("after-binding-commit")
        return json.dumps(receipt, sort_keys=True)
    finally:
        await engine.dispose()


@DBOS.step(name="deliver_campaign_supply_receipt", retries_allowed=False)
async def _delivery_step(workflow_id: str, receipt_json: str) -> None:
    engine = create_engine(get_settings())
    try:
        await CampaignSupplyWorkflowRepository(engine).advance_delivery(
            workflow_id, json.loads(receipt_json), "RECEIPT_DELIVERED"
        )
    finally:
        await engine.dispose()


@DBOS.workflow(name="campaign_supply_command")
async def campaign_supply_command_workflow(
    payload_json: str, workflow_id: str
) -> dict[str, str]:
    receipt_json = await _business_step(payload_json, workflow_id)
    await _delivery_step(workflow_id, receipt_json)
    return json.loads(receipt_json)


async def start_campaign_supply_workflow(
    engine: AsyncEngine,
    request: CampaignSupplyWorkflowRequest,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
):
    binding = await CampaignSupplyWorkflowRepository(engine).start(
        request, application_version=application_version
    )
    with SetWorkflowID(binding.dbos_workflow_id):
        return await DBOS.start_workflow_async(
            campaign_supply_command_workflow,
            request.model_dump_json(exclude_computed_fields=True),
            binding.dbos_workflow_id,
        )


async def finalize_campaign_supply_workflow(
    engine: AsyncEngine, workflow_id: str, receipt: dict[str, str]
) -> None:
    await CampaignSupplyWorkflowRepository(engine).advance_delivery(
        workflow_id, receipt, "RUNTIME_COMPLETED"
    )


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


async def recover_campaign_supply_workflows(
    engine: AsyncEngine, application_version: str = DBOS_APPLICATION_VERSION
) -> dict[str, dict[str, str]]:
    await assert_campaign_supply_compatible_application_version(
        engine, application_version
    )
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
