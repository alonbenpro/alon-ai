import re
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    EmailStr,
    ModelWrapValidatorHandler,
    SecretStr,
    StringConstraints,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import InitErrorDetails
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

SecretHandle = Annotated[
    str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")
]


_SAFE_VALIDATION_MESSAGES = frozenset(
    {
        "A valid PostgreSQL URL with the required driver and database is required",
        "A valid HTTP(S) frontend origin without credentials is required",
        "Production requires explicit database URLs and frontend origin",
        "Production requires non-example database credentials",
        "Production requires an HTTPS frontend origin",
        "Production provider credentials require secret handles",
        "Gmail configuration is required when outreach is enabled",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ALON_AI_",
        extra="ignore",
        hide_input_in_errors=True,
        frozen=True,
    )

    app_name: str = "Alon AI"
    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://alon_ai:alon_ai@localhost:5432/alon_ai"
    )
    dbos_system_database_url: SecretStr = SecretStr(
        "postgresql://alon_ai:alon_ai@localhost:5432/alon_ai"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    outreach_enabled: bool = False
    frontend_origin: str = "http://localhost:3000"
    # Configuration selects an execution mode; it never grants call/effect authority.
    provider_mode: Literal["disabled", "fake", "live"] = "disabled"
    generative_ai_provider: Literal["openai"] = "openai"
    openai_api_key_handle: SecretHandle | None = None
    brave_api_key_handle: SecretHandle | None = None
    firecrawl_api_key_handle: SecretHandle | None = None
    hunter_api_key_handle: SecretHandle | None = None
    gmail_client_id_handle: SecretHandle | None = None
    gmail_client_secret_handle: SecretHandle | None = None
    gmail_refresh_token_handle: SecretHandle | None = None
    # Development compatibility only. Production uses the consumer-bound SecretStore.
    openai_api_key: SecretStr | None = None
    brave_api_key: SecretStr | None = None
    firecrawl_api_key: SecretStr | None = None
    hunter_api_key: SecretStr | None = None
    gmail_client_id: SecretStr | None = None
    gmail_client_secret: SecretStr | None = None
    gmail_refresh_token: SecretStr | None = None
    gmail_sender_email: EmailStr | None = None

    if TYPE_CHECKING:

        def __init__(self, _env_file: str | None = None, **values: Any) -> None: ...

    @field_validator("database_url", "dbos_system_database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        try:
            raw = value.get_secret_value()
            url = make_url(raw)
            parsed = urlsplit(raw)
            expected = (
                "postgresql+psycopg"
                if info.field_name == "database_url"
                else "postgresql"
            )
            if (
                url.drivername != expected
                or bool(parsed.fragment)
                or bool(re.search(r"%(?![0-9a-fA-F]{2})", raw))
                or bool(
                    {"password", "user", "username", "dbname", "database"}
                    & url.query.keys()
                )
                or not url.host
                or not url.database
                or not url.database.strip()
                or any(char.isspace() for char in raw)
                or (url.port is not None and not 1 <= url.port <= 65535)
            ):
                raise ValueError
        except (ValueError, TypeError, ArgumentError):
            raise ValueError(
                "A valid PostgreSQL URL with the required driver and database is required"
            ) from None
        return value

    @field_validator("frontend_origin")
    @classmethod
    def validate_frontend_origin(cls, value: str) -> str:
        try:
            url = urlsplit(value)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.path not in {"", "/"}
                or url.query
                or url.fragment
                or any(char.isspace() for char in value)
                or (url.port is not None and not 1 <= url.port <= 65535)
            ):
                raise ValueError
        except ValueError:
            raise ValueError(
                "A valid HTTP(S) frontend origin without credentials is required"
            ) from None
        return value.rstrip("/")

    @model_validator(mode="after")
    def require_safe_production_settings(self) -> Self:
        if self.environment != "production":
            return self
        if (
            not {"database_url", "dbos_system_database_url", "frontend_origin"}
            <= self.model_fields_set
        ):
            raise ValueError(
                "Production requires explicit database URLs and frontend origin"
            )
        for value in (self.database_url, self.dbos_system_database_url):
            url = make_url(value.get_secret_value())
            if (
                not url.username
                or not url.password
                or url.password.lower()
                in {
                    "alon_ai",
                    "password",
                    "postgres",
                    "example",
                    "changeme",
                }
            ):
                raise ValueError("Production requires non-example database credentials")
        if not self.frontend_origin.startswith("https://"):
            raise ValueError("Production requires an HTTPS frontend origin")
        for name in type(self).model_fields:
            if name not in {"database_url", "dbos_system_database_url"} and isinstance(
                getattr(self, name), SecretStr
            ):
                raise ValueError(
                    "Production provider credentials require secret handles"
                )
        return self

    @model_validator(mode="after")
    def require_gmail_when_outreach_is_enabled(self) -> Self:
        if self.environment == "production":
            gmail_values = (
                self.gmail_client_id_handle,
                self.gmail_client_secret_handle,
                self.gmail_refresh_token_handle,
                self.gmail_sender_email,
            )
        else:
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

    @model_validator(mode="wrap")
    @classmethod
    def redact_validation_inputs(
        cls, values: Any, handler: ModelWrapValidatorHandler[Self]
    ) -> Self:
        # hide_input_in_errors covers str(error), but not errors()/json().
        try:
            return handler(values)
        except ValidationError as error:
            safe_errors: list[InitErrorDetails] = []
            for detail in error.errors(include_url=False):
                message = detail["msg"].removeprefix("Value error, ")
                safe_message = (
                    message
                    if message in _SAFE_VALIDATION_MESSAGES
                    else "Invalid configuration value"
                )
                safe_errors.append(
                    InitErrorDetails(
                        type="value_error",
                        loc=detail["loc"],
                        input="[REDACTED]",
                        ctx={"error": ValueError(safe_message)},
                    )
                )
            raise ValidationError.from_exception_data(
                cls.__name__, safe_errors, hide_input=True
            ) from None


@lru_cache
def get_settings() -> Settings:
    return Settings()
