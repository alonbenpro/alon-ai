# ADR 0001: Begin with a modular monolith

**Status:** Accepted — 2026-08-28

## Context

Alon AI is being built and operated by one developer. The future product needs an API, a worker, a PostgreSQL system of record, provider adapters, and policy-controlled side effects. Starting with independent services would add deployment, observability, and data-consistency work before the core workflow has earned that complexity.

## Decision

Use one Python backend package with explicit module boundaries. Run FastAPI and the worker as separate processes from that package. Keep PostgreSQL as the application system of record and keep integrations behind provider interfaces. The Next.js application remains a dashboard that consumes FastAPI's OpenAPI contract; it is not a second business backend.

## Consequences

- The code remains inspectable and operable on a small private deployment target.
- API and worker can have independent process lifecycles without duplicating domain logic.
- Module boundaries make later extraction possible if a measured operational need emerges.
- A single repository does not itself create resilience or scalability; workflow state, side-effect safety, backups, and observability still require evidence.
- Cross-module dependencies must stay intentional or the monolith will become a tangle.

## Reconsideration trigger

Reconsider extraction only when a measured constraint cannot be addressed inside the modular monolith: independently scaling workloads, a clear failure-isolation requirement, ownership boundaries larger than one operator, or a provider/runtime requirement that materially conflicts with the current process model.
