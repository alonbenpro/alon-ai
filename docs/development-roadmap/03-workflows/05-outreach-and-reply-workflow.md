# Controlled Outreach, Gmail Reconciliation, and Reply Workflow

**Document ID:** WF-05
**Status:** Planned M6 test-inbox product workflow; product outreach disabled
**Milestone:** M6
**Owner:** Solo operator
**Prerequisites:** passing M1/M5, complete M2 schema, promoted M3 draft/reply agents, [WF-02](02-experiment-lifecycle.md), [DB-03](../02-database/03-leads-campaigns-and-messages.md), Gmail OAuth/adapter/history sync, deterministic policy/suppression/budget/approval services, and isolated operator-owned test inboxes
**Outputs:** Finite campaign/send/reconciliation/sync runs, no-duplicate evidence, reply records/classifications, kill/control/rate evidence, and M6 gate bundle
**Unlocks:** M6 exit and later eligibility to enable bounded product outreach; never automatic real-recipient authority
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

M6 proves the complete product-shaped Gmail loop against operator-owned inboxes: draft/approve, intent, queue, last-mile policy, send, ambiguous reconciliation, history cursor, reply, classification, pause/cancel/restart, suppression, and audit. During the pilot, `TEST_INBOX_SENDING` may be enabled for an exact owned-alias allowlist while `PRODUCT_OUTREACH` remains `false`. Only after the retained M6 gate passes can an authenticated later command consider product outreach, and that command still requires M1, recipient/campaign authority, and every deterministic gate.

## Current repository state

There is no product table/workflow, Gmail OAuth/adapter/history sync, policy/suppression/budget implementation, approval, UI control, or send. The minimal `SendGateway` contract has no durable ledger or provider. No current behavior satisfies M6.

## Scope and non-goals

In scope: owned test aliases, exact-scope draft approval, stable intent/RFC identity, DBOS queues/timers/recovery, sole `SendGateway` call, provider result capture, ambiguous Sent reconciliation, bounded conclusive retry, history cursor/replies, typed reply classification, suppression, controls, and gate evidence. Non-goals: real prospects, bulk throughput, agent send authority, blind retry, claiming SMTP delivery/read, automatic response, long-lived open campaign workflow, or using DBOS recovery as provider exactly-once.

## Exact planned implementation surfaces

Create `workflows/outreach.py`, `workflows/send_message.py`, `workflows/gmail_reconciliation.py`, `workflows/gmail_history_sync.py`, `application/sending.py`, and M6 contract/recovery tests.

Exact product tables touched through application commands are `experiments`, `workflow_runs`, `campaigns`, `campaign_members`, `leads`, `approvals`, `suppression_entries`, `system_controls`, `budget_reservations`, `policy_decisions`, `outreach_messages`, `send_intents`, `send_attempts`, `provider_results`, `provider_observations`, `replies`, `gmail_mailboxes`, `gmail_history_cursors`, `agent_runs`, `artifacts`, `artifact_validations`, `artifact_acceptances`, `cost_entries`, `command_idempotency`, `domain_events`, `audit_events`, and `outbox_messages`.

### Workflow and queue identities

| Run | Runtime ID | Queue and initial controls | Finite terminal condition |
| --- | --- | --- | --- |
| campaign stage | `experiment:{experiment_id}:OUTREACH_AND_REPLY:v{version}:run:{workflow_run_id}` | `alon-ai-outreach-v1`, global/worker concurrency `1`; admits only owned test aliases in M6 | sample/window closes; all messages terminal and every ambiguity reconciled/operator-visible |
| one send attempt | `send:{send_intent_id}:attempt:{attempt_number}:v{workflow_version}` | `alon-ai-send-v1`, global/worker concurrency `1`, limiter `1` start per `30` seconds for initial M6; policy caps may be stricter | `SENT`, conclusive `FAILED`, `SUPPRESSED`, or `CANCELLED`; ambiguity delegates to reconciliation |
| reconciliation | `reconcile:{send_attempt_id}:v{strategy_version}` | `alon-ai-reconciliation-v1`, global/worker concurrency `2`; durable bounded timers, no send permission | one match -> sent; conclusive absence -> retry classification; conflict/window exhaustion -> operator-visible permanent failure |
| history page | `gmail-sync:{mailbox_id}:from:{history_id}:run:{workflow_run_id}` | `alon-ai-gmail-sync-v1`, global/worker concurrency `1` per mailbox; schedule triggers finite page-drain runs | cursor page committed or typed cursor-reset/recovery state |

