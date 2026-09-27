"""DBOS worker configuration with immutable application identity."""

from dbos import DBOS, DBOSConfig

from alon_ai.config import Settings
from alon_ai.workflows.schemas.runtime import (
    DBOS_APPLICATION_NAME,
    DBOS_APPLICATION_VERSION,
    DBOS_SYSTEM_SCHEMA,
)


def build_dbos_config(
    settings: Settings,
    *,
    executor_id: str,
    application_version: str = DBOS_APPLICATION_VERSION,
) -> DBOSConfig:
    """Build production-style DBOS configuration without schema mutation authority."""
    return DBOSConfig(
        name=DBOS_APPLICATION_NAME,
        system_database_url=settings.dbos_system_database_url.get_secret_value(),
        application_version=application_version,
        executor_id=executor_id,
        dbos_system_schema=DBOS_SYSTEM_SCHEMA,
        run_migrations=False,
        run_admin_server=False,
        enable_otlp=False,
    )


def configure_dbos(
    settings: Settings,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
    executor_id: str,
) -> None:
    DBOS(
        config=build_dbos_config(
            settings, executor_id=executor_id, application_version=application_version
        )
    )
