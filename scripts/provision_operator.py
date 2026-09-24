"""Bind the one configured private-login subject to the existing operator table."""

import argparse
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from alon_ai.config import get_settings
from alon_ai.db.engine import create_engine


async def provision(display_name: str) -> None:
    settings = get_settings()
    subject = settings.operator_auth_subject
    if (
        not subject
        or not settings.operator_password_hash
        or not settings.session_signing_key
        or not display_name.strip()
    ):
        raise SystemExit("Operator authentication configuration is incomplete")
    engine = create_engine(settings)
    try:
        async with engine.begin() as connection:
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
                    raise SystemExit("Configured operator is disabled")
                print(f"Operator already provisioned: {existing['id']}")
                return
            count = (
                await connection.execute(
                    text("SELECT count(*) FROM record_operators WHERE status='ACTIVE'")
                )
            ).scalar_one()
            if count:
                raise SystemExit("Another active operator is already present")
            now = datetime.now(UTC)
            operator_id = uuid4()
            await connection.execute(
                text("""INSERT INTO record_operators
                    (id,auth_subject,display_name,timezone,status,created_at,updated_at)
                    VALUES (:id,:subject,:display_name,'Asia/Jerusalem','ACTIVE',:now,:now)"""),
                {
                    "id": operator_id,
                    "subject": subject,
                    "display_name": display_name.strip(),
                    "now": now,
                },
            )
        print(f"Operator provisioned: {operator_id}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--display-name", default="Alon")
    asyncio.run(provision(parser.parse_args().display_name))
