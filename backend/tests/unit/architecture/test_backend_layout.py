"""Checked R00A-to-R00B module inventory and canonical startup wiring."""

import ast
import hashlib
import importlib
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[3] / "src" / "alon_ai"
FIXTURE = Path(__file__).with_name("backend_layout.json")


BASELINE_MODULE_DIGEST = (
    "9e3521b3382f6660bf58c7927974f1cbfd1284cb9602bb1bd61ab8412f73b2d3"
)


def _inventory_error(modules: dict[str, dict]) -> str | None:
    if len(modules) != 85:
        return "R00A inventory must contain exactly 85 modules"
    digest = hashlib.sha256("\n".join(sorted(modules)).encode()).hexdigest()
    if digest != BASELINE_MODULE_DIGEST:
        return "R00A module names differ from the verified baseline"
    return None


def _modules() -> dict[str, dict]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["base_sha"] == "ca957f1cf4aa9bb2c2ce680335d16c225c7939c1"
    modules = data["modules"]
    assert _inventory_error(modules) is None, _inventory_error(modules)
    return modules


def _module_path(name: str) -> Path:
    parts = name.split(".")
    assert parts[0] == "alon_ai"
    candidate = SOURCE.joinpath(*parts[1:])
    if candidate.is_dir():
        return candidate / "__init__.py"
    return candidate.with_suffix(".py")


def test_every_baseline_module_has_a_canonical_owner_and_coverage() -> None:
    modules = _modules()
    for old, record in modules.items():
        assert record["disposition"] in {"moved", "split", "retained", "shim"}, old
        owners = record["owners"]
        assert owners and all(owner.startswith("alon_ai.") for owner in owners), old
        assert all(_module_path(owner).is_file() for owner in owners), (old, owners)
        assert isinstance(record["callers"], list), old
        assert isinstance(record["tests"], list), old
        if record["disposition"] == "shim":
            assert (
                record["historical_consumer"]
                and record["removal_condition"]
                and record["shim_test"]
            ), old
            assert _module_path(old).is_file(), old
        elif old not in owners:
            assert not _module_path(old).exists(), (
                f"obsolete implementation remains: {old}"
            )


def test_no_production_imports_obsolete_paths() -> None:
    obsolete = {
        old
        for old, row in _modules().items()
        if row["disposition"] in {"moved", "split", "shim"}
        and old not in row["owners"]
        and not old.endswith(".__init__")
    }
    failures = []
    for path in SOURCE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports = [node.module]
            else:
                continue
            for name in imports:
                if name in obsolete:
                    failures.append(f"{path.relative_to(SOURCE)} imports {name}")
    assert not failures, "\n".join(failures)


def test_canonical_table_metadata_and_worker_startup() -> None:
    table_package = importlib.import_module("alon_ai.db.tables")
    metadata = table_package.metadata
    intake_tables = {
        "record_intakes",
        "record_intake_commands",
        "record_agent_runs",
        "record_agent_run_steps",
    }
    assert intake_tables <= metadata.tables.keys()
    assert len(metadata.tables) == 144, "L07 tables plus intake and Idea run tables"
    # Preserve the accepted R00B/L07 baseline digest; enumerate additions explicitly.
    table_names = "\n".join(sorted(metadata.tables.keys() - intake_tables))
    assert (
        hashlib.sha256(table_names.encode()).hexdigest()
        == "8d37e1f6691858972b1a9b9b50fa3910cc2b37670a829169c07e108b506defd0"
    )
    worker = importlib.import_module("alon_ai.worker.main")
    assert worker.DBOS_EXECUTOR_ID == "alon-ai-worker"
    assert worker.DBOS_APPLICATION_NAME == "alon-ai-worker"
    assert worker.DBOS_APPLICATION_VERSION == "l04-market-research-v1"


def test_checker_rejects_incomplete_inventory() -> None:
    valid = _modules()
    missing = dict(valid)
    missing.pop(next(iter(missing)))
    assert _inventory_error(missing) == "R00A inventory must contain exactly 85 modules"
    substituted = dict(valid)
    name = next(iter(substituted))
    substituted["alon_ai.fake_extra"] = substituted.pop(name)
    assert (
        _inventory_error(substituted)
        == "R00A module names differ from the verified baseline"
    )


def test_cli_startup_and_migration_entrypoints_are_mapped() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    entrypoints = data["entrypoints"]
    assert len(entrypoints) == 8
    repository = SOURCE.parents[2]
    for entry in entrypoints:
        assert (repository / entry["path"]).is_file(), entry
        assert (repository / entry["test"]).is_file(), entry
    local_dev = (repository / "scripts/local-dev.sh").read_text(encoding="utf-8")
    assert "python -m alon_ai.services.combined_idea_provision" in local_dev
    alembic = (repository / "backend/alembic/env.py").read_text(encoding="utf-8")
    assert "alon_ai.db.tables" in alembic


def test_operator_provisioning_cli_has_no_sql() -> None:
    script = SOURCE.parents[2] / "scripts" / "provision_operator.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        name == "sqlalchemy" or name.startswith("sqlalchemy.") for name in imports
    )
    assert "alon_ai.services.operator_provisioning" in imports


def test_experiment_idea_and_research_use_cases_have_focused_owners() -> None:
    def functions(module: str) -> set[str]:
        tree = ast.parse(_module_path(module).read_text(encoding="utf-8"))
        return {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }

    experiment_names = functions("alon_ai.services.experiments")
    idea_names = functions("alon_ai.services.ideas")
    research_names = functions("alon_ai.services.research")
    assert {
        "create_experiment",
        "get_experiment",
        "experiment_runtime_status",
    } <= experiment_names
    idea_cases = {
        "discover_experiment",
        "select_experiment_candidate",
        "refine_experiment",
        "accept_experiment_idea",
    }
    assert idea_cases <= idea_names
    assert idea_cases.isdisjoint(experiment_names)
    assert "start_return_refinement" in research_names
    assert "start_return_refinement" not in experiment_names


def test_all_registered_handlers_have_checked_owner_dispositions() -> None:
    from typing import Annotated, get_args, get_origin, get_type_hints

    from fastapi.routing import APIRoute

    from alon_ai.api.app import create_app

    expected = [
        {key: value for key, value in row.items() if key != "delegation"}
        for row in json.loads(FIXTURE.read_text(encoding="utf-8"))["handlers"]
    ]
    assert len(expected) == 29
    actual = []
    for included in create_app().routes:
        router = getattr(included, "original_router", None)
        if router is None:
            continue
        context = getattr(included, "include_context", None)
        assert context is not None
        prefix = context.prefix
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            handler = route.endpoint
            hints = get_type_hints(handler, include_extras=True)
            service_hint = hints["service"]
            assert get_origin(service_hint) is Annotated
            service_type = get_args(service_hint)[0]
            assert route.methods is not None
            for method in route.methods:
                actual.append(
                    {
                        "method": method,
                        "path": prefix + route.path,
                        "handler": handler.__module__ + "." + handler.__name__,
                        "owner": service_type.__module__,
                        "test": "backend/tests/unit/architecture/test_api_routes.py",
                    }
                )
    assert sorted(actual, key=lambda row: (row["path"], row["method"])) == sorted(
        expected, key=lambda row: (row["path"], row["method"])
    )
