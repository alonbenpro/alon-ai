"""Deterministic reservation and observed-usage calculations for OpenAI."""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal, localcontext
from uuid import UUID, uuid5

from alon_ai.agents.schemas.openai import OpenAIProfile, ParsedResponse
from alon_ai.integrations.schemas.provider import (
    CostKnowledge,
    UsageComponent,
    UsageObservation,
)
from alon_ai.provider_usage.schemas.accounting import CapabilityConfig, PriceVersion


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
