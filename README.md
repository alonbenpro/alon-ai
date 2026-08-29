# Alon AI

Alon AI is being built as a durable, auditable workflow for discovering service ideas, validating them with evidence, qualifying prospects, sending Gmail outreach, synchronizing replies, and deciding whether to scale, revise, or stop an experiment.

## Foundation status

This repository is a foundation, not the finished product. It currently proves a Next.js dashboard, a FastAPI API, PostgreSQL-backed readiness, a separately runnable worker boundary, generated API types, migrations, and guarded Gmail-sending contracts.

It **does not send production outreach**, implement a Gmail adapter or OAuth, run DBOS workflows, call models/search/enrichment providers, provide public authentication, bill customers, or deploy to a VPS. Saying otherwise would be fiction.

The authoritative [M0-M9 development roadmap](docs/development-roadmap/README.md) now documents the complete planned sequence and its audited blockers. It is planning evidence, not proof that the planned product, launch gates, deployment, legal authority, or real experiment exists.

## Architecture

```mermaid
flowchart LR
    Dashboard["Next.js dashboard"] --> API["FastAPI API"]
    API --> DB[("PostgreSQL")]
    Worker["Separate worker"] --> Config["Typed config; outreach default off"]
    API --> Config
```

The detailed current and intended boundaries are in [docs/architecture.md](docs/architecture.md). FastAPI owns business/API contracts; Next.js is the dashboard; PostgreSQL is the system of record. The API and worker are separate processes from one Python package.

## Stack

- Python 3.13 with uv, FastAPI, Pydantic v2, SQLAlchemy async, Psycopg 3, Alembic, Ruff, Pyright, and pytest
- PostgreSQL 18
- DBOS, selected for future finite durable workflows, queues, schedules, retries, timers, and crash recovery on PostgreSQL; production use is blocked on M1 acceptance
- Pydantic AI and Pydantic Evals, selected for future typed agent execution, structured artifacts, tool/model boundaries, and evaluations
- Node.js 24 with Next.js App Router, TypeScript, TanStack Query, `openapi-fetch`, Tailwind CSS, ESLint, and Vitest
- Docker Compose for the local process topology and GitHub Actions for CI

Exact resolved dependency versions live in `backend/uv.lock` and `frontend/package-lock.json`.

## Repository layout

```text
backend/                  FastAPI, worker, database, provider, policy, and workflow boundaries
frontend/                 Next.js dashboard and generated OpenAPI TypeScript declarations
infra/compose.yaml        Local PostgreSQL, API, worker, and frontend topology
docs/architecture.md      Current architecture and intended guarded sending design
docs/decisions/           Architecture decision records
docs/development-roadmap/ Authoritative vertical M0-M9 implementation roadmap
docs/engineering/         Repository engineering workflows, including Graphify-first navigation
docs/runbooks/            Local operating guidance
.github/workflows/ci.yml  Backend, frontend, and container checks
```

## Agent navigation

Repository agents follow the root [AGENTS.md](AGENTS.md): query the active checkout's local Graphify graph before broad repository discovery, then verify graph-selected locations with targeted source reads. Exact-path edits and verification-only commands do not require a graph query. The executable protocol, memory/update rules, hook behavior, and failure exceptions are in the [Graphify-first navigation guide](docs/engineering/graphify-first-navigation.md). Generated `graphify-out/` state stays local and ignored.

## Quick start

Prerequisites: Python 3.13 with uv 0.11.26, and Node.js 24 with npm. The backend rejects a different uv version so local, CI, and container resolution stay aligned. In a clean environment, install the locked dependencies from the repository root:

```sh
make setup
```

On this verification machine, `make setup` encountered a pre-existing global npm-cache ownership error. The exact locally verified setup command used a clean temporary npm cache while running the same locked setup recipe:

```sh
NPM_CONFIG_CACHE=/private/tmp/alon-ai-npm-cache-20260828 make setup
```

After setup, these commands were locally verified:

```sh
make generate
make lint
make typecheck
make test
make build
```

The Docker Compose command path is documented in the [local development runbook](docs/runbooks/local-development.md). Docker is not available in the local verification environment, so the container runtime was not validated locally.

### Auditable container evidence

