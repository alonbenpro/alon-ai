"""Static guardrails for the backend ownership boundary."""

import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[3] / "src" / "alon_ai"


def _import_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _violations(module: str, source: str) -> list[str]:
    tree = ast.parse(source)
    imports = _import_names(tree)
    errors = []
    if module.startswith("services."):
        if any(name == "fastapi" or name.startswith("fastapi.") for name in imports):
            errors.append("FastAPI in service")
        if any(
            name.startswith("alon_ai.api.")
            and not name.startswith("alon_ai.api.schemas.")
            for name in imports
        ):
            errors.append("service imports API implementation")
        if any(
            name.startswith("alon_ai.workflows.")
            and not name.startswith("alon_ai.workflows.schemas.")
            for name in imports
        ):
            errors.append("service imports concrete workflow")
        if any(
            (name == "sqlalchemy" or name.startswith("sqlalchemy."))
            and name != "sqlalchemy.ext.asyncio"
            for name in imports
        ):
            errors.append("SQL query construction in service")
        if any(name.startswith("alon_ai.db.tables") for name in imports):
            errors.append("service imports table definitions")
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "execute"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"connection", "conn", "session"}
            for node in ast.walk(tree)
        ):
            errors.append("service executes SQL directly")
    if (
        module.startswith(("api.routes.", "agents.", "workflows."))
        or module == "api.auth"
    ):
        if any(
            name == "sqlalchemy" or name.startswith("sqlalchemy.") for name in imports
        ):
            errors.append("SQLAlchemy in route, agent, or workflow")
        if any(
            name.startswith(("alon_ai.db.tables", "alon_ai.db.repositories"))
            for name in imports
        ):
            errors.append("direct database dependency in route, agent, or workflow")
    if module.startswith("integrations.") and any(
        name.startswith("alon_ai.db.") for name in imports
    ):
        errors.append("integration owns persistence or governance setup")
    if module.startswith(("agents.", "workflows.")):
        if any(name == "fastapi" or name.startswith("fastapi.") for name in imports):
            errors.append("HTTP framework in agent or workflow")
        if any(name.startswith("alon_ai.api.") for name in imports):
            errors.append("agent or workflow imports API")
    return errors


def test_canonical_boundaries() -> None:
    files = sorted(SOURCE.rglob("*.py"))
    assert len(files) >= 80, "backend discovery must not pass vacuously"
    failures = []
    for path in files:
        module = ".".join(path.relative_to(SOURCE).with_suffix("").parts)
        for error in _violations(module, path.read_text(encoding="utf-8")):
            failures.append(f"{module}: {error}")
    assert not failures, "\n".join(failures)


def test_checker_rejects_deliberate_boundary_violations() -> None:
    cases = [
        ("services.experiments", "from fastapi import Request"),
        ("services.experiments", "from sqlalchemy import select"),
        ("services.experiments", "await connection.execute(query)"),
        ("services.experiments", "from alon_ai.api.routes import experiments"),
        (
            "services.experiments",
            "from alon_ai.workflows.market_research import launch",
        ),
        ("api.routes.experiments", "from sqlalchemy import select"),
        ("agents.runtime", "from alon_ai.db.repositories.records import Records"),
        ("workflows.market_research", "from alon_ai.api.app import app"),
        (
            "integrations.live_idea",
            "from alon_ai.db.repositories.accounting import GovernanceProvisioner",
        ),
    ]
    for module, source in cases:
        assert _violations(module, source), (module, source)
