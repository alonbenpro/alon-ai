"""Transactional commands for immutable L03 product records."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from functools import wraps
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import ValidationError
from pydantic_core import to_jsonable_python
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.records import schema as s
from alon_ai.records.models import (
    ArtifactDispositionReceipt,
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    ArtifactReceipt,
    CommandReceipt,
    CycleReceipt,
    IdeaAcceptanceReceipt,
    MarketResearchTransitionReceipt,
    OperatorCapabilityProfile,
    PivotDecisionReceipt,
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductWorkflow,
    ResearchAttemptReceipt,
    SourceReference,
    VerdictReceipt,
)


def safe_records[**P, R](
    function: Callable[P, Any],
) -> Callable[P, Any]:
    @wraps(function)
    async def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await function(*args, **kwargs)
        except ProductRecordsDenied:
            raise
        except (SQLAlchemyError, ValidationError, ValueError, TypeError):
            pass
        raise ProductRecordsDenied()

    return guarded


def _request_hash(**request: Any) -> str:
    """Fingerprint the complete immutable request; link/source ordering is not semantic."""
    normalized = to_jsonable_python(request)
    for name in ("inputs", "sources"):
        if name in normalized:
            normalized[name].sort(key=lambda item: json.dumps(item, sort_keys=True))
    return sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def market_research_request_hash(
    *,
    experiment_id: UUID,
    cycle_id: UUID,
    accepted_idea: ArtifactInput,
    plan: ArtifactInput,
) -> str:
    """Return the exact hash used by the authoritative transition command."""
    return _request_hash(
        experiment_id=experiment_id,
        cycle_id=cycle_id,
        accepted_idea=accepted_idea,
        plan=plan,
    )


async def _existing(
    connection: AsyncConnection, command_key: UUID, kind: str, request_hash: str
) -> Any:
    row = (
        (
            await connection.execute(
                select(s.commands).where(s.commands.c.command_key == command_key)
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is not None and (row["kind"] != kind or row["request_hash"] != request_hash):
        raise ProductRecordsDenied("COMMAND_CONFLICT")
    return row


async def _complete(
    connection: AsyncConnection,
    *,
    command_key: UUID,
    experiment_id: UUID | None,
    kind: str,
    request_hash: str,
    result_type: str,
    result_id: UUID,
    now: datetime,
) -> UUID:
    command_id = uuid4()
    await connection.execute(
        insert(s.commands).values(
            id=command_id,
            command_key=command_key,
            experiment_id=experiment_id,
            kind=kind,
            request_hash=request_hash,
            result_type=result_type,
            result_id=result_id,
            issued_at=now,
        )
    )
    await connection.execute(
        insert(s.audit).values(
            id=uuid4(),
            command_id=command_id,
            experiment_id=experiment_id,
            kind=kind,
            aggregate_id=result_id,
            created_at=now,
        )
    )
    await connection.execute(
        insert(s.outbox).values(
            id=uuid4(),
            command_id=command_id,
            experiment_id=experiment_id,
            topic="product-record." + kind.lower().replace("_", "-"),
            aggregate_type=result_type,
            aggregate_id=result_id,
            created_at=now,
        )
    )
    return command_id


async def _artifact_receipt(
    connection: AsyncConnection, artifact_id: UUID, command_id: UUID
) -> ArtifactReceipt:
    row = (
        (
            await connection.execute(
                select(s.artifacts).where(s.artifacts.c.id == artifact_id)
            )
        )
        .mappings()
        .one()
    )
    return ArtifactReceipt(
        command_id=command_id,
        result_id=artifact_id,
        artifact_id=artifact_id,
        kind=ArtifactKind(row["kind"]),
        version=row["version"],
        content_hash=row["content_hash"],
    )


class ProductRecordsRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.engine = engine
        self.clock = clock

    @safe_records
    async def register_profile(
        self, profile: OperatorCapabilityProfile, *, command_key: UUID
    ) -> CommandReceipt:
        from alon_ai.records.operators import OperatorRepository

        return await OperatorRepository(self.engine, clock=self.clock).register_profile(
            profile, command_key=command_key
        )

    @safe_records
    async def bind_roots(
        self,
        experiment: ProductExperiment,
        workflow: ProductWorkflow,
        agent: ProductAgent,
        *,
        command_key: UUID,
    ) -> CommandReceipt:
        if workflow.experiment_id != experiment.id or agent.workflow_id != workflow.id:
            raise ProductRecordsDenied("SCOPE")
        async with self.engine.begin() as connection:
            await lock_experiment(connection, experiment.id)
            request_hash = _request_hash(
                experiment=experiment, workflow=workflow, agent=agent
            )
            old = await _existing(connection, command_key, "BIND_ROOTS", request_hash)
            if old:
                if old["result_id"] != experiment.id:
                    raise ProductRecordsDenied("COMMAND_CONFLICT")
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            await connection.execute(
                insert(s.experiments).values(
                    id=experiment.id,
                    operator_profile_id=experiment.operator_profile_id,
                    operator_profile_version=experiment.operator_profile_version,
                    name=experiment.name,
                    created_at=experiment.created_at,
                )
            )
            await connection.execute(
                insert(s.workflows).values(
                    id=workflow.id,
                    experiment_id=workflow.experiment_id,
                    role=workflow.role,
                    created_at=workflow.created_at,
                )
            )
            await connection.execute(
                insert(s.agents).values(
                    id=agent.id,
                    workflow_id=agent.workflow_id,
                    role=agent.role,
                    created_at=agent.created_at,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment.id,
                kind="BIND_ROOTS",
                request_hash=request_hash,
                result_type="EXPERIMENT",
                result_id=experiment.id,
                now=self.clock(),
            )
            return CommandReceipt(command_id=command_id, result_id=experiment.id)

    @safe_records
    async def append_artifact(
        self,
        draft: ArtifactDraft,
        *,
        inputs: Sequence[ArtifactInput] = (),
        sources: Sequence[SourceReference] = (),
        command_key: UUID,
    ) -> ArtifactReceipt:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, draft.experiment_id)
            request_hash = _request_hash(draft=draft, inputs=inputs, sources=sources)
            old = await _existing(
                connection, command_key, "APPEND_ARTIFACT", request_hash
            )
            if old:
                if old["result_id"] != draft.id:
                    raise ProductRecordsDenied("COMMAND_CONFLICT")
                stored = (
                    (
                        await connection.execute(
                            select(s.artifacts).where(s.artifacts.c.id == draft.id)
                        )
                    )
                    .mappings()
                    .one()
                )
                expected = {
                    "logical_id": draft.logical_id,
                    "version": draft.version,
                    "experiment_id": draft.experiment_id,
                    "workflow_id": draft.workflow_id,
                    "agent_id": draft.agent_id,
                    "operation_id": draft.operation_id,
                    "kind": draft.kind,
                    "schema_version": draft.schema_version,
                    "payload": draft.payload,
                    "created_by": draft.created_by,
                    "created_at": draft.created_at,
                }
                if any(stored[key] != value for key, value in expected.items()):
                    raise ProductRecordsDenied("COMMAND_CONFLICT")
                return await _artifact_receipt(connection, draft.id, old["id"])
            await connection.execute(
                insert(s.artifacts).values(
                    id=draft.id,
                    logical_id=draft.logical_id,
                    version=draft.version,
                    experiment_id=draft.experiment_id,
                    workflow_id=draft.workflow_id,
                    agent_id=draft.agent_id,
                    operation_id=draft.operation_id,
                    kind=draft.kind,
                    schema_version=draft.schema_version,
                    payload=draft.payload,
                    created_by=draft.created_by,
                    created_at=draft.created_at,
                )
            )
            for item in inputs:
                await connection.execute(
                    insert(s.artifact_links).values(
                        consumer_id=draft.id,
                        producer_id=item.artifact_id,
                        experiment_id=draft.experiment_id,
                        role=item.role,
                        producer_kind=item.kind,
                        producer_version=item.version,
                        producer_hash=item.content_hash,
                    )
                )
            for source in sources:
                await connection.execute(
                    insert(s.source_refs).values(
                        id=uuid4(),
                        artifact_id=draft.id,
                        experiment_id=draft.experiment_id,
                        **source.model_dump(exclude={"schema_version"}),
                    )
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=draft.experiment_id,
                kind="APPEND_ARTIFACT",
                request_hash=request_hash,
                result_type="ARTIFACT",
                result_id=draft.id,
                now=self.clock(),
            )
            return await _artifact_receipt(connection, draft.id, command_id)

    @safe_records
    async def record_disposition(
        self,
        artifact: ArtifactInput,
        *,
        experiment_id: UUID,
        disposition: Literal["VALIDATED", "ACCEPTED", "REJECTED", "SUPERSEDED"],
        decided_by: UUID,
        validation: ArtifactInput | None = None,
        command_key: UUID,
    ) -> ArtifactDispositionReceipt:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(
                artifact=artifact,
                experiment_id=experiment_id,
                disposition=disposition,
                decided_by=decided_by,
                validation=validation,
            )
            old = await _existing(
                connection, command_key, "RECORD_DISPOSITION", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.artifact_dispositions).where(
                                s.artifact_dispositions.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return ArtifactDispositionReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    artifact_id=row["artifact_id"],
                    disposition=row["disposition"],
                )
            result_id = uuid4()
            await connection.execute(
                insert(s.artifact_dispositions).values(
                    id=result_id,
                    experiment_id=experiment_id,
                    artifact_id=artifact.artifact_id,
                    artifact_kind=artifact.kind,
                    artifact_version=artifact.version,
                    artifact_hash=artifact.content_hash,
                    validation_artifact_id=validation.artifact_id
                    if validation
                    else None,
                    validation_kind=validation.kind if validation else None,
                    validation_version=validation.version if validation else None,
                    validation_hash=validation.content_hash if validation else None,
                    disposition=disposition,
                    decided_by=decided_by,
                    decided_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="RECORD_DISPOSITION",
                request_hash=request_hash,
                result_type="ARTIFACT_DISPOSITION",
                result_id=result_id,
                now=self.clock(),
            )
            return ArtifactDispositionReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                artifact_id=artifact.artifact_id,
                disposition=disposition,
            )

    @safe_records
    async def select_idea_candidate(
        self,
        experiment_id: UUID,
        candidate: ArtifactInput,
        *,
        selected_by: UUID,
        reason: str,
        command_key: UUID,
    ) -> CommandReceipt:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(
                experiment_id=experiment_id,
                candidate=candidate,
                selected_by=selected_by,
                reason=reason,
            )
            old = await _existing(
                connection, command_key, "SELECT_IDEA_CANDIDATE", request_hash
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            artifact = (
                (
                    await connection.execute(
                        select(s.artifacts).where(
                            s.artifacts.c.id == candidate.artifact_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            experiment = (
                (
                    await connection.execute(
                        select(s.experiments).where(s.experiments.c.id == experiment_id)
                    )
                )
                .mappings()
                .one()
            )
            result_id = uuid4()
            await connection.execute(
                insert(s.candidate_selections).values(
                    id=result_id,
                    experiment_id=experiment_id,
                    artifact_id=candidate.artifact_id,
                    artifact_kind=candidate.kind,
                    artifact_version=candidate.version,
                    artifact_hash=candidate.content_hash,
                    workflow_id=artifact["workflow_id"],
                    agent_id=artifact["agent_id"],
                    profile_id=experiment["operator_profile_id"],
                    profile_version=experiment["operator_profile_version"],
                    selected_by=selected_by,
                    reason=reason,
                    created_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="SELECT_IDEA_CANDIDATE",
                request_hash=request_hash,
                result_type="CANDIDATE_SELECTION",
                result_id=result_id,
                now=self.clock(),
            )
            return CommandReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def create_cycle(
        self,
        experiment_id: UUID,
        *,
        seed: ArtifactInput | None = None,
        candidate: ArtifactInput | None = None,
        selection_id: UUID | None = None,
        command_key: UUID,
        parent_cycle_id: UUID | None = None,
    ) -> CycleReceipt:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(
                experiment_id=experiment_id,
                seed=seed,
                candidate=candidate,
                selection_id=selection_id,
                parent_cycle_id=parent_cycle_id,
            )
            old = await _existing(connection, command_key, "CREATE_CYCLE", request_hash)
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.cycles).where(s.cycles.c.id == old["result_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                return CycleReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    experiment_id=row["experiment_id"],
                    ordinal=row["ordinal"],
                )
            if (seed is None) == (candidate is None):
                raise ProductRecordsDenied("EXACT_ORIGIN_REQUIRED")
            origin = seed if seed is not None else candidate
            assert origin is not None
            ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(s.cycles)
                    .where(s.cycles.c.experiment_id == experiment_id)
                )
                or 0
            ) + 1
            result_id = uuid4()
            await connection.execute(
                insert(s.cycles).values(
                    id=result_id,
                    experiment_id=experiment_id,
                    ordinal=ordinal,
                    parent_cycle_id=parent_cycle_id,
                    idea_mode="USER_SEEDED_REFINEMENT"
                    if seed is not None
                    else "SYSTEM_DISCOVERY",
                    selection_id=selection_id,
                    purpose="INITIAL",
                    episode_id=result_id,
                    seed_artifact_id=origin.artifact_id,
                    seed_kind=origin.kind,
                    seed_version=origin.version,
                    seed_hash=origin.content_hash,
                    created_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="CREATE_CYCLE",
                request_hash=request_hash,
                result_type="CYCLE",
                result_id=result_id,
                now=self.clock(),
            )
            return CycleReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                experiment_id=experiment_id,
                ordinal=ordinal,
            )

    @safe_records
    async def accept_idea(
        self,
        cycle_id: UUID,
        idea: ArtifactInput,
        *,
        accepted_by: UUID,
        command_key: UUID,
        pivot_approval_id: UUID | None = None,
    ) -> IdeaAcceptanceReceipt:
        async with self.engine.begin() as connection:
            cycle = (
                (
                    await connection.execute(
                        select(s.cycles).where(s.cycles.c.id == cycle_id)
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, cycle["experiment_id"])
            request_hash = _request_hash(
                cycle_id=cycle_id,
                idea=idea,
                accepted_by=accepted_by,
                pivot_approval_id=pivot_approval_id,
            )
            old = await _existing(connection, command_key, "ACCEPT_IDEA", request_hash)
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.idea_acceptances).where(
                                s.idea_acceptances.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return IdeaAcceptanceReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    cycle_id=row["cycle_id"],
                    artifact_id=row["artifact_id"],
                )
            result_id = uuid4()
            await connection.execute(
                insert(s.idea_acceptances).values(
                    id=result_id,
                    experiment_id=cycle["experiment_id"],
                    cycle_id=cycle_id,
                    artifact_id=idea.artifact_id,
                    artifact_kind=idea.kind,
                    artifact_version=idea.version,
                    artifact_hash=idea.content_hash,
                    pivot_approval_id=pivot_approval_id,
                    accepted_by=accepted_by,
                    accepted_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=cycle["experiment_id"],
                kind="ACCEPT_IDEA",
                request_hash=request_hash,
                result_type="IDEA_ACCEPTANCE",
                result_id=result_id,
                now=self.clock(),
            )
            return IdeaAcceptanceReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                cycle_id=cycle_id,
                artifact_id=idea.artifact_id,
            )

    @safe_records
    async def current_idea(self, cycle_id: UUID) -> IdeaAcceptanceReceipt:
        async with self.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(s.idea_acceptances).where(
                            s.idea_acceptances.c.cycle_id == cycle_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            return IdeaAcceptanceReceipt(
                command_id=UUID(int=0),
                result_id=row["id"],
                id=row["id"],
                cycle_id=row["cycle_id"],
                artifact_id=row["artifact_id"],
            )

    @safe_records
    async def approve_material_pivot(
        self,
        cycle_id: UUID,
        idea: ArtifactInput,
        *,
        approved_by: UUID,
        command_key: UUID,
    ) -> PivotDecisionReceipt:
        async with self.engine.begin() as connection:
            cycle = (
                (
                    await connection.execute(
                        select(s.cycles).where(s.cycles.c.id == cycle_id)
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, cycle["experiment_id"])
            request_hash = _request_hash(
                cycle_id=cycle_id, idea=idea, approved_by=approved_by
            )
            old = await _existing(
                connection, command_key, "APPROVE_MATERIAL_PIVOT", request_hash
            )
            if old:
                return PivotDecisionReceipt(
                    command_id=old["id"],
                    result_id=old["result_id"],
                    id=old["result_id"],
                    cycle_id=cycle_id,
                )
            result_id = uuid4()
            await connection.execute(
                insert(s.pivot_decisions).values(
                    id=result_id,
                    experiment_id=cycle["experiment_id"],
                    cycle_id=cycle_id,
                    artifact_id=idea.artifact_id,
                    artifact_kind=idea.kind,
                    artifact_version=idea.version,
                    artifact_hash=idea.content_hash,
                    approved_by=approved_by,
                    approved_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=cycle["experiment_id"],
                kind="APPROVE_MATERIAL_PIVOT",
                request_hash=request_hash,
                result_type="PIVOT_DECISION",
                result_id=result_id,
                now=self.clock(),
            )
            return PivotDecisionReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                cycle_id=cycle_id,
            )

    @safe_records
    async def start_research_attempt(
        self, cycle_id: UUID, plan: ArtifactInput, *, command_key: UUID
    ) -> ResearchAttemptReceipt:
        async with self.engine.begin() as connection:
            cycle = (
                (
                    await connection.execute(
                        select(s.cycles).where(s.cycles.c.id == cycle_id)
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, cycle["experiment_id"])
            request_hash = _request_hash(cycle_id=cycle_id, plan=plan)
            old = await _existing(
                connection, command_key, "START_RESEARCH_ATTEMPT", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.research_attempts).where(
                                s.research_attempts.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return ResearchAttemptReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    cycle_id=row["cycle_id"],
                    ordinal=row["ordinal"],
                )
            if not await connection.scalar(
                select(s.idea_acceptances.c.id).where(
                    s.idea_acceptances.c.cycle_id == cycle_id
                )
            ):
                raise ProductRecordsDenied("MISSING_ACCEPTED_IDEA")
            ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(s.research_attempts)
                    .where(s.research_attempts.c.cycle_id == cycle_id)
                )
                or 0
            ) + 1
            if ordinal == 1:
                raise ProductRecordsDenied("WORKFLOW_TRANSITION_REQUIRED")
            state = await connection.scalar(
                select(s.cycle_states.c.state).where(
                    s.cycle_states.c.cycle_id == cycle_id,
                    s.cycle_states.c.experiment_id == cycle["experiment_id"],
                )
            )
            if state != "MARKET_RESEARCH":
                raise ProductRecordsDenied("INVALID_STATE")
            result_id = uuid4()
            await connection.execute(
                insert(s.research_attempts).values(
                    id=result_id,
                    experiment_id=cycle["experiment_id"],
                    cycle_id=cycle_id,
                    ordinal=ordinal,
                    plan_artifact_id=plan.artifact_id,
                    plan_kind=plan.kind,
                    plan_version=plan.version,
                    plan_hash=plan.content_hash,
                    created_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=cycle["experiment_id"],
                kind="START_RESEARCH_ATTEMPT",
                request_hash=request_hash,
                result_type="RESEARCH_ATTEMPT",
                result_id=result_id,
                now=self.clock(),
            )
            return ResearchAttemptReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                cycle_id=cycle_id,
                ordinal=ordinal,
            )

    @safe_records
    async def start_market_research(
        self,
        experiment_id: UUID,
        cycle_id: UUID,
        *,
        accepted_idea: ArtifactInput,
        plan: ArtifactInput,
        command_key: UUID,
        runtime_workflow_id: str | None = None,
    ) -> MarketResearchTransitionReceipt:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, experiment_id)
            request_hash = market_research_request_hash(
                experiment_id=experiment_id,
                cycle_id=cycle_id,
                accepted_idea=accepted_idea,
                plan=plan,
            )
            old = await _existing(
                connection, command_key, "START_MARKET_RESEARCH", request_hash
            )
            if runtime_workflow_id is not None:
                binding = (
                    (
                        await connection.execute(
                            select(s.market_research_workflow_bindings)
                            .where(
                                s.market_research_workflow_bindings.c.dbos_workflow_id
                                == runtime_workflow_id,
                                s.market_research_workflow_bindings.c.experiment_id
                                == experiment_id,
                                s.market_research_workflow_bindings.c.cycle_id
                                == cycle_id,
                                s.market_research_workflow_bindings.c.business_command_key
                                == command_key,
                                s.market_research_workflow_bindings.c.request_hash
                                == request_hash,
                            )
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                allowed_states = (
                    {
                        "STARTED",
                        "BUSINESS_COMMITTED",
                        "RECEIPT_DELIVERED",
                        "RUNTIME_COMPLETED",
                    }
                    if old
                    else {"STARTED"}
                )
                if binding is None or binding["delivery_state"] not in allowed_states:
                    raise ProductRecordsDenied("WORKFLOW_NOT_EXECUTABLE")
            if old:
                transition = (
                    (
                        await connection.execute(
                            select(s.cycle_transitions).where(
                                s.cycle_transitions.c.command_id == old["id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                attempt = (
                    (
                        await connection.execute(
                            select(s.research_attempts).where(
                                s.research_attempts.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return MarketResearchTransitionReceipt(
                    command_id=old["id"],
                    result_id=attempt["id"],
                    id=attempt["id"],
                    cycle_id=attempt["cycle_id"],
                    ordinal=attempt["ordinal"],
                    transition_id=transition["id"],
                    state="MARKET_RESEARCH",
                )

            cycle = (
                (
                    await connection.execute(
                        select(s.cycles).where(
                            s.cycles.c.id == cycle_id,
                            s.cycles.c.experiment_id == experiment_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if cycle is None:
                raise ProductRecordsDenied("SCOPE")
            current_cycle_id = await connection.scalar(
                select(s.cycles.c.id)
                .where(s.cycles.c.experiment_id == experiment_id)
                .order_by(s.cycles.c.ordinal.desc())
                .limit(1)
            )
            if current_cycle_id != cycle_id:
                raise ProductRecordsDenied("NON_CURRENT_CYCLE")
            state = (
                (
                    await connection.execute(
                        select(s.cycle_states)
                        .where(
                            s.cycle_states.c.cycle_id == cycle_id,
                            s.cycle_states.c.experiment_id == experiment_id,
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if state["state"] != "IDEA_REFINEMENT":
                raise ProductRecordsDenied("INVALID_STATE")
            acceptance = (
                (
                    await connection.execute(
                        select(s.idea_acceptances).where(
                            s.idea_acceptances.c.cycle_id == cycle_id,
                            s.idea_acceptances.c.experiment_id == experiment_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if acceptance is None:
                raise ProductRecordsDenied("MISSING_ACCEPTED_IDEA")
            if (
                acceptance["artifact_id"] != accepted_idea.artifact_id
                or acceptance["artifact_kind"] != accepted_idea.kind
                or acceptance["artifact_version"] != accepted_idea.version
                or acceptance["artifact_hash"] != accepted_idea.content_hash
            ):
                raise ProductRecordsDenied("STALE_IDEA_LINEAGE")
            idea = (
                (
                    await connection.execute(
                        select(s.artifacts).where(
                            s.artifacts.c.id == accepted_idea.artifact_id,
                            s.artifacts.c.experiment_id == experiment_id,
                        )
                    )
                )
                .mappings()
                .one()
            )
            if await connection.scalar(
                select(s.artifacts.c.id).where(
                    s.artifacts.c.logical_id == idea["logical_id"],
                    s.artifacts.c.version > idea["version"],
                )
            ) or await connection.scalar(
                select(s.artifact_dispositions.c.id).where(
                    s.artifact_dispositions.c.artifact_id == accepted_idea.artifact_id,
                    s.artifact_dispositions.c.disposition == "SUPERSEDED",
                )
            ):
                raise ProductRecordsDenied("STALE_IDEA_LINEAGE")
            attempt_id = uuid4()
            transition_id = uuid4()
            now = self.clock()
            await connection.execute(
                insert(s.research_attempts).values(
                    id=attempt_id,
                    experiment_id=experiment_id,
                    cycle_id=cycle_id,
                    ordinal=1,
                    plan_artifact_id=plan.artifact_id,
                    plan_kind=plan.kind,
                    plan_version=plan.version,
                    plan_hash=plan.content_hash,
                    created_at=now,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="START_MARKET_RESEARCH",
                request_hash=request_hash,
                result_type="RESEARCH_ATTEMPT",
                result_id=attempt_id,
                now=now,
            )
            await connection.execute(
                insert(s.cycle_transitions).values(
                    id=transition_id,
                    experiment_id=experiment_id,
                    cycle_id=cycle_id,
                    ordinal=1,
                    from_state="IDEA_REFINEMENT",
                    to_state="MARKET_RESEARCH",
                    idea_acceptance_id=acceptance["id"],
                    idea_artifact_id=accepted_idea.artifact_id,
                    idea_kind=accepted_idea.kind,
                    idea_version=accepted_idea.version,
                    idea_hash=accepted_idea.content_hash,
                    research_attempt_id=attempt_id,
                    command_id=command_id,
                    created_at=now,
                )
            )
            advanced = await connection.execute(
                update(s.cycle_states)
                .where(
                    s.cycle_states.c.cycle_id == cycle_id,
                    s.cycle_states.c.experiment_id == experiment_id,
                    s.cycle_states.c.state == "IDEA_REFINEMENT",
                    s.cycle_states.c.transition_ordinal == 0,
                )
                .values(
                    state="MARKET_RESEARCH",
                    transition_ordinal=1,
                    last_transition_id=transition_id,
                    updated_at=now,
                )
            )
            if advanced.rowcount != 1:
                raise ProductRecordsDenied("INVALID_STATE")
            return MarketResearchTransitionReceipt(
                command_id=command_id,
                result_id=attempt_id,
                id=attempt_id,
                cycle_id=cycle_id,
                ordinal=1,
                transition_id=transition_id,
                state="MARKET_RESEARCH",
            )

    @safe_records
    async def commit_verdict(
        self,
        attempt_id: UUID,
        *,
        report: ArtifactInput,
        recommendation: ArtifactInput,
        verdict: Literal[
            "PROCEED_TO_OFFER",
            "REFINE_SAME_IDEA",
            "MATERIAL_PIVOT_RECOMMENDED",
            "KILL_IDEA",
            "INCONCLUSIVE",
        ],
        committed_by: UUID,
        command_key: UUID,
    ) -> VerdictReceipt:
        async with self.engine.begin() as connection:
            attempt = (
                (
                    await connection.execute(
                        select(s.research_attempts).where(
                            s.research_attempts.c.id == attempt_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, attempt["experiment_id"])
            request_hash = _request_hash(
                attempt_id=attempt_id,
                report=report,
                recommendation=recommendation,
                verdict=verdict,
                committed_by=committed_by,
            )
            old = await _existing(
                connection, command_key, "COMMIT_VERDICT", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.verdicts).where(
                                s.verdicts.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return VerdictReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    cycle_id=row["cycle_id"],
                    verdict=row["verdict"],
                )
            result_id = uuid4()
            await connection.execute(
                insert(s.verdicts).values(
                    id=result_id,
                    experiment_id=attempt["experiment_id"],
                    cycle_id=attempt["cycle_id"],
                    attempt_id=attempt_id,
                    report_artifact_id=report.artifact_id,
                    report_kind=report.kind,
                    report_version=report.version,
                    report_hash=report.content_hash,
                    recommendation_artifact_id=recommendation.artifact_id,
                    recommendation_kind=recommendation.kind,
                    recommendation_version=recommendation.version,
                    recommendation_hash=recommendation.content_hash,
                    verdict=verdict,
                    committed_by=committed_by,
                    committed_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=attempt["experiment_id"],
                kind="COMMIT_VERDICT",
                request_hash=request_hash,
                result_type="VERDICT",
                result_id=result_id,
                now=self.clock(),
            )
            return VerdictReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                cycle_id=attempt["cycle_id"],
                verdict=verdict,
            )

    async def return_to_refinement(
        self,
        verdict_id: UUID,
        *,
        feedback: ArtifactInput,
        command_key: UUID,
    ) -> CycleReceipt:
        async with self.engine.connect() as connection:
            verdict = await connection.scalar(
                select(s.verdicts.c.verdict).where(s.verdicts.c.id == verdict_id)
            )
        kind = (
            "MATERIAL_PIVOT"
            if verdict == "MATERIAL_PIVOT_RECOMMENDED"
            else "SAME_INTENT"
        )
        return await self.return_to_research(
            verdict_id, kind=kind, feedback=feedback, command_key=command_key
        )

    @safe_records
    async def return_to_research(
        self,
        verdict_id: UUID,
        *,
        kind: str,
        feedback: ArtifactInput,
        offer_input_bundle_id: UUID | None = None,
        command_key: UUID,
    ) -> CycleReceipt:
        async with self.engine.begin() as connection:
            verdict = (
                (
                    await connection.execute(
                        select(s.verdicts).where(s.verdicts.c.id == verdict_id)
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, verdict["experiment_id"])
            request_hash = _request_hash(
                verdict_id=verdict_id,
                kind=kind,
                feedback=feedback,
                offer_input_bundle_id=offer_input_bundle_id,
            )
            old = await _existing(
                connection, command_key, "RETURN_TO_RESEARCH", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.cycles).where(s.cycles.c.id == old["result_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                return CycleReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    experiment_id=row["experiment_id"],
                    ordinal=row["ordinal"],
                )
            ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(s.cycles)
                    .where(s.cycles.c.experiment_id == verdict["experiment_id"])
                )
                or 0
            ) + 1
            result_id = uuid4()
            parent = (
                (
                    await connection.execute(
                        select(s.cycles).where(s.cycles.c.id == verdict["cycle_id"])
                    )
                )
                .mappings()
                .one()
            )
            idea = (
                (
                    await connection.execute(
                        select(s.idea_acceptances).where(
                            s.idea_acceptances.c.cycle_id == parent["id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            root = (
                (
                    await connection.execute(
                        select(s.cycles).where(
                            s.cycles.c.experiment_id == verdict["experiment_id"],
                            s.cycles.c.ordinal == 1,
                        )
                    )
                )
                .mappings()
                .one()
            )
            if kind == "SAME_INTENT":
                scope_id = (
                    parent["seed_artifact_id"]
                    if parent["idea_mode"] == "USER_SEEDED_REFINEMENT"
                    else await connection.scalar(
                        select(s.idea_acceptances.c.artifact_id).where(
                            s.idea_acceptances.c.cycle_id == root["id"]
                        )
                    )
                )
            elif kind == "OFFER_GAP":
                scope_id = idea["artifact_id"]
            else:
                scope_id = parent["episode_id"]
            return_ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(s.returns)
                    .where(
                        s.returns.c.experiment_id == verdict["experiment_id"],
                        s.returns.c.kind == kind,
                        s.returns.c.applicable_scope_id == scope_id,
                    )
                )
                or 0
            ) + 1
            purposes = {
                "SAME_INTENT": "SAME_INTENT_RETURN",
                "MATERIAL_PIVOT": "MATERIAL_PIVOT_RETURN",
                "INCONCLUSIVE_SUPPLEMENT": "INCONCLUSIVE_SUPPLEMENT",
                "OFFER_GAP": "OFFER_GAP_RETURN",
            }
            if kind not in purposes:
                raise ProductRecordsDenied("RETURN_KIND")
            await connection.execute(
                insert(s.cycles).values(
                    id=result_id,
                    experiment_id=verdict["experiment_id"],
                    ordinal=ordinal,
                    parent_cycle_id=verdict["cycle_id"],
                    idea_mode=parent["idea_mode"],
                    selection_id=parent["selection_id"],
                    purpose=purposes[kind],
                    episode_id=parent["episode_id"],
                    seed_artifact_id=parent["seed_artifact_id"],
                    seed_kind=parent["seed_kind"],
                    seed_version=parent["seed_version"],
                    seed_hash=parent["seed_hash"],
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(s.returns).values(
                    id=uuid4(),
                    experiment_id=verdict["experiment_id"],
                    from_cycle_id=verdict["cycle_id"],
                    verdict_id=verdict_id,
                    to_cycle_id=result_id,
                    ordinal=return_ordinal,
                    kind=kind,
                    applicable_scope_id=scope_id,
                    idea_artifact_id=idea["artifact_id"],
                    offer_input_bundle_id=offer_input_bundle_id,
                    feedback_artifact_id=feedback.artifact_id,
                    feedback_kind=feedback.kind,
                    feedback_version=feedback.version,
                    feedback_hash=feedback.content_hash,
                    created_at=self.clock(),
                )
            )
            if kind in {"INCONCLUSIVE_SUPPLEMENT", "OFFER_GAP"}:
                await connection.execute(
                    insert(s.idea_acceptances).values(
                        id=uuid4(),
                        experiment_id=verdict["experiment_id"],
                        cycle_id=result_id,
                        artifact_id=idea["artifact_id"],
                        artifact_kind=idea["artifact_kind"],
                        artifact_version=idea["artifact_version"],
                        artifact_hash=idea["artifact_hash"],
                        accepted_by=idea["accepted_by"],
                        accepted_at=self.clock(),
                    )
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=verdict["experiment_id"],
                kind="RETURN_TO_RESEARCH",
                request_hash=request_hash,
                result_type="CYCLE",
                result_id=result_id,
                now=self.clock(),
            )
            return CycleReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                experiment_id=verdict["experiment_id"],
                ordinal=ordinal,
            )
