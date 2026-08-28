# Alon AI Development Roadmap Documentation Design

**Date:** 2026-08-28  
**Status:** Approved  
**Audience:** The solo developer operating Alon AI

## Purpose

Create a complete, ordered development roadmap under `docs/development-roadmap/`. The roadmap must turn the current foundation into an auditable, revenue-capable idea-validation system without pretending that unimplemented integrations, agents, workflows, or safety controls already exist.

The documentation is organized by subsystem for discoverability, but implementation order is governed by vertical milestones. A layer-first roadmap would defer integration and side-effect failures until too late.

## Product constraint

Alon AI is a single-operator product first. Authentication for one operator, controlled experiments, and operational safety precede billing, teams, multi-tenancy, public APIs, or generalized platform work. Every proposed component must justify itself against the next product-risk gate.

## Required roadmap structure

The roadmap root contains a master `README.md` plus these ordered segment folders:

1. `00-product-strategy/`
2. `01-architecture/`
3. `02-database/`
4. `03-workflows/`
5. `04-agents/`
6. `05-providers/`
7. `06-backend/`
8. `07-frontend/`
9. `08-security-and-compliance/`
10. `09-observability-and-evaluation/`
11. `10-testing/`
12. `11-infrastructure/`
13. `12-launch-and-operations/`

Each segment contains one detailed Markdown file per major implementation deliverable. The approved filenames are listed in the implementation plan.

## Global milestone order

| Milestone | Outcome | Exit gate |
| --- | --- | --- |
| M0 | Product scope, baseline evidence, metrics, and kill criteria are explicit | The operator can state what is being tested and when to stop |
| M1 | Durable-execution engine is selected through a DBOS-first Gmail recovery spike | Crash tests prove no uncontrolled duplicate sends; otherwise select Temporal or another proven alternative |
| M2 | Core PostgreSQL schema, event history, idempotency, and state machines exist | Migrations, constraints, audit events, and restore tests pass |
| M3 | Provider contracts and typed agents work offline with recorded evaluations | Versioned fixtures beat defined quality and cost thresholds |
| M4 | Idea, offer, and market-evidence workflow produces operator-reviewable artifacts | One synthetic experiment completes without outreach |
| M5 | Lead discovery and qualification produce evidence-backed, deduplicated prospects | Qualification evaluation and provenance gates pass |
| M6 | Operator-owned inboxes prove controlled Gmail sending, reconciliation, and reply sync | Kill/restart tests, suppression, rate limits, and audit evidence pass |
| M7 | The dashboard supports experiment control, approvals, funnel analysis, and decisions | Operator can run and diagnose a complete controlled experiment |
| M8 | Private deployment, monitoring, encrypted backups, and restore drills are proven | Fresh-server restore and incident exercises pass |
| M9 | The first real experiment runs with bounded authority | Scale/revise/kill decision is supported by recorded evidence |

No later milestone may be used to justify skipping an earlier exit gate.

## Workflow-engine decision gate

DBOS is provisional, not presumed superior. The roadmap must explicitly compare:

- DBOS as a PostgreSQL-backed durable workflow, queue, schedule, and rate-limit engine.
- Temporal as the mature durable-workflow fallback with separate service or cloud infrastructure.
- LangGraph as graph-oriented agent orchestration with persistence and human-in-the-loop; it overlaps workflow orchestration but does not replace deterministic send policy, idempotency, or reconciliation.
- Restate as a durable runtime with a separate server and journal.
- Prefect as a data-flow/task orchestrator, useful for pipeline workloads but not automatically the right side-effect engine.
- Pydantic AI and LangChain as agent-framework choices, not direct substitutes for durable business-workflow infrastructure.

The default experiment is Pydantic AI plus DBOS because the repository already uses Python, Pydantic, and PostgreSQL. The decision changes if DBOS fails restart, cancellation, duplicate-send, versioning, observability, or operator-control gates. Gmail ambiguity must be reconciled independently of the workflow engine because an API call may succeed before its local completion is durably recorded.

## Document contract

Every major-task file must contain:

1. Document ID, status, milestone, owner, prerequisites, outputs, unlocks, risk, and complexity.
2. Outcome and why it belongs at this point.
3. Current repository state with explicit implemented/missing boundaries.
4. Scope and non-goals.
5. Exact files/modules, symbols, tables, indexes, endpoints, routes, events, agent artifacts, or provider contracts to create or modify.
6. Ordered implementation tasks with checkbox syntax. Each task states inputs, operation, output, test evidence, and failure behavior.
7. Test strategy with named unit, integration, contract, recovery, security, accessibility, or end-to-end cases.
8. Security, privacy, compliance, idempotency, observability, and cost requirements where applicable.
9. Failure modes, rollback or disable path, and operator recovery procedure.
10. Acceptance criteria and evidence that must be retained.
11. Dependencies and the exact next deliverable unlocked.

Files may link to repeated global constraints rather than duplicate long explanations, but may not say “same as another file” in place of task-specific requirements.

## Architectural invariants

- FastAPI owns business behavior and the OpenAPI contract; Next.js is not a second backend.
- PostgreSQL is the application system of record.
- API and worker remain separate processes from one modular Python package.
- Agents produce typed, versioned artifacts; deterministic code owns state transitions and external side effects.
- Agents never call Gmail directly.
- `SendGateway` is the only application path to `GmailProvider`.
- Every external side effect has an idempotency key, policy decision, audit record, timeout, and reconciliation strategy.
- Outreach defaults off and fails closed.
- Provider integrations remain replaceable.
- Finite workflow runs replace immortal agent loops.
- Exact dependency versions come from lockfiles; roadmap prose names only intentional runtime constraints.
- No claims of production readiness, legal compliance, deployment, real users, or real sends without retained evidence.

## Quality constraints

- No `TBD`, `TODO`, “implement later,” or vague “add appropriate tests/error handling” language.
- No fake calendar estimates. Use complexity (`S`, `M`, `L`, `XL`) and risk (`Low`, `Medium`, `High`, `Critical`).
- Cross-links and milestone identifiers must resolve consistently.
- Every current/future statement must match the repository.
- Each segment must be useful independently, while the master README remains the authoritative execution order.

## Acceptance criteria

- All approved folders and files exist.
- The repository README links to the roadmap master index.
- The master README maps every file into one global execution sequence.
- DBOS is explicitly provisional and compared to adjacent and competing layers.
- Frontend, backend, database, workflows, agents, providers, security, observability, tests, infrastructure, and launch operations are covered.
- Every major task has prerequisites, ordered work, tests, failure handling, and a measurable exit gate.
- Placeholder, link, dependency, milestone, and contradiction scans pass.
- Existing application tests remain green.
