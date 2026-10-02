"""Combined native model provisioning against isolated governance PostgreSQL."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError
from pydantic_ai import Agent
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from sqlalchemy import func, select, update
from test_live_idea_runtime import reviewed_manifest
from test_minimal_intake import configured_app

from alon_ai.db.repositories.agent_run_steps import AgentRunStepRepository
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.tables import accounting as gov
from alon_ai.integrations.schemas.provider import ProviderFailure
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    CallState,
    Reason,
)
from alon_ai.services.agent_run_service import AgentRunService
from alon_ai.services.experiments import ExperimentContext
from alon_ai.services.intake import IntakeService
from alon_ai.services.live_idea_provision import (
    make_authority_bundle,
    register_authority,
)
from alon_ai.services.schemas.agent_runs import AgentRunRequest


class TestSecrets:
    __test__ = False

    def get(self, handle):
        return SecretStr("synthetic-only")


@asynccontextmanager
async def allowed_guard():
    yield


def explicit_limits(**overrides):
    from alon_ai.provider_usage.live_idea import CombinedModelLimits

    return CombinedModelLimits(
        **{
            "model_request_limit": 3,
            "input_tokens_limit": 30000,
            "output_tokens_limit": 900,
            "total_tokens_limit": 30900,
            "run_timeout_seconds": 90,
            **overrides,
        }
    )


def test_combined_limits_are_required_finite_positive_policy():
    from alon_ai.provider_usage.live_idea import (
        CombinedModelLimits,
        build_live_combined_model_provider,
    )

    with pytest.raises(ValidationError):
        CombinedModelLimits.model_validate({})
    with pytest.raises(ValidationError):
        explicit_limits(model_request_limit=0)
    config = make_authority_bundle(reviewed_manifest(uuid4(), datetime.now(UTC))).config
    with pytest.raises(TypeError, match="limits"):
        build_live_combined_model_provider(config, TestSecrets())  # type: ignore[call-arg]


async def provision(
    engine, *, budget=Decimal("0.50"), limits=None, response_function=None
):
    from alon_ai.provider_usage.live_idea import build_live_combined_model_provider

    app, operator = await configured_app(engine)
    context = ExperimentContext(engine, app.state.settings, operator)
    experiment_id = await IntakeService(context)._roots(uuid4(), "Seed", draft=False)
    admitted = await AgentRunService(context).admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    assert await AgentRunRepository(engine).start(admitted.run_id)
    bundle = make_authority_bundle(reviewed_manifest(operator, datetime.now(UTC)))
    await register_authority(engine, bundle)
    calls = []

    async def respond(messages, info):
        steps = await AgentRunStepRepository(engine).list(admitted.run_id)
        current = next(row for row in steps if row["ordinal"] == len(calls) + 1)
        assert current["status"] == "CLAIMED"
        assert current["provider_call_id"] is not None
        assert current["operation_id"] is not None
        calls.append(messages)
        if response_function is not None:
            return await response_function(messages, info)
        return ModelResponse(
            [TextPart("native result")],
            usage=RequestUsage(input_tokens=20, output_tokens=5),
        )

    provider = build_live_combined_model_provider(
        bundle.config,
        TestSecrets(),
        limits=limits or explicit_limits(),
        model_factory=lambda secret: FunctionModel(respond),
    )
    arguments: dict[str, Any] = {
        "experiment_id": experiment_id,
        "workflow_id": uuid4(),
        "agent_id": uuid4(),
        "operator_id": operator,
        "run_id": admitted.run_id,
        "budget_usd": budget,
        "dispatch_guard": allowed_guard,
    }
    result = await provider(engine, **arguments)
    return result, calls, provider, arguments


async def model_request(model):
    return await model.request(
        [ModelRequest([UserPromptPart("hello")])], None, ModelRequestParameters()
    )


async def test_activity_omits_unregistered_response_tool_names(governance_engine):
    async def respond(messages, info):
        return ModelResponse(
            [ToolCallPart("SECRET_provider_payload", {}, tool_call_id="call")],
            usage=RequestUsage(input_tokens=20, output_tokens=5),
        )

    result, _, _, arguments = await provision(
        governance_engine, response_function=respond
    )
    await model_request(result.model)
    row = await AgentRunRepository(governance_engine).get(arguments["run_id"])
    assert "SECRET_provider_payload" not in str(row["events"])
    assert "unrecognized tool request" in row["events"][-1]["detail"]


@pytest.mark.integration
async def test_combined_model_uses_two_real_receipts_then_denies_third_before_network(
    governance_engine,
):
    result, calls, _, arguments = await provision(
        governance_engine, budget=Decimal("0.02004")
    )
    assert calls == []
    await model_request(result.model)
    await model_request(result.model)
    with pytest.raises(AccountingDenied) as denied:
        await model_request(result.model)
    assert denied.value.reason is Reason.BUDGET
    assert len(calls) == len(result.model.receipts) == 2
    assert all(item.state is CallState.FINAL for item in result.model.receipts)
    assert all(item.accrued == Decimal("0.00003") for item in result.model.receipts)
    assert result.usage_limits.request_limit == 3
    assert result.usage_limits.input_tokens_limit == 30000
    assert result.usage_limits.output_tokens_limit == 900
    assert result.usage_limits.total_tokens_limit == 30900
    assert result.run_timeout_seconds == 90
    steps = await AgentRunStepRepository(governance_engine).list(arguments["run_id"])
    assert [row["status"] for row in steps] == ["SUCCEEDED", "SUCCEEDED", "BLOCKED"]
    assert steps[2]["reason_code"] == "BUDGET"
    assert steps[2]["provider_call_id"] is None
    parent = await AgentRunRepository(governance_engine).get(arguments["run_id"])
    activity = [
        event for event in parent["events"] if event["type"].startswith("MODEL_")
    ]
    assert [event["type"] for event in activity] == [
        "MODEL_REQUEST",
        "MODEL_RESPONSE",
        "MODEL_REQUEST",
        "MODEL_RESPONSE",
        "MODEL_REQUEST",
        "MODEL_RESPONSE",
    ]
    assert "20" in activity[1]["detail"] and "5" in activity[1]["detail"]
    assert "BUDGET" in activity[-1]["detail"]
    assert "native result" not in str(activity)
    assert 80 < (result.attribution.deadline - datetime.now(UTC)).total_seconds() <= 90
    async with governance_engine.connect() as connection:
        rows = (await connection.execute(select(gov.calls))).mappings().all()
        assert len(rows) == 2
        assert len({row["logical_operation_id"] for row in rows}) == 2
        assert {row["operation_id"] for row in rows} == {
            result.attribution.operation_run_id
        }
        assert await connection.scalar(select(func.count()).select_from(gov.usage)) == 4


@pytest.mark.integration
async def test_combined_agent_honors_explicit_request_limit(governance_engine):
    async def ask_again(messages, info):
        return ModelResponse(
            [ToolCallPart("lookup", {}, tool_call_id="test_call")],
            usage=RequestUsage(input_tokens=20, output_tokens=5),
        )

    result, calls, _, _ = await provision(
        governance_engine,
        limits=explicit_limits(model_request_limit=2),
        response_function=ask_again,
    )
    agent = Agent(result.model, retries=0)

    @agent.tool_plain
    def lookup() -> str:
        return "controlled evidence"

    with pytest.raises(UsageLimitExceeded):
        await agent.run("research", usage_limits=result.usage_limits)
    assert len(calls) == len(result.model.receipts) == 2


@pytest.mark.integration
async def test_child_request_rechecks_current_authority_and_preserves_prior_receipt(
    governance_engine,
):
    result, calls, _, _ = await provision(governance_engine)
    await model_request(result.model)
    async with governance_engine.begin() as connection:
        await connection.execute(update(gov.authorities).values(enabled=False))
    with pytest.raises(AccountingDenied) as denied:
        await model_request(result.model)
    assert denied.value.reason is Reason.CONFIG
    assert len(calls) == len(result.model.receipts) == 1
    assert result.model.receipts[0].state is CallState.FINAL


@pytest.mark.integration
async def test_changed_budget_or_missing_dispatch_guard_cannot_reprovision(
    governance_engine,
):
    _result, calls, provider, arguments = await provision(governance_engine)
    with pytest.raises(AccountingDenied) as denied:
        await provider(
            governance_engine, **{**arguments, "budget_usd": Decimal("0.40")}
        )
    assert denied.value.reason is Reason.BUDGET
    arguments.pop("dispatch_guard")
    with pytest.raises(TypeError, match="dispatch_guard"):
        await provider(governance_engine, **arguments)
    assert calls == []


@pytest.mark.integration
async def test_crash_after_model_dispatch_retains_unknown_step_and_replay_never_dispatches(
    governance_engine,
):
    async def crash(messages, info):
        raise TimeoutError("controlled post-dispatch ambiguity")

    result, calls, provider, arguments = await provision(
        governance_engine, response_function=crash
    )
    with pytest.raises(ProviderFailure):
        await model_request(result.model)
    rows = await AgentRunStepRepository(governance_engine).list(arguments["run_id"])
    assert len(rows) == 1
    assert rows[0]["status"] == "OUTCOME_UNKNOWN"
    assert rows[0]["provider_call_id"] == result.model.receipts[0].call_id
    replay = await provider(governance_engine, **arguments)
    with pytest.raises(ProviderFailure):
        await model_request(replay.model)
    assert len(calls) == 1
    assert replay.model.receipts[0].call_id == result.model.receipts[0].call_id


@pytest.mark.integration
async def test_crash_after_step_claim_before_reservation_never_retries(
    governance_engine, monkeypatch
):
    result, calls, provider, arguments = await provision(governance_engine)

    class ProcessCrash(BaseException):
        pass

    original_claim = AgentRunStepRepository.claim_once

    async def crash_after_claim(self, **kwargs):
        await original_claim(self, **kwargs)
        raise ProcessCrash

    with monkeypatch.context() as patched:
        patched.setattr(AgentRunStepRepository, "claim_once", crash_after_claim)
        with pytest.raises(ProcessCrash):
            await model_request(result.model)
    steps = await AgentRunStepRepository(governance_engine).list(arguments["run_id"])
    assert len(steps) == 1
    assert steps[0]["provider_call_id"] is None
    assert steps[0]["status"] == "CLAIMED"
    replay = await provider(governance_engine, **arguments)
    with pytest.raises(ProviderFailure):
        await model_request(replay.model)
    assert calls == []


@pytest.mark.integration
async def test_concurrent_model_step_owner_is_only_caller_and_replay_cannot_finish_it(
    governance_engine,
):
    import asyncio

    first, calls, provider, arguments = await provision(governance_engine)
    second = await provider(governance_engine, **arguments)
    results = await asyncio.gather(
        model_request(first.model), model_request(second.model), return_exceptions=True
    )
    assert sum(isinstance(item, ModelResponse) for item in results) == 1, results
    assert sum(isinstance(item, ProviderFailure) for item in results) == 1
    assert len(calls) == 1
    rows = await AgentRunStepRepository(governance_engine).list(arguments["run_id"])
    assert len(rows) == 1
    assert rows[0]["status"] == "SUCCEEDED"
