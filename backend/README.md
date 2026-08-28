# Alon AI backend

This package owns the FastAPI control API, PostgreSQL readiness boundary,
Alembic migrations, guarded `SendGateway` contracts, and the separately
runnable foundation worker. It does not implement Gmail OAuth, real sending,
or durable DBOS workflows yet.

Use Python 3.13 and uv 0.11.26. From `backend/`:

```sh
uv sync --locked --all-extras --dev
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest tests/unit -q
uv run alembic upgrade head
uv run uvicorn alon_ai.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

The migration and readiness integration test require
`ALON_AI_DATABASE_URL`. Keep `ALON_AI_OUTREACH_ENABLED=false`; providers may
only send through the deterministic gateway after the separate recovery spike.
