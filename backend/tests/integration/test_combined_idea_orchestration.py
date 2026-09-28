"""Native Pydantic execution through admitted intake; synthetic transport only."""

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_live_idea_runtime import reviewed_manifest
from test_operator_records import owner_and_profile
from test_pydantic_live_provision import TestSecrets, explicit_limits

from alon_ai.config import Settings
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.provider_usage.live_idea import build_live_combined_model_provider
from alon_ai.services.agent_run_service import AgentRunService
from alon_ai.services.combined_idea import CombinedIdeaRuntime
from alon_ai.services.experiments import CreateExperimentRequest, ExperimentContext
from alon_ai.services.intake import IntakeService
from alon_ai.services.live_idea_provision import (
    make_authority_bundle,
    register_authority,
)
from alon_ai.services.research import ResearchService
from alon_ai.services.schemas.intake import GenerateIdeaRequest

pytestmark = pytest.mark.integration


class NoResearchPort:
    async def resolve_references(self, refs):
        assert not refs
        return ()


@asynccontextmanager
async def guard():
    yield


def assessment(version: str | None) -> dict[str, Any]:
    return {
        "status": "ASSESSED",
        "idea_version_ref": version,
        "brief": {
            "title": "Reminder workflow",
            "customer": "Clinics",
            "problem": "Missed appointments",
            "core_intent": "Appointment reminders",
            "intent_relationship": "PRESERVES_CORE_INTENT",
            "material_pivot": False,
            "buyer": {"segment": "Clinics", "role": "Manager"},
            "service_hypothesis": "Reminder service",
            "value_hypothesis": "Reduce missed visits",
            "assumptions": ["Demand unknown"],
            "exclusions": ["Clinical work"],
            "research_questions": ["Will clinics pay?"],
            "grounding_refs": ["SEED"],
            "uncertainties": ["Price unknown"],
        },
        "findings": [
            {
                "topic": "CUSTOMER_PROBLEM",
                "basis": "UNKNOWN",
                "claim": "Demand is unverified",
                "source_refs": [],
                "confidence": "LOW",
                "limitations": ["No external evidence"],
            }
        ],
        "coverage": ["CUSTOMER_PROBLEM"],
        "gaps": ["Demand evidence"],
        "contradictions": [],
        "source_refs": [],
        "recommendation": "INCONCLUSIVE",
    }


