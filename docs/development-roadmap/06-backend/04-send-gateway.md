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

`RecordSendIntent` is handled before gateway execution by BACKEND-05. It atomically loads the exact DB-03 campaign/version/`campaign_member_id`/message/mailbox/approved-row composite and the allowed `APPROVAL_ELIGIBILITY` decision/basis bound by that row. It verifies the immutable `scope_hash` and eligibility decision/facts/version, but never treats eligibility as SEND authority or requires later mutable facts to equal its facts hash. It reserves budget, derives stable mailbox `idempotency_key`/RFC `Message-ID`, inserts `send_intents`, consumes approval, transitions `APPROVED -> SEND_INTENT_RECORDED -> QUEUED`, emits `send.intent_recorded.v1` and `send.queued.v1`, audit/idempotency/outbox, then commits. Queue publication/dequeue cannot precede commit.

`SendExecutionRequestV1` contains only `send_intent_id`, expected message version, workflow run/version, command key, correlation/causation IDs, and cancellation token reference. The gateway loads every authority field from PostgreSQL; runtime/agent input cannot supply or override it.

### Exact last-mile ordering

The order below is normative. Reordering any provider call or mutable check is a contract break.

1. Check cancellation and process/global dequeue disable before opening a unit of work.
2. Begin a serializable transaction and lock exact intent, message, campaign version/member, lead/business, mailbox, approval, eligibility decision, budget/account, controls, suppressions, current attempts, and the mailbox rate window/active lease set.
3. Verify every immutable DB-03 authority field byte-matches: experiment/campaign/version/`campaign_member_id`/lead/message/mailbox/approval/eligibility scope+decision+version+allowed/facts hash/basis scope hash/RFC identity. Require `send_intents.open_for_attempt=true` and `cancelled_at IS NULL`, expected versions, and no unresolved `STARTED/AMBIGUOUS/RECONCILING` attempt.
4. Require M6 test mode or later product mode exactly as BACKEND-03 defines; test control never satisfies product mode.
5. Require current experiment/campaign/member/lead/message/mailbox eligibility and open window.
6. Verify approval is exact `CONSUMED`, was operator-approved, remains unexpired/unrevoked, cap one, is referenced by exactly this unique `send_intents.approval_id`, and binds the same eligibility decision/basis. ApprovalRule exists only in final SEND.
7. Under the same locks, build new `SendPolicyFactsV1` with the approved row and every current recipient identity/evidence, jurisdiction/evidence, affirmative consent or counsel-exception evidence/timestamps/expiry, legal review/policy, disclosure/sender template ID-version-hash/validator, Google-policy review/compatibility, reply/unsubscribe/hard-bounce/complaint/soft-bounce-limit observation, suppression/control/gate/budget/campaign/window/retry/ambiguity/rate fact using one injected UTC instant. Verify every accepted artifact tuple against DB-03/04 and every stop observation against DB-03. Reuse only the immutable `scope_hash`; never reuse eligibility/queued facts or require equality with `eligibility_facts_hash`.
8. Evaluate and record a new `scope='SEND'` policy decision. Any non-suppression denial commits only its policy/audit/idempotent denial result and releases command-local reservations. If denial contains `GLOBAL_SUPPRESSED`, `BUSINESS_SUPPRESSED`, or `RECIPIENT_SUPPRESSED`, atomically transition message `QUEUED -> SUPPRESSED`, atomically flip one-way intent `open_for_attempt=false` and set `cancelled_at/cancellation_reason`, emit `send.suppressed.v1`, release the unsent budget/queue reservation, insert audit/idempotent result/outbox, and commit with zero rate reservation, attempt, credential access, or provider call.
9. Only for allowed SEND: allocate the unique `(mailbox_id,rate_policy_version,window_start,slot_number)` and concurrency lease; insert `send_rate_reservations(RESERVED)`, change it to `CONSUMED`, allocate `attempt_number=attempt_count+1`, and insert `send_attempts` carrying the exact intent composite plus fresh SEND decision and the reservation's immutable concurrency token/non-null `consumed_at` evidence. The composite FK cannot reference a still-`RESERVED` row. Increment attempt count; transition `QUEUED -> SENDING`; set conservative `provider_called_at=started_at`; emit `policy.evaluated.v1`/`send.attempt_started.v1`, audit/idempotent result/outbox; commit. The partial unique active-mailbox lease and slot unique choose one concurrent winner. DBOS remains the outer queue/limiter; PostgreSQL is the final capacity authority.
10. Check cancellation again. If retained proof shows the network call did not begin, recovery records conclusive no-call failure and releases the consumed rate lease. If proof is incomplete, use ambiguity and retain the lease.
11. Decrypt exact recipient/subject/body only in bounded gateway memory, build PROVIDER-01 request from the attempt's fresh SEND tuple, call `GmailProvider.send` exactly once, then erase references. No transaction remains open.
12. Begin result transaction; reload/lock exact intent/attempt/rate reservation/message and reject identity/state mismatch. `GmailResultCaptureService` inserts immutable provider evidence before the state/event bundle.
13. For accepted or conclusive rejection, capture the result, transition attempt/message and canonical event, reconcile budget/cost, and change the consumed rate lease to `RELEASED`. For unknown/possibly-called failure, capture `UNKNOWN`, transition attempt/message `AMBIGUOUS`, emit `send.outcome_ambiguous.v1`, and keep the lease `CONSUMED` so no concurrent mailbox call starts. Recovery changes it to `RELEASED` only after terminal provider evidence or to `EXPIRED` only after conclusive no-call/no-send evidence; wall-clock lease expiry alone never authorizes another call.
14. Commit, then schedule only the finite follow-up. `AMBIGUOUS` schedules PROVIDER-02 reconciliation, never send retry. Runtime replay returns the stored command result and cannot rerun the provider step.

