"""Real governance and durable research steps; all network transport is controlled."""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine
from test_governance import add_event, seed
from test_idea_run_steps import _run

from alon_ai.agents.tools.research import TransientSearchUrls, UnavailableResearchResult
from alon_ai.db.repositories.accounting import (
    GovernanceProvisioner,
    GovernanceRepository,
)
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.agent_run_steps import steps
from alon_ai.db.tables.agent_runs import runs
from alon_ai.integrations.live_research import (
    ResearchCapabilityBinding,
    ResearchRunPolicy,
)
from alon_ai.integrations.schemas.provider import (
    BraveSearchRequest,
    CallAttribution,
    Capability,
    FirecrawlCaptureRequest,
    ProviderErrorCode,
    ProviderFailure,
    UsageComponent,
)
from alon_ai.policies.provider_rights import GrantEvent, GrantEventKind
from alon_ai.provider_usage.live_research import GovernedLiveResearchPort
from alon_ai.provider_usage.schemas.accounting import AccountingDenied
from alon_ai.services.run_diagnostics import diagnostic_for_error

pytestmark = pytest.mark.integration

type ResearchFixture = tuple[
    GovernanceRepository,
    GovernanceProvisioner,
    CallAttribution,
    ResearchCapabilityBinding,
    datetime,
    UUID,
    UUID,
    ResearchRunPolicy,
]


class Secrets:
    def get(self, handle):
        assert handle == "research-test"
        return SecretStr("test-secret")


async def setup(
    engine: AsyncEngine,
    *,
    transient: bool = False,
    price: Decimal = Decimal(".001"),
    capability: Capability = Capability.BRAVE_WEB_COVERAGE,
) -> ResearchFixture:
    run_id, experiment_id, context = await _run(engine)
    repo, admin, original, config, grant, now = await seed(
        engine,
        transient=transient,
        price=price,
        capability=capability,
        price_components=(UsageComponent.CAPTURE_PAGE,)
        if capability is Capability.FIRECRAWL_PAGE_CAPTURE
        else (UsageComponent.REQUEST,),
    )
    attr = original.model_copy(
        update={
            "experiment_id": experiment_id,
            "workflow_run_id": uuid4(),
            "operation_run_id": uuid4(),
        }
    )
    await admin.scope(attr)
    config = config.model_copy(
        update={
            "id": uuid4(),
            "workflow_id": attr.workflow_run_id,
            "secret_handle": "research-test",
        }
    )
    await admin.config(config)
    await admin.budgets(
        attr,
        provider=grant.provider,
        currencies=("USD", "ILS"),
        limit=Decimal(1),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )
    async with engine.begin() as connection:
        await connection.execute(
            update(runs)
            .where(runs.c.run_id == run_id)
            .values(status="RUNNING", started_at=now)
        )
    policy = ResearchRunPolicy(
        approved_by=context.operator_id,
        effective_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(hours=1),
        max_calls=4,
        max_pages=4,
        timeout_seconds=120,
        max_spend_usd=Decimal(1),
        max_results=10,
        max_pdf_bytes=1000000,
        max_pdf_pages=2,
        max_text_chars=10000,
        pdf_cpu_seconds=2,
        pdf_memory_bytes=256_000_000,
        pdf_wall_seconds=5,
    )
    binding = ResearchCapabilityBinding(config=config, grant=grant)
    return repo, admin, attr, binding, now, run_id, context.operator_id, policy


def search(query="market pain"):
    return BraveSearchRequest(
        capability=Capability.BRAVE_WEB_COVERAGE, query=SecretStr(query), limit=1
    )


def port(
    values: ResearchFixture, transport: httpx.AsyncBaseTransport, **updates
) -> GovernedLiveResearchPort:
    repo, _, attr, binding, _, run_id, operator_id, policy = values
    return GovernedLiveResearchPort(
        repo,
        Secrets(),
        run_id=run_id,
        operator_id=operator_id,
        attribution=attr,
        policy=policy,
        bindings={binding.config.intended_use.capability: binding},
        brave_transport=transport,
        **updates,
    )