@pytest.mark.parametrize(
    ("discovery", "idea_seed"),
    [
        (False, "Appointment reminders"),
        (False, "  Appointment reminders \n"),
        (False, '"' * 4000),
        (True, None),
    ],
)
async def test_native_run_reuses_intake_and_persists_truthful_outcome(
    governance_engine, discovery, idea_seed, monkeypatch
):
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
    inputs = []
    errors = []
    original_run = CombinedIdeaRuntime._run

    async def observe_run(self, *args, **kwargs):
        try:
            return await original_run(self, *args, **kwargs)
        except Exception as error:
            errors.append(repr(error))
            raise

    monkeypatch.setattr(CombinedIdeaRuntime, "_run", observe_run)
    from alon_ai.services import ideas

    original_refine = ideas.refine_experiment

    async def observe_refine(*args, **kwargs):
        try:
            return await original_refine(*args, **kwargs)
        except Exception as error:
            errors.append(repr(error.__cause__))
            raise

    monkeypatch.setattr(ideas, "refine_experiment", observe_refine)
    if not discovery:
        from sqlalchemy.exc import DBAPIError

        from alon_ai.db.repositories import experiments as experiment_repository

        original_finish = experiment_repository.finish_refinement

        async def reject_forged_hash(
            engine, run_id, experiment_id, operation_id, success, retry_safe, payload
        ):
            if success:
                with pytest.raises(DBAPIError, match="successful governed run"):
                    await original_finish(
                        engine,
                        run_id,
                        experiment_id,
                        operation_id,
                        success,
                        retry_safe,
                        {**payload, "title": "Uncommitted replacement"},
                    )
            return await original_finish(
                engine,
                run_id,
                experiment_id,
                operation_id,
                success,
                retry_safe,
                payload,
            )

        monkeypatch.setattr(
            experiment_repository, "finish_refinement", reject_forged_hash
        )

    async def respond(messages, info):
        prompt = next(
            part.content
            for message in messages
            for part in message.parts
            if isinstance(part, UserPromptPart)
        )
        assert isinstance(prompt, str)
        input = json.loads(prompt)
        inputs.append(input)
        output = (
            {"status": "INCOMPLETE", "options": [], "gaps": ["No permitted sources"]}
            if discovery
            else assessment(input["idea_version_ref"])
        )
        output = (
            {"result": {"kind": "IncompleteDiscovery", "data": output}}
            if discovery
            else output
        )
        return ModelResponse(
            [TextPart(json.dumps(output))],
            usage=RequestUsage(input_tokens=20, output_tokens=5),
        )

    native = build_live_combined_model_provider(
        bundle.config,
        TestSecrets(),
        limits=explicit_limits(),
        model_factory=lambda secret: FunctionModel(respond),
    )
    settings = Settings(
        _env_file=None, provider_mode="live", idea_intake_budget_usd=Decimal("0.50")
    )
    context = None

    async def provider(engine, **arguments):
        provisioned = await native(engine, **arguments, dispatch_guard=guard)
        row = await AgentRunRepository(engine).get(arguments["run_id"])
        config = SimpleNamespace(
            research_bindings=(), model_dump_json=lambda: '{"test":"synthetic-only"}'
        )
        return (
            CombinedIdeaRuntime(context, config, provisioned, NoResearchPort(), row),
            provisioned.attribution,
            "OPENAI",
        )

    context = ExperimentContext(
        governance_engine, settings, owner.id, idea_runtime_provider=provider
    )
    intake = IntakeService(context)
    key = uuid4()
    snapshot = (
        await intake.generate(
            GenerateIdeaRequest(
                command_key=key, generation_guidance="  Exact generation guidance \n"
            )
        )
        if discovery
        else await intake.create(
            CreateExperimentRequest(command_key=key, idea_seed=idea_seed)
        )
    )
    run = await AgentRunRepository(governance_engine).by_command(key)
    await AgentRunService(context).execute(run["run_id"], propagate_errors=True)
    view = await AgentRunService(context).get(run["run_id"])
    assert len(inputs) == 1, (view.blocked_reason, errors)
    if not discovery:
        assert inputs[0]["idea_text"] == idea_seed
    else:
        assert inputs[0]["generation_guidance"] == "  Exact generation guidance \n"
    assert inputs[0]["operation"] == ("DISCOVER" if discovery else "SELECTED_DEEPEN")
    assert any(
        step.kind == "MODEL_REQUEST" and step.provider_call_id for step in view.steps
    )
    if discovery:
        assert view.status == "BLOCKED"
        assert view.research_status == "INCOMPLETE", (view.blocked_reason, errors)
        assert view.blocked_reason == "RESEARCH_INCOMPLETE"
        assert view.output is None
    else:
        assert view.status == "SUCCEEDED", (view.blocked_reason, errors)
        assert view.research_status == "ASSESSED"
        assert view.output is not None
        assert view.output["core_intent"] == "Appointment reminders"
        case = await ResearchService(context).get_case(snapshot["experiment_id"])
        assert case.finding_count == 1
        assert (
            case.subjects[0].findings[0].observation.evidence_status == "INCONCLUSIVE"
        )