### State/event/result and retry semantics

| Evidence | Attempt/message | Exact event | Next owner |
| --- | --- | --- | --- |
| parsed direct Gmail acceptance with IDs | `SENT` / `SENT` | `send.provider_accepted.v1` | none/reply sync |
| conclusive no-send provider rejection | `FAILED` / retryable or permanent by guards | `send.failed.v1` | `SendRecoveryService` |
| timeout/transport/5xx/malformed success/crash with possible call | `AMBIGUOUS` / `AMBIGUOUS` | `send.outcome_ambiguous.v1` | PROVIDER-02 read reconciliation |
| prior ambiguity, exactly one authorized Sent match | `SENT` / `SENT` | `send.reconciled_as_sent.v1` | none/reply sync |
| conclusive absence after bounded window | `FAILED` / `FAILED_RETRYABLE` only if all guards | `send.failed.v1` | `SendRecoveryService` |
| multiple/cross-mailbox/malformed evidence | failed/conflict / `FAILED_PERMANENT` through recovery | `send.failed.v1` plus incident/audit | operator recovery |

`SendRecoveryService` alone owns `FAILED_RETRYABLE -> QUEUED`. It preserves the intent's experiment/campaign/member/approval-basis/mailbox/RFC identity, requires `attempt_count < max_attempts`, before `retry_deadline`, due retry time, conclusive no-send, no unresolved ambiguity or active consumed rate lease, and every current control/budget/rate guard. A later attempt gets another fresh SEND decision/facts hash and another unique rate slot. It emits `send.retry_scheduled.v1`; exhaustion/operator abort emits `send.retry_exhausted.v1` and `FAILED_PERMANENT`. Runtime timers only wake this decision.

Cancellation/pause/global disable prevents new gateway calls immediately at checked boundaries but cannot turn a possibly called attempt into `CANCELLED`. Campaign cancel may cancel only pre-provider queued messages; `SENDING/AMBIGUOUS/RECONCILING` must resolve. Product campaign completion/failure waits for all outcomes terminal/reconciled.

### Application errors, fixtures, telemetry, and example

The fixture registry combines exact DB-03 compliance-artifact tuples, all 14 dedicated compliance/signal denial branches, fresh final-SEND facts, observed-suppression races, and expected policy/audit/report/UI projections. A successful provider fixture carries only final decision/scope/facts hashes—not recipient, consent, legal, disclosure or observation payload.

Gateway failures are internal typed reasons mapped exactly to BACKEND-02: eligibility can never reach the gateway; `SEND_DISABLED`, `SEND_POLICY_DENIED`, `SEND_SUPPRESSED`, and `SEND_APPROVAL_INVALID` -> 403 `POLICY_DENIED` (suppression still commits its terminal no-call bundle); `SEND_AUTHORITY_MISMATCH`, `SEND_STATE_INVALID`, `SEND_UNRESOLVED_ATTEMPT`, `SEND_CANCELLED_BEFORE_CALL`, `SEND_OUTCOME_AMBIGUOUS`, and `SEND_RESULT_CONFLICT` -> 409 `STATE_TRANSITION_DENIED`, except a resend/requeue while ambiguous uses 409 `AMBIGUOUS_SEND_REQUIRES_RECONCILIATION`; `SEND_BUDGET_DENIED` -> 429 `BUDGET_EXHAUSTED`; `SEND_RATE_DENIED` -> 429 `RATE_LIMITED`; `SEND_PROVIDER_CONCLUSIVE_FAILURE` -> 503 `DEPENDENCY_UNAVAILABLE` only when an HTTP caller is awaiting that internal result; `SEND_PERSISTENCE_FAILED` -> 500 `INTERNAL_ERROR`. The typed reason remains in safe `reason_codes`; it never replaces Gmail/provider errors or ARCH-03 event names.

