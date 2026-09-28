"""Select exact Idea inputs and the configured bounded agent profile."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType
from uuid import UUID

from alon_ai.agents.idea_discovery import (
    _STAGE_SETTINGS,
    IdeaCandidateSetAdvice,
    IdeaStage,
    ReturnedIdeaBriefAdvice,
    SeededIdeaBriefAdvice,
    SelectedCandidateIdeaBriefAdvice,
)
from alon_ai.agents.runtime import (
    AcceptedArtifact,
    OpenAIExecution,
)
from alon_ai.agents.schemas.openai import RoutingFacts, canonical_json, sha256
from alon_ai.db.repositories import experiments as experiment_repository
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.repositories.openai_idea import OpenAIIdeaInputRepository
from alon_ai.db.repositories.openai_run import OpenAIRunOutcome, OpenAIRunStore
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.integrations.schemas.provider import CallAttribution
from alon_ai.services.agent_runs import OpenAIRuntime
from alon_ai.services.combined_idea import CombinedIdeaRuntime
from alon_ai.services.experiments import (
    AcceptRequest,
    ExperimentContext,
    RefineRequest,
    SelectCandidateRequest,
    _artifact_row,
    _confirmed_safe_retry,
    _id,
    _read_experiment,
    _read_persisted_advice,
)
from alon_ai.services.idea_safety import IdeaSafetyError, validate_idea_advice
from alon_ai.services.schemas.records import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    ProductRecordsDenied,
)


class IdeaRuntime:
    """Choose the application profile from durable cycle mode, never model output."""

    def __init__(
        self,
        records_repository: ProductRecordsRepository,
        runtimes: Mapping[IdeaStage, OpenAIRuntime],
    ) -> None:
        if set(runtimes) != set(IdeaStage):
            raise ValueError("Idea runtime requires all configured stages")
        for stage, runtime in runtimes.items():
            settings = _STAGE_SETTINGS[stage]
            if len(runtime.profiles) != 1:
                raise ValueError("Idea runtime profile does not match its stage")
            profile = next(iter(runtime.profiles.values()))
            if (
                profile.prompt_version != settings[0]
                or profile.schema_version != settings[1]
                or profile.instructions != settings[2]
                or profile.schema_json != canonical_json(settings[3])
                or profile.output_model is not settings[4]
                or runtime.routes.cheap != profile.config_id
            ):
                raise ValueError("Idea runtime profile does not match its stage")
        self.records = records_repository
        self.inputs = OpenAIIdeaInputRepository(records_repository.engine)
        self.runtimes = MappingProxyType(dict(runtimes))

    async def discover_system(
        self,
        attribution: CallAttribution,
        *,
        facts: RoutingFacts,
        idempotency_key: UUID,
    ) -> OpenAIExecution:
        operator_profile = await self.inputs.operator_profile(attribution.experiment_id)
        brief = await self.inputs.experiment_brief(attribution.experiment_id)
        if brief is None:
            raise PermissionError("Discovery requires exact ExperimentBrief")
        return await self.runtimes[IdeaStage.SYSTEM_DISCOVERY].run(
            attribution,
            facts=facts,
            sources=(),
            artifacts=(
                AcceptedArtifact(
                    artifact=ArtifactInput(
                        artifact_id=brief["id"],
                        kind=ArtifactKind.EXPERIMENT_BRIEF,
                        version=brief["version"],
                        content_hash=brief["content_hash"],
                        role="EXPERIMENT_BRIEF",
                    ),
                    experiment_id=attribution.experiment_id,
                    schema_version=brief["schema_version"],
                ),
            ),
            operator_profiles=(operator_profile,),
            idempotency_key=idempotency_key,
        )

    async def refine_cycle(
        self,
        attribution: CallAttribution,
        *,
        cycle_id: UUID,
        facts: RoutingFacts,
        idempotency_key: UUID,
    ) -> OpenAIExecution:
        cycle, schema_version = await self.inputs.cycle_origin(
            attribution.experiment_id, cycle_id
        )
        if schema_version is None:
            raise PermissionError("Idea cycle origin is no longer exact")
        if cycle["purpose"] == "SAME_INTENT_RETURN":
            returned, prior, feedback = await self.inputs.return_inputs(
                attribution.experiment_id, cycle_id
            )
            if prior is None or feedback is None:
                raise PermissionError("same-intent inputs are no longer exact")
            stage = IdeaStage.RESEARCH_FEEDBACK_REFINEMENT
            operator_profile = await self.inputs.operator_profile(
                attribution.experiment_id
            )
            return await self.runtimes[stage].run(
                attribution,
                facts=facts,
                sources=(),
                artifacts=(
                    AcceptedArtifact(
                        artifact=ArtifactInput(
                            artifact_id=prior["id"],
                            kind=ArtifactKind.IDEA_BRIEF,
                            version=prior["version"],
                            content_hash=prior["content_hash"],
                            role="PRIOR_IDEA_BRIEF",
                        ),
                        experiment_id=attribution.experiment_id,
                        schema_version=prior["schema_version"],
                        cycle_id=cycle_id,
                        return_id=returned["id"],
                    ),
                    AcceptedArtifact(
                        artifact=ArtifactInput(
                            artifact_id=feedback["id"],
                            kind=ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
                            version=feedback["version"],
                            content_hash=feedback["content_hash"],
                            role="RESEARCH_FEEDBACK",
                        ),
                        experiment_id=attribution.experiment_id,
                        schema_version=feedback["schema_version"],
                        cycle_id=cycle_id,
                        return_id=returned["id"],
                    ),
                ),
                operator_profiles=(operator_profile,),
                idempotency_key=idempotency_key,
            )
        if cycle["idea_mode"] == IdeaStage.USER_SEEDED_REFINEMENT:
            stage = IdeaStage.USER_SEEDED_REFINEMENT
            kind = ArtifactKind.IDEA_SEED
            role = "SEED"
            selection_id = None
        elif cycle["idea_mode"] == IdeaStage.SYSTEM_DISCOVERY:
            if cycle["selection_id"] is None:
                raise PermissionError("System idea cycle lacks candidate selection")
            stage = IdeaStage.SYSTEM_CANDIDATE_REFINEMENT
            kind = ArtifactKind.IDEA_CANDIDATE
            role = "SELECTED_CANDIDATE"
            selection_id = cycle["selection_id"]
        else:
            raise PermissionError("Unknown idea cycle mode")
        if cycle["seed_kind"] != kind:
            raise PermissionError("Idea cycle mode and origin disagree")
        operator_profile = await self.inputs.operator_profile(attribution.experiment_id)
        origin = ArtifactInput(
            artifact_id=cycle["seed_artifact_id"],
            kind=kind,
            version=cycle["seed_version"],
            content_hash=cycle["seed_hash"],
            role=role,
        )
        return await self.runtimes[stage].run(
            attribution,
            facts=facts,
            sources=(),
            artifacts=(
                AcceptedArtifact(
                    artifact=origin,
                    experiment_id=attribution.experiment_id,
                    schema_version=schema_version,
                    selection_id=selection_id,
                    cycle_id=cycle_id,
                ),
            ),
            operator_profiles=(operator_profile,),
            idempotency_key=idempotency_key,
        )


async def discover_experiment(
    request: ExperimentContext,
    experiment_id: UUID,
    body: RefineRequest,
    *,
    allow_regeneration: bool = False,
) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
    if detail["mode"] != "SYSTEM_DISCOVERY":
        raise ExperimentError(409, "DISCOVERY_MODE_REQUIRED")
    if detail["cycle_id"] is not None:
        raise ExperimentError(409, "CANDIDATE_ALREADY_SELECTED")
    engine = request.engine
    prior, roots = await experiment_repository.discovery_prior_and_roots(
        engine, experiment_id
    )
    if prior is not None:
        if prior["run_id"] != body.idempotency_key:
            if not (allow_regeneration and prior["state"] == "SUCCEEDED") and (
                prior["state"] != "DISCOVERY_FAILED" or not detail["retry_safe"]
            ):
                raise ExperimentError(
                    409,
                    "CANDIDATE_REVIEW_PENDING"
                    if prior["state"] == "SUCCEEDED"
                    else "DISCOVERY_RECONCILIATION_REQUIRED",
                )
        elif prior["state"] == "SUCCEEDED":
            snapshot = await _read_experiment(request, experiment_id)
            if snapshot is None:
                raise ExperimentError(409, "DISCOVERY_RECONCILIATION_REQUIRED")
            return {
                "run_id": body.idempotency_key,
                "outcome": "SUCCEEDED",
                "state": "AWAITING_SELECTION",
                "candidates": snapshot["candidates"],
            }
        elif prior["state"] == "RUNNING":
            raise ExperimentError(409, "DISCOVERY_IN_PROGRESS")
        else:
            return {
                "run_id": body.idempotency_key,
                "outcome": await _run_outcome(engine, body.idempotency_key),
                "state": prior["state"],
                "candidates": [],
            }
    settings = request.settings
    if settings.provider_mode == "disabled" or (
        settings.provider_mode == "fake" and settings.environment == "production"
    ):
        raise ExperimentError(409, "DISCOVERY_UNAVAILABLE")
    if roots is None:
        raise ExperimentError(409, "EXPERIMENT_NOT_READY")
    runtime_args = {
        "experiment_id": experiment_id,
        "workflow_id": roots["id"],
        "agent_id": roots["agent_id"],
        "operator_id": request.operator_id,
        "run_id": body.idempotency_key,
        "budget_usd": Decimal(detail["brief"]["budget_usd"]),
    }
    claimed_operation_id: UUID | None = None
    try:
        if settings.provider_mode == "fake":
            service, attribution = await request.recorded_runtime_provisioner(
                engine, **runtime_args
            )
            advice_source = "RECORDED_FAKE"
        else:
            provider = request.idea_runtime_provider
            if provider is None:
                raise ExperimentError(409, "LIVE_CONFIG_REQUIRED")
            service, attribution, advice_source = await provider(engine, **runtime_args)
        await experiment_repository.claim_discovery(
            engine,
            experiment_id,
            prior,
            body.idempotency_key,
            attribution.operation_run_id,
            advice_source,
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
        durable_hash = (
            service.output_hash
            if isinstance(service, CombinedIdeaRuntime)
            else (durable.output_hash if durable else None)
        )
        if not success or durable_hash != sha256(canonical_json(payload)):
            retry_safe = await _confirmed_safe_retry(
                engine,
                body.idempotency_key,
                attribution.operation_run_id,
                experiment_id,
            )
            await experiment_repository.finish_failed_discovery(
                engine, body.idempotency_key, retry_safe
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
                    created_by=request.operator_id,
                    created_at=service.row["created_at"]
                    if isinstance(service, CombinedIdeaRuntime)
                    else datetime.now(UTC),
                ),
                command_key=_id(body.idempotency_key, f"candidate-command-{index}"),
            )
            candidate_ids.append(str(receipt.artifact_id))
        await experiment_repository.finish_successful_discovery(
            engine, body.idempotency_key, payload, candidate_ids
        )
        snapshot = await _read_experiment(request, experiment_id)
        if snapshot is None:
            raise ExperimentError(409, "DISCOVERY_RECONCILIATION_REQUIRED")
        return {
            "run_id": body.idempotency_key,
            "outcome": "SUCCEEDED",
            "state": "AWAITING_SELECTION",
            "candidates": snapshot["candidates"],
        }
    except ExperimentError as error:
        if error.detail == "RESEARCH_INCOMPLETE" and claimed_operation_id is not None:
            await experiment_repository.block_discovery(
                engine, body.idempotency_key, experiment_id, claimed_operation_id
            )
        raise
    except Exception as error:
        if claimed_operation_id is not None:
            await experiment_repository.block_discovery(
                engine, body.idempotency_key, experiment_id, claimed_operation_id
            )
        raise ExperimentError(409, "DISCOVERY_UNAVAILABLE") from error


async def _run_outcome(engine, run_id: UUID) -> str | None:
    return await experiment_repository.run_outcome(engine, run_id)


async def select_experiment_candidate(
    request: ExperimentContext, experiment_id: UUID, body: SelectCandidateRequest
) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
    if detail["mode"] != "SYSTEM_DISCOVERY":
        raise ExperimentError(409, "DISCOVERY_MODE_REQUIRED")
    discovery_run_id = detail["latest_run_id"]
    if discovery_run_id is not None:
        discovery_run = await AgentRunRepository(request.engine).get(discovery_run_id)
        if (
            discovery_run is not None
            and discovery_run["experiment_id"] == experiment_id
            and discovery_run["task_kind"] == "IDEA_DISCOVERY"
            and discovery_run["review_status"] == "REJECTED"
        ):
            raise ExperimentError(409, "DISCOVERY_RUN_REJECTED")
    from alon_ai.db.repositories.intake import IntakeRepository

    revisions = await IntakeRepository(request.engine).history(experiment_id)
    if str(body.candidate_artifact_id) not in {
        str(candidate["artifact_id"]) for candidate in detail["candidates"]
    } | {str(row["id"]) for row in revisions}:
        raise ExperimentError(409, "CANDIDATE_NOT_IN_DISCOVERY")
    (
        candidate,
        selection,
        selection_command,
        candidate_discovery_run_id,
    ) = await experiment_repository.candidate_selection_rows(
        request.engine,
        experiment_id,
        body.candidate_artifact_id,
        _id(body.command_key, "candidate-selection-command"),
    )
    if candidate is None:
        raise ExperimentError(409, "CANDIDATE_NOT_IN_DISCOVERY")
    if candidate_discovery_run_id is not None:
        source_run = await AgentRunRepository(request.engine).get(
            candidate_discovery_run_id
        )
        if source_run is not None and source_run["review_status"] == "REJECTED":
            raise ExperimentError(409, "DISCOVERY_RUN_REJECTED")
    if selection is None and detail["state"] != "AWAITING_SELECTION":
        raise ExperimentError(409, "CANDIDATE_SELECTION_UNAVAILABLE")
    if selection and (
        selection["artifact_id"] != body.candidate_artifact_id
        or selection["reason"] != body.reason
        or selection["selected_by"] != request.operator_id
        or selection_command is None
        or selection_command["result_id"] != selection["id"]
    ):
        raise ExperimentError(409, "CANDIDATE_ALREADY_SELECTED")
    if selection and detail["cycle_id"] is not None:
        return {
            "experiment_id": experiment_id,
            "cycle_id": detail["cycle_id"],
            "selection_id": selection["id"],
            "state": "AWAITING_REFINEMENT",
        }
    repository = ProductRecordsRepository(request.engine)
    candidate_input = ArtifactInput(
        artifact_id=candidate["id"],
        kind=ArtifactKind.IDEA_CANDIDATE,
        version=candidate["version"],
        content_hash=candidate["content_hash"],
        role="SELECTED_CANDIDATE",
    )
    try:
        async with AgentRunRepository(request.engine).review_scope(
            candidate_discovery_run_id, request.operator_id
        ):
            receipt = await repository.select_idea_candidate(
                experiment_id,
                candidate_input,
                selected_by=request.operator_id,
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
        raise ExperimentError(409, error.reason) from None
    return {
        "experiment_id": experiment_id,
        "cycle_id": cycle.id,
        "selection_id": receipt.result_id,
        "state": "AWAITING_REFINEMENT",
    }


async def _claim_refinement(
    request: ExperimentContext,
    *,
    experiment_id: UUID,
    cycle_id: UUID,
    run_id: UUID,
    operation_id: UUID,
    advice_source: str,
) -> None:
    """Serialize the check and RUNNING insert across API processes."""
    await experiment_repository.claim_refinement(
        request.engine, experiment_id, cycle_id, run_id, operation_id, advice_source
    )


async def refine_experiment(
    request: ExperimentContext,
    experiment_id: UUID,
    body: RefineRequest,
    *,
    allow_regeneration: bool = False,
) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
    if detail["mode"] == "SYSTEM_DISCOVERY" and detail["cycle_id"] is None:
        raise ExperimentError(409, "CANDIDATE_SELECTION_REQUIRED")
    if detail["state"] == "IDEA_ACCEPTED":
        raise ExperimentError(409, "IDEA_ALREADY_ACCEPTED")
    if detail["state"] == "REFINEMENT_IN_PROGRESS":
        raise ExperimentError(409, "REFINEMENT_IN_PROGRESS")
    if (
        detail["state"] == "REFINEMENT_BLOCKED"
        and body.idempotency_key != detail["latest_run_id"]
    ):
        raise ExperimentError(409, "REFINEMENT_RECONCILIATION_REQUIRED")
    if (
        detail["state"] == "REFINEMENT_FAILED"
        and not detail["retry_safe"]
        and body.idempotency_key != detail["latest_run_id"]
    ):
        raise ExperimentError(409, "REFINEMENT_RECONCILIATION_REQUIRED")
    if (
        detail["state"] == "AWAITING_REVIEW"
        and body.idempotency_key != detail["latest_run_id"]
    ):
        raise ExperimentError(409, "REVIEW_PENDING")
    settings = request.settings
    engine = request.engine
    existing, roots = await experiment_repository.refinement_existing_and_roots(
        engine, body.idempotency_key, experiment_id
    )
    if existing is not None:
        if existing["experiment_id"] != experiment_id:
            raise ExperimentError(409, "COMMAND_CONFLICT")
        if existing["state"] == "RUNNING":
            raise ExperimentError(409, "REFINEMENT_IN_PROGRESS")
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
        raise ExperimentError(409, "REFINEMENT_UNAVAILABLE")
    if roots is None:
        raise ExperimentError(409, "EXPERIMENT_NOT_READY")
    claimed_operation_id: UUID | None = None
    try:
        runtime_args = {
            "experiment_id": experiment_id,
            "workflow_id": roots["id"],
            "agent_id": roots["agent_id"],
            "operator_id": request.operator_id,
            "run_id": body.idempotency_key,
            "budget_usd": Decimal(detail["brief"]["budget_usd"]),
        }
        if settings.provider_mode == "fake":
            service, attribution = await request.recorded_runtime_provisioner(
                engine, **runtime_args
            )
            advice_source = "RECORDED_FAKE"
        else:
            provider = request.idea_runtime_provider
            if provider is None:
                raise ExperimentError(409, "LIVE_CONFIG_REQUIRED")
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
            durable_hash = (
                service.output_hash
                if isinstance(service, CombinedIdeaRuntime)
                else (durable_run.output_hash if durable_run else None)
            )
            if durable_hash != sha256(canonical_json(payload)):
                success = False
                payload = None
        retry_safe = not success and await _confirmed_safe_retry(
            engine, body.idempotency_key, claimed_operation_id, experiment_id
        )
        await experiment_repository.finish_refinement(
            engine,
            body.idempotency_key,
            experiment_id,
            claimed_operation_id,
            success,
            retry_safe,
            payload,
        )
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
    except ExperimentError as error:
        if error.detail == "RESEARCH_INCOMPLETE" and claimed_operation_id is not None:
            await experiment_repository.block_refinement(
                engine, body.idempotency_key, experiment_id, claimed_operation_id
            )
        raise
    except Exception as error:
        # No output can be accepted after an interrupted or denied run.
        if claimed_operation_id is not None:
            await experiment_repository.block_refinement(
                engine, body.idempotency_key, experiment_id, claimed_operation_id
            )
        raise ExperimentError(409, "REFINEMENT_UNAVAILABLE") from error


async def accept_experiment_idea(
    request: ExperimentContext, experiment_id: UUID, body: AcceptRequest
) -> dict:
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
    engine = request.engine
    operator_run = await AgentRunRepository(engine).get(body.run_id)
    if operator_run is not None and operator_run["review_status"] == "REJECTED":
        raise ExperimentError(409, "IDEA_RUN_REJECTED")
    (
        reviewed,
        seed,
        workflow,
        prior,
        return_feedback,
    ) = await experiment_repository.acceptance_rows(
        engine, body.run_id, experiment_id, detail["cycle_id"], detail["cycle_purpose"]
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
        raise ExperimentError(409, "REFINEMENT_NOT_SUCCESSFUL")
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
        raise ExperimentError(409, "IDEA_UNRELATED")
    if not body.intent_confirmed:
        raise ExperimentError(409, "INTENT_CONFIRMATION_REQUIRED")
    if (
        advice.material_pivot
        or advice.intent_relationship == "MATERIAL_PIVOT"
        or body.intent_relationship == "MATERIAL_PIVOT"
    ):
        raise ExperimentError(409, "MATERIAL_PIVOT_REQUIRES_APPROVAL")
    if operator_run is not None:
        profile_row = await AgentRunRepository(engine).profile_projection(operator_run)
        if profile_row is None:
            raise ExperimentError(409, "IDEA_INPUT_STALE")
        origin = seed["payload"]
        source_text = (
            origin.get("statement")
            or origin.get("hypothesis")
            or origin.get("core_intent")
            or ""
        )
        try:
            validate_idea_advice(
                advice.model_dump(mode="json"),
                seed=source_text,
                capabilities=profile_row["capabilities"],
            )
        except IdeaSafetyError as error:
            raise ExperimentError(409, str(error)) from None
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
        or existing_artifact["created_by"] != request.operator_id
    ):
        raise ExperimentError(409, "COMMAND_CONFLICT")
    expected_review = {
        "run_id": body.run_id,
        "experiment_id": experiment_id,
        "cycle_id": detail["cycle_id"],
        "source_artifact_id": prior["id"] if prior is not None else seed["id"],
        "output_hash": reviewed["output_hash"],
        "relationship": body.intent_relationship,
        "rationale": body.intent_rationale,
        "confirmed_by": request.operator_id,
        "command_key": body.command_key,
    }
    if operator_run is not None:
        await AgentRunRepository(engine).claim_acceptance(
            body.run_id, experiment_id, request.operator_id, body.command_key
        )
    await experiment_repository.save_intent_review(
        engine, experiment_id, body.run_id, expected_review
    )
    if detail["state"] == "IDEA_ACCEPTED":
        accepted = await experiment_repository.accepted_row(engine, detail["cycle_id"])
        if (
            existing_artifact is not None
            and accepted["artifact_id"] == brief_id
            and accepted["accepted_by"] == request.operator_id
        ):
            if operator_run is not None:
                await AgentRunRepository(engine).complete_acceptance(
                    body.run_id, body.command_key
                )
            return {
                "experiment_id": experiment_id,
                "idea_brief_artifact_id": brief_id,
                "acceptance_id": accepted["id"],
                "state": "IDEA_ACCEPTED",
            }
        raise ExperimentError(409, "IDEA_ALREADY_ACCEPTED")
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
                created_by=request.operator_id,
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
            accepted_by=request.operator_id,
            command_key=_id(body.command_key, "idea-acceptance-command"),
        )
    except ProductRecordsDenied as error:
        raise ExperimentError(409, error.reason) from None
    if operator_run is not None:
        await AgentRunRepository(engine).complete_acceptance(
            body.run_id, body.command_key
        )
    return {
        "experiment_id": experiment_id,
        "idea_brief_artifact_id": artifact.artifact_id,
        "acceptance_id": acceptance.id,
        "state": "IDEA_ACCEPTED",
    }


class IdeaService:
    def __init__(self, context: ExperimentContext) -> None:
        self.context = context

    async def discover(self, experiment_id: UUID, body: RefineRequest) -> dict:
        return await discover_experiment(self.context, experiment_id, body)

    async def select(self, experiment_id: UUID, body: SelectCandidateRequest) -> dict:
        return await select_experiment_candidate(self.context, experiment_id, body)

    async def refine(self, experiment_id: UUID, body: RefineRequest) -> dict:
        return await refine_experiment(self.context, experiment_id, body)

    async def accept(self, experiment_id: UUID, body: AcceptRequest) -> dict:
        return await accept_experiment_idea(self.context, experiment_id, body)