@pytest.mark.parametrize(
    ("price", "personal_use"),
    [(Decimal(".001"), False), (Decimal(0), False), (Decimal(0), True)],
    ids=["metered", "included-credit", "personal-included-credit"],
)
async def test_search_capture_two_receipts_replay_and_current_rights(
    governance_engine, price, personal_use
):
    values = await setup(governance_engine, price=price)
    repo, admin, attr, binding, now, run_id, operator_id, policy = values
    _, _, _, capture_config, capture_grant, _ = await seed(
        governance_engine,
        capability=Capability.FIRECRAWL_PAGE_CAPTURE,
        price=price,
        price_components=(UsageComponent.CAPTURE_PAGE,),
        personal_use_approved=personal_use,
    )
    capture_config = capture_config.model_copy(
        update={
            "id": uuid4(),
            "workflow_id": attr.workflow_run_id,
            "version": attr.config_version,
            "secret_handle": "research-test",
        }
    )
    await admin.config(capture_config)
    restored, _ = await repo.generation_config_and_prices(capture_config.id)
    assert restored == capture_config
    if personal_use:
        from alon_ai.db.repositories.openai_live import _ensure_exact_config

        assert (
            restored.intended_use.personal_noncommercial_approval_ref
            == capture_grant.supporting_evidence_ref
        )
        assert (
            "personal_noncommercial_approval_ref"
            not in capture_config.model_dump(mode="json")["intended_use"]
        )
        await _ensure_exact_config(governance_engine, capture_config)
        changed = capture_config.model_copy(
            update={
                "intended_use": capture_config.intended_use.model_copy(
                    update={"personal_noncommercial_approval_ref": uuid4()}
                )
            }
        )
        with pytest.raises(AccountingDenied) as denied:
            await _ensure_exact_config(governance_engine, changed)
        assert denied.value.reason.value == "CONFIG"
    await admin.budgets(
        attr,
        provider=capture_grant.provider,
        currencies=("USD", "ILS"),
        limit=Decimal(1),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )
    calls = []

    def respond(request):
        calls.append(request.url.host)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://example.com/",
                            "description": "search evidence",
                        }
                    ]
                }
            }
            if request.method == "GET"
            else {"success": True, "data": {"markdown": "captured evidence"}},
        )

    transport = httpx.MockTransport(respond)
    kwargs = {
        "run_id": run_id,
        "operator_id": operator_id,
        "attribution": attr,
        "policy": policy,
        "bindings": {
            binding.config.intended_use.capability: binding,
            capture_config.intended_use.capability: ResearchCapabilityBinding(
                config=capture_config, grant=capture_grant
            ),
        },
        "brave_transport": transport,
        "firecrawl_transport": transport,
        "resolver": lambda _: ("8.8.8.8",),
    }
    service = GovernedLiveResearchPort(repo, Secrets(), **kwargs)
    refs = await service.search(attr.experiment_id, search())
    captured = await service.capture(
        attr.experiment_id,
        FirecrawlCaptureRequest(
            capability=Capability.FIRECRAWL_PAGE_CAPTURE, url="https://example.com/"
        ),
    )
    assert isinstance(refs, tuple)
    assert isinstance(captured, tuple)
    assert captured[0].retained_id is not None
    assert refs[0].call_id != captured[0].call_id
    assert (
        await service.read_saved_evidence(
            attr.experiment_id, captured[0].retained_id, max_chars=100
        )
    ).text == "captured evidence"
    replay = GovernedLiveResearchPort(repo, Secrets(), **kwargs)
    assert await replay.search(attr.experiment_id, search()) == refs
    assert len(calls) == 2
    async with governance_engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.operation_id == attr.operation_run_id
                    )
                )
            )
            .mappings()
            .all()
        )
        assert len(rows) == 2 and all(r["state"] == "FINAL" for r in rows)
        assert all(r["accrued"] == price for r in rows)
        if price == 0:
            assert all(r["reserved"] == 0 and r["reserved_ils"] == 0 for r in rows)
        observations = (
            (
                await connection.execute(
                    select(gov.usage).where(
                        gov.usage.c.call_id.in_([r["id"] for r in rows])
                    )
                )
            )
            .mappings()
            .all()
        )
        assert len(observations) == 2
        assert all(
            observed["quantity"] == Decimal(1)
            and observed["cost"] == price
            and observed["knowledge"] == "FINAL"
            for observed in observations
        )
        assert (
            len(
                (
                    await connection.execute(
                        select(steps).where(steps.c.run_id == run_id)
                    )
                ).all()
            )
            == 2
        )
    await add_event(
        admin,
        GrantEvent(
            event_id=uuid4(),
            grant_id=capture_grant.grant_id,
            grant_version=1,
            kind=GrantEventKind.REVOKED,
            effective_at=now,
            actor_id=uuid4(),
            evidence_ref=uuid4(),
        ),
    )
    with pytest.raises(AccountingDenied):
        await service.read_saved_evidence(
            attr.experiment_id, captured[0].retained_id, max_chars=100
        )
    with pytest.raises(AccountingDenied):
        async with service.dispatch_guard():
            pytest.fail("revoked source entered model request")