Fixtures combine exact DB-03 authority rows, eligibility decision/basis, approval, independent final SEND decision/facts, rate reservation/slot/lease, provider request/result, suppression branch, crash boundary, expected rows/events/call count, and RFC 8785 hashes. Required kill points: before intent commit; after queue commit; after attempt commit before HTTP; during request write; after provider acceptance before local result; during result transaction; after result commit before workflow acknowledgement; every reconciliation poll/result commit. M1 uses only its two-table analog; product fixtures use M2 tables and never import spike data.

Telemetry includes safe experiment/campaign/member/message/mailbox/intent/attempt/eligibility/final-SEND/approval/rate-reservation/window-slot/correlation/provider-request IDs and hashes, versions, call count, boundary, duration, outcome/error, ambiguity age, retry eligibility, and cost. It excludes addresses/content/MIME/tokens/provider bodies. `SendGateway` has no public/API DTO containing plaintext.

## Ordered implementation tasks

- [ ] **Implement intent and gateway contracts —** Input: DB-03 composites, ARCH-03 states/events, provider/policy contracts. Operation: encode execution request, errors, repositories, stable identity, and static sole-call rule. Output: importable application gateway. Test evidence: schema/composite/call-graph snapshots. Failure behavior: no provider composition.
- [ ] **Implement exact pre-call transaction/order —** Input: queued eligibility-bound intent/current facts. Operation: lock/recheck, create fresh SEND decision, commit suppression with no attempt or atomically consume a unique rate lease plus attempt/state/events/idempotency/outbox. Output: terminal suppressed result or one conservative started attempt. Test evidence: stale/mutable-fact matrix, failure injection, concurrent lease/slot, suppression no-call, and one-field splice tests. Failure behavior: deterministic denial/rollback and no call.
- [ ] **Implement one provider call and result transactions —** Input: committed attempt and strict provider result. Operation: call once outside transaction, capture evidence, transition/event/cost atomically. Output: accepted/conclusive/ambiguous result. Test evidence: provider status/exception/cancellation and crash matrix. Failure behavior: possible acceptance always ambiguity.
- [ ] **Implement reconciliation/retry handoff —** Input: ambiguous or conclusively failed attempt. Operation: delegate mailbox read, then deterministic recovery guards; prohibit runtime/provider retry. Output: terminal or exactly queued next attempt. Test evidence: zero/one/many/absence/exhaustion tests. Failure behavior: controls off/incident/operator-visible unresolved.
- [ ] **Prove M6 authority and observability —** Input: owned aliases, M1 evidence, controls, queue/rate manifest, fixtures/live captures. Operation: execute restart/concurrency/control/suppression matrix and verify zero uncontrolled duplicates/post-control calls. Output: M6 gateway evidence. Test evidence: full signed trace/call counts. Failure behavior: M6 fails and both controls false.

## Test strategy

- **Ordering `test_sendgateway_checks_every_gate_in_exact_order_before_one_call`:** spies and denial at each step.
- **Relational `test_gateway_rejects_every_cross_scope_authority_splice_before_credential_access`:** includes `campaign_member_id`, eligibility, approval basis, final SEND, and consumed rate reservation composites.
- **Compliance `test_gateway_rechecks_all_recipient_legal_disclosure_google_and_stop_signal_facts_at_final_send`:** one fixture per dedicated denial and one complete allow; generic reason substitution, stale/cross-recipient evidence and queued-fact reuse fail before attempt/credential/provider.
- **Observed stop race `test_signal_suppression_transaction_wins_or_gateway_commits_before_call_with_no_unobserved_gap`:** serializable lock order, crash injection and product-off fallback prove no next provider call after a committed signal.
- **Policy `test_gateway_creates_fresh_send_decision_with_same_basis_and_independent_facts_hash`:** no circular facts equality.
- **Rate `test_two_concurrent_gateway_calls_have_one_consumed_slot_and_attempt`:** loser is 429 `RATE_LIMITED`.
- **Suppression `test_last_mile_suppression_commits_message_intent_event_and_zero_attempt_call`:** exact row/event counts.
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
- [ ] Pre-call order preserves eligibility/approval basis, creates fresh final SEND authority, and atomically consumes one PostgreSQL rate slot with the attempt.
- [ ] Last-mile suppression commits `SUPPRESSED`/intent cancellation/event and zero attempt/provider call.
- [ ] Every possible provider outcome has exact rows/states/events/cost/recovery and no blind retry.
- [ ] M6 owned-inbox and later product authority remain separate and fail-closed.
- [ ] Crash/control/concurrency proof shows zero uncontrolled duplicates and hidden ambiguity.

Retain call/import graph, service/schema snapshots, composite-FK tests, exact ordering traces, provider/error/cancel/crash/reconciliation/retry fixtures, queue/rate/control manifests, cost/audit/event chains, plaintext/secret scans, and signed M6 evidence.

## Dependencies and next deliverable

BACKEND-04 depends on PROVIDER-01/02, BACKEND-03, DB-03/05, and WF-05/06. It unlocks the M6 test-inbox pilot only; passing M6 makes a later separately authenticated bounded product experiment eligible, not authorized automatically.
