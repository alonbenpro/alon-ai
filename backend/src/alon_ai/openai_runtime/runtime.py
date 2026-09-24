"""Application-owned OpenAI execution through the existing governed read path."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, Decimal, localcontext
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import SecretStr

from alon_ai.accounting.models import (
    CallReceipt,
    CallState,
    CapabilityConfig,
    PriceVersion,
)
from alon_ai.accounting.repository import GovernanceRepository
from alon_ai.openai_runtime.contract import (
    OpenAIProfile,
    ParsedResponse,
    Route,
    RoutingFacts,
    RoutingPolicy,
    StrictDTO,
    canonical_json,
    classify_response,
    sha256,
)
from alon_ai.openai_runtime.store import (
    OpenAIRunConflict,
    OpenAIRunIntent,
    OpenAIRunOutcome,
    OpenAIRunStore,
)
from alon_ai.openai_runtime.transport import ResponsesTransport
from alon_ai.providers.contracts import (
    AgentActor,
    CallAttribution,
    Capability,
    CostKnowledge,
    ProviderCallResult,
    ProviderErrorCode,
    ProviderResultMetadata,
    Purpose,
    ResultStatus,
    SafeRequestMetadata,
    UsageComponent,
    UsageObservation,
)
from alon_ai.providers.execution import GovernedExecutor
from alon_ai.providers.rights import GrantEvent, ProviderUsageGrant, RuntimeContent
from alon_ai.security.secrets import SecretStore


@dataclass(frozen=True)
class AcceptedSource:
    """Current source grant is supplied by the trusted content repository."""

    evidence_ref: UUID
    content: RuntimeContent
    current_grant: ProviderUsageGrant
    events: tuple[GrantEvent, ...] = ()


@dataclass(frozen=True)
class OpenAIExecution:
    route: Route
    outcome: OpenAIRunOutcome
    receipt: CallReceipt | None
    output: StrictDTO | None = field(repr=False)

    def __reduce_ex__(self, protocol: object):
        raise TypeError("advisory runtime output cannot be serialized")


def _priced_usage(
    parsed: ParsedResponse, prices: tuple[PriceVersion, ...], key: UUID
) -> tuple[UsageObservation, ...]:
    observations = []
    for price in prices:
        component = price.component
        counts = parsed.usage
        quantity: Decimal | None
        if component is UsageComponent.REQUEST:
            quantity = Decimal(1)
        elif counts is None:
            quantity = None
        elif component is UsageComponent.INPUT_TOKEN:
            # When a separate cached-token price exists, input is the uncached
            # remainder. Otherwise this one price covers every input token.
            has_cached_price = any(
                p.component is UsageComponent.CACHED_TOKEN for p in prices
            )
            quantity = (
                Decimal(
                    counts["input_tokens"]
                    - (counts["cached_tokens"] if has_cached_price else 0)
                )
                if not has_cached_price or "cached_tokens" in counts
                else None
            )
        elif component is UsageComponent.OUTPUT_TOKEN:
            quantity = Decimal(counts["output_tokens"])
        elif component is UsageComponent.CACHED_TOKEN:
            quantity = (
                Decimal(counts["cached_tokens"]) if "cached_tokens" in counts else None
            )
        else:
            quantity = None
        with localcontext() as ctx:
            ctx.prec = 64
            cost = (
                (quantity * price.unit_price / price.unit_quantity).quantize(
                    Decimal("1e-12"), rounding=ROUND_CEILING
                )
                if quantity is not None
                else None
            )
        observations.append(
            UsageObservation(
                component=component,
                quantity=quantity,
                currency=price.currency,
                cost=cost,
                knowledge=CostKnowledge.FINAL
                if quantity is not None
                else CostKnowledge.UNAVAILABLE,
                observation_key=uuid5(key, component.value),
            )
        )
    return tuple(observations)


def _verify_pricing_bounds(
    config: CapabilityConfig,
    prices: tuple[PriceVersion, ...],
    profile: OpenAIProfile,
    input_json: str,
) -> None:
    priced = {price.component: price for price in prices}
    allowed = {
        UsageComponent.REQUEST,
        UsageComponent.INPUT_TOKEN,
        UsageComponent.OUTPUT_TOKEN,
        UsageComponent.CACHED_TOKEN,
    }
    if (
        not {UsageComponent.INPUT_TOKEN, UsageComponent.OUTPUT_TOKEN} <= priced.keys()
        or not priced.keys() <= allowed
    ):
        raise PermissionError("configured OpenAI token prices are incomplete")
    bounds = {
        price.component: next(
            bound.max_quantity for bound in config.prices if bound.price_id == price.id
        )
        for price in prices
    }
    # Byte count plus protocol headroom is a conservative token ceiling for
    # supplied text, instructions and schema. The output bound is explicit.
    input_ceiling = Decimal(
        len((input_json + profile.instructions + profile.schema_json).encode("utf-8"))
        + 1024
    )
    if (
        bounds[UsageComponent.INPUT_TOKEN] < input_ceiling
        or bounds[UsageComponent.OUTPUT_TOKEN] < profile.max_output_tokens
        or (
            UsageComponent.CACHED_TOKEN in bounds
            and bounds[UsageComponent.CACHED_TOKEN] < input_ceiling
        )
    ):
        raise PermissionError("configured OpenAI token reservation is insufficient")


class _ConfiguredResponsesAdapter:
    def __init__(
        self,
        *,
        profile: OpenAIProfile,
        input_json: str,
        client_request_id: UUID,
        key: UUID,
        prices: tuple[PriceVersion, ...],
        transport: ResponsesTransport,
        clock,
    ):
        self.profile = profile
        self.input_json = input_json
        self.client_request_id = client_request_id
        self.key = key
        self.prices = prices
        self.transport = transport
        self.clock = clock
        self.parsed: ParsedResponse | None = None

    async def invoke(
        self, config: CapabilityConfig, secret: SecretStr | None, /
    ) -> ProviderCallResult[RuntimeContent]:
        if (
            config.id != self.profile.config_id
            or config.version != self.profile.config_version
            or config.adapter_version != self.profile.adapter_version
            or config.model_identifier != self.profile.model_identifier
            or config.intended_use.capability is not Capability.OPENAI_GENERATE
            or config.intended_use.purpose is not Purpose.GENERATION
            or secret is None
        ):
            raise ValueError("configured OpenAI capability mismatch")
        started = self.clock()
        response = await self.transport.create(
            profile=self.profile,
            input_json=self.input_json,
            secret=secret,
            client_request_id=self.client_request_id,
            timeout_seconds=self.profile.timeout_seconds,
        )
        finished = self.clock()
        parsed = classify_response(response, self.profile)
        self.parsed = parsed
        status, error = {
            "SUCCEEDED": (ResultStatus.SUCCEEDED, None),
            "REFUSED": (ResultStatus.REFUSED, ProviderErrorCode.REFUSED),
            "SCHEMA_MISMATCH": (
                ResultStatus.FAILED,
                ProviderErrorCode.MALFORMED_RESPONSE,
            ),
            "INCOMPLETE": (ResultStatus.FAILED, ProviderErrorCode.UNAVAILABLE),
            "FAILED": (ResultStatus.FAILED, ProviderErrorCode.UNAVAILABLE),
            "CANCELLED": (ResultStatus.FAILED, ProviderErrorCode.UNAVAILABLE),
            "UNCERTAIN": (ResultStatus.UNKNOWN, ProviderErrorCode.UNAVAILABLE),
        }[parsed.outcome]
        return ProviderCallResult(
            ProviderResultMetadata(
                capability=Capability.OPENAI_GENERATE,
                external_request_id=parsed.external_request_id,
                started_at=started,
                finished_at=finished,
                status=status,
                error_code=error,
                usage=_priced_usage(parsed, self.prices, self.key),
            ),
            None,
        )


class OpenAIRuntime:
    def __init__(
        self,
        repository: GovernanceRepository,
        store: OpenAIRunStore,
        *,
        routes: RoutingPolicy,
        profiles: Mapping[UUID, OpenAIProfile],
        transport: ResponsesTransport,
        secrets: SecretStore,
    ):
        self.repository = repository
        self.store = store
        self.routes = routes
        self.profiles = MappingProxyType(dict(profiles))
        self.transport = transport
        self.secrets = secrets

    async def run(
        self,
        attribution: CallAttribution,
        *,
        facts: RoutingFacts,
        sources: tuple[AcceptedSource, ...],
        idempotency_key: UUID,
    ) -> OpenAIExecution:
        now = self.repository.clock()
        selection = self.routes.select(facts, scope=attribution.experiment_id, now=now)
        if selection.route is Route.NO_AI:
            return OpenAIExecution(Route.NO_AI, OpenAIRunOutcome.NO_AI, None, None)
        assert selection.config_id is not None
        profile = self.profiles[selection.config_id]
        config, prices = await self.repository.generation_config_and_prices(
            profile.config_id
        )
        if (
            config.version != profile.config_version
            or config.adapter_version != profile.adapter_version
            or config.model_identifier != profile.model_identifier
            or config.intended_use.capability is not Capability.OPENAI_GENERATE
            or config.intended_use.purpose is not Purpose.GENERATION
            or config.requested_count != 1
            or config.secret_handle is None
            or attribution.config_version != config.version
        ):
            raise PermissionError(
                "OpenAI run profile does not match immutable capability"
            )
        if not sources:
            raise PermissionError("licensed source content required")
        scoped = []
        for source in sources:
            if source.current_grant.purpose is not Purpose.GENERATION:
                raise PermissionError(
                    "source grant does not authorize model generation"
                )
            retained = source.content.retain(
                current_grant=source.current_grant, events=source.events, now=now
            )
            scoped.append(
                {
                    "ref": str(source.evidence_ref),
                    "grant": str(retained.grant_id),
                    "fields": {
                        key.value: list(value)
                        for key, value in sorted(retained.fields.items())
                    },
                }
            )
        input_json = canonical_json({"sources": scoped})
        _verify_pricing_bounds(config, prices, profile, input_json)
        previous = await self.store.get(idempotency_key)
        intent = OpenAIRunIntent(
            idempotency_key=idempotency_key,
            config_id=config.id,
            config_version=config.version,
            experiment_id=attribution.experiment_id,
            workflow_id=attribution.workflow_run_id,
            operation_id=attribution.operation_run_id,
            agent_run_id=attribution.actor.agent_run_id
            if isinstance(attribution.actor, AgentActor)
            else None,
            prompt_version=profile.prompt_version,
            prompt_hash=sha256(profile.instructions),
            schema_version=profile.schema_version,
            output_schema_hash=sha256(profile.schema_json),
            model_identifier=profile.model_identifier,
            reasoning_effort=profile.reasoning_effort,
            accepted_input_refs=tuple(source.evidence_ref for source in sources),
            input_hash=sha256(input_json),
            client_request_id=uuid5(NAMESPACE_URL, str(idempotency_key)),
            created_at=previous.created_at if previous else now,
        )
        try:
            record = await self.store.begin(intent)
        except OpenAIRunConflict:
            # Concurrent first use may race only on created_at. The store still
            # compares every identity field and will reject altered inputs.
            latest = await self.store.get(idempotency_key)
            if latest is None:
                raise
            record = await self.store.begin(
                intent.model_copy(update={"created_at": latest.created_at})
            )
        if record.outcome is not OpenAIRunOutcome.READY:
            return OpenAIExecution(
                selection.route,
                record.outcome,
                await self.repository.get(record.call_id) if record.call_id else None,
                None,
            )
        adapter = _ConfiguredResponsesAdapter(
            profile=profile,
            input_json=input_json,
            client_request_id=intent.client_request_id,
            key=idempotency_key,
            prices=prices,
            transport=self.transport,
            clock=self.repository.clock,
        )
        executor = GovernedExecutor(
            self.repository,
            adapters={profile.adapter_version: adapter},
            secrets=self.secrets,
        )
        try:
            result = await executor.execute(
                attribution,
                SafeRequestMetadata(config_ref=config.id),
                idempotency_key=idempotency_key,
            )
        except asyncio.CancelledError:
            interrupted = await self.repository.receipt_for_idempotency_key(
                idempotency_key
            )
            await asyncio.shield(
                self.store.finish(
                    idempotency_key,
                    interrupted.call_id if interrupted else None,
                    OpenAIRunOutcome.CANCELLED,
                    None,
                )
            )
            raise
        except Exception:
            interrupted = await self.repository.receipt_for_idempotency_key(
                idempotency_key
            )
            outcome = (
                OpenAIRunOutcome.UNCERTAIN
                if interrupted is not None
                and interrupted.state not in {CallState.RESERVED, CallState.RELEASED}
                else OpenAIRunOutcome.FAILED
            )
            await self.store.finish(
                idempotency_key,
                interrupted.call_id if interrupted else None,
                outcome,
                None,
            )
            raise
        if adapter.parsed is None:
            if result.error is None and result.receipt.state is not CallState.RELEASED:
                # Another caller owns this idempotency key's dispatch. It may
                # still be processing; only its adapter can close this run.
                return OpenAIExecution(
                    selection.route, OpenAIRunOutcome.UNCERTAIN, result.receipt, None
                )
            outcome = (
                OpenAIRunOutcome.TIMEOUT
                if result.error is ProviderErrorCode.TIMEOUT
                else OpenAIRunOutcome.FAILED
                if result.receipt.state is CallState.RELEASED
                else OpenAIRunOutcome.UNCERTAIN
            )
            output = None
            output_hash = None
        else:
            outcome = OpenAIRunOutcome(adapter.parsed.outcome)
            output = (
                adapter.parsed.output
                if result.receipt.state is CallState.FINAL
                else None
            )
            output_hash = adapter.parsed.output_hash
        await self.store.finish(
            idempotency_key, result.receipt.call_id, outcome, output_hash
        )
        return OpenAIExecution(selection.route, outcome, result.receipt, output)
