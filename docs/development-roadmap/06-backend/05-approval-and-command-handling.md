# Approval and Idempotent Command Handling

**Document ID:** BACKEND-05
**Status:** Planned M2/M6 command layer; no product commands, approvals, authentication, or handlers exist today
**Milestone:** M2 command substrate, M4-M5 workflow commands, M6 approvals/controls/recovery
**Owner:** Solo operator
**Prerequisites:** [BACKEND-01](01-domain-services.md), [BACKEND-02](02-api-contracts.md), [BACKEND-03](03-policy-engine.md), DB-03/05, and ARCH-03/WF-06 control states
**Outputs:** Exact command registry, replay/concurrency semantics, immutable approval authority, runtime/provider handoff, controls, and operator recovery commands
**Unlocks:** M6 safe pilot and M7 approval/control UI
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Every operator/workflow/system mutation enters through one registered strict command handler. The handler authenticates authority supplied by the API/workflow boundary, claims an exact command key/hash, executes one sole-writer service transaction, and returns a stored result. Approvals authorize only one immutable message/campaign/mailbox/policy scope until expiry/revocation/consumption; they never override suppression or current policy.

## Current repository state

No operator authentication, product command envelope, handler registry, `command_idempotency`, approval table/service, control command, runtime signal, recovery command, or product API exists. The foundation `SendPolicy` decision is ephemeral and the gateway has no approval concept. All behavior below is planned.

## Scope and non-goals

In scope: strict command/result schemas, handler mapping, actor/expected version, idempotency, atomic events/audit/outbox, approval request/decision/revoke/expire/consume, runtime signal after commit, controls, retries/repairs, and denial evidence. Non-goals: generic arbitrary command names, unauthenticated workflow mutation, approval of mutable text, blanket campaign approval, agent approval, direct provider calls, SQL repair, replaying failed external effects, or approval as legal-compliance proof.

## Exact planned implementation surfaces

Create `application/command_bus.py`, `application/idempotency.py`, `application/approvals.py`, `application/controls.py`, `application/recovery.py`, strict command modules under `application/contracts/`, and API handlers named in BACKEND-02. `IdempotentCommandExecutor` exclusively writes `command_idempotency`; handlers never share an idempotency scope accidentally.

### Shared command and replay contract

`CommandEnvelopeV1` contains literal text request schema version, command type/scope, idempotency key, actor type/ID, expected aggregate type/ID/version where applicable, correlation/causation UUIDv4, issued UTC, and strict payload. Request hash is DB-01 RFC 8785/SHA-256 over the exact schema/payload. `CommandResultV1` uses the route/command's exact result schema/payload/hash and maps to BACKEND-02 `CommandReceiptV1` or resource.

The executor transaction is exact: insert/lock `(command_scope,idempotency_key)` as `IN_PROGRESS`; compare request schema/hash on replay; load/lock expected versions/authority; call one handler/service; write aggregate plus exact domain/audit/outbox bundle; store `SUCCEEDED` result triplet or typed `FAILED` error with SQL-null result triplet; commit. Same hash replays; a live `IN_PROGRESS` returns 409/retry-safe status and never starts another handler; stale orphan inspection compares aggregate/events before an authenticated recovery claim. Different hash is `IDEMPOTENCY_HASH_CONFLICT`.

Provider calls never occur in the command transaction. A committed command may enqueue an outbox/internal durable start signal. Direct runtime control signaling occurs only after the requested product state commits; signal failure leaves the request visible (`PAUSE_REQUESTED`/`CANCEL_REQUESTED`), records safe failure/incident, and retries the signal idempotently—it does not roll back product intent or claim acknowledgement.

### Exact command registry

Command type names are canonical API/application vocabulary. Each maps to one owner and no alias.

