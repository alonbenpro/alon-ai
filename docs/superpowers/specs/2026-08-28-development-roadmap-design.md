# Alon AI Development Roadmap Documentation Design

> **Historical design record — superseded and non-governing.** This document records the 2026-08-28 roadmap decisions and must not be used to direct current implementation, approval policy, or stage decisions. The authoritative sources are the [Autonomous Sales-Validation Roadmap Design](2026-09-08-autonomous-sales-validation-roadmap-design.md) and the governing [development roadmap](../../development-roadmap/README.md). In particular, their autonomous conversation authority and checkpoint model supersede any legacy per-message approval or `SCALE`/`REVISE`/`KILL` wording retained below.

**Date:** 2026-08-28
**Status:** Approved on 2026-08-28 (historical; superseded and non-governing)
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
| M1 | DBOS is proven safe enough for the product through a Gmail production-acceptance spike | Crash tests prove no uncontrolled duplicate sends; any disqualifying failure forces migration to Temporal before workflow product work continues |
| M2 | Core PostgreSQL schema, event history, idempotency, and state machines exist | Migrations, constraints, audit events, and restore tests pass |
| M3 | Provider contracts and typed agents work offline with recorded evaluations | Versioned fixtures beat defined quality and cost thresholds |
| M4 | Idea, offer, and market-evidence workflow produces operator-reviewable artifacts | One synthetic experiment completes without outreach |
| M5 | Lead discovery and qualification produce evidence-backed, deduplicated prospects | Qualification evaluation and provenance gates pass |
| M6 | Operator-owned inboxes prove controlled Gmail sending, reconciliation, and reply sync | Kill/restart tests, suppression, rate limits, and audit evidence pass |
| M7 | The dashboard supports experiment control, approvals, funnel analysis, and decisions | Operator can run and diagnose a complete controlled experiment |
| M8 | Private deployment, monitoring, encrypted backups, and restore drills are proven | Fresh-server restore and incident exercises pass |
| M9 | The first real experiment runs with bounded authority | Scale/revise/kill decision is supported by recorded evidence |

No later milestone may be used to justify skipping an earlier exit gate.

## Selected agent and durable-workflow stack

Alon AI selects Pydantic AI plus DBOS on PostgreSQL. This is an architecture decision, not an open vendor bakeoff:

- Pydantic AI owns typed agent execution, model/tool boundaries, structured artifacts, and evaluation integration.
- DBOS owns finite durable workflows, queues, schedules, retries, timers, and crash recovery.
- PostgreSQL remains the product system of record and the DBOS persistence dependency, with product and workflow ownership kept explicit.
- Deterministic domain and policy code owns state transitions, budgets, suppression, authorization, and every externally visible side effect.
- `SendGateway` remains the only application path to `GmailProvider`; agents and workflows cannot bypass it.

DBOS is selected because it fits the existing Python/Pydantic/PostgreSQL stack and minimizes the operating surface for a solo developer. Selection and M1 acceptance do not authorize product outreach. Only the isolated disposable M1 harness may send, and only to operator-owned test inboxes; product outreach remains disabled until both M1 and M6 evidence gates pass. Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues. Convenience, sunk implementation cost, or lockfile presence cannot waive that fallback.

LangGraph and LangChain are excluded from the initial stack because Alon AI does not currently need a second agent orchestration abstraction. Restate and Prefect are also excluded from the initial stack because they add a separate runtime or a pipeline-oriented model without improving the current product-risk gate. The roadmap retains a concise comparison record so future maintainers understand the layer distinction and the evidence that would justify reconsideration.

Gmail ambiguity must be reconciled independently of DBOS because an API call may succeed before its local completion is durably recorded. The design therefore requires a stable send idempotency key, outbound-attempt ledger, provider-result capture, Sent-folder reconciliation, and operator-visible permanent quarantine. Zero Gmail search/history results never prove non-send and cannot authorize retry or replacement; retry requires explicit provider rejection or local pre-write proof that bytes never left the process.

## Graphify-first repository navigation

Repository agents must use Graphify before broad project discovery. This rule is persisted in a root `AGENTS.md` and expanded in `docs/engineering/graphify-first-navigation.md`.

The required sequence is:

1. Run from the active checkout root, never from another worktree.
2. If `graphify-out/graph.json` exists, run `graphify reflect --if-stale`, read `graphify-out/reflections/LESSONS.md`, expand the question against the graph vocabulary, and run `graphify query` before broad text search or opening many files.
3. If the graph is absent, invoke the Graphify workflow on the checkout root, then query it.
4. Use `rg`, targeted file reads, and direct symbol inspection only after Graphify identifies likely files, locations, or missing coverage.
5. Save useful, dead-end, or corrected query outcomes as Graphify memory.
6. Run an incremental Graphify update after tracked code or documentation changes; the local post-commit hook keeps code changes current, while documentation changes still require the explicit update.

Exact-path edits, tests, builds, formatting, and Git status checks do not require a graph query because they are not repository discovery. Graphify output remains local and ignored so generated artifacts and query memory do not pollute commits. The repository instruction and navigation documents are versioned, and the local Graphify post-commit hook is installed in the current clone.

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
- Pydantic AI and DBOS are the selected initial agent/workflow stack; Temporal is the mandatory durable-runtime fallback after a disqualifying M1 failure.
- LangChain, LangGraph, Restate, and Prefect are not initial runtime dependencies.
- Agents perform Graphify-first repository discovery according to the root `AGENTS.md`.
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
- Pydantic AI and DBOS are selected, their responsibilities do not overlap, only the isolated disposable M1 harness may send to operator-owned test inboxes, and product outreach remains disabled until both M1 and M6 evidence gates pass.
- Temporal is the mandatory fallback after a disqualifying DBOS failure; adjacent frameworks and runtimes are accurately recorded but excluded from the initial stack.
- Root agent instructions and the engineering navigation guide enforce Graphify-first repository discovery without requiring it for exact-path or verification-only work.
- Frontend, backend, database, workflows, agents, providers, security, observability, tests, infrastructure, and launch operations are covered.
- Every major task has prerequisites, ordered work, tests, failure handling, and a measurable exit gate.
- Placeholder, link, dependency, milestone, and contradiction scans pass.
- Existing application tests remain green.