async def test_transient_brave_does_not_retain_and_restart_does_not_reissue(
    governance_engine,
):
    values = await setup(governance_engine, transient=True)
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://example.com/",
                            "title": "private title",
                            "description": "private description",
                        }
                    ]
                }
            },
        )

    service = port(values, httpx.MockTransport(respond))
    response = await service.search(values[2].experiment_id, search())
    assert isinstance(response, TransientSearchUrls) and response.urls == (
        "https://example.com/",
    )
    async with governance_engine.connect() as connection:
        assert not (await connection.execute(select(gov.retained))).all()
        assert "example.com" not in str(
            (await connection.execute(select(steps))).mappings().all()
        )
    with pytest.raises(AccountingDenied):
        await port(values, httpx.MockTransport(respond)).search(
            values[2].experiment_id, search()
        )
    assert len(requests) == 1


async def test_denial_and_unknown_outcome_stop_network_replay(governance_engine):
    values = await setup(governance_engine)
    requests = []

    def fail(request):
        requests.append(request)
        raise httpx.ReadTimeout("secret response detail")

    service = port(values, httpx.MockTransport(fail))
    with pytest.raises(AccountingDenied, match="SCOPE"):
        await service.search(uuid4(), search())
    assert not requests
    with pytest.raises(AccountingDenied, match="UNCERTAIN") as error:
        await service.search(values[2].experiment_id, search())
    assert isinstance(error.value.__cause__, ProviderFailure)
    # The adapter's safe timeout classification survives unknown accounting.
    assert error.value.__cause__.code is ProviderErrorCode.TIMEOUT
    with pytest.raises(AccountingDenied, match="UNCERTAIN"):
        await port(values, httpx.MockTransport(fail)).search(
            values[2].experiment_id, search()
        )
    assert len(requests) == 1
    async with governance_engine.connect() as connection:
        call = (await connection.execute(select(gov.calls))).mappings().one()
        assert call["state"] == "RECONCILING" and call["reserved"] > 0
        assert (
            await connection.execute(select(steps.c.status))
        ).scalar_one() == "OUTCOME_UNKNOWN"


