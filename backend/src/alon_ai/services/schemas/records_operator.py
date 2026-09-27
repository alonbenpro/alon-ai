"""Operator identity and delivery constraints; skills are not permissions."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, Field, field_serializer, field_validator

from alon_ai.integrations.schemas.provider import StrictDTO

Amount = Annotated[
    Decimal,
    Field(ge=0, lt=Decimal(1000000000000), decimal_places=6, allow_inf_nan=False),
]
Rate = Annotated[Decimal, Field(ge=0, le=1, decimal_places=6, allow_inf_nan=False)]


class OperatorIdentity(StrictDTO):
    id: UUID
    auth_subject: str = Field(pattern=r"^[^\s\x00-\x1f]{1,255}$")
    display_name: str = Field(min_length=1, max_length=120)
    timezone: str = "Asia/Jerusalem"

    @field_validator("display_name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("operator name is empty")
        return value

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown timezone") from None
        return value


class DeliveryConstraints(StrictDTO):
    max_project_hours: Annotated[
        Decimal, Field(gt=0, le=100000, decimal_places=2, allow_inf_nan=False)
    ]
    hours_per_week: Annotated[
        Decimal, Field(gt=0, le=168, decimal_places=2, allow_inf_nan=False)
    ]
    concurrent_projects: int = Field(ge=1, le=100)

    @field_serializer("max_project_hours", "hours_per_week", when_used="json")
    def exact_hours(self, value: Decimal) -> str:
        return format(value, "f")


class CommercialConstraints(StrictDTO):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    hourly_cost: Amount
    minimum_project_price: Amount
    minimum_margin_rate: Rate
    maximum_discount_rate: Rate
    minimum_deposit_rate: Rate

    @field_serializer(
        "hourly_cost",
        "minimum_project_price",
        "minimum_margin_rate",
        "maximum_discount_rate",
        "minimum_deposit_rate",
        when_used="json",
    )
    def exact_amount(self, value: Decimal) -> str:
        return "0" if value == 0 else format(value, "f")


class OperatorProfileVersion(StrictDTO):
    id: UUID
    version: int = Field(ge=1)
    operator_id: UUID
    capabilities: tuple[str, ...] = Field(min_length=1, max_length=100)
    constraints: tuple[str, ...] = Field(max_length=100)
    delivery: DeliveryConstraints
    commercial: CommercialConstraints
    approved_by: UUID
    created_at: AwareDatetime

    @field_validator("capabilities", "constraints")
    @classmethod
    def meaningful_entries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)) or any(
            not item.strip() or len(item) > 1000 for item in value
        ):
            raise ValueError("invalid profile entries")
        return value
