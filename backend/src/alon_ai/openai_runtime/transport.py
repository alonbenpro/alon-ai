"""Single-call Responses transport. The SDK is never allowed to retry silently."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

from openai import APITimeoutError, AsyncOpenAI
from pydantic import SecretStr

from alon_ai.openai_runtime.contract import OpenAIProfile


def build_request(profile: OpenAIProfile, input_json: str) -> dict[str, Any]:
    return {
        "model": profile.model_identifier,
        "instructions": profile.instructions,
        "input": input_json,
        "reasoning": {"effort": profile.reasoning_effort},
        "max_output_tokens": profile.max_output_tokens,
        "text": {
            "format": {
                "type": "json_schema",
                "name": profile.schema_version,
                "strict": True,
                "schema": json.loads(profile.schema_json),
            }
        },
        "tools": [],
        "tool_choice": "none",
        "store": False,
    }


class ResponsesTransport(Protocol):
    async def create(
        self,
        *,
        profile: OpenAIProfile,
        input_json: str,
        secret: SecretStr,
        client_request_id: UUID,
        timeout_seconds: float,
    ) -> Mapping[str, Any]: ...


class SDKResponsesTransport:
    async def create(
        self,
        *,
        profile: OpenAIProfile,
        input_json: str,
        secret: SecretStr,
        client_request_id: UUID,
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        # The governed executor owns the dispatch fence. SDK retries would create
        # unledgered paid attempts after a timeout or network ambiguity.
        async with AsyncOpenAI(
            api_key=secret.get_secret_value(),
            max_retries=0,
            timeout=timeout_seconds,
        ) as client:
            try:
                response = await client.responses.create(
                    **build_request(profile, input_json),
                    extra_headers={"X-Client-Request-Id": str(client_request_id)},
                )
            except APITimeoutError:
                raise TimeoutError("Responses dispatch timed out") from None
        return response.model_dump(mode="json")