async def test_zero_price_completed_rejection_is_recoverable_without_inventing_usage(
    governance_engine,
):
    from alon_ai.agents.tools.research import ResearchTools

    values = await setup(
        governance_engine,
        price=Decimal(0),
        capability=Capability.FIRECRAWL_PAGE_CAPTURE,
    )
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {"markdown": "" if len(calls) == 2 else "usable evidence"},
            },
        )

    transport = httpx.MockTransport(respond)
    service = port(
        values,
        transport,
        firecrawl_transport=transport,
        resolver=lambda _: ("8.8.8.8",),
    )
    tools = ResearchTools(values[2].experiment_id, service)
    first = await tools.capture_page("https://example.com/good")
    rejected = await tools.capture_page("https://example.com/bad")
    assert isinstance(rejected, UnavailableResearchResult)
    assert rejected.status == "SOURCE_UNAVAILABLE"
    assert rejected.rejection is not None
    assert rejected.rejection.reason.value == "CONTENT_EMPTY"
    assert "not evidence" in rejected.guidance
    # Same failed request returns the same explicit unavailability, never retries.
    assert await tools.capture_page("https://example.com/bad") == rejected
    assert len(calls) == 2
    assert isinstance(first, tuple) and first[0].retained_id is not None
    assert (
        await tools.read_saved_evidence(first[0].retained_id)
    ).text == "usable evidence"
    async with governance_engine.connect() as connection:
        failed = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.result_metadata["status"].astext == "FAILED"
                    )
                )
            )
            .mappings()
            .one()
        )
        assert (
            failed["state"] == "FINAL"
            and failed["accrued"] == 0
            and failed["reserved"] == 0
        )
        assert "rejection" not in failed["result_metadata"]
        events = (
            await connection.execute(
                select(runs.c.events).where(runs.c.run_id == values[5])
            )
        ).scalar_one()
        assert any(
            event["type"] == "RESEARCH_RESPONSE"
            and "CONTENT_EMPTY" in (event.get("detail") or "")
            and "content_chars=0" in (event.get("detail") or "")
            for event in events
        )
        usage = (
            (
                await connection.execute(
                    select(gov.usage).where(gov.usage.c.call_id == failed["id"])
                )
            )
            .mappings()
            .one()
        )
        assert (
            usage["quantity"] is None
            and usage["cost"] == 0
            and usage["knowledge"] == "FINAL"
        )
        assert not (
            await connection.execute(
                select(gov.retained).where(gov.retained.c.call_id == failed["id"])
            )
        ).first()
        authority = (await connection.execute(select(gov.authorities))).mappings().one()
        assert authority["active"] == 0 and authority["quota_used"] == 2
        failed_step = (
            (
                await connection.execute(
                    select(steps).where(steps.c.provider_call_id == failed["id"])
                )
            )
            .mappings()
            .one()
        )
        assert (
            failed_step["status"] == "FAILED"
            and failed_step["reason_code"] == "MALFORMED_RESPONSE"
        )
    assert await tools.capture_page("https://example.com/alternate")
    assert len(calls) == 3


