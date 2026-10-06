"""Private exchange reads reuse current licensed retention without provider effects."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4, uuid5

import httpx
import pytest
from fastapi import FastAPI
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from sqlalchemy import func, select, update
from test_governance import add_event
from test_idea_run_steps import _run
from test_live_research_port import port, setup

from alon_ai.agents.tools.research import SavedEvidenceExcerpt
from alon_ai.api.dependencies import get_agent_run_service
from alon_ai.api.routes.agent_runs import router
from alon_ai.config import Settings
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import ExperimentError, claim_refinement
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.agent_runs import runs
from alon_ai.integrations.schemas.provider import Capability, FirecrawlCaptureRequest
from alon_ai.policies.provider_rights import GrantEvent, GrantEventKind
from alon_ai.services.agent_run_service import AgentRunService
from alon_ai.services.experiments import ExperimentContext
from alon_ai.services.intake import IntakeService
from alon_ai.services.run_exchanges import (
    RunExchange,
    model_request_exchange,
    model_response_exchange,
    tool_result_payload,
)
from alon_ai.services.schemas.agent_runs import AgentRunRequest
from alon_ai.services.schemas.records import ArtifactDraft, ArtifactInput, ArtifactKind
from alon_ai.services.schemas.research import MarketResearchReportPayload

pytestmark = pytest.mark.integration


async def test_revision_trace_reads_only_exact_pinned_prior_report_lineage(
    governance_engine, monkeypatch
):
    import test_governance

    now = datetime.now(UTC)
    monkeypatch.setattr(test_governance, "datetime", lambda *args, **kwargs: now)
    values = await setup(
        governance_engine, capability=Capability.FIRECRAWL_PAGE_CAPTURE
    )
    _, _, attr, _, _, parent_run, owner, _ = values
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "success": True,
                "data": {"markdown": "prior licensed evidence"},
            },
        )
    )
    research = port(
        values,
        transport,
        firecrawl_transport=transport,
        resolver=lambda _: ("8.8.8.8",),
    )
    refs = await research.capture(
        attr.experiment_id,
        FirecrawlCaptureRequest(
            capability=Capability.FIRECRAWL_PAGE_CAPTURE,
            url="https://example.com/",
        ),
    )
    assert isinstance(refs, tuple) and refs[0].retained_id is not None
    excerpt = await research.read_saved_evidence(
        attr.experiment_id, refs[0].retained_id, max_chars=14
    )
    store = AgentRunRepository(governance_engine)
    parent = await store.get(parent_run)
    seed_ref = next(ref for ref in parent["input_refs"] if ref["role"] == "SEED")
    seed = await store.artifact(attr.experiment_id, seed_ref)
    from alon_ai.db.tables import records

    async with governance_engine.connect() as connection:
        cycle = await connection.scalar(
            select(records.cycles.c.id).where(
                records.cycles.c.experiment_id == attr.experiment_id
            )
        )
    await claim_refinement(
        governance_engine,
        attr.experiment_id,
        cycle,
        parent_run,
        attr.operation_run_id,
        "OPENAI",
    )
    async with governance_engine.begin() as connection:
        await connection.execute(
            records.workflows.insert().values(
                id=attr.workflow_run_id,
                experiment_id=attr.experiment_id,
                role="MARKET_RESEARCH",
                created_at=now,
            )
        )
    writer = ProductRecordsRepository(governance_engine)
    report_id = uuid5(parent_run, "combined-case")
    report = await writer.append_artifact(
        ArtifactDraft(
            id=report_id,
            logical_id=report_id,
            version=1,
            experiment_id=attr.experiment_id,
            workflow_id=attr.workflow_run_id,
            operation_id=attr.operation_run_id,
            kind=ArtifactKind.MARKET_RESEARCH_REPORT,
            payload=MarketResearchReportPayload(
                finding="Prior assessment", limitations=[], unresolved_questions=[]
            ).model_dump(mode="json"),
            created_by=owner,
            created_at=now,
        ),
        command_key=uuid4(),
    )
    revision_id = uuid4()
    revision = await writer.append_artifact(
        ArtifactDraft(
            id=revision_id,
            logical_id=seed["logical_id"],
            version=seed["version"] + 1,
            experiment_id=attr.experiment_id,
            kind=ArtifactKind.IDEA_SEED,
            payload=seed["payload"],
            created_by=owner,
            created_at=now,
        ),
        inputs=(
            ArtifactInput.model_validate_json(json.dumps(seed_ref)).model_copy(
                update={"role": "SUPERSEDES"}
            ),
        ),
        command_key=uuid4(),
    )
    revision_ref = ArtifactInput.from_receipt(
        revision, role="OPERATOR_REVISION"
    ).model_dump(mode="json", exclude={"schema_version"})
    report_ref = ArtifactInput.from_receipt(report, role="PRIOR_RESEARCH").model_dump(
        mode="json", exclude={"schema_version"}
    )
    payload, omissions = tool_result_payload(
        "read_saved_evidence", {"max_chars": 14}, excerpt
    )
    context = ExperimentContext(
        governance_engine,
        Settings(
            _env_file=None, provider_mode="fake", idea_intake_budget_usd=Decimal(1)
        ),
        owner,
    )
    service = AgentRunService(context)
    other_experiment = await IntakeService(context)._roots(
        uuid4(), "Separate experiment", draft=False
    )
    for target_experiment, inputs, available in (
        (attr.experiment_id, [revision_ref, report_ref], True),
        (attr.experiment_id, [revision_ref], False),
        (attr.experiment_id, [report_ref], False),
        (
            attr.experiment_id,
            [revision_ref, {**report_ref, "content_hash": "0" * 64}],
            False,
        ),
        (
            attr.experiment_id,
            [revision_ref, {**report_ref, "version": report_ref["version"] + 1}],
            False,
        ),
        (
            attr.experiment_id,
            [{**revision_ref, "content_hash": "0" * 64}, report_ref],
            False,
        ),
        (other_experiment, [revision_ref, report_ref], False),
    ):
        child = uuid4()
        await store.admit(
            {
                **{
                    key: parent[key]
                    for key in (
                        "operator_id",
                        "experiment_id",
                        "task_kind",
                        "profile_id",
                        "profile_version",
                        "profile_hash",
                        "provider_mode",
                        "application_version",
                    )
                },
                "run_id": child,
                "experiment_id": target_experiment,
                "command_key": uuid4(),
                "request_hash": "a" * 64,
                "input_refs": inputs,
                "dbos_workflow_id": f"idea-{child}",
            }
        )
        await store.record_activity(
            child,
            "TOOL_RESPONSE",
            exchange=RunExchange(
                tool_name="read_saved_evidence",
                tool_call_id="prior-read",
                status="COMPLETED",
                payload=payload,
                omissions=omissions,
            ),
        )
        exchange = (await service.events(child)).events[-1].exchange
        assert exchange is not None
        assert exchange.payload["availability"] == (
            "AVAILABLE" if available else "UNAVAILABLE"
        )
        if available:
            assert exchange.payload["text"] == "prior licensed"
        else:
            assert "text" not in exchange.payload


async def test_private_events_api_preserves_exact_failed_output_and_legacy_unavailability(
    governance_engine,
):
    run_id, _experiment_id, context = await _run(governance_engine)
    store = AgentRunRepository(governance_engine)
    actual = "  Websites for restaurants\n"
    await store.record_activity(
        run_id,
        "MODEL_REQUEST",
        exchange=model_request_exchange(
            1,
            "controlled-model",
            [
                ModelRequest(
                    [UserPromptPart(actual)], instructions="Pinned real instructions"
                )
            ],
            ModelRequestParameters(),
            {"max_tokens": 1000},
        ),
    )
    raw = '{"price":{"amount":"$12/mo","kind":"OBSERVED"}}'
    await store.record_activity(
        run_id,
        "MODEL_RESPONSE",
        exchange=model_response_exchange(
            1,
            ModelResponse([TextPart(raw)], finish_reason="length"),
            failed=True,
        ),
    )
    service = AgentRunService(context)
    app = FastAPI()
    app.include_router(router, prefix="/operator")
    app.dependency_overrides[get_agent_run_service] = lambda: service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/operator/agent-runs/{run_id}/events")
        assert response.status_code == 200, response.text
        events = response.json()["events"]
        assert (
            events[0]["exchange"] is None
        )  # legacy admission was never a captured model prompt
        request = events[-2]["exchange"]
        assert request["payload"]["messages"][0]["parts"][0]["content"] == actual
        assert (
            request["payload"]["messages"][0]["instructions"]
            == "Pinned real instructions"
        )
        assert events[-1]["exchange"]["status"] == "FAILED"
        assert events[-1]["exchange"]["payload"]["parts"][0]["content"] == raw
        assert (
            await client.get(f"/operator/agent-runs/{run_id}/events")
        ).json() == response.json()
    async with governance_engine.connect() as connection:
        assert await connection.scalar(select(func.count()).select_from(gov.calls)) == 0
    foreign = ExperimentContext(governance_engine, context.settings, uuid4())
    with pytest.raises(ExperimentError) as denied:
        await AgentRunService(foreign).events(run_id)
    assert denied.value.status_code == 404


@pytest.mark.parametrize("deny", ["expired", "revoked"])
async def test_source_excerpt_read_checks_current_rights_and_never_copies_source_into_events(
    governance_engine, deny, monkeypatch
):
    import test_governance

    current = datetime.now(UTC)
    monkeypatch.setattr(test_governance, "datetime", lambda *args, **kwargs: current)
    values = await setup(
        governance_engine, capability=Capability.FIRECRAWL_PAGE_CAPTURE
    )
    _, admin, attr, binding, now, run_id, owner_id, _ = values
    network = []

    def respond(request):
        network.append(request.url.host)
        return httpx.Response(
            200,
            json={"success": True, "data": {"markdown": "licensed captured evidence"}},
        )

    transport = httpx.MockTransport(respond)
    research = port(
        values,
        transport,
        firecrawl_transport=transport,
        resolver=lambda _: ("8.8.8.8",),
    )
    references = await research.capture(
        attr.experiment_id,
        FirecrawlCaptureRequest(
            capability=Capability.FIRECRAWL_PAGE_CAPTURE,
            url="https://example.com/",
        ),
    )
    assert isinstance(references, tuple)
    ref = references[0]
    assert ref.retained_id is not None
    excerpt = await research.read_saved_evidence(
        attr.experiment_id, ref.retained_id, max_chars=12
    )
    assert isinstance(excerpt, SavedEvidenceExcerpt)
    payload, omissions = tool_result_payload(
        "read_saved_evidence", {"max_chars": 12}, excerpt
    )
    await AgentRunRepository(governance_engine).record_activity(
        run_id,
        "TOOL_RESPONSE",
        exchange=RunExchange(
            tool_name="read_saved_evidence",
            tool_call_id="evidence-1",
            status="COMPLETED",
            payload=payload,
            omissions=omissions,
        ),
    )
    context = ExperimentContext(
        governance_engine,
        Settings(
            environment="test",
            provider_mode="fake",
            idea_intake_budget_usd=Decimal(1),
        ),
        owner_id,
    )
    service = AgentRunService(context)
    events = await service.events(run_id)
    exchange = events.events[-1].exchange
    assert exchange is not None
    assert exchange.payload["availability"] == "AVAILABLE", json.dumps(exchange.payload)
    assert exchange.payload["text"] == "licensed cap"
    assert exchange.payload["availability"] == "AVAILABLE"
    assert (await service.events(run_id)).model_dump() == events.model_dump()
    assert network == ["api.firecrawl.dev"]
    async with governance_engine.connect() as connection:
        saved = await connection.scalar(
            select(runs.c.events).where(runs.c.run_id == run_id)
        )
        assert "licensed cap" not in json.dumps(saved)
        before = await connection.scalar(select(func.count()).select_from(gov.calls))

    # The same reference cannot expose content when copied into another owned run.
    other_experiment = await IntakeService(context)._roots(
        uuid4(), "Different seed", draft=False
    )
    other_run = (
        await service.admit(
            other_experiment,
            AgentRunRequest(
                task_kind="IDEA_REFINEMENT",
                command_key=uuid4(),
            ),
        )
    ).run_id
    await AgentRunRepository(governance_engine).record_activity(
        other_run,
        "TOOL_RESPONSE",
        exchange=RunExchange(
            tool_name="read_saved_evidence",
            status="COMPLETED",
            payload=payload,
        ),
    )
    other_events = await service.events(other_run)
    other_exchange = other_events.events[-1].exchange
    assert other_exchange is not None
    assert other_exchange.payload["availability"] == "UNAVAILABLE"
    assert "text" not in other_exchange.payload

    if deny == "expired":
        async with governance_engine.begin() as connection:
            await connection.execute(
                update(gov.retained)
                .where(gov.retained.c.id == ref.retained_id)
                .values(
                    expires_at=datetime.now(UTC) - timedelta(seconds=1),
                )
            )
    else:
        await add_event(
            admin,
            GrantEvent(
                event_id=uuid4(),
                grant_id=binding.grant.grant_id,
                grant_version=binding.grant.version,
                kind=GrantEventKind.REVOKED,
                effective_at=now,
                actor_id=uuid4(),
                evidence_ref=uuid4(),
            ),
        )
    denied = (await service.events(run_id)).events[-1].exchange
    assert denied is not None
    assert denied.payload["availability"] == "UNAVAILABLE"
    assert "text" not in denied.payload
    assert denied.omissions
    assert network == ["api.firecrawl.dev"]
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(select(func.count()).select_from(gov.calls))
            == before
        )