@pytest.mark.parametrize(
    "discovery", [False, True, "incomplete", "selected", "revision"]
)
async def test_native_tool_loop_uses_governed_brave_and_firecrawl_and_publishes_case(
    governance_engine, monkeypatch, discovery
):
    from datetime import timedelta

    import httpx
    import test_governance
    from pydantic_ai.messages import ToolCallPart

    from alon_ai.integrations.live_research import (
        ResearchCapabilityBinding,
        ResearchRunPolicy,
    )
    from alon_ai.integrations.schemas.provider import Capability, UsageComponent
    from alon_ai.provider_usage.live_research import GovernedLiveResearchPort
    from alon_ai.services import combined_idea
    from alon_ai.services.combined_idea import (
        CombinedIdeaConfig,
        build_combined_idea_provider,
    )

    _, owner, _ = await owner_and_profile(governance_engine)
    now = datetime.now(UTC)
    monkeypatch.setattr(test_governance, "datetime", lambda *args, **kwargs: now)
    _, _, _, brave_config, brave_grant, _ = await test_governance.seed(
        governance_engine, transient=True
    )
    _, _, _, capture_config, capture_grant, _ = await test_governance.seed(
        governance_engine,
        capability=Capability.FIRECRAWL_PAGE_CAPTURE,
        price_components=(UsageComponent.CAPTURE_PAGE,),
    )
    manifest = reviewed_manifest(owner.id, now)
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
    config = CombinedIdeaConfig(
        version=1,
        model=bundle.config,
        limits=explicit_limits(model_request_limit=5),
        research_policy=ResearchRunPolicy(
            approved_by=owner.id,
            effective_at=now - timedelta(seconds=1),
            expires_at=now + timedelta(hours=1),
            max_calls=3,
            max_pages=2,
            timeout_seconds=90,
            max_spend_usd=Decimal("0.25"),
            max_results=2,
            max_pdf_bytes=100000,
            max_pdf_pages=1,
            max_text_chars=10000,
            pdf_cpu_seconds=2,
            pdf_memory_bytes=256000000,
            pdf_wall_seconds=5,
        ),
        research_bindings=tuple(
            ResearchCapabilityBinding(
                config=cfg.model_copy(update={"secret_handle": "synthetic-research"}),
                grant=grant,
            )
            for cfg, grant in (
                (brave_config, brave_grant),
                (capture_config, capture_grant),
            )
        ),
    )
    errors = []
    from alon_ai.services import ideas

    original_refine = ideas.refine_experiment

    async def observe_refine(*args, **kwargs):
        try:
            return await original_refine(*args, **kwargs)
        except Exception as error:
            errors.append(repr(error.__cause__))
            raise

    monkeypatch.setattr(ideas, "refine_experiment", observe_refine)
    original_discover = ideas.discover_experiment

    async def observe_discover(*args, **kwargs):
        try:
            return await original_discover(*args, **kwargs)
        except Exception as error:
            errors.append(repr(error.__cause__))
            raise

    monkeypatch.setattr(ideas, "discover_experiment", observe_discover)
    from alon_ai.services import intake as intake_module

    monkeypatch.setattr(intake_module, "discover_experiment", observe_discover)
    captured = []
    network = []

    def transport(request):
        network.append(request.url.host)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://example.com/",
                            "description": "A public clinic workflow",
                        }
                    ]
                }
            }
            if request.method == "GET"
            else {
                "success": True,
                "data": {
                    "markdown": "Clinics send appointment reminders manually. Starter reminder plan: USD 29.99 per month."
                },
            },
        )

    class ControlledPort(GovernedLiveResearchPort):
        def __init__(self, *args, **kwargs):
            super().__init__(
                *args,
                **kwargs,
                brave_transport=httpx.MockTransport(transport),
                firecrawl_transport=httpx.MockTransport(transport),
                resolver=lambda _: ("8.8.8.8",),
            )

        async def capture(self, experiment_id, request):
            result = await super().capture(experiment_id, request)
            captured.extend(result)
            return result

    monkeypatch.setattr(combined_idea, "GovernedLiveResearchPort", ControlledPort)
    calls = []
    per_run_calls = {}
    native_inputs = []

    async def respond(messages, info):
        calls.append(messages)
        raw_prompt = next(
            part.content
            for message in messages
            for part in message.parts
            if isinstance(part, UserPromptPart)
        )
        assert isinstance(raw_prompt, str)
        native_input = json.loads(raw_prompt)
        scope_key = native_input["approved_limits_ref"]
        per_run_calls[scope_key] = per_run_calls.get(scope_key, 0) + 1
        index = per_run_calls[scope_key]
        if index == 1:
            native_inputs.append(native_input)
        is_discovery = native_input["operation"] == "DISCOVER"
        if index == 1:
            parts = [
                ToolCallPart(
                    "search_web",
                    {"query": "clinic appointment workflow", "limit": 1},
                    tool_call_id="search",
                )
            ]
        elif index == 2:
            parts = [
                ToolCallPart(
                    "capture_page",
                    {"url": "https://example.com/"},
                    tool_call_id="capture",
                )
            ]
        elif index == 3:
            assert captured
            parts = [
                ToolCallPart(
                    "read_saved_evidence",
                    {"retained_id": str(captured[-1].retained_id)},
                    tool_call_id="read",
                )
            ]
        else:
            raw = next(
                part.content
                for message in messages
                for part in message.parts
                if isinstance(part, UserPromptPart)
            )
            assert isinstance(raw, str)
            output: dict[str, Any] = assessment(json.loads(raw).get("idea_version_ref"))
            if (
                not is_discovery
                and native_input["operation"] in {"SELECTED_DEEPEN", "REFINE"}
                and discovery
            ):
                output["brief"]["grounding_refs"] = ["SELECTED_CANDIDATE"]
            output["source_refs"] = [str(captured[-1].retained_id)]
            output["findings"][0].update(
                basis="OBSERVED",
                claim="Manual reminder work appears in one published clinic workflow.",
                source_refs=[str(captured[-1].retained_id)],
            )
            if is_discovery:
                options = [
                    {
                        "title": f"Clinic workflow {index}",
                        "customer": "Clinics",
                        "problem": f"Manual reminder stage {index}",
                        "approach": "Administrative workflow software",
                        "commercial_reasoning": "Time savings may create willingness to pay; not verified.",
                        "alternatives": ["Manual reminders"],
                        "risks": ["Unknown willingness to pay"],
                        "source_refs": output["source_refs"],
                        "findings": output["findings"],
                        "unknowns": ["Buyer budget"],
                    }
                    for index in range(2 if discovery == "incomplete" else 3)
                ]
                output = {
                    "status": "INCOMPLETE"
                    if discovery == "incomplete"
                    else "SUCCEEDED",
                    "options": options,
                }
                if discovery == "incomplete":
                    output["gaps"] = ["A third defensible option was not supported"]
                output = {
                    "result": {
                        "kind": "IncompleteDiscovery"
                        if discovery == "incomplete"
                        else "ResearchedCandidateSet",
                        "data": output,
                    }
                }
            if not is_discovery:
                output["price_observations"] = [
                    {
                        "subject": "Published reminder plan",
                        "kind": "EXACT",
                        "currency": "USD",
                        "amount_low": "29.99",
                        "unit": "month",
                        "package": "Starter",
                        "observed_date": "2026-09-28",
                        "source_refs": [str(captured[-1].retained_id)],
                    },
                    {
                        "subject": "Enterprise plan",
                        "kind": "NOT_FOUND",
                        "source_refs": [],
                    },
                ]
                output["contradictions"] = [
                    "Self-reported interest conflicts with the missing spending evidence."
                ]
            parts = [TextPart(json.dumps(output))]
        return ModelResponse(
            parts, usage=RequestUsage(input_tokens=20, output_tokens=5)
        )

    original_factory = build_live_combined_model_provider
    monkeypatch.setattr(
        combined_idea,
        "build_live_combined_model_provider",
        lambda config, secrets, **kwargs: original_factory(
            config, secrets, **kwargs, model_factory=lambda _: FunctionModel(respond)
        ),
    )

    class ScopedSyntheticSecrets(TestSecrets):
        def for_consumer(self, consumer):
            return self

        def research_store(self):
            return self

    settings = Settings(
        _env_file=None, provider_mode="live", idea_intake_budget_usd=Decimal("0.50")
    )
    provider = build_combined_idea_provider(config, ScopedSyntheticSecrets(), settings)
    context = ExperimentContext(
        governance_engine, settings, owner.id, idea_runtime_provider=provider
    )
    intake = IntakeService(context)
    key = uuid4()
    snapshot = (
        await intake.generate(GenerateIdeaRequest(command_key=key))
        if discovery
        else await intake.create(
            CreateExperimentRequest(command_key=key, idea_seed="Appointment reminders")
        )
    )
    row = await AgentRunRepository(governance_engine).by_command(key)
    await AgentRunService(context).execute(row["run_id"], propagate_errors=True)
    result = await AgentRunService(context).get(row["run_id"])
    assert result.status == ("BLOCKED" if discovery == "incomplete" else "SUCCEEDED"), (
        result.blocked_reason,
        errors,
        len(calls),
        network,
    )
    assert network == ["api.search.brave.com", "api.firecrawl.dev"]
    assert len(calls) == 4
    assert len(result.receipts) == 6
    assert {receipt.provider for receipt in result.receipts} == {
        "OPENAI",
        "BRAVE",
        "FIRECRAWL",
    }
    assert result.actual_cost_usd is not None, (
        result.blocked_reason,
        errors,
        [receipt.model_dump() for receipt in result.receipts],
    )
    case = await ResearchService(context).get_case(snapshot["experiment_id"])
    assert case.finding_count == (
        14 if discovery == "incomplete" else 21 if discovery else 4
    )
    if discovery == "incomplete":
        assert result.research_status == "INCOMPLETE"
        assert len(result.partial_options) == 2
        assert result.research_gaps == ["A third defensible option was not supported"]
    elif discovery:
        assert result.output is not None
        assert len(result.output["candidates"]) == 3
    saved = next(
        item
        for item in case.subjects[0].findings
        if item.observation.dimension == "CUSTOMER_PAIN"
        and item.observation.evidence_status == "SUPPORTED"
    )
    assert any("confidence: LOW" in note for note in saved.observation.limitations)
    if not discovery:
        prices = [
            item
            for item in case.subjects[0].findings
            if item.observation.dimension == "PRICING"
        ]
        assert len(prices) == 2
        observed = next(
            item for item in prices if item.observation.evidence_status == "SUPPORTED"
        )
        assert json.loads(observed.observation.finding)["amount_low"] == "29.99"
        assert observed.sources[0].reference == captured[0]
        missing = next(
            item
            for item in prices
            if item.observation.evidence_status == "INCONCLUSIVE"
        )
        assert missing.sources == []
        assert any(
            "Self-reported interest" in item.observation.finding
            for item in case.subjects[0].findings
        )
        assert result.research_summary is not None
        assert any(
            "CUSTOMER_PROBLEM" in note
            for note in result.research_summary["limitations"]
        )
    assert saved.observation.evidence_status == "SUPPORTED"
    assert saved.sources[0].reference == captured[0]
    assert "manual reminder" in saved.observation.claim.lower()
    if discovery:
        assert any(
            item.observation.claim == "Commercial reasoning"
            and item.observation.finding
            == "Time savings may create willingness to pay; not verified."
            and item.observation.evidence_status == "INCONCLUSIVE"
            and not item.sources
            for item in case.subjects[0].findings
        )
        refreshed = await ResearchService(context).get_case(snapshot["experiment_id"])
        assert refreshed == case
    if discovery in {"selected", "revision"}:
        from dataclasses import replace

        from fastapi.testclient import TestClient
        from pydantic import SecretStr
        from test_minimal_intake import login
        from test_operator_access import ORIGIN

        from alon_ai.api.app import create_app
        from alon_ai.services.auth import hash_password

        selected_id = case.subjects[0].subject.artifact_id
        revision_text = "  Exact revised guidance: focus on reminder scheduling for small clinics. \n"
        api_settings = settings.model_copy(
            update={
                "database_url": SecretStr(
                    governance_engine.url.render_as_string(hide_password=False)
                ),
                "operator_auth_subject": owner.auth_subject,
                "operator_password_hash": SecretStr(hash_password("test-password")),
                "session_signing_key": SecretStr("a" * 64),
            }
        )
        app = create_app(api_settings)
        with TestClient(app) as client:
            app.state.experiment_service_factory = replace(
                app.state.experiment_service_factory, idea_runtime_provider=provider
            )
            login(client)
            if discovery == "revision":
                revision_response = client.post(
                    f"/operator/ideas/{snapshot['experiment_id']}/revisions",
                    headers=ORIGIN,
                    json={
                        "command_key": str(uuid4()),
                        "candidate_artifact_id": str(selected_id),
                        "idea_seed": revision_text,
                    },
                )
                assert revision_response.status_code == 200, revision_response.text
                selected_id = UUID(
                    revision_response.json()["proposal_history"][-1]["artifact_id"]
                )
            start_key = uuid4()
            start_response = client.post(
                f"/operator/ideas/{snapshot['experiment_id']}/start",
                headers=ORIGIN,
                json={
                    "command_key": str(start_key),
                    "candidate_artifact_id": str(selected_id),
                },
            )
            assert start_response.status_code == 200, start_response.text
        selected_run = await AgentRunRepository(governance_engine).by_command(start_key)
        assert selected_run is not None and selected_run["status"] == "QUEUED"
        await AgentRunService(context).execute(
            selected_run["run_id"], propagate_errors=True
        )
        selected_result = await AgentRunService(context).get(selected_run["run_id"])
        assert selected_result.status == "SUCCEEDED", selected_result.blocked_reason
        assert native_inputs[-1]["idea_version_ref"] == str(selected_id)
        assert native_inputs[-1]["operation"] == (
            "REFINE" if discovery == "revision" else "SELECTED_DEEPEN"
        )
        if discovery == "revision":
            assert native_inputs[-1]["revision_guidance"] == revision_text
            assert native_inputs[-1]["idea_text"] == revision_text
        after = await ResearchService(context).get_case(snapshot["experiment_id"])
        selected_subject = next(
            item for item in after.subjects if item.subject.artifact_id == selected_id
        )
        assert any(
            finding.observation.run_id == str(selected_run["run_id"])
            and finding.sources
            for finding in selected_subject.findings
        )