| Command type | Scope and owner | Core result / exact canonical events |
| --- | --- | --- |
| `CreateExperiment` | `operator:{operator_id}:experiments`; `ExperimentCommandService` + brief owner | experiment/brief v1; `experiment.created.v1` |
| `ApproveExperimentScope` | `experiment:{id}`; `ExperimentCommandService` | state/version; `experiment.scope_approved.v1`, `experiment.state_changed.v1` |
| `StartResearch`, `StartLeadQualification`, `StartOutreachAndReply`, `StartExperimentEvaluation` | `experiment:{id}:stage:{stage}`; stage command service | new workflow run; `workflow.run_started.v1`, state-changed |
| `CompleteWorkflowRun`, `FailWorkflowRun` | `workflow-run:{id}`; `WorkflowRunProjectionService` plus experiment owner transaction | exact result/failure events from WF-02 |
| `PauseExperiment`, `ResumeExperiment`, `CancelExperiment`, `CancelRun`, `RetryExperimentStage`, `ReviseExperiment` | exact aggregate scope; `ControlCommandService`/`ExperimentCommandService` | WF-06 exact requested/acknowledged experiment/run events; retry creates new run |
| `RecordExperimentDecision` | `experiment:{id}:decision`; `ExperimentCommandService` | immutable decision; `experiment.decision_recorded.v1`, state-changed |
| `CreateCampaignVersion`, `ActivateCampaign`, `PauseCampaign`, `ResumeCampaign`, `CancelCampaign` | `campaign:{id}:version:{version}`; `CampaignCommandService` | exact complete campaign event family plus state-changed |
| `RequestApproval`, `ApproveApproval`, `DenyApproval`, `RevokeApproval`, `ExpireApproval`, `ConsumeApproval` | `approval:{approval_id}` or new exact scope; `ApprovalCommandService` | `approval.requested.v1`, `approval.decided.v1`, or `approval.revoked.v1`; consumption has safe audit and message/intent bundle event rather than invented domain alias |
| `RecordSendIntent` | `message:{id}:send-intent`; BACKEND-04 prerecord path | intent/queue result; `send.intent_recorded.v1`, `send.queued.v1` |
| `ExecuteSendAttempt` | `send-intent:{id}:attempt:{n}`; `SendGateway` | BACKEND-04 result events |
| `ReconcileSendAttempt`, `RetrySend`, `AbortSendRetry` | `send-attempt:{id}:recovery` or intent retry scope; `SendRecoveryService` | reconciliation/retry/exhaustion exact events |
| `EnableSystemControl`, `DisableSystemControl` | `control:{control_name}`; `ControlCommandService` | `system.outreach_enabled.v1`/`system.outreach_disabled.v1` only for `PRODUCT_OUTREACH`; test control uses safe audit/control version without inventing product event |
| `SyncGmailMailbox`, `RevokeGmailAuthorization` | `gmail-mailbox:{id}`; Gmail mailbox/history owners | finite sync/revoke result; cursor event only when cursor advances |
| `AcceptArtifact`, `RejectArtifact`, `SupersedeArtifact` | `artifact:{id}`; validation/acceptance owners | exact artifact events, never agent-authored |
| `SuppressRecipient`, `SuppressBusiness`, `EnableGlobalSuppression`, `DeactivateSuppression` | target scope; `SuppressionCommandService` | `lead.suppressed.v1` where a lead transitions plus safe audit |
| `RepairIncident` | `incident:{id}:repair`; `RecoveryCommandService` | `repair_actions`, correction/audit/existing canonical transition event; never user SQL |

API route-to-command mapping is one-to-one with BACKEND-02 operation IDs. Workflow step commands use key `workflow:{workflow_run_id}:step:{step_name}:v{step_version}` and actor type `WORKFLOW`; they can request only registered transitions for their frozen run. Provider observations enter provider capture services with actor type `PROVIDER`; they cannot invoke arbitrary commands. Agents never appear as command actors.

### Exact approval authority and lifecycle

`RequestApproval` loads one DB-03 `outreach_messages` composite plus campaign/member/lead/mailbox/artifact and a current allowed SEND `policy_decisions` row. It constructs `ApprovalScopeV1` with literal schema version 1 and exact experiment/campaign ID+version/lead/message/mailbox/content hash/artifact version refs/policy version/facts hash/intended operation/max send count=1/expiry. `scope_hash` and `artifact_version_refs_hash` use DB-01 RFC 8785 envelopes `approval.scope.v1` and `approval.artifact_refs.v1`. It inserts `PENDING` and emits `approval.requested.v1` atomically with `DRAFT -> APPROVAL_PENDING` where applicable.

