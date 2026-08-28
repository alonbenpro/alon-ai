# SendGateway and Gmail Side-Effect Protocol

**Document ID:** BACKEND-04
**Status:** Planned M6 full gateway; current implementation is a minimal in-memory guard only
**Milestone:** M6 after passing M1/M5 and all provider/policy/security prerequisites
**Owner:** Solo operator
**Prerequisites:** [PROVIDER-01](../05-providers/01-gmail-oauth-and-adapter.md), [PROVIDER-02](../05-providers/02-gmail-history-sync.md), [BACKEND-03](03-policy-engine.md), [DB-03](../02-database/03-leads-campaigns-and-messages.md), and [WF-05](../03-workflows/05-outreach-and-reply-workflow.md)
**Outputs:** Sole Gmail send call path, exact last-mile ordering, attempt/result transactions, ambiguity/reconciliation, retry handoff, and crash evidence
**Unlocks:** M6 controlled owned-inbox pilot and later separately authorized bounded product outreach eligibility
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

One queued immutable send intent can cause at most one provider invocation per numbered attempt, through one application service. The gateway rechecks current authority, commits the attempt before the network, calls Gmail once outside a transaction, and records direct acceptance, conclusive failure, or ambiguity. An unknown outcome is quarantined and reconciled; it is never retried as a generic exception. Product outreach remains disabled until both M1 and M6 pass; passing either or both grants no automatic campaign, recipient, or spend authority.

## Current repository state

`domain/sending.py` currently checks a boolean, awaits a minimal `SendPolicy`, and calls a protocol. It has no product tables, transaction, intent, attempt, provider adapter, stable RFC ID, result capture, cost, ambiguity, or reconciliation. No current code sends Gmail. The M6 target moves orchestration inward to `application/sending.py`; foundation DTOs remain only migration inputs until removed by a tested compatibility change.

## Scope and non-goals

In scope: intent prerequisites, exact ordering, policy/control/suppression/budget/rate/approval recheck, composite authority, one attempt/call, provider result capture, canonical states/events, cancellation, ambiguity, conclusive retry handoff, fixtures, and M1/M6 gating. Non-goals: content generation, recipient selection, provider retry loop, SMTP, direct workflow/agent calls, treating DBOS recovery as exactly-once, sending inside a database/outbox transaction, or deleting/rewriting sent evidence.

## Exact planned implementation surfaces

Create `application/sending.py` with `SendGateway`, `SendExecutionRequestV1`, and typed application errors; move provider-facing contracts to PROVIDER-01; create repository ports and M6 tests. Only API/worker composition constructs the gateway. Static rules permit exactly one production edge to `GmailProvider.send`: `SendGateway.execute_attempt`. Reconciliation/history receive only PROVIDER-02 read port.

### Prerecorded intent contract

`RecordSendIntent` is handled before gateway execution by BACKEND-05. It atomically loads the DB-03 campaign-version/member/message/mailbox/approval/allowed SEND policy composite, verifies exact `scope_hash/policy_facts_hash/policy_version`, reserves budget, derives stable `idempotency_key` and RFC `Message-ID`, inserts immutable `send_intents`, consumes approval when appropriate, transitions `APPROVED -> SEND_INTENT_RECORDED -> QUEUED`, emits `send.intent_recorded.v1` and `send.queued.v1`, audit/idempotency/outbox, then commits. Queue publication/dequeue cannot precede commit.

`SendExecutionRequestV1` contains only `send_intent_id`, expected message version, workflow run/version, command key, correlation/causation IDs, and cancellation token reference. The gateway loads every other authority field from PostgreSQL; runtime/agent input cannot supply/override it.

### Exact last-mile ordering

The order below is normative. Reordering that moves a provider call or mutable check earlier is a contract break.

