"""Native model round trips must retain the existing accounting fence."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import uuid4

import pytest
from pydantic import SecretStr
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from alon_ai.db.repositories.accounting import GovernanceRepository
from alon_ai.integrations.schemas.provider import (
    CallAttribution,
    Capability,
    CostKnowledge,
    Provider,
    ProviderFailure,
    Purpose,
    SystemActor,
    UsageComponent,
)
from alon_ai.policies.provider_rights import IntendedUse
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    CallReceipt,
    CallState,
    CapabilityConfig,
    PriceBound,
    PriceVersion,
    Reason,
)


class Ledger:
    """Deterministic repository boundary; the production executor is unmocked."""

    def __init__(self, config):
        self.config = config
        self.calls = {}
        self.keys = {}
        self.events = []
        self.observations = []
        self.logical_operations = {}
        self.deny_after = 100

    def clock(self):
        return datetime.now(UTC)

    async def reserve(self, attribution, request, *, idempotency_key):
        self.events.append("reserve")
        if idempotency_key in self.keys:
            return self.calls[self.keys[idempotency_key]]
        if attribution.logical_operation_id in self.logical_operations:
            raise AccountingDenied(Reason.CONFLICT)
        if len(self.calls) >= self.deny_after:
            raise AccountingDenied(Reason.BUDGET)
        receipt = CallReceipt(
            call_id=uuid4(),
            state=CallState.RESERVED,
            currency="USD",
            reserved=Decimal(1),
            reserved_ils=Decimal(4),
            accrued=Decimal(0),
            accrued_ils=Decimal(0),
        )
        self.calls[receipt.call_id] = receipt
        self.keys[idempotency_key] = receipt.call_id
        self.logical_operations[attribution.logical_operation_id] = receipt.call_id
        return receipt

    async def config_for_call(self, call_id):
        return self.config

    async def dispatch(self, call_id):
        self.events.append("dispatch")
        receipt = self.calls[call_id].model_copy(
            update={
                "state": CallState.DISPATCHED,
                "token": uuid4(),
                "timeout_seconds": 10.0,
            }
        )
        self.calls[call_id] = receipt
        return receipt

    async def record_usage(self, call_id, usage, *, token):
        self.events.append("usage")
        self.observations.extend(usage)

    async def finish_attempt(self, call_id, *, token, success, metadata):
        self.events.append("finish")
        return uuid4()

    async def reconcile(self, call_id, *, command_key, evidence_id):
        self.events.append("reconcile")
        self.calls[call_id] = self.calls[call_id].model_copy(
            update={"state": CallState.FINAL}
        )
        return self.calls[call_id]

    async def mark_unknown(self, call_id, *, token):
        self.events.append("unknown")
        self.calls[call_id] = self.calls[call_id].model_copy(
            update={"state": CallState.RECONCILING}
        )
        return self.calls[call_id]

    async def get(self, call_id):
        return self.calls[call_id]

    async def receipt_for_idempotency_key(self, key):
        return self.calls.get(self.keys.get(key))


class Secrets:
    def get(self, handle):
        return SecretStr("controlled-test-secret")


@pytest.fixture
def setup_model():
    from alon_ai.provider_usage.pydantic_model import GovernedPydanticModel

    now = datetime.now(UTC)
    prices = tuple(
        PriceVersion(
            id=uuid4(),
            effective_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=1),
            evidence_id=uuid4(),
            model_identifier="gpt-4.1-mini",
            capability=Capability.OPENAI_GENERATE,
            component=component,
            currency="USD",
            unit_price=Decimal("0.01"),
            unit_quantity=Decimal(1000),
            currency_quantum=Decimal("0.01"),
        )
        for component in (
            UsageComponent.INPUT_TOKEN,
            UsageComponent.OUTPUT_TOKEN,
            UsageComponent.CACHED_TOKEN,
        )
    )
    config = CapabilityConfig(
        id=uuid4(),
        version=uuid4(),
        workflow_id=uuid4(),
        intended_use=IntendedUse(
            capability=Capability.OPENAI_GENERATE,
            purpose=Purpose.GENERATION,
            provider=Provider.OPENAI,
            account_handle="test",
            plan_identifier="test",
            order_form_ref="test",
            terms_version="test",
            required_fields=frozenset(),
        ),
        prices=tuple(
            PriceBound(price_id=p.id, max_quantity=Decimal(100000)) for p in prices
        ),
        fx_id=uuid4(),
        requested_count=1,
        secret_handle="openai",
        adapter_version=uuid4(),
        model_identifier="gpt-4.1-mini",
    )
    attribution = CallAttribution(
        experiment_id=uuid4(),
        workflow_run_id=config.workflow_id,
        operation_run_id=uuid4(),
        actor=SystemActor(service="provider-executor"),
        correlation_id=uuid4(),
        logical_operation_id=uuid4(),
        config_version=config.version,
        deadline=now + timedelta(minutes=5),
    )
    ledger = Ledger(config)
    responses = []

    async def respond(messages, info):
        ledger.events.append("network")
        response = ModelResponse(
            [TextPart("done")],
            usage=RequestUsage(input_tokens=20, output_tokens=5, cache_read_tokens=4),
        )
        responses.append(response)
        return response

    @asynccontextmanager
    async def guard():
        ledger.events.append("guard")
        yield

    def build(
        *, function=respond, dispatch_guard=guard, run_key=None, production=False
    ):
        return GovernedPydanticModel(
            repository=cast(GovernanceRepository, ledger),
            attribution=attribution,
            config=config,
            prices=prices,
            secrets=Secrets(),
            run_key=run_key or uuid4(),
            max_output_tokens=1000,
            model_factory=None
            if production
            else lambda secret: FunctionModel(function),
            dispatch_guard=dispatch_guard,
        )

    return build, ledger, responses


async def request(model):
    return await model.request(
        [ModelRequest([UserPromptPart("hello")])], None, ModelRequestParameters()
    )


async def test_third_request_denied_preserves_two_native_responses_and_receipts(
    setup_model,
):
    build, ledger, responses = setup_model
    ledger.deny_after = 2
    model = build()
    assert await request(model) is responses[0]
    assert await request(model) is responses[1]
    with pytest.raises(AccountingDenied, match="BUDGET"):
        await request(model)
    assert ledger.events == [
        "reserve",
        "dispatch",
        "guard",
        "network",
        "usage",
        "finish",
        "reconcile",
    ] * 2 + ["reserve"]
    assert len(model.receipts) == 2
    assert all(r.state is CallState.FINAL for r in model.receipts)
    assert [o.quantity for o in ledger.observations[:3]] == [
        Decimal(16),
        Decimal(5),
        Decimal(4),
    ]


async def test_timeout_keeps_unknown_reservation_and_never_retries(setup_model):
    build, ledger, _ = setup_model

    async def timeout(messages, info):
        ledger.events.append("network")
        raise TimeoutError("sensitive upstream detail")

    model = build(function=timeout)
    with pytest.raises(ProviderFailure, match="TIMEOUT"):
        await request(model)
    assert ledger.events.count("network") == 1
    assert model.receipts[0].state is CallState.RECONCILING
    assert "reconcile" not in ledger.events


async def test_missing_native_usage_is_unknown_not_free(setup_model):
    build, ledger, _ = setup_model

    async def missing(messages, info):
        return ModelResponse([TextPart("done")], usage=RequestUsage())

    # FunctionModel fabricates token estimates for empty usage; bypass that helper.
    model = build(function=missing)
    model._model_factory = lambda secret: MissingUsageModel()
    with pytest.raises(ProviderFailure):
        await request(model)
    assert model.receipts[0].state is CallState.RECONCILING
    assert all(o.knowledge is CostKnowledge.UNAVAILABLE for o in ledger.observations)


from pydantic_ai.models import Model


class MissingUsageModel(Model):
    @property
    def model_name(self):
        return "gpt-4.1-mini"

    @property
    def system(self):
        return "openai"

    async def request(self, messages, model_settings, model_request_parameters):
        return ModelResponse([TextPart("done")])


async def test_cancelled_request_records_unknown_receipt(setup_model):
    build, _ledger, _ = setup_model

    async def cancelled(messages, info):
        raise asyncio.CancelledError

    model = build(function=cancelled)
    with pytest.raises(asyncio.CancelledError):
        await request(model)
    assert model.receipts[0].state is CallState.RECONCILING


async def test_recreated_model_replays_no_network_and_cannot_redeliver_content(
    setup_model,
):
    build, ledger, _ = setup_model
    key = uuid4()
    await request(build(run_key=key))
    replay = build(run_key=key)
    with pytest.raises(ProviderFailure):
        await request(replay)
    assert ledger.events.count("network") == 1
    assert len(replay.receipts) == 1


async def test_revoked_dispatch_guard_records_zero_cost_without_network(setup_model):
    build, ledger, _ = setup_model

    @asynccontextmanager
    async def denied():
        raise PermissionError("revoked")
        yield

    model = build(dispatch_guard=denied)
    with pytest.raises(ProviderFailure, match="DENIED"):
        await request(model)
    assert "network" not in ledger.events
    assert model.receipts[0].state is CallState.FINAL
    assert all(o.quantity == 0 and o.cost == 0 for o in ledger.observations)


async def test_native_openai_http_error_has_one_wire_request_and_unknown_receipt(
    setup_model,
):
    import httpx2

    from alon_ai.integrations.pydantic_openai import openai_model_factory

    build, _ledger, _ = setup_model
    wire_requests = []

    async def handler(request):
        wire_requests.append(request)
        return httpx2.Response(
            503, json={"error": {"message": "private failure", "type": "server_error"}}
        )

    model = build()
    model._model_factory = openai_model_factory(
        "gpt-4.1-mini", http_transport=httpx2.MockTransport(handler)
    )
    with pytest.raises(ProviderFailure, match="UNAVAILABLE"):
        await request(model)
    assert len(wire_requests) == 1
    assert model.receipts[0].state is CallState.RECONCILING


async def test_native_openai_tool_call_and_usage_are_not_wrapped_in_legacy_envelope(
    setup_model,
):
    import json

    import httpx2

    from alon_ai.integrations.pydantic_openai import openai_model_factory

    build, ledger, _ = setup_model
    payloads = []

    async def handler(request):
        payloads.append(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "id": "resp_native",
                "created_at": 1720000000,
                "object": "response",
                "model": "gpt-4.1-mini",
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "id": "fc_1",
                        "call_id": "call_1",
                        "name": "search",
                        "arguments": '{"query":"test"}',
                        "status": "completed",
                    }
                ],
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 5,
                    "total_tokens": 25,
                    "input_tokens_details": {"cached_tokens": 4},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    model = build()
    model._model_factory = openai_model_factory(
        "gpt-4.1-mini", http_transport=httpx2.MockTransport(handler)
    )
    response = await request(model)
    assert response.parts[0].part_kind == "tool-call"
    assert response.provider_response_id == "resp_native"
    assert payloads[0]["store"] is False
    assert payloads[0]["max_output_tokens"] == 1000
    assert payloads[0]["background"] is False
    assert [o.quantity for o in ledger.observations] == [
        Decimal(16),
        Decimal(5),
        Decimal(4),
    ]


async def test_growing_tool_context_cannot_exceed_reserved_input_bound(setup_model):
    build, ledger, _ = setup_model
    model = build()
    await request(model)
    with pytest.raises(AccountingDenied, match="PRICE"):
        await model.request(
            [ModelRequest([UserPromptPart("x" * 100001)])],
            None,
            ModelRequestParameters(),
        )
    assert ledger.events.count("network") == 1
    assert len(model.receipts) == 1


async def test_agent_cannot_override_fixed_settings_or_add_native_tools(setup_model):
    from pydantic_ai.native_tools import WebSearchTool

    build, ledger, _ = setup_model
    model = build()
    with pytest.raises(AccountingDenied, match="CONFIG"):
        await model.request([], {"max_tokens": 9000}, ModelRequestParameters())
    with pytest.raises(AccountingDenied, match="CONFIG"):
        await model.request(
            [], None, ModelRequestParameters(native_tools=[WebSearchTool()])
        )
    assert ledger.events == []


async def test_real_agent_tool_loop_accounts_for_each_native_model_turn(setup_model):
    from pydantic import BaseModel
    from pydantic_ai import Agent, NativeOutput
    from pydantic_ai.messages import ToolCallPart

    class Answer(BaseModel):
        answer: str

    build, ledger, _ = setup_model
    calls = []

    async def respond(messages, info):
        calls.append(messages)
        if len(calls) == 1:
            return ModelResponse(
                [ToolCallPart("lookup", {"query": "hello"}, tool_call_id="c1")],
                usage=RequestUsage(
                    input_tokens=20, output_tokens=5, cache_read_tokens=0
                ),
            )
        assert (
            "controlled evidence"
            in ModelMessagesTypeAdapter.dump_json(messages).decode()
        )
        return ModelResponse(
            [TextPart('{"answer":"grounded"}')],
            usage=RequestUsage(input_tokens=40, output_tokens=6, cache_read_tokens=4),
        )

    from pydantic_ai.messages import ModelMessagesTypeAdapter

    model = build(function=respond)
    agent = Agent(model, output_type=NativeOutput(Answer), retries=0)

    @agent.tool_plain
    def lookup(query: str) -> str:
        return "controlled evidence"

    result = await agent.run("answer using lookup")
    assert result.output.answer == "grounded"
    assert len(calls) == 2
    assert len(model.receipts) == 2
    assert len(ledger.observations) == 6


async def test_default_factory_uses_shared_integration_builder_after_dispatch_and_closes_client(
    setup_model,
    monkeypatch,
):
    import httpx2

    from alon_ai.integrations import pydantic_openai

    build, ledger, _ = setup_model
    original = pydantic_openai.build_openai_model
    constructed = []
    wire_requests = []
    monkeypatch.setenv("OPENAI_BASE_URL", "https://unexpected.invalid/v1")

    async def reject_network(self, request):
        raise AssertionError("test attempted an uncontrolled network request")

    monkeypatch.setattr(
        httpx2.AsyncHTTPTransport, "handle_async_request", reject_network
    )

    async def handler(request):
        wire_requests.append(request)
        return httpx2.Response(
            503, json={"error": {"message": "failure", "type": "server_error"}}
        )

    def construct(**kwargs):
        assert ledger.events[-1] == "guard"
        kwargs["http_transport"] = httpx2.MockTransport(handler)
        model = original(**kwargs)
        constructed.append(model)
        return model

    monkeypatch.setattr(pydantic_openai, "build_openai_model", construct)
    model = build(production=True)
    assert constructed == []
    with pytest.raises(ProviderFailure):
        await request(model)
    assert len(constructed) == len(wire_requests) == 1
    assert str(wire_requests[0].url) == "https://api.openai.com/v1/responses"
    assert constructed[0].client.is_closed()
    assert constructed[0].client.max_retries == 0
    assert constructed[0].settings["openai_store"] is False
    assert constructed[0].settings["openai_background"] is False
    assert model.receipts[0].state is CallState.RECONCILING
