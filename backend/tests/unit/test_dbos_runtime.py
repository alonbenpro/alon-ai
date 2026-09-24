from uuid import UUID

from alon_ai.config import Settings
from alon_ai.workflows.market_research import (
    DBOS_APPLICATION_NAME,
    DBOS_APPLICATION_VERSION,
    DBOS_SYSTEM_SCHEMA,
    build_dbos_config,
    inconclusive_supplement_workflow_id,
    market_research_outcome_workflow_id,
    market_research_workflow_id,
    material_pivot_decision_workflow_id,
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


def test_decision_workflow_ids_use_business_and_command_identity():
    operation_id = UUID("00000000-0000-0000-0000-000000000101")
    command_key = UUID("00000000-0000-0000-0000-000000000202")
    decision_id = UUID("00000000-0000-0000-0000-000000000303")

    assert market_research_outcome_workflow_id(operation_id, command_key) == (
        f"market-research-outcome:{operation_id}:{command_key}"
    )
    assert material_pivot_decision_workflow_id(operation_id, decision_id) == (
        f"material-pivot-decision:{operation_id}:{decision_id}"
    )
    assert inconclusive_supplement_workflow_id(operation_id, command_key) == (
        f"inconclusive-supplement:{operation_id}:{command_key}"
    )
