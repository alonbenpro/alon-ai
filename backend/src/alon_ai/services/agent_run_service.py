"""Operator admission, inspection and control of durable Idea runs."""

from decimal import Decimal
from uuid import UUID, uuid5

from alon_ai.agents.schemas.openai import canonical_json, sha256
from alon_ai.db.repositories.agent_run_steps import AgentRunStepRepository
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import ExperimentError, artifact_row
from alon_ai.db.repositories.intake import IntakeRepository
from alon_ai.db.repositories.openai_idea import OpenAIIdeaInputRepository
from alon_ai.db.repositories.openai_run import OpenAIRunStore
from alon_ai.services.experiments import (
    ExperimentContext,
    RefineRequest,
    _id,
    _read_experiment,
)
from alon_ai.services.ideas import IdeaService
from alon_ai.services.run_exchanges import resolve_exchange_evidence
from alon_ai.services.schemas.agent_runs import (
    AgentRunRequest,
    CancelRunRequest,
    CancelRunResult,
    OperatorProfileProjection,
    RejectRunRequest,
    ResolvedInput,
    RunEvent,
    RunEvents,
    RunReceipt,
    RunRef,
    RunResult,
    RunStep,
    RunView,
    UsageItem,
)
from alon_ai.workflows.schemas.runtime import DBOS_APPLICATION_VERSION


