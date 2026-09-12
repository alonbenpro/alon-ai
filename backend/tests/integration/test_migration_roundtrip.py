"""Prove the complete migration chain restores the same schema after rollback."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from alon_ai.db.schema_manifest import collect_schema


async def test_full_migration_chain_roundtrip(governance_engine):
    engine = governance_engine  # The fixture owns this newly created database.
    async with engine.connect() as connection:
        before = await collect_schema(connection)
    await engine.dispose()
    env = dict(
        os.environ,
        ALON_AI_DATABASE_URL=engine.url.render_as_string(hide_password=False),
        ALON_AI_ENVIRONMENT="test",
    )
    for direction, target in (("downgrade", "base"), ("upgrade", "head")):
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", direction, target],
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        async with engine.connect() as connection:
            actual = await collect_schema(connection)
        if direction == "downgrade":
            assert actual["alembic_heads"] == []
            for component in (
                "tables",
                "columns",
                "constraints",
                "indexes",
                "triggers",
                "functions",
            ):
                assert actual[component] == [], component
        else:
            assert actual == before
        await engine.dispose()