async def test_capture_circuit_release_allows_agent_to_finish_using_saved_evidence(
    governance_engine,
):
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
    from pydantic_ai.models.function import FunctionModel
    from pydantic_ai.toolsets import FunctionToolset

    from alon_ai.agents.tools.research import ResearchTools

    values = await setup(
        governance_engine,
        price=Decimal(0),
        capability=Capability.FIRECRAWL_PAGE_CAPTURE,
    )
    network, results = [], []

    def respond(request):
        network.append(request)
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {"markdown": "saved evidence" if len(network) == 1 else ""},
            },
        )

    transport = httpx.MockTransport(respond)
    service = port(
        values,
        transport,
        firecrawl_transport=transport,
        resolver=lambda _: ("8.8.8.8",),
    )
    tools = ResearchTools(values[2].experiment_id, service)

    async def capture_page(url: str):
        result = await tools.capture_page(url)
        results.append(result)
        return result

    turns = 0

    async def model(messages, info):
        nonlocal turns
        turns += 1
        if turns == 1:
            return ModelResponse(
                [
                    ToolCallPart(
                        "capture_page",
                        {"url": f"https://example.com/{index}"},
                        tool_call_id=f"c{index}",
                    )
                    for index in range(4)
                ]
            )
        if turns == 2:
            assert results[-1].status == "NOT_DISPATCHED"
            return ModelResponse(
                [
                    ToolCallPart(
                        "read_saved_evidence",
                        {"retained_id": str(results[0][0].retained_id)},
                        tool_call_id="read",
                    )
                ]
            )
        return ModelResponse(
            [TextPart("Assessment uses saved evidence and names unavailable sources.")]
        )

    result = await Agent(
        FunctionModel(model),
        toolsets=[
            FunctionToolset([capture_page, tools.read_saved_evidence], sequential=True)
        ],
        retries=0,
    ).run("research")
    assert (
        result.output == "Assessment uses saved evidence and names unavailable sources."
    )
    assert len(network) == 3
    assert results[-1].reason == "CIRCUIT"
    assert "Do not retry this capability" in results[-1].guidance
    assert await tools.capture_page("https://example.com/3") == results[-1]
    assert len(network) == 3
    async with governance_engine.connect() as connection:
        calls = (await connection.execute(select(gov.calls))).mappings().all()
        blocked = next(call for call in calls if call["state"] == "RELEASED")
        assert blocked["dispatch_at"] is None and blocked["accrued"] == 0
        step = (
            (
                await connection.execute(
                    select(steps).where(steps.c.provider_call_id == blocked["id"])
                )
            )
            .mappings()
            .one()
        )
        assert step["status"] == "BLOCKED" and step["reason_code"] == "CIRCUIT"
        authority = (await connection.execute(select(gov.authorities))).mappings().one()
        assert (
            authority["active"] == 0
            and authority["quota_used"] == 3
            and authority["failures"] == 2
        )
        assert not (
            await connection.execute(
                select(gov.usage).where(gov.usage.c.call_id == blocked["id"])
            )
        ).first()
        assert not (
            await connection.execute(
                select(gov.retained).where(gov.retained.c.call_id == blocked["id"])
            )
        ).first()
    run = await AgentRunRepository(governance_engine).get(values[5])
    assert any(
        "blocked · CIRCUIT · not dispatched" in (event.get("detail") or "")
        for event in run["events"]
    )