class AgentRunService:
    def __init__(self, context: ExperimentContext):
        self.context = context
        self.store = AgentRunRepository(context.engine)

    async def _pinned_inputs(self, experiment_id: UUID, task_kind: str):
        inputs = OpenAIIdeaInputRepository(self.context.engine)
        profile = await inputs.operator_profile(experiment_id)
        brief = await inputs.experiment_brief(experiment_id)
        if brief is None:
            raise ExperimentError(409, "EXPERIMENT_NOT_READY")
        if task_kind == "IDEA_DISCOVERY":
            source = brief
            role = "EXPERIMENT_BRIEF"
        else:
            detail = await _read_experiment(self.context, experiment_id)
            if detail is None or detail["cycle_id"] is None:
                raise ExperimentError(409, "CANDIDATE_SELECTION_REQUIRED")
            cycle, schema_version = await inputs.cycle_origin(
                experiment_id, detail["cycle_id"]
            )
            if schema_version is None:
                raise ExperimentError(409, "IDEA_INPUT_STALE")
            if cycle["purpose"] == "SAME_INTENT_RETURN":
                _returned, prior, feedback = await inputs.return_inputs(
                    experiment_id, detail["cycle_id"]
                )
                if prior is None or feedback is None:
                    raise ExperimentError(409, "IDEA_INPUT_STALE")
                return profile, [
                    {
                        "artifact_id": str(item["id"]),
                        "kind": item["kind"],
                        "version": item["version"],
                        "content_hash": item["content_hash"],
                        "role": role,
                    }
                    for item, role in (
                        (brief, "EXPERIMENT_BRIEF"),
                        (prior, "PRIOR_IDEA_BRIEF"),
                        (feedback, "RESEARCH_FEEDBACK"),
                    )
                ]
            source = await self.store.artifact(
                experiment_id,
                {
                    "artifact_id": cycle["seed_artifact_id"],
                    "kind": cycle["seed_kind"],
                    "version": cycle["seed_version"],
                    "content_hash": cycle["seed_hash"],
                },
            )
            role = "SEED" if cycle["seed_kind"] == "IDEA_SEED" else "SELECTED_CANDIDATE"
        if source is None:
            raise ExperimentError(409, "IDEA_INPUT_STALE")
        reference = {
            "artifact_id": str(source["id"]),
            "kind": source["kind"],
            "version": source["version"],
            "content_hash": source["content_hash"],
            "role": role,
        }
        brief_ref = {
            "artifact_id": str(brief["id"]),
            "kind": brief["kind"],
            "version": brief["version"],
            "content_hash": brief["content_hash"],
            "role": "EXPERIMENT_BRIEF",
        }
        return profile, [reference] if task_kind == "IDEA_DISCOVERY" else [
            brief_ref,
            reference,
        ]

    async def admit(
        self,
        experiment_id: UUID,
        body: AgentRunRequest,
        *,
        revision_inputs: list[dict] | None = None,
    ) -> RunRef:
        previous = await self.store.by_command(body.command_key)
        if previous is not None:
            if (
                previous["operator_id"] != self.context.operator_id
                or previous["experiment_id"] != experiment_id
                or previous["task_kind"] != body.task_kind
            ):
                raise ExperimentError(409, "COMMAND_CONFLICT")
            return RunRef.model_validate(
                {field: previous[field] for field in RunRef.model_fields}
            )
        detail = await _read_experiment(self.context, experiment_id)
        if detail is None:
            raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
        if body.task_kind == "IDEA_REFINEMENT" and revision_inputs is None:
            latest = await self.store.latest(experiment_id, self.context.operator_id)
            if latest is not None and any(
                ref["role"] == "OPERATOR_REVISION" for ref in latest["input_refs"]
            ):
                if detail["state"] == "REFINEMENT_FAILED" and not detail["retry_safe"]:
                    raise ExperimentError(409, "REFINEMENT_RECONCILIATION_REQUIRED")
                if (
                    detail["state"] != "REFINEMENT_FAILED"
                    or not detail["retry_safe"]
                    or detail["latest_run_id"] != latest["run_id"]
                    or latest["status"] != "FAILED"
                ):
                    raise ExperimentError(409, "REFINEMENT_NOT_ADMISSIBLE")
                async with self.store.revision_scope(
                    latest["run_id"], self.context.operator_id
                ):
                    current = await self.store.latest(
                        experiment_id, self.context.operator_id
                    )
                    if current is None or current["run_id"] != latest["run_id"]:
                        replay = await self.store.by_command(body.command_key)
                        if replay is None:
                            raise ExperimentError(409, "REFINEMENT_IN_PROGRESS")
                    return await self.admit(
                        experiment_id, body, revision_inputs=latest["input_refs"]
                    )
        if self.context.settings.idea_intake_budget_usd is None:
            raise ExperimentError(409, "INTAKE_BUDGET_REQUIRED")
        if body.task_kind == "IDEA_DISCOVERY":
            if detail["mode"] != "SYSTEM_DISCOVERY" or detail["cycle_id"] is not None:
                raise ExperimentError(409, "DISCOVERY_MODE_REQUIRED")
        elif revision_inputs is None and (
            detail["cycle_id"] is None
            or detail["state"]
            not in {
                "AWAITING_REFINEMENT",
                "REFINEMENT_FAILED",
            }
        ):
            raise ExperimentError(409, "REFINEMENT_NOT_ADMISSIBLE")
        profile, input_refs = await self._pinned_inputs(experiment_id, body.task_kind)
        if revision_inputs is not None:
            input_refs = revision_inputs
        run_id = _id(body.command_key, "first-agent")
        request_hash = sha256(
            canonical_json(
                {
                    "experiment_id": str(experiment_id),
                    "task_kind": body.task_kind,
                    "profile": [
                        str(profile.profile_id),
                        profile.version,
                        profile.content_hash,
                    ],
                    "input_refs": input_refs,
                    "runtime_config_hash": getattr(
                        self.context.idea_runtime_provider, "config_fingerprint", None
                    ),
                }
            )
        )
        row = await self.store.admit(
            {
                "run_id": run_id,
                "command_key": body.command_key,
                "experiment_id": experiment_id,
                "operator_id": self.context.operator_id,
                "task_kind": body.task_kind,
                "request_hash": request_hash,
                "input_refs": input_refs,
                "profile_id": profile.profile_id,
                "profile_version": profile.version,
                "profile_hash": profile.content_hash,
                "provider_mode": self.context.settings.provider_mode,
                "dbos_workflow_id": f"idea-{run_id}",
                "application_version": DBOS_APPLICATION_VERSION,
            }
        )
        blocked_reason = (
            "IDEA_RUNTIME_DISABLED"
            if self.context.settings.provider_mode == "disabled"
            else "LIVE_CONFIG_REQUIRED"
            if self.context.settings.provider_mode == "live"
            and self.context.idea_runtime_provider is None
            else None
        )
        if blocked_reason is not None:
            row = await self.store.finish(
                run_id, "BLOCKED", blocked_reason=blocked_reason
            )
        return RunRef.model_validate(
            {field: row[field] for field in RunRef.model_fields}
        )

    async def _resolved(self, row, *, strict: bool = True) -> list[ResolvedInput]:
        result = []
        for ref in row["input_refs"]:
            source = await self.store.artifact(row["experiment_id"], ref)
            if source is None:
                if strict:
                    raise ExperimentError(409, "IDEA_INPUT_STALE")
                result.append(ResolvedInput(**ref, payload=None))
            else:
                result.append(ResolvedInput(**ref, payload=source["payload"]))
        return result

    async def get(self, run_id: UUID) -> RunView:
        row = await self.store.owned(run_id, self.context.operator_id)
        product, intent, call, usage_rows, accepted = await self.store.details(
            run_id, row["task_kind"]
        )
        resolved = await self._resolved(row, strict=False)
        profile_row = await self.store.profile_projection(row)
        if profile_row is None:
            raise ExperimentError(409, "IDEA_INPUT_STALE")
        view = {field: row[field] for field in RunView.model_fields if field in row}
        diagnostic = next(
            (
                event["diagnostic"]
                for event in reversed(row["events"])
                if event.get("diagnostic") is not None
            ),
            None,
        )
        review_status = "ACCEPTED" if accepted else row["review_status"]
        phase = (
            "ACCEPTED"
            if review_status == "ACCEPTED"
            else "REJECTED"
            if review_status == "REJECTED"
            else "WAITING_FOR_OPERATOR"
            if row["status"] == "SUCCEEDED"
            else "ADMITTED"
            if row["status"] == "QUEUED"
            else "EXECUTING"
            if row["status"] == "RUNNING"
            else "OUTCOME_UNKNOWN"
            if row["status"] == "OUTCOME_UNKNOWN"
            else "CANCELLED"
            if row["status"] == "CANCELLED"
            else "BLOCKED"
        )
        steps = await AgentRunStepRepository(self.context.engine).list(run_id)
        case_step = next(
            (item for item in steps if item["kind"] == "ARTIFACT_SAVE"), None
        )
        research_status = (
            "NOT_STARTED"
            if case_step is None
            else "ASSESSED"
            if case_step["status"] == "SUCCEEDED"
            else "INCOMPLETE"
            if case_step["reason_code"] == "RESEARCH_INCOMPLETE"
            else "RUNNING"
            if case_step["status"] == "CLAIMED"
            else "OUTCOME_UNKNOWN"
        )
        summary = await artifact_row(
            self.context.engine, uuid5(run_id, "combined-case")
        )
        partial_options = []
        if research_status == "INCOMPLETE" and row["task_kind"] == "IDEA_DISCOVERY":
            for index in range(2):
                candidate = await artifact_row(
                    self.context.engine, _id(run_id, f"candidate-{index}")
                )
                if (
                    candidate is not None
                    and candidate["experiment_id"] == row["experiment_id"]
                ):
                    partial_options.append(
                        {"artifact_id": str(candidate["id"]), **candidate["payload"]}
                    )
        view.update(
            research_summary=summary["payload"] if summary else None,
            research_gaps=summary["payload"]["unresolved_questions"] if summary else [],
            partial_options=partial_options,
            steps=[
                RunStep.model_validate(
                    {field: step[field] for field in RunStep.model_fields}
                )
                for step in steps
            ],
            research_status=research_status,
            phase=phase,
            input_refs=resolved,
            resolved_inputs=resolved,
            output=product["advice"] if product else None,
            advice_source=product["advice_source"] if product else None,
            outcome=(intent["outcome"] if intent else row["outcome"]),
            model_identifier=intent["model_identifier"] if intent else None,
            receipt_id=call["id"] if call else None,
            pending_cost_usd=str(call["reserved"])
            if call
            and call["currency"] == "USD"
            and call["state"] not in {"FINAL", "RELEASED"}
            else None,
            actual_cost_usd=str(call["accrued"])
            if call
            and call["currency"] == "USD"
            and call["state"] in {"FINAL", "RELEASED"}
            and not any(item["knowledge"] == "UNAVAILABLE" for item in usage_rows)
            else None,
            usage=[
                UsageItem(
                    component=item["component"],
                    quantity=str(item["quantity"])
                    if item["quantity"] is not None
                    else None,
                    cost=str(item["cost"]) if item["cost"] is not None else None,
                    currency=item["currency"],
                    knowledge=item["knowledge"],
                )
                for item in usage_rows
            ],
            review_status=review_status,
            diagnostic=diagnostic,
            cancel_requested=row["cancel_requested_at"] is not None,
            operator_profile=OperatorProfileProjection(
                profile_id=profile_row["id"],
                version=profile_row["version"],
                content_hash=profile_row["content_hash"],
                capabilities=profile_row["capabilities"],
                constraints=profile_row["constraints"],
            ),
        )
        children = await AgentRunStepRepository(self.context.engine).receipts(run_id)
        calls = {
            item["call"]["id"]: item for item in children if item["call"] is not None
        }
        if calls:
            projected = []
            for item in calls.values():
                child = item["call"]
                superseded = {
                    usage["supersedes_id"]
                    for usage in item["usage"]
                    if usage["supersedes_id"]
                }
                latest = [
                    usage for usage in item["usage"] if usage["id"] not in superseded
                ]
                projected.append(
                    RunReceipt(
                        receipt_id=child["id"],
                        provider=child["provider"],
                        model_identifier=child["model_identifier"],
                        state=child["state"],
                        currency=child["currency"],
                        reserved=str(child["reserved"]),
                        accrued=str(child["accrued"]),
                        usage=[
                            UsageItem(
                                component=usage["component"],
                                quantity=str(usage["quantity"])
                                if usage["quantity"] is not None
                                else None,
                                cost=str(usage["cost"])
                                if usage["cost"] is not None
                                else None,
                                currency=usage["currency"],
                                knowledge=usage["knowledge"],
                            )
                            for usage in latest
                        ],
                    )
                )
            known = all(
                receipt.state in {"FINAL", "RELEASED"}
                and receipt.currency == "USD"
                and all(usage.knowledge == "FINAL" for usage in receipt.usage)
                for receipt in projected
            )
            pending = [
                receipt
                for receipt in projected
                if receipt.state not in {"FINAL", "RELEASED"}
            ]
            view.update(
                receipts=projected,
                receipt_id=None,
                model_identifier=next(
                    (
                        receipt.model_identifier
                        for receipt in projected
                        if receipt.model_identifier
                    ),
                    None,
                ),
                usage=[usage for receipt in projected for usage in receipt.usage],
                actual_cost_usd=str(
                    sum((Decimal(receipt.accrued) for receipt in projected), Decimal(0))
                )
                if known
                else None,
                pending_cost_usd=str(
                    sum((Decimal(receipt.reserved) for receipt in pending), Decimal(0))
                )
                if pending and all(receipt.currency == "USD" for receipt in pending)
                else None,
            )
        return RunView.model_validate(view)

    async def result(self, run_id: UUID) -> RunResult:
        view = await self.get(run_id)
        return RunResult(
            run_id=view.run_id,
            status=view.status,
            research_summary=view.research_summary,
            research_gaps=view.research_gaps,
            partial_options=view.partial_options,
            steps=view.steps,
            receipts=view.receipts,
            research_status=view.research_status,
            output=view.output,
            advice_source=view.advice_source,
            receipt_id=view.receipt_id,
            actual_cost_usd=view.actual_cost_usd,
            usage=view.usage,
            diagnostic=view.diagnostic,
        )

    async def events(self, run_id: UUID) -> RunEvents:
        row = await self.store.owned(run_id, self.context.operator_id)
        events = []
        for saved in row["events"]:
            event = RunEvent.model_validate(saved)
            if event.exchange is not None:
                event.exchange = await resolve_exchange_evidence(
                    event.exchange,
                    engine=self.context.engine,
                    run_id=run_id,
                    experiment_id=row["experiment_id"],
                )
            events.append(event)
        return RunEvents(events=events)

    async def cancel(self, run_id: UUID, body: CancelRunRequest) -> CancelRunResult:
        row = await self.store.cancel(
            run_id, self.context.operator_id, body.command_key
        )
        return CancelRunResult(
            run_id=run_id,
            requested=row["cancel_requested_at"] is not None,
            confirmed=row["cancel_confirmed"],
            status=row["status"],
        )

    async def reject(self, run_id: UUID, body: RejectRunRequest) -> RunView:
        await self.store.reject(
            run_id, self.context.operator_id, body.command_key, body.reason
        )
        return await self.get(run_id)

    async def execute(
        self, run_id: UUID, *, intake_service=None, propagate_errors: bool = False
    ) -> None:
        row = await self.store.get(run_id)
        if row is None or row["status"] != "QUEUED":
            return
        context = self.context
        if context.operator_id != row["operator_id"]:
            raise ExperimentError(404, "AGENT_RUN_NOT_FOUND")
        if row["provider_mode"] != context.settings.provider_mode:
            await self.store.finish(
                run_id, "BLOCKED", blocked_reason="RUN_PROVIDER_MODE_CHANGED"
            )
            return
        if row["application_version"] != DBOS_APPLICATION_VERSION:
            await self.store.finish(
                run_id, "BLOCKED", blocked_reason="RUN_APPLICATION_VERSION_CHANGED"
            )
            return
        expected_hash = sha256(
            canonical_json(
                {
                    "experiment_id": str(row["experiment_id"]),
                    "task_kind": row["task_kind"],
                    "profile": [
                        str(row["profile_id"]),
                        row["profile_version"],
                        row["profile_hash"],
                    ],
                    "input_refs": row["input_refs"],
                    "runtime_config_hash": getattr(
                        context.idea_runtime_provider, "config_fingerprint", None
                    ),
                }
            )
        )
        if row["request_hash"] != expected_hash:
            await self.store.finish(
                run_id, "BLOCKED", blocked_reason="RUN_CONFIGURATION_CHANGED"
            )
            return
        if not await self.store.start(run_id):
            return
        try:
            await self._resolved(row)
            current_profile = await OpenAIIdeaInputRepository(
                context.engine
            ).operator_profile(row["experiment_id"])
            if (
                current_profile.profile_id != row["profile_id"]
                or current_profile.version != row["profile_version"]
                or current_profile.content_hash != row["profile_hash"]
            ):
                raise ExperimentError(409, "IDEA_INPUT_STALE")
            intake_command = await IntakeRepository(context.engine).command(
                row["experiment_id"], row["command_key"]
            )
            if intake_command is not None:
                from alon_ai.services.intake import IntakeService

                action = intake_command["action"]
                result = await (intake_service or IntakeService(context))._dispatch(
                    row["experiment_id"],
                    row["command_key"],
                    discovery=action in {"GENERATE", "REGENERATE"},
                    started=action in {"START_SEED", "START_PROPOSAL"},
                    regenerate=action == "REGENERATE",
                    run_owned=True,
                )
            else:
                service = IdeaService(context)
                body = RefineRequest(idempotency_key=run_id)
                result = (
                    await service.discover(row["experiment_id"], body)
                    if row["task_kind"] == "IDEA_DISCOVERY"
                    else await service.refine(row["experiment_id"], body)
                )
            state = result["state"]
            status = (
                "BLOCKED"
                if result.get("stage_status") == "BLOCKED"
                else "SUCCEEDED"
                if state in {"AWAITING_REVIEW", "AWAITING_SELECTION"}
                else "BLOCKED"
                if "BLOCKED" in state
                else "FAILED"
            )
            reported_outcome = (
                result.get("outcome")
                or result.get("latest_outcome")
                or (
                    "SUCCEEDED"
                    if status == "SUCCEEDED"
                    else result.get("blocked_reason")
                )
            )
            await self.store.finish(
                run_id,
                status,
                outcome=str(reported_outcome) if reported_outcome else None,
                blocked_reason=None
                if status == "SUCCEEDED"
                else result.get("blocked_reason") or state,
            )
        except BaseException as error:
            durable = await OpenAIRunStore(context.engine).get(run_id)
            status = (
                "OUTCOME_UNKNOWN"
                if durable
                and durable.outcome in {"UNCERTAIN", "RECOVERING", "RESULT_UNAVAILABLE"}
                else "BLOCKED"
            )
            reason = (
                error.detail
                if isinstance(error, ExperimentError)
                else "IDEA_RUN_RECONCILIATION_REQUIRED"
            )
            await self.store.finish(run_id, status, blocked_reason=reason)
            if propagate_errors or isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise


