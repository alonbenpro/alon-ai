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

from alon_ai.agents.tools.research import TransientSearchUrls
from alon_ai.db.repositories.accounting import (
    GovernanceProvisioner,
    GovernanceRepository,
)
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
    UsageComponent,
)
from alon_ai.policies.provider_rights import GrantEvent, GrantEventKind
from alon_ai.provider_usage.live_research import GovernedLiveResearchPort
from alon_ai.provider_usage.schemas.accounting import AccountingDenied

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
    engine: AsyncEngine, *, transient: bool = False, price: Decimal = Decimal(".001")
) -> ResearchFixture:
    run_id, experiment_id, context = await _run(engine)
    repo, admin, original, config, grant, now = await seed(
        engine, transient=transient, price=price
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
    "price", [Decimal(".001"), Decimal(0)], ids=["metered", "included-credit"]
)
async def test_search_capture_two_receipts_replay_and_current_rights(
    governance_engine, price
):
    values = await setup(governance_engine, price=price)
    repo, admin, attr, binding, now, run_id, operator_id, policy = values
    _, _, _, capture_config, capture_grant, _ = await seed(
        governance_engine,
        capability=Capability.FIRECRAWL_PAGE_CAPTURE,
        price=price,
        price_components=(UsageComponent.CAPTURE_PAGE,),
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
    with pytest.raises(AccountingDenied, match="UNCERTAIN"):
        await service.search(values[2].experiment_id, search())
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