async def test_candidate_selection_holds_source_run_lock_through_publication(
    governance_engine, monkeypatch
):
    import asyncio

    from test_governance import wait_for_pg_lock

    from alon_ai.bootstrap import recorded_runtime_provisioner
    from alon_ai.db.repositories.records import ProductRecordsRepository
    from alon_ai.services.experiments import SelectCandidateRequest
    from alon_ai.services.ideas import IdeaService

    _, owner, _ = await owner_and_profile(governance_engine)
    settings = Settings(
        _env_file=None, provider_mode="fake", idea_intake_budget_usd=Decimal("0.50")
    )
    context = ExperimentContext(
        governance_engine,
        settings,
        owner.id,
        recorded_runtime_provisioner=recorded_runtime_provisioner,
    )
    snapshot = await IntakeService(context).generate(
        GenerateIdeaRequest(command_key=uuid4())
    )
    run_id = snapshot["latest_run_id"]
    entered, release = asyncio.Event(), asyncio.Event()
    original = ProductRecordsRepository.select_idea_candidate

    async def paused(self, *args, **kwargs):
        entered.set()
        await release.wait()
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(ProductRecordsRepository, "select_idea_candidate", paused)
    selecting = asyncio.create_task(
        IdeaService(context).select(
            snapshot["experiment_id"],
            SelectCandidateRequest(
                command_key=uuid4(),
                candidate_artifact_id=snapshot["candidates"][0]["artifact_id"],
                reason="Review candidate",
            ),
        )
    )
    await entered.wait()
    rejecting = asyncio.create_task(
        AgentRunRepository(governance_engine).reject(
            run_id, owner.id, uuid4(), "Reject later"
        )
    )
    try:
        await wait_for_pg_lock(governance_engine, rejecting)
        assert not rejecting.done()
    finally:
        release.set()
    assert (await selecting)["state"] == "AWAITING_REFINEMENT"
    assert (await rejecting)["review_status"] == "REJECTED"