1. Check cancellation and process/global dequeue disable before opening a unit of work.
2. Begin and lock the exact `send_intents`, `outreach_messages`, latest numbered attempt set, campaign version, member, lead/business, mailbox, approval, original `policy_decisions`, budget reservation/account, controls, suppression matches, and rate reservation/window.
3. Verify every DB-03 composite authority field byte-matches: experiment/campaign/version/lead/message/mailbox/approval/policy scope/version/allow flag/scope/facts/RFC identity. Verify intent/message expected versions and no unresolved `STARTED/AMBIGUOUS/RECONCILING` attempt.
4. Require M6 mode (`TEST_INBOX_SENDING=true`, `PRODUCT_OUTREACH=false`, owned alias) or later product mode (`PRODUCT_OUTREACH=true`, both M1/M6 evidence, exact bounded recipient/campaign/spend authority). A test control can never satisfy product mode.
5. Require experiment/campaign/lead/message/mailbox canonical eligibility and open send window.
6. Evaluate global, business, and recipient suppression; suppression always wins.
7. Verify approval remains `APPROVED`, unexpired, unrevoked, one-send cap, and exact content/artifact/campaign/mailbox/policy scope.
8. Rebuild BACKEND-03 facts using one injected UTC instant. The original allowed decision may replay only when policy version/scope/facts hashes are identical; any change records denial and no attempt. Verify jurisdiction, budget reservation, campaign caps, concurrency, rate capacity, retry bounds, and no ambiguity.
9. Allocate `attempt_number=attempt_count+1`; insert `send_attempts` carrying the exact intent composite with state `STARTED`, `started_at` and conservative `provider_called_at` set to the same pre-call UTC instant; increment immutable-intent `attempt_count`; transition message `QUEUED -> SENDING`; emit `policy.evaluated.v1` and `send.attempt_started.v1`; insert audit/idempotency/outbox; commit. Marking `provider_called_at` before network deliberately makes a crash conservative: recovery assumes the call may have begun.
10. Check cancellation again. Cancellation after the pre-call commit cannot prove no call; if it prevents network locally with retained proof, `SendRecoveryService` records conclusive no-call failure. If proof is incomplete, use ambiguity.
11. Decrypt exact recipient/subject/body only in bounded gateway memory, build PROVIDER-01 strict request/MIME, call `GmailProvider.send` exactly once, and erase references after use. No transaction remains open.
12. Begin result transaction; reload/lock exact intent/attempt/message and reject any identity/state mismatch. `GmailResultCaptureService` inserts one immutable `provider_results` evidence row before the state/event bundle commits.
13. For `ACCEPTED`, capture `outcome='ACCEPTED'`, attempt/message `SENT`, cost/budget reconciliation, `send.provider_accepted.v1`. For `CONCLUSIVE_REJECTION`, capture `REJECTED`, attempt `FAILED`, message `FAILED_RETRYABLE` only if deterministic recovery eligibility exists else `FAILED_PERMANENT`, `send.failed.v1`, release/reconcile budget. For `UNKNOWN` or exception after call might begin, capture `UNKNOWN`, attempt/message `AMBIGUOUS`, `send.outcome_ambiguous.v1`; retain reservation until reconciliation policy resolves.
14. Commit, then schedule only the appropriate finite follow-up. `AMBIGUOUS` schedules PROVIDER-02 reconciliation, never send retry. All exceptions are converted into one typed application outcome; the queue/runtime cannot automatically rerun the provider step.

### State/event/result and retry semantics

| Evidence | Attempt/message | Exact event | Next owner |
| --- | --- | --- | --- |
| parsed direct Gmail acceptance with IDs | `SENT` / `SENT` | `send.provider_accepted.v1` | none/reply sync |
| conclusive no-send provider rejection | `FAILED` / retryable or permanent by guards | `send.failed.v1` | `SendRecoveryService` |
| timeout/transport/5xx/malformed success/crash with possible call | `AMBIGUOUS` / `AMBIGUOUS` | `send.outcome_ambiguous.v1` | PROVIDER-02 read reconciliation |
| prior ambiguity, exactly one authorized Sent match | `SENT` / `SENT` | `send.reconciled_as_sent.v1` | none/reply sync |
| conclusive absence after bounded window | `FAILED` / `FAILED_RETRYABLE` only if all guards | `send.failed.v1` | `SendRecoveryService` |
| multiple/cross-mailbox/malformed evidence | failed/conflict / `FAILED_PERMANENT` through recovery | `send.failed.v1` plus incident/audit | operator recovery |

