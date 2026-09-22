# Alon AI backend

This package owns the FastAPI control API, PostgreSQL readiness boundary,
Alembic migrations, guarded `SendGateway` contracts, and the separately
runnable DBOS worker. DBOS is only the durable control plane; PostgreSQL
commands remain authoritative for business state and effects. The current
durable workflow covers only `IDEA_REFINEMENT` to `MARKET_RESEARCH`. It does
not implement Gmail OAuth, real sending, providers, agents, or campaigns.

Use Python 3.13 and uv 0.11.26. From `backend/`:

```sh
uv sync --locked --all-extras --dev
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest tests/unit -q
uv run alembic upgrade head
uv run dbos migrate --sys-db-url "$ALON_AI_DBOS_SYSTEM_DATABASE_URL" --schema dbos
uv run uvicorn alon_ai.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Run the DBOS migration explicitly during setup or release. Worker startup uses
`run_migrations=False`; it verifies the `dbos` system schema and exits when the
schema is missing or behind instead of changing it silently.

The migration and readiness integration test require
`ALON_AI_DATABASE_URL`. Keep `ALON_AI_OUTREACH_ENABLED=false`; providers may
only send through the deterministic gateway after the separate recovery spike.
