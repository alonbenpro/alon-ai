import shlex
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"


def docker_context_sources() -> set[str]:
    sources: set[str] = set()
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")
    for raw_line in dockerfile.splitlines():
        line = raw_line.strip()
        if not line.startswith("COPY "):
            continue
        tokens = shlex.split(line)
        if any(token.startswith("--from=") for token in tokens):
            continue
        sources.update(token for token in tokens[1:-1] if not token.startswith("--"))
    return sources


def docker_environment(dockerfile_path: Path) -> dict[str, str]:
    environment: dict[str, str] = {}
    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    for raw_line in dockerfile.splitlines():
        line = raw_line.strip()
        if not line.startswith("ENV "):
            continue
        for assignment in shlex.split(line)[1:]:
            name, value = assignment.split("=", maxsplit=1)
            environment[name] = value
    return environment


def test_backend_image_contains_alembic_runtime_contract() -> None:
    copied_sources = docker_context_sources()

    assert "alembic.ini" in copied_sources
    assert "alembic" in copied_sources
    assert (BACKEND_ROOT / "alembic.ini").is_file()
    assert (BACKEND_ROOT / "alembic" / "env.py").is_file()


def test_frontend_image_binds_standalone_server_to_all_container_interfaces() -> None:
    environment = docker_environment(REPOSITORY_ROOT / "frontend" / "Dockerfile")

    assert environment["HOSTNAME"] == "0.0.0.0"
    assert environment["PORT"] == "3000"