`SendRecoveryService` alone owns `FAILED_RETRYABLE -> QUEUED`. It preserves the same intent/mailbox/RFC identity, requires `attempt_count < max_attempts`, before `retry_deadline`, due retry time, conclusive no-send, no unresolved ambiguity, and every current policy/control/budget/rate guard. It emits `send.retry_scheduled.v1`; exhaustion/operator abort emits `send.retry_exhausted.v1` and `FAILED_PERMANENT`. Runtime timers only wake this decision.

Cancellation/pause/global disable prevents new gateway calls immediately at checked boundaries but cannot turn a possibly called attempt into `CANCELLED`. Campaign cancel may cancel only pre-provider queued messages; `SENDING/AMBIGUOUS/RECONCILING` must resolve. Product campaign completion/failure waits for all outcomes terminal/reconciled.

### Application errors, fixtures, telemetry, and example

Gateway failures are internal typed reasons mapped exactly to BACKEND-02: `SEND_DISABLED`, `SEND_POLICY_DENIED`, `SEND_SUPPRESSED`, and `SEND_APPROVAL_INVALID` -> 403 `POLICY_DENIED`; `SEND_AUTHORITY_MISMATCH`, `SEND_STATE_INVALID`, `SEND_UNRESOLVED_ATTEMPT`, `SEND_CANCELLED_BEFORE_CALL`, `SEND_OUTCOME_AMBIGUOUS`, and `SEND_RESULT_CONFLICT` -> 409 `STATE_TRANSITION_DENIED`, except a resend/requeue while ambiguous uses 409 `AMBIGUOUS_SEND_REQUIRES_RECONCILIATION`; `SEND_BUDGET_DENIED` -> 429 `BUDGET_EXHAUSTED`; `SEND_RATE_DENIED` -> 429 `RATE_LIMITED`; `SEND_PROVIDER_CONCLUSIVE_FAILURE` -> 503 `DEPENDENCY_UNAVAILABLE` only when an HTTP caller is awaiting that internal result; `SEND_PERSISTENCE_FAILED` -> 500 `INTERNAL_ERROR`. The typed reason remains in safe `reason_codes`; it never replaces Gmail/provider errors or ARCH-03 event names.

Fixtures combine exact DB-03 authority rows, policy facts/decision, provider request/result, crash boundary, expected rows/events/call count, and RFC 8785 hashes. Required kill points: before intent commit; after queue commit; after attempt commit before HTTP; during request write; after provider acceptance before local result; during result transaction; after result commit before workflow acknowledgement; every reconciliation poll/result commit. M1 uses only its two-table analog; product fixtures use M2 tables and never import spike data.

Telemetry includes safe experiment/campaign/message/mailbox/intent/attempt/policy/approval/correlation/provider-request IDs, versions, call count, boundary, duration, outcome/error, ambiguity age, retry eligibility, and cost. It excludes addresses/content/MIME/tokens/provider bodies. `SendGateway` has no public/API DTO containing plaintext.

## Ordered implementation tasks

