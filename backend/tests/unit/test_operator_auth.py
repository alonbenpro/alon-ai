import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from alon_ai.api.app import create_app
from alon_ai.api.auth import _password_matches, hash_password
from alon_ai.api.routes.operator import _STATES
from alon_ai.config import Settings


def test_scrypt_verifier_is_salted_and_rejects_changes() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first != second
    assert _password_matches("correct horse battery staple", first)
    assert not _password_matches("wrong", first)
    assert not _password_matches("correct horse battery staple", "scrypt$bad")


def test_activity_states_are_truthful_terminal_and_uncertain_projections() -> None:
    assert _STATES["RESERVED"] == ("queued", "Operation queued")
    assert _STATES["DISPATCHED"] == ("running", "Operation running")
    assert _STATES["FINAL"] == ("completed", "Operation finished")
    assert _STATES["RECONCILING"] == ("blocked", "Operation requires reconciliation")
    assert _STATES["RELEASED"] == ("blocked", "Operation stopped")


def test_production_worker_rejects_missing_or_weak_session_credentials() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+psycopg://app:unique-pass@localhost/app",
        dbos_system_database_url="postgresql://worker:unique-pass@localhost/system",
        frontend_origin="https://app.example.org",
    )
    with (
        pytest.raises(RuntimeError, match="Operator authentication is not configured"),
        TestClient(create_app(settings)),
    ):
        pass
    weak = settings.model_copy(
        update={
            "operator_auth_subject": "alon@example.test",
            "operator_password_hash": SecretStr(hash_password("password")),
            "session_signing_key": SecretStr("short"),
        }
    )
    with (
        pytest.raises(RuntimeError, match="Operator authentication is not configured"),
        TestClient(create_app(weak)),
    ):
        pass
