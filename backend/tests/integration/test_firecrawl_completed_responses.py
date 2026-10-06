"""EOF proof, zero-cash settlement and incomplete-response quarantine."""

from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from test_live_research_port import port, setup

from alon_ai.agents.tools.research import UnavailableResearchResult
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.agent_run_steps import steps
from alon_ai.db.tables.agent_runs import runs
from alon_ai.integrations.firecrawl import FirecrawlAdapter
from alon_ai.integrations.schemas.provider import Capability, FirecrawlCaptureRequest
from alon_ai.provider_usage.schemas.accounting import AccountingDenied

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("price", [Decimal(0), Decimal(".001")])
@pytest.mark.parametrize(
    "raw,reason",
    [
        (b'{"PRIVATE"', "JSON_INVALID"),
        (b'{"success":false,"error":"PRIVATE"}', "ENVELOPE_INVALID"),
    ],
)
async def test_completed_http_200_only_settles_exact_zero_cash(
    governance_engine, price, raw, reason
):
    values = await setup(
        governance_engine, price=price, capability=Capability.FIRECRAWL_PAGE_CAPTURE
    )
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, content=raw)

    transport = httpx.MockTransport(respond)
    service = port(
        values,
        transport,
        firecrawl_transport=transport,
        resolver=lambda _: ("8.8.8.8",),
    )
    request = FirecrawlCaptureRequest(url="https://example.com/PRIVATE")
    if price == 0:
        result = await service.capture(values[2].experiment_id, request)
        assert isinstance(result, UnavailableResearchResult)
        assert result.rejection is not None and result.rejection.reason == reason
        assert "not evidence" in result.guidance
        replayed = await service.capture(values[2].experiment_id, request)
        assert isinstance(replayed, UnavailableResearchResult)
    else:
        for _ in range(2):
            with pytest.raises(AccountingDenied, match="UNCERTAIN"):
                await service.capture(values[2].experiment_id, request)
    assert len(requests) == 1

    async with governance_engine.connect() as connection:
        call = (await connection.execute(select(gov.calls))).mappings().one()
        usage = (await connection.execute(select(gov.usage))).mappings().one()
        step = (await connection.execute(select(steps))).mappings().one()
        assert usage["quantity"] is None
        assert not (await connection.execute(select(gov.retained))).first()
        if price == 0:
            assert call["state"] == "FINAL" and call["accrued"] == 0
            assert call["reserved"] == 0 and usage["cost"] == 0
            assert usage["knowledge"] == "FINAL"
            assert call["result_metadata"]["status"] == "FAILED"
            assert "rejection" not in call["result_metadata"]
            assert step["status"] == "FAILED"
            authority = (
                (await connection.execute(select(gov.authorities))).mappings().one()
            )
            assert authority["quota_used"] == 1
            events = (
                await connection.execute(
                    select(runs.c.events).where(runs.c.run_id == values[5])
                )
            ).scalar_one()
            assert any(reason in (event.get("detail") or "") for event in events)
            assert "PRIVATE" not in str(events)
        else:
            assert call["state"] == "RECONCILING" and call["reserved"] > 0
            assert usage["cost"] is None and usage["knowledge"] == "UNAVAILABLE"
            assert step["status"] == "OUTCOME_UNKNOWN"


@pytest.mark.parametrize("failure", ["byte_limit", "timeout"])
async def test_incomplete_http_200_stays_unknown_even_at_zero_price(
    governance_engine, failure
):
    values = await setup(
        governance_engine,
        price=Decimal(0),
        capability=Capability.FIRECRAWL_PAGE_CAPTURE,
    )
    requests = []
    completed = False

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            nonlocal completed
            if failure == "byte_limit":
                yield b"x" * (12 * values[7].max_text_chars + 256000 + 1)
            else:
                yield b'{"success":true}'
                raise httpx.ReadTimeout("PRIVATE")
            completed = True

    def respond(request):
        requests.append(request)
        return httpx.Response(200, stream=Stream())

    transport = httpx.MockTransport(respond)
    service = port(
        values,
        transport,
        firecrawl_transport=transport,
        resolver=lambda _: ("8.8.8.8",),
    )
    request = FirecrawlCaptureRequest(url="https://example.com/a")
    for _ in range(2):
        with pytest.raises(AccountingDenied, match="UNCERTAIN"):
            await service.capture(values[2].experiment_id, request)
    assert len(requests) == 1 and not completed
    async with governance_engine.connect() as connection:
        call = (await connection.execute(select(gov.calls))).mappings().one()
        assert call["state"] == "RECONCILING" and call["result_metadata"] is None
        assert not (await connection.execute(select(gov.retained))).first()
        assert (await connection.execute(select(steps.c.status))).scalar_one() == (
            "OUTCOME_UNKNOWN"
        )


async def test_native_assessment_uses_alternate_source_after_completed_json_failure(
    governance_engine, monkeypatch
):
    from test_combined_idea_orchestration import (
        test_startup_allowance_blocks_before_any_provider_dispatch,
    )

    response = httpx.Response
    captures = 0

    def respond(status_code, *args, **kwargs):
        nonlocal captures
        payload = kwargs.get("json")
        if (
            status_code == 200
            and isinstance(payload, dict)
            and payload.get("success") is True
            and isinstance(payload.get("data"), dict)
            and "markdown" in payload["data"]
        ):
            captures += 1
            if captures == 1:
                return response(200, content=b'{"PRIVATE"')
            kwargs["json"] = {
                "success": True,
                "data": {"markdown": "Public clinic workflow."},
            }
        return response(status_code, *args, **kwargs)

    monkeypatch.setattr(httpx, "Response", respond)
    await test_startup_allowance_blocks_before_any_provider_dispatch(
        governance_engine,
        monkeypatch,
        10,
        10,
        10,
        3,
        None,
        None,
        capture_failures=1,
    )
    # The helper verifies native model/tool turns, retained alternate evidence,
    # final ASSESSED output and operator review, including one settled failed step.
    assert captures == 2


async def test_pre_response_internal_failure_stays_unknown_at_zero_price(
    governance_engine, monkeypatch
):
    values = await setup(
        governance_engine,
        price=Decimal(0),
        capability=Capability.FIRECRAWL_PAGE_CAPTURE,
    )

    async def broken_post(*args, **kwargs):
        raise TypeError("PRIVATE internal failure")

    monkeypatch.setattr(FirecrawlAdapter, "_post", broken_post)

    def respond(request):
        raise AssertionError("No provider response exists")

    transport = httpx.MockTransport(respond)
    service = port(
        values,
        transport,
        firecrawl_transport=transport,
        resolver=lambda _: ("8.8.8.8",),
    )
    with pytest.raises(AccountingDenied, match="UNCERTAIN"):
        await service.capture(
            values[2].experiment_id,
            FirecrawlCaptureRequest(url="https://example.com/a"),
        )
    async with governance_engine.connect() as connection:
        call = (await connection.execute(select(gov.calls))).mappings().one()
        assert call["state"] == "RECONCILING" and call["result_metadata"] is None
        assert not (await connection.execute(select(gov.usage))).first()
        assert (await connection.execute(select(steps.c.status))).scalar_one() == (
            "OUTCOME_UNKNOWN"
        )