- [ ] **Implement intent and gateway contracts —** Input: DB-03 composites, ARCH-03 states/events, provider/policy contracts. Operation: encode execution request, errors, repositories, stable identity, and static sole-call rule. Output: importable application gateway. Test evidence: schema/composite/call-graph snapshots. Failure behavior: no provider composition.
- [ ] **Implement exact pre-call transaction/order —** Input: queued intent/current facts. Operation: lock/recheck in normative order, replay/evaluate policy, reserve rate, insert attempt/state/events/idempotency/outbox, commit. Output: one conservative started attempt. Test evidence: failure injection and one-field race/splice matrix. Failure behavior: rollback/no call.
- [ ] **Implement one provider call and result transactions —** Input: committed attempt and strict provider result. Operation: call once outside transaction, capture evidence, transition/event/cost atomically. Output: accepted/conclusive/ambiguous result. Test evidence: provider status/exception/cancellation and crash matrix. Failure behavior: possible acceptance always ambiguity.
- [ ] **Implement reconciliation/retry handoff —** Input: ambiguous or conclusively failed attempt. Operation: delegate mailbox read, then deterministic recovery guards; prohibit runtime/provider retry. Output: terminal or exactly queued next attempt. Test evidence: zero/one/many/absence/exhaustion tests. Failure behavior: controls off/incident/operator-visible unresolved.
- [ ] **Prove M6 authority and observability —** Input: owned aliases, M1 evidence, controls, queue/rate manifest, fixtures/live captures. Operation: execute restart/concurrency/control/suppression matrix and verify zero uncontrolled duplicates/post-control calls. Output: M6 gateway evidence. Test evidence: full signed trace/call counts. Failure behavior: M6 fails and both controls false.

## Test strategy

- **Ordering `test_sendgateway_checks_every_gate_in_exact_order_before_one_call`:** spies and denial at each step.
- **Relational `test_gateway_rejects_every_cross_scope_authority_splice_before_credential_access`:** PostgreSQL composites.
- **Recovery `test_kill_after_possible_acceptance_is_ambiguous_and_reconciles_without_resend`:** stable RFC ID.
- **Events `test_direct_and_reconciled_acceptance_events_are_never_interchanged`:** payload snapshots.
- **Retry `test_only_sendrecoveryservice_can_requeue_conclusive_failure_with_all_guards`:** no ambiguity edge.
- **Security `test_gateway_plaintext_and_credentials_never_escape_bounded_memory_or_logs`:** scan/call graph.

## Security, privacy, compliance, idempotency, observability, and cost

Authority is the complete immutable composite, not any single ID. Stable mailbox command/intent/RFC keys and numbered attempts prevent accidental duplicates but do not claim Gmail idempotency. Decrypted values are minimized and zeroized by lifetime; safety evidence retains hashes/IDs. Every call is policy/budget/rate/correlation/cost linked. DB-06 ambiguity/incident/suppression holds prevent unsafe purge. Compliance facts are operator/legal configuration, never model output.

## Failure, rollback, and operator recovery

On duplicate call, impossible state, tuple mismatch, post-control call, conflicting candidate, or persistence uncertainty: disable both controls, stop dequeue/workers, preserve evidence, reconcile every possible call, and open an incident. Roll back code using M1-proven workflow drain/versioning. Resolve only through typed reconcile/repair commands with before/after hashes; never direct SQL or resend to “see what happens.”

## Acceptance and retained evidence

- [ ] Exactly one application edge reaches `GmailProvider.send`; agents/workflows/routes/read services cannot bypass it.
- [ ] Pre-call order and two transaction boundaries preserve policy/approval/budget/intent/attempt authority.
- [ ] Every possible provider outcome has exact rows/states/events/cost/recovery and no blind retry.
- [ ] M6 owned-inbox and later product authority remain separate and fail-closed.
- [ ] Crash/control/concurrency proof shows zero uncontrolled duplicates and hidden ambiguity.

Retain call/import graph, service/schema snapshots, composite-FK tests, exact ordering traces, provider/error/cancel/crash/reconciliation/retry fixtures, queue/rate/control manifests, cost/audit/event chains, plaintext/secret scans, and signed M6 evidence.

## Dependencies and next deliverable

BACKEND-04 depends on PROVIDER-01/02, BACKEND-03, DB-03/05, and WF-05/06. It unlocks the M6 test-inbox pilot only; passing M6 makes a later separately authenticated bounded product experiment eligible, not authorized automatically.
