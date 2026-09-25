"""Explicit live Idea composition using the shared L06 governed runtime.

Trusted startup injects a reviewed immutable configuration and a consumer-scoped
secret store. This module never accepts a raw key or grants provider rights.
"""

from __future__ import annotations

import json
import os
import stat
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import AwareDatetime, Field, SecretStr, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting import schema as gov
from alon_ai.accounting.models import (
    AccountingDenied,
    CapabilityConfig,
    PriceBound,
    Reason,
)
from alon_ai.accounting.repository import (
    GovernanceProvisioner,
    GovernanceRepository,
    safe_errors,
)
from alon_ai.openai_runtime.contract import RoutingPolicy
from alon_ai.openai_runtime.idea import IdeaRuntime, IdeaStage, idea_profile
from alon_ai.openai_runtime.runtime import OpenAIRuntime
from alon_ai.openai_runtime.store import OpenAIRunStore
from alon_ai.openai_runtime.transport import ResponsesTransport, SDKResponsesTransport
from alon_ai.providers.contracts import (
    AgentActor,
    CallAttribution,
    Capability,
    ContentField,
    OperationRunKind,
    Provider,
    Purpose,
    StrictDTO,
)
from alon_ai.providers.rights import IntendedUse
from alon_ai.records import ProductRecordsRepository
from alon_ai.security.secrets import EncryptedFileSecretStore, SecretStore


def _id(run_id: UUID, label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"alon-ai-l07-live/{run_id}/{label}")


class LiveIdeaRuntimeProvider(Protocol):
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
    ) -> tuple[IdeaRuntime, CallAttribution, str]: ...


class LiveIdeaRuntimeConfig(StrictDTO):
    """An operator-approved reference to preprovisioned rights and prices."""

    approved_by: UUID
    effective_at: AwareDatetime
    expires_at: AwareDatetime
    intended_use: IntendedUse
    prices: tuple[PriceBound, ...] = Field(min_length=2, max_length=4)
    fx_id: UUID
    fx_rate: Decimal = Field(gt=0, allow_inf_nan=False)
    secret_handle: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    model_identifier: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"]
    max_output_tokens: int = Field(ge=1, le=32768)
    timeout_seconds: int = Field(ge=1, le=3600)
    budget_cap_usd: Decimal = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def limited_generation(self) -> LiveIdeaRuntimeConfig:
        use = self.intended_use
        if (
            self.effective_at >= self.expires_at
            or use.provider is not Provider.OPENAI
            or use.capability is not Capability.OPENAI_GENERATE
            or use.purpose is not Purpose.GENERATION
            or use.required_fields != frozenset({ContentField.TEXT})
            or len({bound.price_id for bound in self.prices}) != len(self.prices)
        ):
            raise ValueError("invalid live Idea authority configuration")
        return self


def load_live_idea_runtime_config(path: Path) -> LiveIdeaRuntimeConfig:
    """Read only an owner-private, regular JSON policy file; redact all errors."""

    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 65536
        ):
            raise ValueError("private file required")
        raw = path.read_text(encoding="utf-8")
        if not isinstance(json.loads(raw), dict):
            raise TypeError("object required")
        return LiveIdeaRuntimeConfig.model_validate_json(raw)
    except Exception:  # noqa: BLE001 - paths and values must remain private
        raise AccountingDenied(Reason.CONFIG) from None


def load_live_secret_store(
    data_dir: Path, *, allowed_handle: str
) -> EncryptedFileSecretStore:
    """Open only the container UID's private wrapping key and encrypted store."""

    try:
        key_path = data_dir / "live-secret.key"
        info = key_path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size != 32
        ):
            raise ValueError("private key file required")
        key = key_path.read_bytes()
        if len(key) != 32:
            raise ValueError("invalid wrapping key")
        return EncryptedFileSecretStore(
            data_dir / "secrets",
            consumer="openai-idea",
            allowed_handles={allowed_handle},
            keys={"v1": key},
            active_key_version="v1",
        )
    except Exception:  # noqa: BLE001 - key and path details must remain private
        raise AccountingDenied(Reason.SECRET) from None


@safe_errors
async def _ensure_exact_config(engine: AsyncEngine, config: CapabilityConfig) -> None:
    """A pre-claim retry may reuse only the same immutable config and price caps."""

    expected = {
        "id": config.id,
        "workflow_id": config.workflow_id,
        "version": config.version,
        "account": config.intended_use.account_handle,
        "capability": config.intended_use.capability,
        "fx_id": config.fx_id,
        "data": config.model_dump(mode="json"),
    }
    async with engine.begin() as connection:
        await connection.execute(
            pg_insert(gov.configs)
            .values(**expected)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        actual = (
            (
                await connection.execute(
                    select(gov.configs).where(gov.configs.c.id == config.id)
                )
            )
            .mappings()
            .one()
        )
        if any(actual[key] != value for key, value in expected.items()):
            raise AccountingDenied(Reason.CONFIG)
        for bound in config.prices:
            await connection.execute(
                pg_insert(gov.config_prices)
                .values(
                    config_id=config.id,
                    price_id=bound.price_id,
                    max_quantity=bound.max_quantity,
                )
                .on_conflict_do_nothing(index_elements=["config_id", "price_id"])
            )
        actual_bounds = (
            (
                await connection.execute(
                    select(
                        gov.config_prices.c.price_id,
                        gov.config_prices.c.max_quantity,
                    ).where(gov.config_prices.c.config_id == config.id)
                )
            )
            .mappings()
            .all()
        )
        if {row["price_id"]: row["max_quantity"] for row in actual_bounds} != {
            bound.price_id: bound.max_quantity for bound in config.prices
        }:
            raise AccountingDenied(Reason.CONFIG)


@safe_errors
async def _require_same_operation_budget(
    engine: AsyncEngine, operation_id: UUID, usd: Decimal, ils: Decimal
) -> None:
    async with engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    select(
                        gov.budget_accounts.c.currency,
                        gov.budget_accounts.c.limit,
                    ).where(
                        gov.budget_accounts.c.scope == "OPERATION",
                        gov.budget_accounts.c.operation_id == operation_id,
                    )
                )
            )
            .mappings()
            .all()
        )
    expected = {"USD": usd, "ILS": ils}
    if any(row["limit"] != expected.get(row["currency"]) for row in rows):
        raise AccountingDenied(Reason.BUDGET)


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
        return (
            IdeaRuntime(ProductRecordsRepository(engine), runtimes),
            attribution,
            "OPENAI",
        )

    return provision_live_seeded_runtime
