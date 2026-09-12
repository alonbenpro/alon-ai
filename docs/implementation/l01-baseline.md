# L01 — foundation baseline evidence

Audit date: 12 September 2026. Owning task: [L01 — Audit the repository and establish a green baseline](https://app.notion.com/p/3d6caf700cba81b1b657eb90c9a930de). Source baseline: `08250bf` plus the bounded setup, documentation and dependency repairs in this change. This report is implementation evidence, not a new roadmap.

## Scope and source handling

Read Founder OS, the active roadmap and task database, L01, and the current architecture/database specifications. Independent agents audited backend/frontend and read both complete architecture/schema references. Their amendments explicitly override obsolete stage/four-batch requirements in lower sections. No future product task was marked implemented from documentation or package installation.

The initial working tree contained an unfinished Brave research prototype. It passed its own unit checks but was not the current accepted research workflow and hid the foundation readiness UI. Its original tracked diff and untracked files were backed up and byte-checked before restoring the corresponding committed foundation files. The local backup is `.worktrees/pre-l01-local-work-2026-09-12/`, ignored by Git; it contains the original source tree and `original-working-tree.patch`. Provider secrets were not copied into it or committed. The preexisting explicit dictionary-narrowing repair in the offline brief test was retained.

Final baseline verification used an independent clean `git archive` source snapshot under `/private/tmp/alon-l01-clean`, with only the intended L01 files overlaid. It did not inherit the prototype, existing virtual environment, node_modules, ignored environment files or existing database. The temporary snapshot is not a second planning authority.

## Implemented versus planned

| Area | Observed implementation | Not established by L01 |
| --- | --- | --- |
| API | FastAPI factory/lifespan; liveness; real `SELECT 1` readiness; CORS; structured sanitized request logs | Private auth, product commands, accepted-artifact projections |
| Configuration | Pydantic Settings; safe outreach default; Gmail completeness guard; typed environment | Complete provider grants, secret-store handles, budgets/cost ledger |
| PostgreSQL | SQLAlchemy async/Psycopg connection and readiness | Product tables, repositories, transaction/outbox/command stores |
| Migrations | Alembic online/offline configuration runs against PostgreSQL | **Zero product revision files; empty target metadata** |
| Worker | Separate non-root process; `worker_ready`; graceful signal termination | DBOS initialization, queues, workflows, recovery or worker DB health |
| AI | DBOS/Pydantic AI/Evals installed and locked | Shared AI runtime, model evaluations, actual agent runs |
| Frontend | Next.js foundation screen; API/database status; generated OpenAPI client; TanStack Query | Dark-first Mission Control, experiment creation, business controls, SSE/map/learning UI |
| Sending | Deterministic contracts with fake-provider/unit evidence | Gmail OAuth, live adapter, production recovery or real-send authority |
| Operations | Local loopback Compose topology; locked installs/builds; CI definitions | Production ingress/authentication, backups/restoration, real campaign readiness |

L01 deliberately does not implement L02–L34. A successful `alembic upgrade head` proves the harness connects; `worker_ready` proves process startup only. The historical M0 validator and retained roadmap tests do not validate the current Notion plan.

## Repairs

- Added `database`, `migrate`, `api`, `worker`, `frontend` and `test-integration` Make targets. `dev` now waits for PostgreSQL and migrates before starting the full application.
- Added `COMPOSE`/`COMPOSE_ARGS` overrides and a loopback-only `ALON_AI_POSTGRES_PORT` override. An existing host database can remain on 5432 while this stack uses 55432.
- Pinned the observed Docker base images and CI PostgreSQL service to immutable digests. Existing application package versions remain locked.
- Patched only the vulnerable OpenAPI-tooling dependency chain: `@redocly/openapi-core` 1.34.19 → 1.34.20, replacing its pinned `js-yaml` 4.3.1 with 4.3.2. No direct package/framework or API-contract change.
- Replaced stale setup/roadmap claims with an honest foundation inventory and canonical local runbook.

## Verification results

| Check | Result and limit |
| --- | --- |
| Clean locked install | PASS: `uv sync --locked --all-extras --dev` and `npm ci` in the clean snapshot. An isolated npm cache resolved the host's preexisting shared-cache EACCES. |
| Generated API contracts | PASS: fresh OpenAPI export and TypeScript generation compare byte-identical with the intended source files; repeated after the YAML dependency patch. |
| Backend formatting/lint/types | PASS: 35 files formatted, Ruff clean, Pyright zero errors/warnings. |
| Backend unit tests | PASS: **315** tests in clean foundation source. Prototype tests are excluded from this count. |
| Real database integration | PASS: **1** readiness test against isolated PostgreSQL **18.6** on host port **55432**. |
| Frontend checks | PASS: ESLint, TypeScript, **5** tests across **2** files, Next.js production build. |
| Backend package | PASS: source distribution and wheel built. |
| Compose/images | PASS: configuration, API/worker/frontend image builds, migration command and detached startup with health wait. |
| API liveness | PASS: HTTP 200 `{"status":"ok","service":"api"}`. |
| API/database readiness | PASS: HTTP 200 `{"status":"ready","database":"up"}` from the running container. |
| Worker | PASS: process running; startup log includes `worker_ready`, `service=worker`, `outreach_enabled=False`; API/worker UID **10001**. No durable-workflow claim. |
| Browser | PASS: in-app browser at `http://localhost:3000/`, title “Alon AI”, meaningful foundation screen, API/database online text, no framework overlay, no console errors/warnings on initial load; screenshot inspected. |
| Outage/recovery | PASS: stopped only the isolated PostgreSQL container; API returned **503** and UI showed **Services unavailable**. Restart restored HTTP **200** and **Database online** after reload. No fixture substituted for the database. |
| Dependency advisory | PASS after patch: `npm audit --audit-level=high` reports **0 vulnerabilities**. This is npm's advisory result, not a complete security review. |
| Historical roadmap | PASS: existing artifact validator remains green; non-authoritative planning references only. |

The local container VM is Colima profile `alon-ai` (2 CPUs, 4 GiB memory, 20 GiB disk). Host PostgreSQL 16 was left untouched. Compose project `alon-l01` uses its own volume. The running validation stack is built from the clean snapshot, not ignored local research code.

## Audited runtime versions

Host checks: Python **3.13.14**, uv **0.11.26**, Node **24.18.0**, npm **11.16.0**. Container checks: Python **3.13.15**, Node **24.21.0**, PostgreSQL **18.6**. Both supported host/container patch combinations built successfully. Developer/CI host selectors still permit the supported Python 3.13/Node 24 lines; release containers use the exact digests below.

Backend lock highlights: FastAPI 0.141.1, SQLAlchemy 2.0.52, Psycopg 3.3.4, Alembic 1.19.1, DBOS 2.31.0, Pydantic 2.13.4, Pydantic AI/Evals 2.35.3, pytest 9.1.1, Ruff 0.16.5, Pyright 1.1.411. Frontend lock highlights: Next 16.3.3, React 19.2.8, TypeScript 5.9.3, TanStack Query 5.102.8, Vitest 4.1.11, openapi-typescript 7.13.0.

| Image | Observed immutable digest |
| --- | --- |
| `postgres:18` | `sha256:4ef4dbc939d61acea57712655ddb4b4ab27419c913f94cca0cd57cb3ea3c2280` |
| `python:3.13-slim-bookworm` | `sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e` |
| `node:24-alpine` | `sha256:50c8e8ca1d27439048670df5883f32d57cf81cff6233222c893fd0d9884cbd81` |
| `ghcr.io/astral-sh/uv:0.11.26` | `sha256:3d868e555f8f1dbc324afa005066cd11e1053fc4743b9808ca8025283e65efa5` |

Each exact pinned digest was independently read from its registry and verified as an OCI image index containing both `linux/amd64` and `linux/arm64` manifests. The local image architecture alone was not treated as proof of cross-platform support. The final pinned-image/patched-lock rebuild and health-checked startup passed.

## Remaining limits

- L01 is a local foundation audit; authentication and DBOS/Pydantic AI durability compatibility/acceptance belong to later owning tasks. No model, research-provider, Gmail or Calendar calls were made by the product.
- The existing frontend is a light foundation screen, not the required final dark-first product. No mobile/tablet or complete desktop product acceptance is claimed.
- `@types/node` remains the existing locked 20.x supporting dependency while runtime is Node 24; current source typechecks, but new Node APIs need aligned declarations before use.
- Image pins need deliberate future security updates; mutable host-tool selectors are documented separately from immutable container releases.
- The API readiness probe currently checks connectivity only, not schema revision, worker health or provider eligibility.
- CI definitions were inspected; a newly pushed commit's CI result must be recorded separately rather than inferred from prior runs or these local checks.

See [local development](../runbooks/local-development.md) for the exact operator commands and prerequisite troubleshooting. Passing this report does not authorize any live recipient campaign.
