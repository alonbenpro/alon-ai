"""Operator-owned, user-seeded experiment creation and Idea review."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import null, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from alon_ai.accounting import schema as gov
from alon_ai.api.recorded_idea_runtime import provision_recorded_seeded_runtime
from alon_ai.openai_runtime.contract import RoutingFacts, canonical_json, sha256
from alon_ai.openai_runtime.idea import (
    IdeaCandidateSetAdvice,
    LegacyIdeaBriefAdvice,
    ReturnedIdeaBriefAdvice,
    SeededIdeaBriefAdvice,
    SelectedCandidateIdeaBriefAdvice,
)
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


def _read_persisted_advice(model, payload: object) -> dict:
    """Read historical advice without relaxing the current provider contract."""
    raw = json.dumps(payload)
    for candidate in (
        model,
        SeededIdeaBriefAdvice,
        SelectedCandidateIdeaBriefAdvice,
    ):
        try:
            return candidate.model_validate_json(raw).model_dump(
                mode="json", exclude={"schema_version"}
            )
        except ValidationError:
            continue
    return LegacyIdeaBriefAdvice.model_validate_json(raw).model_dump(
        mode="json", exclude={"schema_version"}
    )


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
    idea_seed: str | None = Field(default=None, min_length=1, max_length=4000)
    brief: ExperimentBriefInput
    operator_profile: OperatorProfileInput
    command_key: UUID

    @field_validator("name", "idea_seed")
    @classmethod
    def not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("required text is blank")
        return value


class CreateExperimentResponse(StrictRequest):
    experiment_id: UUID
    cycle_id: UUID | None
    brief_artifact_id: UUID
    seed_artifact_id: UUID | None
    state: Literal["AWAITING_REFINEMENT", "AWAITING_DISCOVERY"]


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
                seed_artifact_id=seed_id if body.idea_seed is not None else None,
                state="AWAITING_REFINEMENT"
                if body.idea_seed is not None
                else "AWAITING_DISCOVERY",
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
        seed_input: ArtifactInput | None = None
        if body.idea_seed is not None:
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
                        payload={
                            "origin": "USER_SUPPLIED",
                            "statement": body.idea_seed,
                        },
                        created_by=operator_id,
                        created_at=now,
                    ),
                    command_key=_id(body.command_key, "seed-command"),
                )
                seed_input = ArtifactInput.from_receipt(seed, role="SEED")
            else:
                if seed_row["payload"] != {
                    "origin": "USER_SUPPLIED",
                    "statement": body.idea_seed,
                }:
                    raise HTTPException(409, "COMMAND_CONFLICT")
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
        if body.idea_seed is None:
            if existing_cycle is not None:
                raise HTTPException(409, "COMMAND_CONFLICT")
            cycle_id = None
        elif existing_cycle is None:
            assert seed_input is not None
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
        seed_artifact_id=seed_id if body.idea_seed is not None else None,
        state="AWAITING_REFINEMENT"
        if body.idea_seed is not None
        else "AWAITING_DISCOVERY",
    )


async def _read_experiment(request: Request, experiment_id: UUID) -> dict | None:
    await _reconcile_stale_refinement(request, experiment_id)
    await _reconcile_stale_discovery(request, experiment_id)
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
                    .where(
                        records.idea_refinements.c.experiment_id == experiment_id,
                        records.idea_refinements.c.cycle_id == cycle["id"],
                    )
                    .order_by(
                        records.idea_refinements.c.created_at.desc(),
                        records.idea_refinements.c.run_id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
            if cycle
            else None
        )
        discovery = (
            (
                await connection.execute(
                    select(records.idea_discoveries)
                    .where(records.idea_discoveries.c.experiment_id == experiment_id)
                    .order_by(
                        records.idea_discoveries.c.created_at.desc(),
                        records.idea_discoveries.c.run_id.desc(),
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
        discovery_outcome = (
            await connection.scalar(
                select(run_intents.c.outcome).where(
                    run_intents.c.idempotency_key == discovery["run_id"]
                )
            )
            if discovery
            else None
        )
        returned = (
            (
                await connection.execute(
                    select(records.returns).where(
                        records.returns.c.to_cycle_id == cycle["id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if cycle and cycle["purpose"] == "SAME_INTENT_RETURN"
            else None
        )
        return_context_rows = None
        if returned is not None:
            return_context_rows = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id.in_(
                                [
                                    returned["idea_artifact_id"],
                                    returned["feedback_artifact_id"],
                                ]
                            )
                        )
                    )
                )
                .mappings()
                .all()
            )
        return_verdict = (
            (
                await connection.execute(
                    select(records.verdicts).where(
                        records.verdicts.c.id == returned["verdict_id"]
                    )
                )
            )
            .mappings()
            .one()
            if returned is not None
            else None
        )
        available_verdict = (
            (
                await connection.execute(
                    select(records.verdicts)
                    .where(
                        records.verdicts.c.experiment_id == experiment_id,
                        records.verdicts.c.cycle_id == cycle["id"],
                        records.verdicts.c.verdict == "REFINE_SAME_IDEA",
                    )
                    .order_by(records.verdicts.c.committed_at.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
            if cycle and acceptance and cycle["purpose"] != "SAME_INTENT_RETURN"
            else None
        )
        available_feedback_rows = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.experiment_id == experiment_id,
                        records.artifacts.c.kind
                        == ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
                    )
                )
            )
            .mappings()
            .all()
            if available_verdict is not None
            else []
        )
        return_block = (
            (
                await connection.execute(
                    select(records.research_return_blocks)
                    .where(
                        records.research_return_blocks.c.experiment_id == experiment_id,
                        records.research_return_blocks.c.cycle_id == cycle["id"],
                        records.research_return_blocks.c.return_kind == "SAME_INTENT",
                    )
                    .order_by(records.research_return_blocks.c.created_at.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
            if cycle
            else None
        )
        cycle_state = (
            await connection.scalar(
                select(records.cycle_states.c.state).where(
                    records.cycle_states.c.cycle_id == cycle["id"],
                    records.cycle_states.c.experiment_id == experiment_id,
                )
            )
            if cycle
            else None
        )
        managed_return = (
            await connection.scalar(
                select(records.cycle_transitions.c.id)
                .join(
                    records.commands,
                    records.commands.c.id == records.cycle_transitions.c.command_id,
                )
                .where(
                    records.cycle_transitions.c.verdict_id == available_verdict["id"],
                    records.commands.c.kind == "COMMIT_MARKET_RESEARCH_OUTCOME",
                )
            )
            if available_verdict is not None
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
    return_context = None
    async with request.app.state.engine.connect() as connection:
        lineage_rows = (
            (
                await connection.execute(
                    select(records.returns)
                    .where(
                        records.returns.c.experiment_id == experiment_id,
                        records.returns.c.kind == "SAME_INTENT",
                    )
                    .order_by(records.returns.c.ordinal)
                )
            )
            .mappings()
            .all()
        )
    lineage_payload = [
        {
            "return_id": row["id"],
            "ordinal": row["ordinal"],
            "from_cycle_id": row["from_cycle_id"],
            "to_cycle_id": row["to_cycle_id"],
            "verdict_id": row["verdict_id"],
            "prior_brief_artifact_id": row["idea_artifact_id"],
            "feedback_artifact_id": row["feedback_artifact_id"],
        }
        for row in lineage_rows
    ]
    if returned is not None and return_context_rows is not None:
        assert return_verdict is not None
        prior = next(
            row
            for row in return_context_rows
            if row["id"] == returned["idea_artifact_id"]
        )
        feedback = next(
            row
            for row in return_context_rows
            if row["id"] == returned["feedback_artifact_id"]
        )
        return_context = {
            "return_id": returned["id"],
            "ordinal": returned["ordinal"],
            "from_cycle_id": returned["from_cycle_id"],
            "to_cycle_id": returned["to_cycle_id"],
            "verdict_id": returned["verdict_id"],
            "research_cycle_id": returned["from_cycle_id"],
            "prior_brief": {
                "artifact_id": prior["id"],
                "version": prior["version"],
                "content_hash": prior["content_hash"],
                "payload": prior["payload"],
            },
            "feedback": {
                "artifact_id": feedback["id"],
                "version": feedback["version"],
                "content_hash": feedback["content_hash"],
                "payload": feedback["payload"],
                "failed_dimensions": feedback["payload"].get("failed_dimensions", []),
            },
            "evidence": {
                "report_artifact_id": return_verdict["report_artifact_id"],
                "recommendation_artifact_id": return_verdict[
                    "recommendation_artifact_id"
                ],
            },
            "return_lineage": lineage_payload,
        }
    return_available = None
    return_review = (
        {
            "reason_code": return_block["reason_code"],
            "verdict_id": return_block["verdict_id"],
            "research_cycle_id": return_block["cycle_id"],
        }
        if return_block is not None
        else None
    )
    if (
        available_verdict is not None
        and acceptance is not None
        and cycle_state == "MARKET_RESEARCH"
        and managed_return is None
        and return_review is None
    ):
        matching = []
        async with request.app.state.engine.connect() as connection:
            for feedback in available_feedback_rows:
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
                                select(records.artifact_links).where(
                                    records.artifact_links.c.consumer_id
                                    == feedback["id"]
                                )
                            )
                        )
                        .mappings()
                        .all()
                    )
                }
                if {
                    (
                        acceptance["artifact_id"],
                        acceptance["artifact_kind"],
                        acceptance["artifact_version"],
                        acceptance["artifact_hash"],
                        "ACCEPTED_IDEA",
                    ),
                    (
                        available_verdict["report_artifact_id"],
                        available_verdict["report_kind"],
                        available_verdict["report_version"],
                        available_verdict["report_hash"],
                        "REPORT",
                    ),
                    (
                        available_verdict["recommendation_artifact_id"],
                        available_verdict["recommendation_kind"],
                        available_verdict["recommendation_version"],
                        available_verdict["recommendation_hash"],
                        "RECOMMENDATION",
                    ),
                } != links:
                    continue
                if set(feedback["payload"]) != {
                    "preserve",
                    "change",
                    "failed_dimensions",
                    "research_questions",
                }:
                    continue
                if not await connection.scalar(
                    select(records.artifact_dispositions.c.id).where(
                        records.artifact_dispositions.c.artifact_id == feedback["id"],
                        records.artifact_dispositions.c.disposition == "ACCEPTED",
                    )
                ):
                    continue
                if await connection.scalar(
                    select(records.artifacts.c.id).where(
                        records.artifacts.c.logical_id == feedback["logical_id"],
                        records.artifacts.c.version > feedback["version"],
                    )
                ) or await connection.scalar(
                    select(records.artifact_dispositions.c.id).where(
                        records.artifact_dispositions.c.artifact_id == feedback["id"],
                        records.artifact_dispositions.c.disposition == "SUPERSEDED",
                    )
                ):
                    continue
                if len(feedback["payload"]["failed_dimensions"]) != len(
                    set(feedback["payload"]["failed_dimensions"])
                ):
                    continue
                if all(
                    isinstance(value, str) and value.strip()
                    for field in (
                        "preserve",
                        "change",
                        "failed_dimensions",
                        "research_questions",
                    )
                    for value in feedback["payload"][field]
                ):
                    matching.append(feedback)
        if len(matching) == 1:
            feedback = matching[0]
            prior = next(
                row for row in artifacts if row["id"] == acceptance["artifact_id"]
            )
            return_available = {
                "verdict_id": available_verdict["id"],
                "research_cycle_id": cycle["id"],
                "prior_brief": {
                    "artifact_id": prior["id"],
                    "version": prior["version"],
                    "content_hash": prior["content_hash"],
                    "payload": prior["payload"],
                },
                "feedback": {
                    "artifact_id": feedback["id"],
                    "version": feedback["version"],
                    "content_hash": feedback["content_hash"],
                    "payload": feedback["payload"],
                    "failed_dimensions": feedback["payload"].get(
                        "failed_dimensions", []
                    ),
                },
                "evidence": {
                    "report_artifact_id": available_verdict["report_artifact_id"],
                    "recommendation_artifact_id": available_verdict[
                        "recommendation_artifact_id"
                    ],
                },
                "return_lineage": lineage_payload,
            }
    if brief is None:
        return None
    mode = "USER_SEEDED_REFINEMENT" if seed else "SYSTEM_DISCOVERY"
    candidate_advice = (
        IdeaCandidateSetAdvice.model_validate_json(json.dumps(discovery["advice"]))
        if discovery and discovery["state"] == "SUCCEEDED" and discovery["advice"]
        else None
    )
    candidates = (
        [
            {
                "artifact_id": artifact_id,
                **candidate.model_dump(
                    mode="json", exclude={"schema_version", "grounding_refs"}
                ),
            }
            for artifact_id, candidate in zip(
                discovery["candidate_ids"], candidate_advice.candidates, strict=True
            )
        ]
        if candidate_advice
        else []
    )
    advice_model = (
        ReturnedIdeaBriefAdvice
        if cycle and cycle["purpose"] == "SAME_INTENT_RETURN"
        else SeededIdeaBriefAdvice
        if mode == "USER_SEEDED_REFINEMENT"
        else SelectedCandidateIdeaBriefAdvice
    )
    return {
        "experiment_id": experiment_id,
        "name": experiment["name"],
        "mode": mode,
        "state": "RETURN_REVIEW_REQUIRED"
        if return_review is not None or return_available is not None
        else "IDEA_ACCEPTED"
        if acceptance
        else "AWAITING_REVIEW"
        if latest and latest["state"] == "SUCCEEDED"
        else "REFINEMENT_FAILED"
        if latest and latest["state"] == "REFINEMENT_FAILED"
        else "REFINEMENT_BLOCKED"
        if latest and latest["state"] == "REFINEMENT_BLOCKED"
        else "REFINEMENT_IN_PROGRESS"
        if latest and latest["state"] == "RUNNING"
        else "AWAITING_REFINEMENT"
        if cycle
        else "AWAITING_SELECTION"
        if discovery and discovery["state"] == "SUCCEEDED"
        else "DISCOVERY_BLOCKED"
        if discovery and discovery["state"] == "DISCOVERY_BLOCKED"
        else "DISCOVERY_FAILED"
        if discovery and discovery["state"] == "DISCOVERY_FAILED"
        else "DISCOVERY_IN_PROGRESS"
        if discovery and discovery["state"] == "RUNNING"
        else "AWAITING_DISCOVERY",
        "brief": brief["payload"],
        "idea_seed": seed["payload"]["statement"] if seed else None,
        "cycle_id": cycle["id"] if cycle else None,
        "cycle_purpose": cycle["purpose"] if cycle else None,
        "return_context": return_context,
        "return_available": return_available,
        "return_review": return_review,
        "candidates": candidates,
        "selected_candidate_artifact_id": cycle["seed_artifact_id"]
        if cycle and mode == "SYSTEM_DISCOVERY"
        else None,
        "latest_run_id": latest["run_id"]
        if latest
        else discovery["run_id"]
        if discovery
        else None,
        "latest_outcome": run_outcome if latest else discovery_outcome,
        "advice_source": latest["advice_source"]
        if latest
        else discovery["advice_source"]
        if discovery
        else None,
        "advice": _read_persisted_advice(advice_model, latest["advice"])
        if latest and latest["advice"]
        else None,
        "accepted_brief": accepted["payload"] if accepted else None,
        "retry_safe": await _confirmed_safe_retry(
            request.app.state.engine,
            latest["run_id"] if latest else discovery["run_id"] if discovery else None,
            latest["operation_id"]
            if latest
            else discovery["operation_id"]
            if discovery
            else None,
            experiment_id,
        )
        if (latest and latest["state"] == "REFINEMENT_FAILED")
        or (not latest and discovery and discovery["state"] == "DISCOVERY_FAILED")
        else False,
    }


async def _confirmed_safe_retry(
    engine, run_id: UUID | None, operation_id: UUID | None, experiment_id: UUID
) -> bool:
    """A fresh key is allowed only after immutable terminal and call-ledger proof."""
    if run_id is None or operation_id is None:
        return False
    async with engine.connect() as connection:
        intent = (
            (
                await connection.execute(
                    select(run_intents).where(
                        run_intents.c.idempotency_key == run_id,
                        run_intents.c.experiment_id == experiment_id,
                        run_intents.c.operation_id == operation_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        call = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.idempotency_key == run_id,
                        gov.calls.c.experiment_id == experiment_id,
                        gov.calls.c.operation_id == operation_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
    return _terminal_failure_settled(intent, call)


def _terminal_failure_settled(intent, call) -> bool:
    """A missing call or intent cannot prove that the original owner has stopped."""
    if intent is None or call is None:
        return False
    if (
        intent["outcome"]
        not in {
            OpenAIRunOutcome.FAILED,
            OpenAIRunOutcome.REFUSED,
            OpenAIRunOutcome.SCHEMA_MISMATCH,
            OpenAIRunOutcome.INCOMPLETE,
            OpenAIRunOutcome.TIMEOUT,
            OpenAIRunOutcome.CANCELLED,
        }
        or intent["finished_at"] is None
    ):
        return False
    return intent["call_id"] == call["id"] and call["state"] == "FINAL"


async def _reconcile_stale_discovery(request: Request, experiment_id: UUID) -> None:
    stale_before = datetime.now(UTC) - timedelta(seconds=3690)
    async with request.app.state.engine.begin() as connection:
        owned = await connection.scalar(
            select(records.experiments.c.id)
            .select_from(
                records.experiments.join(
                    records.operator_profiles,
                    (
                        records.experiments.c.operator_profile_id
                        == records.operator_profiles.c.id
                    )
                    & (
                        records.experiments.c.operator_profile_version
                        == records.operator_profiles.c.version
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
                    select(records.idea_discoveries).where(
                        records.idea_discoveries.c.experiment_id == experiment_id,
                        records.idea_discoveries.c.state == "RUNNING",
                        records.idea_discoveries.c.created_at < stale_before,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if pending is None:
            return
        call = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.idempotency_key == pending["run_id"],
                        gov.calls.c.experiment_id == experiment_id,
                        gov.calls.c.operation_id == pending["operation_id"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        intent = (
            (
                await connection.execute(
                    select(run_intents).where(
                        run_intents.c.idempotency_key == pending["run_id"],
                        run_intents.c.experiment_id == experiment_id,
                        run_intents.c.operation_id == pending["operation_id"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        safe = _terminal_failure_settled(intent, call)
        await connection.execute(
            update(records.idea_discoveries)
            .where(
                records.idea_discoveries.c.run_id == pending["run_id"],
                records.idea_discoveries.c.state == "RUNNING",
            )
            .values(
                state="DISCOVERY_FAILED" if safe else "DISCOVERY_BLOCKED",
                finished_at=datetime.now(UTC),
            )
        )


async def _reconcile_stale_refinement(request: Request, experiment_id: UUID) -> None:
    """Resolve stale claims only from settled terminal evidence; otherwise block."""
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
        call = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.idempotency_key == pending["run_id"],
                        gov.calls.c.experiment_id == experiment_id,
                        gov.calls.c.operation_id == pending["operation_id"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        intent = (
            (
                await connection.execute(
                    select(run_intents).where(
                        run_intents.c.idempotency_key == pending["run_id"],
                        run_intents.c.experiment_id == experiment_id,
                        run_intents.c.operation_id == pending["operation_id"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        safe_to_retry = _terminal_failure_settled(intent, call)
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


class ReturnFeedbackInput(StrictRequest):
    artifact_id: UUID
    kind: Literal[ArtifactKind.RESEARCH_FEEDBACK_BRIEF]
    version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: Literal["RESEARCH_FEEDBACK"]

    def artifact(self) -> ArtifactInput:
        return ArtifactInput(
            artifact_id=self.artifact_id,
            kind=self.kind,
            version=self.version,
            content_hash=self.content_hash,
            role=self.role,
        )


class StartReturnRefinementRequest(StrictRequest):
    verdict_id: UUID
    feedback: ReturnFeedbackInput
    command_key: UUID


@router.post("/experiments/{experiment_id}/returns/refine")
async def start_return_refinement(
    request: Request, experiment_id: UUID, body: StartReturnRefinementRequest
) -> dict:
    """Claim an already-committed L08 feedback return; no model call occurs here."""
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise HTTPException(404, "EXPERIMENT_NOT_FOUND")
    async with request.app.state.engine.connect() as connection:
        owned_verdict = await connection.scalar(
            select(records.verdicts.c.id).where(
                records.verdicts.c.id == body.verdict_id,
                records.verdicts.c.experiment_id == experiment_id,
            )
        )
    if owned_verdict is None:
        raise HTTPException(409, "FORGED_RESEARCH_FEEDBACK")
    try:
        receipt = await ProductRecordsRepository(
            request.app.state.engine
        ).start_same_intent_refinement_return(
            body.verdict_id,
            feedback=body.feedback.artifact(),
            command_key=body.command_key,
        )
    except ProductRecordsDenied as error:
        raise HTTPException(409, error.reason) from None
    if receipt.experiment_id != experiment_id:
        raise HTTPException(404, "EXPERIMENT_NOT_FOUND")
    return {
        "experiment_id": experiment_id,
        "cycle_id": receipt.id,
        "state": "AWAITING_REFINEMENT"
        if receipt.outcome == "STARTED"
        else "RETURN_REVIEW_REQUIRED",
        "reason_code": receipt.reason_code,
    }


@router.post("/experiments/{experiment_id}/discover")
async def discover_experiment(
    request: Request, experiment_id: UUID, body: RefineRequest
) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise HTTPException(404, "EXPERIMENT_NOT_FOUND")
    if detail["mode"] != "SYSTEM_DISCOVERY":
        raise HTTPException(409, "DISCOVERY_MODE_REQUIRED")
    if detail["cycle_id"] is not None:
        raise HTTPException(409, "CANDIDATE_ALREADY_SELECTED")
    engine = request.app.state.engine
    async with engine.connect() as connection:
        prior = (
            (
                await connection.execute(
                    select(records.idea_discoveries)
                    .where(records.idea_discoveries.c.experiment_id == experiment_id)
                    .order_by(
                        records.idea_discoveries.c.created_at.desc(),
                        records.idea_discoveries.c.run_id.desc(),
                    )
                    .limit(1)
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
    if prior is not None:
        if prior["run_id"] != body.idempotency_key:
            if prior["state"] != "DISCOVERY_FAILED" or not detail["retry_safe"]:
                raise HTTPException(
                    409,
                    "CANDIDATE_REVIEW_PENDING"
                    if prior["state"] == "SUCCEEDED"
                    else "DISCOVERY_RECONCILIATION_REQUIRED",
                )
        elif prior["state"] == "SUCCEEDED":
            snapshot = await _read_experiment(request, experiment_id)
            if snapshot is None:
                raise HTTPException(409, "DISCOVERY_RECONCILIATION_REQUIRED")
            return {
                "run_id": body.idempotency_key,
                "outcome": "SUCCEEDED",
                "state": "AWAITING_SELECTION",
                "candidates": snapshot["candidates"],
            }
        elif prior["state"] == "RUNNING":
            raise HTTPException(409, "DISCOVERY_IN_PROGRESS")
        else:
            return {
                "run_id": body.idempotency_key,
                "outcome": await _run_outcome(engine, body.idempotency_key),
                "state": prior["state"],
                "candidates": [],
            }
    settings = request.app.state.settings
    if settings.provider_mode == "disabled" or (
        settings.provider_mode == "fake" and settings.environment == "production"
    ):
        raise HTTPException(409, "DISCOVERY_UNAVAILABLE")
    if roots is None:
        raise HTTPException(409, "EXPERIMENT_NOT_READY")
    runtime_args = {
        "experiment_id": experiment_id,
        "workflow_id": roots["id"],
        "agent_id": roots["agent_id"],
        "operator_id": request.state.operator.id,
        "run_id": body.idempotency_key,
        "budget_usd": Decimal(detail["brief"]["budget_usd"]),
    }
    claimed_operation_id: UUID | None = None
    try:
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
        async with engine.begin() as connection:
            await connection.execute(
                select(records.experiments.c.id)
                .where(records.experiments.c.id == experiment_id)
                .with_for_update()
            )
            latest_run = await connection.scalar(
                select(records.idea_discoveries.c.run_id)
                .where(records.idea_discoveries.c.experiment_id == experiment_id)
                .order_by(
                    records.idea_discoveries.c.created_at.desc(),
                    records.idea_discoveries.c.run_id.desc(),
                )
                .limit(1)
            )
            if latest_run != (prior["run_id"] if prior else None):
                raise HTTPException(409, "DISCOVERY_IN_PROGRESS")
            await connection.execute(
                records.idea_discoveries.insert().values(
                    run_id=body.idempotency_key,
                    experiment_id=experiment_id,
                    operation_id=attribution.operation_run_id,
                    state="RUNNING",
                    advice_source=advice_source,
                    created_at=datetime.now(UTC),
                )
            )
        claimed_operation_id = attribution.operation_run_id
        execution = await service.discover_system(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=body.idempotency_key,
        )
        advice = (
            execution.output
            if isinstance(execution.output, IdeaCandidateSetAdvice)
            else None
        )
        success = execution.outcome is OpenAIRunOutcome.SUCCEEDED and advice is not None
        payload = (
            advice.model_dump(mode="json") if success and advice is not None else None
        )
        durable = await OpenAIRunStore(engine).get(body.idempotency_key)
        if (
            not success
            or durable is None
            or durable.output_hash != sha256(canonical_json(payload))
        ):
            retry_safe = await _confirmed_safe_retry(
                engine,
                body.idempotency_key,
                attribution.operation_run_id,
                experiment_id,
            )
            async with engine.begin() as connection:
                await connection.execute(
                    update(records.idea_discoveries)
                    .where(
                        records.idea_discoveries.c.run_id == body.idempotency_key,
                        records.idea_discoveries.c.state == "RUNNING",
                    )
                    .values(
                        state="DISCOVERY_FAILED" if retry_safe else "DISCOVERY_BLOCKED",
                        finished_at=datetime.now(UTC),
                    )
                )
            return {
                "run_id": body.idempotency_key,
                "outcome": execution.outcome,
                "state": "DISCOVERY_FAILED" if retry_safe else "DISCOVERY_BLOCKED",
                "candidates": [],
            }
        repository = ProductRecordsRepository(engine)
        assert advice is not None
        candidate_ids = []
        for index, candidate in enumerate(advice.candidates):
            candidate_id = _id(body.idempotency_key, f"candidate-{index}")
            receipt = await repository.append_artifact(
                ArtifactDraft(
                    id=candidate_id,
                    logical_id=candidate_id,
                    version=1,
                    experiment_id=experiment_id,
                    workflow_id=roots["id"],
                    agent_id=roots["agent_id"],
                    operation_id=attribution.operation_run_id,
                    kind=ArtifactKind.IDEA_CANDIDATE,
                    payload={
                        "title": candidate.title,
                        "hypothesis": candidate.hypothesis,
                    },
                    created_by=request.state.operator.id,
                    created_at=datetime.now(UTC),
                ),
                command_key=_id(body.idempotency_key, f"candidate-command-{index}"),
            )
            candidate_ids.append(str(receipt.artifact_id))
        async with engine.begin() as connection:
            await connection.execute(
                update(records.idea_discoveries)
                .where(
                    records.idea_discoveries.c.run_id == body.idempotency_key,
                    records.idea_discoveries.c.state == "RUNNING",
                )
                .values(
                    state="SUCCEEDED",
                    advice=payload,
                    output_hash=sha256(canonical_json(payload)),
                    candidate_ids=candidate_ids,
                    finished_at=datetime.now(UTC),
                )
            )
        snapshot = await _read_experiment(request, experiment_id)
        if snapshot is None:
            raise HTTPException(409, "DISCOVERY_RECONCILIATION_REQUIRED")
        return {
            "run_id": body.idempotency_key,
            "outcome": "SUCCEEDED",
            "state": "AWAITING_SELECTION",
            "candidates": snapshot["candidates"],
        }
    except HTTPException:
        raise
    except Exception as error:
        if claimed_operation_id is not None:
            async with engine.begin() as connection:
                await connection.execute(
                    update(records.idea_discoveries)
                    .where(
                        records.idea_discoveries.c.run_id == body.idempotency_key,
                        records.idea_discoveries.c.experiment_id == experiment_id,
                        records.idea_discoveries.c.operation_id == claimed_operation_id,
                        records.idea_discoveries.c.state == "RUNNING",
                    )
                    .values(state="DISCOVERY_BLOCKED", finished_at=datetime.now(UTC))
                )
        raise HTTPException(409, "DISCOVERY_UNAVAILABLE") from error


async def _run_outcome(engine, run_id: UUID) -> str | None:
    async with engine.connect() as connection:
        return await connection.scalar(
            select(run_intents.c.outcome).where(run_intents.c.idempotency_key == run_id)
        )


class SelectCandidateRequest(StrictRequest):
    candidate_artifact_id: UUID
    reason: str = Field(min_length=1, max_length=4000)
    command_key: UUID

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("selection reason is blank")
        return value


@router.post("/experiments/{experiment_id}/select")
async def select_experiment_candidate(
    request: Request, experiment_id: UUID, body: SelectCandidateRequest
) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise HTTPException(404, "EXPERIMENT_NOT_FOUND")
    if detail["mode"] != "SYSTEM_DISCOVERY":
        raise HTTPException(409, "DISCOVERY_MODE_REQUIRED")
    if str(body.candidate_artifact_id) not in {
        str(candidate["artifact_id"]) for candidate in detail["candidates"]
    }:
        raise HTTPException(409, "CANDIDATE_NOT_IN_DISCOVERY")
    async with request.app.state.engine.connect() as connection:
        candidate = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == body.candidate_artifact_id,
                        records.artifacts.c.experiment_id == experiment_id,
                        records.artifacts.c.kind == ArtifactKind.IDEA_CANDIDATE,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        selection = (
            (
                await connection.execute(
                    select(records.candidate_selections).where(
                        records.candidate_selections.c.experiment_id == experiment_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        selection_command = (
            (
                await connection.execute(
                    select(records.commands).where(
                        records.commands.c.command_key
                        == _id(body.command_key, "candidate-selection-command"),
                        records.commands.c.experiment_id == experiment_id,
                        records.commands.c.kind == "SELECT_IDEA_CANDIDATE",
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
    if candidate is None:
        raise HTTPException(409, "CANDIDATE_NOT_IN_DISCOVERY")
    if selection is None and detail["state"] != "AWAITING_SELECTION":
        raise HTTPException(409, "CANDIDATE_SELECTION_UNAVAILABLE")
    if selection and (
        selection["artifact_id"] != body.candidate_artifact_id
        or selection["reason"] != body.reason
        or selection["selected_by"] != request.state.operator.id
        or selection_command is None
        or selection_command["result_id"] != selection["id"]
    ):
        raise HTTPException(409, "CANDIDATE_ALREADY_SELECTED")
    if selection and detail["cycle_id"] is not None:
        return {
            "experiment_id": experiment_id,
            "cycle_id": detail["cycle_id"],
            "selection_id": selection["id"],
            "state": "AWAITING_REFINEMENT",
        }
    repository = ProductRecordsRepository(request.app.state.engine)
    candidate_input = ArtifactInput(
        artifact_id=candidate["id"],
        kind=ArtifactKind.IDEA_CANDIDATE,
        version=candidate["version"],
        content_hash=candidate["content_hash"],
        role="SELECTED_CANDIDATE",
    )
    try:
        receipt = await repository.select_idea_candidate(
            experiment_id,
            candidate_input,
            selected_by=request.state.operator.id,
            reason=body.reason,
            command_key=_id(body.command_key, "candidate-selection-command"),
        )
        cycle = await repository.create_cycle(
            experiment_id,
            candidate=candidate_input,
            selection_id=receipt.result_id,
            command_key=_id(body.command_key, "selected-cycle-command"),
        )
    except ProductRecordsDenied as error:
        raise HTTPException(409, error.reason) from None
    return {
        "experiment_id": experiment_id,
        "cycle_id": cycle.id,
        "selection_id": receipt.result_id,
        "state": "AWAITING_REFINEMENT",
    }


class AcceptRequest(StrictRequest):
    run_id: UUID
    command_key: UUID
    intent_relationship: Literal[
        "PRESERVES_CORE_INTENT",
        "CLARIFIES_CORE_INTENT",
        "NARROWS_CORE_INTENT",
        "MATERIAL_PIVOT",
        "UNRELATED",
    ]
    intent_confirmed: bool
    intent_rationale: str = Field(min_length=1, max_length=4000)

    @field_validator("intent_rationale")
    @classmethod
    def rationale_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("intent rationale is blank")
        return value


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
                    .where(
                        records.idea_refinements.c.experiment_id == experiment_id,
                        records.idea_refinements.c.cycle_id == cycle_id,
                    )
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
            select(records.returns.c.idea_artifact_id).where(
                records.returns.c.to_cycle_id == cycle_id,
                records.returns.c.experiment_id == experiment_id,
                records.returns.c.kind == "SAME_INTENT",
            )
        ) or await connection.scalar(
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
    if detail["mode"] == "SYSTEM_DISCOVERY" and detail["cycle_id"] is None:
        raise HTTPException(409, "CANDIDATE_SELECTION_REQUIRED")
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
        detail["state"] == "REFINEMENT_FAILED"
        and not detail["retry_safe"]
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
            "advice": _read_persisted_advice(
                ReturnedIdeaBriefAdvice
                if detail["cycle_purpose"] == "SAME_INTENT_RETURN"
                else SeededIdeaBriefAdvice
                if detail["mode"] == "USER_SEEDED_REFINEMENT"
                else SelectedCandidateIdeaBriefAdvice,
                existing["advice"],
            )
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
            advice,
            ReturnedIdeaBriefAdvice
            if detail["cycle_purpose"] == "SAME_INTENT_RETURN"
            else SeededIdeaBriefAdvice
            if detail["mode"] == "USER_SEEDED_REFINEMENT"
            else SelectedCandidateIdeaBriefAdvice,
        )
        payload = advice.model_dump(mode="json") if success and advice else None
        if success and payload:
            durable_run = await OpenAIRunStore(engine).get(body.idempotency_key)
            if durable_run is None or durable_run.output_hash != sha256(
                canonical_json(payload)
            ):
                success = False
                payload = None
        retry_safe = not success and await _confirmed_safe_retry(
            engine, body.idempotency_key, claimed_operation_id, experiment_id
        )
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
                    state="SUCCEEDED"
                    if success
                    else "REFINEMENT_FAILED"
                    if retry_safe
                    else "REFINEMENT_BLOCKED",
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
            "state": "AWAITING_REVIEW"
            if success
            else "REFINEMENT_FAILED"
            if retry_safe
            else "REFINEMENT_BLOCKED",
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
        returned = (
            (
                await connection.execute(
                    select(records.returns).where(
                        records.returns.c.to_cycle_id == detail["cycle_id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if detail["cycle_purpose"] == "SAME_INTENT_RETURN"
            else None
        )
        prior = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == returned["idea_artifact_id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if returned is not None
            else None
        )
        return_feedback = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == returned["feedback_artifact_id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if returned is not None
            else None
        )
    if (
        reviewed is None
        or reviewed["state"] != "SUCCEEDED"
        or reviewed["cycle_id"] != detail["cycle_id"]
        or body.run_id != detail["latest_run_id"]
        or seed is None
        or workflow is None
        or (
            detail["cycle_purpose"] == "SAME_INTENT_RETURN"
            and (prior is None or return_feedback is None)
        )
    ):
        raise HTTPException(409, "REFINEMENT_NOT_SUCCESSFUL")
    advice = (
        ReturnedIdeaBriefAdvice
        if detail["cycle_purpose"] == "SAME_INTENT_RETURN"
        else SeededIdeaBriefAdvice
        if detail["mode"] == "USER_SEEDED_REFINEMENT"
        else SelectedCandidateIdeaBriefAdvice
    ).model_validate_json(json.dumps(reviewed["advice"]))
    if (
        body.intent_relationship == "UNRELATED"
        or advice.intent_relationship == "UNRELATED"
    ):
        raise HTTPException(409, "IDEA_UNRELATED")
    if not body.intent_confirmed:
        raise HTTPException(409, "INTENT_CONFIRMATION_REQUIRED")
    if (
        advice.material_pivot
        or advice.intent_relationship == "MATERIAL_PIVOT"
        or body.intent_relationship == "MATERIAL_PIVOT"
    ):
        raise HTTPException(409, "MATERIAL_PIVOT_REQUIRES_APPROVAL")
    repository = ProductRecordsRepository(engine)
    brief_id = _id(body.command_key, "accepted-idea-brief")
    advice_payload = advice.model_dump(mode="json")
    payload = {
        key: advice_payload[key]
        for key in (
            "title",
            "customer",
            "problem",
            "core_intent",
            "material_pivot",
            "buyer",
            "service_hypothesis",
            "value_hypothesis",
            "assumptions",
            "exclusions",
            "research_questions",
        )
    }
    logical_id = prior["logical_id"] if prior is not None else brief_id
    version = prior["version"] + 1 if prior is not None else 1
    existing_artifact = await _artifact_row(request, brief_id)
    if existing_artifact is not None and (
        existing_artifact["experiment_id"] != experiment_id
        or existing_artifact["workflow_id"] != workflow["id"]
        or existing_artifact["agent_id"] != workflow["agent_id"]
        or existing_artifact["operation_id"] != reviewed["operation_id"]
        or existing_artifact["kind"] != ArtifactKind.IDEA_BRIEF
        or existing_artifact["logical_id"] != logical_id
        or existing_artifact["version"] != version
        or existing_artifact["payload"] != payload
        or existing_artifact["created_by"] != request.state.operator.id
    ):
        raise HTTPException(409, "COMMAND_CONFLICT")
    expected_review = {
        "run_id": body.run_id,
        "experiment_id": experiment_id,
        "cycle_id": detail["cycle_id"],
        "source_artifact_id": prior["id"] if prior is not None else seed["id"],
        "output_hash": reviewed["output_hash"],
        "relationship": body.intent_relationship,
        "rationale": body.intent_rationale,
        "confirmed_by": request.state.operator.id,
        "command_key": body.command_key,
    }
    async with engine.begin() as connection:
        await connection.execute(
            select(records.experiments.c.id)
            .where(records.experiments.c.id == experiment_id)
            .with_for_update()
        )
        await connection.execute(
            pg_insert(records.idea_intent_reviews)
            .values(**expected_review, created_at=datetime.now(UTC))
            .on_conflict_do_nothing(index_elements=["run_id"])
        )
        intent_review = (
            (
                await connection.execute(
                    select(records.idea_intent_reviews).where(
                        records.idea_intent_reviews.c.run_id == body.run_id
                    )
                )
            )
            .mappings()
            .one()
        )
        if any(intent_review[key] != value for key, value in expected_review.items()):
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
                logical_id=logical_id,
                version=version,
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
                (
                    ArtifactInput(
                        artifact_id=prior["id"],
                        kind=ArtifactKind.IDEA_BRIEF,
                        version=prior["version"],
                        content_hash=prior["content_hash"],
                        role="SUPERSEDES",
                    )
                    if prior is not None
                    else ArtifactInput(
                        artifact_id=seed["id"],
                        kind=ArtifactKind(seed["kind"]),
                        version=seed["version"],
                        content_hash=seed["content_hash"],
                        role="SEED"
                        if detail["mode"] == "USER_SEEDED_REFINEMENT"
                        else "SELECTED_CANDIDATE",
                    )
                ),
                *(
                    (
                        ArtifactInput(
                            artifact_id=return_feedback["id"],
                            kind=ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
                            version=return_feedback["version"],
                            content_hash=return_feedback["content_hash"],
                            role="RESEARCH_FEEDBACK",
                        ),
                    )
                    if return_feedback is not None
                    else ()
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