Queue settings are pinned deployment evidence and verified from DBOS before pilot. Application policy, not queue configuration, is final authority. A runtime wake/dequeue can only request an application command.

### Pre-send state/data transaction

1. Draft agent writes only `OutreachDraft` `PRODUCED`; validators/approval service move artifact and `outreach_messages` through `DRAFT -> APPROVAL_PENDING -> APPROVED` using exact ARCH-03 approval/artifact events.
2. `RecordSendIntent` reads `experiments`, active `campaigns`/member, `leads(QUALIFIED)`, `approvals`, `suppression_entries`, `system_controls`, budget, policy facts, and immutable message/artifact versions.
3. One transaction inserts `policy_decisions`, reserves budget, inserts unique `send_intents.idempotency_key`/`rfc_message_id`, transitions message `APPROVED -> SEND_INTENT_RECORDED -> QUEUED`, appends `send.intent_recorded.v1` and `send.queued.v1`, audit/idempotency/outbox, and queues the runtime start after commit.
4. In M6 that transaction requires `TEST_INBOX_SENDING=true`, `PRODUCT_OUTREACH=false`, and the recipient hash in the owned-alias manifest. After M6, real-recipient mode instead requires `PRODUCT_OUTREACH=true` plus separate authority; the test control cannot authorize it.

### Gateway, ambiguity, retry, and reply map

| Step | Reads | Writes/constraint | Exact event/transition |
| --- | --- | --- | --- |
| dequeue/recheck | message/intent, experiment/campaign/lead, approval, suppression, both controls, policy/budget/rate, no unresolved attempt | insert unique attempt number; increment intent count; message `QUEUED -> SENDING`; commit before network | `policy.evaluated.v1`, `send.attempt_started.v1` |
| Gmail result | attempt + stable RFC ID | insert unique `provider_results`; message/attempt `SENT`; reconcile budget/cost | provider IDs retained; terminal sent uses authoritative send evidence (direct success retains `send.attempt_started.v1`; reconciled success emits the catalog event below) |
| unknown outcome | attempt | attempt/message `AMBIGUOUS`; provider error fingerprint/evidence | `send.outcome_ambiguous.v1`; no requeue |
| reconcile | attempt/result/observations + Sent query | `RECONCILING`, provider observations/results; exact match or typed failure | `send.reconciliation_started.v1`; one match -> `send.reconciled_as_sent.v1`; conclusive failure -> `send.failed.v1` |
| retry | `FAILED_RETRYABLE`, immutable retry policy/deadline, controls/policy/budget, no ambiguity | deterministic `SendRecoveryService` returns message to `QUEUED`; new attempt number later | `send.retry_scheduled.v1`; exhaustion/abort -> `send.retry_exhausted.v1` and `FAILED_PERMANENT` |
| history/reply | cursor + Gmail page/provider identities | observations, replies, events, and cursor in one transaction | `reply.received.v1`, `gmail.history_cursor_advanced.v1`; classification artifact acceptance later emits `reply.classified.v1` |

The workflow/agent never calls Gmail or updates these rows directly. `SendGateway` is the only Gmail send caller; reconciliation/history services use read-only provider primitives. A direct Gmail success must still retain provider IDs/result evidence and message `SENT`; no new event alias is invented beyond ARCH-03.

## Ordered implementation tasks