async def queued_idea_run_bindings(engine):
    return await AgentRunRepository(engine).pending()


async def reconcile_incomplete_idea_runs(engine, *, mark_running: bool = True) -> None:
    """Resolve product facts after worker restart without resending provider work."""
    store = AgentRunRepository(engine)
    for row in await store.incomplete():
        product, intent, _call, _usage, _accepted = await store.details(
            row["run_id"], row["task_kind"]
        )
        state = product["state"] if product is not None else None
        if state == "SUCCEEDED":
            await store.finish(
                row["run_id"],
                "SUCCEEDED",
                outcome=intent["outcome"] if intent is not None else "SUCCEEDED",
            )
        elif state and ("FAILED" in state or "BLOCKED" in state):
            await store.finish(
                row["run_id"],
                "BLOCKED" if "BLOCKED" in state else "FAILED",
                outcome=intent["outcome"] if intent is not None else state,
                blocked_reason=state,
            )
        elif row["status"] == "RUNNING" and mark_running:
            await store.finish(
                row["run_id"],
                "OUTCOME_UNKNOWN",
                outcome=intent["outcome"] if intent is not None else None,
                blocked_reason="IDEA_RUN_RECONCILIATION_REQUIRED",
            )


async def run_admitted_idea_job(engine, settings, run_id: UUID) -> None:
    from alon_ai.bootstrap import (
        load_idea_runtime_provider,
        recorded_runtime_provisioner,
    )

    row = await AgentRunRepository(engine).get(run_id)
    if row is None:
        return
    if row["provider_mode"] != settings.provider_mode:
        await AgentRunRepository(engine).finish(
            run_id, "BLOCKED", blocked_reason="RUN_PROVIDER_MODE_CHANGED"
        )
        return
    if row["application_version"] != DBOS_APPLICATION_VERSION:
        await AgentRunRepository(engine).finish(
            run_id, "BLOCKED", blocked_reason="RUN_APPLICATION_VERSION_CHANGED"
        )
        return
    try:
        provider = load_idea_runtime_provider(settings)
    except RuntimeError:
        await AgentRunRepository(engine).finish(
            run_id, "BLOCKED", blocked_reason="LIVE_CONFIG_REQUIRED"
        )
        return
    context = ExperimentContext(
        engine,
        settings,
        row["operator_id"],
        idea_runtime_provider=provider,
        recorded_runtime_provisioner=recorded_runtime_provisioner,
    )
    await AgentRunService(context).execute(run_id)