`ApproveApproval` requires authenticated operator, state `PENDING`, exact unexpired scope/content/artifact/policy facts, and reason code; it enters `APPROVED`, sets decision fields, emits `approval.decided.v1`, and moves message to `APPROVED` only in the same transaction. `DenyApproval` enters `DENIED`, emits the same decision event with decision `DENIED`, and message `CANCELLED` under ARCH-03. `RevokeApproval` changes only `APPROVED -> REVOKED`, emits `approval.revoked.v1`, and prevents intent creation; it cannot cancel a possibly called attempt. `ExpireApproval` deterministically changes overdue `PENDING/APPROVED -> EXPIRED` with safe audit and invalidates the message's send eligibility. `ConsumeApproval` is legal only in the atomic `RecordSendIntent` bundle, changes `APPROVED -> CONSUMED`, and cannot be called as a freestanding API.

Changed message content/version, artifact refs, campaign version, recipient/lead/mailbox, policy version/facts, scope, expiry, or suppression/control does not mutate/rebase an approval: the old approval is revoked/expired, a new request gets a new UUID/scope hash, and queued intent creation is denied. Approval never grants product outreach, budget, rate, jurisdiction, or provider authority by itself.

### Controls, retries, and recovery authority

`DisableSystemControl` is always permitted to an active authenticated operator for the named control and commits before worker signals. `EnableSystemControl(PRODUCT_OUTREACH)` additionally requires verified retained M1 and M6 gate IDs/hashes, no open blocking incident/unresolved ambiguity, current compliance/security evidence, and explicit reason/evidence. Success changes a control only; it creates no campaign/member/message/intent/queue/reservation. `EnableSystemControl(TEST_INBOX_SENDING)` requires the M6 owned-alias manifest and cannot alter product control.

Pause/cancel requested versus acknowledged states follow WF-06 exactly. `RetryExperimentStage` creates a new workflow run; it never resumes a terminal run. `RetrySend` is internal to `SendRecoveryService` and requires conclusive no-send plus all ARCH-03 guards. `ReconcileSendAttempt` may only read the immutable authorized mailbox. `RepairIncident` accepts a registered repair kind, expected before hash, desired after hash/evidence; it records `repair_actions` and executes an existing typed transition. Arbitrary field patch and SQL strings are rejected.

### Errors, telemetry, fixtures, and example

Handlers return only BACKEND-02 `error_code` values with exact safe reasons: `COMMAND_IN_PROGRESS`, `APPROVAL_NOT_PENDING`, `APPROVAL_EXPIRED`, `APPROVAL_ALREADY_CONSUMED`, and `RUNTIME_ACK_PENDING` are reason codes under 409 `STATE_TRANSITION_DENIED`; `APPROVAL_SCOPE_MISMATCH` is a reason under 409 `VERSION_CONFLICT`; `ACTOR_NOT_ALLOWED` maps to 403 `AUTHORIZATION_DENIED`; `CONTROL_GATE_MISSING` maps to 403 `POLICY_DENIED`; `REPAIR_KIND_NOT_ALLOWED` maps to 400 `VALIDATION_FAILED`; and an unregistered internal command is 500 `INTERNAL_ERROR` and opens an incident. No command-only alias escapes in API `error_code`; every safe denial is audited.

Fixtures contain exact request/result schema versions/payloads/hashes, actor/scope/key, initial rows, expected rows/events/audit/outbox, runtime/provider call count, and replay outcome. Telemetry contains safe command/actor-type/aggregate IDs, versions, replay, status/error/reasons, duration, runtime signal status, and correlation—not approval content, address, credentials, raw facts, or command sensitive payload.

```json
{"schema_version":"api.decide_approval.request.v1","reason_code":"OPERATOR_REVIEWED_EXACT_SCOPE"}
```

## Ordered implementation tasks

