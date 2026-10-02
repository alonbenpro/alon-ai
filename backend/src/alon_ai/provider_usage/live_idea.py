"""Live Idea provider authority, budgets, and governed runtime construction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, SecretStr
from pydantic_ai.usage import UsageLimits
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.agents.idea_discovery import IdeaStage, idea_profile
from alon_ai.agents.schemas.openai import RoutingPolicy
from alon_ai.db.repositories.accounting import (
    GovernanceProvisioner,
    GovernanceRepository,
)
from alon_ai.db.repositories.agent_run_steps import AgentRunStepRepository
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.openai_live import (
    _ensure_exact_config,
    _require_same_operation_budget,
)
from alon_ai.db.repositories.openai_run import OpenAIRunStore
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.integrations.live_idea import (
    LiveIdeaRuntimeConfig,
    LiveIdeaRuntimeProvider,
)
from alon_ai.integrations.openai import ResponsesTransport, SDKResponsesTransport
from alon_ai.integrations.schemas.provider import (
    AgentActor,
    CallAttribution,
    OperationRunKind,
    Provider,
    StrictDTO,
)
from alon_ai.provider_usage.pydantic_model import (
    DispatchGuard,
    GovernedPydanticModel,
    ModelFactory,
    ModelStepCheckpoint,
)
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    CapabilityConfig,
    Reason,
)
from alon_ai.security.secrets import SecretStore
from alon_ai.services.agent_runs import OpenAIRuntime

if TYPE_CHECKING:
    from alon_ai.services.ideas import IdeaRuntime


def _id(run_id: UUID, label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"alon-ai-l07-live/{run_id}/{label}")


async def _provision_live_scope(
    engine: AsyncEngine,
    config: LiveIdeaRuntimeConfig,
    secrets: SecretStore,
    *,
    experiment_id: UUID,
    workflow_id: UUID,
    agent_id: UUID,
    operator_id: UUID,
    run_id: UUID,
    budget_usd: Decimal,
    run_timeout_seconds: int,
    namespace: str,
    admitted_at: datetime | None = None,
) -> tuple[GovernanceRepository, CapabilityConfig, CallAttribution]:
    """Reuse reviewed rights, immutable price bounds, scope and currency budgets."""

    def identity(label: str) -> UUID:
        return _id(run_id, f"{namespace}{label}")

    now = datetime.now(UTC)
    scope_started_at = admitted_at if admitted_at is not None else now
    if operator_id != config.approved_by or not (
        config.effective_at <= now < config.expires_at
    ):
        raise AccountingDenied(Reason.CONFIG)
    if (
        type(budget_usd) is not Decimal
        or not budget_usd.is_finite()
        or budget_usd <= 0
        or budget_usd > config.budget_cap_usd
    ):
        raise AccountingDenied(Reason.BUDGET)
    try:
        resolved: SecretStr = secrets.get(config.secret_handle)
        if not isinstance(resolved, SecretStr) or not resolved.get_secret_value():
            raise ValueError("secret unavailable")
    except Exception:  # noqa: BLE001 - never disclose secret-store details
        raise AccountingDenied(Reason.SECRET) from None

    config_version = identity("version")
    attribution = CallAttribution(
        experiment_id=experiment_id,
        workflow_run_id=workflow_id,
        operation_run_id=identity("operation"),
        operation_run_kind=OperationRunKind.SYSTEM,
        actor=AgentActor(agent_run_id=agent_id),
        correlation_id=identity("correlation"),
        logical_operation_id=identity("logical"),
        config_version=config_version,
        deadline=min(
            scope_started_at + timedelta(seconds=run_timeout_seconds), config.expires_at
        ),
    )
    provisioner = GovernanceProvisioner(engine)
    await provisioner.scope(attribution)
    await _require_same_operation_budget(
        engine,
        attribution.operation_run_id,
        budget_usd,
        budget_usd * config.fx_rate,
    )
    capability_config = CapabilityConfig(
        id=identity("config"),
        version=config_version,
        workflow_id=workflow_id,
        intended_use=config.intended_use,
        prices=config.prices,
        fx_id=config.fx_id,
        requested_count=1,
        secret_handle=config.secret_handle,
        adapter_version=identity("adapter"),
        model_identifier=config.model_identifier,
    )
    await _ensure_exact_config(engine, capability_config)
    await provisioner.budgets(
        attribution,
        provider=Provider.OPENAI,
        currencies=("USD",),
        limit=budget_usd,
        effective_at=scope_started_at,
        expires_at=config.expires_at,
    )
    await provisioner.budgets(
        attribution,
        provider=Provider.OPENAI,
        currencies=("ILS",),
        limit=budget_usd * config.fx_rate,
        effective_at=scope_started_at,
        expires_at=config.expires_at,
    )
    repository = GovernanceRepository(engine)
    return repository, capability_config, attribution


def build_live_idea_runtime_provider(
    config: LiveIdeaRuntimeConfig,
    secrets: SecretStore,
    *,
    transport: ResponsesTransport | None = None,
) -> LiveIdeaRuntimeProvider:
    """Bind explicit operator policy and secret authority to a route callable."""

    legacy_reasoning_effort = config.reasoning_effort
    if legacy_reasoning_effort == "max":
        raise AccountingDenied(Reason.CONFIG)

    selected_transport = transport if transport is not None else SDKResponsesTransport()

    async def provision_live_seeded_runtime(
        engine: AsyncEngine,
        *,
        experiment_id: UUID,
        workflow_id: UUID,
        agent_id: UUID,
        operator_id: UUID,
        run_id: UUID,
        budget_usd: Decimal,
    ) -> tuple[IdeaRuntime, CallAttribution, str]:
        repository, capability_config, attribution = await _provision_live_scope(
            engine,
            config,
            secrets,
            experiment_id=experiment_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            operator_id=operator_id,
            run_id=run_id,
            budget_usd=budget_usd,
            run_timeout_seconds=config.timeout_seconds + 30,
            namespace="",
        )
        config_version = attribution.config_version
        runtimes = {}
        for stage in IdeaStage:
            profile = idea_profile(
                stage,
                config_id=capability_config.id,
                config_version=config_version,
                adapter_version=capability_config.adapter_version,
                model_identifier=config.model_identifier,
                reasoning_effort=legacy_reasoning_effort,
                max_output_tokens=config.max_output_tokens,
                timeout_seconds=config.timeout_seconds,
            )
            runtimes[stage] = OpenAIRuntime(
                repository,
                OpenAIRunStore(engine),
                routes=RoutingPolicy(
                    cheap=capability_config.id,
                    stronger=_id(run_id, "unprovisioned-stronger"),
                    premium=_id(run_id, "unprovisioned-premium"),
                ),
                profiles={capability_config.id: profile},
                transport=selected_transport,
                secrets=secrets,
            )
        from alon_ai.services.ideas import IdeaRuntime

        return (
            IdeaRuntime(ProductRecordsRepository(engine), runtimes),
            attribution,
            "OPENAI",
        )

    return provision_live_seeded_runtime


class CombinedModelLimits(StrictDTO):
    """Required operator policy for the entire loop, separate from request caps."""

    model_request_limit: int = Field(gt=0)
    input_tokens_limit: int = Field(gt=0)
    output_tokens_limit: int = Field(gt=0)
    total_tokens_limit: int = Field(gt=0)
    run_timeout_seconds: int = Field(gt=0, le=86400)


@dataclass(frozen=True)
class ProvisionedCombinedModel:
    """Runtime-only composition. Pass usage limits and timeout to the agent loop."""

    model: GovernedPydanticModel = field(repr=False)
    attribution: CallAttribution
    usage_limits: UsageLimits
    run_timeout_seconds: int
    source: Literal["OPENAI"] = "OPENAI"

    def __reduce_ex__(self, protocol: object):
        raise TypeError("provisioned runtime model cannot be serialized")


class LiveCombinedModelProvider(Protocol):
    async def __call__(
        self,
        engine: AsyncEngine,
        *,
        experiment_id: UUID,
        workflow_id: UUID,
        agent_id: UUID,
        operator_id: UUID,
        run_id: UUID,
        budget_usd: Decimal,
        dispatch_guard: DispatchGuard,
    ) -> ProvisionedCombinedModel: ...


def build_live_combined_model_provider(
    config: LiveIdeaRuntimeConfig,
    secrets: SecretStore,
    *,
    limits: CombinedModelLimits,
    model_factory: ModelFactory | None = None,
) -> LiveCombinedModelProvider:
    """Provision native multi-request generation from explicit trusted policy.

    The service must pass the returned UsageLimits into its Pydantic AI run and
    enforce the returned wall-clock ceiling around that run. Each actual model
    request independently rechecks ledger rights, prices, budget and deadline.
    The required guard binds current pinned-input authority to final dispatch.
    """
    if not isinstance(limits, CombinedModelLimits):
        raise AccountingDenied(Reason.CONFIG)

    async def provision(
        engine: AsyncEngine,
        *,
        experiment_id: UUID,
        workflow_id: UUID,
        agent_id: UUID,
        operator_id: UUID,
        run_id: UUID,
        budget_usd: Decimal,
        dispatch_guard: DispatchGuard,
    ) -> ProvisionedCombinedModel:
        if not callable(dispatch_guard):
            raise AccountingDenied(Reason.CONFIG)
        parent = await AgentRunRepository(engine).get(run_id)
        if (
            parent is None
            or parent["experiment_id"] != experiment_id
            or parent["operator_id"] != operator_id
            or parent["status"] != "RUNNING"
            or parent["started_at"] is None
        ):
            raise AccountingDenied(Reason.SCOPE)
        repository, capability_config, attribution = await _provision_live_scope(
            engine,
            config,
            secrets,
            experiment_id=experiment_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            operator_id=operator_id,
            run_id=run_id,
            budget_usd=budget_usd,
            run_timeout_seconds=limits.run_timeout_seconds,
            namespace="combined/",
            admitted_at=parent["started_at"],
        )
        # The same immutable versions price both the reservation and the native
        # usage observations; provisioning never accepts independent cost values.
        immutable_config, prices = await repository.generation_config_and_prices(
            capability_config.id
        )
        model = GovernedPydanticModel(
            repository=repository,
            attribution=attribution,
            config=immutable_config,
            prices=prices,
            secrets=secrets,
            run_key=_id(run_id, "combined/model"),
            max_output_tokens=config.max_output_tokens,
            dispatch_guard=dispatch_guard,
            model_factory=model_factory,
            reasoning_effort=config.reasoning_effort,
            timeout_seconds=config.timeout_seconds,
            step_checkpoint=ModelStepCheckpoint(AgentRunStepRepository(engine), run_id),
        )
        return ProvisionedCombinedModel(
            model=model,
            attribution=attribution,
            usage_limits=UsageLimits(
                request_limit=limits.model_request_limit,
                input_tokens_limit=limits.input_tokens_limit,
                output_tokens_limit=limits.output_tokens_limit,
                total_tokens_limit=limits.total_tokens_limit,
            ),
            run_timeout_seconds=limits.run_timeout_seconds,
        )

    return provision
