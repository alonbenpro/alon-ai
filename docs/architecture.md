# Architecture

## Scope and status

Alon AI is a modular monolith foundation for a future durable workflow that discovers service ideas, validates them with evidence, finds prospects, sends Gmail outreach, synchronizes replies, and evaluates experiments. This repository currently proves a smaller vertical slice: a Next.js dashboard reads a FastAPI API's database-backed readiness state from PostgreSQL, and a separate worker process starts with guarded configuration.

The foundation contains Gmail provider and deterministic sending-gateway contracts. Pydantic AI and DBOS are selected for future agent/workflow work, but this checkout does **not** implement a typed agent, DBOS workflow, Gmail adapter, OAuth flow, queue, schedule, outbound-attempt ledger, reconciliation worker, or production outreach. Nothing in this checkout sends email.

## Current runtime

```mermaid
flowchart LR
    Dashboard["Next.js dashboard"] -->|"GET /health/ready"| API["FastAPI API"]
    API -->|"database health check"| DB[("PostgreSQL 18")]
    Worker["Python worker process"] -->|"safe startup state only"| Config["typed configuration"]
    API --> Config
```

The API and worker are separately runnable processes from one Python package. PostgreSQL is the system of record. The frontend consumes the API's generated OpenAPI contract; generated TypeScript declarations are committed and CI rejects drift.

## Intended guarded sending path

This is the design boundary for the product, not a completed runtime path:

```mermaid
flowchart LR
    Agent["Pydantic AI typed artifact"] --> Intent["Send intent + idempotency key + attempt ledger"]
    Intent --> Policy["Deterministic policy checks"]
    Policy --> Queue["Durable queue and rate limits"]
    Queue --> Gateway["Deterministic SendGateway"]
    Gateway --> Provider["GmailProvider adapter"]
    Provider --> Gmail["Gmail API"]
    Gmail --> Reconcile["Sent-mail reconciliation + history sync"]
```

Pydantic AI agents must never call Gmail directly or hold unrestricted Gmail authority. DBOS workflows may coordinate finite work but cannot bypass the deterministic gateway. `SendGateway` must recheck suppression, jurisdictional rules, campaign state, budget, rate limits, and the global kill switch before a provider call. Each external send must have a stable idempotency key, outbound-attempt ledger, provider-result capture, audit record, operator-visible ambiguous state, and Sent-folder reconciliation. A possibly accepted write remains permanently quarantined until positive Sent evidence resolves it; retry is reserved for explicit rejection or local proof that no bytes left the process.

## Selected agent and workflow stack

- Pydantic AI owns typed agent execution, model/tool boundaries, structured artifacts, and evaluation integration.
- DBOS owns finite durable workflows, queues, schedules, retries, timers, and crash recovery on PostgreSQL.
- PostgreSQL remains the application system of record; DBOS persistence and product data keep explicit ownership.
- Deterministic domain/policy code owns business transitions, authorization, budgets, suppression, and external side effects.
- M1 is DBOS production acceptance, not outreach authorization. Only the isolated disposable M1 harness may send, and only to operator-owned test inboxes; product outreach remains disabled until both M1 and M6 evidence gates pass.
- Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues.
- Passing M1 and M6 grants no recipient, campaign, or spending authority by itself; bounded real-recipient authority remains a later experiment decision.

LangGraph and LangChain are excluded from the initial stack because the product does not need a second agent-orchestration abstraction beside Pydantic AI. Restate is a separate durable runtime and Prefect is pipeline/task orchestration; both are excluded because they do not improve the current gate. This classification records decision history without making them dependencies.

## Boundaries

| Boundary | Responsibility | Current state |
| --- | --- | --- |
| `frontend/` | Dashboard and generated OpenAPI client types | Implemented for readiness |
| `backend/src/alon_ai/api/` | HTTP API and OpenAPI source of truth | Implemented for health |
| `backend/src/alon_ai/db/` | SQLAlchemy engine and migrations | Implemented for readiness/migration base |
| `backend/src/alon_ai/worker/` | Separate worker process boundary | Startup boundary only |
| `backend/src/alon_ai/domain/` | Send gateway and domain contracts | Guarded contracts only |
| `backend/src/alon_ai/policies/` | Deterministic approval/denial interfaces | Contract only |
| `backend/src/alon_ai/providers/` | Gmail provider interface | Contract only; no Gmail adapter |
| `backend/src/alon_ai/agents/` | Pydantic AI typed-agent boundary | Reserved; selected but not implemented |
| `backend/src/alon_ai/workflows/` | DBOS durable workflow/queue/schedule boundary | Reserved; selected but not implemented or production-accepted |

## Operational constraints

- `ALON_AI_OUTREACH_ENABLED` defaults to `false`; it is a guard, not evidence that sending is implemented.
- The API has distinct liveness (`/health/live`) and database-backed readiness (`/health/ready`) endpoints.
- The foundation is intentionally not a deployment, billing, authentication, multi-user, or webhook system.
- DBOS is selected, but the next milestone must production-accept it for Gmail side effects. Any disqualifying failure requires Temporal before more workflow product work proceeds.

The governing design is [the approved foundation specification](superpowers/specs/2026-08-28-alon-ai-foundation-design.md). The stack decision and fallback are recorded in [ADR 0002](decisions/0002-dbos-workflow-runtime.md), and the ordered implementation gates are in the [development roadmap](development-roadmap/README.md).
