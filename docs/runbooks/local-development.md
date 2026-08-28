# Local development runbook

This runbook is for the repository foundation. It does not deploy anything and it does not authorize production outreach.

## Prerequisites

- Python 3.13 and [uv 0.11.26](https://docs.astral.sh/uv/)
- Node.js 24 and npm
- PostgreSQL 18 for host-based integration testing, or Docker Engine with Docker Compose for the local stack

## Setup and checks

From the repository root:

```sh
make setup
make generate
make lint
make typecheck
make test
make build
```

`make setup` uses the committed Python and npm lockfiles. `make generate` exports FastAPI's OpenAPI document and regenerates `frontend/src/lib/api/schema.d.ts`; generated changes are deliberate review items. Check accidental drift with:

```sh
git diff --exit-code -- frontend/openapi.json frontend/src/lib/api/schema.d.ts
```

## Host PostgreSQL and backend migration

The safe local example values are in `.env.example`. They point at a database and role both named `alon_ai` on port 5432. Do not put real provider credentials in that file.

For a local PostgreSQL instance matching that example, export the connection string and run migrations:

```sh
export ALON_AI_DATABASE_URL=postgresql+psycopg://alon_ai:alon_ai@localhost:5432/alon_ai
cd backend && uv run alembic upgrade head
```

Run the API against that database in a second terminal:

```sh
cd backend && uv run uvicorn alon_ai.api.app:app --reload --host 127.0.0.1 --port 8000
```

Run the frontend in another terminal:

```sh
npm --prefix frontend run dev
```

The health endpoints are `http://127.0.0.1:8000/health/live` and `http://127.0.0.1:8000/health/ready`. The dashboard default is `http://localhost:3000`.

## Docker Compose

For a Docker-capable environment, use the committed local configuration:

```sh
docker compose --env-file .env.example -f infra/compose.yaml config
docker compose --env-file .env.example -f infra/compose.yaml run --rm api alembic upgrade head
make dev
```

Stop the stack with:

```sh
make down
```

Docker is unavailable in this local environment, so these Compose commands and image builds have not been executed here. The CI workflow is configured to validate Compose and build both images; its remote result is pending. Do not describe Docker as CI-validated until that workflow has passed.

## Common database failures

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `connection refused` | PostgreSQL is not running or port 5432 is not reachable | Start PostgreSQL/Compose and confirm the host and port in `ALON_AI_DATABASE_URL`. |
| `password authentication failed` | Role/password does not match the example | Create/use the `alon_ai` role and database, or update the environment variable for your local instance. |
| `/health/ready` returns 503 | API cannot complete its database check | Read API logs and verify the database URL, role, database name, and PostgreSQL availability. |
| Alembic cannot connect | Migration command lacks `ALON_AI_DATABASE_URL` | Export it in the terminal running Alembic; do not rely on another shell's variables. |
| Port 5432 is already in use | Another local PostgreSQL instance owns the port | Stop the conflicting service or select a different port and update every local connection string consistently. |

## Secrets and safety

- Keep `.env`, OAuth refresh tokens, private keys, and provider credentials out of Git.
- `.env.example` contains safe local placeholders only. Copy values into an ignored local environment file or inject them through your shell/secret manager.
- Keep `ALON_AI_OUTREACH_ENABLED=false`. The foundation has no Gmail adapter and does not send real outreach.
- Never give an agent direct Gmail credentials. The next milestone must implement the deterministic gateway and prove crash recovery with operator-controlled test inboxes.
