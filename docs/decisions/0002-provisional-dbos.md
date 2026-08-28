# ADR 0002: Treat DBOS as provisional workflow infrastructure

**Status:** Accepted provisionally — 2026-08-28

## Context

The product needs finite, durable workflow runs, queues, rate limits, retries, cancellation, and recovery around externally visible Gmail side effects. DBOS is a candidate for these responsibilities, but the foundation has not yet demonstrated its behavior when a worker crashes around an email send.

## Decision

Keep a DBOS workflow boundary in the backend and defer substantive workflow implementation until a dedicated DBOS/Gmail recovery spike. DBOS is not accepted as production-safe merely because its dependency is installed or its module exists.

## Consequences

- The foundation avoids committing business workflows to an unproven recovery model.
- The next milestone has a crisp, testable scope: finite scheduled runs, typed artifacts, rate-limited test sends, reply synchronization, cancellation, and crash recovery.
- Product outreach remains blocked until the spike proves the required behavior.
- Delaying the decision costs a short spike now but avoids reputational damage from duplicate or uncontrolled messages later.

## Reconsideration trigger

Replace DBOS with Temporal before building further workflow product work if the spike fails crash-recovery, cancellation, or duplicate-send tests. A failure in any of those tests is disqualifying; convenience is not a reason to accept unsafe side effects.
