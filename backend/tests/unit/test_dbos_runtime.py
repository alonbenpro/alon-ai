from uuid import UUID

from alon_ai.config import Settings
from alon_ai.workflows.market_research import (
    DBOS_APPLICATION_NAME,
    DBOS_APPLICATION_VERSION,
    DBOS_SYSTEM_SCHEMA,
    build_dbos_config,
    market_research_workflow_id,
)


def test_dbos_runtime_configuration_is_explicit_and_never_migrates_on_startup():
    settings = Settings(
        dbos_system_database_url="postgresql://worker:secret@localhost/alon_ai"
    )

    config = build_dbos_config(settings, executor_id="l04-test-executor")

    assert config == {
        "name": DBOS_APPLICATION_NAME,
        "system_database_url": "postgresql://worker:secret@localhost/alon_ai",
        "application_version": DBOS_APPLICATION_VERSION,
        "executor_id": "l04-test-executor",
        "dbos_system_schema": DBOS_SYSTEM_SCHEMA,
        "run_migrations": False,
        "run_admin_server": False,
        "enable_otlp": False,
    }
    assert "application_database_url" not in config
    assert "database_url" not in config


def test_market_research_workflow_id_is_deterministic_and_request_bound():
    cycle_id = UUID("00000000-0000-0000-0000-000000000111")

    first = market_research_workflow_id(cycle_id, "a" * 64)

    assert first == market_research_workflow_id(cycle_id, "a" * 64)
    assert first != market_research_workflow_id(cycle_id, "b" * 64)
    assert str(cycle_id) in first
    assert "a" * 64 in first
