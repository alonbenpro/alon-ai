"""Explicit live Idea composition using the shared L06 governed runtime.

Trusted startup injects a reviewed immutable configuration and a consumer-scoped
secret store. This module never accepts a raw key or grants provider rights.
"""

from __future__ import annotations

import json
import os
import stat
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.integrations.schemas.provider import (
    CallAttribution,
    Capability,
    ContentField,
    Provider,
    Purpose,
    StrictDTO,
)
from alon_ai.policies.provider_rights import IntendedUse
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    PriceBound,
    Reason,
)
from alon_ai.security.secrets import EncryptedFileSecretStore

if TYPE_CHECKING:
    from alon_ai.services.ideas import IdeaRuntime


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
    reasoning_effort: Literal[
        "none", "minimal", "low", "medium", "high", "xhigh", "max"
    ]
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