@pytest.mark.parametrize(
    "price,failure",
    [
        (Decimal(".001"), "content"),
        (Decimal(0), "timeout"),
        (Decimal(".001"), "envelope"),
        (Decimal(0), "permission"),
    ],
)
async def test_recovery_does_not_release_paid_unknown_transport_or_permission_failures(
    governance_engine, price, failure
):
    values = await setup(
        governance_engine, price=price, capability=Capability.FIRECRAWL_PAGE_CAPTURE
    )
    calls = []

    def respond(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("SECRET")
        if failure == "permission":
            return httpx.Response(302, headers={"Location": "https://other.example/"})
        return httpx.Response(
            200, json={"success": failure != "envelope", "data": {"markdown": ""}}
        )

    transport = httpx.MockTransport(respond)
    service = port(
        values,
        transport,
        firecrawl_transport=transport,
        resolver=lambda _: ("8.8.8.8",),
    )
    request = FirecrawlCaptureRequest(
        capability=Capability.FIRECRAWL_PAGE_CAPTURE, url="https://example.com/bad"
    )
    with pytest.raises(AccountingDenied, match="UNCERTAIN"):
        await service.capture(values[2].experiment_id, request)
    with pytest.raises(AccountingDenied, match="UNCERTAIN"):
        await service.capture(values[2].experiment_id, request)
    assert len(calls) == 1
    async with governance_engine.connect() as connection:
        call = (await connection.execute(select(gov.calls))).mappings().one()
        assert call["state"] == "RECONCILING"
        assert not (await connection.execute(select(gov.retained))).first()
        assert (
            await connection.execute(select(steps.c.status))
        ).scalar_one() == "OUTCOME_UNKNOWN"


async def test_http_502_is_visible_but_unknown_call_cannot_replay(governance_engine):
    values = await setup(governance_engine)
    requests = []

    def fail(request):
        requests.append(request)
        return httpx.Response(502, text="SECRET provider response")

    service = port(values, httpx.MockTransport(fail))
    with pytest.raises(AccountingDenied, match="UNCERTAIN") as raised:
        await service.search(values[2].experiment_id, search())
    assert isinstance(raised.value.__cause__, ProviderFailure)
    assert raised.value.__cause__.http_status == 502
    diagnostic = diagnostic_for_error("AGENT_EXECUTION", raised.value)
    assert diagnostic.code == "HTTP_502"
    assert diagnostic.message == "The provider returned HTTP 502."
    with pytest.raises(AccountingDenied, match="UNCERTAIN"):
        await port(values, httpx.MockTransport(fail)).search(
            values[2].experiment_id, search()
        )
    assert len(requests) == 1
    run = await AgentRunRepository(governance_engine).get(values[5])
    assert run is not None
    details = [event.get("detail") or "" for event in run["events"]]
    assert any(
        "HTTP_502 · accounting pending reconciliation" in detail for detail in details
    )
    assert "SECRET" not in str(details) + diagnostic.model_dump_json()
    async with governance_engine.connect() as connection:
        call = (await connection.execute(select(gov.calls))).mappings().one()
        assert call["state"] == "RECONCILING" and call["reserved"] > 0
        assert (
            await connection.execute(select(steps.c.status))
        ).scalar_one() == "OUTCOME_UNKNOWN"


@pytest.mark.parametrize(
    "price", [Decimal(".001"), Decimal(0)], ids=["metered", "included-credit"]
)
async def test_durable_call_cap_serializes_concurrent_claims(governance_engine, price):
    original = await setup(governance_engine, price=price)
    values: ResearchFixture = (
        *original[:-1],
        original[-1].model_copy(update={"max_calls": 1}),
    )
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {"url": "https://example.com/", "description": "evidence"}
                    ]
                }
            },
        )

    service = port(values, httpx.MockTransport(respond))
    results = await asyncio.gather(
        service.search(values[2].experiment_id, search("first")),
        service.search(values[2].experiment_id, search("second")),
        return_exceptions=True,
    )
    assert len(requests) == 1
    assert sum(isinstance(r, AccountingDenied) for r in results) == 1


async def test_map_reserves_result_ceiling_without_inventing_billed_credits(
    governance_engine,
):
    from alon_ai.integrations.schemas.provider import FirecrawlMapRequest

    values = await setup(governance_engine)
    repo, admin, attr, _binding, now, run_id, operator_id, policy = values
    _, _, _, config, grant, _ = await seed(
        governance_engine, capability=Capability.FIRECRAWL_MAP, price=Decimal(".01")
    )
    config = config.model_copy(
        update={
            "id": uuid4(),
            "workflow_id": attr.workflow_run_id,
            "version": attr.config_version,
            "secret_handle": "research-test",
            "prices": (
                config.prices[0].model_copy(
                    update={"max_quantity": Decimal(policy.max_results)}
                ),
            ),
            "intended_use": config.intended_use.model_copy(
                update={"required_fields": frozenset()}
            ),
        }
    )
    # This independently verified map fixture uses a URL retention grant.
    from alon_ai.integrations.schemas.provider import ContentField

    grant = grant.model_copy(
        update={
            "grant_id": uuid4(),
            "storage_fields": frozenset({ContentField.URL}),
            "supersedes_id": grant.grant_id,
        }
    )
    await admin.grant(grant)
    config = config.model_copy(
        update={
            "intended_use": config.intended_use.model_copy(
                update={"required_fields": frozenset({ContentField.URL})}
            )
        }
    )
    await admin.config(config)
    await admin.budgets(
        attr,
        provider=grant.provider,
        currencies=("USD", "ILS"),
        limit=Decimal(1),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )
    reserved = []

    async def respond(request):
        async with governance_engine.connect() as connection:
            reserved.append(
                (await connection.execute(select(gov.calls.c.reserved))).scalar_one()
            )
        return httpx.Response(
            200,
            json={
                "success": True,
                "links": ["https://example.com/a", "https://example.com/b"],
            },
        )

    service = GovernedLiveResearchPort(
        repo,
        Secrets(),
        run_id=run_id,
        operator_id=operator_id,
        attribution=attr,
        policy=policy,
        bindings={
            Capability.FIRECRAWL_MAP: ResearchCapabilityBinding(
                config=config, grant=grant
            )
        },
        firecrawl_transport=httpx.MockTransport(respond),
        resolver=lambda _: ("8.8.8.8",),
    )
    await service.map(
        attr.experiment_id,
        FirecrawlMapRequest(url="https://example.com/", limit=policy.max_results),
    )
    assert reserved == [Decimal(".10")]
    async with governance_engine.connect() as connection:
        call = (await connection.execute(select(gov.calls))).mappings().one()
        assert call["state"] == "RECONCILING" and call["accrued"] == 0
        assert call["reserved"] == Decimal(".10")


