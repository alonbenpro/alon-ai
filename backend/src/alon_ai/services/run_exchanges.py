"""Visible native exchanges; retained evidence stays in the governed content store."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.toolsets import WrapperToolset
from pydantic_core import to_jsonable_python

from alon_ai.agents.tools.research import SavedEvidenceExcerpt
from alon_ai.services.run_diagnostics import diagnostic_for_error


class RunExchange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_request_number: int | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    status: Literal["PREPARED", "COMPLETED", "FAILED", "NOT_DISPATCHED", "UNAVAILABLE"]
    payload: dict[str, Any]
    omissions: list[str] = Field(default_factory=list)


_PARAMETERS = TypeAdapter(ModelRequestParameters)
_SOURCE_FIELDS = {
    "source_excerpt",
    "source_text",
    "excerpt",
    "raw_content",
    "source_content",
    "page_markdown",
    "markdown",
    "html",
}
_SECRET_FIELDS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "set_cookie",
    "headers",
    "password",
    "secret",
    "access_token",
    "refresh_token",
    "encrypted_content",
    "signature",
    "provider_details",
}
_CREDENTIAL = re.compile(
    r"\bsk-[A-Za-z0-9_-]{8,}|\bBearer\s+[A-Za-z0-9._-]+", re.IGNORECASE
)
_RESEARCH_URL_TOOLS = {"capture_page", "capture_pdf", "map_site"}


def _mentioned_fields(value: str) -> set[str]:
    fields = set()
    tokens = re.findall(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')\s*(?::|$)', value)
    for token in tokens:
        try:
            # Decode JSON escapes even when the enclosing response is truncated.
            key = json.loads(
                token if token.startswith('"') else '"' + token[1:-1] + '"'
            )
        except ValueError:
            # An undecodable key cannot establish that its value is retainable.
            return _SOURCE_FIELDS | _SECRET_FIELDS
        fields.add(key.lower().replace("-", "_"))
    return fields


def _visible(value: Any, omissions: list[str], *, source_fields: bool = True):
    """Preserve visible values exactly unless an explicit excluded field is present."""
    if isinstance(value, str):
        cleaned = _CREDENTIAL.sub("[credential omitted]", value)
        if cleaned != value:
            omissions.append("Credential values were omitted.")
        if source_fields:
            try:
                parsed = json.loads(cleaned)
            except (ValueError, TypeError):
                if _mentioned_fields(cleaned) & (_SOURCE_FIELDS | _SECRET_FIELDS):
                    omissions.append(
                        "Malformed structured content containing excluded source or credential fields was omitted."
                    )
                    return "[malformed restricted structured content omitted]"
                return cleaned
            if isinstance(parsed, (dict, list)):
                before = len(omissions)
                projected = _visible(parsed, omissions)
                if len(omissions) != before:
                    return json.dumps(projected, ensure_ascii=False)
        return cleaned
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _SECRET_FIELDS:
                result[key] = "[credential or provider metadata omitted]"
                omissions.append(f"Excluded field: {key}.")
            elif source_fields and normalized in _SOURCE_FIELDS:
                result[key] = "[source content omitted; use retained evidence]"
                omissions.append(f"Source content field {key} was omitted.")
            else:
                result[key] = _visible(child, omissions, source_fields=source_fields)
        return result
    if isinstance(value, (list, tuple)):
        return [
            _visible(item, omissions, source_fields=source_fields) for item in value
        ]
    return to_jsonable_python(value)


def _tool_arguments(name: str, arguments: Any, omissions: list[str]):
    if name in _RESEARCH_URL_TOOLS:
        parsed = arguments
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
            except ValueError:
                omissions.append(
                    "Malformed research URL arguments were omitted because transient source provenance is unavailable."
                )
                return "[malformed research URL arguments omitted]"
        if not isinstance(parsed, dict):
            omissions.append("Research arguments with an invalid shape were omitted.")
            return "[invalid research arguments omitted]"
        projected = {}
        if (
            name == "map_site"
            and "limit" in parsed
            and (type(parsed["limit"]) is int or parsed["limit"] is None)
        ):
            projected["limit"] = parsed["limit"]
        if "url" in parsed:
            omissions.append(
                "Research URL arguments were omitted because transient source provenance is unavailable."
            )
        if set(parsed) - {"url"} - set(projected):
            omissions.append("Unrecognized research arguments were omitted.")
        return _visible(projected, omissions)
    return _visible(arguments, omissions)


def tool_result_payload(
    name: str, arguments: dict, result: Any
) -> tuple[dict, list[str]]:
    omissions: list[str] = []
    if name == "read_saved_evidence" and isinstance(result, SavedEvidenceExcerpt):
        return {
            "type": "retained_evidence_excerpt",
            "reference": result.reference.model_dump(mode="json"),
            "max_chars": arguments.get("max_chars", 4000),
            "availability": "CURRENT_RIGHTS_REQUIRED",
        }, ["Source excerpt is resolved from retained evidence under current rights."]
    if name in {"search_web", "map_site"} and isinstance(result, (list, tuple)):
        # References are retained identities; transient discovery URLs are not.
        from alon_ai.services.schemas.records import SourceReference

        if not all(isinstance(item, SourceReference) for item in result):
            return {
                "observed_count": len(result),
                "availability": "TRANSIENT_RESULT_NOT_RETAINED",
            }, [
                "Transient discovery results were not retained under current provider rights."
            ]
    return {"result": _visible(to_jsonable_python(result), omissions)}, omissions


def _response_parts(
    response: ModelResponse, omissions: list[str], allowed_names: set[str] | None = None
) -> list[dict]:
    parts = []
    for part in response.parts:
        if isinstance(part, TextPart):
            parts.append(
                {"part_kind": "text", "content": _visible(part.content, omissions)}
            )
        elif isinstance(part, ToolCallPart):
            if allowed_names is None or part.tool_name not in allowed_names:
                omissions.append("An unregistered tool call was omitted.")
                continue
            parts.append(
                {
                    "part_kind": "tool-call",
                    "tool_name": part.tool_name,
                    "tool_call_id": part.tool_call_id,
                    "args": _tool_arguments(part.tool_name, part.args, omissions),
                }
            )
        elif isinstance(part, ThinkingPart):
            omissions.append("Reasoning and encrypted signatures are excluded.")
        else:
            omissions.append(
                f"Unsupported response part {part.part_kind} was not retained."
            )
    return parts


def model_request_exchange(
    number, model, messages: list[ModelMessage], parameters, settings
) -> RunExchange:
    omissions: list[str] = []
    allowed_names = {
        tool.name for tool in [*parameters.function_tools, *parameters.output_tools]
    }
    calls = {}
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    try:
                        calls[part.tool_call_id] = part.args_as_dict()
                    except ValueError:
                        # Preserve malformed visible arguments in the response below.
                        calls[part.tool_call_id] = {}
    projected = []
    for message in messages:
        if isinstance(message, ModelResponse):
            projected.append(
                {
                    "kind": "response",
                    "parts": _response_parts(message, omissions, allowed_names),
                }
            )
            continue
        parts = []
        for part in message.parts:
            if isinstance(part, (SystemPromptPart, UserPromptPart)):
                parts.append(
                    {
                        "part_kind": part.part_kind,
                        "content": _visible(part.content, omissions),
                    }
                )
            elif isinstance(part, ToolReturnPart):
                if part.tool_name not in allowed_names:
                    omissions.append("An unregistered tool return was omitted.")
                    continue
                payload, omitted = tool_result_payload(
                    part.tool_name, calls.get(part.tool_call_id, {}), part.content
                )
                omissions.extend(omitted)
                parts.append(
                    {
                        "part_kind": "tool-return",
                        "tool_name": part.tool_name,
                        "tool_call_id": part.tool_call_id,
                        "content": payload,
                    }
                )
            elif isinstance(part, RetryPromptPart):
                if part.tool_name is not None and part.tool_name not in allowed_names:
                    omissions.append("An unregistered tool retry was omitted.")
                    continue
                content = part.content
                if isinstance(content, list):
                    content = [
                        {
                            key: value
                            for key, value in error.items()
                            if key not in {"input", "ctx"}
                        }
                        for error in content
                    ]
                    omissions.append(
                        "Validation retry input copies and exception context are excluded."
                    )
                parts.append(
                    {
                        "part_kind": "retry-prompt",
                        "content": _visible(content, omissions),
                        "tool_name": part.tool_name,
                        "tool_call_id": part.tool_call_id,
                    }
                )
            else:
                omissions.append(
                    f"Unsupported request part {part.part_kind} was not retained."
                )
        projected.append(
            {
                "kind": "request",
                "instructions": _visible(message.instructions, omissions),
                "parts": parts,
            }
        )
    return RunExchange(
        model_request_number=number,
        status="PREPARED",
        payload={
            "model_identifier": model,
            "messages": projected,
            "parameters": _visible(
                _PARAMETERS.dump_python(parameters, mode="json"),
                omissions,
                source_fields=False,
            ),
            "settings": _visible(settings, omissions, source_fields=False),
        },
        omissions=list(dict.fromkeys(omissions)),
    )


def model_response_exchange(
    number,
    response: ModelResponse | None,
    *,
    failed=False,
    error_code=None,
    allowed_names: set[str] | None = None,
) -> RunExchange:
    omissions: list[str] = []
    payload = {
        "parts": _response_parts(response, omissions, allowed_names)
        if response
        else [],
        "finish_reason": response.finish_reason if response else None,
        "state": response.state if response else None,
    }
    if error_code:
        payload["error_code"] = error_code
    if response is None:
        omissions.append("No model response content was received.")
    return RunExchange(
        model_request_number=number,
        status="FAILED" if failed else "COMPLETED",
        payload=payload,
        omissions=list(dict.fromkeys(omissions)),
    )


async def record_exchange(store, run_id, event_type, exchange, detail=None):
    """Persistence cannot replace a provider outcome or the original tool error."""
    try:
        if callable(exchange):
            exchange = exchange()
        await store.record_activity(run_id, event_type, detail, exchange=exchange)
    except Exception as error:  # noqa: BLE001 - capture must not change a provider outcome
        structlog.get_logger(__name__).error(
            "agent_run_exchange_persistence_failed",
            run_id=str(run_id),
            error_type=type(error).__name__,
        )


@dataclass
class ExchangeToolset(WrapperToolset):
    store: Any
    run_id: UUID

    async def call_tool(self, name, tool_args, ctx, tool):
        def request_exchange():
            omissions: list[str] = []
            payload = {"arguments": _tool_arguments(name, tool_args, omissions)}
            return RunExchange(
                tool_name=name,
                tool_call_id=ctx.tool_call_id,
                status="PREPARED",
                payload=payload,
                omissions=omissions,
            )

        await record_exchange(
            self.store,
            self.run_id,
            "TOOL_REQUEST",
            request_exchange,
        )
        try:
            result = await self.wrapped.call_tool(name, tool_args, ctx, tool)
        except BaseException as error:

            def failed_exchange(error=error):
                diagnostic = (
                    diagnostic_for_error("TOOL_EXECUTION", error)
                    if isinstance(error, Exception)
                    else None
                )
                return RunExchange(
                    tool_name=name,
                    tool_call_id=ctx.tool_call_id,
                    status="FAILED",
                    payload={
                        "error": diagnostic.model_dump(mode="json")
                        if diagnostic
                        else {"code": "CANCELLED"}
                    },
                )

            await asyncio.shield(
                record_exchange(
                    self.store,
                    self.run_id,
                    "TOOL_RESPONSE",
                    failed_exchange,
                )
            )
            raise

        def completed_exchange():
            payload, omissions = tool_result_payload(name, tool_args, result)
            status = (
                "NOT_DISPATCHED"
                if getattr(result, "status", None) == "NOT_DISPATCHED"
                or isinstance(result, dict)
                and result.get("status") == "NOT_DISPATCHED"
                else "COMPLETED"
            )
            return RunExchange(
                tool_name=name,
                tool_call_id=ctx.tool_call_id,
                status=status,
                payload=payload,
                omissions=omissions,
            )

        await record_exchange(
            self.store,
            self.run_id,
            "TOOL_RESPONSE",
            completed_exchange,
        )
        return result


async def resolve_exchange_evidence(
    exchange: RunExchange, *, engine, run_id: UUID, experiment_id: UUID
) -> RunExchange:
    """Resolve only exact existing evidence linked to this run; never retain a copy."""
    from alon_ai.db.repositories.accounting import GovernanceRepository
    from alon_ai.db.repositories.agent_runs import AgentRunRepository
    from alon_ai.provider_usage.schemas.accounting import AccountingDenied
    from alon_ai.services.schemas.records import SourceReference

    repository = GovernanceRepository(engine)
    run_store = AgentRunRepository(engine)
    omissions = list(exchange.omissions)

    async def resolve(value):
        if isinstance(value, list):
            return [await resolve(child) for child in value]
        if not isinstance(value, dict):
            return value
        if value.get("type") != "retained_evidence_excerpt":
            return {key: await resolve(child) for key, child in value.items()}
        unavailable = {**value, "availability": "UNAVAILABLE"}
        reason = "EVIDENCE_REFERENCE_INVALID"
        try:
            ref = SourceReference.model_validate_json(json.dumps(value["reference"]))
            bound = value["max_chars"]
            if (
                ref.kind != "RETAINED_CONTENT"
                or ref.call_id is None
                or type(bound) is not int
                or not 1 <= bound <= 4000
            ):
                raise ValueError
            row = await run_store.scoped_evidence_reference(run_id, experiment_id, ref)
            reason = "EVIDENCE_SCOPE_OR_RETENTION"
            if row is None or row["expires_at"] <= repository.clock():
                raise ValueError
            reason = "EVIDENCE_RIGHTS"
            fields = await repository.read_content(ref.call_id)
            reason = "EVIDENCE_FIELD_UNAVAILABLE"
            if ref.field not in fields:
                raise ValueError
            text = "\n\n".join(fields[ref.field])[:bound]
            return {**value, "availability": "AVAILABLE", "text": text}
        except (AccountingDenied, ValueError, KeyError, TypeError):
            omissions.append(
                "Referenced source excerpt is unavailable under current scope, rights or retention."
            )
            return {**unavailable, "reason": reason}

    payload = await resolve(exchange.payload)
    return exchange.model_copy(
        update={"payload": payload, "omissions": list(dict.fromkeys(omissions))}
    )