- [ ] **Provision isolated M6 authority —** Input: M1 pass, owned aliases, OAuth/security/policy controls. Operation: seed no recipient, register allowlist evidence, enable only `TEST_INBOX_SENDING` by authenticated command, and verify product outreach false. Output: isolated pilot authority. Test evidence: address-hash/control call-path tests. Failure behavior: no send.
- [ ] **Implement draft/approval/intent path —** Input: qualified lead mapped to owned alias, exact artifact/campaign/policy versions. Operation: validate/approve, record policy/budget/intent, transition/queue atomically. Output: one immutable queued intent. Test evidence: replay, changed-draft, revoked approval, suppression, and concurrent intent tests. Failure behavior: deny/audit/release reservation.
- [ ] **Implement gateway and ambiguous reconciliation —** Input: queued intent and last-mile facts. Operation: commit attempt, call Gmail once, capture result or ambiguity, reconcile Sent before any retry. Output: terminal/retryable/operator-visible result. Test evidence: M1 kill matrix expanded across product tables. Failure behavior: global/test disable on impossible/duplicate/conflicting evidence.
- [ ] **Implement reply sync/classification —** Input: mailbox cursor/page. Operation: atomically dedupe observations/replies/events/cursor, then classify through typed agent/validator. Output: reply timeline and accepted classification. Test evidence: page crash, duplicate history, stale cursor, malformed message, agent abstention. Failure behavior: do not advance cursor past lost observation; classification remains absent/rejected.
- [ ] **Prove controls, rate, suppression, and campaign completion —** Input: pilot scenario manifest. Operation: run restart/concurrency/pause/cancel/suppression/rate/window matrix and close only when all attempts reconcile. Output: M6 bundle and `OUTREACH_ACTIVE -> EVALUATING`. Test evidence: zero uncontrolled duplicates/post-control calls and complete event chain. Failure behavior: M6 fails; both send controls disabled.
- [ ] **Keep product outreach disabled until gate record —** Input: complete M1+M6 evidence. Operation: verify bundle independently; only then make later enable command eligible. Output: eligibility, not automatic enable/send. Test evidence: missing/stale/failed evidence denial. Failure behavior: `PRODUCT_OUTREACH=false`.

## Test strategy

- **Contract `test_only_sendgateway_calls_gmail_send_and_agents_never_receive_port`:** one authority edge.
- **Atomicity `test_policy_budget_intent_message_event_queue_commit_together`:** failure injection.
- **Recovery `test_kill_after_provider_acceptance_reconciles_stable_rfc_without_resend`:** K4/K5 equivalent.
- **Retry `test_ambiguous_never_requeues_and_exhaustion_is_terminal`:** ARCH-03 exact guards/events.
- **History `test_observation_reply_event_cursor_are_atomic_and_deduplicated`:** crash/replay.
- **Control `test_pause_cancel_suppression_and_global_stop_prevent_new_provider_calls`:** bounded response.
- **Security `test_m6_allows_only_owned_alias_hashes_and_redacts_content`:** no prospect leakage.

## Security, privacy, compliance, idempotency, observability, and cost

OAuth tokens remain inside the Gmail adapter and use least scopes/rotation/revocation. Addresses/content are encrypted; logs/events use safe IDs/hashes. Jurisdiction/compliance facts are deterministic configuration plus operator/legal review, not an agent claim. Stable command/intent/RFC/attempt/provider identities connect all evidence. Queue/policy/rate/budget/control/provider/reconciliation/reply metrics are correlated and cost reservations reconcile to provider results.

## Failure, rollback, and operator recovery

Duplicate, unknown state, provider leakage, suppression/control/rate breach, ambiguous-window conflict, cursor gap, or credential concern disables both send controls and opens an incident. Stop new dequeues, let no new provider call begin, reconcile every in-flight/ambiguous attempt, revoke credentials when indicated, preserve restricted evidence, and recover only through audited commands. Rollback drains/version-routes in-flight workflows; product schema/history remains authoritative.

## Acceptance and retained evidence

- [ ] M6 used only operator-owned inbox aliases while product outreach stayed false.
- [ ] Every workflow read/write/constraint maps to DB-01/03/04/05 and every named event/state matches ARCH-03.
- [ ] Zero uncontrolled duplicate sends, blind retries, post-control calls, skipped replies, and unresolved hidden ambiguities.
- [ ] Stable identity, attempt/result ledger, Sent reconciliation, bounded retry, and visible conflict cover every Gmail outcome.
- [ ] Passing M6 grants eligibility only; real outreach still needs explicit bounded authority.

Retain OAuth scope/alias/control manifests, queue config, policy/approval/suppression/budget records, call-path proof, crash/control/rate traces, provider/Sent/history evidence, reply fixtures, cost reconciliation, signed M6 gate, and cleanup/credential actions.

## Dependencies and next deliverable

WF-05 depends on M1-M5 and all M6 provider/policy/security controls. Its pilot uses [WF-06](06-pause-cancel-resume-and-recovery.md). A passing M6 unlocks M7 control UI and later bounded product-outreach eligibility; a failure returns to M1/M6 safety work with sending disabled.
