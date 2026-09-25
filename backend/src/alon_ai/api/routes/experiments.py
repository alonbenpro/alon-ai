"""Operator-owned, user-seeded experiment creation and Idea review."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import null, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from alon_ai.accounting import schema as gov
from alon_ai.api.recorded_idea_runtime import provision_recorded_seeded_runtime
from alon_ai.openai_runtime.contract import RoutingFacts, canonical_json, sha256
from alon_ai.openai_runtime.idea import SeededIdeaBriefAdvice
from alon_ai.openai_runtime.schema import run_intents
from alon_ai.openai_runtime.store import OpenAIRunOutcome, OpenAIRunStore
from alon_ai.records import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    CommercialConstraints,
    DeliveryConstraints,
    OperatorProfileVersion,
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductRecordsRepository,
    ProductWorkflow,
)
from alon_ai.records import schema as records
from alon_ai.records.operators import OperatorRepository

router = APIRouter()


def _id(key: UUID, name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"alon-ai-l07/{key}/{name}")


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExperimentBriefInput(StrictRequest):
    objective: str = Field(min_length=1, max_length=4000)
    target_customer: str = Field(min_length=1, max_length=4000)
    problem: str = Field(min_length=1, max_length=4000)
    geographies: list[str] = Field(min_length=1, max_length=20)
    commercial_boundaries: str = Field(min_length=1, max_length=4000)
    budget_usd: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    evidence_definitions: list[str] = Field(min_length=1, max_length=20)
    launch_stage: Literal["SHADOW"]

    @field_validator("objective", "target_customer", "problem", "commercial_boundaries")
    @classmethod
    def meaningful_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required text is blank")
        return value

    @field_validator("geographies", "evidence_definitions")
    @classmethod
    def meaningful_list(cls, values: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 4000 for item in values) or len(
            values
        ) != len(set(values)):
            raise ValueError("invalid experiment list")
        return values

    def artifact_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class DeliveryInput(StrictRequest):
    max_project_hours: Annotated[Decimal, Field(gt=0, le=100000, decimal_places=2)]
    hours_per_week: Annotated[Decimal, Field(gt=0, le=168, decimal_places=2)]
    concurrent_projects: int = Field(ge=1, le=100)


class CommercialInput(StrictRequest):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    hourly_cost: Annotated[Decimal, Field(ge=0, decimal_places=6)]
    minimum_project_price: Annotated[Decimal, Field(ge=0, decimal_places=6)]
    minimum_margin_rate: Annotated[Decimal, Field(ge=0, le=1, decimal_places=6)]
    maximum_discount_rate: Annotated[Decimal, Field(ge=0, le=1, decimal_places=6)]
    minimum_deposit_rate: Annotated[Decimal, Field(ge=0, le=1, decimal_places=6)]


class OperatorProfileInput(StrictRequest):
    capabilities: tuple[str, ...] = Field(min_length=1, max_length=100)
    constraints: tuple[str, ...] = Field(max_length=100)
    delivery: DeliveryInput
    commercial: CommercialInput


class CreateExperimentRequest(StrictRequest):
    name: str = Field(min_length=1, max_length=120)
    idea_seed: str = Field(min_length=1, max_length=4000)
    brief: ExperimentBriefInput
    operator_profile: OperatorProfileInput
    command_key: UUID

    @field_validator("name", "idea_seed")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required text is blank")
        return value


class CreateExperimentResponse(StrictRequest):
    experiment_id: UUID
    cycle_id: UUID
    brief_artifact_id: UUID
    seed_artifact_id: UUID
    state: Literal["AWAITING_REFINEMENT"] = "AWAITING_REFINEMENT"


async def _profile(
    request: Request, payload: OperatorProfileInput, operator_id: UUID
) -> tuple[UUID, int]:
    engine = request.app.state.engine
    delivery = DeliveryConstraints.model_validate(payload.delivery.model_dump())
    commercial = CommercialConstraints.model_validate(payload.commercial.model_dump())
    async with engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    select(records.operator_profiles)
                    .where(records.operator_profiles.c.operator_id == operator_id)
                    .order_by(records.operator_profiles.c.version.desc())
                )
            )
            .mappings()
            .all()
        )
    expected_delivery = delivery.model_dump(mode="json")
    expected_commercial = commercial.model_dump(mode="json")
    for row in rows:
        if (
            row["capabilities"] == list(payload.capabilities)
            and row["constraints"] == list(payload.constraints)
            and row["delivery"] == expected_delivery
            and row["commercial"] == expected_commercial
        ):
            return row["id"], row["version"]
    profile_id = rows[0]["id"] if rows else _id(operator_id, "profile")
    version = rows[0]["version"] + 1 if rows else 1
    profile = OperatorProfileVersion(
        id=profile_id,
        version=version,
        operator_id=operator_id,
        capabilities=payload.capabilities,
        constraints=payload.constraints,
        delivery=delivery,
        commercial=commercial,
        approved_by=operator_id,
        created_at=datetime.now(UTC),
    )
    await OperatorRepository(engine).register_profile(
        profile, command_key=_id(profile_id, f"v{version}")
    )
    return profile_id, version


async def _artifact_row(request: Request, artifact_id: UUID):
    async with request.app.state.engine.connect() as connection:
        return (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == artifact_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )


@router.post("/experiments", response_model=CreateExperimentResponse, status_code=201)
async def create_experiment(
    request: Request, body: CreateExperimentRequest
) -> CreateExperimentResponse:
    operator_id: UUID = request.state.operator.id
    repository = ProductRecordsRepository(request.app.state.engine)
    experiment_id = _id(body.command_key, "experiment")
    workflow_id = _id(body.command_key, "workflow")
    agent_id = _id(body.command_key, "agent")
    brief_id = _id(body.command_key, "brief")
    seed_id = _id(body.command_key, "seed")
    cycle_id = _id(body.command_key, "cycle")
    async with request.app.state.engine.connect() as connection:
        existing = (
            (
                await connection.execute(
                    select(records.experiments)
                    .select_from(
                        records.experiments.join(
                            records.operator_profiles,
                            (
                                records.operator_profiles.c.id
                                == records.experiments.c.operator_profile_id
                            )
                            & (
                                records.operator_profiles.c.version
                                == records.experiments.c.operator_profile_version
                            ),
                        )
                    )
                    .where(
                        records.experiments.c.id == experiment_id,
                        records.operator_profiles.c.operator_id
                        == request.state.operator.id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
    if existing is not None:
        async with request.app.state.engine.connect() as connection:
            bound_profile = (
                (
                    await connection.execute(
                        select(records.operator_profiles).where(
                            records.operator_profiles.c.id
                            == existing["operator_profile_id"],
                            records.operator_profiles.c.version
                            == existing["operator_profile_version"],
                            records.operator_profiles.c.operator_id == operator_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        if (
            existing["name"] != body.name
            or bound_profile is None
            or bound_profile["capabilities"] != list(body.operator_profile.capabilities)
            or bound_profile["constraints"] != list(body.operator_profile.constraints)
            or bound_profile["delivery"]
            != DeliveryConstraints.model_validate(
                body.operator_profile.delivery.model_dump()
            ).model_dump(mode="json")
            or bound_profile["commercial"]
            != CommercialConstraints.model_validate(
                body.operator_profile.commercial.model_dump()
            ).model_dump(mode="json")
        ):
            raise HTTPException(409, "COMMAND_CONFLICT")
        detail = await _read_experiment(request, experiment_id)
        if detail is not None:
            if (
                detail["idea_seed"] != body.idea_seed
                or detail["brief"] != body.brief.artifact_payload()
            ):
                raise HTTPException(409, "COMMAND_CONFLICT")
            return CreateExperimentResponse(
                experiment_id=experiment_id,
                cycle_id=detail["cycle_id"],
                brief_artifact_id=brief_id,
                seed_artifact_id=seed_id,
            )
    try:
        if existing is None:
            profile_id, profile_version = await _profile(
                request, body.operator_profile, operator_id
            )
        else:
            profile_id, profile_version = (
                existing["operator_profile_id"],
                existing["operator_profile_version"],
            )
        async with request.app.state.engine.begin() as connection:
            for table, values in (
                (gov.experiments, {"id": experiment_id}),
                (gov.workflows, {"id": workflow_id, "experiment_id": experiment_id}),
                (gov.agents, {"id": agent_id, "workflow_id": workflow_id}),
            ):
                await connection.execute(
                    pg_insert(table).values(**values).on_conflict_do_nothing()
                )
        now = datetime.now(UTC)
        if existing is None:
            await repository.bind_roots(
                ProductExperiment(
                    id=experiment_id,
                    operator_profile_id=profile_id,
                    operator_profile_version=profile_version,
                    name=body.name,
                    created_at=now,
                ),
                ProductWorkflow(
                    id=workflow_id,
                    experiment_id=experiment_id,
                    role="IDEA_TO_RESEARCH",
                    created_at=now,
                ),
                ProductAgent(
                    id=agent_id,
                    workflow_id=workflow_id,
                    role="IDEA_DISCOVERY",
                    created_at=now,
                ),
                command_key=_id(body.command_key, "roots-command"),
            )
        brief_row = await _artifact_row(request, brief_id)
        if brief_row is None:
            await repository.append_artifact(
                ArtifactDraft(
                    id=brief_id,
                    logical_id=brief_id,
                    version=1,
                    experiment_id=experiment_id,
                    workflow_id=workflow_id,
                    agent_id=agent_id,
                    kind=ArtifactKind.EXPERIMENT_BRIEF,
                    payload=body.brief.artifact_payload(),
                    created_by=operator_id,
                    created_at=now,
                ),
                command_key=_id(body.command_key, "brief-command"),
            )
        elif brief_row["payload"] != body.brief.artifact_payload():
            raise HTTPException(409, "COMMAND_CONFLICT")
        seed_row = await _artifact_row(request, seed_id)
        if seed_row is None:
            seed = await repository.append_artifact(
                ArtifactDraft(
                    id=seed_id,
                    logical_id=seed_id,
                    version=1,
                    experiment_id=experiment_id,
                    workflow_id=workflow_id,
                    agent_id=agent_id,
                    kind=ArtifactKind.IDEA_SEED,
                    payload={"origin": "USER_SUPPLIED", "statement": body.idea_seed},
                    created_by=operator_id,
                    created_at=now,
                ),
                command_key=_id(body.command_key, "seed-command"),
            )
            seed_input = ArtifactInput.from_receipt(seed, role="SEED")
        elif seed_row["payload"] != {
            "origin": "USER_SUPPLIED",
            "statement": body.idea_seed,
        }:
            raise HTTPException(409, "COMMAND_CONFLICT")
        else:
            seed_input = ArtifactInput(
                artifact_id=seed_row["id"],
                kind=ArtifactKind.IDEA_SEED,
                version=seed_row["version"],
                content_hash=seed_row["content_hash"],
                role="SEED",
            )
        async with request.app.state.engine.connect() as connection:
            existing_cycle = (
                await connection.execute(
                    select(records.cycles.c.id).where(
                        records.cycles.c.experiment_id == experiment_id
                    )
                )
            ).scalar_one_or_none()
        if existing_cycle is None:
            cycle = await repository.create_cycle(
                experiment_id,
                seed=seed_input,
                command_key=_id(body.command_key, "cycle-command"),
            )
            cycle_id = cycle.id
        else:
            cycle_id = existing_cycle
    except ProductRecordsDenied as error:
        raise HTTPException(409, error.reason) from None
    return CreateExperimentResponse(
        experiment_id=experiment_id,
        cycle_id=cycle_id,
        brief_artifact_id=brief_id,
        seed_artifact_id=seed_id,
    )


async def _read_experiment(request: Request, experiment_id: UUID) -> dict | None:
    await _reconcile_stale_refinement(request, experiment_id)
    async with request.app.state.engine.connect() as connection:
        experiment = (
            (
                await connection.execute(
                    select(records.experiments)
                    .select_from(
                        records.experiments.join(
                            records.operator_profiles,
                            (
                                records.operator_profiles.c.id
                                == records.experiments.c.operator_profile_id
                            )
                            & (
                                records.operator_profiles.c.version
                                == records.experiments.c.operator_profile_version
                            ),
                        )
                    )
                    .where(
                        records.experiments.c.id == experiment_id,
                        records.operator_profiles.c.operator_id
                        == request.state.operator.id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if experiment is None:
            return None
        artifacts = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.experiment_id == experiment_id
                    )
                )
            )
            .mappings()
            .all()
        )
        cycle = (
            (
                await connection.execute(
                    select(records.cycles)
                    .where(records.cycles.c.experiment_id == experiment_id)
                    .order_by(records.cycles.c.ordinal.desc())
                )
            )
            .mappings()
            .first()
        )
        acceptance = (
            (
                await connection.execute(
                    select(records.idea_acceptances).where(
                        records.idea_acceptances.c.cycle_id == cycle["id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if cycle
            else None
        )
        latest = (
            (
                await connection.execute(
                    select(records.idea_refinements)
                    .where(records.idea_refinements.c.experiment_id == experiment_id)
                    .order_by(
                        records.idea_refinements.c.created_at.desc(),
                        records.idea_refinements.c.run_id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        run_outcome = (
            await connection.scalar(
                select(run_intents.c.outcome).where(
                    run_intents.c.idempotency_key == latest["run_id"]
                )
            )
            if latest
            else None
        )
    brief = next(
        (row for row in artifacts if row["kind"] == ArtifactKind.EXPERIMENT_BRIEF), None
    )
    seed = next(
        (row for row in artifacts if row["kind"] == ArtifactKind.IDEA_SEED), None
    )
    accepted = next(
        (
            row
            for row in artifacts
            if acceptance and row["id"] == acceptance["artifact_id"]
        ),
        None,
    )
    if brief is None or seed is None or cycle is None:
        return None
    return {
        "experiment_id": experiment_id,
        "name": experiment["name"],
        "state": "IDEA_ACCEPTED"
        if acceptance
        else "AWAITING_REVIEW"
        if latest and latest["state"] == "SUCCEEDED"
        else "REFINEMENT_FAILED"
        if latest and latest["state"] == "REFINEMENT_FAILED"
        else "REFINEMENT_BLOCKED"
        if latest and latest["state"] == "REFINEMENT_BLOCKED"
        else "REFINEMENT_IN_PROGRESS"
        if latest and latest["state"] == "RUNNING"
        else "AWAITING_REFINEMENT",
        "brief": brief["payload"],
        "idea_seed": seed["payload"]["statement"],
        "cycle_id": cycle["id"],
        "latest_run_id": latest["run_id"] if latest else None,
        "latest_outcome": run_outcome if latest else None,
        "advice_source": latest["advice_source"] if latest else None,
        "advice": SeededIdeaBriefAdvice.model_validate_json(
            json.dumps(latest["advice"])
        ).model_dump(mode="json", exclude={"schema_version"})
        if latest and latest["advice"]
        else None,
        "accepted_brief": accepted["payload"] if accepted else None,
    }


async def _reconcile_stale_refinement(request: Request, experiment_id: UUID) -> None:
    """Recover a dead RUNNING claim only after every live attribution has expired.

    L07 live timeouts are bounded to 3600 seconds plus 30 seconds. An extra
    minute ensures an old worker cannot pass the governed dispatch deadline.
    Any evidence of a call or an ambiguous run keeps the experiment blocked.
    """
    stale_before = datetime.now(UTC) - timedelta(seconds=3690)
    async with request.app.state.engine.begin() as connection:
        owned = await connection.scalar(
            select(records.experiments.c.id)
            .select_from(
                records.experiments.join(
                    records.operator_profiles,
                    (
                        records.operator_profiles.c.id
                        == records.experiments.c.operator_profile_id
                    )
                    & (
                        records.operator_profiles.c.version
                        == records.experiments.c.operator_profile_version
                    ),
                )
            )
            .where(
                records.experiments.c.id == experiment_id,
                records.operator_profiles.c.operator_id == request.state.operator.id,
            )
            .with_for_update(of=records.experiments)
        )
        if owned is None:
            return
        pending = (
            (
                await connection.execute(
                    select(records.idea_refinements)
                    .where(
                        records.idea_refinements.c.experiment_id == experiment_id,
                        records.idea_refinements.c.state == "RUNNING",
                        records.idea_refinements.c.created_at < stale_before,
                    )
                    .order_by(records.idea_refinements.c.created_at.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if pending is None:
            return
        call_id = await connection.scalar(
            select(gov.calls.c.id).where(
                gov.calls.c.idempotency_key == pending["run_id"],
                gov.calls.c.experiment_id == experiment_id,
                gov.calls.c.operation_id == pending["operation_id"],
            )
        )
        outcome = await connection.scalar(
            select(run_intents.c.outcome).where(
                run_intents.c.idempotency_key == pending["run_id"],
                run_intents.c.experiment_id == experiment_id,
                run_intents.c.operation_id == pending["operation_id"],
            )
        )
        safe_to_retry = call_id is None and outcome in (None, "READY")
        await connection.execute(
            update(records.idea_refinements)
            .where(
                records.idea_refinements.c.run_id == pending["run_id"],
                records.idea_refinements.c.state == "RUNNING",
            )
            .values(
                state="REFINEMENT_FAILED" if safe_to_retry else "REFINEMENT_BLOCKED",
                finished_at=datetime.now(UTC),
            )
        )


class ExperimentRuntimeStatus(StrictRequest):
    provider_mode: Literal["disabled", "fake", "live"]
    ready: bool


@router.get("/experiments/runtime", response_model=ExperimentRuntimeStatus)
async def experiment_runtime_status(request: Request) -> ExperimentRuntimeStatus:
    settings = request.app.state.settings
    return ExperimentRuntimeStatus(
        provider_mode=settings.provider_mode,
        ready=(
            settings.provider_mode == "fake" and settings.environment != "production"
        )
        or (
            settings.provider_mode == "live"
            and getattr(request.app.state, "idea_runtime_provider", None) is not None
        ),
    )


@router.get("/experiments/{experiment_id}")
async def get_experiment(request: Request, experiment_id: UUID) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise HTTPException(404, "EXPERIMENT_NOT_FOUND")
    return detail


class RefineRequest(StrictRequest):
    idempotency_key: UUID


class AcceptRequest(StrictRequest):
    run_id: UUID
    command_key: UUID


async def _claim_refinement(
    request: Request,
    *,
    experiment_id: UUID,
    cycle_id: UUID,
    run_id: UUID,
    operation_id: UUID,
    advice_source: str,
) -> None:
    """Serialize the check and RUNNING insert across API processes."""
    async with request.app.state.engine.begin() as connection:
        await connection.execute(
            select(records.experiments.c.id)
            .where(records.experiments.c.id == experiment_id)
            .with_for_update()
        )
        accepted = await connection.scalar(
            select(records.idea_acceptances.c.id).where(
                records.idea_acceptances.c.cycle_id == cycle_id
            )
        )
        if accepted is not None:
            raise HTTPException(409, "IDEA_ALREADY_ACCEPTED")
        latest = (
            (
                await connection.execute(
                    select(records.idea_refinements)
                    .where(records.idea_refinements.c.experiment_id == experiment_id)
                    .order_by(
                        records.idea_refinements.c.created_at.desc(),
                        records.idea_refinements.c.run_id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if latest is not None:
            if latest["run_id"] == run_id:
                raise HTTPException(409, "REFINEMENT_IN_PROGRESS")
            if latest["state"] == "RUNNING":
                raise HTTPException(409, "REFINEMENT_IN_PROGRESS")
            if latest["state"] == "SUCCEEDED":
                raise HTTPException(409, "REVIEW_PENDING")
            if latest["state"] == "REFINEMENT_BLOCKED":
                raise HTTPException(409, "REFINEMENT_RECONCILIATION_REQUIRED")
        seed_id = await connection.scalar(
            select(records.cycles.c.seed_artifact_id).where(
                records.cycles.c.id == cycle_id,
                records.cycles.c.experiment_id == experiment_id,
            )
        )
        if seed_id is None:
            raise HTTPException(409, "EXPERIMENT_NOT_READY")
        await connection.execute(
            records.idea_refinements.insert().values(
                run_id=run_id,
                experiment_id=experiment_id,
                cycle_id=cycle_id,
                seed_artifact_id=seed_id,
                operation_id=operation_id,
                state="RUNNING",
                advice_source=advice_source,
                created_at=datetime.now(UTC),
            )
        )


@router.post("/experiments/{experiment_id}/refine")
async def refine_experiment(
    request: Request, experiment_id: UUID, body: RefineRequest
) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise HTTPException(404, "EXPERIMENT_NOT_FOUND")
    if detail["state"] == "IDEA_ACCEPTED":
        raise HTTPException(409, "IDEA_ALREADY_ACCEPTED")
    if detail["state"] == "REFINEMENT_IN_PROGRESS":
        raise HTTPException(409, "REFINEMENT_IN_PROGRESS")
    if (
        detail["state"] == "REFINEMENT_BLOCKED"
        and body.idempotency_key != detail["latest_run_id"]
    ):
        raise HTTPException(409, "REFINEMENT_RECONCILIATION_REQUIRED")
    if (
        detail["state"] == "AWAITING_REVIEW"
        and body.idempotency_key != detail["latest_run_id"]
    ):
        raise HTTPException(409, "REVIEW_PENDING")
    settings = request.app.state.settings
    engine = request.app.state.engine
    async with engine.connect() as connection:
        existing = (
            (
                await connection.execute(
                    select(records.idea_refinements).where(
                        records.idea_refinements.c.run_id == body.idempotency_key
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        roots = (
            (
                await connection.execute(
                    select(
                        records.workflows.c.id, records.agents.c.id.label("agent_id")
                    )
                    .select_from(
                        records.workflows.join(
                            records.agents,
                            records.agents.c.workflow_id == records.workflows.c.id,
                        )
                    )
                    .where(records.workflows.c.experiment_id == experiment_id)
                )
            )
            .mappings()
            .first()
        )
    if existing is not None:
        if existing["experiment_id"] != experiment_id:
            raise HTTPException(409, "COMMAND_CONFLICT")
        if existing["state"] == "RUNNING":
            raise HTTPException(409, "REFINEMENT_IN_PROGRESS")
        durable_outcome = await OpenAIRunStore(engine).get(body.idempotency_key)
        return {
            "run_id": existing["run_id"],
            "outcome": durable_outcome.outcome
            if durable_outcome is not None
            else "REFINEMENT_FAILED",
            "state": "AWAITING_REVIEW"
            if existing["state"] == "SUCCEEDED"
            else existing["state"],
            "advice_source": existing["advice_source"],
            "advice": SeededIdeaBriefAdvice.model_validate_json(
                json.dumps(existing["advice"])
            ).model_dump(mode="json", exclude={"schema_version"})
            if existing["advice"]
            else None,
        }
    if settings.provider_mode == "disabled" or (
        settings.provider_mode == "fake" and settings.environment == "production"
    ):
        raise HTTPException(409, "REFINEMENT_UNAVAILABLE")
    if roots is None:
        raise HTTPException(409, "EXPERIMENT_NOT_READY")
    claimed_operation_id: UUID | None = None
    try:
        runtime_args = {
            "experiment_id": experiment_id,
            "workflow_id": roots["id"],
            "agent_id": roots["agent_id"],
            "operator_id": request.state.operator.id,
            "run_id": body.idempotency_key,
            "budget_usd": Decimal(detail["brief"]["budget_usd"]),
        }
        if settings.provider_mode == "fake":
            service, attribution = await provision_recorded_seeded_runtime(
                engine, **runtime_args
            )
            advice_source = "RECORDED_FAKE"
        else:
            provider = getattr(request.app.state, "idea_runtime_provider", None)
            if provider is None:
                raise HTTPException(409, "LIVE_CONFIG_REQUIRED")
            service, attribution, advice_source = await provider(engine, **runtime_args)
        await _claim_refinement(
            request,
            experiment_id=experiment_id,
            cycle_id=detail["cycle_id"],
            run_id=body.idempotency_key,
            operation_id=attribution.operation_run_id,
            advice_source=advice_source,
        )
        claimed_operation_id = attribution.operation_run_id
        execution = await service.refine_cycle(
            attribution,
            cycle_id=detail["cycle_id"],
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=body.idempotency_key,
        )
        advice = execution.output
        success = execution.outcome is OpenAIRunOutcome.SUCCEEDED and isinstance(
            advice, SeededIdeaBriefAdvice
        )
        payload = advice.model_dump(mode="json") if success and advice else None
        if success and payload:
            durable_run = await OpenAIRunStore(engine).get(body.idempotency_key)
            if durable_run is None or durable_run.output_hash != sha256(
                canonical_json(payload)
            ):
                success = False
                payload = None
        async with engine.begin() as connection:
            finalized = await connection.execute(
                update(records.idea_refinements)
                .where(
                    records.idea_refinements.c.run_id == body.idempotency_key,
                    records.idea_refinements.c.experiment_id == experiment_id,
                    records.idea_refinements.c.operation_id == claimed_operation_id,
                    records.idea_refinements.c.state == "RUNNING",
                )
                .values(
                    state="SUCCEEDED" if success else "REFINEMENT_BLOCKED",
                    advice=payload if payload else null(),
                    output_hash=sha256(canonical_json(payload)) if payload else None,
                    finished_at=datetime.now(UTC),
                )
            )
            if finalized.rowcount != 1:
                raise HTTPException(409, "REFINEMENT_RECONCILIATION_REQUIRED")
        return {
            "run_id": body.idempotency_key,
            "outcome": execution.outcome,
            "state": "AWAITING_REVIEW" if success else "REFINEMENT_BLOCKED",
            "advice_source": advice_source,
            "advice": advice.model_dump(mode="json", exclude={"schema_version"})
            if success and advice
            else None,
        }
    except HTTPException:
        raise
    except Exception as error:
        # No output can be accepted after an interrupted or denied run.
        if claimed_operation_id is not None:
            async with engine.begin() as connection:
                await connection.execute(
                    update(records.idea_refinements)
                    .where(
                        records.idea_refinements.c.run_id == body.idempotency_key,
                        records.idea_refinements.c.experiment_id == experiment_id,
                        records.idea_refinements.c.operation_id == claimed_operation_id,
                        records.idea_refinements.c.state == "RUNNING",
                    )
                    .values(state="REFINEMENT_BLOCKED", finished_at=datetime.now(UTC))
                )
        raise HTTPException(409, "REFINEMENT_UNAVAILABLE") from error


@router.post("/experiments/{experiment_id}/accept")
async def accept_experiment_idea(
    request: Request, experiment_id: UUID, body: AcceptRequest
) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise HTTPException(404, "EXPERIMENT_NOT_FOUND")
    engine = request.app.state.engine
    async with engine.connect() as connection:
        reviewed = (
            (
                await connection.execute(
                    select(records.idea_refinements).where(
                        records.idea_refinements.c.run_id == body.run_id,
                        records.idea_refinements.c.experiment_id == experiment_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        seed = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == reviewed["seed_artifact_id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if reviewed
            else None
        )
        workflow = (
            (
                await connection.execute(
                    select(
                        records.workflows.c.id, records.agents.c.id.label("agent_id")
                    )
                    .select_from(
                        records.workflows.join(
                            records.agents,
                            records.agents.c.workflow_id == records.workflows.c.id,
                        )
                    )
                    .where(records.workflows.c.experiment_id == experiment_id)
                )
            )
            .mappings()
            .first()
        )
    if (
        reviewed is None
        or reviewed["state"] != "SUCCEEDED"
        or reviewed["cycle_id"] != detail["cycle_id"]
        or body.run_id != detail["latest_run_id"]
        or seed is None
        or workflow is None
    ):
        raise HTTPException(409, "REFINEMENT_NOT_SUCCESSFUL")
    advice = SeededIdeaBriefAdvice.model_validate_json(json.dumps(reviewed["advice"]))
    if advice.material_pivot:
        raise HTTPException(409, "MATERIAL_PIVOT_REQUIRES_APPROVAL")
    original_intent = " ".join(seed["payload"]["statement"].split()).casefold()
    proposed_intent = " ".join(advice.core_intent.split()).casefold()
    if proposed_intent != original_intent and not proposed_intent.startswith(
        original_intent + " "
    ):
        raise HTTPException(409, "IDEA_VALIDATION_FAILED")
    repository = ProductRecordsRepository(engine)
    brief_id = _id(body.command_key, "accepted-idea-brief")
    payload = {
        key: getattr(advice, key)
        for key in ("title", "customer", "problem", "core_intent", "material_pivot")
    }
    existing_artifact = await _artifact_row(request, brief_id)
    if existing_artifact is not None and (
        existing_artifact["experiment_id"] != experiment_id
        or existing_artifact["workflow_id"] != workflow["id"]
        or existing_artifact["agent_id"] != workflow["agent_id"]
        or existing_artifact["operation_id"] != reviewed["operation_id"]
        or existing_artifact["kind"] != ArtifactKind.IDEA_BRIEF
        or existing_artifact["payload"] != payload
        or existing_artifact["created_by"] != request.state.operator.id
    ):
        raise HTTPException(409, "COMMAND_CONFLICT")
    if detail["state"] == "IDEA_ACCEPTED":
        async with engine.connect() as connection:
            accepted = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == detail["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
        if (
            existing_artifact is not None
            and accepted["artifact_id"] == brief_id
            and accepted["accepted_by"] == request.state.operator.id
        ):
            return {
                "experiment_id": experiment_id,
                "idea_brief_artifact_id": brief_id,
                "acceptance_id": accepted["id"],
                "state": "IDEA_ACCEPTED",
            }
        raise HTTPException(409, "IDEA_ALREADY_ACCEPTED")
    try:
        artifact = await repository.append_artifact(
            ArtifactDraft(
                id=brief_id,
                logical_id=brief_id,
                version=1,
                experiment_id=experiment_id,
                workflow_id=workflow["id"],
                agent_id=workflow["agent_id"],
                operation_id=reviewed["operation_id"],
                kind=ArtifactKind.IDEA_BRIEF,
                payload=payload,
                created_by=request.state.operator.id,
                created_at=existing_artifact["created_at"]
                if existing_artifact is not None
                else datetime.now(UTC),
            ),
            inputs=(
                ArtifactInput(
                    artifact_id=seed["id"],
                    kind=ArtifactKind.IDEA_SEED,
                    version=seed["version"],
                    content_hash=seed["content_hash"],
                    role="SEED",
                ),
            ),
            command_key=_id(body.command_key, "accepted-brief-command"),
        )
        acceptance = await repository.accept_idea(
            detail["cycle_id"],
            ArtifactInput.from_receipt(artifact, role="ACCEPTED_IDEA"),
            accepted_by=request.state.operator.id,
            command_key=_id(body.command_key, "idea-acceptance-command"),
        )
    except ProductRecordsDenied as error:
        raise HTTPException(409, error.reason) from None
    return {
        "experiment_id": experiment_id,
        "idea_brief_artifact_id": artifact.artifact_id,
        "acceptance_id": acceptance.id,
        "state": "IDEA_ACCEPTED",
    }
