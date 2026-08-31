# Alon AI Repository Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, verify, document, and privately publish the runnable Alon AI monorepo foundation.

**Architecture:** A modular monolith uses one Python package for FastAPI and the DBOS worker, one Next.js dashboard, and PostgreSQL as the source of truth. External providers sit behind typed interfaces; automatic Gmail sending can occur only through a deterministic gateway that enforces configuration and policy checks.

**Tech Stack:** Python 3.13, uv, FastAPI, Pydantic v2, SQLAlchemy 2 async, Psycopg 3, Alembic, DBOS, Pydantic AI/Evals, pytest, Ruff, Pyright, Next.js App Router, TypeScript, npm, TanStack Query, openapi-typescript, openapi-fetch, Tailwind CSS, Vitest, Docker Compose, PostgreSQL, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-28-alon-ai-foundation-design.md`

## Global Constraints

- Product display name is exactly `Alon AI`; repository slug is exactly `alon-ai`.
- GitHub target is exactly `alonbenpro/alon-ai`, private, with `main` as the default branch.
- Python is pinned to 3.13; the frontend and CI use Node.js 24.
- FastAPI is the only business backend. Next.js never accesses PostgreSQL directly.
- PostgreSQL is the only application source of truth.
- `OUTREACH_ENABLED` defaults to `false`.
- Agents never call Gmail directly; only `SendGateway` may invoke `GmailProvider.send`.
- Pydantic AI is selected for typed agents; DBOS is selected for finite durable workflows, queues, schedules, retries, timers, and crash recovery on PostgreSQL.
- Only the isolated disposable M1 harness may send, and only to operator-owned test inboxes; product outreach remains blocked until both M1 and M6 evidence gates pass.
- Do not add Redis, Celery, RabbitMQ, LangChain, LangGraph, Restate, Prefect, Kafka, Kubernetes, Elasticsearch, a vector database, microservices, billing, or multi-user authentication.
- Do not track real credentials, OAuth tokens, generated secrets, or local `.env` files.
- Exact dependency versions are resolved once and committed in `uv.lock` and `frontend/package-lock.json`.
- Every task ends with focused verification and a commit.

---

## File Map

### Repository root

- `.python-version`: pins Python 3.13 for uv and CI.
- `.env.example`: safe local configuration contract.
- `.gitignore`: excludes secrets, environments, caches, builds, and editor state.
- `.editorconfig`: shared whitespace rules.
- `Makefile`: one command surface for setup, checks, generation, and Compose.
- `README.md`: verified setup, architecture, safety model, and roadmap.

### Backend

- `backend/pyproject.toml`: package metadata, runtime dependencies, and tooling configuration.
- `backend/src/alon_ai/config.py`: validated environment settings.
- `backend/src/alon_ai/logging.py`: structured logging setup.
- `backend/src/alon_ai/api/app.py`: FastAPI application factory and lifespan.
- `backend/src/alon_ai/api/routes/health.py`: liveness and database-backed readiness routes.
- `backend/src/alon_ai/db/engine.py`: async engine lifecycle and database health checker.
- `backend/src/alon_ai/providers/gmail.py`: Gmail provider protocol and email value types.
- `backend/src/alon_ai/policies/sending.py`: sending-policy protocol and decision type.
- `backend/src/alon_ai/domain/sending.py`: guarded send gateway and domain errors.
- `backend/src/alon_ai/worker/main.py`: separately runnable foundation worker.
- `backend/alembic.ini`, `backend/alembic/env.py`: migration configuration.
- `backend/tests/unit/`: fast unit and API tests.
- `backend/tests/integration/test_database_readiness.py`: real PostgreSQL readiness test.

### Frontend

- `frontend/src/app/layout.tsx`: root layout and query provider.
- `frontend/src/app/page.tsx`: minimal operational home page.
- `frontend/src/components/api-status.tsx`: API/database readiness display.
- `frontend/src/components/query-provider.tsx`: TanStack Query client boundary.
- `frontend/src/lib/api/client.ts`: typed OpenAPI client.
- `frontend/src/lib/api/readiness.ts`: readiness fetcher.
- `frontend/src/lib/api/schema.d.ts`: generated OpenAPI types.
- `frontend/src/components/api-status.test.tsx`: component states.
- `frontend/openapi.json`: generated backend contract.
- `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`: component test harness.

### Infrastructure and automation

- `backend/Dockerfile`: one backend image used by API and worker.
- `frontend/Dockerfile`: standalone Next.js image.
- `infra/compose.yaml`: PostgreSQL, API, worker, and frontend services.
- `scripts/export_openapi.py`: deterministic OpenAPI export.
- `.github/workflows/ci.yml`: backend, frontend, integration, and container checks.
- `docs/architecture.md`: concise maintained architecture.
- `docs/decisions/0001-modular-monolith.md`: service-boundary decision.
- `docs/decisions/0002-dbos-workflow-runtime.md`: selected runtime, production-acceptance gate, and mandatory Temporal fallback.
- `docs/decisions/0003-guarded-gmail-sending.md`: automatic-email authority boundary.
- `docs/runbooks/local-development.md`: setup, startup, shutdown, and failure diagnosis.

---

### Task 1: Python package, settings, logging, and liveness

**Files:**
- Create: `.python-version`
- Create: `backend/pyproject.toml`
- Create: `backend/src/alon_ai/__init__.py`
- Create: `backend/src/alon_ai/config.py`
- Create: `backend/src/alon_ai/logging.py`
- Create: `backend/src/alon_ai/api/__init__.py`
- Create: `backend/src/alon_ai/api/app.py`
- Create: `backend/src/alon_ai/api/routes/__init__.py`
- Create: `backend/src/alon_ai/api/routes/health.py`
- Create: `backend/tests/unit/test_config.py`
- Create: `backend/tests/unit/test_liveness.py`

**Interfaces:**
- Produces: `Settings`, `get_settings() -> Settings`, `configure_logging(settings: Settings) -> None`, `create_app(settings: Settings | None = None) -> FastAPI`, and module-level `app`.
- Produces: `GET /health/live` returning HTTP 200 and `{"status":"ok","service":"api"}`.

- [ ] **Step 1: Initialize the package and dependencies**

Run from the repository root:

    printf '3.13\n' > .python-version
    mkdir -p backend
    cd backend
    uv init --lib --name alon-ai-backend --python 3.13
    uv add "fastapi[standard-no-fastapi-cloud-cli]" pydantic-settings structlog "sqlalchemy[asyncio]" "psycopg[binary,pool]" alembic dbos "pydantic-ai[dbos]" pydantic-evals httpx email-validator
    uv add --dev pytest pytest-asyncio pyright ruff

Then make `backend/pyproject.toml` use `src/alon_ai`, set `requires-python = ">=3.13,<3.14"`, configure pytest with `asyncio_mode = "auto"`, configure Ruff for Python 3.13, and configure Pyright to check `src` and `tests`.

- [ ] **Step 2: Write failing settings tests**

Create `backend/tests/unit/test_config.py`:

~~~python
import pytest
from pydantic import ValidationError

from alon_ai.config import Settings


def test_safe_defaults_disable_outreach() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "Alon AI"
    assert settings.environment == "development"
    assert settings.outreach_enabled is False


def test_environment_variables_use_alon_ai_prefix(monkeypatch) -> None:
    monkeypatch.setenv("ALON_AI_LOG_LEVEL", "DEBUG")
    settings = Settings(_env_file=None)
    assert settings.log_level == "DEBUG"


def test_outreach_requires_complete_gmail_configuration() -> None:
    with pytest.raises(ValidationError, match="Gmail configuration"):
        Settings(outreach_enabled=True, _env_file=None)
~~~

- [ ] **Step 3: Run the settings test and confirm failure**

Run: `cd backend && uv run pytest tests/unit/test_config.py -q`

Expected: collection fails because `alon_ai.config` does not exist.

- [ ] **Step 4: Implement validated settings and structured logging**

Create `backend/src/alon_ai/config.py` with:

~~~python
from functools import lru_cache
from typing import Literal

from pydantic import EmailStr, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ALON_AI_",
        extra="ignore",
    )

    app_name: str = "Alon AI"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://alon_ai:alon_ai@localhost:5432/alon_ai"
    )
    log_level: str = "INFO"
    outreach_enabled: bool = False
    frontend_origin: str = "http://localhost:3000"
    dbos_system_database_url: str = (
        "postgresql://alon_ai:alon_ai@localhost:5432/alon_ai"
    )
    gmail_client_id: SecretStr | None = None
    gmail_client_secret: SecretStr | None = None
    gmail_refresh_token: SecretStr | None = None
    gmail_sender_email: EmailStr | None = None

    @model_validator(mode="after")
    def require_gmail_when_outreach_is_enabled(self) -> "Settings":
        gmail_values = (
            self.gmail_client_id.get_secret_value() if self.gmail_client_id else "",
            self.gmail_client_secret.get_secret_value()
            if self.gmail_client_secret
            else "",
            self.gmail_refresh_token.get_secret_value()
            if self.gmail_refresh_token
            else "",
            str(self.gmail_sender_email or ""),
        )
        if self.outreach_enabled and not all(gmail_values):
            raise ValueError(
                "Gmail configuration is required when outreach is enabled"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
~~~

Create `configure_logging` with stdlib logging plus structlog JSON rendering in production and readable console rendering elsewhere. Do not log environment variable values.

- [ ] **Step 5: Run settings tests**

Run: `cd backend && uv run pytest tests/unit/test_config.py -q`

Expected: 3 passed.

- [ ] **Step 6: Write the failing liveness test**

Create `backend/tests/unit/test_liveness.py`:

~~~python
from fastapi.testclient import TestClient

from alon_ai.api.app import create_app
from alon_ai.config import Settings


def test_liveness_does_not_require_database() -> None:
    app = create_app(Settings(environment="test", _env_file=None))
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
~~~

- [ ] **Step 7: Run the liveness test and confirm failure**

Run: `cd backend && uv run pytest tests/unit/test_liveness.py -q`

Expected: import or route failure because the application factory does not exist.

- [ ] **Step 8: Implement the application factory and liveness route**

`create_app` must construct FastAPI with title `Alon AI API`, install CORS only for `settings.frontend_origin`, include the health router, and attach settings to `app.state.settings`. The liveness route must be:

~~~python
@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok", "service": "api"}
~~~

Expose `app = create_app()` at module scope.

- [ ] **Step 9: Run focused and static checks**

Run:

    cd backend
    uv run pytest tests/unit/test_config.py tests/unit/test_liveness.py -q
    uv run ruff format --check .
    uv run ruff check .
    uv run pyright

Expected: all commands pass.

- [ ] **Step 10: Commit Task 1**

    git add .python-version backend
    git commit -m "feat: initialize Alon AI backend"

---

### Task 2: Database lifecycle, readiness, and Alembic

**Files:**
- Create: `backend/src/alon_ai/db/__init__.py`
- Create: `backend/src/alon_ai/db/engine.py`
- Modify: `backend/src/alon_ai/api/app.py`
- Modify: `backend/src/alon_ai/api/routes/health.py`
- Create: `backend/tests/unit/test_readiness.py`
- Create: `backend/tests/integration/test_database_readiness.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/.gitkeep`

**Interfaces:**
- Consumes: `Settings.database_url` and `create_app`.
- Produces: `create_engine(settings: Settings) -> AsyncEngine`.
- Produces: `DatabaseHealthChecker(engine: AsyncEngine)` with `async __call__() -> bool`.
- Produces: `GET /health/ready`; HTTP 200 with `{"status":"ready","database":"up"}` or HTTP 503 with `{"status":"not_ready","database":"down"}`.

- [ ] **Step 1: Write readiness route tests with a replaceable checker**

Create `backend/tests/unit/test_readiness.py` using a small async fake assigned to `app.state.database_health`. Assert the 200 and 503 responses exactly.

~~~python
class FakeHealth:
    def __init__(self, healthy: bool) -> None:
        self.healthy = healthy

    async def __call__(self) -> bool:
        return self.healthy
~~~

- [ ] **Step 2: Run readiness tests and confirm failure**

Run: `cd backend && uv run pytest tests/unit/test_readiness.py -q`

Expected: failures because `/health/ready` does not exist.

- [ ] **Step 3: Implement the engine and readiness checker**

`DatabaseHealthChecker.__call__` must execute `SELECT 1` inside `async with engine.connect()`, return `True` on success, and return `False` only for `SQLAlchemyError`. It must not swallow cancellation or programming errors.

~~~python
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alon_ai.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


class DatabaseHealthChecker:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def __call__(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True
~~~

- [ ] **Step 4: Wire engine ownership into FastAPI lifespan**

The lifespan must create one engine, assign `DatabaseHealthChecker` to `app.state.database_health`, yield, and dispose the engine in `finally`. Tests may replace `app.state.database_health` after startup.

~~~python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    engine = create_engine(settings)
    app.state.database_health = DatabaseHealthChecker(engine)
    try:
        yield
    finally:
        await engine.dispose()
~~~

- [ ] **Step 5: Implement the readiness route**

Use a `JSONResponse(status_code=503, ...)` for failure. Do not turn database failure into HTTP 200.

~~~python
@router.get("/ready")
async def ready(request: Request) -> Response:
    if not await request.app.state.database_health():
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "down"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "database": "up"},
    )
~~~

- [ ] **Step 6: Run unit readiness tests**

Run: `cd backend && uv run pytest tests/unit/test_readiness.py -q`

Expected: all readiness tests pass.

- [ ] **Step 7: Add a real PostgreSQL integration test**

Create `backend/tests/integration/test_database_readiness.py`:

~~~python
import os

import pytest

from alon_ai.config import Settings
from alon_ai.db.engine import DatabaseHealthChecker, create_engine


@pytest.mark.integration
async def test_real_postgres_is_ready() -> None:
    settings = Settings(
        environment="test",
        database_url=os.environ["ALON_AI_DATABASE_URL"],
        _env_file=None,
    )
    engine = create_engine(settings)
    try:
        assert await DatabaseHealthChecker(engine)() is True
    finally:
        await engine.dispose()
~~~

- [ ] **Step 8: Configure Alembic for the async database URL**

Initialize Alembic, then replace generated URL handling so `alembic/env.py` imports `get_settings().database_url`. Use SQLAlchemy async migration execution and an empty metadata object until real models exist. Do not create a fake business table.

- [ ] **Step 9: Verify Task 2**

Run unit checks locally:

    cd backend
    uv run pytest tests/unit -q
    uv run ruff format --check .
    uv run ruff check .
    uv run pyright

Run the integration test when PostgreSQL is reachable:

    ALON_AI_DATABASE_URL=postgresql+psycopg://alon_ai:alon_ai@localhost:5432/alon_ai uv run pytest tests/integration/test_database_readiness.py -q

Expected: all available checks pass; CI will supply PostgreSQL if Docker is unavailable locally.

- [ ] **Step 10: Commit Task 2**

    git add backend
    git commit -m "feat: add database-backed readiness"

---

### Task 3: Guarded Gmail contracts and worker boundary

**Files:**
- Create: `backend/src/alon_ai/providers/__init__.py`
- Create: `backend/src/alon_ai/providers/gmail.py`
- Create: `backend/src/alon_ai/policies/__init__.py`
- Create: `backend/src/alon_ai/policies/sending.py`
- Create: `backend/src/alon_ai/domain/__init__.py`
- Create: `backend/src/alon_ai/domain/sending.py`
- Create: `backend/src/alon_ai/agents/__init__.py`
- Create: `backend/src/alon_ai/workflows/__init__.py`
- Create: `backend/src/alon_ai/worker/__init__.py`
- Create: `backend/src/alon_ai/worker/main.py`
- Create: `backend/tests/unit/test_send_gateway.py`
- Create: `backend/tests/unit/test_worker.py`

**Interfaces:**
- Produces: `EmailDraft`, `SendRequest`, `SendResult`, and `GmailProvider.send(request: SendRequest) -> SendResult`.
- Produces: `PolicyDecision` and `SendPolicy.evaluate(request: SendRequest) -> PolicyDecision`.
- Produces: `SendGateway.send(request: SendRequest) -> SendResult`.
- Produces errors: `OutreachDisabledError` and `SendRejectedError`.
- Produces: `build_worker_startup_event(settings: Settings) -> dict[str, str | bool]`.

- [ ] **Step 1: Write failing send-gateway tests**

Cover three exact behaviors:

1. With outreach disabled, the gateway raises `OutreachDisabledError` and neither policy nor provider is called.
2. With outreach enabled but policy denied, it raises `SendRejectedError` and provider is not called.
3. With outreach enabled and policy allowed, provider is awaited exactly once and its `SendResult` is returned.

Use `AsyncMock(spec=GmailProvider)` and `AsyncMock(spec=SendPolicy)`.

- [ ] **Step 2: Run the tests and confirm failure**

Run: `cd backend && uv run pytest tests/unit/test_send_gateway.py -q`

Expected: import failures because the contracts do not exist.

- [ ] **Step 3: Implement typed Gmail and policy contracts**

Use immutable Pydantic models:

~~~python
class EmailDraft(BaseModel):
    model_config = ConfigDict(frozen=True)
    to: EmailStr
    subject: str = Field(min_length=1, max_length=200)
    body_text: str = Field(min_length=1)


class SendRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    idempotency_key: UUID
    draft: EmailDraft


class SendResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider_message_id: str
    provider_thread_id: str
~~~

Define `GmailProvider` and `SendPolicy` as runtime-checkable protocols with async methods.

`PolicyDecision` is an immutable Pydantic model with `allowed: bool` and non-empty `reason: str`.

- [ ] **Step 4: Implement the guarded gateway**

The method order must be: check `outreach_enabled`; evaluate policy; call provider. No caller may bypass the policy by passing a pre-approved boolean.

~~~python
class SendGateway:
    def __init__(
        self,
        *,
        outreach_enabled: bool,
        policy: SendPolicy,
        provider: GmailProvider,
    ) -> None:
        self._outreach_enabled = outreach_enabled
        self._policy = policy
        self._provider = provider

    async def send(self, request: SendRequest) -> SendResult:
        if not self._outreach_enabled:
            raise OutreachDisabledError
        decision = await self._policy.evaluate(request)
        if not decision.allowed:
            raise SendRejectedError(decision.reason)
        return await self._provider.send(request)
~~~

- [ ] **Step 5: Run gateway tests**

Run: `cd backend && uv run pytest tests/unit/test_send_gateway.py -q`

Expected: all 3 behaviors pass.

- [ ] **Step 6: Write and implement the worker startup-event test**

`build_worker_startup_event` must return:

~~~python
{
    "event": "worker_ready",
    "service": "worker",
    "outreach_enabled": False,
}
~~~

`main()` configures logging, emits this event, and waits for termination without starting Gmail, search, model, or campaign work. This is a process boundary, not an agent loop.

- [ ] **Step 7: Run all backend checks**

    cd backend
    uv run pytest tests/unit -q
    uv run ruff format --check .
    uv run ruff check .
    uv run pyright

Expected: all pass.

- [ ] **Step 8: Commit Task 3**

    git add backend
    git commit -m "feat: add guarded sending boundary"

---

### Task 4: Typed OpenAPI client and readiness dashboard

**Files:**
- Create: `scripts/export_openapi.py`
- Create: `frontend/` with create-next-app
- Modify: `frontend/package.json`
- Modify: `frontend/next.config.ts`
- Modify: `frontend/src/app/layout.tsx`
- Replace: `frontend/src/app/page.tsx`
- Replace: `frontend/src/app/globals.css`
- Create: `frontend/src/components/query-provider.tsx`
- Create: `frontend/src/components/api-status.tsx`
- Create: `frontend/src/lib/api/client.ts`
- Create: `frontend/src/lib/api/readiness.ts`
- Generate: `frontend/openapi.json`
- Generate: `frontend/src/lib/api/schema.d.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/components/api-status.test.tsx`

**Interfaces:**
- Consumes: `GET /health/ready` from Task 2.
- Produces: `fetchReadiness() -> Promise<Readiness>`.
- Produces: `ApiStatus` states: loading, ready, and unavailable.
- Produces npm scripts: `api:generate`, `test`, `typecheck`, `lint`, and `build`.

- [ ] **Step 1: Export the backend OpenAPI document**

Create `scripts/export_openapi.py` with an `--output` argument. It imports `create_app`, calls `app.openapi()`, serializes sorted indented JSON with a trailing newline, and writes only to the requested repository path.

- [ ] **Step 2: Scaffold the frontend with current create-next-app**

Run:

    npx create-next-app@latest frontend --ts --eslint --tailwind --app --src-dir --use-npm --import-alias "@/*" --empty --yes
    cd frontend
    npm install @tanstack/react-query openapi-fetch
    npm install --save-dev openapi-typescript vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom

Commit the resolved `package-lock.json`.

- [ ] **Step 3: Generate the typed client contract**

Run:

    backend/.venv/bin/python scripts/export_openapi.py --output frontend/openapi.json
    cd frontend
    npx openapi-typescript openapi.json -o src/lib/api/schema.d.ts

Add these package scripts so generation and verification are reproducible:

~~~json
{
  "scripts": {
    "api:export": "../backend/.venv/bin/python ../scripts/export_openapi.py --output openapi.json",
    "api:generate": "npm run api:export && openapi-typescript openapi.json -o src/lib/api/schema.d.ts",
    "test": "vitest",
    "typecheck": "tsc --noEmit"
  }
}
~~~

- [ ] **Step 4: Write failing component tests**

Mock `fetchReadiness` and test:

- pending query renders `Checking services…`;
- resolved ready response renders `API online` and `Database online`;
- rejected request renders `Services unavailable`.

Wrap `ApiStatus` in a fresh QueryClient per test with retries disabled.

- [ ] **Step 5: Run the component tests and confirm failure**

Run: `cd frontend && npm test -- --run`

Expected: imports fail because the provider, fetcher, and component do not exist.

- [ ] **Step 6: Implement the query provider and typed client**

`apiClient` must use the generated `paths` type and:

~~~typescript
const baseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = createClient<paths>({ baseUrl });
~~~

`fetchReadiness` must call `apiClient.GET("/health/ready")`, return the typed data on success, and throw `Error("API readiness check failed")` for a non-success response.

~~~typescript
import { apiClient } from "@/lib/api/client";

export async function fetchReadiness() {
  const { data, error } = await apiClient.GET("/health/ready");
  if (error || !data) {
    throw new Error("API readiness check failed");
  }
  return data;
}
~~~

- [ ] **Step 7: Implement the minimal dashboard**

The page contains the product name, a one-sentence purpose, the readiness card, and a visible `Outreach disabled by default` safety indicator. Keep it operational and sparse; do not add mock charts, fake leads, or invented metrics.

Implement the status behavior directly:

~~~tsx
"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchReadiness } from "@/lib/api/readiness";

export function ApiStatus() {
  const query = useQuery({
    queryKey: ["readiness"],
    queryFn: fetchReadiness,
    refetchInterval: 30_000,
    retry: 1,
  });

  if (query.isPending) return <p>Checking services…</p>;
  if (query.isError) return <p>Services unavailable</p>;

  return (
    <dl>
      <div><dt>API</dt><dd>API online</dd></div>
      <div><dt>Database</dt><dd>Database online</dd></div>
    </dl>
  );
}
~~~

- [ ] **Step 8: Configure standalone output and tests**

Set `output: "standalone"` in `next.config.ts`. Configure Vitest for jsdom and Testing Library setup.

- [ ] **Step 9: Verify Task 4**

    cd frontend
    npm run lint
    npm run typecheck
    npm test -- --run
    npm run build

Expected: all pass.

- [ ] **Step 10: Commit Task 4**

    git add scripts frontend
    git commit -m "feat: add readiness dashboard"

---

### Task 5: Containers, Compose, and root developer commands

**Files:**
- Create: `.env.example`
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `Makefile`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `infra/compose.yaml`

**Interfaces:**
- Consumes: backend API and worker modules plus standalone frontend.
- Produces: Compose services `postgres`, `api`, `worker`, and `frontend`.
- Produces root targets: `setup`, `generate`, `format`, `lint`, `typecheck`, `test`, `build`, `containers`, `dev`, and `down`.

- [ ] **Step 1: Create the secret-safe repository defaults**

`.env.example` must contain safe local values for PostgreSQL, API URLs, frontend origin, log level, DBOS system database URL, and `ALON_AI_OUTREACH_ENABLED=false`. It must not contain usable provider credentials.

`.gitignore` must exclude all `.env` variants except `.env.example`, Python environments/caches, Node modules, Next.js builds, coverage, Playwright artifacts, local OAuth tokens, and OS/editor files.

- [ ] **Step 2: Add root commands**

`make test` runs backend unit tests and frontend component tests. `make build` builds the Python distribution and production frontend. `make containers` validates Compose and builds both Docker images. `make generate` regenerates OpenAPI JSON and TypeScript types. Each target must fail on the first failing command.

Use this command surface:

~~~make
.PHONY: setup generate format lint typecheck test build containers dev down

setup:
	cd backend && uv sync --locked --all-extras --dev
	npm --prefix frontend ci

generate:
	npm --prefix frontend run api:generate

format:
	cd backend && uv run ruff format .
	npm --prefix frontend run lint -- --fix

lint:
	cd backend && uv run ruff format --check .
	cd backend && uv run ruff check .
	npm --prefix frontend run lint

typecheck:
	cd backend && uv run pyright
	npm --prefix frontend run typecheck

test:
	cd backend && uv run pytest tests/unit -q
	npm --prefix frontend test -- --run

build:
	cd backend && uv build
	npm --prefix frontend run build

containers:
	docker compose --env-file .env.example -f infra/compose.yaml config
	docker build -f backend/Dockerfile -t alon-ai-backend:local backend
	docker build -f frontend/Dockerfile -t alon-ai-frontend:local frontend

dev:
	docker compose --env-file .env.example -f infra/compose.yaml up --build

down:
	docker compose --env-file .env.example -f infra/compose.yaml down
~~~

- [ ] **Step 3: Create the backend image**

Use the official uv Python 3.13 Debian-based image, install from `uv.lock` with `uv sync --locked --no-dev`, copy the source after the lockfile layer, and use exec-form commands. The same image must support:

    uv run uvicorn alon_ai.api.app:app --host 0.0.0.0 --port 8000
    uv run python -m alon_ai.worker.main

The Dockerfile must follow this cache order:

~~~dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "alon_ai.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
~~~

- [ ] **Step 4: Create the frontend standalone image**

Use Node 24 for the build stage and a non-root runtime user. Copy only `.next/standalone`, `.next/static`, and `public` into the runtime image.

~~~dockerfile
FROM node:24-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
~~~

- [ ] **Step 5: Create Compose**

Use PostgreSQL 18 with `pg_isready`. Mark API and worker dependencies with `condition: service_healthy`. API health checks call `/health/ready`. Frontend depends on healthy API. Keep PostgreSQL and API ports bound to localhost in local development.

The service contract is:

~~~yaml
services:
  postgres:
    image: postgres:18
    environment:
      POSTGRES_DB: alon_ai
      POSTGRES_USER: alon_ai
      POSTGRES_PASSWORD: alon_ai
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U alon_ai -d alon_ai"]
      interval: 5s
      timeout: 5s
      retries: 10
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build:
      context: ../backend
    environment:
      ALON_AI_DATABASE_URL: postgresql+psycopg://alon_ai:alon_ai@postgres:5432/alon_ai
      ALON_AI_ENVIRONMENT: development
      ALON_AI_OUTREACH_ENABLED: "false"
      ALON_AI_FRONTEND_ORIGIN: http://localhost:3000
    command: ["uvicorn", "alon_ai.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')"]
      interval: 5s
      timeout: 5s
      retries: 10

  worker:
    build:
      context: ../backend
    environment:
      ALON_AI_DATABASE_URL: postgresql+psycopg://alon_ai:alon_ai@postgres:5432/alon_ai
      ALON_AI_DBOS_SYSTEM_DATABASE_URL: postgresql://alon_ai:alon_ai@postgres:5432/alon_ai
      ALON_AI_OUTREACH_ENABLED: "false"
    command: ["python", "-m", "alon_ai.worker.main"]
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    build:
      context: ../frontend
      args:
        NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      api:
        condition: service_healthy

volumes:
  postgres_data:
~~~

- [ ] **Step 6: Validate configuration**

Run when Docker is available:

    docker compose --env-file .env.example -f infra/compose.yaml config
    docker build -f backend/Dockerfile -t alon-ai-backend:local backend
    docker build -f frontend/Dockerfile -t alon-ai-frontend:local frontend

Expected: Compose renders and both images build. If Docker is absent, record that fact and rely on Task 6 CI for these exact checks.

- [ ] **Step 7: Re-run application checks**

    make lint
    make typecheck
    make test

Expected: all pass.

- [ ] **Step 8: Commit Task 5**

    git add .env.example .gitignore .editorconfig Makefile backend/Dockerfile frontend/Dockerfile infra
    git commit -m "build: add local container stack"

---

### Task 6: CI, architecture records, runbook, and README

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `docs/architecture.md`
- Create: `docs/decisions/0001-modular-monolith.md`
- Create: `docs/decisions/0002-dbos-workflow-runtime.md`
- Create: `docs/decisions/0003-guarded-gmail-sending.md`
- Create: `docs/runbooks/local-development.md`
- Create: `README.md`

**Interfaces:**
- Consumes: all verified commands from Tasks 1-5.
- Produces: CI checks named `backend`, `frontend`, and `containers`.
- Produces: operator documentation that makes no unverified capability claims.

- [ ] **Step 1: Create least-privilege CI**

Set `permissions: contents: read`. Use current official actions:

- `actions/checkout@v7`;
- `astral-sh/setup-uv@v9` with Python 3.13 and locked sync;
- `actions/setup-node@v7` with Node 24 and npm caching.

The backend job starts PostgreSQL 18 as a service, runs Alembic, Ruff, Pyright, unit tests, and the real readiness integration test. The frontend job regenerates the API contract, runs `npm ci`, verifies no generated diff, then runs lint, type checking, tests, and build. The container job validates Compose and builds both images.

Use this workflow shape:

~~~yaml
name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_DB: alon_ai
          POSTGRES_USER: alon_ai
          POSTGRES_PASSWORD: alon_ai
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U alon_ai -d alon_ai"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      ALON_AI_DATABASE_URL: postgresql+psycopg://alon_ai:alon_ai@localhost:5432/alon_ai
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v9
        with:
          python-version: "3.13"
          enable-cache: true
      - run: uv sync --locked --all-extras --dev
        working-directory: backend
      - run: uv run ruff format --check .
        working-directory: backend
      - run: uv run ruff check .
        working-directory: backend
      - run: uv run pyright
        working-directory: backend
      - run: uv run alembic upgrade head
        working-directory: backend
      - run: uv run pytest tests -q
        working-directory: backend

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v9
        with:
          python-version: "3.13"
      - run: uv sync --locked --all-extras --dev
        working-directory: backend
      - uses: actions/setup-node@v7
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npm run api:generate
        working-directory: frontend
      - run: git diff --exit-code -- openapi.json src/lib/api/schema.d.ts
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend
      - run: npm run typecheck
        working-directory: frontend
      - run: npm test -- --run
        working-directory: frontend
      - run: npm run build
        working-directory: frontend

  containers:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: docker compose --env-file .env.example -f infra/compose.yaml config
      - run: docker build -f backend/Dockerfile -t alon-ai-backend:ci backend
      - run: docker build -f frontend/Dockerfile -t alon-ai-frontend:ci frontend
~~~

- [ ] **Step 2: Write architecture and decision records**

Each record must state context, decision, consequences, and reconsideration trigger. The DBOS record selects Pydantic AI for typed agents and DBOS for finite durable workflows/queues/schedules on PostgreSQL; M1 is necessary but not sufficient for product outreach, which remains disabled until both M1 and M6 evidence gates pass. Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues. The Gmail record must explicitly say automated sending is supported but agents cannot call Gmail directly.

- [ ] **Step 3: Write the local runbook**

Document prerequisites, setup, generation, test commands, Docker startup/shutdown, health URLs, common database failures, and secret handling. Do not include VPS deployment steps because deployment is outside this foundation.

- [ ] **Step 4: Write README**

README sections:

1. Product purpose and current foundation status.
2. Architecture diagram.
3. Exact stack.
4. Repository layout.
5. Quick start using only verified commands.
6. Development and checks.
7. Automatic Gmail sending design.
8. Safety boundaries.
9. Mandatory DBOS production-acceptance spike.
10. Roadmap and explicit non-goals.

State clearly that the repository foundation does not yet send production outreach.

- [ ] **Step 5: Verify documentation and CI syntax**

Run:

    git diff --check
    make generate
    git diff --exit-code -- frontend/openapi.json frontend/src/lib/api/schema.d.ts
    make lint
    make typecheck
    make test

If Docker is available, also run the Compose validation and image builds from Task 5.

Expected: no generated drift, whitespace errors, or failing checks.

- [ ] **Step 6: Commit Task 6**

    git add .github README.md docs
    git commit -m "docs: document Alon AI foundation"

---

### Task 7: Full local verification and clean-history checkpoint

**Files:**
- Modify only files required to fix failures found by the complete verification.

**Interfaces:**
- Consumes: every command and artifact from Tasks 1-6.
- Produces: a clean `main` branch ready for private publication.

- [ ] **Step 1: Verify lockfile installs**

    cd backend && uv sync --locked --all-extras --dev
    cd ../frontend && npm ci

Expected: both complete without modifying lockfiles.

- [ ] **Step 2: Run complete backend verification**

    cd backend
    uv run ruff format --check .
    uv run ruff check .
    uv run pyright
    uv run pytest tests/unit -q

Run the integration suite against PostgreSQL locally when available; otherwise confirm the CI workflow supplies PostgreSQL 18.

- [ ] **Step 3: Run complete frontend verification**

    cd frontend
    npm run api:generate
    npm run lint
    npm run typecheck
    npm test -- --run
    npm run build

Expected: all pass and generated files remain unchanged.

- [ ] **Step 4: Run container verification**

When Docker is available:

    docker compose --env-file .env.example -f infra/compose.yaml config
    docker compose --env-file .env.example -f infra/compose.yaml up --build -d
    curl --fail http://localhost:8000/health/live
    curl --fail http://localhost:8000/health/ready
    curl --fail http://localhost:3000
    docker compose --env-file .env.example -f infra/compose.yaml down --volumes

Expected: all services become healthy and all three HTTP checks succeed.

- [ ] **Step 5: Audit repository hygiene**

    git diff --check
    git status --short
    git ls-files | rg '(^|/)(\.env|.*token.*|.*credential.*|node_modules|\.venv)(/|$)' && exit 1 || true

Expected: no uncommitted generated drift and no secret/dependency directories tracked.

- [ ] **Step 6: Commit only if verification required fixes**

    git add -u
    git commit -m "fix: complete foundation verification"

If no fixes were required, do not create an empty commit.

---

### Task 8: Create private GitHub repository and connect the Codex project

**Files/state:**
- Modify Git remote `origin`.
- Create private GitHub repository `alonbenpro/alon-ai`.
- Update only the current Codex local-project display-name field from `Money Workflow` to `Alon AI`; preserve project ID, root path, order, thread assignments, and writable roots.

**Interfaces:**
- Consumes: verified clean `main` from Task 7.
- Produces: private remote with pushed `main` and Codex project label `Alon AI`.

- [ ] **Step 1: Confirm exact local and remote targets**

    git branch --show-current
    git remote -v
    gh auth status

Expected: branch is `main`; no conflicting `origin`; GitHub auth is currently invalid and must be repaired.

- [ ] **Step 2: Reauthenticate GitHub CLI**

Run:

    gh auth login -h github.com -w
    gh auth setup-git
    gh auth status

Expected: account `alonbenpro` is active. Stop if another account is active.

- [ ] **Step 3: Confirm repository-name availability**

Run: `gh repo view alonbenpro/alon-ai`

Expected: not found. If it exists, inspect it and stop rather than overwriting or repointing it.

- [ ] **Step 4: Create and push the private repository**

Run:

    gh repo create alonbenpro/alon-ai --private --source=. --remote=origin --push

Do not request GitHub-generated README, license, or gitignore because local history already contains them.

- [ ] **Step 5: Verify GitHub state**

Run:

    gh repo view alonbenpro/alon-ai --json nameWithOwner,isPrivate,defaultBranchRef,url
    git remote -v
    git ls-remote --heads origin main

Expected: `nameWithOwner` is `alonbenpro/alon-ai`, `isPrivate` is `true`, default branch is `main`, and remote `main` exists.

- [ ] **Step 6: Wait for remote CI and fix failures**

Run:

    alon_ai_run_id="$(gh run list --workflow ci.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
    gh run watch "$alon_ai_run_id" --exit-status

Expected: backend, frontend, and container jobs pass. If a job fails, inspect it with `gh run view "$alon_ai_run_id" --log-failed`, fix the actual cause locally, rerun the affected local checks, commit, push, and watch the new run.

- [ ] **Step 7: Rename the Codex local project safely**

First query `codex_app__list_projects` and confirm project ID `b7b19b00-0985-4e7a-b092-2630ae86560a` still maps to root `/Users/alonbensa/Documents/ChatGPT/Money Workflow`.

Because no project-update tool is available, request permission for this app-state change and then run:

    alon_ai_state="/Users/alonbensa/.codex/.codex-global-state.json"
    alon_ai_backup="$(mktemp /Users/alonbensa/.codex/.codex-global-state.json.bak.alon-ai.XXXXXX)"
    cp "$alon_ai_state" "$alon_ai_backup"
    alon_ai_temp_state="$(mktemp /Users/alonbensa/.codex/.codex-global-state.json.alon-ai.XXXXXX)"
    jq '.["local-projects"]["b7b19b00-0985-4e7a-b092-2630ae86560a"].name = "Alon AI"' "$alon_ai_state" > "$alon_ai_temp_state"
    jq empty "$alon_ai_temp_state"
    mv "$alon_ai_temp_state" "$alon_ai_state"

This atomically updates only:

    ["local-projects"]["b7b19b00-0985-4e7a-b092-2630ae86560a"]["name"]

from `Money Workflow` to `Alon AI`. Validate the new JSON with `jq empty` before replacing the state file. Do not change the root path or thread assignments.

- [ ] **Step 8: Verify Codex connection**

Call `codex_app__list_projects` again.

Expected: label is `Alon AI`, path is unchanged, and `isGitRepository` is `true`. If the app still shows cached state, restart Codex once and recheck rather than editing any additional fields.

- [ ] **Step 9: Final handoff evidence**

Record:

- GitHub repository URL;
- latest local and remote commit SHA;
- passing checks and unavailable checks;
- Docker availability;
- Codex project label/path/repository status;
- explicit reminder that real Gmail sending is the next recovery-spike milestone, not a completed foundation capability.
