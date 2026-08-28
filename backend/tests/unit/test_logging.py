import json
import logging
import re
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.api.app import create_app
from alon_ai.config import Settings
from alon_ai.db.engine import DatabaseHealthChecker
from alon_ai.logging import configure_logging


def production_settings() -> Settings:
    return Settings(environment="production", _env_file=None)


def emitted_json(stderr: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in stderr.splitlines() if line.strip()]


def test_production_request_log_is_structured_correlated_and_sanitized(
    capsys,
) -> None:
    app = create_app(production_settings())

    with TestClient(app) as client:
        response = client.get(
            "/health/live?token=do-not-log",
            headers={
                "Authorization": "Bearer do-not-log",
                "X-Request-ID": "request-safe_123",
            },
        )
        logging.getLogger("uvicorn.access").info(
            '127.0.0.1 - "GET /health/live?token=do-not-log HTTP/1.1" 200'
        )

    records = emitted_json(capsys.readouterr().err)
    request_records = [
        record for record in records if record.get("event") == "http_request_completed"
    ]

    assert response.headers["x-request-id"] == "request-safe_123"
    assert len(request_records) == 1
    assert request_records[0] == {
        **request_records[0],
        "duration_ms": request_records[0]["duration_ms"],
        "event": "http_request_completed",
        "level": "info",
        "method": "GET",
        "path": "/health/live",
        "request_id": "request-safe_123",
        "service": "api",
        "status": 200,
    }
    assert isinstance(request_records[0]["duration_ms"], int)
    assert request_records[0]["duration_ms"] >= 0
    serialized = "\n".join(json.dumps(record) for record in records)
    assert "do-not-log" not in serialized
    assert "uvicorn.access" not in serialized


def test_invalid_request_id_is_replaced_and_returned(capsys) -> None:
    app = create_app(production_settings())

    with TestClient(app) as client:
        response = client.get(
            "/health/live",
            headers={"X-Request-ID": "../../ unsafe request id"},
        )

    records = emitted_json(capsys.readouterr().err)
    request_record = next(
        record for record in records if record.get("event") == "http_request_completed"
    )
    response_request_id = response.headers["x-request-id"]

    assert re.fullmatch(r"[0-9a-f]{32}", response_request_id)
    assert request_record["request_id"] == response_request_id
    assert "unsafe request id" not in json.dumps(request_record)


def test_production_exception_request_log_does_not_expose_exception(capsys) -> None:
    app = create_app(production_settings())

    async def fail() -> None:
        raise RuntimeError("credential=do-not-log postgresql://do-not-log")

    app.add_api_route("/failure", fail)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/failure?secret=do-not-log")

    try:
        raise RuntimeError("credential=do-not-log postgresql://do-not-log")
    except RuntimeError:
        logging.getLogger("uvicorn.error").exception("ASGI request failed")

    records = emitted_json(capsys.readouterr().err)
    request_record = next(
        record for record in records if record.get("event") == "http_request_completed"
    )

    assert response.status_code == 500
    assert request_record["status"] == 500
    assert request_record["path"] == "/failure"
    serialized = json.dumps(records)
    assert "do-not-log" not in serialized
    assert "RuntimeError" not in serialized


class FailingConnectionContext:
    async def __aenter__(self) -> None:
        raise OperationalError(
            "SELECT 1",
            {},
            RuntimeError("password=do-not-log postgresql://do-not-log"),
        )

    async def __aexit__(self, *args: object) -> None:
        return None


class FailingEngine:
    def connect(self) -> FailingConnectionContext:
        return FailingConnectionContext()


async def test_readiness_failure_log_exposes_only_error_type(capsys) -> None:
    configure_logging(production_settings())
    checker = DatabaseHealthChecker(cast(AsyncEngine, FailingEngine()))

    assert await checker() is False

    records = emitted_json(capsys.readouterr().err)
    readiness_record = next(
        record
        for record in records
        if record.get("event") == "database_readiness_failed"
    )

    assert readiness_record["service"] == "api"
    assert readiness_record["error_type"] == "OperationalError"
    assert "error" not in readiness_record
    assert "exception" not in readiness_record
    assert "do-not-log" not in json.dumps(readiness_record)
