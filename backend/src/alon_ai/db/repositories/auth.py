"""Atomic operator session authentication and revocation persistence."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

SESSION_AGE = timedelta(hours=8)
LOGIN_CAPACITY = 2
_LOGIN_DELAY_THRESHOLD = 5
_LOGIN_DELAY_SECONDS = 2
_LOGIN_WINDOW = timedelta(minutes=15)


class LoginRateLimited(Exception):
    """Both bounded login admission slots are occupied."""


class AuthRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def login_admitted(
        self,
        subject: str,
        password: str,
        verifier: str,
        password_matches: Callable[[str, str], bool],
    ) -> tuple[UUID, UUID, str] | None:
        async with self.engine.begin() as connection:
            # Two-int advisory keys allow one verifier and one waiter across workers.
            for slot in range(LOGIN_CAPACITY):
                acquired = (
                    await connection.execute(
                        text("SELECT pg_try_advisory_xact_lock(590006, :slot)"),
                        {"slot": slot},
                    )
                ).scalar_one()
                if acquired:
                    break
            else:
                raise LoginRateLimited
            await connection.execute(text("SELECT pg_advisory_xact_lock(590006)"))
            now = datetime.now(UTC)
            failures = (
                await connection.execute(
                    text("""SELECT count(*) FROM operator_login_failures
                        WHERE auth_subject=:subject AND attempted_at>=:since"""),
                    {"subject": subject, "since": now - _LOGIN_WINDOW},
                )
            ).scalar_one()
            if failures >= _LOGIN_DELAY_THRESHOLD:
                await asyncio.sleep(_LOGIN_DELAY_SECONDS)
                now = datetime.now(UTC)
            verification = asyncio.create_task(
                asyncio.to_thread(password_matches, password, verifier)
            )
            try:
                valid_password = await asyncio.shield(verification)
            except asyncio.CancelledError:
                # Scrypt continues in a thread; hold the transaction lock until it exits.
                while not verification.done():
                    try:
                        await asyncio.shield(verification)
                    except asyncio.CancelledError:
                        continue
                raise
            if not valid_password:
                await connection.execute(
                    text("""INSERT INTO operator_login_failures(id,auth_subject,attempted_at)
                        VALUES (:id,:subject,:attempted_at)"""),
                    {"id": uuid4(), "subject": subject, "attempted_at": now},
                )
                return None
            row = (
                (
                    await connection.execute(
                        text("""SELECT id, display_name FROM record_operators
                        WHERE auth_subject=:subject AND status='ACTIVE'"""),
                        {"subject": subject},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            session_id = uuid4()
            await connection.execute(
                text("""INSERT INTO operator_sessions
                    (id,operator_id,issued_at,expires_at)
                    VALUES (:id,:operator_id,:issued_at,:expires_at)"""),
                {
                    "id": session_id,
                    "operator_id": row["id"],
                    "issued_at": now,
                    "expires_at": now + SESSION_AGE,
                },
            )
        return session_id, row["id"], row["display_name"]

    async def resolve(self, session_id: UUID, subject: str) -> tuple[UUID, str] | None:
        async with self.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("""SELECT o.id, o.display_name
                        FROM operator_sessions s
                        JOIN record_operators o ON o.id=s.operator_id
                        WHERE s.id=:id AND s.revoked_at IS NULL
                          AND s.expires_at>now() AND o.status='ACTIVE'
                          AND o.auth_subject=:subject"""),
                        {"id": session_id, "subject": subject},
                    )
                )
                .mappings()
                .one_or_none()
            )
        return (row["id"], row["display_name"]) if row is not None else None

    async def logout(self, session_id: UUID) -> None:
        async with self.engine.begin() as connection:
            await connection.execute(
                text("""UPDATE operator_sessions SET revoked_at=GREATEST(now(), issued_at)
                    WHERE id=:id AND revoked_at IS NULL"""),
                {"id": session_id},
            )