- [ ] **Implement command envelope/registry/executor —** Input: DB-01/05 hashes/tables and registry above. Operation: encode strict commands, actor rules, scopes, atomic replay/result semantics, and safe errors. Output: command bus. Test evidence: schema/registry/concurrency/failure-injection matrix. Failure behavior: unregistered/invalid command never calls service.
- [ ] **Implement approval lifecycle —** Input: exact message/campaign/mailbox/artifact/policy scope. Operation: hash/request/decide/revoke/expire/consume in documented transactions/events. Output: one immutable one-send authority or denial. Test evidence: transition/scope/race/replay/expiry tests. Failure behavior: no intent/provider call.
- [ ] **Implement stage/control/runtime handlers —** Input: authenticated/API or frozen workflow commands. Operation: commit product intent first, signal runtime after commit, record acknowledgement/failure visibly. Output: canonical states/events. Test evidence: kill/restart at request/signal/ack boundaries. Failure behavior: keep controls closed/request pending.
- [ ] **Implement send/recovery/control enable gates —** Input: M1/M6 evidence, intent/attempt/control/incident facts. Operation: route only exact owners and enforce separate test/product authority. Output: safe queued/reconcile/retry/control result. Test evidence: missing/stale gate, ambiguity, suppression, and repair matrices. Failure behavior: no send/enable.
- [ ] **Prove audit/API/operator workflows —** Input: command fixtures/OpenAPI/browser flows. Operation: verify exact response replay, denial audit, approval/control/recovery visibility, and safe telemetry. Output: M6/M7 command evidence. Test evidence: contract/E2E/redaction scans. Failure behavior: release blocked.

## Test strategy

- **Idempotency `test_same_command_hash_replays_and_different_hash_conflicts`:** no second event/runtime/provider call.
- **Approval `test_changed_any_authority_field_invalidates_approval_and_requires_new_uuid`:** every tuple column.
- **Concurrency `test_two_approval_decisions_or_consumptions_have_one_winner`:** PostgreSQL optimistic/unique enforcement.
- **Control `test_product_outreach_enable_requires_m1_m6_and_grants_no_campaign_recipient_spend`:** exact negative proof.
- **Runtime `test_signal_failure_leaves_requested_state_visible_and_no_false_ack`:** restart-safe.
- **Authority `test_agent_provider_and_frontend_cannot_register_or_execute_business_commands`:** graph/runtime object test.

## Security, privacy, compliance, idempotency, observability, and cost

Strong operator auth, actor allowlists, expected versions, reason/evidence, and safe audit apply even for one operator. Approval records hashes/IDs, not decrypted content. Command replay horizon and retention are `SAFETY_LONG`; sensitive business content follows DB-06. Provider/workflow signals carry IDs only. Metrics show conflicts, denials, pending acknowledgement, approval age/expiry, control changes, repair, and correlation. Command success never bypasses provider budget/cost policy.

## Failure, rollback, and operator recovery

On stuck command, unknown handler, split event/result suspicion, duplicate decision, false runtime acknowledgement, or authority mismatch: stop affected workers/dequeue, close send controls where relevant, preserve rows/events, compare the exact hash chain, and run a typed recovery claim/repair. Roll back code without changing stored results. Never delete an `IN_PROGRESS` row, edit approval scope, or force a runtime state through SQL.

## Acceptance and retained evidence

- [ ] Every mutation has one canonical command type/scope/actor/owner/schema/hash/result/event set.
- [ ] Replay, version conflict, concurrency, runtime signalling, and failure behavior are explicit and tested.
- [ ] Approval is immutable exact one-send authority and cannot override current suppression/policy/control/budget/rate.
- [ ] Test/product controls and M1/M6 gates remain separate; enable grants no downstream authority.
- [ ] Recovery uses typed audited commands, never direct SQL/provider replay.

Retain command registry/schema/hash snapshots, concurrency/replay/failure traces, approval scope/event fixtures, control/gate denials, runtime signal/ack crash evidence, repair records, API/browser E2E, authority graph, and safe telemetry/redaction scans.

## Dependencies and next deliverable

BACKEND-05 depends on BACKEND-01 through BACKEND-04 and exact DB/ARCH/WF contracts. It unlocks the M6 operator-controlled pilot and M7 approval/control frontend; it never authorizes a real send without the separate exact intent/gateway path.
