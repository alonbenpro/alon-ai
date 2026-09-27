"""Live Idea provider authority, budgets, and governed runtime construction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.agents.idea_discovery import IdeaStage, idea_profile
from alon_ai.agents.schemas.openai import RoutingPolicy
from alon_ai.db.repositories.accounting import (
    GovernanceProvisioner,
    GovernanceRepository,
)
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


def build_live_idea_runtime_provider(
    config: LiveIdeaRuntimeConfig,
    secrets: SecretStore,
    *,
    transport: ResponsesTransport | None = None,
) -> LiveIdeaRuntimeProvider:
    """Bind explicit operator policy and secret authority to a route callable."""

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
        now = datetime.now(UTC)
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

        config_version = _id(run_id, "version")
        attribution = CallAttribution(
            experiment_id=experiment_id,
            workflow_run_id=workflow_id,
            operation_run_id=_id(run_id, "operation"),
            operation_run_kind=OperationRunKind.SYSTEM,
            actor=AgentActor(agent_run_id=agent_id),
            correlation_id=_id(run_id, "correlation"),
            logical_operation_id=_id(run_id, "logical"),
            config_version=config_version,
            deadline=min(
                now + timedelta(seconds=config.timeout_seconds + 30), config.expires_at
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
            id=_id(run_id, "config"),
            version=config_version,
            workflow_id=workflow_id,
            intended_use=config.intended_use,
            prices=config.prices,
            fx_id=config.fx_id,
            requested_count=1,
            secret_handle=config.secret_handle,
            adapter_version=_id(run_id, "adapter"),
            model_identifier=config.model_identifier,
        )
        await _ensure_exact_config(engine, capability_config)
        await provisioner.budgets(
            attribution,
            provider=Provider.OPENAI,
            currencies=("USD",),
            limit=budget_usd,
            effective_at=now,
            expires_at=config.expires_at,
        )
        await provisioner.budgets(
            attribution,
            provider=Provider.OPENAI,
            currencies=("ILS",),
            limit=budget_usd * config.fx_rate,
            effective_at=now,
            expires_at=config.expires_at,
        )
        repository = GovernanceRepository(engine)
        runtimes = {}
        for stage in IdeaStage:
            profile = idea_profile(
                stage,
                config_id=capability_config.id,
                config_version=config_version,
                adapter_version=capability_config.adapter_version,
                model_identifier=config.model_identifier,
                reasoning_effort=config.reasoning_effort,
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
