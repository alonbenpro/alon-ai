import pytest
from pydantic import ValidationError

from alon_ai.config import Settings


def test_safe_defaults_disable_outreach() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "Alon AI"
    assert settings.environment == "development"
    assert settings.outreach_enabled is False


def test_environment_variables_use_alon_ai_prefix(monkeypatch) -> None:
    monkeypatch.setenv("ALON_AI_LOG_LEVEL", "DEBUG")
    settings = Settings(_env_file=None)
    assert settings.log_level == "DEBUG"


def test_outreach_requires_complete_gmail_configuration() -> None:
    with pytest.raises(ValidationError, match="Gmail configuration"):
        Settings(outreach_enabled=True, _env_file=None)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("database_url", "sqlite:///bad"),
        ("database_url", "postgresql://user:pass@localhost/db"),
        ("database_url", "postgresql+psycopg://user:pass@localhost/"),
        ("database_url", "postgresql+psycopg://user:pass@localhost:bad/db"),
        ("dbos_system_database_url", "https://user:pass@example.com/db"),
        ("frontend_origin", "javascript:alert(1)"),
        ("frontend_origin", "https://user:pass@example.com"),
        ("frontend_origin", "https://example.com/path"),
        ("log_level", "LOUD"),
        ("provider_mode", "automatic"),
        ("generative_ai_provider", "another-provider"),
        ("openai_api_key_handle", "../escape"),
    ],
)
def test_invalid_configuration_fails_closed(field, value) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_settings_serialization_does_not_expose_credentials() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://alice:db-password@localhost/db",
        dbos_system_database_url="postgresql://alice:workflow-password@localhost/db",
        openai_api_key="api-secret-value",
        gmail_refresh_token="oauth-secret-value",
    )
    rendered = repr(settings) + settings.model_dump_json() + repr(settings.model_dump())
    for secret in (
        "db-password",
        "workflow-password",
        "api-secret-value",
        "oauth-secret-value",
    ):
        assert secret not in rendered


def test_validation_errors_never_include_secret_inputs() -> None:
    with pytest.raises(ValidationError) as raised:
        Settings(
            _env_file=None,
            database_url="bad://db-secret-value",
            openai_api_key="api-secret-value",
            gmail_refresh_token="oauth-secret-value",
            outreach_enabled=True,
        )
    rendered = str(raised.value) + raised.value.json() + repr(raised.value.errors())
    for secret in ("db-secret-value", "api-secret-value", "oauth-secret-value"):
        assert secret not in rendered


def production_values() -> dict[str, str]:
    return {
        "environment": "production",
        "database_url": "postgresql+psycopg://app:unique-pass@db.internal/app",
        "dbos_system_database_url": "postgresql://worker:unique-pass@db.internal/system",
        "frontend_origin": "https://app.example.org",
    }


@pytest.mark.parametrize(
    "missing", ["database_url", "dbos_system_database_url", "frontend_origin"]
)
def test_production_requires_explicit_configuration(missing, monkeypatch) -> None:
    monkeypatch.delenv("ALON_AI_" + missing.upper(), raising=False)
    values = production_values()
    del values[missing]
    with pytest.raises(ValidationError, match="Production requires explicit"):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("frontend_origin", "http://app.example.org"),
        ("database_url", "postgresql+psycopg://alon_ai:alon_ai@postgres:5432/alon_ai"),
        (
            "dbos_system_database_url",
            "postgresql://alon_ai:alon_ai@postgres:5432/alon_ai",
        ),
        ("openai_api_key", "raw-secret"),
        ("gmail_refresh_token", "raw-secret"),
    ],
)
def test_production_rejects_examples_and_raw_provider_credentials(field, value) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{**production_values(), field: value})


def test_production_accepts_handles_without_authorizing_provider_or_outreach() -> None:
    settings = Settings(
        _env_file=None, openai_api_key_handle="openai-main", **production_values()
    )
    assert settings.provider_mode == "disabled"
    assert not settings.outreach_enabled


def test_percent_encoded_database_credentials_reach_engine_unmodified() -> None:
    from alon_ai.db.engine import create_engine

    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://alice:p%40ss%25word@localhost/db",
    )
    engine = create_engine(settings)
    assert engine.url.password == "p@ss%word"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://alice:bad%ZZ@localhost/db",
        "postgresql+psycopg://alice:pass@localhost/db#fragment",
        "postgresql+psycopg://alice:pass@localhost/db?password=override",
    ],
)
def test_database_urls_reject_malformed_escapes_fragments_and_credential_overrides(
    url,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=url)


def test_after_validator_errors_redact_complete_input_dictionary() -> None:
    with pytest.raises(ValidationError) as raised:
        Settings(
            _env_file=None,
            outreach_enabled=True,
            gmail_refresh_token="private-refresh-value",
        )
    assert "private-refresh-value" not in str(raised.value)
    assert "private-refresh-value" not in raised.value.json()
    assert "private-refresh-value" not in repr(raised.value.errors())