async def test_rights_denied_before_network_and_during_response(governance_engine):
    values = await setup(governance_engine)
    _, admin, attr, binding, now, *_ = values

    def revoke():
        return add_event(
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

    async def respond(request):
        await revoke()
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://example.com/",
                            "description": "forbidden after revocation",
                        }
                    ]
                }
            },
        )

    service = port(values, httpx.MockTransport(respond))
    with pytest.raises(AccountingDenied):
        await service.search(attr.experiment_id, search())

    def denied(request):
        pytest.fail("revoked grant reached transport")

    with pytest.raises(AccountingDenied, match="RIGHTS"):
        await port(values, httpx.MockTransport(denied)).search(
            attr.experiment_id, search("new request")
        )
    async with governance_engine.connect() as connection:
        assert not (await connection.execute(select(gov.retained))).all()


async def test_native_function_model_consumes_transient_urls_without_retention(
    governance_engine,
):
    import copy
    import pickle

    from pydantic_ai import Agent
    from pydantic_ai.messages import (
        ModelMessagesTypeAdapter,
        ModelRequest,
        ModelResponse,
        TextPart,
        ToolCallPart,
        ToolReturnPart,
    )
    from pydantic_ai.models.function import FunctionModel

    from alon_ai.agents.tools.research import ResearchTools

    values = await setup(governance_engine, transient=True)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://example.com/",
                            "title": "provider-title",
                            "description": "provider-snippet",
                        }
                    ]
                }
            },
        )
    )
    service = port(values, transport)
    facade = ResearchTools(values[2].experiment_id, service)
    model_turns = []

    def respond(messages, info):
        model_turns.append(messages)
        if len(model_turns) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "search_web",
                        {"query": "official site", "limit": 1},
                        tool_call_id="search-1",
                    )
                ]
            )
        returned = [
            part
            for message in messages
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        assert returned[-1].content == ("https://example.com/",)
        # Native Pydantic messages may be copied/serialized in process. The
        # trusted runtime never writes this history into durable checkpoints.
        encoded = ModelMessagesTypeAdapter.dump_json(copy.deepcopy(messages))
        assert b"https://example.com/" in encoded
        assert b"provider-title" not in encoded and b"provider-snippet" not in encoded
        return ModelResponse(
            parts=[TextPart("Capture the discovered official source next.")]
        )

    agent = Agent(FunctionModel(respond), tools=[facade.search_web])
    result = await agent.run("Find the official source.")
    assert result.output == "Capture the discovered official source next."
    assert len(model_turns) == 2
    with pytest.raises(TypeError, match="cannot be checkpointed"):
        pickle.dumps(TransientSearchUrls(("https://example.com/",)))
    async with governance_engine.connect() as connection:
        assert not (await connection.execute(select(gov.retained))).all()
        checkpoint_dump = str(
            (await connection.execute(select(steps))).mappings().all()
        )
        assert "example.com" not in checkpoint_dump
        assert (
            "provider-title" not in checkpoint_dump
            and "provider-snippet" not in checkpoint_dump
        )
