"""Construct the approved Pydantic AI/OpenAI Responses model.

The caller supplies a secret from approved storage and wraps the resulting
Model with per-request admission/accounting before passing it to an agent.
"""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Literal

import httpx2 as httpx
from openai import AsyncOpenAI
from pydantic import SecretStr
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider


class _OwnedOpenAIModel(OpenAIResponsesModel):
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.client.close()


def build_openai_model(
    *,
    model_identifier: str,
    secret: SecretStr,
    timeout_seconds: float,
    max_output_tokens: int,
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"],
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> OpenAIResponsesModel:
    """The sole production construction path; use as an async context manager.

    The context owns and closes its client, including on a failed request.
    ``http_transport`` provides controlled tests without a provider connection.
    """

    if not model_identifier or not 0 < timeout_seconds <= 3600:
        raise ValueError("invalid approved OpenAI model or timeout")
    if not 1 <= max_output_tokens <= 32768:
        raise ValueError("invalid approved output-token limit")
    client = AsyncOpenAI(
        api_key=secret.get_secret_value(),
        max_retries=0,
        timeout=timeout_seconds,
        base_url="https://api.openai.com/v1",
        http_client=httpx.AsyncClient(
            transport=http_transport,
            follow_redirects=False,
        ),
    )
    provider = OpenAIProvider(openai_client=client)
    settings = OpenAIResponsesModelSettings(
        openai_store=False,
        openai_background=False,
        max_tokens=max_output_tokens,
        timeout=timeout_seconds,
        openai_reasoning_effort=reasoning_effort,
    )
    return _OwnedOpenAIModel(model_identifier, provider=provider, settings=settings)


def openai_model_factory(
    model_identifier: str,
    *,
    timeout_seconds: float = 60,
    max_output_tokens: int = 32768,
    reasoning_effort: Literal[
        "none", "minimal", "low", "medium", "high", "xhigh"
    ] = "low",
    http_transport: httpx.AsyncBaseTransport | None = None,
) -> Callable[[SecretStr], Model]:
    """Defer construction and secret access until governed dispatch admits it."""

    def create(secret: SecretStr) -> Model:
        return build_openai_model(
            model_identifier=model_identifier,
            secret=secret,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            http_transport=http_transport,
        )

    return create
