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

from alon_ai.accounting import schema as gov
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
    MarketResearchOutcomeReceipt,
    MarketResearchTransitionReceipt,
    MaterialPivotDecisionReceipt,
    OperatorCapabilityProfile,
    PivotDecisionReceipt,
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductWorkflow,
    ResearchAttemptReceipt,
    ResearchContinuationReceipt,
    ResearchCycleBudgetInput,
    SameIntentReturnReceipt,
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


def market_research_outcome_request_hash(
    *,
    attempt_id: UUID,
    report: ArtifactInput,
    recommendation: ArtifactInput,
    verdict: str,
    committed_by: UUID,
    feedback: ArtifactInput | None = None,
    feedback_validation: ArtifactInput | None = None,
    proposed_idea: ArtifactInput | None = None,
    plan: ArtifactInput | None = None,
    budget: ResearchCycleBudgetInput | None = None,
    accepted_by: UUID | None = None,
) -> str:
    return _request_hash(
        attempt_id=attempt_id,
        report=report,
        recommendation=recommendation,
        verdict=verdict,
        committed_by=committed_by,
        feedback=feedback,
        feedback_validation=feedback_validation,
        proposed_idea=proposed_idea,
        plan=plan,
        budget=budget,
        accepted_by=accepted_by,
    )


def material_pivot_decision_request_hash(
    *,
    verdict_id: UUID,
    decision_id: UUID,
    decision: str,
    decided_by: UUID,
    reason_code: str,
    proposed_idea: ArtifactInput | None = None,
    feedback: ArtifactInput | None = None,
    feedback_validation: ArtifactInput | None = None,
    plan: ArtifactInput | None = None,
    budget: ResearchCycleBudgetInput | None = None,
    accepted_by: UUID | None = None,
) -> str:
    return _request_hash(
        verdict_id=verdict_id,
        decision_id=decision_id,
        decision=decision,
        decided_by=decided_by,
        reason_code=reason_code,
        proposed_idea=proposed_idea,
        feedback=feedback,
        feedback_validation=feedback_validation,
        plan=plan,
        budget=budget,
        accepted_by=accepted_by,
    )


