from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal

from pydantic import EmailStr, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ALON_AI_",
        extra="ignore",
    )

    app_name: str = "Alon AI"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://alon_ai:alon_ai@localhost:5432/alon_ai"
    log_level: str = "INFO"
    outreach_enabled: bool = False
    frontend_origin: str = "http://localhost:3000"
    dbos_system_database_url: str = (
        "postgresql://alon_ai:alon_ai@localhost:5432/alon_ai"
    )
    gmail_client_id: SecretStr | None = None
    gmail_client_secret: SecretStr | None = None
    gmail_refresh_token: SecretStr | None = None
    gmail_sender_email: EmailStr | None = None

    if TYPE_CHECKING:

        def __init__(self, _env_file: str | None = None, **values: Any) -> None: ...

    @model_validator(mode="after")
    def require_gmail_when_outreach_is_enabled(self) -> "Settings":
        gmail_values = (
            self.gmail_client_id.get_secret_value() if self.gmail_client_id else "",
            self.gmail_client_secret.get_secret_value()
            if self.gmail_client_secret
            else "",
            self.gmail_refresh_token.get_secret_value()
            if self.gmail_refresh_token
            else "",
            str(self.gmail_sender_email or ""),
        )
        if self.outreach_enabled and not all(gmail_values):
            raise ValueError("Gmail configuration is required when outreach is enabled")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
