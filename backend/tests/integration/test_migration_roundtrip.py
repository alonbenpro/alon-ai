"""Prove the complete migration chain restores the same schema after rollback."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from test_idea_experiment_api import creation_body
from test_operator_access import ORIGIN, _app

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
                "extensions",
                "views",
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


async def test_l07_return_downgrade_rejects_rich_immutable_evidence(
    governance_engine,
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        )
        assert created.status_code == 201, created.text
        experiment_id = created.json()["experiment_id"]
        refined = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert refined.status_code == 200, refined.text
        accepted = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={
                "run_id": refined.json()["run_id"],
                "command_key": str(uuid4()),
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "Creates a retained rich brief.",
            },
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text
    await governance_engine.dispose()
    env = dict(
        os.environ,
        ALON_AI_DATABASE_URL=governance_engine.url.render_as_string(
            hide_password=False
        ),
        ALON_AI_ENVIRONMENT="test",
    )
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "downgrade", "20260926_26"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode != 0
    assert "cannot discard L07 rich return evidence" in result.stderr
