"""Exact operator revisions stay separate from automatic correction cycles."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_minimal_intake import configured_app

from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.tables import records
from alon_ai.services.agent_run_service import AgentRunService
from alon_ai.services.experiments import CreateExperimentRequest, ExperimentContext
from alon_ai.services.ideas import IdeaService
from alon_ai.services.intake import IntakeService
from alon_ai.services.schemas.idea_revisions import IdeaRevisionRequest


async def ready(engine):
    app, operator = await configured_app(engine)
    from alon_ai.provider_usage.recorded_idea import provision_recorded_seeded_runtime

    context = ExperimentContext(
        engine,
        app.state.settings,
        operator,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    snapshot = await IntakeService(context).create(
        CreateExperimentRequest(
            idea_seed="Appointment intake assistant", command_key=uuid4()
        )
    )
    return context, snapshot


async def test_revision_replay_pins_exact_instructions_and_preserves_review(
    governance_engine,
):
    context, before = await ready(governance_engine)
    request = IdeaRevisionRequest(
        command_key=uuid4(),
        run_id=before["latest_run_id"],
        instructions="  Avoid medical-record integrations.\n",
    )
    service = IdeaService(context)
    first = await service.revise_brief(before["experiment_id"], request)
    assert first == await service.revise_brief(before["experiment_id"], request)
    view = await AgentRunService(context).get(first.run_id)
    refs = {ref.role: ref for ref in view.resolved_inputs}
    assert refs["REVISION_GUIDANCE"].payload is not None
    assert refs["PRIOR_IDEA_BRIEF"].payload is not None
    assert refs["REVISION_GUIDANCE"].payload["statement"] == request.instructions
    assert (
        refs["PRIOR_IDEA_BRIEF"].payload["core_intent"]
        == before["advice"]["core_intent"]
    )
    assert refs["OPERATOR_REVISION"].version == 2
    assert first.revised_run_id == request.run_id
    assert first.command_key == request.command_key
    assert first.status == "QUEUED"
    previous = await AgentRunService(context).get(request.run_id)
    assert previous.output is not None
    assert {
        key: value for key, value in previous.output.items() if key != "schema_version"
    } == before["advice"]
    assert previous.review_status == "PENDING"
    with pytest.raises(ExperimentError, match="IDEA_REVIEW_STALE"):
        await AgentRunRepository(governance_engine).claim_acceptance(
            request.run_id, before["experiment_id"], context.operator_id, uuid4()
        )
    after = await IntakeService(context).snapshot(before["experiment_id"])
    assert after["cycle_id"] == before["cycle_id"]
    assert after["accepted_brief"] is None
    assert after["latest_run_id"] == first.run_id
    async with governance_engine.connect() as connection:
        assert (
            len(
                (
                    await connection.execute(
                        select(records.cycles).where(
                            records.cycles.c.experiment_id == before["experiment_id"]
                        )
                    )
                ).all()
            )
            == 1
        )
    with pytest.raises(ExperimentError, match="COMMAND_CONFLICT"):
        await service.revise_brief(
            before["experiment_id"],
            request.model_copy(update={"instructions": "Different change"}),
        )


async def test_concurrent_revision_commands_do_not_fork_review(governance_engine):
    context, before = await ready(governance_engine)
    service = IdeaService(context)
    results = await asyncio.gather(
        *(
            service.revise_brief(
                before["experiment_id"],
                IdeaRevisionRequest(
                    command_key=uuid4(),
                    run_id=before["latest_run_id"],
                    instructions=text,
                ),
            )
            for text in ("Avoid integrations", "Focus on scheduling")
        ),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, BaseException) for result in results) == 1
    assert sum(isinstance(result, ExperimentError) for result in results) == 1
    old = await AgentRunRepository(governance_engine).get(before["latest_run_id"])
    assert old["review_status"] == "PENDING"


async def test_saved_prior_evidence_requires_explicit_read_and_current_rights(
    governance_engine,
):
    import httpx
    from test_governance import add_event
    from test_live_research_port import Secrets, setup

    from alon_ai.integrations.schemas.provider import (
        Capability,
        FirecrawlCaptureRequest,
    )
    from alon_ai.policies.provider_rights import GrantEvent, GrantEventKind
    from alon_ai.provider_usage.live_research import GovernedLiveResearchPort
    from alon_ai.provider_usage.schemas.accounting import AccountingDenied

    repo, admin, attr, binding, now, run_id, operator, policy = await setup(
        governance_engine, capability=Capability.FIRECRAWL_PAGE_CAPTURE
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "prior retained evidence",
                    "metadata": {"url": "https://example.com/"},
                },
            },
        )
    )
    kwargs = {
        "operator_id": operator,
        "attribution": attr,
        "policy": policy,
        "bindings": {binding.config.intended_use.capability: binding},
        "firecrawl_transport": transport,
        "resolver": lambda _: ("8.8.8.8",),
    }
    old = GovernedLiveResearchPort(repo, Secrets(), run_id=run_id, **kwargs)
    captured = await old.capture(
        attr.experiment_id,
        FirecrawlCaptureRequest(
            capability=Capability.FIRECRAWL_PAGE_CAPTURE, url="https://example.com/"
        ),
    )
    assert isinstance(captured, tuple)
    retained_id = captured[0].retained_id
    assert retained_id is not None
    later = GovernedLiveResearchPort(repo, Secrets(), run_id=uuid4(), **kwargs)
    with pytest.raises(AccountingDenied):
        await later.resolve_references((str(retained_id),))
    with pytest.raises(AccountingDenied):
        await later.read_saved_evidence(uuid4(), retained_id, max_chars=50)
    excerpt = await later.read_saved_evidence(
        attr.experiment_id, retained_id, max_chars=50
    )
    assert await later.resolve_references((str(retained_id),)) == (excerpt.reference,)
    await add_event(
        admin,
        GrantEvent(
            event_id=uuid4(),
            grant_id=binding.grant.grant_id,
            grant_version=1,
            kind=GrantEventKind.REVOKED,
            effective_at=now,
            actor_id=uuid4(),
            evidence_ref=uuid4(),
        ),
    )
    with pytest.raises(AccountingDenied):
        await later.resolve_references((str(retained_id),))


@pytest.mark.parametrize("return_stage", [False, True, "retry"])
async def test_operator_revision_runs_native_refinement_and_preserves_versions(
    governance_engine,
    return_stage,
    monkeypatch,
):
    import json
    from datetime import UTC, datetime
    from decimal import Decimal
    from types import SimpleNamespace

    from pydantic_ai.messages import ModelResponse, TextPart, UserPromptPart
    from pydantic_ai.models.function import FunctionModel
    from pydantic_ai.usage import RequestUsage
    from test_combined_idea_orchestration import NoResearchPort, assessment, guard
    from test_live_idea_runtime import reviewed_manifest
    from test_operator_records import owner_and_profile
    from test_pydantic_live_provision import TestSecrets, explicit_limits

    from alon_ai.config import Settings
    from alon_ai.provider_usage.live_idea import build_live_combined_model_provider
    from alon_ai.services.combined_idea import CombinedIdeaRuntime
    from alon_ai.services.live_idea_provision import (
        make_authority_bundle,
        register_authority,
    )
    from alon_ai.services.research import ResearchService

    _, owner, _ = await owner_and_profile(governance_engine)
    manifest = reviewed_manifest(owner.id, datetime.now(UTC))
    manifest = manifest.model_copy(
        update={
            "prices": (
                manifest.prices[0].model_copy(update={"max_quantity": Decimal(100000)}),
                manifest.prices[1],
            )
        }
    )
    bundle = make_authority_bundle(manifest)
    await register_authority(governance_engine, bundle)
    prompts = []

    async def respond(messages, info):
        prompt = next(
            part.content
            for message in messages
            for part in message.parts
            if isinstance(part, UserPromptPart)
        )
        assert isinstance(prompt, str)
        parsed = json.loads(prompt)
        prompts.append(parsed)
        result = assessment(parsed["idea_version_ref"])
        if parsed["origin_stage"] == "RESEARCH_FEEDBACK_REFINEMENT":
            result["brief"]["grounding_refs"] = [
                "PRIOR_IDEA_BRIEF",
                "RESEARCH_FEEDBACK",
            ]
        if parsed["operation"] == "REFINE":
            result["brief"]["exclusions"] = ["Medical-record integrations"]
        return ModelResponse(
            [TextPart(json.dumps(result))],
            usage=RequestUsage(input_tokens=20, output_tokens=5),
        )

    native = build_live_combined_model_provider(
        bundle.config,
        TestSecrets(),
        limits=explicit_limits(),
        model_factory=lambda _: FunctionModel(respond),
    )
    context = None

    async def provider(engine, **arguments):
        provisioned = await native(engine, **arguments, dispatch_guard=guard)
        row = await AgentRunRepository(engine).get(arguments["run_id"])
        config = SimpleNamespace(
            research_bindings=(),
            research_policy=SimpleNamespace(
                max_results=20,
                max_calls=2,
                max_pages=1,
                max_pdf_pages=1,
                max_spend_usd=Decimal("0.25"),
                timeout_seconds=90,
            ),
            model_dump_json=lambda: '{"test":"revision"}',
            model_dump=lambda **kwargs: {"test": "revision"},
        )
        return (
            CombinedIdeaRuntime(context, config, provisioned, NoResearchPort(), row),
            provisioned.attribution,
            "OPENAI",
        )

    context = ExperimentContext(
        governance_engine,
        Settings(
            _env_file=None, provider_mode="live", idea_intake_budget_usd=Decimal("0.50")
        ),
        owner.id,
        idea_runtime_provider=provider,
    )
    intake = IntakeService(context)
    first_key = uuid4()
    snapshot = await intake.create(
        CreateExperimentRequest(
            command_key=first_key, idea_seed="Appointment reminders"
        )
    )
    runs = AgentRunService(context)
    initial = await runs.store.by_command(first_key)
    await runs.execute(initial["run_id"], propagate_errors=True)
    original_view = await runs.get(initial["run_id"])
    assert original_view.status == "SUCCEEDED"
    assert original_view.output is not None
    returns_before = []
    returned = None
    if return_stage is True:
        from test_research_origins import research_verdict, return_feedback

        from alon_ai.db.repositories.experiments import artifact_row
        from alon_ai.db.repositories.records import ProductRecordsRepository
        from alon_ai.services.experiments import AcceptRequest
        from alon_ai.services.schemas.agent_runs import AgentRunRequest
        from alon_ai.services.schemas.records import ArtifactInput, ArtifactKind

        accepted = await IdeaService(context).accept(
            snapshot["experiment_id"],
            AcceptRequest(
                run_id=initial["run_id"],
                command_key=uuid4(),
                intent_relationship="PRESERVES_CORE_INTENT",
                intent_confirmed=True,
                intent_rationale="Reviewed initial idea",
            ),
        )
        source = await artifact_row(
            governance_engine, accepted["idea_brief_artifact_id"]
        )
        idea = SimpleNamespace(
            artifact_id=source["id"],
            kind=ArtifactKind.IDEA_BRIEF,
            version=source["version"],
            content_hash=source["content_hash"],
        )
        from test_product_records import register_test_operator

        await register_test_operator(governance_engine)
        import test_research_origins
        from test_product_records import artifact

        async def current_put(repo, experiment_id, kind, payload, **kwargs):
            draft = artifact(experiment_id, kind, payload).model_copy(
                update={"created_at": datetime.now(UTC), "created_by": owner.id}
            )
            return await repo.append_artifact(draft, command_key=uuid4(), **kwargs)

        monkeypatch.setattr(test_research_origins, "put", current_put)
        import test_product_records

        def owned_artifact(*args, **kwargs):
            return artifact(*args, **kwargs).model_copy(
                update={"created_at": datetime.now(UTC), "created_by": owner.id}
            )

        monkeypatch.setattr(test_product_records, "artifact", owned_artifact)
        records_store = ProductRecordsRepository(governance_engine)
        original_disposition = records_store.record_disposition

        async def owned_disposition(*args, **kwargs):
            kwargs["decided_by"] = owner.id
            return await original_disposition(*args, **kwargs)

        monkeypatch.setattr(records_store, "record_disposition", owned_disposition)

        async def commit_verdict(*args, **kwargs):
            kwargs["committed_by"] = owner.id
            return await ProductRecordsRepository.commit_verdict(
                records_store, *args, **kwargs
            )

        monkeypatch.setattr(records_store, "commit_verdict", commit_verdict)
        verdict, report, recommendation = await research_verdict(
            records_store,
            snapshot["experiment_id"],
            SimpleNamespace(id=snapshot["cycle_id"]),
            idea,
            "REFINE_SAME_IDEA",
        )
        feedback = await return_feedback(
            records_store, snapshot["experiment_id"], idea, report, recommendation
        )
        returned = await records_store.start_same_intent_refinement_return(
            verdict.id,
            feedback=ArtifactInput.from_receipt(feedback, role="RESEARCH_FEEDBACK"),
            command_key=uuid4(),
        )
        returned_run = await runs.admit(
            snapshot["experiment_id"],
            AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4()),
        )
        await runs.execute(returned_run.run_id, propagate_errors=True)
        initial = await runs.store.get(returned_run.run_id)
        original_view = await runs.get(returned_run.run_id)
        assert original_view.output is not None
        assert original_view.status == "SUCCEEDED"
        async with governance_engine.connect() as connection:
            returns_before = (
                (
                    await connection.execute(
                        select(records.returns).where(
                            records.returns.c.experiment_id == snapshot["experiment_id"]
                        )
                    )
                )
                .mappings()
                .all()
            )
        assert len(returns_before) == 1
    previous_prompt_count = len(prompts)
    body = IdeaRevisionRequest(
        command_key=uuid4(),
        run_id=initial["run_id"],
        instructions="Avoid medical-record integrations.",
    )
    admitted = await IdeaService(context).revise_brief(snapshot["experiment_id"], body)
    command_run_id = admitted.run_id
    if return_stage == "retry":
        from alon_ai.agents.runtime import OpenAIExecution
        from alon_ai.agents.schemas.openai import Route
        from alon_ai.db.repositories.openai_run import OpenAIRunOutcome
        from alon_ai.services import (
            experiments as experiment_module,
        )
        from alon_ai.services import (
            ideas as ideas_module,
        )
        from alon_ai.services.schemas.agent_runs import AgentRunRequest

        original_refine = CombinedIdeaRuntime.refine_cycle

        async def stopped(self, *args, **kwargs):
            return OpenAIExecution(Route.CHEAP, OpenAIRunOutcome.REFUSED, None, None)

        async def settled_failure(*args):
            return args[1] == command_run_id

        # Isolate the existing settled-call proof boundary: no new provider request
        # is made by this controlled failed execution.
        monkeypatch.setattr(CombinedIdeaRuntime, "refine_cycle", stopped)
        monkeypatch.setattr(ideas_module, "_confirmed_safe_retry", settled_failure)
        await runs.execute(admitted.run_id, propagate_errors=True)
        failed_view = await runs.get(admitted.run_id)
        assert failed_view.status == "FAILED"
        with pytest.raises(ExperimentError, match="REFINEMENT_RECONCILIATION_REQUIRED"):
            await runs.admit(
                snapshot["experiment_id"],
                AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4()),
            )
        monkeypatch.setattr(experiment_module, "_confirmed_safe_retry", settled_failure)
        monkeypatch.setattr(CombinedIdeaRuntime, "refine_cycle", original_refine)
        admitted = await runs.admit(
            snapshot["experiment_id"],
            AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4()),
        )
        assert (await runs.store.get(admitted.run_id))["input_refs"] == (
            await runs.store.get(command_run_id)
        )["input_refs"]
    await runs.execute(admitted.run_id, propagate_errors=True)
    revised = await runs.get(admitted.run_id)
    assert revised.status == "SUCCEEDED", revised.blocked_reason
    assert revised.output is not None
    assert len(prompts) == previous_prompt_count + 1
    assert prompts[-1]["operation"] == "REFINE"
    assert prompts[-1]["revision_guidance"] == body.instructions
    assert prompts[-1]["idea_version_ref"] != prompts[0]["idea_version_ref"]
    assert (
        json.loads(prompts[-1]["prior_research_summary"])["PRIOR_IDEA_BRIEF"][
            "core_intent"
        ]
        == original_view.output["core_intent"]
    )
    assert revised.output["exclusions"] == ["Medical-record integrations"]
    assert (await runs.get(initial["run_id"])).output == original_view.output
    case = await ResearchService(context).get_case(snapshot["experiment_id"])
    assert {str(item.subject.artifact_id) for item in case.subjects} >= {
        prompts[0]["idea_version_ref"],
        prompts[-1]["idea_version_ref"],
    }
    replay = await IdeaService(context).revise_brief(snapshot["experiment_id"], body)
    assert replay.run_id == command_run_id
    await runs.execute(replay.run_id)
    assert len(prompts) == previous_prompt_count + 1
    if return_stage is True:
        async with governance_engine.connect() as connection:
            returns_after = (
                (
                    await connection.execute(
                        select(records.returns).where(
                            records.returns.c.experiment_id == snapshot["experiment_id"]
                        )
                    )
                )
                .mappings()
                .all()
            )
        assert returns_after == returns_before
        assert returned is not None
        assert (await intake.snapshot(snapshot["experiment_id"]))[
            "cycle_id"
        ] == returned.id
        returned_context = json.loads(prompts[-1]["prior_research_summary"])
        assert returned_context["research_feedback"]["change"]
        assert (
            returned_context["prior_idea_brief"]["exclusions"]
            == original_view.output["exclusions"]
        )
    assert (await intake.snapshot(snapshot["experiment_id"]))["accepted_brief"] is None
    from alon_ai.services.experiments import AcceptRequest

    accepted = await IdeaService(context).accept(
        snapshot["experiment_id"],
        AcceptRequest(
            run_id=admitted.run_id,
            command_key=uuid4(),
            intent_relationship="NARROWS_CORE_INTENT",
            intent_confirmed=True,
            intent_rationale="The requested integration exclusion preserves the reminder idea.",
        ),
    )
    assert accepted["state"] == "IDEA_ACCEPTED"
    assert (await runs.get(admitted.run_id)).review_status == "ACCEPTED"


async def test_revision_http_is_authenticated_and_replayable(governance_engine):
    from fastapi.testclient import TestClient
    from test_minimal_intake import login
    from test_operator_access import ORIGIN

    app, _ = await configured_app(governance_engine)
    with TestClient(app) as client:
        route = f"/operator/experiments/{uuid4()}/idea-revisions"
        body = {
            "command_key": str(uuid4()),
            "run_id": str(uuid4()),
            "instructions": "Avoid integrations",
        }
        assert client.post(route, json=body, headers=ORIGIN).status_code == 401
        login(client)
        original = client.post(
            "/operator/experiments",
            json={
                "idea_seed": "Appointment intake assistant",
                "command_key": str(uuid4()),
            },
            headers=ORIGIN,
        ).json()
        route = f"/operator/experiments/{original['experiment_id']}/idea-revisions"
        body["run_id"] = original["latest_run_id"]
        assert (
            client.post(
                route, json={**body, "instructions": "  "}, headers=ORIGIN
            ).status_code
            == 422
        )
        response = client.post(route, json=body, headers=ORIGIN)
        assert response.status_code == 200, response.text
        assert response.json()["revised_run_id"] == body["run_id"]
        assert response.json()["command_key"] == body["command_key"]
        assert client.post(route, json=body, headers=ORIGIN).json() == response.json()
        assert (
            client.post(
                route,
                json={**body, "instructions": "Different request"},
                headers=ORIGIN,
            ).status_code
            == 409
        )
