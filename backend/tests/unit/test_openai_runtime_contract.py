"""The shared Responses boundary is deterministic and fails closed."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import SecretStr

from alon_ai.openai_runtime.contract import (
    AdvisoryAnswer,
    OpenAIProfile,
    PremiumAuthorization,
    Route,
    RoutingFacts,
    RoutingPolicy,
    classify_response,
)
from alon_ai.openai_runtime.transport import SDKResponsesTransport, build_request

SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


def profile() -> OpenAIProfile:
    return OpenAIProfile(
        config_id=uuid4(),
        config_version=uuid4(),
        adapter_version=uuid4(),
        prompt_version="answer-v1",
        instructions="Summarize only the supplied evidence.",
        schema_version="answer-v1",
        json_schema=SCHEMA,
        output_model=AdvisoryAnswer,
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=300,
    )


def test_route_never_accepts_agent_selected_model_or_tools():
    cheap, strong, premium = uuid4(), uuid4(), uuid4()
    scope = uuid4()
    now = datetime.now(UTC)
    authorization = PremiumAuthorization(
        scope=scope,
        expires_at=now + timedelta(minutes=1),
        authorization_id=uuid4(),
        approved_by=uuid4(),
        approved_at=now,
    )
    policy = RoutingPolicy(
        cheap=cheap, stronger=strong, premium=premium, approved_premium=(authorization,)
    )
    assert (
        policy.select(RoutingFacts(needs_ai=False), scope=scope, now=now).route
        is Route.NO_AI
    )
    assert (
        policy.select(RoutingFacts(needs_ai=True), scope=scope, now=now).config_id
        == cheap
    )
    assert (
        policy.select(
            RoutingFacts(needs_ai=True, validated_escalation=True), scope=scope, now=now
        ).config_id
        == strong
    )
    with pytest.raises(PermissionError):
        policy.select(
            RoutingFacts(needs_ai=True, premium_requested=True), scope=scope, now=now
        )
    assert (
        policy.select(
            RoutingFacts(
                needs_ai=True,
                premium_requested=True,
                premium_authorization=authorization,
            ),
            scope=scope,
            now=now,
        ).config_id
        == premium
    )
    with pytest.raises(PermissionError):
        policy.select(
            RoutingFacts(
                needs_ai=True,
                premium_requested=True,
                premium_authorization=authorization,
            ),
            scope=uuid4(),
            now=now,
        )
    with pytest.raises(PermissionError):
        policy.select(
            RoutingFacts(
                needs_ai=True,
                premium_requested=True,
                premium_authorization=authorization,
            ),
            scope=scope,
            now=authorization.expires_at,
        )


def test_profile_requires_strict_object_schema():
    p = profile()
    with pytest.raises(ValueError):
        replace(p, json_schema={**SCHEMA, "additionalProperties": True})
    with pytest.raises(TypeError):
        p.json_schema["properties"]["answer"]["type"] = "number"


def test_response_classifies_refusal_mismatch_incomplete_and_tool_output():
    p = profile()
    base = {
        "status": "completed",
        "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
    }
    good = {
        **base,
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": '{"answer":"ok"}'}],
            }
        ],
    }
    parsed = classify_response(good, p)
    assert parsed.outcome == "SUCCEEDED"
    assert parsed.output == AdvisoryAnswer(answer="ok")
    assert parsed.output_hash is not None
    assert (
        classify_response(
            {
                **base,
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "no"}],
                    }
                ],
            },
            p,
        ).outcome
        == "REFUSED"
    )
    assert (
        classify_response(
            {
                **base,
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"wrong":1}'}],
                    }
                ],
            },
            p,
        ).outcome
        == "SCHEMA_MISMATCH"
    )
    assert (
        classify_response(
            {
                **base,
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output": [],
            },
            p,
        ).outcome
        == "INCOMPLETE"
    )
    assert (
        classify_response(
            {**base, "output": [{"type": "function_call", "name": "send_email"}]}, p
        ).outcome
        == "SCHEMA_MISMATCH"
    )
    assert (
        classify_response({**base, "status": "cancelled", "output": []}, p).outcome
        == "CANCELLED"
    )


def test_reasoning_item_before_typed_message_is_valid():
    parsed = classify_response(
        {
            "status": "completed",
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"answer":"ok"}'}],
                },
            ],
        },
        profile(),
    )
    assert parsed.outcome == "SUCCEEDED"
    assert parsed.output == AdvisoryAnswer(answer="ok")


def test_declared_schema_constraints_are_enforced_after_typed_parse():
    limited = replace(
        profile(),
        json_schema={
            "type": "object",
            "properties": {"answer": {"type": "string", "enum": ["allowed"]}},
            "required": ["answer"],
            "additionalProperties": False,
        },
    )
    response = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": '{"answer":"disallowed"}'}],
            }
        ],
    }
    assert classify_response(response, limited).outcome == "SCHEMA_MISMATCH"


def test_response_usage_absence_is_unknown_and_never_zero():
    p = profile()
    parsed = classify_response(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"answer":"ok"}'}],
                }
            ],
        },
        p,
    )
    assert parsed.usage is None


def test_missing_cached_detail_is_not_invented_as_zero():
    response = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": '{"answer":"ok"}'}],
            }
        ],
        "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
    }
    parsed = classify_response(response, profile())
    assert parsed.usage is not None
    assert "cached_tokens" not in parsed.usage


def test_request_disables_storage_and_all_tool_authority():
    request = build_request(profile(), '{"evidence":"licensed"}')
    assert request["store"] is False
    assert request["tools"] == []
    assert request["tool_choice"] == "none"
    assert request["text"]["format"]["strict"] is True
    assert request["input"] == '{"evidence":"licensed"}'
    assert "model" in request and "reasoning" in request


@pytest.mark.asyncio
async def test_sdk_transport_has_no_hidden_retry_or_live_network(monkeypatch):
    options = {}

    class StubResponse:
        def model_dump(self, *, mode):
            assert mode == "json"
            return {"status": "completed", "output": []}

    class StubResponses:
        async def create(self, **kwargs):
            options["request"] = kwargs
            return StubResponse()

    class StubClient:
        def __init__(self, **kwargs):
            options["client"] = kwargs
            self.responses = StubResponses()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr("alon_ai.openai_runtime.transport.AsyncOpenAI", StubClient)
    await SDKResponsesTransport().create(
        profile=profile(),
        input_json='{"sources":[]}',
        secret=SecretStr("recorded-only"),
        client_request_id=uuid4(),
        timeout_seconds=3,
    )
    assert options["client"]["max_retries"] == 0
    assert options["client"]["timeout"] == 3
    assert options["request"]["tools"] == []
    assert options["request"]["store"] is False
    assert "X-Client-Request-Id" in options["request"]["extra_headers"]
