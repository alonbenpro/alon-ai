"""One native Pydantic AI request per governed reservation and dispatch.

The factory and dispatch guard are trusted composition, never agent tools. The
guard must revalidate pinned inputs, current rights and cancellation under locks,
and hold those locks across the request. Model messages remain process-local.
Only the ordinary non-streaming request path is supported; inherited Model
methods fail closed for streaming, token counting and provider compaction.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from copy import deepcopy
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal, localcontext
from typing import Literal
from uuid import UUID, uuid5

from pydantic import SecretStr, TypeAdapter
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
)
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from pydantic_ai.profiles.openai import openai_model_profile
from pydantic_ai.settings import ModelSettings

from alon_ai.agents.schemas.openai import canonical_json, sha256
from alon_ai.db.repositories.accounting import GovernanceRepository
from alon_ai.db.repositories.agent_run_steps import AgentRunStepRepository
from alon_ai.integrations.pydantic_openai import openai_model_factory
from alon_ai.integrations.schemas.provider import (
    CallAttribution,
    Capability,
    CostKnowledge,
    ProviderCallResult,
    ProviderErrorCode,
    ProviderFailure,
    ProviderResultMetadata,
    Purpose,
    ResultStatus,
    SafeRequestMetadata,
    UsageComponent,
    UsageObservation,
)
from alon_ai.policies.provider_rights import RuntimeContent
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    CallReceipt,
    CallState,
    CapabilityConfig,
    PriceVersion,
    Reason,
)
from alon_ai.provider_usage.service import ExecutionResult, GovernedExecutor
from alon_ai.security.secrets import SecretStore

ModelFactory = Callable[[SecretStr], Model]
DispatchGuard = Callable[[], AbstractAsyncContextManager[None]]
_PARAMETERS = TypeAdapter(ModelRequestParameters)
_COMPONENTS = {
    UsageComponent.INPUT_TOKEN,
    UsageComponent.OUTPUT_TOKEN,
    UsageComponent.CACHED_TOKEN,
    UsageComponent.REQUEST,
}


@dataclass(frozen=True)
class ModelStepCheckpoint:
    """Durable admission identity supplied only by trusted combined composition."""

    repository: AgentRunStepRepository
    run_id: UUID


def _request_hash(
    messages: list[ModelMessage], parameters: ModelRequestParameters
) -> str:
    serialized = ModelMessagesTypeAdapter.dump_python(messages, mode="json")
    # Pydantic timestamps identify local construction, not model request content.
    # Remove only known message/part timestamps; tool content stays untouched.
    for message in serialized:
        message.pop("timestamp", None)
        for part in message["parts"]:
            part.pop("timestamp", None)
    return sha256(
        canonical_json(
            {
                "messages": serialized,
                "parameters": _PARAMETERS.dump_python(parameters, mode="json"),
            }
        )
    )


def _usage(
    response: ModelResponse | None,
    prices: tuple[PriceVersion, ...],
    key: UUID,
    *,
    not_dispatched: bool = False,
) -> tuple[UsageObservation, ...]:
    # RequestUsage exposes default zeros even when no provider usage exists.
    # Only explicitly observed fields establish known quantities.
    raw = vars(response.usage) if response is not None else {}
    input_tokens = raw.get("input_tokens")
    output_tokens = raw.get("output_tokens")
    cached = raw.get("cache_read_tokens")
    valid = (
        type(input_tokens) is int
        and input_tokens >= 0
        and type(output_tokens) is int
        and output_tokens >= 0
        and (cached is None or type(cached) is int and 0 <= cached <= input_tokens)
    )
    observations = []
    has_cached = any(p.component is UsageComponent.CACHED_TOKEN for p in prices)
    for price in prices:
        quantity = None
        if not_dispatched:
            quantity = Decimal(0)
        elif price.component is UsageComponent.REQUEST:
            quantity = Decimal(1)
        elif valid:
            assert isinstance(input_tokens, int) and isinstance(output_tokens, int)
            if price.component is UsageComponent.INPUT_TOKEN:
                if not has_cached:
                    quantity = Decimal(input_tokens)
                elif cached is not None:
                    quantity = Decimal(input_tokens - cached)
            elif price.component is UsageComponent.OUTPUT_TOKEN:
                quantity = Decimal(output_tokens)
            elif price.component is UsageComponent.CACHED_TOKEN and cached is not None:
                quantity = Decimal(cached)
        with localcontext() as context:
            context.prec = 64
            cost = (
                (quantity * price.unit_price / price.unit_quantity).quantize(
                    Decimal("1e-12"),
                    rounding=ROUND_CEILING,
                )
                if quantity is not None
                else None
            )
        observations.append(
            UsageObservation(
                component=price.component,
                quantity=quantity,
                currency=price.currency,
                cost=cost,
                knowledge=CostKnowledge.FINAL
                if cost is not None
                else CostKnowledge.UNAVAILABLE,
                observation_key=uuid5(key, price.component.value),
            )
        )
    return tuple(observations)


class _RequestAdapter:
    def __init__(
        self,
        owner: GovernedPydanticModel,
        messages: list[ModelMessage],
        parameters: ModelRequestParameters,
        key: UUID,
    ) -> None:
        self.owner, self.messages, self.parameters, self.key = (
            owner,
            messages,
            parameters,
            key,
        )
        self.response: ModelResponse | None = None

    async def invoke(
        self,
        config: CapabilityConfig,
        secret: SecretStr | None,
        /,
    ) -> ProviderCallResult[RuntimeContent]:
        owner = self.owner
        if config != owner._config or secret is None or not secret.get_secret_value():
            raise ValueError("configured native model mismatch")
        started = owner._repository.clock()
        if owner._step_checkpoint is not None:
            receipt = await owner._repository.receipt_for_idempotency_key(self.key)
            if receipt is None:
                raise AccountingDenied(Reason.STATE)
            await owner._bind_step(self.key, receipt)
        entered = False
        try:
            async with owner._dispatch_guard():
                entered = True
                async with owner._model_factory(secret) as model:
                    self.response = await model.request(
                        self.messages,
                        owner._request_settings.copy(),
                        self.parameters,
                    )
        except PermissionError:
            if entered:
                # A provider or guard-exit failure cannot prove no dispatch.
                raise
            return ProviderCallResult(
                ProviderResultMetadata(
                    capability=Capability.OPENAI_GENERATE,
                    started_at=started,
                    finished_at=owner._repository.clock(),
                    status=ResultStatus.FAILED,
                    error_code=ProviderErrorCode.DENIED,
                    usage=_usage(None, owner._prices, self.key, not_dispatched=True),
                ),
                None,
            )
        response = self.response
        assert response is not None
        observations = _usage(response, owner._prices, self.key)
        status, error = ResultStatus.SUCCEEDED, None
        if (
            any(item.knowledge is CostKnowledge.UNAVAILABLE for item in observations)
            or response.state != "complete"
        ):
            status, error = ResultStatus.UNKNOWN, ProviderErrorCode.UNAVAILABLE
        elif response.finish_reason == "content_filter":
            status, error = ResultStatus.REFUSED, ProviderErrorCode.REFUSED
        elif response.finish_reason in {"length", "error"}:
            status, error = ResultStatus.FAILED, ProviderErrorCode.INCOMPLETE_RESULT
        response_id = response.provider_response_id
        if (
            response_id is not None
            and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", response_id) is None
        ):
            response_id = None
        return ProviderCallResult(
            ProviderResultMetadata(
                capability=Capability.OPENAI_GENERATE,
                external_request_id=response_id,
                started_at=started,
                finished_at=owner._repository.clock(),
                status=status,
                error_code=error,
                usage=observations,
            ),
            None,
        )


class GovernedPydanticModel(Model):
    """A run-scoped text model; each turn reserves its full configured ceiling.

    Recreating with the same ``run_key`` fences replay at each ordinal. Completed
    receipts do not imply the original transient response is replayable. A new
    authorized attempt needs a new run key. Factories may not retry or fall back.
    """

    def __init__(
        self,
        *,
        repository: GovernanceRepository,
        attribution: CallAttribution,
        config: CapabilityConfig,
        prices: tuple[PriceVersion, ...],
        secrets: SecretStore,
        run_key: UUID,
        max_output_tokens: int,
        dispatch_guard: DispatchGuard,
        model_factory: ModelFactory | None = None,
        reasoning_effort: Literal[
            "none", "minimal", "low", "medium", "high", "xhigh", "max"
        ] = "low",
        timeout_seconds: int = 60,
        step_checkpoint: ModelStepCheckpoint | None = None,
    ) -> None:
        if (
            config.model_identifier is None
            or config.secret_handle is None
            or config.intended_use.capability is not Capability.OPENAI_GENERATE
            or config.intended_use.purpose is not Purpose.GENERATION
            or config.requested_count != 1
            or config.version != attribution.config_version
            or config.workflow_id != attribution.workflow_run_id
            or not 1 <= max_output_tokens <= 32768
            or not 1 <= timeout_seconds <= 3600
            or reasoning_effort
            not in {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
        ):
            raise AccountingDenied(Reason.CONFIG)
        components = {price.component for price in prices}
        if (
            not {UsageComponent.INPUT_TOKEN, UsageComponent.OUTPUT_TOKEN} <= components
            or not components <= _COMPONENTS
            or len(components) != len(prices)
            or {p.id for p in prices} != {b.price_id for b in config.prices}
            or len(config.prices) != len(prices)
            or any(
                p.model_identifier != config.model_identifier
                or p.capability is not Capability.OPENAI_GENERATE
                for p in prices
            )
        ):
            raise AccountingDenied(Reason.PRICE)
        super().__init__(profile=openai_model_profile(config.model_identifier))
        self._repository, self._attribution, self._config = (
            repository,
            attribution,
            config,
        )
        self._prices, self._secrets, self._run_key = prices, secrets, run_key
        self._model_factory = model_factory or openai_model_factory(
            config.model_identifier
        )
        self._dispatch_guard = dispatch_guard
        self._step_checkpoint = step_checkpoint
        self._max_output_tokens = max_output_tokens
        self._request_settings: OpenAIResponsesModelSettings = {
            "max_tokens": max_output_tokens,
            "timeout": timeout_seconds,
            "openai_reasoning_effort": reasoning_effort,
            "openai_store": False,
            "openai_background": False,
        }
        self._ordinal = 0
        self._receipts: list[CallReceipt] = []

    @property
    def model_name(self) -> str:
        assert self._config.model_identifier is not None
        return self._config.model_identifier

    @property
    def system(self) -> str:
        return "openai"

    @property
    def receipts(self) -> tuple[CallReceipt, ...]:
        return tuple(self._receipts)

    async def _claim_step(
        self,
        key: UUID,
        messages: list[ModelMessage],
        parameters: ModelRequestParameters,
    ) -> None:
        checkpoint = self._step_checkpoint
        if checkpoint is None:
            return
        _row, created = await checkpoint.repository.claim_once(
            run_id=checkpoint.run_id,
            experiment_id=self._attribution.experiment_id,
            step_key=key,
            ordinal=self._ordinal,
            kind="MODEL_REQUEST",
            request_ref=checkpoint.run_id,
            request_version=1,
            request_hash=_request_hash(messages, parameters),
            config_ref=self._config.id,
            config_version=self._config.schema_version,
            config_hash=sha256(
                canonical_json(
                    {
                        "capability": self._config.model_dump(mode="json"),
                        "settings": self._request_settings,
                    }
                )
            ),
        )
        if not created:
            # No checkpoint contains replayable model text or tool instructions.
            # A crashed or concurrent owner retains its original step and ledger.
            receipt = await self._repository.receipt_for_idempotency_key(key)
            if receipt is not None:
                self._receipts.append(receipt)
            raise ProviderFailure(ProviderErrorCode.UNAVAILABLE)

    async def _bind_step(self, key: UUID, receipt: CallReceipt) -> None:
        checkpoint = self._step_checkpoint
        if checkpoint is not None:
            await checkpoint.repository.bind(
                checkpoint.run_id,
                key,
                operation_id=self._attribution.operation_run_id,
                operation_workflow_id=self._attribution.workflow_run_id,
                provider_call_id=receipt.call_id,
            )

    async def _checkpoint_result(
        self,
        key: UUID,
        result: ExecutionResult | None,
        response: ModelResponse | None,
        failure_reason: str,
    ) -> None:
        receipt = await self._repository.receipt_for_idempotency_key(key)
        if receipt is not None:
            self._receipts.append(receipt)
        checkpoint = self._step_checkpoint
        if checkpoint is None:
            return
        if receipt is not None:
            await self._bind_step(key, receipt)
        if (
            result is not None
            and result.error is None
            and response is not None
            and receipt is not None
            and receipt.state is CallState.FINAL
        ):
            status, reason = "SUCCEEDED", None
        elif receipt is not None and (
            receipt.state not in {CallState.FINAL, CallState.RELEASED} or result is None
        ):
            status, reason = "OUTCOME_UNKNOWN", "PROVIDER_OUTCOME_UNKNOWN"
        elif result is not None:
            status = "BLOCKED" if result.error is ProviderErrorCode.DENIED else "FAILED"
            reason = (
                result.error.value if result.error is not None else "RESULT_UNAVAILABLE"
            )
        else:
            status, reason = "BLOCKED", failure_reason
        await checkpoint.repository.finish(
            checkpoint.run_id,
            key,
            status=status,
            reason_code=reason,
        )

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        # Own the exact context that is bounded, hashed, claimed and dispatched.
        messages = deepcopy(messages)
        model_request_parameters = deepcopy(model_request_parameters)
        if (
            model_settings
            or model_request_parameters.native_tools
            or model_request_parameters.allow_image_output
        ):
            raise AccountingDenied(Reason.CONFIG)
        if any(
            isinstance(part, UserPromptPart) and not isinstance(part.content, str)
            for message in messages
            if isinstance(message, ModelRequest)
            for part in message.parts
        ):
            raise AccountingDenied(Reason.CONFIG)
        ceiling = Decimal(
            len(ModelMessagesTypeAdapter.dump_json(messages))
            + len(_PARAMETERS.dump_json(model_request_parameters))
            + 1024
        )
        bounds = {
            p.component: next(
                b.max_quantity for b in self._config.prices if b.price_id == p.id
            )
            for p in self._prices
        }
        if (
            bounds[UsageComponent.INPUT_TOKEN] < ceiling
            or bounds[UsageComponent.OUTPUT_TOKEN] < self._max_output_tokens
            or UsageComponent.CACHED_TOKEN in bounds
            and bounds[UsageComponent.CACHED_TOKEN] < ceiling
        ):
            raise AccountingDenied(Reason.PRICE)
        self._ordinal += 1
        key = uuid5(self._run_key, f"model-request/{self._ordinal}")
        await self._claim_step(key, messages, model_request_parameters)
        adapter = _RequestAdapter(self, messages, model_request_parameters, key)
        executor = GovernedExecutor(
            self._repository,
            adapters={self._config.adapter_version: adapter},
            secrets=self._secrets,
        )
        result = None
        failure_reason = "CALL_FAILED"
        try:
            result = await executor.execute(
                self._attribution.model_copy(update={"logical_operation_id": key}),
                SafeRequestMetadata(config_ref=self._config.id),
                idempotency_key=key,
            )
        except AccountingDenied as exc:
            failure_reason = exc.reason.value
            raise
        except asyncio.CancelledError:
            failure_reason = "CANCELLED"
            raise
        finally:
            await asyncio.shield(
                self._checkpoint_result(key, result, adapter.response, failure_reason)
            )
        assert result is not None
        if result.error is not None:
            raise ProviderFailure(result.error)
        if result.receipt.state is not CallState.FINAL or adapter.response is None:
            raise ProviderFailure(ProviderErrorCode.UNAVAILABLE)
        return adapter.response
