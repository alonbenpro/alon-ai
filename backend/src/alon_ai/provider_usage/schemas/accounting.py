"""Exact, sanitized accounting contracts. No provider request/content payloads."""

from datetime import datetime
from decimal import ROUND_CEILING, Decimal, localcontext
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from alon_ai.integrations.schemas.provider import Capability, StrictDTO, UsageComponent
from alon_ai.policies.provider_rights import IntendedUse

Money = Annotated[
    Decimal,
    Field(ge=0, lt=Decimal(1000000000000), decimal_places=12, allow_inf_nan=False),
]
Precise = Annotated[
    Decimal,
    Field(
        ge=0,
        lt=Decimal(1000000000000000000000000),
        decimal_places=24,
        allow_inf_nan=False,
    ),
]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class Reason(StrEnum):
    CONFIG = "CONFIG"
    SCOPE = "SCOPE"
    RIGHTS = "RIGHTS"
    PRICE = "PRICE"
    BUDGET = "BUDGET"
    QUOTA = "QUOTA"
    CONCURRENCY = "CONCURRENCY"
    CIRCUIT = "CIRCUIT"
    DEADLINE = "DEADLINE"
    CONFLICT = "CONFLICT"
    UNCERTAIN = "UNCERTAIN"
    STATE = "STATE"
    USAGE = "USAGE"
    RETENTION = "RETENTION"
    WRITE = "WRITE"
    GATE = "GATE"
    SECRET = "SECRET"


class AccountingDenied(Exception):
    def __init__(self, reason: Reason):
        if not isinstance(reason, Reason):
            raise TypeError("reason required")
        self.reason = reason
        super().__init__(reason.value)


class Version(StrictDTO):
    id: UUID
    effective_at: AwareDatetime
    expires_at: AwareDatetime
    evidence_id: UUID

    @model_validator(mode="after")
    def timeline(self) -> Self:
        if self.expires_at <= self.effective_at:
            raise ValueError("invalid validity period")
        return self


class PriceVersion(Version):
    model_identifier: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_.:-]{1,100}$"
    )
    capability: Capability
    component: UsageComponent
    currency: Currency
    unit_price: Money
    unit_quantity: Money = Field(gt=0)
    currency_quantum: Decimal = Field(gt=0, le=1, decimal_places=4, allow_inf_nan=False)
    rounding_version: Literal["CEILING_V1"] = "CEILING_V1"

    @model_validator(mode="after")
    def quantum(self) -> Self:
        if self.currency not in {"USD", "ILS"} or self.currency_quantum != Decimal(
            ".01"
        ):
            raise ValueError("unsupported currency quantum")
        if (self.capability == Capability.OPENAI_GENERATE) != (
            self.model_identifier is not None
        ):
            raise ValueError("model price binding required")
        return self


class FxVersion(Version):
    currency: Currency
    rate: Money = Field(gt=0)
    quote_currency: Literal["ILS"] = "ILS"
    rounding_version: Literal["EXACT_V1"] = "EXACT_V1"

    @model_validator(mode="after")
    def same_currency(self) -> Self:
        if self.currency not in {"USD", "ILS"} or (
            self.currency == "ILS" and self.rate != 1
        ):
            raise ValueError("identity FX must equal one")
        return self


class PriceBound(StrictDTO):
    price_id: UUID
    max_quantity: Money = Field(gt=0)


class CapabilityConfig(StrictDTO):
    """Trusted, immutable provisioning; bound quantities describe one exact config."""

    id: UUID
    version: UUID
    workflow_id: UUID
    intended_use: IntendedUse
    prices: tuple[PriceBound, ...] = Field(min_length=1, max_length=10)
    fx_id: UUID
    requested_count: int = Field(ge=1, le=100)
    secret_handle: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"
    )
    adapter_version: UUID
    model_identifier: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_.:-]{1,100}$"
    )


class ControlPolicy(Version):
    capability: Capability
    account_handle: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    timeout_seconds: int = Field(gt=0, le=3600)
    quota_limit: int = Field(gt=0)
    window_seconds: int = Field(gt=0, le=31536000)
    concurrency_limit: int = Field(gt=0, le=1000)
    failure_threshold: int = Field(gt=0, le=1000)
    failure_window_seconds: int = Field(gt=0, le=86400)
    cooldown_seconds: int = Field(gt=0, le=86400)


class CallState(StrEnum):
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    RECONCILING = "RECONCILING"
    FINAL = "FINAL"
    RELEASED = "RELEASED"


class CallReceipt(StrictDTO):
    call_id: UUID
    state: CallState
    currency: Currency
    reserved: Precise
    reserved_ils: Precise
    accrued: Precise
    accrued_ils: Precise
    token: UUID | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)


def reserve_amount(amount: Decimal, quantum: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 64
        return (amount / quantum).to_integral_value(rounding=ROUND_CEILING) * quantum


def exact_product(a: Decimal, b: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 64
        return a * b


def current(version: Version, now: datetime) -> bool:
    return version.effective_at <= now < version.expires_at


class EvidenceRecord(StrictDTO):
    id: UUID
    kind: Literal[
        "PRICE",
        "FX",
        "GRANT",
        "GRANT_EVENT",
        "CONTROL",
        "RECONCILIATION",
        "INVOICE",
        "PROVIDER_RESULT",
    ]
    mode: Literal["SYNTHETIC", "TRUSTED_REFERENCE"]
    registered_by: UUID
    registered_at: AwareDatetime
    call_id: UUID | None = None

    @model_validator(mode="after")
    def bound_proof(self) -> Self:
        if (self.kind in {"RECONCILIATION", "INVOICE", "PROVIDER_RESULT"}) != (
            self.call_id is not None
        ):
            raise ValueError("proof scope mismatch")
        return self


class CostSnapshot(StrictDTO):
    call_id: UUID
    state: CallState
    currency: Currency
    live_reserved: Precise
    live_reserved_ils: Precise
    accrued: Precise
    accrued_ils: Precise
    estimated: Precise
    unknown_components: int = Field(ge=0)
    cash: Precise
    cash_ils: Precise
