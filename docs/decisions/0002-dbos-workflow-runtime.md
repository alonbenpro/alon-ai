# ADR 0002: Select DBOS as the durable workflow runtime

**Status:** Accepted with mandatory production-acceptance gate — 2026-08-28

## Context

The product needs finite durable workflow runs, queues, schedules, rate limits, retries, timers, cancellation, and crash recovery around externally visible Gmail side effects. It also needs typed agent execution without adding a second agent-orchestration layer. The repository already uses Python, Pydantic, Pydantic AI, PostgreSQL, and a separately runnable worker, so a PostgreSQL-backed DBOS runtime minimizes the operating surface for one developer.

Runtime selection and production acceptance are separate decisions. The foundation has not demonstrated a DBOS workflow, Gmail adapter, or worker recovery around an ambiguous email result.

## Decision

Select Pydantic AI for typed agent execution, model/tool boundaries, structured artifacts, and evaluation integration. Select DBOS for finite durable workflows, queues, schedules, rate limits, retries, timers, and crash recovery on PostgreSQL. PostgreSQL remains the application system of record; DBOS persistence and product records keep explicit ownership.

M1 is the mandatory DBOS production-acceptance spike. Only its isolated disposable harness may send, and only to operator-owned test inboxes. Product outreach remains disabled until both M1 and M6 evidence gates pass; passing both makes the send path eligible for a later bounded real experiment but grants no recipient, campaign, or spending authority by itself. M1 must prove restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, and rate-limit enforcement under restart and concurrency. `SendGateway` remains the only application path to `GmailProvider`; agents and workflows cannot bypass deterministic policy, idempotency, the outbound-attempt ledger, provider-result capture, Sent-folder reconciliation, or bounded retry rules.

Any disqualifying M1 failure forces migration to Temporal before workflow product work continues. Convenience, sunk implementation cost, and lockfile presence cannot waive the fallback.

LangGraph and LangChain are agent-orchestration frameworks and are excluded from the initial stack because Pydantic AI already owns the required typed-agent layer. Restate is a separate durable runtime, and Prefect is a pipeline/task orchestrator; both are excluded from the initial stack because they do not improve the current product-risk gate. They are comparison history, not initial runtime dependencies.

## Consequences

- Later roadmap work has one agent framework and one durable runtime rather than an open vendor bakeoff.
- DBOS alignment with Python/PostgreSQL reduces initial deployment and operational complexity for a solo operator.
- M1 is necessary but not sufficient for product outreach: its disposable harness is test-inbox-only, and product outreach remains blocked until both M1 and M6 evidence gates pass.
- Gmail ambiguity remains an application/provider reconciliation problem even when DBOS recovers the workflow.
- Temporal migration work is mandatory after a disqualifying result, which deliberately makes failure visible before product workflows accumulate around an unsafe runtime.

## Reconsideration trigger

Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues. Reconsider the selected stack later only when retained evidence shows a concrete product requirement that Pydantic AI plus DBOS/Temporal cannot satisfy.
