# ADR 0003: Route automatic Gmail sending through a guarded deterministic gateway

**Status:** Accepted — 2026-08-28

## Context

Alon AI's product direction includes automatic Gmail outreach. A language model can help research prospects and create typed drafts, but direct agent access to Gmail would make policy enforcement, idempotency, auditability, and recovery unreliable. A repeated or non-compliant message can damage a solopreneur's reputation immediately.

## Decision

Automatic sending is a supported product capability, but agents cannot call Gmail directly. A deterministic `SendGateway` is the only intended path to a `GmailProvider`. It must require an idempotency key and recheck deterministic policy decisions before it invokes the provider. The eventual path records send intents and Gmail message/thread identifiers, and permanently quarantines an ambiguous write until positive Gmail Sent evidence resolves it. Zero search/history results never prove non-send or authorize retry; only explicit provider rejection or local pre-write proof can do so.

The current repository implements only the contracts and a default-off feature gate. It does not yet send real Gmail outreach.

## Consequences

- The design preserves automatic sending without granting a model unrestricted external authority.
- Policy checks can cover suppression, jurisdiction, campaign state, budget, rate limits, and a global kill switch in deterministic code.
- Each send can be audited and reconciled; an ambiguous provider outcome can never be retried or replaced on negative-search evidence.
- This adds implementation work before product sending can begin, including OAuth, queueing, persistence, policies, and recovery tests.
- `ALON_AI_OUTREACH_ENABLED=false` is a safety default, not a substitute for the required controls.

## Reconsideration trigger

Reconsider the gateway design only if controlled test evidence shows it cannot enforce idempotency, policy checks, audit records, and reconciliation around Gmail outcomes. Any alternative must preserve at least those guarantees; direct Gmail calls by agents are not an acceptable fallback.