def inconclusive_supplement_request_hash(
    *,
    verdict_id: UUID,
    feedback: ArtifactInput,
    feedback_validation: ArtifactInput,
    plan: ArtifactInput,
    budget: ResearchCycleBudgetInput,
    accepted_by: UUID,
) -> str:
    return _request_hash(
        verdict_id=verdict_id,
        feedback=feedback,
        feedback_validation=feedback_validation,
        plan=plan,
        budget=budget,
        accepted_by=accepted_by,
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


async def _continuation_block_reason(
    connection: AsyncConnection, cycle_id: UUID, now: datetime
) -> str | None:
    budget = (
        (
            await connection.execute(
                select(s.research_cycle_budgets).where(
                    s.research_cycle_budgets.c.cycle_id == cycle_id
                )
            )
        )
        .mappings()
        .one_or_none()
    )
    if budget is None:
        return "MISSING_EVIDENCE"
    account = (
        (
            await connection.execute(
                select(gov.budget_accounts).where(
                    gov.budget_accounts.c.id == budget["budget_account_id"]
                )
            )
        )
        .mappings()
        .one()
    )
    if (
        account["frozen"]
        or account["expires_at"] <= now
        or account["reserved"] + account["accrued"] >= account["limit"]
    ):
        return "BUDGET_EXHAUSTED"
    calls = (
        (
            await connection.execute(
                select(gov.calls).where(
                    gov.calls.c.experiment_id == budget["experiment_id"],
                    gov.calls.c.workflow_id == budget["workflow_id"],
                )
            )
        )
        .mappings()
        .all()
    )
    search_results = 0
    captured_pages = 0
    openai_calls = 0
    for call in calls:
        if call["state"] == "RELEASED":
            continue
        if call["state"] != "FINAL":
            return "UNFINALIZED_USAGE"
        usage = (
            (
                await connection.execute(
                    select(gov.usage).where(gov.usage.c.call_id == call["id"])
                )
            )
            .mappings()
            .all()
        )
        superseded = {row["supersedes_id"] for row in usage if row["supersedes_id"]}
        live = [row for row in usage if row["id"] not in superseded]
        if any(row["knowledge"] != "FINAL" for row in live):
            return "UNFINALIZED_USAGE"
        settlement = (
            (
                await connection.execute(
                    select(gov.settlements)
                    .where(gov.settlements.c.call_id == call["id"])
                    .order_by(
                        gov.settlements.c.created_at.desc(),
                        gov.settlements.c.id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if (
            settlement is None
            or settlement["cost"] != call["accrued"]
            or settlement["cost_ils"] != call["accrued_ils"]
        ):
            return "UNFINALIZED_USAGE"
        for row in live:
            quantity = int(row["quantity"] or 0)
            if row["component"] == "SEARCH_RESULT":
                search_results += quantity
            elif row["component"] == "CAPTURE_PAGE":
                captured_pages += quantity
        config = (
            await connection.execute(
                select(gov.configs.c.data).where(gov.configs.c.id == call["config_id"])
            )
        ).scalar_one()
        if config["intended_use"]["provider"] == "OPENAI":
            openai_calls += 1
    if (
        search_results >= budget["max_search_results"]
        or captured_pages >= budget["max_capture_pages"]
        or openai_calls >= budget["max_openai_calls"]
    ):
        return "BUDGET_EXHAUSTED"
    return None


async def _require_exact_artifact(
    connection: AsyncConnection, experiment_id: UUID, artifact: ArtifactInput
) -> Any:
    row = (
        (
            await connection.execute(
                select(s.artifacts).where(
                    s.artifacts.c.id == artifact.artifact_id,
                    s.artifacts.c.experiment_id == experiment_id,
                    s.artifacts.c.kind == artifact.kind,
                    s.artifacts.c.version == artifact.version,
                    s.artifacts.c.content_hash == artifact.content_hash,
                )
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ProductRecordsDenied("STALE_INPUT")
    if await connection.scalar(
        select(s.artifacts.c.id).where(
            s.artifacts.c.logical_id == row["logical_id"],
            s.artifacts.c.version > row["version"],
        )
    ) or await connection.scalar(
        select(s.artifact_dispositions.c.id).where(
            s.artifact_dispositions.c.artifact_id == row["id"],
            s.artifact_dispositions.c.disposition == "SUPERSEDED",
        )
    ):
        raise ProductRecordsDenied("STALE_INPUT")
    return row


async def _supplied_budget_block_reason(
    connection: AsyncConnection,
    experiment_id: UUID,
    budget: ResearchCycleBudgetInput,
    now: datetime,
) -> str | None:
    if (
        min(
            budget.max_search_results,
            budget.max_capture_pages,
            budget.max_openai_calls,
        )
        <= 0
    ):
        return "BUDGET_EXHAUSTED"
    if not await connection.scalar(
        select(gov.configs.c.id).where(
            gov.configs.c.id == budget.config_id,
            gov.configs.c.workflow_id == budget.workflow_id,
            gov.configs.c.version == budget.config_version,
        )
    ):
        return "STALE_INPUT"
    account = (
        (
            await connection.execute(
                select(gov.budget_accounts).where(
                    gov.budget_accounts.c.id == budget.budget_account_id,
                    gov.budget_accounts.c.scope == "WORKFLOW",
                    gov.budget_accounts.c.experiment_id == experiment_id,
                    gov.budget_accounts.c.workflow_id == budget.workflow_id,
                )
            )
        )
        .mappings()
        .one_or_none()
    )
    if account is None:
        return "STALE_INPUT"
    if (
        account["frozen"]
        or account["effective_at"] > now
        or account["expires_at"] <= now
        or account["reserved"] + account["accrued"] >= account["limit"]
    ):
        return "BUDGET_EXHAUSTED"
    calls = (
        (
            await connection.execute(
                select(gov.calls).where(
                    gov.calls.c.experiment_id == experiment_id,
                    gov.calls.c.workflow_id == budget.workflow_id,
                )
            )
        )
        .mappings()
        .all()
    )
    search_results = captured_pages = openai_calls = 0
    for call in calls:
        if call["state"] == "RELEASED":
            continue
        if call["state"] != "FINAL":
            return "UNFINALIZED_USAGE"
        usage = (
            (
                await connection.execute(
                    select(gov.usage).where(gov.usage.c.call_id == call["id"])
                )
            )
            .mappings()
            .all()
        )
        superseded = {row["supersedes_id"] for row in usage if row["supersedes_id"]}
        live = [row for row in usage if row["id"] not in superseded]
        if any(row["knowledge"] != "FINAL" for row in live):
            return "UNFINALIZED_USAGE"
        settlement = (
            (
                await connection.execute(
                    select(gov.settlements)
                    .where(gov.settlements.c.call_id == call["id"])
                    .order_by(
                        gov.settlements.c.created_at.desc(),
                        gov.settlements.c.id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if (
            settlement is None
            or settlement["cost"] != call["accrued"]
            or settlement["cost_ils"] != call["accrued_ils"]
        ):
            return "UNFINALIZED_USAGE"
        for row in live:
            quantity = int(row["quantity"] or 0)
            if row["component"] == "SEARCH_RESULT":
                search_results += quantity
            elif row["component"] == "CAPTURE_PAGE":
                captured_pages += quantity
        config = await connection.scalar(
            select(gov.configs.c.data).where(gov.configs.c.id == call["config_id"])
        )
        if config is None:
            return "STALE_INPUT"
        if config["intended_use"]["provider"] == "OPENAI":
            openai_calls += 1
    if (
        search_results >= budget.max_search_results
        or captured_pages >= budget.max_capture_pages
        or openai_calls >= budget.max_openai_calls
    ):
        return "BUDGET_EXHAUSTED"
    return None


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

    @safe_records
    async def bind_research_cycle_budget(
        self,
        cycle_id: UUID,
        budget: ResearchCycleBudgetInput,
        *,
        command_key: UUID,
    ) -> CommandReceipt:
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
            request_hash = _request_hash(cycle_id=cycle_id, budget=budget)
            old = await _existing(
                connection, command_key, "BIND_RESEARCH_CYCLE_BUDGET", request_hash
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            await connection.execute(
                insert(s.research_cycle_budgets).values(
                    cycle_id=cycle_id,
                    experiment_id=cycle["experiment_id"],
                    **budget.model_dump(exclude={"schema_version"}),
                    created_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=cycle["experiment_id"],
                kind="BIND_RESEARCH_CYCLE_BUDGET",
                request_hash=request_hash,
                result_type="RESEARCH_CYCLE_BUDGET",
                result_id=cycle_id,
                now=self.clock(),
            )
            return CommandReceipt(command_id=command_id, result_id=cycle_id)

    @safe_records
    async def commit_market_research_outcome(
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
        runtime_workflow_id: str | None = None,
        feedback: ArtifactInput | None = None,
        feedback_validation: ArtifactInput | None = None,
        proposed_idea: ArtifactInput | None = None,
        plan: ArtifactInput | None = None,
        budget: ResearchCycleBudgetInput | None = None,
        accepted_by: UUID | None = None,
    ) -> MarketResearchOutcomeReceipt:
        """Commit the exact research verdict and its guarded state transition."""
        states: dict[
            str,
            Literal[
                "PROCEED_TO_OFFER",
                "RETURN_FOR_REFINEMENT",
                "WAITING_FOR_PIVOT_APPROVAL",
                "KILLED",
                "INCONCLUSIVE_REVIEW",
            ],
        ] = {
            "PROCEED_TO_OFFER": "PROCEED_TO_OFFER",
            "REFINE_SAME_IDEA": "RETURN_FOR_REFINEMENT",
            "MATERIAL_PIVOT_RECOMMENDED": "WAITING_FOR_PIVOT_APPROVAL",
            "KILL_IDEA": "KILLED",
            "INCONCLUSIVE": "INCONCLUSIVE_REVIEW",
        }
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
            request_hash = market_research_outcome_request_hash(
                attempt_id=attempt_id,
                report=report,
                recommendation=recommendation,
                verdict=verdict,
                committed_by=committed_by,
                feedback=feedback,
                feedback_validation=feedback_validation,
                proposed_idea=proposed_idea,
                plan=plan,
                budget=budget,
                accepted_by=accepted_by,
            )
            old = await _existing(
                connection, command_key, "COMMIT_MARKET_RESEARCH_OUTCOME", request_hash
            )
            if runtime_workflow_id is not None:
                binding = (
                    (
                        await connection.execute(
                            select(s.market_research_decision_workflow_bindings)
                            .where(
                                s.market_research_decision_workflow_bindings.c.dbos_workflow_id
                                == runtime_workflow_id,
                                s.market_research_decision_workflow_bindings.c.operation_kind
                                == "OUTCOME",
                                s.market_research_decision_workflow_bindings.c.operation_id
                                == attempt_id,
                                s.market_research_decision_workflow_bindings.c.business_command_key
                                == command_key,
                                s.market_research_decision_workflow_bindings.c.request_hash
                                == request_hash,
                            )
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                allowed = (
                    {
                        "STARTED",
                        "BUSINESS_COMMITTED",
                        "RECEIPT_DELIVERED",
                        "RUNTIME_COMPLETED",
                    }
                    if old
                    else {"STARTED"}
                )
                if binding is None or binding["delivery_state"] not in allowed:
                    raise ProductRecordsDenied("WORKFLOW_NOT_EXECUTABLE")
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
                transition = (
                    (
                        await connection.execute(
                            select(s.cycle_transitions).where(
                                s.cycle_transitions.c.verdict_id == row["id"],
                                s.cycle_transitions.c.command_id == old["id"],
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                child_cycle_id = await connection.scalar(
                    select(s.cycle_transitions.c.cycle_id).where(
                        s.cycle_transitions.c.command_id == old["id"],
                        s.cycle_transitions.c.ordinal == 1,
                        s.cycle_transitions.c.cycle_id != row["cycle_id"],
                    )
                )
                block_id = await connection.scalar(
                    select(s.research_return_blocks.c.id).where(
                        s.research_return_blocks.c.verdict_id == row["id"],
                        s.research_return_blocks.c.command_id == old["id"],
                    )
                )
                return MarketResearchOutcomeReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    cycle_id=row["cycle_id"],
                    verdict=row["verdict"],
                    transition_id=transition["id"],
                    state=transition["to_state"],
                    child_cycle_id=child_cycle_id,
                    block_id=block_id,
                )
            await _require_exact_artifact(connection, attempt["experiment_id"], report)
            await _require_exact_artifact(
                connection, attempt["experiment_id"], recommendation
            )
            state = (
                (
                    await connection.execute(
                        select(s.cycle_states)
                        .where(
                            s.cycle_states.c.cycle_id == attempt["cycle_id"],
                            s.cycle_states.c.experiment_id == attempt["experiment_id"],
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if state["state"] != "MARKET_RESEARCH":
                raise ProductRecordsDenied("INVALID_STATE")
            acceptance = (
                (
                    await connection.execute(
                        select(s.idea_acceptances).where(
                            s.idea_acceptances.c.cycle_id == attempt["cycle_id"],
                            s.idea_acceptances.c.experiment_id
                            == attempt["experiment_id"],
                        )
                    )
                )
                .mappings()
                .one()
            )
            block_reason: str | None = None
            return_ordinal: int | None = None
            scope_id: UUID | None = None
            if verdict == "REFINE_SAME_IDEA":
                parent = (
                    (
                        await connection.execute(
                            select(s.cycles).where(s.cycles.c.id == attempt["cycle_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                root = (
                    (
                        await connection.execute(
                            select(s.cycles).where(
                                s.cycles.c.experiment_id == attempt["experiment_id"],
                                s.cycles.c.ordinal == 1,
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                scope_id = (
                    parent["seed_artifact_id"]
                    if parent["idea_mode"] == "USER_SEEDED_REFINEMENT"
                    else await connection.scalar(
                        select(s.idea_acceptances.c.artifact_id).where(
                            s.idea_acceptances.c.cycle_id == root["id"]
                        )
                    )
                )
                return_ordinal = (
                    await connection.scalar(
                        select(func.count())
                        .select_from(s.returns)
                        .where(
                            s.returns.c.experiment_id == attempt["experiment_id"],
                            s.returns.c.kind == "SAME_INTENT",
                            s.returns.c.applicable_scope_id == scope_id,
                        )
                    )
                    or 0
                ) + 1
                if return_ordinal > 2:
                    block_reason = "SAME_INTENT_LIMIT_REACHED"
                elif any(
                    item is None
                    for item in (
                        feedback,
                        feedback_validation,
                        proposed_idea,
                        plan,
                        budget,
                        accepted_by,
                    )
                ):
                    block_reason = "MISSING_EVIDENCE"
                else:
                    assert feedback is not None
                    assert feedback_validation is not None
                    assert proposed_idea is not None
                    assert plan is not None
                    for supplied in (
                        feedback,
                        feedback_validation,
                        proposed_idea,
                        plan,
                    ):
                        await _require_exact_artifact(
                            connection, attempt["experiment_id"], supplied
                        )
                    block_reason = await _continuation_block_reason(
                        connection, attempt["cycle_id"], self.clock()
                    )
                    if block_reason is None:
                        assert budget is not None
                        block_reason = await _supplied_budget_block_reason(
                            connection,
                            attempt["experiment_id"],
                            budget,
                            self.clock(),
                        )
                        if block_reason == "STALE_INPUT":
                            raise ProductRecordsDenied("STALE_INPUT")
            result_id, transition_id = uuid4(), uuid4()
            now = self.clock()
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
                    committed_at=now,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=attempt["experiment_id"],
                kind="COMMIT_MARKET_RESEARCH_OUTCOME",
                request_hash=request_hash,
                result_type="VERDICT",
                result_id=result_id,
                now=now,
            )
            await connection.execute(
                insert(s.cycle_transitions).values(
                    id=transition_id,
                    experiment_id=attempt["experiment_id"],
                    cycle_id=attempt["cycle_id"],
                    ordinal=state["transition_ordinal"] + 1,
                    from_state="MARKET_RESEARCH",
                    to_state=states[verdict],
                    idea_acceptance_id=acceptance["id"],
                    idea_artifact_id=acceptance["artifact_id"],
                    idea_kind=acceptance["artifact_kind"],
                    idea_version=acceptance["artifact_version"],
                    idea_hash=acceptance["artifact_hash"],
                    research_attempt_id=attempt_id,
                    verdict_id=result_id,
                    command_id=command_id,
                    created_at=now,
                )
            )
            advanced = await connection.execute(
                update(s.cycle_states)
                .where(
                    s.cycle_states.c.cycle_id == attempt["cycle_id"],
                    s.cycle_states.c.experiment_id == attempt["experiment_id"],
                    s.cycle_states.c.state == "MARKET_RESEARCH",
                    s.cycle_states.c.transition_ordinal == state["transition_ordinal"],
                )
                .values(
                    state=states[verdict],
                    transition_ordinal=state["transition_ordinal"] + 1,
                    last_transition_id=transition_id,
                    updated_at=now,
                )
            )
            if advanced.rowcount != 1:
                raise ProductRecordsDenied("INVALID_STATE")
            block_id: UUID | None = None
            child_cycle_id: UUID | None = None
            if verdict == "REFINE_SAME_IDEA" and block_reason is not None:
                block_id = uuid4()
                await connection.execute(
                    insert(s.research_return_blocks).values(
                        id=block_id,
                        experiment_id=attempt["experiment_id"],
                        cycle_id=attempt["cycle_id"],
                        verdict_id=result_id,
                        return_kind="SAME_INTENT",
                        reason_code=block_reason,
                        command_id=command_id,
                        created_at=now,
                    )
                )
            elif verdict == "REFINE_SAME_IDEA":
                assert feedback is not None
                assert feedback_validation is not None
                assert proposed_idea is not None
                assert plan is not None
                assert budget is not None
                assert accepted_by is not None
                assert return_ordinal is not None
                assert scope_id is not None
                parent_idea = (
                    (
                        await connection.execute(
                            select(s.artifacts).where(
                                s.artifacts.c.id == acceptance["artifact_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                next_idea = (
                    (
                        await connection.execute(
                            select(s.artifacts).where(
                                s.artifacts.c.id == proposed_idea.artifact_id,
                                s.artifacts.c.experiment_id == attempt["experiment_id"],
                                s.artifacts.c.kind == proposed_idea.kind,
                                s.artifacts.c.version == proposed_idea.version,
                                s.artifacts.c.content_hash
                                == proposed_idea.content_hash,
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                if (
                    proposed_idea.kind != ArtifactKind.IDEA_BRIEF
                    or next_idea["logical_id"] != parent_idea["logical_id"]
                    or next_idea["version"] != parent_idea["version"] + 1
                    or next_idea["payload"]["core_intent"]
                    != parent_idea["payload"]["core_intent"]
                    or next_idea["payload"]["material_pivot"] is not False
                    or await connection.scalar(
                        select(s.artifacts.c.id).where(
                            s.artifacts.c.logical_id == next_idea["logical_id"],
                            s.artifacts.c.version > next_idea["version"],
                        )
                    )
                    or not await connection.scalar(
                        select(s.artifact_dispositions.c.id).where(
                            s.artifact_dispositions.c.artifact_id
                            == proposed_idea.artifact_id,
                            s.artifact_dispositions.c.disposition == "VALIDATED",
                        )
                    )
                ):
                    raise ProductRecordsDenied("INVALID_PROPOSED_IDEA")
                required_idea_links = {
                    ("ACCEPTED_IDEA", acceptance["artifact_id"]),
                    ("REPORT", report.artifact_id),
                    ("RECOMMENDATION", recommendation.artifact_id),
                    ("RETURN_FEEDBACK", feedback.artifact_id),
                }
                actual_idea_links = set(
                    (
                        await connection.execute(
                            select(
                                s.artifact_links.c.role,
                                s.artifact_links.c.producer_id,
                            ).where(
                                s.artifact_links.c.consumer_id
                                == proposed_idea.artifact_id
                            )
                        )
                    ).all()
                )
                if not required_idea_links.issubset(actual_idea_links):
                    raise ProductRecordsDenied("INVALID_PROPOSED_IDEA_LINEAGE")
                if not await connection.scalar(
                    select(s.artifact_dispositions.c.id).where(
                        s.artifact_dispositions.c.artifact_id == feedback.artifact_id,
                        s.artifact_dispositions.c.disposition == "ACCEPTED",
                    )
                ):
                    await connection.execute(
                        insert(s.artifact_dispositions).values(
                            id=uuid4(),
                            experiment_id=attempt["experiment_id"],
                            artifact_id=feedback.artifact_id,
                            artifact_kind=feedback.kind,
                            artifact_version=feedback.version,
                            artifact_hash=feedback.content_hash,
                            validation_artifact_id=feedback_validation.artifact_id,
                            validation_kind=feedback_validation.kind,
                            validation_version=feedback_validation.version,
                            validation_hash=feedback_validation.content_hash,
                            disposition="ACCEPTED",
                            decided_by=accepted_by,
                            decided_at=now,
                        )
                    )
                parent = (
                    (
                        await connection.execute(
                            select(s.cycles).where(s.cycles.c.id == attempt["cycle_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                cycle_ordinal = (
                    await connection.scalar(
                        select(func.count())
                        .select_from(s.cycles)
                        .where(s.cycles.c.experiment_id == attempt["experiment_id"])
                    )
                    or 0
                ) + 1
                child_cycle_id, return_id = uuid4(), uuid4()
                child_attempt_id, child_transition_id = uuid4(), uuid4()
                child_acceptance_id = uuid4()
                await connection.execute(
                    insert(s.cycles).values(
                        id=child_cycle_id,
                        experiment_id=attempt["experiment_id"],
                        ordinal=cycle_ordinal,
                        parent_cycle_id=attempt["cycle_id"],
                        idea_mode=parent["idea_mode"],
                        selection_id=parent["selection_id"],
                        purpose="SAME_INTENT_RETURN",
                        episode_id=parent["episode_id"],
                        seed_artifact_id=parent["seed_artifact_id"],
                        seed_kind=parent["seed_kind"],
                        seed_version=parent["seed_version"],
                        seed_hash=parent["seed_hash"],
                        created_at=now,
                    )
                )
                await connection.execute(
                    insert(s.returns).values(
                        id=return_id,
                        experiment_id=attempt["experiment_id"],
                        from_cycle_id=attempt["cycle_id"],
                        verdict_id=result_id,
                        to_cycle_id=child_cycle_id,
                        ordinal=return_ordinal,
                        kind="SAME_INTENT",
                        applicable_scope_id=scope_id,
                        idea_artifact_id=acceptance["artifact_id"],
                        offer_input_bundle_id=None,
                        feedback_artifact_id=feedback.artifact_id,
                        feedback_kind=feedback.kind,
                        feedback_version=feedback.version,
                        feedback_hash=feedback.content_hash,
                        created_at=now,
                    )
                )
                await connection.execute(
                    insert(s.idea_acceptances).values(
                        id=child_acceptance_id,
                        experiment_id=attempt["experiment_id"],
                        cycle_id=child_cycle_id,
                        artifact_id=proposed_idea.artifact_id,
                        artifact_kind=proposed_idea.kind,
                        artifact_version=proposed_idea.version,
                        artifact_hash=proposed_idea.content_hash,
                        pivot_approval_id=None,
                        accepted_by=accepted_by,
                        accepted_at=now,
                    )
                )
                plan_row = (
                    (
                        await connection.execute(
                            select(s.artifacts).where(
                                s.artifacts.c.id == plan.artifact_id,
                                s.artifacts.c.experiment_id == attempt["experiment_id"],
                                s.artifacts.c.kind == plan.kind,
                                s.artifacts.c.version == plan.version,
                                s.artifacts.c.content_hash == plan.content_hash,
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                if plan_row["workflow_id"] != budget.workflow_id:
                    raise ProductRecordsDenied("BUDGET_WORKFLOW_MISMATCH")
                await connection.execute(
                    insert(s.research_cycle_budgets).values(
                        cycle_id=child_cycle_id,
                        experiment_id=attempt["experiment_id"],
                        **budget.model_dump(exclude={"schema_version"}),
                        created_at=now,
                    )
                )
                await connection.execute(
                    insert(s.research_attempts).values(
                        id=child_attempt_id,
                        experiment_id=attempt["experiment_id"],
                        cycle_id=child_cycle_id,
                        ordinal=1,
                        plan_artifact_id=plan.artifact_id,
                        plan_kind=plan.kind,
                        plan_version=plan.version,
                        plan_hash=plan.content_hash,
                        created_at=now,
                    )
                )
                await connection.execute(
                    insert(s.cycle_transitions).values(
                        id=child_transition_id,
                        experiment_id=attempt["experiment_id"],
                        cycle_id=child_cycle_id,
                        ordinal=1,
                        from_state="IDEA_REFINEMENT",
                        to_state="MARKET_RESEARCH",
                        idea_acceptance_id=child_acceptance_id,
                        idea_artifact_id=proposed_idea.artifact_id,
                        idea_kind=proposed_idea.kind,
                        idea_version=proposed_idea.version,
                        idea_hash=proposed_idea.content_hash,
                        research_attempt_id=child_attempt_id,
                        verdict_id=None,
                        command_id=command_id,
                        created_at=now,
                    )
                )
                child_advanced = await connection.execute(
                    update(s.cycle_states)
                    .where(
                        s.cycle_states.c.cycle_id == child_cycle_id,
                        s.cycle_states.c.state == "IDEA_REFINEMENT",
                        s.cycle_states.c.transition_ordinal == 0,
                    )
                    .values(
                        state="MARKET_RESEARCH",
                        transition_ordinal=1,
                        last_transition_id=child_transition_id,
                        updated_at=now,
                    )
                )
                if child_advanced.rowcount != 1:
                    raise ProductRecordsDenied("INVALID_STATE")
            return MarketResearchOutcomeReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                cycle_id=attempt["cycle_id"],
                verdict=verdict,
                transition_id=transition_id,
                state=states[verdict],
                child_cycle_id=child_cycle_id,
                block_id=block_id,
            )

    @safe_records
    async def decide_material_pivot(
        self,
        verdict_id: UUID,
        *,
        decision_id: UUID,
        decision: Literal["APPROVED", "DENIED"],
        decided_by: UUID,
        reason_code: str,
        command_key: UUID,
        proposed_idea: ArtifactInput | None = None,
        feedback: ArtifactInput | None = None,
        feedback_validation: ArtifactInput | None = None,
        plan: ArtifactInput | None = None,
        budget: ResearchCycleBudgetInput | None = None,
        accepted_by: UUID | None = None,
        runtime_workflow_id: str | None = None,
    ) -> MaterialPivotDecisionReceipt:
        """Append one explicit pivot decision; denials never change the idea."""
        async with self.engine.begin() as connection:
            verdict_row = (
                (
                    await connection.execute(
                        select(s.verdicts).where(s.verdicts.c.id == verdict_id)
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, verdict_row["experiment_id"])
            request_hash = material_pivot_decision_request_hash(
                verdict_id=verdict_id,
                decision_id=decision_id,
                decision=decision,
                decided_by=decided_by,
                reason_code=reason_code,
                proposed_idea=proposed_idea,
                feedback=feedback,
                feedback_validation=feedback_validation,
                plan=plan,
                budget=budget,
                accepted_by=accepted_by,
            )
            old = await _existing(
                connection, command_key, "DECIDE_MATERIAL_PIVOT", request_hash
            )
            if runtime_workflow_id is not None:
                binding = (
                    (
                        await connection.execute(
                            select(s.market_research_decision_workflow_bindings)
                            .where(
                                s.market_research_decision_workflow_bindings.c.dbos_workflow_id
                                == runtime_workflow_id,
                                s.market_research_decision_workflow_bindings.c.operation_kind
                                == "PIVOT_DECISION",
                                s.market_research_decision_workflow_bindings.c.operation_id
                                == verdict_id,
                                s.market_research_decision_workflow_bindings.c.business_command_key
                                == command_key,
                                s.market_research_decision_workflow_bindings.c.request_hash
                                == request_hash,
                            )
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                allowed = (
                    {
                        "STARTED",
                        "BUSINESS_COMMITTED",
                        "RECEIPT_DELIVERED",
                        "RUNTIME_COMPLETED",
                    }
                    if old
                    else {"STARTED"}
                )
                if binding is None or binding["delivery_state"] not in allowed:
                    raise ProductRecordsDenied("WORKFLOW_NOT_EXECUTABLE")
            if old:
                if old["result_type"] == "RESEARCH_RETURN_BLOCK":
                    block = (
                        (
                            await connection.execute(
                                select(s.research_return_blocks).where(
                                    s.research_return_blocks.c.id == old["result_id"]
                                )
                            )
                        )
                        .mappings()
                        .one()
                    )
                    return MaterialPivotDecisionReceipt(
                        command_id=old["id"],
                        result_id=block["id"],
                        id=block["id"],
                        verdict_id=verdict_id,
                        cycle_id=block["cycle_id"],
                        decision=decision,
                        decision_ordinal=block["decision_ordinal"],
                        block_id=block["id"],
                    )
                row = (
                    (
                        await connection.execute(
                            select(s.pivot_decisions).where(
                                s.pivot_decisions.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return MaterialPivotDecisionReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    verdict_id=verdict_id,
                    cycle_id=verdict_row["cycle_id"],
                    decision=row["decision"],
                    decision_ordinal=row["decision_ordinal"],
                    child_cycle_id=await connection.scalar(
                        select(s.idea_acceptances.c.cycle_id).where(
                            s.idea_acceptances.c.pivot_approval_id == row["id"]
                        )
                    ),
                )
            if verdict_row["verdict"] != "MATERIAL_PIVOT_RECOMMENDED":
                raise ProductRecordsDenied("PIVOT_VERDICT_REQUIRED")
            state = (
                (
                    await connection.execute(
                        select(s.cycle_states)
                        .where(s.cycle_states.c.cycle_id == verdict_row["cycle_id"])
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if state["state"] != "WAITING_FOR_PIVOT_APPROVAL":
                raise ProductRecordsDenied("INVALID_STATE")
            if decision == "APPROVED" and any(
                item is None
                for item in (
                    proposed_idea,
                    feedback,
                    feedback_validation,
                    plan,
                    budget,
                    accepted_by,
                )
            ):
                raise ProductRecordsDenied("PIVOT_IDEA_REQUIRED")
            if decision == "DENIED" and proposed_idea is not None:
                raise ProductRecordsDenied("PIVOT_IDEA_FORBIDDEN")
            ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(s.pivot_decisions)
                    .where(s.pivot_decisions.c.verdict_id == verdict_id)
                )
                or 0
            ) + 1
            now = self.clock()
            if decision == "APPROVED":
                assert proposed_idea is not None
                assert feedback is not None
                assert feedback_validation is not None
                assert plan is not None
                assert budget is not None
                assert accepted_by is not None
                for supplied in (
                    proposed_idea,
                    feedback,
                    feedback_validation,
                    plan,
                ):
                    await _require_exact_artifact(
                        connection, verdict_row["experiment_id"], supplied
                    )
                block_reason = await _continuation_block_reason(
                    connection, verdict_row["cycle_id"], now
                )
                if block_reason is None:
                    block_reason = await _supplied_budget_block_reason(
                        connection,
                        verdict_row["experiment_id"],
                        budget,
                        now,
                    )
                    if block_reason == "STALE_INPUT":
                        raise ProductRecordsDenied("STALE_INPUT")
                if block_reason is not None:
                    block_id = uuid4()
                    command_id = await _complete(
                        connection,
                        command_key=command_key,
                        experiment_id=verdict_row["experiment_id"],
                        kind="DECIDE_MATERIAL_PIVOT",
                        request_hash=request_hash,
                        result_type="RESEARCH_RETURN_BLOCK",
                        result_id=block_id,
                        now=now,
                    )
                    await connection.execute(
                        insert(s.research_return_blocks).values(
                            id=block_id,
                            experiment_id=verdict_row["experiment_id"],
                            cycle_id=verdict_row["cycle_id"],
                            verdict_id=verdict_id,
                            return_kind="MATERIAL_PIVOT",
                            reason_code=block_reason,
                            decision_ordinal=ordinal,
                            command_id=command_id,
                            created_at=now,
                        )
                    )
                    return MaterialPivotDecisionReceipt(
                        command_id=command_id,
                        result_id=block_id,
                        id=block_id,
                        verdict_id=verdict_id,
                        cycle_id=verdict_row["cycle_id"],
                        decision=decision,
                        decision_ordinal=ordinal,
                        block_id=block_id,
                    )
                source_cycle = (
                    (
                        await connection.execute(
                            select(s.cycles).where(
                                s.cycles.c.id == verdict_row["cycle_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                source_acceptance = (
                    (
                        await connection.execute(
                            select(s.idea_acceptances).where(
                                s.idea_acceptances.c.cycle_id == verdict_row["cycle_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                source_idea = (
                    (
                        await connection.execute(
                            select(s.artifacts).where(
                                s.artifacts.c.id == source_acceptance["artifact_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                candidate = (
                    (
                        await connection.execute(
                            select(s.artifacts).where(
                                s.artifacts.c.id == proposed_idea.artifact_id,
                                s.artifacts.c.experiment_id
                                == verdict_row["experiment_id"],
                                s.artifacts.c.kind == proposed_idea.kind,
                                s.artifacts.c.version == proposed_idea.version,
                                s.artifacts.c.content_hash
                                == proposed_idea.content_hash,
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                if (
                    candidate["logical_id"] != source_idea["logical_id"]
                    or candidate["version"] != source_idea["version"] + 1
                    or candidate["payload"]["core_intent"]
                    == source_idea["payload"]["core_intent"]
                    or candidate["payload"]["material_pivot"] is not True
                    or await connection.scalar(
                        select(s.artifacts.c.id).where(
                            s.artifacts.c.logical_id == candidate["logical_id"],
                            s.artifacts.c.version > candidate["version"],
                        )
                    )
                    or not await connection.scalar(
                        select(s.artifact_dispositions.c.id).where(
                            s.artifact_dispositions.c.artifact_id
                            == proposed_idea.artifact_id,
                            s.artifact_dispositions.c.disposition == "VALIDATED",
                        )
                    )
                ):
                    raise ProductRecordsDenied("INVALID_PROPOSED_IDEA")
                required_links = {
                    ("ACCEPTED_IDEA", source_acceptance["artifact_id"]),
                    ("REPORT", verdict_row["report_artifact_id"]),
                    ("RECOMMENDATION", verdict_row["recommendation_artifact_id"]),
                    ("RETURN_FEEDBACK", feedback.artifact_id),
                }
                actual_links = set(
                    (
                        await connection.execute(
                            select(
                                s.artifact_links.c.role,
                                s.artifact_links.c.producer_id,
                            ).where(
                                s.artifact_links.c.consumer_id
                                == proposed_idea.artifact_id
                            )
                        )
                    ).all()
                )
                if not required_links.issubset(actual_links):
                    raise ProductRecordsDenied("INVALID_PROPOSED_IDEA_LINEAGE")
                if not await connection.scalar(
                    select(s.artifact_dispositions.c.id).where(
                        s.artifact_dispositions.c.artifact_id == feedback.artifact_id,
                        s.artifact_dispositions.c.disposition == "ACCEPTED",
                    )
                ):
                    await connection.execute(
                        insert(s.artifact_dispositions).values(
                            id=uuid4(),
                            experiment_id=verdict_row["experiment_id"],
                            artifact_id=feedback.artifact_id,
                            artifact_kind=feedback.kind,
                            artifact_version=feedback.version,
                            artifact_hash=feedback.content_hash,
                            validation_artifact_id=feedback_validation.artifact_id,
                            validation_kind=feedback_validation.kind,
                            validation_version=feedback_validation.version,
                            validation_hash=feedback_validation.content_hash,
                            disposition="ACCEPTED",
                            decided_by=accepted_by,
                            decided_at=now,
                        )
                    )
                child_cycle_id, return_id = uuid4(), uuid4()
                child_attempt_id, child_transition_id = uuid4(), uuid4()
                child_acceptance_id, parent_transition_id = uuid4(), uuid4()
                cycle_ordinal = (
                    await connection.scalar(
                        select(func.count())
                        .select_from(s.cycles)
                        .where(s.cycles.c.experiment_id == verdict_row["experiment_id"])
                    )
                    or 0
                ) + 1
                return_ordinal = (
                    await connection.scalar(
                        select(func.count())
                        .select_from(s.returns)
                        .where(
                            s.returns.c.experiment_id == verdict_row["experiment_id"],
                            s.returns.c.kind == "MATERIAL_PIVOT",
                            s.returns.c.applicable_scope_id
                            == source_cycle["episode_id"],
                        )
                    )
                    or 0
                ) + 1
                await connection.execute(
                    insert(s.cycles).values(
                        id=child_cycle_id,
                        experiment_id=verdict_row["experiment_id"],
                        ordinal=cycle_ordinal,
                        parent_cycle_id=verdict_row["cycle_id"],
                        idea_mode=source_cycle["idea_mode"],
                        selection_id=source_cycle["selection_id"],
                        purpose="MATERIAL_PIVOT_RETURN",
                        episode_id=source_cycle["episode_id"],
                        seed_artifact_id=source_cycle["seed_artifact_id"],
                        seed_kind=source_cycle["seed_kind"],
                        seed_version=source_cycle["seed_version"],
                        seed_hash=source_cycle["seed_hash"],
                        created_at=now,
                    )
                )
                await connection.execute(
                    insert(s.returns).values(
                        id=return_id,
                        experiment_id=verdict_row["experiment_id"],
                        from_cycle_id=verdict_row["cycle_id"],
                        verdict_id=verdict_id,
                        to_cycle_id=child_cycle_id,
                        ordinal=return_ordinal,
                        kind="MATERIAL_PIVOT",
                        applicable_scope_id=source_cycle["episode_id"],
                        idea_artifact_id=source_acceptance["artifact_id"],
                        offer_input_bundle_id=None,
                        feedback_artifact_id=feedback.artifact_id,
                        feedback_kind=feedback.kind,
                        feedback_version=feedback.version,
                        feedback_hash=feedback.content_hash,
                        created_at=now,
                    )
                )
                await connection.execute(
                    insert(s.pivot_decisions).values(
                        id=decision_id,
                        experiment_id=verdict_row["experiment_id"],
                        cycle_id=child_cycle_id,
                        artifact_id=proposed_idea.artifact_id,
                        artifact_kind=proposed_idea.kind,
                        artifact_version=proposed_idea.version,
                        artifact_hash=proposed_idea.content_hash,
                        approved_by=decided_by,
                        approved_at=now,
                        verdict_id=verdict_id,
                        decision=decision,
                        decision_ordinal=ordinal,
                        reason_code=reason_code,
                    )
                )
                await connection.execute(
                    insert(s.idea_acceptances).values(
                        id=child_acceptance_id,
                        experiment_id=verdict_row["experiment_id"],
                        cycle_id=child_cycle_id,
                        artifact_id=proposed_idea.artifact_id,
                        artifact_kind=proposed_idea.kind,
                        artifact_version=proposed_idea.version,
                        artifact_hash=proposed_idea.content_hash,
                        pivot_approval_id=decision_id,
                        accepted_by=accepted_by,
                        accepted_at=now,
                    )
                )
                plan_row = (
                    (
                        await connection.execute(
                            select(s.artifacts).where(
                                s.artifacts.c.id == plan.artifact_id,
                                s.artifacts.c.content_hash == plan.content_hash,
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                if plan_row["workflow_id"] != budget.workflow_id:
                    raise ProductRecordsDenied("BUDGET_WORKFLOW_MISMATCH")
                await connection.execute(
                    insert(s.research_cycle_budgets).values(
                        cycle_id=child_cycle_id,
                        experiment_id=verdict_row["experiment_id"],
                        **budget.model_dump(exclude={"schema_version"}),
                        created_at=now,
                    )
                )
                await connection.execute(
                    insert(s.research_attempts).values(
                        id=child_attempt_id,
                        experiment_id=verdict_row["experiment_id"],
                        cycle_id=child_cycle_id,
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
                    experiment_id=verdict_row["experiment_id"],
                    kind="DECIDE_MATERIAL_PIVOT",
                    request_hash=request_hash,
                    result_type="PIVOT_DECISION",
                    result_id=decision_id,
                    now=now,
                )
                await connection.execute(
                    insert(s.cycle_transitions).values(
                        id=parent_transition_id,
                        experiment_id=verdict_row["experiment_id"],
                        cycle_id=verdict_row["cycle_id"],
                        ordinal=3,
                        from_state="WAITING_FOR_PIVOT_APPROVAL",
                        to_state="RETURN_FOR_REFINEMENT",
                        idea_acceptance_id=source_acceptance["id"],
                        idea_artifact_id=source_acceptance["artifact_id"],
                        idea_kind=source_acceptance["artifact_kind"],
                        idea_version=source_acceptance["artifact_version"],
                        idea_hash=source_acceptance["artifact_hash"],
                        research_attempt_id=verdict_row["attempt_id"],
                        verdict_id=verdict_id,
                        command_id=command_id,
                        created_at=now,
                    )
                )
                await connection.execute(
                    update(s.cycle_states)
                    .where(
                        s.cycle_states.c.cycle_id == verdict_row["cycle_id"],
                        s.cycle_states.c.state == "WAITING_FOR_PIVOT_APPROVAL",
                    )
                    .values(
                        state="RETURN_FOR_REFINEMENT",
                        transition_ordinal=3,
                        last_transition_id=parent_transition_id,
                        updated_at=now,
                    )
                )
                await connection.execute(
                    insert(s.cycle_transitions).values(
                        id=child_transition_id,
                        experiment_id=verdict_row["experiment_id"],
                        cycle_id=child_cycle_id,
                        ordinal=1,
                        from_state="IDEA_REFINEMENT",
                        to_state="MARKET_RESEARCH",
                        idea_acceptance_id=child_acceptance_id,
                        idea_artifact_id=proposed_idea.artifact_id,
                        idea_kind=proposed_idea.kind,
                        idea_version=proposed_idea.version,
                        idea_hash=proposed_idea.content_hash,
                        research_attempt_id=child_attempt_id,
                        verdict_id=None,
                        command_id=command_id,
                        created_at=now,
                    )
                )
                await connection.execute(
                    update(s.cycle_states)
                    .where(
                        s.cycle_states.c.cycle_id == child_cycle_id,
                        s.cycle_states.c.state == "IDEA_REFINEMENT",
                    )
                    .values(
                        state="MARKET_RESEARCH",
                        transition_ordinal=1,
                        last_transition_id=child_transition_id,
                        updated_at=now,
                    )
                )
                return MaterialPivotDecisionReceipt(
                    command_id=command_id,
                    result_id=decision_id,
                    id=decision_id,
                    verdict_id=verdict_id,
                    cycle_id=verdict_row["cycle_id"],
                    decision=decision,
                    decision_ordinal=ordinal,
                    child_cycle_id=child_cycle_id,
                )
            await connection.execute(
                insert(s.pivot_decisions).values(
                    id=decision_id,
                    experiment_id=verdict_row["experiment_id"],
                    cycle_id=verdict_row["cycle_id"],
                    artifact_id=proposed_idea.artifact_id if proposed_idea else None,
                    artifact_kind=proposed_idea.kind if proposed_idea else None,
                    artifact_version=proposed_idea.version if proposed_idea else None,
                    artifact_hash=(
                        proposed_idea.content_hash if proposed_idea else None
                    ),
                    approved_by=decided_by,
                    approved_at=now,
                    verdict_id=verdict_id,
                    decision=decision,
                    decision_ordinal=ordinal,
                    reason_code=reason_code,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=verdict_row["experiment_id"],
                kind="DECIDE_MATERIAL_PIVOT",
                request_hash=request_hash,
                result_type="PIVOT_DECISION",
                result_id=decision_id,
                now=now,
            )
            return MaterialPivotDecisionReceipt(
                command_id=command_id,
                result_id=decision_id,
                id=decision_id,
                verdict_id=verdict_id,
                cycle_id=verdict_row["cycle_id"],
                decision=decision,
                decision_ordinal=ordinal,
            )

    @safe_records
    async def start_inconclusive_supplement(
        self,
        verdict_id: UUID,
        *,
        feedback: ArtifactInput,
        feedback_validation: ArtifactInput,
        plan: ArtifactInput,
        budget: ResearchCycleBudgetInput,
        accepted_by: UUID,
        command_key: UUID,
        runtime_workflow_id: str | None = None,
    ) -> ResearchContinuationReceipt:
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
            request_hash = inconclusive_supplement_request_hash(
                verdict_id=verdict_id,
                feedback=feedback,
                feedback_validation=feedback_validation,
                plan=plan,
                budget=budget,
                accepted_by=accepted_by,
            )
            old = await _existing(
                connection,
                command_key,
                "START_INCONCLUSIVE_SUPPLEMENT",
                request_hash,
            )
            if runtime_workflow_id is not None:
                binding = (
                    (
                        await connection.execute(
                            select(s.market_research_decision_workflow_bindings)
                            .where(
                                s.market_research_decision_workflow_bindings.c.dbos_workflow_id
                                == runtime_workflow_id,
                                s.market_research_decision_workflow_bindings.c.operation_kind
                                == "INCONCLUSIVE_SUPPLEMENT",
                                s.market_research_decision_workflow_bindings.c.operation_id
                                == verdict_id,
                                s.market_research_decision_workflow_bindings.c.business_command_key
                                == command_key,
                                s.market_research_decision_workflow_bindings.c.request_hash
                                == request_hash,
                            )
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                allowed = (
                    {
                        "STARTED",
                        "BUSINESS_COMMITTED",
                        "RECEIPT_DELIVERED",
                        "RUNTIME_COMPLETED",
                    }
                    if old
                    else {"STARTED"}
                )
                if binding is None or binding["delivery_state"] not in allowed:
                    raise ProductRecordsDenied("WORKFLOW_NOT_EXECUTABLE")
            if old:
                if old["result_type"] == "RESEARCH_RETURN_BLOCK":
                    block = (
                        (
                            await connection.execute(
                                select(s.research_return_blocks).where(
                                    s.research_return_blocks.c.id == old["result_id"]
                                )
                            )
                        )
                        .mappings()
                        .one()
                    )
                    return ResearchContinuationReceipt(
                        command_id=old["id"],
                        result_id=block["id"],
                        id=block["id"],
                        verdict_id=verdict_id,
                        cycle_id=verdict["cycle_id"],
                        outcome="BLOCKED",
                        block_id=block["id"],
                        reason_code=block["reason_code"],
                    )
                child = (
                    (
                        await connection.execute(
                            select(s.cycles).where(s.cycles.c.id == old["result_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                return ResearchContinuationReceipt(
                    command_id=old["id"],
                    result_id=child["id"],
                    id=child["id"],
                    verdict_id=verdict_id,
                    cycle_id=verdict["cycle_id"],
                    outcome="STARTED",
                    child_cycle_id=child["id"],
                )
            state = (
                (
                    await connection.execute(
                        select(s.cycle_states)
                        .where(s.cycle_states.c.cycle_id == verdict["cycle_id"])
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if (
                verdict["verdict"] != "INCONCLUSIVE"
                or state["state"] != "INCONCLUSIVE_REVIEW"
            ):
                raise ProductRecordsDenied("INVALID_STATE")
            for supplied in (feedback, feedback_validation, plan):
                await _require_exact_artifact(
                    connection, verdict["experiment_id"], supplied
                )
            source_cycle = (
                (
                    await connection.execute(
                        select(s.cycles).where(s.cycles.c.id == verdict["cycle_id"])
                    )
                )
                .mappings()
                .one()
            )
            source_acceptance = (
                (
                    await connection.execute(
                        select(s.idea_acceptances).where(
                            s.idea_acceptances.c.cycle_id == verdict["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            existing_count = (
                await connection.scalar(
                    select(func.count())
                    .select_from(s.returns)
                    .where(
                        s.returns.c.experiment_id == verdict["experiment_id"],
                        s.returns.c.kind == "INCONCLUSIVE_SUPPLEMENT",
                        s.returns.c.applicable_scope_id == source_cycle["episode_id"],
                    )
                )
                or 0
            )
            now = self.clock()
            reason = (
                "SUPPLEMENT_LIMIT_REACHED"
                if existing_count >= 1
                else await _continuation_block_reason(
                    connection, verdict["cycle_id"], now
                )
            )
            if reason is None:
                reason = await _supplied_budget_block_reason(
                    connection,
                    verdict["experiment_id"],
                    budget,
                    now,
                )
                if reason == "STALE_INPUT":
                    raise ProductRecordsDenied("STALE_INPUT")
            if reason is not None:
                block_id = uuid4()
                command_id = await _complete(
                    connection,
                    command_key=command_key,
                    experiment_id=verdict["experiment_id"],
                    kind="START_INCONCLUSIVE_SUPPLEMENT",
                    request_hash=request_hash,
                    result_type="RESEARCH_RETURN_BLOCK",
                    result_id=block_id,
                    now=now,
                )
                await connection.execute(
                    insert(s.research_return_blocks).values(
                        id=block_id,
                        experiment_id=verdict["experiment_id"],
                        cycle_id=verdict["cycle_id"],
                        verdict_id=verdict_id,
                        return_kind="INCONCLUSIVE_SUPPLEMENT",
                        reason_code=reason,
                        command_id=command_id,
                        created_at=now,
                    )
                )
                return ResearchContinuationReceipt(
                    command_id=command_id,
                    result_id=block_id,
                    id=block_id,
                    verdict_id=verdict_id,
                    cycle_id=verdict["cycle_id"],
                    outcome="BLOCKED",
                    block_id=block_id,
                    reason_code=reason,
                )
            if not await connection.scalar(
                select(s.artifact_dispositions.c.id).where(
                    s.artifact_dispositions.c.artifact_id == feedback.artifact_id,
                    s.artifact_dispositions.c.disposition == "ACCEPTED",
                )
            ):
                await connection.execute(
                    insert(s.artifact_dispositions).values(
                        id=uuid4(),
                        experiment_id=verdict["experiment_id"],
                        artifact_id=feedback.artifact_id,
                        artifact_kind=feedback.kind,
                        artifact_version=feedback.version,
                        artifact_hash=feedback.content_hash,
                        validation_artifact_id=feedback_validation.artifact_id,
                        validation_kind=feedback_validation.kind,
                        validation_version=feedback_validation.version,
                        validation_hash=feedback_validation.content_hash,
                        disposition="ACCEPTED",
                        decided_by=accepted_by,
                        decided_at=now,
                    )
                )
            plan_row = (
                (
                    await connection.execute(
                        select(s.artifacts).where(
                            s.artifacts.c.id == plan.artifact_id,
                            s.artifacts.c.content_hash == plan.content_hash,
                        )
                    )
                )
                .mappings()
                .one()
            )
            if plan_row["workflow_id"] != budget.workflow_id:
                raise ProductRecordsDenied("BUDGET_WORKFLOW_MISMATCH")
            child_cycle_id, return_id = uuid4(), uuid4()
            attempt_id, child_transition_id, parent_transition_id = (
                uuid4(),
                uuid4(),
                uuid4(),
            )
            acceptance_id = uuid4()
            cycle_ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(s.cycles)
                    .where(s.cycles.c.experiment_id == verdict["experiment_id"])
                )
                or 0
            ) + 1
            await connection.execute(
                insert(s.cycles).values(
                    id=child_cycle_id,
                    experiment_id=verdict["experiment_id"],
                    ordinal=cycle_ordinal,
                    parent_cycle_id=verdict["cycle_id"],
                    idea_mode=source_cycle["idea_mode"],
                    selection_id=source_cycle["selection_id"],
                    purpose="INCONCLUSIVE_SUPPLEMENT",
                    episode_id=source_cycle["episode_id"],
                    seed_artifact_id=source_cycle["seed_artifact_id"],
                    seed_kind=source_cycle["seed_kind"],
                    seed_version=source_cycle["seed_version"],
                    seed_hash=source_cycle["seed_hash"],
                    created_at=now,
                )
            )
            await connection.execute(
                insert(s.returns).values(
                    id=return_id,
                    experiment_id=verdict["experiment_id"],
                    from_cycle_id=verdict["cycle_id"],
                    verdict_id=verdict_id,
                    to_cycle_id=child_cycle_id,
                    ordinal=1,
                    kind="INCONCLUSIVE_SUPPLEMENT",
                    applicable_scope_id=source_cycle["episode_id"],
                    idea_artifact_id=source_acceptance["artifact_id"],
                    offer_input_bundle_id=None,
                    feedback_artifact_id=feedback.artifact_id,
                    feedback_kind=feedback.kind,
                    feedback_version=feedback.version,
                    feedback_hash=feedback.content_hash,
                    created_at=now,
                )
            )
            await connection.execute(
                insert(s.idea_acceptances).values(
                    id=acceptance_id,
                    experiment_id=verdict["experiment_id"],
                    cycle_id=child_cycle_id,
                    artifact_id=source_acceptance["artifact_id"],
                    artifact_kind=source_acceptance["artifact_kind"],
                    artifact_version=source_acceptance["artifact_version"],
                    artifact_hash=source_acceptance["artifact_hash"],
                    pivot_approval_id=None,
                    accepted_by=source_acceptance["accepted_by"],
                    accepted_at=now,
                )
            )
            await connection.execute(
                insert(s.research_cycle_budgets).values(
                    cycle_id=child_cycle_id,
                    experiment_id=verdict["experiment_id"],
                    **budget.model_dump(exclude={"schema_version"}),
                    created_at=now,
                )
            )
            await connection.execute(
                insert(s.research_attempts).values(
                    id=attempt_id,
                    experiment_id=verdict["experiment_id"],
                    cycle_id=child_cycle_id,
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
                experiment_id=verdict["experiment_id"],
                kind="START_INCONCLUSIVE_SUPPLEMENT",
                request_hash=request_hash,
                result_type="CYCLE",
                result_id=child_cycle_id,
                now=now,
            )
            await connection.execute(
                insert(s.cycle_transitions).values(
                    id=parent_transition_id,
                    experiment_id=verdict["experiment_id"],
                    cycle_id=verdict["cycle_id"],
                    ordinal=3,
                    from_state="INCONCLUSIVE_REVIEW",
                    to_state="RETURN_FOR_REFINEMENT",
                    idea_acceptance_id=source_acceptance["id"],
                    idea_artifact_id=source_acceptance["artifact_id"],
                    idea_kind=source_acceptance["artifact_kind"],
                    idea_version=source_acceptance["artifact_version"],
                    idea_hash=source_acceptance["artifact_hash"],
                    research_attempt_id=verdict["attempt_id"],
                    verdict_id=verdict_id,
                    command_id=command_id,
                    created_at=now,
                )
            )
            await connection.execute(
                update(s.cycle_states)
                .where(
                    s.cycle_states.c.cycle_id == verdict["cycle_id"],
                    s.cycle_states.c.state == "INCONCLUSIVE_REVIEW",
                )
                .values(
                    state="RETURN_FOR_REFINEMENT",
                    transition_ordinal=3,
                    last_transition_id=parent_transition_id,
                    updated_at=now,
                )
            )
            await connection.execute(
                insert(s.cycle_transitions).values(
                    id=child_transition_id,
                    experiment_id=verdict["experiment_id"],
                    cycle_id=child_cycle_id,
                    ordinal=1,
                    from_state="IDEA_REFINEMENT",
                    to_state="MARKET_RESEARCH",
                    idea_acceptance_id=acceptance_id,
                    idea_artifact_id=source_acceptance["artifact_id"],
                    idea_kind=source_acceptance["artifact_kind"],
                    idea_version=source_acceptance["artifact_version"],
                    idea_hash=source_acceptance["artifact_hash"],
                    research_attempt_id=attempt_id,
                    verdict_id=None,
                    command_id=command_id,
                    created_at=now,
                )
            )
            await connection.execute(
                update(s.cycle_states)
                .where(
                    s.cycle_states.c.cycle_id == child_cycle_id,
                    s.cycle_states.c.state == "IDEA_REFINEMENT",
                )
                .values(
                    state="MARKET_RESEARCH",
                    transition_ordinal=1,
                    last_transition_id=child_transition_id,
                    updated_at=now,
                )
            )
            return ResearchContinuationReceipt(
                command_id=command_id,
                result_id=child_cycle_id,
                id=child_cycle_id,
                verdict_id=verdict_id,
                cycle_id=verdict["cycle_id"],
                outcome="STARTED",
                child_cycle_id=child_cycle_id,
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
    async def start_same_intent_refinement_return(
        self,
        verdict_id: UUID,
        *,
        feedback: ArtifactInput,
        command_key: UUID,
    ) -> SameIntentReturnReceipt:
        """Start the bounded L07 return without accepting a successor brief.

        This intentionally consumes only the plain committed verdict contract.
        Managed L08 outcomes own their own continuation workflow and are refused.
        """
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
                verdict_id=verdict_id, feedback=feedback, command="L07_SAME_INTENT"
            )
            old = await _existing(
                connection,
                command_key,
                "START_SAME_INTENT_REFINEMENT_RETURN",
                request_hash,
            )
            if old:
                if old["result_type"] == "RESEARCH_RETURN_BLOCK":
                    block = (
                        (
                            await connection.execute(
                                select(s.research_return_blocks).where(
                                    s.research_return_blocks.c.id == old["result_id"]
                                )
                            )
                        )
                        .mappings()
                        .one()
                    )
                    return SameIntentReturnReceipt(
                        command_id=old["id"],
                        result_id=block["id"],
                        experiment_id=verdict["experiment_id"],
                        verdict_id=verdict_id,
                        outcome="REVIEW_REQUIRED",
                        block_id=block["id"],
                        reason_code=block["reason_code"],
                    )
                cycle = (
                    (
                        await connection.execute(
                            select(s.cycles).where(s.cycles.c.id == old["result_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                return SameIntentReturnReceipt(
                    command_id=old["id"],
                    result_id=cycle["id"],
                    id=cycle["id"],
                    experiment_id=cycle["experiment_id"],
                    verdict_id=verdict_id,
                    outcome="STARTED",
                )
            if verdict["verdict"] != "REFINE_SAME_IDEA":
                raise ProductRecordsDenied("REFINE_SAME_IDEA_VERDICT_REQUIRED")
            if await connection.scalar(
                select(s.cycle_transitions.c.id)
                .join(s.commands, s.commands.c.id == s.cycle_transitions.c.command_id)
                .where(
                    s.cycle_transitions.c.verdict_id == verdict_id,
                    s.commands.c.kind == "COMMIT_MARKET_RESEARCH_OUTCOME",
                )
            ):
                raise ProductRecordsDenied("MANAGED_RETURN_COMMAND_REQUIRED")
            await _require_exact_artifact(
                connection, verdict["experiment_id"], feedback
            )
            if feedback.kind is not ArtifactKind.RESEARCH_FEEDBACK_BRIEF:
                raise ProductRecordsDenied("RESEARCH_FEEDBACK_REQUIRED")
            feedback_row = (
                (
                    await connection.execute(
                        select(s.artifacts).where(
                            s.artifacts.c.id == feedback.artifact_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            if set(feedback_row["payload"]) != {
                "preserve",
                "change",
                "failed_dimensions",
                "research_questions",
            }:
                raise ProductRecordsDenied("STRUCTURED_FEEDBACK_REQUIRED")
            if not await connection.scalar(
                select(s.artifact_dispositions.c.id).where(
                    s.artifact_dispositions.c.artifact_id == feedback.artifact_id,
                    s.artifact_dispositions.c.disposition == "ACCEPTED",
                )
            ):
                raise ProductRecordsDenied("UNCOMMITTED_FEEDBACK")
            if await connection.scalar(
                select(s.artifacts.c.id).where(
                    s.artifacts.c.logical_id == feedback_row["logical_id"],
                    s.artifacts.c.version > feedback_row["version"],
                )
            ) or await connection.scalar(
                select(s.artifact_dispositions.c.id).where(
                    s.artifact_dispositions.c.artifact_id == feedback.artifact_id,
                    s.artifact_dispositions.c.disposition == "SUPERSEDED",
                )
            ):
                raise ProductRecordsDenied("STALE_RESEARCH_FEEDBACK")
            parent = (
                (
                    await connection.execute(
                        select(s.cycles).where(s.cycles.c.id == verdict["cycle_id"])
                    )
                )
                .mappings()
                .one()
            )
            current_cycle = await connection.scalar(
                select(s.cycles.c.id)
                .where(s.cycles.c.experiment_id == verdict["experiment_id"])
                .order_by(s.cycles.c.ordinal.desc())
                .limit(1)
            )
            if current_cycle != parent["id"]:
                raise ProductRecordsDenied("STALE_IDEA_LINEAGE")
            acceptance = (
                (
                    await connection.execute(
                        select(s.idea_acceptances).where(
                            s.idea_acceptances.c.cycle_id == parent["id"],
                            s.idea_acceptances.c.experiment_id
                            == verdict["experiment_id"],
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if acceptance is None:
                raise ProductRecordsDenied("MISSING_ACCEPTED_IDEA")
            state = await connection.scalar(
                select(s.cycle_states.c.state).where(
                    s.cycle_states.c.cycle_id == parent["id"],
                    s.cycle_states.c.experiment_id == verdict["experiment_id"],
                )
            )
            if state != "MARKET_RESEARCH":
                raise ProductRecordsDenied("RESEARCH_CYCLE_NOT_ACTIVE")
            expected_links = {
                (
                    acceptance["artifact_id"],
                    acceptance["artifact_kind"],
                    acceptance["artifact_version"],
                    acceptance["artifact_hash"],
                    "ACCEPTED_IDEA",
                ),
                (
                    verdict["report_artifact_id"],
                    verdict["report_kind"],
                    verdict["report_version"],
                    verdict["report_hash"],
                    "REPORT",
                ),
                (
                    verdict["recommendation_artifact_id"],
                    verdict["recommendation_kind"],
                    verdict["recommendation_version"],
                    verdict["recommendation_hash"],
                    "RECOMMENDATION",
                ),
            }
            links = {
                (
                    row["producer_id"],
                    row["producer_kind"],
                    row["producer_version"],
                    row["producer_hash"],
                    row["role"],
                )
                for row in (
                    (
                        await connection.execute(
                            select(s.artifact_links).where(
                                s.artifact_links.c.consumer_id == feedback.artifact_id
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
            }
            if links != expected_links:
                raise ProductRecordsDenied("FORGED_RESEARCH_FEEDBACK")
            scope_id = (
                parent["seed_artifact_id"]
                if parent["idea_mode"] == "USER_SEEDED_REFINEMENT"
                else await connection.scalar(
                    select(s.idea_acceptances.c.artifact_id).where(
                        s.idea_acceptances.c.cycle_id
                        == select(s.cycles.c.id)
                        .where(
                            s.cycles.c.experiment_id == verdict["experiment_id"],
                            s.cycles.c.ordinal == 1,
                        )
                        .scalar_subquery()
                    )
                )
            )
            assert scope_id is not None
            prior_feedbacks = (
                (
                    await connection.execute(
                        select(s.artifacts.c.payload)
                        .select_from(
                            s.returns.join(
                                s.artifacts,
                                s.artifacts.c.id == s.returns.c.feedback_artifact_id,
                            )
                        )
                        .where(
                            s.returns.c.experiment_id == verdict["experiment_id"],
                            s.returns.c.kind == "SAME_INTENT",
                            s.returns.c.applicable_scope_id == scope_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            dimensions = tuple(
                sorted(set(feedback_row["payload"]["failed_dimensions"]))
            )
            reason = (
                "SAME_INTENT_LIMIT_REACHED"
                if len(prior_feedbacks) >= 2
                else "REPEATED_BLOCKER"
                if any(
                    tuple(sorted(set(item.get("failed_dimensions", [])))) == dimensions
                    for item in prior_feedbacks
                )
                else None
            )
            now = self.clock()
            if reason is not None:
                block_id = uuid4()
                command_id = await _complete(
                    connection,
                    command_key=command_key,
                    experiment_id=verdict["experiment_id"],
                    kind="START_SAME_INTENT_REFINEMENT_RETURN",
                    request_hash=request_hash,
                    result_type="RESEARCH_RETURN_BLOCK",
                    result_id=block_id,
                    now=now,
                )
                await connection.execute(
                    insert(s.research_return_blocks).values(
                        id=block_id,
                        experiment_id=verdict["experiment_id"],
                        cycle_id=parent["id"],
                        verdict_id=verdict_id,
                        return_kind="SAME_INTENT",
                        reason_code=reason,
                        command_id=command_id,
                        created_at=now,
                    )
                )
                return SameIntentReturnReceipt(
                    command_id=command_id,
                    result_id=block_id,
                    experiment_id=verdict["experiment_id"],
                    verdict_id=verdict_id,
                    outcome="REVIEW_REQUIRED",
                    block_id=block_id,
                    reason_code=reason,
                )
            child_id = uuid4()
            ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(s.cycles)
                    .where(s.cycles.c.experiment_id == verdict["experiment_id"])
                )
                or 0
            ) + 1
            await connection.execute(
                insert(s.cycles).values(
                    id=child_id,
                    experiment_id=verdict["experiment_id"],
                    ordinal=ordinal,
                    parent_cycle_id=parent["id"],
                    idea_mode=parent["idea_mode"],
                    selection_id=parent["selection_id"],
                    purpose="SAME_INTENT_RETURN",
                    episode_id=parent["episode_id"],
                    seed_artifact_id=parent["seed_artifact_id"],
                    seed_kind=parent["seed_kind"],
                    seed_version=parent["seed_version"],
                    seed_hash=parent["seed_hash"],
                    created_at=now,
                )
            )
            await connection.execute(
                insert(s.returns).values(
                    id=uuid4(),
                    experiment_id=verdict["experiment_id"],
                    from_cycle_id=parent["id"],
                    verdict_id=verdict_id,
                    to_cycle_id=child_id,
                    ordinal=len(prior_feedbacks) + 1,
                    kind="SAME_INTENT",
                    applicable_scope_id=scope_id,
                    idea_artifact_id=acceptance["artifact_id"],
                    feedback_artifact_id=feedback.artifact_id,
                    feedback_kind=feedback.kind,
                    feedback_version=feedback.version,
                    feedback_hash=feedback.content_hash,
                    created_at=now,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=verdict["experiment_id"],
                kind="START_SAME_INTENT_REFINEMENT_RETURN",
                request_hash=request_hash,
                result_type="CYCLE",
                result_id=child_id,
                now=now,
            )
            return SameIntentReturnReceipt(
                command_id=command_id,
                result_id=child_id,
                id=child_id,
                experiment_id=verdict["experiment_id"],
                verdict_id=verdict_id,
                outcome="STARTED",
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
            if await connection.scalar(
                select(s.cycle_transitions.c.id)
                .join(
                    s.commands,
                    s.commands.c.id == s.cycle_transitions.c.command_id,
                )
                .where(
                    s.cycle_transitions.c.verdict_id == verdict_id,
                    s.commands.c.kind == "COMMIT_MARKET_RESEARCH_OUTCOME",
                )
            ):
                raise ProductRecordsDenied("MANAGED_RETURN_COMMAND_REQUIRED")
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
