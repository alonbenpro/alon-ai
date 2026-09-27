"""Atomic registration of the single configured operator."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class OperatorProvisioningDenied(Exception):
    """An existing operator record prevents registration."""


class OperatorProvisioningRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def provision(self, subject: str, display_name: str) -> tuple[UUID, bool]:
        async with self.engine.begin() as connection:
            await connection.execute(text("SELECT pg_advisory_xact_lock(590005)"))
            existing = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,status FROM record_operators WHERE auth_subject=:subject"
                        ),
                        {"subject": subject},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                if existing["status"] != "ACTIVE":
                    raise OperatorProvisioningDenied("Configured operator is disabled")
                return existing["id"], False
            count = (
                await connection.execute(
                    text("SELECT count(*) FROM record_operators WHERE status='ACTIVE'")
                )
            ).scalar_one()
            if count:
                raise OperatorProvisioningDenied(
                    "Another active operator is already present"
                )
            now = datetime.now(UTC)
            operator_id = uuid4()
            await connection.execute(
                text("""INSERT INTO record_operators
                    (id,auth_subject,display_name,timezone,status,created_at,updated_at)
                    VALUES (:id,:subject,:display_name,'Asia/Jerusalem','ACTIVE',:now,:now)"""),
                {
                    "id": operator_id,
                    "subject": subject,
                    "display_name": display_name,
                    "now": now,
                },
            )
        return operator_id, True
