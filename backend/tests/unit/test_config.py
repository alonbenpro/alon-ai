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
