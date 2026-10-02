"""Minimal operator intake, exact revisions and governed first-agent dispatch."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from alon_ai.db.repositories import experiments as repo
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.repositories.intake import IntakeRepository
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.services.experiments import (
    CreateExperimentRequest,
    ExperimentContext,
    RefineRequest,
    SelectCandidateRequest,
    _id,
    _read_experiment,
)
from alon_ai.services.ideas import IdeaService, discover_experiment
from alon_ai.services.schemas.agent_runs import AgentRunRequest
from alon_ai.services.schemas.intake import (
    ExperimentSnapshot,
    GenerateIdeaRequest,
    IntakePolicySnapshot,
    RegenerateIdeaRequest,
    ReviseProposalRequest,
    StartProposalRequest,
)
from alon_ai.services.schemas.records import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductWorkflow,
)


class IntakeService:
    def __init__(self, context: ExperimentContext):
        self.context = context
        self.store = IntakeRepository(context.engine)
        self.records = ProductRecordsRepository(context.engine)

    async def _roots(
        self,
        key: UUID,
        idea_seed: str | None,
        *,
        draft: bool,
        generation_guidance: str | None = None,
    ) -> UUID:
        context = self.context
        experiment_id = _id(context.operator_id, f"intake/{key}")
        existing = await repo.existing_experiment(
            context.engine, context.operator_id, experiment_id
        )
        intake = await self.store.get(experiment_id, context.operator_id)
        if intake is not None:
            if intake["command_key"] != key or intake["idea_seed"] != idea_seed:
                raise ExperimentError(409, "COMMAND_CONFLICT")
            if existing is not None and await self.store.has_commands(experiment_id):
                return experiment_id
            profile = {"id": intake["profile_id"], "version": intake["profile_version"]}
        else:
            profiles = await repo.profile_rows(context.engine, context.operator_id)
            profiles = [
                row
                for row in profiles
                if row["profile_schema_version"] == 2
                and row["approved_by"] == context.operator_id
            ]
            if not profiles:
                raise ExperimentError(409, "OPERATOR_PROFILE_REQUIRED")
            if context.settings.idea_intake_budget_usd is None:
                raise ExperimentError(409, "INTAKE_BUDGET_REQUIRED")
            intake = await self.store.reserve(
                experiment_id,
                key,
                context.operator_id,
                idea_seed,
                draft,
                profiles[0],
                context.settings.idea_intake_budget_usd,
            )
            profile = {"id": intake["profile_id"], "version": intake["profile_version"]}
        now = intake["created_at"]
        workflow_id, agent_id = (
            _id(experiment_id, "workflow"),
            _id(experiment_id, "agent"),
        )
        await repo.insert_governance_roots(
            context.engine, experiment_id, workflow_id, agent_id
        )
        if existing is None:
            await self.records.bind_roots(
                ProductExperiment(
                    id=experiment_id,
                    operator_profile_id=profile["id"],
                    operator_profile_version=profile["version"],
                    name=idea_seed.strip()[:120] if idea_seed else "Idea proposals",
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
                command_key=_id(experiment_id, "roots-command"),
            )
        brief_id = _id(experiment_id, "brief")
        brief = await repo.artifact_row(context.engine, brief_id)
        if brief is None:
            payload = IntakePolicySnapshot(
                budget_usd=intake["budget_usd"],
                guidance=generation_guidance or "",
            ).model_dump(mode="json")
            await self.records.append_artifact(
                ArtifactDraft(
                    id=brief_id,
                    logical_id=brief_id,
                    version=1,
                    experiment_id=experiment_id,
                    workflow_id=workflow_id,
                    agent_id=agent_id,
                    kind=ArtifactKind.EXPERIMENT_BRIEF,
                    payload=payload,
                    created_by=context.operator_id,
                    created_at=now,
                ),
                command_key=_id(experiment_id, "brief-command"),
            )
        if idea_seed is not None:
            seed_id = _id(experiment_id, "seed")
            seed = await repo.artifact_row(context.engine, seed_id)
            if seed is None:
                receipt = await self.records.append_artifact(
                    ArtifactDraft(
                        id=seed_id,
                        logical_id=seed_id,
                        version=1,
                        experiment_id=experiment_id,
                        workflow_id=workflow_id,
                        agent_id=agent_id,
                        kind=ArtifactKind.IDEA_SEED,
                        payload={"origin": "USER_SUPPLIED", "statement": idea_seed},
                        created_by=context.operator_id,
                        created_at=now,
                    ),
                    command_key=_id(experiment_id, "seed-command"),
                )
                origin = ArtifactInput.from_receipt(receipt, role="SEED")
            else:
                if seed["payload"]["statement"] != idea_seed:
                    raise ExperimentError(409, "COMMAND_CONFLICT")
                origin = self._input(seed, "SEED")
            await self.records.create_cycle(
                experiment_id,
                seed=origin,
                command_key=_id(experiment_id, "cycle-command"),
            )
        return experiment_id

    @staticmethod
    def _input(row, role):
        return ArtifactInput(
            artifact_id=row["id"],
            kind=ArtifactKind(row["kind"]),
            version=row["version"],
            content_hash=row["content_hash"],
            role=role,
        )

    async def _require_owner(self, experiment_id):
        intake = await self.store.get(experiment_id, self.context.operator_id)
        if intake is None:
            raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
        return intake

    async def _require_draft(self, experiment_id):
        intake = await self._require_owner(experiment_id)
        if not intake["draft"]:
            raise ExperimentError(409, "EXPERIMENT_ALREADY_STARTED")
        return intake

    async def _result(self, experiment_id, key) -> dict:
        await self._require_owner(experiment_id)
        retained = await self.store.receipt(experiment_id, key)
        if retained is not None:
            return ExperimentSnapshot.model_validate(retained).model_dump()
        snapshot = ExperimentSnapshot.model_validate(await self.snapshot(experiment_id))
        retained = await self.store.receipt(
            experiment_id,
            key,
            snapshot.model_dump(mode="json"),
            expected_run_id=_id(key, "first-agent"),
        )
        return (
            ExperimentSnapshot.model_validate(retained).model_dump()
            if retained is not None
            else snapshot.model_dump()
        )

    async def _dispatch(
        self,
        experiment_id,
        key,
        *,
        discovery=False,
        started=False,
        regenerate=False,
        run_owned=False,
    ):
        if not await self.store.owns_command(experiment_id, key):
            return await self._result(experiment_id, key)
        if not run_owned:
            from alon_ai.services.agent_run_service import AgentRunService

            runs = AgentRunService(self.context)
            admitted = await runs.admit(
                experiment_id,
                AgentRunRequest(
                    task_kind="IDEA_DISCOVERY" if discovery else "IDEA_REFINEMENT",
                    command_key=key,
                ),
            )
            if admitted.status == "BLOCKED":
                blocked = await runs.get(admitted.run_id)
                await self.store.finish(
                    experiment_id, key, blocked_reason=blocked.blocked_reason
                )
                return await self._result(experiment_id, key)
            if (
                self.context.settings.provider_mode == "live"
                and self.context.idea_runtime_provider is not None
            ):
                return await self.snapshot(experiment_id)
            await runs.execute(
                admitted.run_id, intake_service=self, propagate_errors=True
            )
            return await self._result(experiment_id, key)
        try:
            if discovery:
                await discover_experiment(
                    self.context,
                    experiment_id,
                    RefineRequest(idempotency_key=_id(key, "first-agent")),
                    allow_regeneration=regenerate,
                )
            else:
                await IdeaService(self.context).refine(
                    experiment_id,
                    RefineRequest(idempotency_key=_id(key, "first-agent")),
                )
        except asyncio.CancelledError:
            await asyncio.shield(
                self.store.finish(
                    experiment_id,
                    key,
                    blocked_reason="INTAKE_RECONCILIATION_REQUIRED",
                    started=started and await self.store.has_refinement(experiment_id),
                )
            )
            raise
        except Exception as error:  # noqa: BLE001 - persist safe recovery state at the use-case boundary
            reason = (
                error.detail
                if isinstance(error, ExperimentError)
                else "INTAKE_UNAVAILABLE"
            )
            await self.store.finish(
                experiment_id,
                key,
                blocked_reason=reason,
                started=started and await self.store.has_refinement(experiment_id),
            )
            return await self._result(experiment_id, key)
        await self.store.finish(experiment_id, key, started=started)
        return await self._result(experiment_id, key)

    async def create(self, body: CreateExperimentRequest) -> dict:
        if body.idea_seed is None:
            raise ExperimentError(409, "IDEA_REQUIRED")
        experiment_id = await self._roots(body.command_key, body.idea_seed, draft=False)
        if not await self.store.claim(
            experiment_id, body.command_key, "START_SEED", body.model_dump(mode="json")
        ):
            return await self._dispatch(experiment_id, body.command_key, started=True)
        return await self._dispatch(experiment_id, body.command_key, started=True)

    async def generate(self, body: GenerateIdeaRequest) -> dict:
        experiment_id = await self._roots(
            body.command_key,
            None,
            draft=True,
            generation_guidance=body.generation_guidance,
        )
        if not await self.store.claim(
            experiment_id, body.command_key, "GENERATE", body.model_dump(mode="json")
        ):
            return await self._dispatch(experiment_id, body.command_key, discovery=True)
        return await self._dispatch(experiment_id, body.command_key, discovery=True)

    async def snapshot(self, experiment_id: UUID) -> dict:
        snapshot = await _read_experiment(self.context, experiment_id)
        if snapshot is None:
            raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
        intake = await self.store.get(experiment_id, self.context.operator_id)
        if intake is not None:
            pending = await self.store.pending(experiment_id)
            if pending is not None:
                run_id = _id(pending["command_key"], "first-agent")
                owns_latest = snapshot["latest_run_id"] == run_id
                terminal = owns_latest and snapshot["state"] in {
                    "AWAITING_REVIEW",
                    "AWAITING_SELECTION",
                    "REFINEMENT_FAILED",
                    "REFINEMENT_BLOCKED",
                    "DISCOVERY_FAILED",
                    "DISCOVERY_BLOCKED",
                    "IDEA_ACCEPTED",
                }
                stale = pending["created_at"] < datetime.now(UTC) - timedelta(
                    seconds=3690
                )
                if terminal or stale:
                    reason = (
                        None
                        if terminal
                        and snapshot["state"]
                        in {"AWAITING_REVIEW", "AWAITING_SELECTION", "IDEA_ACCEPTED"}
                        else "INTAKE_RECONCILIATION_REQUIRED"
                    )
                    await self.store.finish(
                        experiment_id,
                        pending["command_key"],
                        blocked_reason=reason,
                        started=pending["action"].startswith("START")
                        and await self.store.has_refinement(experiment_id),
                    )
                    intake = await self.store.get(
                        experiment_id, self.context.operator_id
                    )
                elif pending["action"] != "REVISE":
                    snapshot["latest_run_id"] = run_id
                    snapshot["state"] = (
                        "DISCOVERY_IN_PROGRESS"
                        if pending["action"] in {"GENERATE", "REGENERATE"}
                        else "REFINEMENT_IN_PROGRESS"
                    )
        history = await self.store.history(experiment_id) if intake else []
        history_payload = [
            {
                "artifact_id": r["id"],
                "version": r["version"],
                "parent_artifact_id": r["parent_artifact_id"],
                "title": r["payload"]["title"],
                "hypothesis": r["payload"]["hypothesis"],
                "idea_seed": r["payload"]["hypothesis"],
                "origin": "GENERATED" if r["run_id"] else "OPERATOR_EDIT",
                "run_id": r["run_id"],
            }
            for r in history
        ]
        if intake and intake["draft"]:
            known = {str(c["artifact_id"]) for c in snapshot["candidates"]}
            snapshot["candidates"] += [
                {
                    "artifact_id": r["id"],
                    "title": r["payload"]["title"],
                    "hypothesis": r["payload"]["hypothesis"],
                    "demand_status": "UNVERIFIED",
                    "uncertainties": ["Operator edit; demand remains unverified"],
                }
                for r in history
                if r["run_id"] is None and str(r["id"]) not in known
            ]
        state = snapshot["state"]
        blocked_reason = intake["blocked_reason"] if intake else None
        if blocked_reason and state in {"AWAITING_REVIEW", "IDEA_ACCEPTED"}:
            # A later successful governed retry supersedes the failed intake attempt.
            await self.store.clear_block(experiment_id)
            blocked_reason = None
        snapshot.update(
            draft=bool(intake and intake["draft"]),
            provider_mode=self.context.settings.provider_mode,
            stage="IDEA_REFINEMENT" if snapshot["cycle_id"] else "IDEA_DISCOVERY",
            stage_status="BLOCKED"
            if blocked_reason or "BLOCKED" in state or "FAILED" in state
            else "RUNNING"
            if "IN_PROGRESS" in state
            else "COMPLETE"
            if state == "IDEA_ACCEPTED"
            else "WAITING_FOR_INPUT",
            blocked_reason=blocked_reason,
            proposal_history=history_payload,
        )
        latest_run = await AgentRunRepository(self.context.engine).latest(
            experiment_id, self.context.operator_id
        )
        if (
            latest_run is not None
            and snapshot["latest_run_id"] != latest_run["run_id"]
            and latest_run["status"]
            in {
                "QUEUED",
                "RUNNING",
                "BLOCKED",
                "FAILED",
                "CANCELLED",
                "OUTCOME_UNKNOWN",
            }
        ):
            snapshot["latest_run_id"] = latest_run["run_id"]
            if snapshot["blocked_reason"]:
                pass
            elif latest_run["status"] in {"QUEUED", "RUNNING"}:
                snapshot["state"] = (
                    "DISCOVERY_IN_PROGRESS"
                    if latest_run["task_kind"] == "IDEA_DISCOVERY"
                    else "REFINEMENT_IN_PROGRESS"
                )
                snapshot["stage_status"] = "RUNNING"
            else:
                snapshot["stage_status"] = "BLOCKED"
                snapshot["blocked_reason"] = (
                    latest_run["blocked_reason"] or latest_run["status"]
                )
        return snapshot

    async def revise(self, experiment_id: UUID, body: ReviseProposalRequest) -> dict:
        await self._require_owner(experiment_id)
        replay_payload = dict(
            body.model_dump(mode="json"),
            revision_id=str(_id(body.command_key, "proposal-revision")),
        )
        if await self.store.replayed(
            experiment_id, body.command_key, "REVISE", replay_payload
        ):
            return await self._result(experiment_id, body.command_key)
        await self._require_draft(experiment_id)
        history = await self.store.history(experiment_id)
        source = next(
            (r for r in history if r["id"] == body.candidate_artifact_id), None
        )
        if source is None:
            raise ExperimentError(409, "CANDIDATE_NOT_IN_DISCOVERY")
        revision_id = _id(body.command_key, "proposal-revision")
        payload = dict(body.model_dump(mode="json"), revision_id=str(revision_id))
        if not await self.store.claim(
            experiment_id, body.command_key, "REVISE", payload
        ):
            return await self._result(experiment_id, body.command_key)
        try:
            await self.records.append_artifact(
                ArtifactDraft(
                    id=revision_id,
                    logical_id=revision_id,
                    version=1,
                    experiment_id=experiment_id,
                    workflow_id=source["workflow_id"],
                    agent_id=source["agent_id"],
                    kind=ArtifactKind.IDEA_CANDIDATE,
                    payload={
                        "title": body.idea_seed.strip()[:120],
                        "hypothesis": body.idea_seed,
                    },
                    created_by=self.context.operator_id,
                    created_at=datetime.now(UTC),
                ),
                inputs=(self._input(source, "REFINES"),),
                command_key=_id(body.command_key, "revision-command"),
            )
        except ProductRecordsDenied as error:
            await self.store.finish(
                experiment_id, body.command_key, blocked_reason=error.reason
            )
            raise ExperimentError(409, error.reason) from None
        await self.store.finish(experiment_id, body.command_key)
        return await self._result(experiment_id, body.command_key)

    async def start(self, experiment_id: UUID, body: StartProposalRequest) -> dict:
        await self._require_owner(experiment_id)
        if await self.store.replayed(
            experiment_id,
            body.command_key,
            "START_PROPOSAL",
            body.model_dump(mode="json"),
        ):
            return await self._result(experiment_id, body.command_key)
        intake = await self._require_draft(experiment_id)
        history = await self.store.history(experiment_id)
        if not any(row["id"] == body.candidate_artifact_id for row in history):
            raise ExperimentError(409, "CANDIDATE_NOT_IN_DISCOVERY")
        detail = await _read_experiment(self.context, experiment_id)
        assert detail is not None
        if detail["cycle_id"] is not None and (
            detail["selected_candidate_artifact_id"] != body.candidate_artifact_id
            or await self.store.has_refinement(experiment_id)
        ):
            raise ExperimentError(409, "REFINEMENT_RECONCILIATION_REQUIRED")
        if not await self.store.claim(
            experiment_id,
            body.command_key,
            "START_PROPOSAL",
            body.model_dump(mode="json"),
        ):
            return await self._result(experiment_id, body.command_key)
        try:
            if not intake["draft"]:
                raise ExperimentError(409, "EXPERIMENT_ALREADY_STARTED")
            detail = await _read_experiment(self.context, experiment_id)
            assert detail is not None
            if detail["cycle_id"] is not None:
                # Explicit retry after selection committed but no agent claim exists.
                if detail[
                    "selected_candidate_artifact_id"
                ] != body.candidate_artifact_id or await self.store.has_refinement(
                    experiment_id
                ):
                    raise ExperimentError(409, "REFINEMENT_RECONCILIATION_REQUIRED")
            else:
                await IdeaService(self.context).select(
                    experiment_id,
                    SelectCandidateRequest(
                        candidate_artifact_id=body.candidate_artifact_id,
                        reason="Operator selected this exact proposal revision to start the experiment.",
                        command_key=body.command_key,
                    ),
                )
        except ExperimentError as error:
            await self.store.finish(
                experiment_id, body.command_key, blocked_reason=error.detail
            )
            raise
        return await self._dispatch(experiment_id, body.command_key, started=True)

    async def regenerate(
        self, experiment_id: UUID, body: RegenerateIdeaRequest
    ) -> dict:
        await self._require_owner(experiment_id)
        payload = dict(
            body.model_dump(mode="json"),
            guidance_artifact_id=str(_id(body.command_key, "guidance-brief")),
            run_id=str(_id(body.command_key, "first-agent")),
        )
        if await self.store.replayed(
            experiment_id, body.command_key, "REGENERATE", payload
        ):
            return await self._result(experiment_id, body.command_key)
        await self._require_draft(experiment_id)
        history = await self.store.history(experiment_id)
        if body.candidate_artifact_id is not None and not any(
            row["id"] == body.candidate_artifact_id for row in history
        ):
            raise ExperimentError(409, "CANDIDATE_NOT_IN_DISCOVERY")
        if not await self.store.claim(
            experiment_id, body.command_key, "REGENERATE", payload
        ):
            return await self._result(experiment_id, body.command_key)
        try:
            history = await self.store.history(experiment_id)
            source = next(
                (row for row in history if row["id"] == body.candidate_artifact_id),
                None,
            )
            if body.candidate_artifact_id is not None and source is None:
                raise ExperimentError(409, "CANDIDATE_NOT_IN_DISCOVERY")
            detail = await _read_experiment(self.context, experiment_id)
            assert detail is not None
            _, roots = await repo.discovery_prior_and_roots(
                self.context.engine, experiment_id
            )
            assert roots is not None
            brief_id = _id(body.command_key, "guidance-brief")
            await self.records.append_artifact(
                ArtifactDraft(
                    id=brief_id,
                    logical_id=brief_id,
                    version=1,
                    experiment_id=experiment_id,
                    workflow_id=roots["id"],
                    agent_id=roots["agent_id"],
                    kind=ArtifactKind.EXPERIMENT_BRIEF,
                    payload=IntakePolicySnapshot(
                        budget_usd=detail["brief"]["budget_usd"],
                        guidance=source["payload"]["hypothesis"] if source else "",
                    ).model_dump(mode="json"),
                    created_by=self.context.operator_id,
                    created_at=datetime.now(UTC),
                ),
                inputs=(self._input(source, "GUIDANCE"),) if source else (),
                command_key=_id(body.command_key, "guidance-command"),
            )
        except (ExperimentError, ProductRecordsDenied) as error:
            reason = (
                error.detail if isinstance(error, ExperimentError) else error.reason
            )
            await self.store.finish(
                experiment_id, body.command_key, blocked_reason=reason
            )
            raise ExperimentError(409, reason) from None
        return await self._dispatch(
            experiment_id, body.command_key, discovery=True, regenerate=True
        )
