import shlex
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


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


def test_backend_image_contains_alembic_runtime_contract() -> None:
    copied_sources = docker_context_sources()

    assert "alembic.ini" in copied_sources
    assert "alembic" in copied_sources
    assert (BACKEND_ROOT / "alembic.ini").is_file()
    assert (BACKEND_ROOT / "alembic" / "env.py").is_file()
