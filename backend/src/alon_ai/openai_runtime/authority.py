"""Content-free, durable authority facts for a single Responses dispatch."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting import schema as gov
from alon_ai.openai_runtime.contract import (
    PremiumAuthorization,
    Route,
    canonical_json,
    sha256,
)
from alon_ai.openai_runtime.schema import (
    premium_approvals,
    route_decisions,
    run_intents,
)
from alon_ai.openai_runtime.store import OpenAIRunConflict
from alon_ai.providers.contracts import CallAttribution
from alon_ai.providers.rights import GrantEvent, ProviderUsageGrant


@dataclass(frozen=True)
class AuthoritySnapshot:
    """One coherent read of grants, grant events, and premium approval state."""

    grants: Mapping[tuple[UUID, int], ProviderUsageGrant]
    events: tuple[GrantEvent, ...]
    approval: PremiumAuthorization | None
    approval_config_id: UUID | None
    revoked_at: datetime | None


class OpenAIAuthorityStoreError(Exception):
    def __init__(self):
        super().__init__("OpenAI authority evidence store unavailable")


def _hash(value: object) -> str:
    return sha256(canonical_json(value))


def _attribution_values(attribution: CallAttribution) -> dict[str, UUID | str]:
    return {
        "experiment_id": attribution.experiment_id,
        "workflow_id": attribution.workflow_run_id,
        "operation_id": attribution.operation_run_id,
        "config_version": attribution.config_version,
        "correlation_id": attribution.correlation_id,
        "logical_operation_id": attribution.logical_operation_id,
        "attribution_hash": _hash(attribution.model_dump(mode="json")),
    }


def _approval_values(
    authorization: PremiumAuthorization, config_id: UUID
) -> dict[str, UUID | datetime]:
    if (
        authorization.approved_at.tzinfo is None
        or authorization.expires_at.tzinfo is None
        or authorization.approved_at >= authorization.expires_at
    ):
        raise OpenAIRunConflict()
    return {
        "authorization_id": authorization.authorization_id,
        "scope": authorization.scope,
        "config_id": config_id,
        "approved_by": authorization.approved_by,
        "approved_at": authorization.approved_at,
        "expires_at": authorization.expires_at,
    }


class OpenAIAuthorityStore:
    """Immutable decision and approval evidence; it never handles source content."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def approve(
        self, authorization: PremiumAuthorization, config_id: UUID
    ) -> None:
        values = _approval_values(authorization, config_id)
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    pg_insert(premium_approvals)
                    .values(**values)
                    .on_conflict_do_nothing(index_elements=["authorization_id"])
                )
                row = (
                    (
                        await connection.execute(
                            select(premium_approvals).where(
                                premium_approvals.c.authorization_id
                                == authorization.authorization_id
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                if any(row[key] != value for key, value in values.items()):
                    raise OpenAIRunConflict()
        except OpenAIRunConflict:
            raise
        except SQLAlchemyError:
            raise OpenAIAuthorityStoreError() from None

    async def revoke(self, approval_id: UUID, at: datetime) -> None:
        if at.tzinfo is None or at.utcoffset() is None:
            raise OpenAIRunConflict()
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    update(premium_approvals)
                    .where(
                        premium_approvals.c.authorization_id == approval_id,
                        premium_approvals.c.revoked_at.is_(None),
                    )
                    .values(revoked_at=at)
                )
                row = (
                    await connection.execute(
                        select(premium_approvals.c.revoked_at).where(
                            premium_approvals.c.authorization_id == approval_id
                        )
                    )
                ).scalar_one_or_none()
                if row != at:
                    raise OpenAIRunConflict()
        except OpenAIRunConflict:
            raise
        except SQLAlchemyError:
            raise OpenAIAuthorityStoreError() from None

    async def bind_decision(
        self,
        key: UUID,
        attribution: CallAttribution,
        facts_hash: str,
        route: Route,
        config_id: UUID | None,
        approval_id: UUID | None,
    ) -> None:
        if len(facts_hash) != 64 or any(
            char not in "0123456789abcdef" for char in facts_hash
        ):
            raise OpenAIRunConflict()
        values: dict[str, UUID | str | datetime | None] = {
            "idempotency_key": key,
            **_attribution_values(attribution),
            "facts_hash": facts_hash,
            "route": route.value,
            "config_id": config_id,
            "approval_id": approval_id,
            "created_at": datetime.now(UTC),
        }
        no_ai = route is Route.NO_AI
        if no_ai != (config_id is None and approval_id is None):
            raise OpenAIRunConflict()
        if route in {Route.CHEAP, Route.STRONGER} and (
            config_id is None or approval_id is not None
        ):
            raise OpenAIRunConflict()
        if route is Route.PREMIUM and (config_id is None or approval_id is None):
            raise OpenAIRunConflict()
        try:
            async with self.engine.begin() as connection:
                # Every runtime path writes this decision before it can create a
                # run intent. The lock makes conflicting first decisions linear.
                await connection.execute(
                    text(
                        "SELECT pg_advisory_xact_lock("
                        "hashtextextended(CAST(:key AS text), 0))"
                    ),
                    {"key": key},
                )
                if no_ai:
                    paid_exists = (
                        await connection.execute(
                            text(
                                "SELECT EXISTS(SELECT 1 FROM openai_run_intents "
                                "WHERE idempotency_key=:key) OR EXISTS(SELECT 1 "
                                "FROM gov_calls WHERE idempotency_key=:key)"
                            ),
                            {"key": key},
                        )
                    ).scalar_one()
                    if paid_exists:
                        raise OpenAIRunConflict()
                else:
                    # L06's first checkpoint created intents before route facts
                    # existed. A new decision may only adopt that legacy evidence
                    # when every durable paid lineage fact is exact.
                    legacy_intent = (
                        (
                            await connection.execute(
                                select(run_intents).where(
                                    run_intents.c.idempotency_key == key
                                )
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    legacy_call = (
                        (
                            await connection.execute(
                                select(gov.calls).where(
                                    gov.calls.c.idempotency_key == key
                                )
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    expected = {
                        "config_id": config_id,
                        "config_version": attribution.config_version,
                        "experiment_id": attribution.experiment_id,
                        "workflow_id": attribution.workflow_run_id,
                        "operation_id": attribution.operation_run_id,
                    }
                    if legacy_intent is not None and any(
                        legacy_intent[name] != value for name, value in expected.items()
                    ):
                        raise OpenAIRunConflict()
                    if legacy_call is not None and (
                        any(
                            legacy_call[name] != value
                            for name, value in expected.items()
                        )
                        or legacy_call["attribution"]
                        != attribution.model_dump(mode="json")
                    ):
                        raise OpenAIRunConflict()
                if route is Route.PREMIUM:
                    approval = (
                        (
                            await connection.execute(
                                select(
                                    premium_approvals.c.scope,
                                    premium_approvals.c.config_id,
                                ).where(
                                    premium_approvals.c.authorization_id == approval_id
                                )
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if (
                        approval is None
                        or approval["scope"] != attribution.experiment_id
                        or approval["config_id"] != config_id
                    ):
                        raise OpenAIRunConflict()
                await connection.execute(
                    pg_insert(route_decisions)
                    .values(**values)
                    .on_conflict_do_nothing(index_elements=["idempotency_key"])
                )
                row = (
                    (
                        await connection.execute(
                            select(route_decisions).where(
                                route_decisions.c.idempotency_key == key
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                if any(
                    row[name] != value
                    for name, value in values.items()
                    if name != "created_at"
                ):
                    raise OpenAIRunConflict()
        except OpenAIRunConflict:
            raise
        except SQLAlchemyError:
            raise OpenAIAuthorityStoreError() from None

    async def snapshot(
        self,
        grant_refs: tuple[tuple[UUID, int], ...],
        approval_id: UUID | None,
    ) -> AuthoritySnapshot:
        try:
            async with self.engine.connect() as connection:
                return await self._snapshot(connection, grant_refs, approval_id)
        except SQLAlchemyError:
            raise OpenAIAuthorityStoreError() from None

    @asynccontextmanager
    async def dispatch_guard(
        self,
        grant_refs: tuple[tuple[UUID, int], ...],
        approval_id: UUID | None,
    ) -> AsyncIterator[AuthoritySnapshot]:
        """Serialize dispatch with grant events and premium revocation.

        The caller may only hold this guard for rights checks and one bounded
        transport call. Ledger writes occur after it exits, preserving the
        governance repository's established lock order.
        """
        grant_ids = [grant_id for grant_id, _ in grant_refs]
        grant_versions = [version for _, version in grant_refs]
        try:
            async with self.engine.begin() as connection:
                # GovernanceProvisioner writes a grant event under FOR UPDATE on
                # the same authority row. Ordered shared locks therefore make a
                # completed snapshot remain current through the transport call.
                await connection.execute(
                    text(
                        """
SELECT a.account, a.capability
FROM gov_authorities a
JOIN gov_grants g ON g.account=a.account AND g.capability=a.capability
JOIN unnest(CAST(:grant_ids AS uuid[]), CAST(:grant_versions AS integer[]))
  AS r(grant_id, grant_version) ON r.grant_id=g.id AND r.grant_version=g.version
ORDER BY a.account, a.capability
FOR SHARE OF a
                        """
                    ),
                    {"grant_ids": grant_ids, "grant_versions": grant_versions},
                )
                if approval_id is not None:
                    # revoke() updates this exact row; its row lock waits until
                    # the accepted transport call leaves the guard.
                    await connection.execute(
                        text(
                            """SELECT authorization_id
FROM openai_premium_approvals
WHERE authorization_id=CAST(:approval_id AS uuid)
FOR SHARE"""
                        ),
                        {"approval_id": approval_id},
                    )
                yield await self._snapshot(connection, grant_refs, approval_id)
        except SQLAlchemyError:
            raise OpenAIAuthorityStoreError() from None

    async def _snapshot(
        self,
        connection,
        grant_refs: tuple[tuple[UUID, int], ...],
        approval_id: UUID | None,
    ) -> AuthoritySnapshot:
        grant_ids = [grant_id for grant_id, _ in grant_refs]
        grant_versions = [version for _, version in grant_refs]
        row = (
            (
                await connection.execute(
                    text(
                        """
WITH requested(grant_id, grant_version) AS (
  SELECT * FROM unnest(CAST(:grant_ids AS uuid[]), CAST(:grant_versions AS integer[]))
), chosen_grants AS (
  SELECT g.id, g.version, g.data FROM gov_grants g
  JOIN requested r ON r.grant_id=g.id AND r.grant_version=g.version
)
SELECT
 COALESCE((SELECT jsonb_agg(data ORDER BY id, version) FROM chosen_grants), '[]'::jsonb) AS grants,
 COALESCE((SELECT jsonb_agg(e.data ORDER BY e.id) FROM gov_grant_events e
   JOIN requested r ON r.grant_id=e.grant_id AND r.grant_version=e.grant_version), '[]'::jsonb) AS events,
 p.authorization_id, p.scope, p.approved_by, p.approved_at, p.expires_at,
 p.config_id AS approval_config_id, p.revoked_at
FROM (SELECT 1) anchor
LEFT JOIN openai_premium_approvals p
 ON p.authorization_id=CAST(:approval_id AS uuid)
                        """
                    ),
                    {
                        "grant_ids": grant_ids,
                        "grant_versions": grant_versions,
                        "approval_id": approval_id,
                    },
                )
            )
            .mappings()
            .one()
        )
        grants = tuple(
            ProviderUsageGrant.model_validate_json(json.dumps(value, default=str))
            for value in row["grants"]
        )
        events = tuple(
            GrantEvent.model_validate_json(json.dumps(value, default=str))
            for value in row["events"]
        )
        approval = (
            PremiumAuthorization(
                authorization_id=row["authorization_id"],
                scope=row["scope"],
                approved_by=row["approved_by"],
                approved_at=row["approved_at"],
                expires_at=row["expires_at"],
            )
            if row["authorization_id"] is not None
            else None
        )
        return AuthoritySnapshot(
            grants=MappingProxyType(
                {(grant.grant_id, grant.version): grant for grant in grants}
            ),
            events=events,
            approval=approval,
            approval_config_id=row["approval_config_id"],
            revoked_at=row["revoked_at"],
        )