On 2026-08-28, immutable [GitHub Actions run 33179438858](https://github.com/alonbenpro/alon-ai/actions/runs/33179438858) passed at commit `8081008d13adfc7e8a09ee104e2bf54c37187e0b`. Its `containers` job validated the unchanged foundation Compose configuration, built both application images, initialized PostgreSQL 18, ran the foundation Alembic migration, started the stack, checked API/frontend and live/ready endpoints, verified the worker ran as non-root with outreach disabled, and removed the stack/volumes. This baseline did not test this documentation branch or any planned product DBOS/Gmail/schema/API/UI/VPS/AWS/backup/public-ingress system, and it is not a local Docker or real-send claim.

## Development and checks

| Command | Purpose |
| --- | --- |
| `make generate` | Regenerate OpenAPI JSON and TypeScript schema declarations |
| `make format` | Format Python and apply frontend lint fixes |
| `make lint` | Check Python formatting/linting and frontend linting |
| `make typecheck` | Run Pyright and TypeScript checks |
| `make test` | Run backend unit tests and frontend tests |
| `make build` | Build the Python package and production frontend |
| `make containers` | Validate Compose and build images; unavailable for local verification without Docker |

CI has four jobs: `security` checks tracked filenames and high-signal credential material without printing values; `backend` provisions PostgreSQL 18, migrates it, and runs the real readiness integration test; `frontend` regenerates the contract and rejects generated drift; `containers` validates Compose, builds the images, migrates a disposable database, starts the full stack, checks service health and HTTP endpoints, verifies the worker remains running as a non-root user with outreach disabled, and always destroys the stack and its volumes.

## Automatic Gmail sending design

Automatic Gmail sending is a planned product capability, but agents cannot call Gmail directly. Agents will produce typed artifacts. Deterministic code will create a send intent with an idempotency key, enforce suppression/jurisdiction/campaign/budget/rate-limit/kill-switch policies, and then route eligible work through a `SendGateway` to a `GmailProvider`.

The eventual implementation must commit a stable idempotency key and outbound-attempt ledger before the provider call, capture Gmail message/thread identifiers and provider evidence, and expose an ambiguous state. An ambiguous outcome must reconcile Gmail's Sent mailbox before any bounded retry; blind retries are prohibited. Today this repository supplies only the guarded contracts and an `ALON_AI_OUTREACH_ENABLED=false` default. It does not send real email.

## Safety boundaries

- PostgreSQL readiness is a real connection check; liveness alone does not prove database health.
- Secrets, OAuth tokens, and provider credentials do not belong in Git or `.env.example`.
- An agent must never receive direct Gmail authority.
- Every external side effect needs a deterministic policy decision, idempotency key, audit trail, and reconciliation strategy.
- No claims of deployment, users, billing, production metrics, compliance coverage, or send volume are made by this foundation.

## Mandatory DBOS production-acceptance spike

DBOS is the selected runtime, but selection and M1 acceptance do not authorize product outreach. Only the isolated disposable M1 harness may send, and only to operator-owned test inboxes. Product outreach remains disabled until both M1 and M6 evidence gates pass; passing both only makes the later bounded real experiment eligible for separate authority.

1. A scheduled finite DBOS workflow and validated Pydantic AI artifact.
2. Five synthetic leads passing through a DBOS queue whose rate limits remain enforced under restart and concurrency, to operator-owned test recipients only.
3. A stable send idempotency key, outbound-attempt ledger, and provider-result capture surrounding every Gmail call.
4. Worker termination before, during, and after the Gmail call with zero uncontrolled duplicate messages after restart.
5. Ambiguous outcomes enter an operator-visible state and reconcile Gmail Sent evidence before any bounded retry.
6. Pause, cancellation, and resume have deterministic behavior with zero provider calls after confirmed cancellation.
7. An in-flight workflow survives the tested workflow-version upgrade path.
8. Correlated observability exposes the workflow run, policy decision, send attempt, provider evidence, and recovery action to the operator.

Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues. See [ADR 0002](docs/decisions/0002-dbos-workflow-runtime.md).

## Roadmap and explicit non-goals

Near term: complete DBOS production acceptance, then follow the [development roadmap](docs/development-roadmap/README.md) and only build controlled outreach features that earlier gates make safe. Pydantic AI and DBOS are the selected initial stack; Temporal is the mandatory fallback after a disqualifying M1 result. LangChain, LangGraph, Restate, and Prefect are excluded from the initial stack. The foundation explicitly does not yet include public auth, multi-user accounts, billing, public webhooks, VPS deployment, Redis/Celery/RabbitMQ/Kafka, microservices, Kubernetes, vector databases, or a complete experiment state machine.
