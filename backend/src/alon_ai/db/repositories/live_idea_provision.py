"""Atomic reviewed live Idea authority registration and operator lookup."""

from __future__ import annotations

import json
from typing import Protocol
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.db.repositories.accounting import safe_errors
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.records_operator import operators
from alon_ai.policies.provider_rights import ProviderUsageGrant
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    ControlPolicy,
    EvidenceRecord,
    FxVersion,
    PriceVersion,
    Reason,
)


class AuthorityBundleLike(Protocol):
    @property
    def policy(self) -> ControlPolicy: ...

    @property
    def grant(self) -> ProviderUsageGrant: ...

    @property
    def prices(self) -> tuple[PriceVersion, ...]: ...

    @property
    def fx(self) -> FxVersion: ...

    @property
    def evidence(self) -> tuple[EvidenceRecord, ...]: ...


@safe_errors
async def register_authority_rows(
    engine: AsyncEngine, bundle: AuthorityBundleLike
) -> None:
    """Register the same L03 authority rows in one all-or-nothing transaction."""

    policy = bundle.policy
    grant = bundle.grant
    async with engine.begin() as connection:
        existing_authority = (
            (
                await connection.execute(
                    select(gov.authorities)
                    .where(
                        gov.authorities.c.account == policy.account_handle,
                        gov.authorities.c.capability == policy.capability,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if existing_authority is not None:

            async def exact(table, key, expected) -> bool:
                row = (
                    (await connection.execute(select(table).where(table.c.id == key)))
                    .mappings()
                    .one_or_none()
                )
                return row is not None and all(
                    row[field] == value for field, value in expected.items()
                )

            async def exact_grant() -> bool:
                row = (
                    (
                        await connection.execute(
                            select(gov.grants).where(gov.grants.c.id == grant.grant_id)
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    return False
                return (
                    row["version"] == grant.version
                    and row["account"] == grant.account_handle
                    and row["capability"] == grant.capability
                    and row["effective_at"] == grant.effective_at
                    and row["expires_at"] == grant.expires_at
                    and row["evidence_id"] == grant.supporting_evidence_ref
                    and ProviderUsageGrant.model_validate_json(json.dumps(row["data"]))
                    == grant
                )

            matches = (
                existing_authority["enabled"] is True
                and existing_authority["policy_id"] == policy.id
                and await exact(
                    gov.policies,
                    policy.id,
                    {
                        "account": policy.account_handle,
                        "capability": policy.capability,
                        "data": policy.model_dump(mode="json"),
                        "evidence_id": policy.evidence_id,
                    },
                )
                and await exact_grant()
                and all(
                    [
                        await exact(
                            gov.evidence,
                            proof.id,
                            proof.model_dump(exclude={"schema_version"}),
                        )
                        for proof in bundle.evidence
                    ]
                )
                and all(
                    [
                        await exact(
                            gov.prices,
                            price.id,
                            price.model_dump(exclude={"schema_version"}),
                        )
                        for price in bundle.prices
                    ]
                )
                and await exact(
                    gov.fx,
                    bundle.fx.id,
                    bundle.fx.model_dump(exclude={"schema_version"}),
                )
                and (
                    await connection.scalar(
                        select(gov.grant_events.c.id).where(
                            gov.grant_events.c.grant_id == grant.grant_id,
                            gov.grant_events.c.grant_version == grant.version,
                        )
                    )
                )
                is None
            )
            if not matches:
                raise AccountingDenied(Reason.CONFIG)
            return
        for proof in bundle.evidence:
            await connection.execute(
                insert(gov.evidence).values(
                    **proof.model_dump(exclude={"schema_version"})
                )
            )
        inserted = await connection.execute(
            pg_insert(gov.authorities)
            .values(account=policy.account_handle, capability=policy.capability)
            .on_conflict_do_nothing()
            .returning(gov.authorities.c.account)
        )
        if inserted.scalar_one_or_none() is None:
            raise AccountingDenied(Reason.CONFIG)
        await connection.execute(
            insert(gov.policies).values(
                id=policy.id,
                account=policy.account_handle,
                capability=policy.capability,
                data=policy.model_dump(mode="json"),
                evidence_id=policy.evidence_id,
            )
        )
        await connection.execute(
            update(gov.authorities)
            .where(
                gov.authorities.c.account == policy.account_handle,
                gov.authorities.c.capability == policy.capability,
            )
            .values(policy_id=policy.id)
        )
        await connection.execute(
            insert(gov.grants).values(
                id=grant.grant_id,
                version=grant.version,
                account=grant.account_handle,
                capability=grant.capability,
                effective_at=grant.effective_at,
                expires_at=grant.expires_at,
                data=grant.model_dump(mode="json"),
                evidence_id=grant.supporting_evidence_ref,
            )
        )
        for price in bundle.prices:
            await connection.execute(
                insert(gov.prices).values(
                    **price.model_dump(exclude={"schema_version"})
                )
            )
        await connection.execute(
            insert(gov.fx).values(**bundle.fx.model_dump(exclude={"schema_version"}))
        )


async def current_operator_status(engine: AsyncEngine, operator_id: UUID) -> str | None:
    async with engine.connect() as connection:
        return await connection.scalar(
            select(operators.c.status).where(operators.c.id == operator_id)
        )


async def active_operator_for_subject(
    engine: AsyncEngine, auth_subject: str
) -> UUID | None:
    """Resolve only the active local operator bound to this login subject."""
    async with engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    select(operators.c.id, operators.c.status).where(
                        operators.c.auth_subject == auth_subject
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
    if row is None or row["status"] != "ACTIVE":
        return None
    return row["id"]
