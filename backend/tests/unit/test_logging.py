import json
import logging
import re
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.api.app import create_app
from alon_ai.api.auth import OperatorSession
from alon_ai.config import Settings
from alon_ai.db.engine import DatabaseHealthChecker
from alon_ai.logging import configure_logging


def production_settings() -> Settings:
    return Settings(
        environment="production",
        database_url="postgresql+psycopg://app:unique-pass@db.internal/app",
        dbos_system_database_url="postgresql://worker:unique-pass@db.internal/system",
        frontend_origin="https://app.example.org",
        operator_auth_subject="operator@example.org",
        operator_password_hash=SecretStr("test-only-verifier"),
        session_signing_key=SecretStr("test-only-signing-key-with-32-bytes"),
        _env_file=None,
    )


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
        app.state.auth.resolve = AsyncMock(
            return_value=OperatorSession(id=uuid4(), display_name="Test operator")
        )
        client.cookies.set("alon_ai_session", "test-cookie")
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


def test_nested_secrets_provider_payload_and_foreign_messages_are_redacted(
    capsys,
) -> None:
    import structlog

    settings = Settings(
        _env_file=None,
        environment="test",
        openai_api_key="configured-api-value",
        gmail_refresh_token="configured-oauth-value",
    )
    configure_logging(settings)
    structlog.get_logger("test").warning(
        "safe_event %s",
        "configured-api-value",
        request_id="safe-correlation",
        nested={
            "items": [
                {"api_key": "unconfigured-key-value"},
                {"message": "configured-oauth-value"},
            ]
        },
        provider_output={"data": "raw-provider-value"},
        error=RuntimeError("unconfigured-exception-value"),
    )
    logging.getLogger("foreign").warning(
        "connecting %s; key=%s",
        "postgresql+psycopg://user:unconfigured-password@host/db",
        "configured-api-value",
    )
    rendered = capsys.readouterr().err
    for value in (
        "configured-api-value",
        "configured-oauth-value",
        "unconfigured-key-value",
        "raw-provider-value",
        "unconfigured-exception-value",
        "unconfigured-password",
    ):
        assert value not in rendered
    assert "safe-correlation" in rendered


def test_unmatched_and_parameterized_request_paths_do_not_log_user_values(
    capsys,
) -> None:
    app = create_app(production_settings())

    async def item(item_id: str) -> dict[str, str]:
        return {"id": item_id}

    app.add_api_route("/items/{item_id}", item)
    with TestClient(app) as client:
        app.state.auth.resolve = AsyncMock(
            return_value=OperatorSession(id=uuid4(), display_name="Test operator")
        )
        client.cookies.set("alon_ai_session", "test-cookie")
        client.get("/unrecognized/private-path-value")
        client.get("/items/private-item-value")
    rendered = capsys.readouterr().err
    assert "private-path-value" not in rendered
    assert "private-item-value" not in rendered
    assert '"path": "/items/{item_id}"' in rendered


def test_foreign_traceback_and_stack_are_removed_after_formatting(capsys) -> None:
    configure_logging(production_settings())
    try:
        raise RuntimeError("private-exception-value")
    except RuntimeError:
        logging.getLogger("foreign").exception(
            "failed %s", "https://user:private-url-value@example.org", stack_info=True
        )
    rendered = capsys.readouterr().err
    assert "private-exception-value" not in rendered
    assert "private-url-value" not in rendered
    assert "Stack (most recent call last)" not in rendered


def test_configured_secret_cannot_leak_via_valid_request_id(capsys) -> None:
    settings = production_settings()
    # A database password is valid request-id syntax; it must still be redacted.
    app = create_app(settings)
    with TestClient(app) as client:
        client.get("/health/live", headers={"X-Request-ID": "unique-pass"})
    assert "unique-pass" not in capsys.readouterr().err


class SensitiveLogObject:
    def __str__(self) -> str:
        return "unlisted-object-value-123"

    def __repr__(self) -> str:
        return "unlisted-object-value-123"


class SensitiveLogInteger(int):
    def __repr__(self) -> str:
        return "unlisted-object-value-123"


def test_unknown_objects_are_sanitized_before_stdlib_interpolation(capsys) -> None:
    configure_logging(production_settings())
    logger = logging.getLogger("foreign")
    logger.warning("operation failed: %s", RuntimeError("sensitive-value-123"))
    logger.warning("operation failed: %r", SensitiveLogObject())
    logger.warning("operation failed: %(failure)s", {"failure": SensitiveLogObject()})
    logger.warning("operation failed: %s", {"items": [SensitiveLogObject()]})
    logger.warning(SensitiveLogObject())
    logger.warning("subclass=%r", SensitiveLogInteger(503))
    logger.warning("bad numeric argument=%d", SensitiveLogObject())
    logger.warning("safe status=%d label=%s", 503, "retryable")
    rendered = capsys.readouterr().err
    assert "sensitive-value-123" not in rendered
    assert "unlisted-object-value-123" not in rendered
    records = emitted_json(rendered)
    assert len(records) == 8
    assert records[-1]["event"] == "safe status=503 label=retryable"


def test_unknown_objects_are_sanitized_before_structlog_interpolation(capsys) -> None:
    import structlog

    configure_logging(production_settings())
    logger = structlog.get_logger("structured")
    logger.warning("operation failed: %s", RuntimeError("sensitive-value-123"))
    logger.warning("operation failed: %r", SensitiveLogObject())
    logger.warning("operation failed: %(failure)s", {"failure": SensitiveLogObject()})
    logger.warning("operation failed: %s", {"items": [SensitiveLogObject()]})
    logger.warning(SensitiveLogObject())
    logger.warning("subclass=%r", SensitiveLogInteger(503))
    logger.warning("bad numeric argument=%d", SensitiveLogObject())
    logger.warning(
        "safe status=%d label=%s", 503, "retryable", request_id="safe-correlation"
    )
    rendered = capsys.readouterr().err
    assert "sensitive-value-123" not in rendered
    assert "unlisted-object-value-123" not in rendered
    records = emitted_json(rendered)
    assert len(records) == 8
    assert records[-1]["event"] == "safe status=503 label=retryable"
    assert records[-1]["request_id"] == "safe-correlation"


def test_percent_encoded_credential_query_keys_are_redacted_for_all_loggers(
    capsys,
) -> None:
    import structlog

    configure_logging(production_settings())
    url = "https://example.org?api%5Fkey=unlisted-value-123"
    logging.getLogger("foreign").warning("request failed: %s", url)
    structlog.get_logger("structured").warning("request failed: %s", url)
    rendered = capsys.readouterr().err
    assert "unlisted-value-123" not in rendered
    assert len(emitted_json(rendered)) == 2
