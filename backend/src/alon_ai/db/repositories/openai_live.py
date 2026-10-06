"""Atomic persistence checks for provisioned live OpenAI runs."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.db.repositories.accounting import safe_errors
from alon_ai.db.tables import accounting as gov
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    CapabilityConfig,
    Reason,
)


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
        "data": config.database_data(),
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
        if any(
            actual[key] != value for key, value in expected.items() if key != "data"
        ) or (
            CapabilityConfig.model_validate_json(json.dumps(actual["data"])) != config
        ):
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
