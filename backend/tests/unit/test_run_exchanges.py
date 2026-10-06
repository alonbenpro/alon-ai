"""Actual visible exchanges, with licensed evidence kept in its existing store."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import FunctionToolset

from alon_ai.agents.tools.research import SavedEvidenceExcerpt
from alon_ai.services.run_exchanges import (
    ExchangeToolset,
    model_request_exchange,
    model_response_exchange,
    tool_result_payload,
)
from alon_ai.services.schemas.records import SourceReference


def reference():
    return SourceReference.retained_content(
        retained_id=uuid4(),
        call_id=uuid4(),
        grant_id=uuid4(),
        grant_version=1,
        field="PAGE_MARKDOWN",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


def parameters(*names):
    return ModelRequestParameters(
        function_tools=[
            ToolDefinition(name=name, parameters_json_schema={"type": "object"})
            for name in names
        ]
    )


def test_request_keeps_actual_instructions_prompt_and_tool_args_but_not_source_copies():
    ref = reference()
    messages = [
        ModelRequest(
            [UserPromptPart("Original operator prompt")],
            instructions="Actual dynamic instruction",
        ),
        ModelResponse(
            [
                ToolCallPart(
                    "search_web", {"query": "buyer price"}, tool_call_id="search-1"
                ),
                ToolCallPart(
                    "read_saved_evidence",
                    {"retained_id": str(ref.retained_id), "max_chars": 17},
                    tool_call_id="read-1",
                ),
                ThinkingPart("hidden reasoning", signature="encrypted-signature"),
            ]
        ),
        ModelRequest(
            [
                ToolReturnPart(
                    "search_web",
                    ("https://transient.example/",),
                    tool_call_id="search-1",
                ),
                ToolReturnPart(
                    "read_saved_evidence",
                    SavedEvidenceExcerpt(ref, "licensed excerpt"),
                    tool_call_id="read-1",
                ),
            ]
        ),
    ]
    exchange = model_request_exchange(
        2,
        "approved-model",
        messages,
        parameters("search_web", "read_saved_evidence"),
        {"max_tokens": 1200},
    )
    encoded = exchange.model_dump_json()
    assert "Original operator prompt" in encoded
    assert "Actual dynamic instruction" in encoded
    assert "buyer price" in encoded and "search-1" in encoded
    assert "max_tokens" in encoded and "1200" in encoded
    assert "licensed excerpt" not in encoded and "transient.example" not in encoded
    assert "hidden reasoning" not in encoded and "encrypted-signature" not in encoded
    assert str(ref.retained_id) in encoded
    assert exchange.omissions


def test_failed_visible_json_is_retained_and_source_fields_credentials_are_explicitly_omitted():
    raw = '{"price":{"amount":"not-a-number","kind":"OBSERVED"}}'
    response = ModelResponse(
        [
            TextPart(raw),
            ThinkingPart("private reasoning", signature="opaque-signature"),
            ToolCallPart(
                "capture_page",
                {"url": "https://buyer.example/"},
                tool_call_id="capture-3",
            ),
        ],
        finish_reason="length",
        provider_details={"headers": {"Authorization": "secret-header"}},
    )
    exchange = model_response_exchange(
        3, response, failed=True, allowed_names={"capture_page"}
    )
    assert exchange.status == "FAILED"
    assert exchange.payload["parts"][0]["content"] == raw
    assert exchange.payload["parts"][1]["tool_call_id"] == "capture-3"
    assert "private reasoning" not in exchange.model_dump_json()
    assert "opaque-signature" not in exchange.model_dump_json()
    assert "secret-header" not in exchange.model_dump_json()
    assert exchange.payload["finish_reason"] == "length"

    sensitive = model_response_exchange(
        4,
        ModelResponse(
            [
                TextPart(
                    json.dumps(
                        {
                            "finding": "Visible finding",
                            "source_excerpt": "licensed source bytes",
                            "api_key": "sk-credential-value",
                            "price": {"amount": "wrong"},
                        }
                    )
                )
            ]
        ),
        failed=True,
    )
    encoded = sensitive.model_dump_json()
    assert "Visible finding" in encoded and "wrong" in encoded
    assert (
        "licensed source bytes" not in encoded and "sk-credential-value" not in encoded
    )
    assert sensitive.omissions


def test_saved_evidence_result_retains_reference_and_exact_bound_only():
    ref = reference()
    payload, omissions = tool_result_payload(
        "read_saved_evidence", {"max_chars": 8}, SavedEvidenceExcerpt(ref, "licensed")
    )
    assert payload["type"] == "retained_evidence_excerpt"
    assert payload["max_chars"] == 8
    assert payload["reference"]["retained_id"] == str(ref.retained_id)
    assert "licensed" not in json.dumps(payload)
    assert omissions


def test_malformed_tool_arguments_remain_visible_without_breaking_request_capture():
    malformed = '{"query":'
    exchange = model_request_exchange(
        2,
        "controlled-model",
        [
            ModelResponse(
                [
                    ToolCallPart("search_web", malformed, tool_call_id="malformed-1"),
                ]
            )
        ],
        parameters("search_web"),
        {},
    )
    assert exchange.payload["messages"][0]["parts"][0]["args"] == malformed


@pytest.mark.parametrize(
    "field", ["source_excerpt", "api_key", "headers", "encrypted_content"]
)
def test_truncated_restricted_json_is_withheld_but_failed_price_only_output_is_exact(
    field,
):
    raw = '{"' + field + '":"restricted-content'
    exchange = model_response_exchange(
        1, ModelResponse([TextPart(raw)], finish_reason="length"), failed=True
    )
    assert "restricted-content" not in exchange.model_dump_json()
    assert exchange.omissions
    assert "omitted" in exchange.payload["parts"][0]["content"]
    price_only = '{"price":{"amount":"$12/mo"'
    price = model_response_exchange(
        2, ModelResponse([TextPart(price_only)], finish_reason="length"), failed=True
    )
    assert price.payload["parts"][0]["content"] == price_only


async def test_native_search_then_capture_never_retains_transient_url_in_any_exchange():
    events = []
    received = []
    transient_url = "https://transient-result.example/research"
    ref = reference()

    class Store:
        async def record_activity(self, run_id, kind, detail=None, *, exchange=None):
            events.append((kind, exchange))

    def search_web(query: str):
        return (transient_url,)

    def capture_page(url: str, limit: int = 1):
        received.append((url, limit))
        return (ref,)

    turns = []

    def respond(messages, info):
        turns.append(messages)
        events.append(
            (
                "MODEL_REQUEST",
                model_request_exchange(
                    len(turns),
                    "controlled",
                    messages,
                    parameters("search_web", "capture_page"),
                    {},
                ),
            )
        )
        if len(turns) == 1:
            response = ModelResponse(
                [
                    ToolCallPart(
                        "search_web",
                        {"query": "buyer evidence"},
                        tool_call_id="search-real",
                    )
                ]
            )
        elif len(turns) == 2:
            returned = [
                part
                for message in messages
                if isinstance(message, ModelRequest)
                for part in message.parts
                if isinstance(part, ToolReturnPart)
            ]
            selected = returned[-1].content
            assert isinstance(selected, tuple)
            assert selected == (transient_url,)
            selected_url = selected[0]
            assert isinstance(selected_url, str)
            response = ModelResponse(
                [
                    ToolCallPart(
                        "capture_page",
                        {"url": selected_url, "limit": 1},
                        tool_call_id="capture-real",
                    )
                ]
            )
        else:
            response = ModelResponse([TextPart("Researched finding")])
        events.append(
            (
                "MODEL_RESPONSE",
                model_response_exchange(
                    len(turns), response, allowed_names={"search_web", "capture_page"}
                ),
            )
        )
        return response

    agent = Agent(
        FunctionModel(respond),
        toolsets=[
            ExchangeToolset(
                FunctionToolset(tools=[search_web, capture_page]), Store(), uuid4()
            )
        ],
    )
    assert (await agent.run("Find buyer evidence")).output == "Researched finding"
    assert received == [(transient_url, 1)]  # the real tool input is never changed
    assert transient_url not in "\n".join(
        exchange.model_dump_json() for _, exchange in events
    )
    request = next(
        exchange
        for kind, exchange in events
        if kind == "TOOL_REQUEST" and exchange.tool_name == "capture_page"
    )
    assert request.tool_call_id == "capture-real"
    assert request.payload["arguments"] == {}
    assert request.omissions


def test_unknown_research_url_keys_and_nested_args_are_omitted_without_mutating_model_args():
    arguments = {
        "Url": "https://transient.example/",
        "extra": {"url": "https://nested-transient.example/"},
    }
    response = ModelResponse(
        [ToolCallPart("capture_page", arguments, tool_call_id="unknown-url")]
    )
    exchange = model_response_exchange(1, response, allowed_names={"capture_page"})
    assert exchange.payload["parts"][0]["args"] == {}
    assert "transient.example" not in exchange.model_dump_json()
    assert exchange.omissions
    original_call = response.parts[0]
    assert isinstance(original_call, ToolCallPart)
    assert original_call.args == arguments


@pytest.mark.parametrize(
    ("raw", "restricted"),
    [
        (r'{"source\u005fexcerpt":"licensed source", "price":', "licensed source"),
        (r'{"api\u005fkey":"fc-private-credential", "price":', "fc-private-credential"),
    ],
)
def test_malformed_escaped_restricted_keys_are_decoded_before_omission(raw, restricted):
    exchange = model_response_exchange(
        1, ModelResponse([TextPart(raw)], finish_reason="length"), failed=True
    )
    assert restricted not in exchange.model_dump_json()
    assert exchange.omissions


def test_malformed_escaped_research_url_arguments_are_omitted_from_response_and_history():
    raw = r'{"\u0075rl":"https://transient.example/", "other":'
    response = ModelResponse(
        [ToolCallPart("capture_page", raw, tool_call_id="escaped-url")]
    )
    captured = model_response_exchange(1, response, allowed_names={"capture_page"})
    history = model_request_exchange(
        2, "controlled", [response], parameters("capture_page"), {}
    )
    for exchange in (captured, history):
        assert "transient.example" not in exchange.model_dump_json()
        assert "escaped-url" in exchange.model_dump_json()
        assert exchange.omissions


def test_valid_escaped_restricted_keys_keep_owned_values_and_omit_source_and_secret():
    raw = r'{"source\u005fexcerpt":"licensed source", "api\u005fkey":"fc-private-credential", "price":{"amount":"$12/mo"}}'
    exchange = model_response_exchange(1, ModelResponse([TextPart(raw)]), failed=True)
    text = exchange.payload["parts"][0]["content"]
    assert "licensed source" not in text and "fc-private-credential" not in text
    assert json.loads(text)["price"]["amount"] == "$12/mo"
    assert exchange.omissions


def test_unregistered_tool_names_are_absent_from_response_history_and_retry():
    secret_name = "SECRET_provider_payload"
    response = ModelResponse(
        [
            ToolCallPart(
                secret_name, {"url": "https://example.com/"}, tool_call_id="unknown"
            )
        ]
    )
    captured = model_response_exchange(1, response)
    assert secret_name not in captured.model_dump_json()
    assert captured.omissions
    request = model_request_exchange(
        2,
        "controlled",
        [
            response,
            ModelRequest(
                [
                    ToolReturnPart(
                        secret_name, "unsafe provider metadata", tool_call_id="unknown"
                    ),
                    RetryPromptPart("unregistered tool retry", tool_name=secret_name),
                ]
            ),
        ],
        parameters("capture_page"),
        {},
    )
    assert secret_name not in request.model_dump_json()
    assert "unsafe provider metadata" not in request.model_dump_json()
    assert request.omissions


@pytest.mark.parametrize("outcome", ["success", "failure"])
async def test_tool_projection_failures_cannot_change_actual_tool_outcome(
    monkeypatch, outcome
):
    from alon_ai.services import run_exchanges

    ran = []

    class Store:
        async def record_activity(self, run_id, kind, detail=None, *, exchange=None):
            pass

    def fail_projection(*args, **kwargs):
        raise ValueError("capture-only failure")

    monkeypatch.setattr(run_exchanges, "_visible", fail_projection)
    monkeypatch.setattr(run_exchanges, "tool_result_payload", fail_projection)
    monkeypatch.setattr(run_exchanges, "diagnostic_for_error", fail_projection)

    def execute(query: str):
        ran.append(query)
        if outcome == "failure":
            raise RuntimeError("original tool failure")
        return "actual tool success"

    turns = []

    def respond(messages, info):
        turns.append(messages)
        if len(turns) == 1:
            return ModelResponse(
                [
                    ToolCallPart(
                        "execute",
                        {"query": "original argument"},
                        tool_call_id="capture-fails",
                    )
                ]
            )
        return ModelResponse([TextPart("Complete")])

    agent = Agent(
        FunctionModel(respond),
        toolsets=[ExchangeToolset(FunctionToolset(tools=[execute]), Store(), uuid4())],
    )
    if outcome == "failure":
        with pytest.raises(RuntimeError, match="original tool failure"):
            await agent.run("Execute")
    else:
        assert (await agent.run("Execute")).output == "Complete"
    assert ran == ["original argument"]


async def test_tool_scheduling_stop_is_visible_before_a_next_model_request():
    recorded = []

    class Store:
        async def record_activity(self, run_id, kind, detail=None, *, exchange=None):
            recorded.append((kind, exchange))

    def unavailable(query: str):
        return {"status": "NOT_DISPATCHED", "guidance": "Use saved evidence"}

    turns = []

    def respond(messages, info):
        turns.append(messages)
        if len(turns) == 1:
            return ModelResponse(
                [ToolCallPart("unavailable", {"query": "buyer"}, tool_call_id="stop-1")]
            )
        assert len(recorded) == 2
        return ModelResponse([TextPart("Gap preserved")])

    agent = Agent(
        FunctionModel(respond),
        toolsets=[
            ExchangeToolset(FunctionToolset(tools=[unavailable]), Store(), uuid4())
        ],
    )
    assert (await agent.run("Research buyer")).output == "Gap preserved"
    assert recorded[-1][1].status == "NOT_DISPATCHED"
    assert recorded[-1][1].tool_call_id == "stop-1"
    assert recorded[-1][1].payload["result"]["guidance"] == "Use saved evidence"


async def test_native_wrapper_records_last_failed_tool_with_native_id_and_original_error():
    recorded = []

    class Store:
        async def record_activity(self, run_id, kind, detail=None, *, exchange=None):
            recorded.append((kind, exchange))

    async def fail(query: str):
        raise ValueError("do not retain arbitrary exception content")

    def respond(messages, info):
        return ModelResponse(
            [
                ToolCallPart(
                    "fail", {"query": "actual argument"}, tool_call_id="failure-1"
                )
            ]
        )

    agent = Agent(
        FunctionModel(respond),
        toolsets=[ExchangeToolset(FunctionToolset(tools=[fail]), Store(), uuid4())],
    )
    with pytest.raises(ValueError, match="do not retain"):
        await agent.run("run the tool")
    assert [kind for kind, _ in recorded] == ["TOOL_REQUEST", "TOOL_RESPONSE"]
    assert recorded[0][1].tool_call_id == recorded[1][1].tool_call_id == "failure-1"
    assert recorded[0][1].payload == {"arguments": {"query": "actual argument"}}
    assert recorded[1][1].status == "FAILED"
    assert "do not retain" not in recorded[1][1].model_dump_json()
