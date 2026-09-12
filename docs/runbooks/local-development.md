# Local development

Run commands from the repository root. The current acceptance scope is [L01](https://app.notion.com/p/3d6caf700cba81b1b657eb90c9a930de): a working foundation, not a completed private production application.

## Prerequisites

- Python 3.13 and uv **0.11.26** (`uv --version`). `uv sync` selects a compatible Python interpreter; application packages come from the committed lockfile.
- Node **24** and npm (`node --version`, `npm --version`). The audit used Node 24.18.0 and npm 11.16.0.
- A running Docker engine and Compose (`docker info`, `docker compose version`). Installing a Docker CLI alone does not start an engine.
- Free loopback ports 3000 and 8000. PostgreSQL uses host port 5432 by default and can use a different port below.

On macOS, Docker Desktop or Colima can supply the engine. This audit installed Homebrew `colima`, `docker` and `docker-compose` and started a dedicated profile:

```sh
colima start --profile alon-ai --cpu 2 --memory 4 --disk 20 --activate=false
export DOCKER_HOST="unix://$HOME/.colima/alon-ai/docker.sock"
export COMPOSE=docker-compose
```

The standalone `docker-compose` override avoids changing an existing Docker CLI configuration to discover Homebrew's Compose plugin. Use the same environment for all subsequent Make/Compose commands. A Docker Desktop installation with a working plugin uses the default `docker compose` command instead. No automatic start-at-login service is required.

## Container stack

```sh
make setup
make dev
```

`make setup` installs locked host dependencies for tests and API generation. `make dev` starts the PostgreSQL 18 container, waits for its health check, runs `alembic upgrade head`, then builds/starts the API, idle worker and frontend. Alembic currently has no product revisions; successful execution is migration-tool connectivity evidence only.

The safe `.env.example` is Compose's interpolation file. Containers have explicit database/local configuration and hard-code outreach off; they do not load `backend/.env` or provider credentials. API/frontend/DB ports bind only to `127.0.0.1`. The local stack has no application authentication yet and must not be exposed publicly.

If port 5432 is occupied:

```sh
export ALON_AI_POSTGRES_PORT=55432
make dev
```

Only the host port changes; API/worker still use `postgres:5432` inside Compose. This does not modify the existing host PostgreSQL server.

Open <http://localhost:3000>. Expected API results:

```sh
curl --fail http://127.0.0.1:8000/health/live
# {"status":"ok","service":"api"}
curl --fail http://127.0.0.1:8000/health/ready
# {"status":"ready","database":"up"}
```

Readiness executes a real database query. If the DB is unavailable, it returns HTTP 503 with `{"status":"not_ready","database":"down"}`. The worker logs `worker_ready` and waits for SIGINT/SIGTERM; that does not prove durable workflow execution.

```sh
make down
```

Shutdown retains the PostgreSQL volume. Do not add `--volumes` to ordinary shutdown; it deletes local database data.

## Host development with a container database

```sh
make setup
make database
export ALON_AI_DATABASE_URL=postgresql+psycopg://alon_ai:alon_ai@127.0.0.1:5432/alon_ai
export ALON_AI_OUTREACH_ENABLED=false
make migrate
```

Use `55432` in this URL if `ALON_AI_POSTGRES_PORT=55432`. In three terminals, retaining those variables, run `make api`, `make worker`, and `make frontend`. Do not run host API/frontend on ports already occupied by the full Compose stack.

Python settings read `backend/.env` when launched by these Make targets, because they run from `backend/`. Root `.env.example` is not automatically a host-process environment file. Keep secrets only in ignored local files; do not paste credentials into commands, committed templates or logs. L01 needs no provider keys.

## Verification

```sh
make generate
make lint
make typecheck
make test
make build
make test-integration
make containers
python3 scripts/check_secrets.py
```

- `make generate` requires backend setup first and regenerates `frontend/openapi.json` and `frontend/src/lib/api/schema.d.ts`. Inspect `git diff --exit-code -- frontend/openapi.json frontend/src/lib/api/schema.d.ts` for drift.
- `make test` runs backend unit and frontend tests without provider credentials. `make test-integration` requires the explicit database URL above and a real running PostgreSQL server.
- Run frontend typecheck/build sequentially; Next generates types in `.next` during its build.
- `make containers` validates Compose and builds images. It does not start the stack or prove live readiness.
- `make roadmap` checks only retained historical planning artifacts. It does not read or validate the current Notion roadmap.

## Diagnosing setup failures

- **Docker command/daemon missing:** check both Compose and `docker info`; start the selected engine/profile. Do not substitute the host's unrelated PostgreSQL installation for the configured PostgreSQL 18 container.
- **Database connection refused:** confirm the container is healthy, check the host port override, and set `ALON_AI_DATABASE_URL` for host tests. Do not use container hostname `postgres` in host commands.
- **npm EACCES in a shared cache:** use an isolated writable cache, e.g. `npm_config_cache="$(mktemp -d)" make setup`. Do not use sudo npm or recursively change ownership of unrelated user data.
- **Frontend API error:** confirm the API responds on port 8000 and that the browser uses the matching `NEXT_PUBLIC_API_BASE_URL`. Container frontend configuration is built into the image; rebuild after changing it.
- **Network-sandbox failures:** DNS or package-registry failures under an agent sandbox are not proof of invalid credentials or a broken lockfile. Repeat only the necessary authorized network operation with the appropriate permission.
