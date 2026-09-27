"""Operator-owned, user-seeded experiment creation and Idea review."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.agents.idea_discovery import (
    IdeaCandidateSetAdvice,
    LegacyIdeaBriefAdvice,
    ReturnedIdeaBriefAdvice,
    SeededIdeaBriefAdvice,
    SelectedCandidateIdeaBriefAdvice,
)
from alon_ai.config import Settings
from alon_ai.db.repositories import experiments as experiment_repository
from alon_ai.db.repositories.experiments import (
    ExperimentError,
    _terminal_failure_settled,
)
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.db.repositories.records_operators import OperatorRepository
from alon_ai.services.schemas.records import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductWorkflow,
)
from alon_ai.services.schemas.records_operator import (
    CommercialConstraints,
    DeliveryConstraints,
    OperatorProfileVersion,
)


@dataclass(frozen=True)
class ExperimentContext:
    engine: AsyncEngine
    settings: Settings
    operator_id: UUID
    idea_runtime_provider: Any = None
    recorded_runtime_provisioner: Any = None


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


class HistoricalExperimentInput(StrictRequest):
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


class CreateExperimentRequest(StrictRequest):
    idea_seed: str | None = Field(default=None, min_length=1, max_length=4000)
    command_key: UUID

    @field_validator("idea_seed")
    @classmethod
    def meaningful_idea(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("idea is blank")
        return value


class CreateExperimentResponse(StrictRequest):
    experiment_id: UUID
    cycle_id: UUID | None
    brief_artifact_id: UUID
    seed_artifact_id: UUID | None
    state: Literal["AWAITING_REFINEMENT", "AWAITING_DISCOVERY"]


async def _profile(
    request: ExperimentContext, payload: OperatorProfileInput, operator_id: UUID
) -> tuple[UUID, int]:
    engine = request.engine
    delivery = DeliveryConstraints.model_validate(payload.delivery.model_dump())
    commercial = CommercialConstraints.model_validate(payload.commercial.model_dump())
    rows = await experiment_repository.profile_rows(engine, operator_id)
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


async def _artifact_row(request: ExperimentContext, artifact_id: UUID):
    return await experiment_repository.artifact_row(request.engine, artifact_id)


async def create_experiment(
    request: ExperimentContext, body: HistoricalExperimentInput
) -> CreateExperimentResponse:
    operator_id: UUID = request.operator_id
    repository = ProductRecordsRepository(request.engine)
    experiment_id = _id(body.command_key, "experiment")
    workflow_id = _id(body.command_key, "workflow")
    agent_id = _id(body.command_key, "agent")
    brief_id = _id(body.command_key, "brief")
    seed_id = _id(body.command_key, "seed")
    cycle_id = _id(body.command_key, "cycle")
    existing = await experiment_repository.existing_experiment(
        request.engine, request.operator_id, experiment_id
    )
    if existing is not None:
        bound_profile = await experiment_repository.bound_profile(
            request.engine, existing, operator_id
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
            raise ExperimentError(409, "COMMAND_CONFLICT")
        detail = await _read_experiment(request, experiment_id)
        if detail is not None:
            if (
                detail["idea_seed"] != body.idea_seed
                or detail["brief"] != body.brief.artifact_payload()
            ):
                raise ExperimentError(409, "COMMAND_CONFLICT")
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
        await experiment_repository.insert_governance_roots(
            request.engine, experiment_id, workflow_id, agent_id
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
            raise ExperimentError(409, "COMMAND_CONFLICT")
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
                    raise ExperimentError(409, "COMMAND_CONFLICT")
                seed_input = ArtifactInput(
                    artifact_id=seed_row["id"],
                    kind=ArtifactKind.IDEA_SEED,
                    version=seed_row["version"],
                    content_hash=seed_row["content_hash"],
                    role="SEED",
                )
        existing_cycle = await experiment_repository.existing_cycle(
            request.engine, experiment_id
        )
        if body.idea_seed is None:
            if existing_cycle is not None:
                raise ExperimentError(409, "COMMAND_CONFLICT")
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
        raise ExperimentError(409, error.reason) from None
    return CreateExperimentResponse(
        experiment_id=experiment_id,
        cycle_id=cycle_id,
        brief_artifact_id=brief_id,
        seed_artifact_id=seed_id if body.idea_seed is not None else None,
        state="AWAITING_REFINEMENT"
        if body.idea_seed is not None
        else "AWAITING_DISCOVERY",
    )


async def _read_experiment(
    request: ExperimentContext, experiment_id: UUID
) -> dict | None:
    await _reconcile_stale_refinement(request, experiment_id)
    await _reconcile_stale_discovery(request, experiment_id)
    snapshot_rows = await experiment_repository.experiment_snapshot_rows(
        request.engine, request.operator_id, experiment_id
    )
    if snapshot_rows is None:
        return None
    (
        experiment,
        artifacts,
        cycle,
        acceptance,
        latest,
        discovery,
        run_outcome,
        discovery_outcome,
        returned,
        return_context_rows,
        return_verdict,
        available_verdict,
        available_feedback_rows,
        return_block,
        cycle_state,
        managed_return,
    ) = snapshot_rows
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
    lineage_rows = await experiment_repository.return_lineage_rows(
        request.engine, experiment_id
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
        matching = await experiment_repository.matching_feedback(
            request.engine, available_feedback_rows, acceptance, available_verdict
        )
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
            request.engine,
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
    intent, call = await experiment_repository.safe_retry_evidence(
        engine, run_id, operation_id, experiment_id
    )
    return _terminal_failure_settled(intent, call)


async def _reconcile_stale_discovery(
    request: ExperimentContext, experiment_id: UUID
) -> None:
    stale_before = datetime.now(UTC) - timedelta(seconds=3690)
    await experiment_repository.reconcile_stale_discovery(
        request.engine, request.operator_id, experiment_id, stale_before
    )


async def _reconcile_stale_refinement(
    request: ExperimentContext, experiment_id: UUID
) -> None:
    """Resolve stale claims only from settled terminal evidence; otherwise block."""
    stale_before = datetime.now(UTC) - timedelta(seconds=3690)
    await experiment_repository.reconcile_stale_refinement(
        request.engine, request.operator_id, experiment_id, stale_before
    )


class ExperimentRuntimeStatus(StrictRequest):
    provider_mode: Literal["disabled", "fake", "live"]
    ready: bool


async def experiment_runtime_status(
    request: ExperimentContext,
) -> ExperimentRuntimeStatus:
    settings = request.settings
    return ExperimentRuntimeStatus(
        provider_mode=settings.provider_mode,
        ready=(
            settings.provider_mode == "fake" and settings.environment != "production"
        )
        or (
            settings.provider_mode == "live"
            and request.idea_runtime_provider is not None
        ),
    )


async def get_experiment(request: ExperimentContext, experiment_id: UUID) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
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


class ExperimentService:
    def __init__(self, context: ExperimentContext) -> None:
        self.context = context

    async def create(self, body: CreateExperimentRequest) -> dict:
        from alon_ai.services.intake import IntakeService

        return await IntakeService(self.context).create(body)

    async def runtime_status(self) -> ExperimentRuntimeStatus:
        return await experiment_runtime_status(self.context)

    async def get(self, experiment_id: UUID) -> dict:
        from alon_ai.services.intake import IntakeService

        return await IntakeService(self.context).snapshot(experiment_id)
