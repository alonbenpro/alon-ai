"""L05 private sessions are enforced by the server, never browser state."""

import asyncio
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from starlette.requests import Request
from test_governance import reserve, seed

from alon_ai.api.app import create_app
from alon_ai.api.auth import COOKIE_NAME, AuthService, LoginRateLimited, hash_password
from alon_ai.api.routes import operator as operator_routes
from alon_ai.config import Settings

ORIGIN = {"Origin": "http://localhost:3000"}


async def test_one_operator_provisioning_is_idempotent(governance_engine):
    subject = "alon@example.test"
    verifier = hash_password("test-password")
    environment = dict(
        os.environ,
        ALON_AI_ENVIRONMENT="test",
        ALON_AI_DATABASE_URL=governance_engine.url.render_as_string(
            hide_password=False
        ),
        ALON_AI_OPERATOR_AUTH_SUBJECT=subject,
        ALON_AI_OPERATOR_PASSWORD_HASH=verifier,
        ALON_AI_SESSION_SIGNING_KEY="a" * 64,
    )
    for _ in range(2):
        result = await asyncio.to_thread(
            subprocess.run,
            [
                sys.executable,
                "../scripts/provision_operator.py",
                "--display-name",
                "Alon",
            ],
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    async with governance_engine.connect() as connection:
        assert (
            await connection.execute(text("SELECT count(*) FROM record_operators"))
        ).scalar_one() == 1


async def _app(engine):
    subject = "alon@example.test"
    operator_id = uuid4()
    now = datetime.now(UTC)
    async with engine.begin() as connection:
        await connection.execute(
            text("""INSERT INTO record_operators
                (id,auth_subject,display_name,timezone,status,created_at,updated_at)
                VALUES (:id,:subject,'Alon','Asia/Jerusalem','ACTIVE',:now,:now)"""),
            {"id": operator_id, "subject": subject, "now": now},
        )
    settings = Settings(
        environment="test",
        _env_file=None,
        database_url=engine.url.render_as_string(hide_password=False),
        operator_auth_subject=subject,
        operator_password_hash=SecretStr(hash_password("test-password")),
        session_signing_key=SecretStr("a" * 64),
    )
    return create_app(settings), operator_id


async def test_private_session_login_logout_and_server_denial(governance_engine):
    app, operator_id = await _app(governance_engine)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        for path in (
            "/operator/status",
            "/operator/activity",
            "/auth/session",
            "/openapi.json",
        ):
            assert client.get(path).status_code == 401
        assert (
            client.get(
                "/operator/status",
                headers={"X-Operator-Role": "owner", "X-Allowed-Command": "true"},
            ).status_code
            == 401
        )
        assert (
            client.post("/auth/login", json={"password": "test-password"}).status_code
            == 403
        )
        assert (
            client.post(
                "/auth/login",
                json={"password": "test-password"},
                headers={"Origin": "https://attacker.example"},
            ).status_code
            == 403
        )
        secret_marker = "sensitive-password-" + "x" * 1100
        invalid = client.post(
            "/auth/login", json={"password": secret_marker}, headers=ORIGIN
        )
        assert invalid.status_code == 422
        assert secret_marker not in invalid.text
        assert (
            client.post(
                "/auth/login", json={"password": "wrong"}, headers=ORIGIN
            ).status_code
            == 401
        )
        response = client.post(
            "/auth/login", json={"password": "test-password"}, headers=ORIGIN
        )
        assert response.status_code == 200
        assert response.json() == {
            "authenticated": True,
            "operator": {"id": str(operator_id), "display_name": "Alon"},
        }
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=lax" in response.headers["set-cookie"].lower()
        token = client.cookies.get(COOKIE_NAME)
        assert token
        assert client.get("/auth/session").status_code == 200
        assert client.get("/operator/status").json() == {
            "health": {"status": "ok"},
            "readiness": {"status": "ready"},
            "counts": {"queued": 0, "running": 0, "completed": 0, "blocked": 0},
        }
        assert client.get("/operator/activity").json() == {"items": [], "cursor": None}
        assert client.get("/operator/activity").headers["cache-control"] == "no-store"
        assert (
            client.post(
                "/auth/logout", headers={"Origin": "https://wrong.test"}
            ).status_code
            == 403
        )
        first_logout = client.post("/auth/logout", headers=ORIGIN)
        assert first_logout.status_code == 204
        assert COOKIE_NAME not in client.cookies
        client.cookies.set(COOKIE_NAME, token)
        assert client.get("/auth/session").status_code == 401
        repeated_logout = client.post("/auth/logout", headers=ORIGIN)
        assert repeated_logout.status_code == 204
        assert "max-age=0" in repeated_logout.headers["set-cookie"].lower()


async def test_tampered_cookie_is_denied(governance_engine):
    app, _ = await _app(governance_engine)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        token = client.cookies.get(COOKIE_NAME)
        assert token
        client.cookies.set(COOKIE_NAME, token + "0")
        assert client.get("/operator/status").status_code == 401
        assert app.state.auth._parse(token[:-1] + "é") is None
        client.cookies.set(COOKIE_NAME, token[:-1] + "%E9")
        assert client.get("/operator/status").status_code == 401


async def test_login_failures_delay_but_do_not_lock_out_correct_credentials(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    service = AuthService(governance_engine, app.state.settings)
    from alon_ai.api import auth as auth_module

    original = auth_module._password_matches

    def slow_password_check(password: str, verifier: str) -> bool:
        time.sleep(0.2)
        return original(password, verifier)

    monkeypatch.setattr(auth_module, "_password_matches", slow_password_check)
    before = time.monotonic()
    pending = asyncio.create_task(service.login("wrong"))
    await asyncio.sleep(0.02)
    assert time.monotonic() - before < 0.15
    assert await pending is None
    monkeypatch.setattr(auth_module, "_password_matches", original)
    with TestClient(app) as client:
        for _ in range(4):
            assert (
                client.post(
                    "/auth/login", json={"password": "wrong"}, headers=ORIGIN
                ).status_code
                == 401
            )
        before = time.monotonic()
        pending = asyncio.create_task(service.login("still-wrong"))
        await asyncio.sleep(0.02)
        assert time.monotonic() - before < 0.15
        assert await pending is None
        assert time.monotonic() - before >= 2
        before = time.monotonic()
        response = client.post(
            "/auth/login", json={"password": "test-password"}, headers=ORIGIN
        )
        assert response.status_code == 200
        assert time.monotonic() - before >= 2
        assert client.get("/auth/session").status_code == 200
    async with governance_engine.connect() as connection:
        assert (
            await connection.execute(
                text("SELECT count(*) FROM operator_login_failures")
            )
        ).scalar_one() == 6


async def test_concurrent_login_burst_is_rejected_without_queuing_password_work(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    service = AuthService(governance_engine, app.state.settings)
    other_service = AuthService(governance_engine, app.state.settings)
    from alon_ai.api import auth as auth_module

    original = auth_module._password_matches
    started = threading.Event()
    release = threading.Event()

    def held_password_check(password: str, verifier: str) -> bool:
        started.set()
        assert release.wait(timeout=5)
        return original(password, verifier)

    monkeypatch.setattr(auth_module, "_password_matches", held_password_check)
    pending = asyncio.create_task(service.login("test-password"))
    try:
        assert await asyncio.to_thread(started.wait, 2)
        results = await asyncio.wait_for(
            asyncio.gather(
                *(other_service.login("wrong") for _ in range(8)),
                return_exceptions=True,
            ),
            timeout=1,
        )
        assert all(isinstance(result, LoginRateLimited) for result in results)
    finally:
        release.set()
        result = await pending
    assert result is not None
    assert await service.resolve(result[0]) is not None
    async with governance_engine.connect() as connection:
        assert (
            await connection.execute(
                text("SELECT count(*) FROM operator_login_failures")
            )
        ).scalar_one() == 0


async def test_expired_session_and_immutable_session_history(governance_engine):
    app, operator_id = await _app(governance_engine)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        token = client.cookies.get(COOKIE_NAME)
        assert token
        session_id = UUID(token.split(".")[1])
        async with governance_engine.begin() as connection:
            with pytest.raises(
                Exception, match="operator session history is immutable"
            ):
                await connection.execute(
                    text(
                        "UPDATE operator_sessions SET expires_at=now()-interval '1 hour' WHERE id=:id"
                    ),
                    {"id": session_id},
                )
        async with governance_engine.begin() as connection:
            with pytest.raises(
                Exception, match="operator session history cannot be deleted"
            ):
                await connection.execute(
                    text("DELETE FROM operator_sessions WHERE id=:id"),
                    {"id": session_id},
                )
        past = datetime.now(UTC) - timedelta(days=2)
        expired_id = uuid4()
        async with governance_engine.begin() as connection:
            await connection.execute(
                text("""INSERT INTO operator_sessions(id,operator_id,issued_at,expires_at)
                    VALUES (:id,:operator_id,:issued_at,:expires_at)"""),
                {
                    "id": expired_id,
                    "operator_id": operator_id,
                    "issued_at": past,
                    "expires_at": past + timedelta(hours=8),
                },
            )
        expired_token = app.state.auth._sign(expired_id)
        client.cookies.set(COOKIE_NAME, expired_token)
        assert client.get("/operator/status").status_code == 401
        expired_logout = client.post("/auth/logout", headers=ORIGIN)
        assert expired_logout.status_code == 204
        assert "max-age=0" in expired_logout.headers["set-cookie"].lower()
        client.cookies.set(COOKIE_NAME, token)
        assert client.get("/operator/status").status_code == 200
        async with governance_engine.begin() as connection:
            await connection.execute(
                text("UPDATE record_operators SET status='DISABLED' WHERE id=:id"),
                {"id": operator_id},
            )
        assert client.get("/operator/status").status_code == 401
        async with governance_engine.begin() as connection:
            await connection.execute(
                text("UPDATE record_operators SET status='ACTIVE' WHERE id=:id"),
                {"id": operator_id},
            )
            await connection.execute(
                text(
                    "UPDATE operator_sessions SET revoked_at=:when WHERE operator_id=:id AND revoked_at IS NULL"
                ),
                {"id": operator_id, "when": datetime.now(UTC) + timedelta(seconds=1)},
            )
        assert client.get("/operator/status").status_code == 401


async def test_activity_projection_uses_only_governed_server_state(governance_engine):
    app, _ = await _app(governance_engine)
    repo, _, attr, config, _, _ = await seed(governance_engine)
    receipt = await reserve(repo, attr, config)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        response = client.get(
            "/operator/activity", params={"experiment_id": str(attr.experiment_id)}
        )
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["id"] == str(receipt.call_id)
        assert item["state"] == "queued"
        assert item["label"] == "Operation queued"
        assert "request" not in item and "attribution" not in item
        assert client.get("/operator/status").json()["counts"]["queued"] == 1
    await repo.dispatch(receipt.call_id)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        assert client.get("/operator/activity").json()["items"][0]["state"] == "running"
        assert client.get("/operator/status").json()["counts"]["running"] == 1


async def test_activity_stream_updates_and_stops_after_revocation(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    repo, _, attr, config, _, _ = await seed(governance_engine)
    receipt = await reserve(repo, attr, config)
    app.state.engine = governance_engine
    auth = AuthService(governance_engine, app.state.settings)
    app.state.auth = auth
    login = await auth.login("test-password")
    assert login is not None
    token, _ = login
    monkeypatch.setattr(operator_routes, "EVENT_POLL_SECONDS", 0.01)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "path": "/operator/activity/events",
            "headers": [(b"cookie", f"{COOKIE_NAME}={token}".encode())],
            "app": app,
        },
        receive,
    )
    response = await operator_routes.activity_events(request)
    stream = aiter(response.body_iterator)
    first = await asyncio.wait_for(anext(stream), timeout=1)
    first = first.decode() if isinstance(first, bytes) else first
    assert "event: activity" in first and '"state":"queued"' in first
    await repo.dispatch(receipt.call_id)
    second = await asyncio.wait_for(anext(stream), timeout=1)
    second = second.decode() if isinstance(second, bytes) else second
    assert "event: activity" in second and '"state":"running"' in second
    await auth.logout(token)
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(stream), timeout=1)
