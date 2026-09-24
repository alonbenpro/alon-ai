"""Trusted operator binding and immutable delivery/commercial profile versions.

Authentication/allowlist verification belongs to the caller (L05). This internal
repository is not a prospect registration surface or a source of model authority.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting import schema as gov
from alon_ai.records import schema as records
from alon_ai.records.operator_models import OperatorIdentity, OperatorProfileVersion

operators = Table(
    "record_operators",
    gov.metadata,
    gov.col("id", gov.U, primary_key=True),
    gov.col("auth_subject", String(255), nullable=True),
    gov.col("display_name", String(120)),
    gov.col("timezone", String(100)),
    gov.col("status", String(16)),
    gov.col("created_at", gov.T),
    gov.col("updated_at", gov.T),
    UniqueConstraint("auth_subject", name="uq_record_operator_subject"),
    CheckConstraint(
        "status IN ('ACTIVE','DISABLED')", name="ck_record_operator_status"
    ),
    CheckConstraint(
        "status<>'ACTIVE' OR auth_subject IS NOT NULL", name="ck_record_operator_bound"
    ),
    CheckConstraint(
        "length(btrim(display_name)) BETWEEN 1 AND 120", name="ck_record_operator_name"
    ),
    CheckConstraint(
        "auth_subject IS NULL OR auth_subject ~ '^[^[:space:][:cntrl:]]{1,255}$'",
        name="ck_record_operator_subject",
    ),
)

profiles = records.operator_profiles
profiles.append_column(gov.col("profile_schema_version", Integer, server_default="1"))
profiles.append_column(gov.col("delivery", JSONB, nullable=True))
profiles.append_column(gov.col("commercial", JSONB, nullable=True))
profiles.append_column(gov.col("approved_by", gov.U, nullable=True))
profiles.append_constraint(
    ForeignKeyConstraint(
        ["operator_id"], ["record_operators.id"], name="fk_record_profile_operator"
    )
)
profiles.append_constraint(
    ForeignKeyConstraint(
        ["approved_by"], ["record_operators.id"], name="fk_record_profile_approver"
    )
)
profiles.append_constraint(
    CheckConstraint(
        "profile_schema_version=1 OR (profile_schema_version=2 AND delivery IS NOT NULL AND commercial IS NOT NULL AND approved_by IS NOT NULL AND approved_by=operator_id)",
        name="ck_record_profile_shape",
    )
)
Index(
    "uq_record_profile_owner_version",
    profiles.c.operator_id,
    profiles.c.version,
    unique=True,
    postgresql_where=profiles.c.profile_schema_version == 2,
)
Index("ix_record_profile_approver", profiles.c.approved_by)


class OperatorRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.engine = engine
        self.clock = clock

    async def register_operator(self, identity: OperatorIdentity, *, command_key: UUID):
        from alon_ai.records.models import CommandReceipt, ProductRecordsDenied
        from alon_ai.records.repository import _complete, _existing, _request_hash

        try:
            async with self.engine.begin() as c:
                await self._lock(c, identity.id)
                request_hash = _request_hash(identity=identity)
                prior = await _existing(
                    c, command_key, "REGISTER_OPERATOR", request_hash
                )
                if prior:
                    return CommandReceipt(
                        command_id=prior["id"], result_id=prior["result_id"]
                    )
                row = (
                    (
                        await c.execute(
                            select(operators)
                            .where(operators.c.id == identity.id)
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                values = identity.model_dump(exclude={"schema_version"})
                if row is None:
                    await c.execute(
                        insert(operators).values(
                            **values,
                            status="ACTIVE",
                            created_at=self.clock(),
                            updated_at=self.clock(),
                        )
                    )
                elif row["auth_subject"] is None:
                    # Bind a disabled historical identity only from an explicit
                    # trusted identity command; never synthesize an auth subject.
                    await c.execute(
                        update(operators)
                        .where(operators.c.id == identity.id)
                        .values(**values, status="ACTIVE", updated_at=self.clock())
                    )
                elif any(row[key] != value for key, value in values.items()):
                    raise ProductRecordsDenied("IDENTITY_CONFLICT")
                command = await _complete(
                    c,
                    command_key=command_key,
                    experiment_id=None,
                    kind="REGISTER_OPERATOR",
                    request_hash=request_hash,
                    result_type="OPERATOR",
                    result_id=identity.id,
                    now=self.clock(),
                )
                return CommandReceipt(command_id=command, result_id=identity.id)
        except SQLAlchemyError:
            pass
        raise ProductRecordsDenied()

    async def register_profile(
        self, profile: OperatorProfileVersion, *, command_key: UUID
    ):
        from alon_ai.records.models import CommandReceipt, ProductRecordsDenied
        from alon_ai.records.repository import _complete, _existing, _request_hash

        if (
            profile.approved_by != profile.operator_id
            or profile.created_at > self.clock()
        ):
            raise ProductRecordsDenied("PROFILE_APPROVAL")
        try:
            async with self.engine.begin() as c:
                await self._lock(c, profile.operator_id)
                request_hash = _request_hash(profile=profile)
                prior = await _existing(
                    c, command_key, "REGISTER_PROFILE", request_hash
                )
                if prior:
                    return CommandReceipt(
                        command_id=prior["id"], result_id=prior["result_id"]
                    )
                await c.execute(
                    insert(profiles).values(
                        id=profile.id,
                        version=profile.version,
                        operator_id=profile.operator_id,
                        capabilities=list(profile.capabilities),
                        constraints=list(profile.constraints),
                        created_at=profile.created_at,
                        profile_schema_version=2,
                        delivery=profile.delivery.model_dump(mode="json"),
                        commercial=profile.commercial.model_dump(mode="json"),
                        approved_by=profile.approved_by,
                    )
                )
                command = await _complete(
                    c,
                    command_key=command_key,
                    experiment_id=None,
                    kind="REGISTER_PROFILE",
                    request_hash=request_hash,
                    result_type="OPERATOR_PROFILE",
                    result_id=profile.id,
                    now=self.clock(),
                )
                return CommandReceipt(command_id=command, result_id=profile.id)
        except SQLAlchemyError:
            pass
        raise ProductRecordsDenied()

    async def set_operator_status(
        self, operator_id: UUID, *, active: bool, acted_by: UUID, command_key: UUID
    ):
        from alon_ai.records.models import CommandReceipt, ProductRecordsDenied
        from alon_ai.records.repository import _complete, _existing, _request_hash

        if acted_by != operator_id or type(active) is not bool:
            raise ProductRecordsDenied("OPERATOR_OWNER")
        try:
            async with self.engine.begin() as c:
                await self._lock(c, operator_id)
                request_hash = _request_hash(
                    operator_id=operator_id, active=active, acted_by=acted_by
                )
                prior = await _existing(
                    c, command_key, "SET_OPERATOR_STATUS", request_hash
                )
                if prior:
                    return CommandReceipt(
                        command_id=prior["id"], result_id=prior["result_id"]
                    )
                row = (
                    (
                        await c.execute(
                            select(operators)
                            .where(operators.c.id == operator_id)
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None or row["auth_subject"] is None:
                    raise ProductRecordsDenied("UNBOUND_OPERATOR")
                await c.execute(
                    update(operators)
                    .where(operators.c.id == operator_id)
                    .values(
                        status="ACTIVE" if active else "DISABLED",
                        updated_at=self.clock(),
                    )
                )
                command = await _complete(
                    c,
                    command_key=command_key,
                    experiment_id=None,
                    kind="SET_OPERATOR_STATUS",
                    request_hash=request_hash,
                    result_type="OPERATOR",
                    result_id=operator_id,
                    now=self.clock(),
                )
                return CommandReceipt(command_id=command, result_id=operator_id)
        except SQLAlchemyError:
            pass
        raise ProductRecordsDenied()

    @staticmethod
    async def _lock(c, operator_id: UUID):
        await c.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": "record-operator:" + str(operator_id)},
        )
