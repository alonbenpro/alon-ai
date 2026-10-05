"""Research scheduling preserves capture capacity without weakening admission."""

from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from alon_ai.agents.tools.research import ResearchToolError
from alon_ai.db.repositories.agent_run_steps import AgentRunStepRepository
from alon_ai.integrations.schemas.provider import Capability
from alon_ai.services import combined_idea


@pytest.fixture
def runtime(monkeypatch):
    rows = [{"kind": "BRAVE_SEARCH"} for _ in range(5)]
    quotas = [
        {"capability": capability.value, "remaining_calls": 20}
        for capability in (
            Capability.BRAVE_WEB_COVERAGE,
            Capability.FIRECRAWL_PAGE_CAPTURE,
            Capability.FIRECRAWL_PDF_CAPTURE,
        )
    ]

    class Steps:
        async def list(self, run_id):
            return rows.copy()

    class Governance:
        def __init__(self, engine):
            pass

        async def quota_snapshot(self, scopes):
            return quotas

    monkeypatch.setattr(combined_idea, "GovernanceRepository", Governance)
    instance = combined_idea.CombinedIdeaRuntime.__new__(
        combined_idea.CombinedIdeaRuntime
    )
    instance.context = SimpleNamespace(engine=None)
    instance.row = {"run_id": uuid4()}
    instance.steps = cast(AgentRunStepRepository, Steps())
    instance.config = SimpleNamespace(
        research_policy=SimpleNamespace(
            max_calls=14,
            max_pages=6,
            max_pdf_pages=4,
            max_results=4,
            max_spend_usd="0.2",
            timeout_seconds=900,
        ),
        research_bindings=[
            SimpleNamespace(
                config=SimpleNamespace(
                    intended_use=SimpleNamespace(
                        account_handle="test", capability=Capability(q["capability"])
                    )
                )
            )
            for q in quotas
        ],
    )
    return instance, rows, quotas


async def test_one_model_batch_cannot_spend_capture_allocation_on_searches(runtime):
    instance, rows, _ = runtime
    returned = []

    class Tools:
        async def search_web(self, query: str, *, limit: int | None = None):
            rows.append({"kind": "BRAVE_SEARCH"})
            return ("https://example.com",)

        async def capture_page(self, url: str):
            rows.append({"kind": "FIRECRAWL_PAGE_CAPTURE"})
            return "retained-reference"

        async def capture_pdf(self, url: str):
            raise AssertionError("not requested")

        async def map_site(self, url: str, *, limit: int | None = None):
            raise AssertionError("not requested")

        async def read_saved_evidence(self, retained_id: str):
            return "retained excerpt"

    turns = 0

    async def model(messages, info):
        nonlocal turns
        turns += 1
        if turns == 1:
            return ModelResponse(
                [
                    ToolCallPart(
                        "search_web", {"query": f"query {i}"}, tool_call_id=f"s{i}"
                    )
                    for i in range(10)
                ]
            )
        returned.extend(
            part.content
            for message in messages[-1:]
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        )
        if turns == 2:
            assert '"calls_remaining":7' in info.instructions
            assert '"discovery_calls_remaining":0' in info.instructions
            return ModelResponse(
                [
                    ToolCallPart(
                        "capture_page", {"url": "https://example.com"}, tool_call_id="c"
                    )
                ]
            )
        return ModelResponse([TextPart("incomplete; report named gaps")])

    result = await Agent(
        FunctionModel(model), toolsets=[instance._research_toolset(Tools())], retries=0
    ).run("research")
    assert result.output == "incomplete; report named gaps"
    assert sum(row["kind"] == "BRAVE_SEARCH" for row in rows) == 7
    assert rows[-1]["kind"] == "FIRECRAWL_PAGE_CAPTURE"
    stopped = [
        item
        for item in returned
        if isinstance(item, dict) and item.get("status") == "NOT_DISPATCHED"
    ]
    assert len(stopped) == 8
    assert all("capture" in item["guidance"] for item in stopped)


async def test_zero_quota_and_pdf_page_reservation_stop_before_dispatch(runtime):
    instance, rows, quotas = runtime
    calls = []

    async def dispatch():
        calls.append(True)

    quotas[0]["remaining_calls"] = 0
    result = await instance._scheduled_research(Capability.BRAVE_WEB_COVERAGE, dispatch)
    assert result["status"] == "NOT_DISPATCHED"
    rows.append({"kind": "FIRECRAWL_PDF_CAPTURE"})
    result = await instance._scheduled_research(
        Capability.FIRECRAWL_PDF_CAPTURE, dispatch
    )
    assert result["status"] == "NOT_DISPATCHED"
    snapshot = await instance._research_allowance()
    assert snapshot["run_usage"]["pages_remaining"] == 2
    assert snapshot["run_usage"]["calls_remaining"] == 8
    assert calls == []


async def test_exhausted_run_preserves_only_existing_evidence_and_named_gaps(runtime):
    instance, rows, _ = runtime
    rows.extend({"kind": "BRAVE_SEARCH"} for _ in range(9))

    async def dispatch():
        raise AssertionError("exhausted run dispatched")

    result = await instance._scheduled_research(
        Capability.FIRECRAWL_PAGE_CAPTURE, dispatch
    )
    assert result["status"] == "NOT_DISPATCHED"
    assert result["remaining"]["calls_remaining"] == 0
    assert "required native result with named gaps" in result["guidance"]
    instructions = await instance._research_instructions(None)
    assert '"calls_used":14' in instructions
    assert '"calls_remaining":0' in instructions
    assert "not evidence" in instructions


async def test_scheduling_never_swallows_governed_failures(runtime):
    instance, _, _ = runtime

    async def dispatch():
        raise ResearchToolError("BUDGET")

    with pytest.raises(ResearchToolError, match="BUDGET"):
        await instance._scheduled_research(Capability.FIRECRAWL_PAGE_CAPTURE, dispatch)
