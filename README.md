# Alon AI

Alon AI is a private client-acquisition application for one operator. The intended journey runs from idea refinement and market research through an accepted offer, qualified leads, evidence-backed outreach, and an operator-owned invoice, demo or confirmed meeting handoff.

[Founder OS](https://www.notion.so/3d6caf700cba81a7a26bcb3b258f6ee1), its [Active Roadmap](https://app.notion.com/p/3d6caf700cba81dbb43fd57b1e534684) and Lean Build Tasks are the sole current planning authority. Follow the lowest-order eligible task and its acceptance checks. GitHub records implemented code and verification evidence. The retained `docs/development-roadmap/` tree and its validator describe historical planning; they do not override Notion or establish product completion.

## What is implemented

- FastAPI liveness and PostgreSQL-backed readiness endpoints, typed configuration and structured request logging.
- A Next.js foundation page with API/database status, generated OpenAPI types and TanStack Query.
- A separately runnable worker process that logs startup and waits for termination. It does **not** execute DBOS workflows yet.
- Reviewed PostgreSQL migrations for provider governance and bounded campaign supply, with real database concurrency and replay tests.
- Encrypted consumer-scoped secrets, capability/usage-grant checks, offline provider adapters, and durable native-currency/ILS reservations, reconciliation, quotas and circuit state.
- Fixed 50/100/3 supply rules, evidence-backed retry feedback, contactability-first admission and atomic stopping of untouched paid supply work.
- Deterministic outbound authorization/idempotency contracts tested with fake providers, plus an offline historical experiment-brief validator.
- Locked dependencies, unit and PostgreSQL integration tests, container definitions and GitHub Actions checks.

Private authentication, product records, durable workflows, shared AI execution, accepted research/offer artifacts, lead acquisition, Gmail/Calendar integrations, learning and deployment remain work for their owning Notion tasks. Installed DBOS and Pydantic AI packages are not proof that these capabilities exist. A local research prototype is separate from accepted product research and does not complete L07 or L08.

See the [L01 baseline evidence](docs/implementation/l01-baseline.md) for the audited source scope, exact results and remaining gaps.

## Local development

Use Python 3.13, uv 0.11.26, Node 24 with npm, and a working Docker engine with Compose. PostgreSQL 18 runs in the local container. Exact application package versions are retained in `backend/uv.lock` and `frontend/package-lock.json`.

From the repository root:

```sh
make setup
make dev
```

`make dev` starts PostgreSQL, runs Alembic, then builds and starts API, worker and frontend. Open [the local dashboard](http://localhost:3000). API liveness is at [health/live](http://localhost:8000/health/live) and database readiness at [health/ready](http://localhost:8000/health/ready). All published ports bind to loopback. Outreach is disabled and the Compose stack receives no provider credentials. This local topology is not production authentication.

If an existing PostgreSQL server owns port 5432, use `ALON_AI_POSTGRES_PORT=55432 make dev`. Do not stop or replace the existing database. `make down` stops this Compose stack without deleting its volume.

The [local development runbook](docs/runbooks/local-development.md) covers Docker/Colima, host processes, environment variables, migrations, integration tests and troubleshooting.

## Checks

```sh
make generate
make lint
make typecheck
make test
make build
make containers
```

`make test` runs offline unit/frontend tests. For the real database test, supply `ALON_AI_DATABASE_URL` and run `make test-integration`; see the runbook. Generated OpenAPI files must stay consistent with the API. `make roadmap` only checks the retained historical planning snapshot.

## Architecture and execution boundaries

The codebase is one modular application: a FastAPI backend and worker share Python services and PostgreSQL; Next.js consumes server-owned contracts. The selected future runtime is DBOS with Pydantic AI and OpenAI Responses. Logical product agents are roles within that application, not separately deployed services.

Future integrations must preserve deterministic acceptance, commercial limits, source rights, contact-history exclusion, suppression, budgets, idempotency and recovery. SendGateway owns Gmail writes; BookingGateway owns Calendar writes. The current roadmap requires a final 50-qualified-contactable-lead cohort from at most three adaptive batches of up to 100 new businesses each. Do not revive the historical REVIEW_20/four-batch model or infer real-send authority from a passing test.

## Layout

```text
backend/                  API, worker, provider/policy boundaries and tests
frontend/                 Next.js UI and generated API contracts
infra/compose.yaml        Loopback-only local stack
scripts/                  Contract generation and retained validators
.github/workflows/ci.yml  Application, security and container checks
docs/implementation/      Retained verification evidence
docs/runbooks/            Reproducible operating instructions
```
