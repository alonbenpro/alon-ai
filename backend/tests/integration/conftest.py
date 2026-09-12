"""Every governance test owns a newly created database, never an existing schema."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
async def governance_engine():
    raw = os.environ.get(
        "ALON_AI_DATABASE_URL",
        "postgresql+psycopg://alon_ai:alon_ai@localhost:55432/alon_ai",
    )
    url = make_url(raw)
    if not os.environ.get("CI") and url.port != 55432:
        pytest.fail("Local governance tests require isolated PostgreSQL port 55432")
    name = "alon_ai_test_" + uuid4().hex
    admin = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    test_url = url.set(database=name)
    engine = create_async_engine(test_url, hide_parameters=True)
    try:
        env = dict(
            os.environ,
            ALON_AI_DATABASE_URL=test_url.render_as_string(hide_password=False),
            ALON_AI_ENVIRONMENT="test",
        )
        completed = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        yield engine
    finally:
        await engine.dispose()
        async with admin.connect() as conn:
            await conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        await admin.dispose()
