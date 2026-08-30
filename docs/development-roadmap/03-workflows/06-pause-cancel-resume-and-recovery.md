# Pause, Cancel, Resume, Retry, and Operator Recovery

**Document ID:** WF-06
**Status:** Planned cross-workflow control/recovery contract
**Milestone:** M6, with M4-M5 no-send controls implemented earlier
**Owner:** Solo operator
**Prerequisites:** [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [WF-02](02-experiment-lifecycle.md), [WF-05](05-outreach-and-reply-workflow.md), DB-01/03/05, authenticated command handling, and M1-proven runtime control/recovery behavior
**Outputs:** Idempotent control commands, cooperative/runtime pause/cancel mapping, guarded resume, closed failure exits, ambiguous-send quarantine, and recovery/repair evidence
**Unlocks:** Safe M6 pilot and M7 operator control center
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

One operator can stop new expensive/reputation-bearing work quickly, see what is still in flight, and recover without direct SQL. Pause is reversible and retains `paused_from_state`; cancel is terminal for the run/experiment version where ARCH-03 says so; retry of a failed experiment stage creates a new run. Neither pause nor cancel pretends an ambiguous Gmail call did not happen.

## Current repository state

There is no authentication, product control table, workflow run, DBOS workflow/control adapter, pause/resume/cancel API, kill switch, incident, reconciliation, recovery UI, or repair command. Process termination is the only current worker stop behavior and carries no product state.

## Scope and non-goals

In scope: authenticated idempotent commands, experiment/run/campaign/send admission controls, runtime cooperative stop, bounded acknowledgement, restart recovery, guarded resume, cancellation drain, failed-stage retry, permanent ambiguous quarantine with positive-evidence reconciliation, send retry only after explicit provider rejection or signed local pre-write proof, incident/repair trail, and unknown-state fail-closed behavior. Non-goals: arbitrary workflow rewind, resuming terminal runs, deleting history, cancelling a provider action already accepted, direct DB edits, compensating email deletion, or agent-authored recovery.

## Exact planned implementation surfaces

Create `application/controls.py`, `application/recovery.py`, workflow runtime control adapter methods, API commands later in M7, and recovery tests. Control command keys are `control:{aggregate_type}:{aggregate_id}:{command}:{operator_request_id}`. Commands first persist intent/state/audit/outbox under expected versions, then call the runtime adapter. The runtime may implement pause cooperatively at safe step boundaries using the exact M1-proven DBOS mechanism; no claim of a native primitive is made without WF-01 evidence.

Exact product tables touched through application commands are `experiments`, `workflow_runs`, `campaigns`, `outreach_messages`, `send_intents`, `send_rate_reservations`, `send_attempts`, `provider_results`, `provider_observations`, `system_controls`, `suppression_entries`, `policy_decisions`, `incidents`, `repair_actions`, `command_idempotency`, `domain_events`, `audit_events`, and `outbox_messages`.

### Canonical experiment/run control map

| Command | Preconditions/reads | Atomic product writes | Runtime action and exact canonical event |
| --- | --- | --- | --- |
| `PauseExperiment` | experiment in `RESEARCHING/QUALIFYING_LEADS/OUTREACH_ACTIVE/EVALUATING`; active run; no command conflict | experiment -> `PAUSED` with exact `paused_from_state`; run -> `PAUSE_REQUESTED`; audit/idempotency/outbox | stop new child/provider steps/dequeues; on safe acknowledgement run -> `PAUSED`; `experiment.paused.v1`, `experiment.state_changed.v1`, then `workflow.run_paused.v1` |
| `ResumeExperiment` | experiment `PAUSED`, run `PAUSED`, saved target, prerequisites/versions still valid | experiment -> saved target; run -> `RUNNING`; invalidate stale approvals as needed | send durable resume/control; all guards rechecked; `experiment.resumed.v1`, `experiment.state_changed.v1`; outreach resume additionally rechecks M1/M6, controls, campaign, suppression, policy, budget, rate |
| `CancelExperiment` | any ARCH-03 cancellable state; no unknown in-flight provider outcome | experiment -> `CANCELLED`; run -> `CANCEL_REQUESTED`; cancel unsent queued intents where legal | runtime cancel/drain; on acknowledgement run -> `CANCELLED`; `experiment.cancelled.v1`, `experiment.state_changed.v1`, `workflow.run_cancelled.v1` |
| `CancelRun` | nonterminal run, aggregate command permits | run -> `CANCEL_REQUESTED`; no aggregate terminal inference | runtime cancel; run -> `CANCELLED` and `workflow.run_cancelled.v1`; separate application command decides aggregate |
| `RetryExperimentStage` | experiment `FAILED` and one exact ARCH-03 exit guard; prior run terminal; retry budget remains | increment retry count; create new run; transition to `RESEARCHING`, `QUALIFYING_LEADS`, or `READY_FOR_OUTREACH` exactly | start new runtime ID; `experiment.retry_started.v1`, `experiment.state_changed.v1`, `workflow.run_started.v1` |
| `ReviseExperiment` | `FAILED`, no in-flight run, side effects terminal/reconciled, new brief | append brief, invalidate approvals, experiment -> `DRAFT` | no old-run resume; `experiment.revision_started.v1`, `experiment.state_changed.v1` |

The `FAILED -> READY_FOR_OUTREACH` path is deliberate: it never jumps to `OUTREACH_ACTIVE`. `DECIDED`/`CANCELLED` experiments and `CANCELLED/SUCCEEDED/FAILED` runs are terminal.

### Campaign/message/provider recovery rules

- Campaign pause emits `campaign.paused.v1` plus `campaign.state_changed.v1` on the exact `(campaign_id,campaign_version)`; resume emits `campaign.resumed.v1` plus state-changed after a new deterministic policy/control check. Cancel emits `campaign.cancelled.v1` plus state-changed and may make unsent `QUEUED` messages `CANCELLED`; it cannot overwrite `SENDING`, `AMBIGUOUS`, or `RECONCILING`. Completion/failure use `campaign.completed.v1`/`campaign.failed.v1` plus state-changed.
- A pre-provider queued message may become `CANCELLED` or `SUPPRESSED` under ARCH-03. Last-mile suppression atomically records fresh denied SEND policy, `QUEUED -> SUPPRESSED`, `send.suppressed.v1`, one-way `open_for_attempt=false` intent cancellation, and reservation release with zero rate reservation/attempt/provider call. Once an attempt/consumed lease exists or the provider call may have started, intent cancellation is relationally forbidden; the attempt remains `SENDING/AMBIGUOUS/RECONCILING` until evidence resolves it.
- Gmail OAuth recovery follows PROVIDER-01, not workflow retry: exact `IN_PROGRESS` plus expired/free flow handler lease may resume STAGED/ACTIVE without code exchange; ACTIVE proof must precede mailbox+SUCCEEDED commit; post-DB replay returns stored redirect. `EXCHANGE_STARTED` with no credential after bounded strong reads requires fresh authorization. GC may delete only after 24 hours, no handler/bind lease, and repeatable-read proof of no mailbox or matching IN_PROGRESS command; one CAS wins cleanup versus resume. A stuck resumable IN_PROGRESS saga requires typed `RepairIncident(ABORT_OAUTH_SAGA)` before any later GC; elapsed time never deletes it.
- `FAILED_RETRYABLE -> QUEUED` is owned only by `SendRecoveryService`, preserves the immutable campaign-member/approval-basis/mailbox/RFC identity, requires no active consumed rate lease and every ARCH-03 retry guard, and creates no policy decision until a later fresh last-mile SEND; runtime timers merely wake evaluation. Mailbox-bound `send.retry_scheduled.v1` records admission; exhaustion/operator abort emits mailbox-bound `send.retry_exhausted.v1` and reaches `FAILED_PERMANENT`.
- Global `system_controls` changes are versioned/authenticated. `system.outreach_disabled.v1` is emitted for product-wide disable; re-enable uses `system.outreach_enabled.v1` only after incident/gate evidence. M6 test-inbox control cannot enable product outreach.
- Unknown runtime/product disagreement opens `incidents`, leaves send controls false, and requires `repair_actions` with before/after hashes. Direct SQL is forbidden.

### Read/write and constraint map

| Recovery surface | Reads | Writes/constraints |
| --- | --- | --- |
| experiment/run control | `experiments`, active `workflow_runs`, command result, artifact/brief/gate versions | verify DB-01 RFC 8785 input digest before resume and result digest before consumption; optimistic versions, active-run unique, canonical safety bundle |
| outreach stop | `system_controls`, campaign/messages/intents/rate reservations/attempts, suppression/policy/budget, runtime status | control version; queued cancellation/suppression with one-way intent marker and no attempt; release only provably uncalled leases; no mutation of ambiguous/terminal rows |
| retry | failed experiment/message fields, attempt/deadline, all current controls | new workflow run unique ID or next attempt unique number; retry count/cap checks; retry events |
| reconcile/repair | intent's immutable experiment/campaign/member/lead/message/mailbox/approval/eligibility-basis/RFC tuple plus attempt's fresh SEND decision/consumed rate lease, matching results/observations/cursor/events/audit/runtime/incident | reject any tuple mismatch before querying; search only authorized account; append composite evidence/repair; direct success uses `send.provider_accepted.v1`, prior ambiguity uses `send.reconciled_as_sent.v1` |
| OAuth credential consistency | flow object, exact DB mailbox flow/account/scope/handle/version/key/generation tuple, command state, handler/bind/GC leases | resume STAGED/ACTIVE or replay committed result; mismatch disables mailbox/controls, opens incident, and requires typed repair/fresh authorization; never SQL/secret patch |

## Ordered implementation tasks

- [ ] **Implement idempotent control command service —** Input: authenticated operator, expected versions, reason, command key. Operation: validate matrix, persist request/state/events/audit/outbox/result atomically, then signal runtime. Output: authoritative requested state. Test evidence: command replay, stale version, illegal state matrix. Failure behavior: typed denial/no runtime call.
- [ ] **Implement cooperative acknowledgement —** Input: requested state and runtime handle. Operation: prevent new steps/dequeues, wait boundedly for safe boundary, record canonical run acknowledgement. Output: `PAUSED`/`CANCELLED` or visible pending/incident state. Test evidence: kill/restart at request, signal, step, acknowledgement. Failure behavior: keep control closed and escalate; never report completion early.
- [ ] **Implement guarded resume/retry —** Input: saved state/prior failure plus current evidence. Operation: revalidate every version/gate/control; resume nonterminal paused run or create a new failed-stage run. Output: exact ARCH-03 state/events. Test evidence: changed artifact/policy/suppression/gate and retry-exhaustion cases. Failure behavior: remain paused/failed.
- [ ] **Implement send drain/reconciliation —** Input: all nonterminal messages/attempts/provider evidence. Operation: cancel provably unsent work; quarantine and reconcile possibly sent work; prohibit retry/replacement permanently for every ambiguous/negative/conflicting read result. Only a separate explicit provider rejection or signed local pre-write proof may create retryable state. Output: terminal or permanently quarantined operator-visible ledger. Test evidence: cancel at every WF-05 network boundary plus zero/many/delayed-search non-escape. Failure behavior: both controls off, incident open.
- [ ] **Implement recovery/repair runbook command —** Input: incident, product/runtime/provider comparison, signed evidence. Operation: choose a typed repair transition, record before/after hashes, execute under idempotency, and verify invariants. Output: auditable recovery without SQL. Test evidence: corrupted/unknown-state fixtures and restore drill. Failure behavior: keep system degraded/off and restore to isolated database.

## Test strategy

- **Unit `test_control_matrix_matches_arch03_and_terminal_states_have_no_resume`:** exhaustive states.
- **Atomicity `test_control_state_events_idempotency_outbox_commit_together`:** failure injection.
- **Recovery `test_kill_each_control_boundary_never_starts_post_pause_cancel_provider_call`:** M1/M6 matrix.
- **Ambiguity `test_cancel_does_not_convert_unknown_provider_outcome_to_cancelled`:** reconcile first.
- **Mailbox `test_recovery_proves_authorized_mailbox_and_rejects_cross_account_evidence`:** immutable member/approval basis/intent/attempt account is the only search/result scope.
- **OAuth `test_recovery_resumes_only_flow_indexed_staged_or_active_handle_and_gc_cannot_race_commit`:** no second exchange/no success without ACTIVE proof.
- **Rate `test_recovery_releases_or_expires_lease_only_after_conclusive_provider_evidence`:** wall-clock expiry never grants retry.
- **Suppression `test_recovery_never_creates_attempt_for_cancelled_suppressed_intent`:** composite FK enforcement.
- **Digest `test_resume_and_repair_reject_noncanonical_or_wrong_schema_workflow_snapshot`:** verify before upcast/action.
- **Retry `test_failed_stage_retry_creates_new_run_and_outreach_returns_ready`:** exact five-exit model.
- **Security `test_only_authenticated_operator_can_control_or_repair_and_denials_are_audited`:** authority.
- **E2E `test_operator_can_pause_inspect_resume_cancel_and_recover_without_sql`:** M7-ready journey.

## Security, privacy, compliance, idempotency, observability, and cost

Controls/repairs require strong operator authentication and reason/evidence. Least-data status views hide credentials/content. Command keys make repeated clicks safe. Correlated timelines expose request/acknowledgement latency, queue/dequeue, provider in-flight/ambiguity age, reconciliation, runtime mapping, policy/control versions, incident, and cost. Pause stops new cost but does not erase already incurred provider charges.

## Failure, rollback, and operator recovery

If control acknowledgement exceeds its tested bound, OAuth DB/secret binding disagrees, runtime mapping is unknown, or product/provider histories disagree, keep both send controls disabled, stop workers/dequeues, reconcile provider outcomes, preserve evidence, and open an incident. Roll back workflow code using M1-proven version/drain strategy. Restore into an isolated database when invariants cannot be repaired through typed commands. Never force engine/product state to agree by deletion.

## Acceptance and retained evidence

- [ ] Every control has actor, guard, requested/acknowledged state, exact ARCH-03 events, idempotency, timeout, and failure path.
- [ ] Pause/cancel stops new provider calls within the tested bound but never hides ambiguous calls.
- [ ] Resume rechecks current authority; failed-stage retry creates a new finite run and closed exit.
- [ ] Runtime/product/provider disagreements are visible, incident-linked, and repairable without SQL.
- [ ] M6/M7 operator can diagnose every pending/terminal state from retained evidence.

Retain control matrix, API/runtime contracts, queue/control configurations, command/event fixtures, kill/acknowledgement/restart traces, ambiguity drains, repair/incident records, and operator E2E evidence.

## Dependencies and next deliverable

WF-06 depends on M1-proven runtime controls, ARCH-03, M2 safety tables, and WF-02/05. It is required for the M6 gate and unlocks the M7 experiment control center/error-recovery UI; failure keeps sending disabled.
