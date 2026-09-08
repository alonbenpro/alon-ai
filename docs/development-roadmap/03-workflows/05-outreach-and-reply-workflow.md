# Controlled Outreach, Gmail Reconciliation, and Reply Workflow

**Document ID:** WF-05
**Status:** Planned M6 test-inbox product workflow; product outreach disabled
**Milestone:** M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-05-T01 -> WF-05-T02 -> WF-05-T03 -> WF-05-T04 -> WF-05-T05 -> WF-05-T06`; cross-document task Inputs `WF-05-T01 <- TEST-03-T03,SEC-05-T03,BACKEND-05-T06,PROVIDER-01-T03,SEC-02-T04,LAUNCH-01-T03,WF-00-T04; WF-05-T02 <- BACKEND-05-T03,WF-04-T04,AGENT-07-T03; WF-05-T03 <- SEC-05-T03,BACKEND-04-T04; WF-05-T04 <- PROVIDER-02-T04,AGENT-08-T03,SEC-05-T02; WF-05-T05 <- BACKEND-04-T05,SEC-05-T04,WF-06-T04,LAUNCH-01-T03; WF-05-T06 <- TEST-04-T06`. Descriptive source authorities/resources (not whole-document completion dependencies): passing M1/M5, complete M2 schema, promoted M3 draft/reply agents, [WF-02](02-experiment-lifecycle.md), [DB-03](../02-database/03-leads-campaigns-and-messages.md), Gmail OAuth/adapter/history sync, deterministic policy/suppression/budget/approval services, and isolated operator-owned test inboxes
**Outputs:** Finite campaign/send/reconciliation/sync runs, no-duplicate evidence, reply records/classifications, kill/control/rate evidence, and M6 gate bundle
**Unlocks:** M6 exit and later eligibility to enable bounded product outreach; never automatic real-recipient authority
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

M6 proves the complete product-shaped Gmail loop against operator-owned inboxes: draft/approve, intent, queue, last-mile policy, send, ambiguous reconciliation, history cursor, reply, classification, pause/cancel/restart, suppression, and audit. During the pilot, `TEST_INBOX_SENDING` may be enabled for an exact owned-alias allowlist while `PRODUCT_OUTREACH` remains `false`. Only after the retained M6 gate passes can an authenticated later command consider product outreach, and that command still requires M1, recipient/campaign authority, and every deterministic gate.

The later M9 composition consumes PRODUCT-02's staged rule without changing this M6 proof: final admission binds one of the exact `100/200/300/400` increments, its `100/300/600/1,000` cumulative ceiling, unique experiment-recipient membership, and the prior signed `CONTINUE` for stages above one. Queue prefetch may not cross a barrier. Replies, suppression, ambiguity, disable, budget, or policy stops close all provably unsent stage work and prevent later-stage admission.

## Current repository state

There is no product table/workflow, Gmail OAuth/adapter/history sync, policy/suppression/budget implementation, approval, UI control, or send. The minimal `SendGateway` contract has no durable ledger or provider. No current behavior satisfies M6.

## Scope and non-goals

In scope: owned test aliases, exact-scope draft approval, stable intent/RFC identity, DBOS queues/timers/recovery, sole `SendGateway` call, provider result capture, permanent ambiguous quarantine with positive Sent reconciliation, bounded retry only after explicit provider rejection or signed local pre-write proof, history cursor/replies, typed reply classification, suppression, controls, and gate evidence. Non-goals: real prospects, bulk throughput, agent send authority, blind retry, claiming SMTP delivery/read, automatic response, long-lived open campaign workflow, or using DBOS recovery as provider exactly-once.

## Exact planned implementation surfaces

Create `workflows/outreach.py`, `workflows/send_message.py`, `workflows/gmail_reconciliation.py`, `workflows/gmail_history_sync.py`, `application/sending.py`, and M6 contract/recovery tests.

Exact product tables touched through application commands are `experiments`, `workflow_runs`, `campaigns`, `campaign_members`, `leads`, `approvals`, `suppression_entries`, `system_controls`, `budget_reservations`, `policy_decisions`, `outreach_messages`, `send_intents`, `send_rate_reservations`, `send_attempts`, `provider_results`, `provider_observations`, `replies`, `gmail_mailboxes`, `gmail_history_cursors`, `agent_runs`, `artifacts`, `artifact_validations`, `artifact_acceptances`, `cost_entries`, `command_idempotency`, `domain_events`, `audit_events`, and `outbox_messages`.

### Workflow and queue identities

| Run | Runtime ID | Queue and initial controls | Finite terminal condition |
| --- | --- | --- | --- |
| campaign stage | `experiment:{experiment_id}:OUTREACH_AND_REPLY:v{version}:run:{workflow_run_id}` | `alon-ai-outreach-v1`, global/worker concurrency `1`; admits only owned test aliases in M6 | sample/window closes; all messages terminal and every ambiguity reconciled/operator-visible |
| one send attempt | `send:{send_intent_id}:attempt:{attempt_number}:v{workflow_version}` | `alon-ai-send-v1`, global/worker concurrency `1`, limiter `1` start per `30` seconds for initial M6; policy caps may be stricter | `SENT`, conclusive `FAILED`, `SUPPRESSED`, or `CANCELLED`; ambiguity delegates to reconciliation |
| reconciliation | `reconcile:{send_attempt_id}:v{strategy_version}` | `alon-ai-reconciliation-v1`, global/worker concurrency `2`; durable bounded timers, no send permission | one match -> sent; zero/multiple/conflicting evidence -> operator-visible permanent quarantine and incident, never retry |
| history page | `gmail-sync:{mailbox_id}:from:{history_id}:run:{workflow_run_id}` | `alon-ai-gmail-sync-v1`, global/worker concurrency `1` per mailbox; schedule triggers finite page-drain runs | cursor page committed or typed cursor-reset/recovery state |

Queue settings are pinned deployment evidence and verified from DBOS before pilot. Application policy, not queue configuration, is final authority. A runtime wake/dequeue can only request an application command.
Every campaign-stage workflow input/result uses DB-01's text-versioned UTF-8 RFC 8785 envelope digest. Resume verifies stored bytes before any authority read; a different version or payload creates a new finite run.

### Pre-send state/data transactions

1. Draft agent writes only `OutreachDraft` `PRODUCED`; deterministic validation/acceptance creates the exact immutable artifact/message basis.
2. `RequestApproval` loads campaign version+experiment, member `(campaign_member_id,campaign_id,campaign_version,lead_id)`, message/member/mailbox, general artifact refs and exact recipient identity/jurisdiction/consent-or-counsel-exception/legal-review/legal-policy/disclosure-sender/Google-policy artifact tuples; computes `PolicyScopeV1`/`ApprovalBasisScopeV1`; records `APPROVAL_ELIGIBILITY` without ApprovalRule; and only when allowed atomically inserts a basis-bound `PENDING` approval and `approval.requested.v1`. Eligibility can authorize no intent, queue, attempt, rate reservation, or send.
3. After step-up, the operator alone views the exact recipient address, subject, body, rendered RFC bytes and immutable basis in BACKEND-02's uncached sensitive preview; `ApproveApproval` must carry its fresh receipt and re-materialize the same hash. Denial needs no preview. A changed immutable basis expires/revokes it; mutable suppression/control/budget/rate/jurisdiction facts are not eligibility facts and do not need the same hash.
4. `RecordSendIntent` requires exact manually previewed `APPROVED`, eligibility decision, `campaign_member_id`, basis `scope_hash`, message version/content hash, and preview materialization hash; re-renders the tuple, reserves budget, consumes approval under unique `send_intents.approval_id`, inserts the preview-bound eligibility intent with stable mailbox idempotency/RFC identity, transitions `APPROVED -> SEND_INTENT_RECORDED -> QUEUED`, and emits intent/queue events. It records no final SEND decision. In M6 it also requires test mode/owned alias; later product mode requires separate authority.
5. Only last-mile SendGateway creates a fresh `SEND` decision from the approved row plus locked current compliance evidence/status/timestamps, reply/unsubscribe/bounce/complaint observations and every other mutable fact. The final decision shares the immutable basis `scope_hash` but has its own `facts_hash`; each missing/stale/stop fact has a dedicated denial and cannot reuse generic jurisdiction/authority.

### Gateway, ambiguity, retry, and reply map

| Step | Reads | Writes/constraint | Exact event/transition |
| --- | --- | --- | --- |
| dequeue/final policy | eligibility-bound intent + exact campaign member/approved basis + current mutable facts, no unresolved attempt | create a new SEND decision with the same scope hash and independent facts hash | full scope/member/approval/facts in `policy.evaluated.v1` |
| last-mile suppression | denied SEND with active global/business/recipient suppression | atomically message `QUEUED -> SUPPRESSED`, one-way intent cancellation, release unsent reservations; no rate row/attempt/call | `send.suppressed.v1` plus audit/idempotent result/outbox |
| allowed rate/attempt | allowed fresh SEND, locked mailbox/window, DBOS admission | atomically reserve+consume unique `send_rate_reservations` slot/lease and insert attempt carrying final SEND/member/rate authority; commit before network | `send.attempt_started.v1` |
| Gmail result | attempt + authorized mailbox + stable RFC ID + consumed rate lease | insert mailbox-bound unique `provider_results`; message/attempt `SENT`; reconcile budget/cost and release rate lease | direct accepted result captures provider identity and emits `send.provider_accepted.v1` |
| unknown outcome | attempt + consumed rate lease | attempt/message `AMBIGUOUS`; retain active lease and provider error fingerprint/evidence | `send.outcome_ambiguous.v1`; no requeue |
| reconcile | unresolved attempt/result/observations plus immutable `send_intents.mailbox_id` and RFC ID | query only that authorized Gmail account; store every mailbox-bound candidate/result; one exact match resolves sent; zero/multiple/conflicting evidence retains `AMBIGUOUS`/`RECONCILING`, the consumed lease, and permanent quarantine | mailbox payload in `send.reconciliation_started.v1`; one post-ambiguity match -> `send.reconciled_as_sent.v1`; 300 seconds only opens/escalates an incident |
| retry | `FAILED_RETRYABLE` created only by explicit provider rejection or signed local pre-write proof, immutable campaign-member/basis/mailbox/RFC/retry policy/deadline, no ambiguity/active lease | deterministic recovery returns message to `QUEUED`; a later attempt gets a fresh SEND decision and unique rate slot | mailbox/RFC payload in `send.retry_scheduled.v1`; exhaustion/abort -> `send.retry_exhausted.v1` and `FAILED_PERMANENT` |
| history/recipient signal | mailbox cursor plus Gmail page/message/thread/history/campaign-member identities | ordinary observation commits normally; reply/unsubscribe/hard-bounce/complaint/soft-limit invokes `RecipientSignalSuppressionService` and atomically inserts observation/reply, canonical suppression plus durable opaque target ref, lead/pre-call-message/intent closure, replay result, events/audit/outbox and cursor; failure leaves cursor and product control closed; no workflow input/output carries recipient lookup material | `suppression.created.v1` with stored target ref, applicable `lead.suppressed.v1`/`send.suppressed.v1`, `reply.received.v1`, `gmail.history_cursor_advanced.v1`; classification later cannot delay stop |

The workflow/agent never calls Gmail or updates these rows directly. `SendGateway` is the only Gmail send caller; reconciliation/history services use read-only provider primitives scoped to the immutable authorized mailbox. Direct success uses `send.provider_accepted.v1`; `send.reconciled_as_sent.v1` is reserved for resolving a prior `AMBIGUOUS` attempt.

## Ordered implementation tasks

<!-- roadmap-task id=WF-05-T01 milestone=M6 depends_on=TEST-03-T03,SEC-05-T03,BACKEND-05-T06,PROVIDER-01-T03,SEC-02-T04,LAUNCH-01-T03,WF-00-T04 mode=serial locks=gmail-side-effects,workflow-runtime,live-environment -->
- [ ] **Provision isolated M6 authority —** Input: M1 pass, owned aliases, OAuth/security/policy controls; real authenticated operator boundary and signed bounded M6 entry/preflight; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient. Operation: seed no recipient, register allowlist evidence, enable only `TEST_INBOX_SENDING` by authenticated command, and verify product outreach false. Output: isolated pilot authority. Test evidence: address-hash/control call-path tests. Failure behavior: no send.
<!-- roadmap-task id=WF-05-T02 milestone=M6 depends_on=WF-05-T01,BACKEND-05-T03,WF-04-T04,AGENT-07-T03 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Implement eligibility/approval/intent path —** Input: qualified lead, exact campaign member/artifact basis; qualified lead assessment and immutable drafting review artifact. Operation: compose qualified lead/draft/immutable campaign basis through the existing BACKEND-05 approval and intent owners; reserve/queue only through those services and never create a second approval/intent/budget writer. Output: one immutable queued intent. Test evidence: circularity negative, member splice, changed basis, mutable-fact, revoked/expired approval, and replay tests. Failure behavior: deny/audit/release reservation.
<!-- roadmap-task id=WF-05-T03 milestone=M6 depends_on=WF-05-T02,SEC-05-T03,BACKEND-04-T04 mode=serial locks=gmail-side-effects,workflow-runtime,live-environment -->
- [ ] **Implement gateway, rate lease, suppression, and reconciliation —** Input: queued intent/approved basis/current last-mile facts and the implemented BACKEND-04 SendGateway execution/result/reconciliation interface. Operation: create fresh SEND; commit suppression/no-call or one consumed slot+attempt; call Gmail once; capture/release or permanently quarantine ambiguity; retry only explicit rejection/local pre-write proof. Output: terminal/retryable/operator-visible result. Test evidence: M1 kill matrix expanded across product tables. Failure behavior: global/test disable on impossible/duplicate/conflicting evidence.
<!-- roadmap-task id=WF-05-T04 milestone=M6 depends_on=WF-05-T03,PROVIDER-02-T04,AGENT-08-T03,SEC-05-T02 mode=serial locks=gmail-side-effects,workflow-runtime -->
- [ ] **Implement recipient-signal sync/classification —** Input: mailbox cursor/page; typed reply classifier contract and implemented RecipientSignalSuppressionService. Operation: atomically dedupe observations, replies, observed suppression, provably-uncalled intent closure, events and cursor, then classify through typed agent/validator. Output: implemented versioned recipient-signal sync/classification interface plus blocked recipient path and later classification. Test evidence: every signal, page/write crash, concurrent gateway, duplicate history, stale cursor, malformed message and agent abstention. Failure behavior: do not advance cursor; force product control false until repaired.
<!-- roadmap-task id=WF-05-T05 milestone=M6 depends_on=WF-05-T04,BACKEND-04-T05,SEC-05-T04,WF-06-T04,LAUNCH-01-T03 mode=serial locks=gmail-side-effects,milestone-gate,live-environment -->
- [ ] **Prove controls, rate, suppression, and campaign completion —** Input: the pilot scenario manifest, BACKEND-04 gateway authority/evidence, SEC-05 bounded-stop implementation, and WF-06 terminal control ledger; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: run restart/concurrency/pause/cancel/suppression/rate/window matrix and close only when all attempts reconcile; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: M6 bundle and `OUTREACH_ACTIVE -> EVALUATING` plus complete versioned finite Gmail workflow execution/control contract. Test evidence: zero uncontrolled duplicates/post-control calls and complete event chain. Failure behavior: M6 fails; both send controls disabled.
<!-- roadmap-task id=WF-05-T06 milestone=M6 depends_on=WF-05-T05,TEST-04-T06 mode=serial locks=milestone-gate -->
- [ ] **Keep product outreach disabled until gate record —** Input: complete M1+M6 evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: verify bundle independently; only then make later enable command eligible; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: eligibility, not automatic enable/send. Test evidence: missing/stale/failed evidence denial. Failure behavior: `PRODUCT_OUTREACH=false`.

## Test strategy

- **Contract `test_only_sendgateway_calls_gmail_send_and_agents_never_receive_port`:** one authority edge.
- **Atomicity `test_eligibility_approval_budget_intent_message_event_queue_transactions_are_distinct_and_complete`:** failure injection.
- **Policy `test_final_send_has_same_basis_hash_independent_facts_and_current_mutable_denials`:** no circular equality.
- **Relational authority `test_cross_experiment_campaign_member_approval_eligibility_final_send_rate_attempt_fails_fk`:** every one-column splice is rejected by PostgreSQL.
- **Rate `test_concurrent_mailbox_attempts_have_one_consumed_window_slot`:** DBOS outer limiter plus PostgreSQL winner.
- **Suppression `test_last_mile_suppression_has_terminal_event_cancelled_intent_zero_attempt_call`:** exact counts.
- **Recovery `test_kill_after_provider_acceptance_reconciles_stable_rfc_without_resend`:** K4/K5 equivalent.
- **Mailbox authority `test_recovery_searches_only_approved_immutable_mailbox`:** altered account, cross-mailbox candidate, and mailbox/scope-hash mismatch all fail closed and preserve the authorized account ID.
- **Retry `test_ambiguous_never_requeues_and_exhaustion_is_terminal`:** ARCH-03 exact guards/events.
- **History `test_observation_reply_suppression_intent_event_cursor_are_atomic_and_deduplicated`:** crash/replay/concurrent gateway; failure forces product off and no next SEND.
- **Observation identity `test_reply_and_cursor_reject_observation_from_other_mailbox_or_provider_identity`:** no bare observation-ID authority.
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
- [ ] Stable identity, attempt/result ledger, positive-evidence Sent reconciliation, permanent ambiguity quarantine, explicit-rejection/local-pre-write-only bounded retry, and visible conflict cover every Gmail outcome.
- [ ] Passing M6 grants eligibility only; real outreach still needs explicit bounded authority.

Retain OAuth scope/alias/control manifests, queue config, policy/approval/suppression/budget records, call-path proof, crash/control/rate traces, provider/Sent/history evidence, reply fixtures, cost reconciliation, signed M6 gate, and cleanup/credential actions.

## Dependencies and next deliverable

WF-05 depends on M1-M5 and all M6 provider/policy/security controls. Its pilot uses [WF-06](06-pause-cancel-resume-and-recovery.md). A passing M6 unlocks M7 control UI and later bounded product-outreach eligibility; a failure returns to M1/M6 safety work with sending disabled.
