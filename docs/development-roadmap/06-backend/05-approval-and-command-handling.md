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
| `PauseExperiment`, `ResumeExperiment`, `CancelExperiment`, `CancelRun` (API `cancelWorkflowRun`), `RetryExperimentStage`, `ReviseExperiment` | exact aggregate scope; `ControlCommandService`/`ExperimentCommandService` | WF-06 exact requested/acknowledged experiment/run events; retry creates new run |
| `RecordExperimentDecision` | `experiment:{id}:decision`; `ExperimentCommandService` | immutable decision; `experiment.decision_recorded.v1`, state-changed |
| `CreateCampaignVersion`, `ReadyCampaign`, `ActivateCampaign`, `PauseCampaign`, `ResumeCampaign`, `CancelCampaign` | `campaign:{id}:version:{version}`; `CampaignCommandService` | exact complete campaign event family plus state-changed |
| `RequestApproval`, `ApproveApproval`, `DenyApproval`, `RevokeApproval`, `ExpireApproval`, `ConsumeApproval` | `approval:{approval_id}` or new exact scope; `ApprovalCommandService` | `approval.requested.v1`, `approval.decided.v1`, or `approval.revoked.v1`; consumption has safe audit and message/intent bundle event rather than invented domain alias |
| `RecordSendIntent` | `message:{id}:send-intent`; BACKEND-04 prerecord path | intent/queue result; `send.intent_recorded.v1`, `send.queued.v1` |
| `ExecuteSendAttempt` | `send-intent:{id}:attempt:{n}`; `SendGateway` | BACKEND-04 result events |
| `ReconcileSendAttempt`, `RetrySend`, `AbortSendRetry` | `send-attempt:{id}:recovery` or intent retry scope; `SendRecoveryService` | reconciliation/retry/exhaustion exact events |
| `EnableSystemControl`, `DisableSystemControl` | `control:{control_name}`; `ControlCommandService` | `system.outreach_enabled.v1`/`system.outreach_disabled.v1` only for `PRODUCT_OUTREACH`; test control uses safe audit/control version without inventing product event |
| `CompleteGmailAuthorization` | scope family `gmail.oauth.complete`, concrete `gmail.oauth.complete:{oauth_flow_id}`; `GmailMailboxCommandService` through PROVIDER-01 | stored opaque redirect result; audit-only OAuth type, no domain-event alias |
| `SyncGmailMailbox`, `RevokeGmailAuthorization` | `gmail-mailbox:{id}`; Gmail mailbox/history owners | finite sync/revoke result; cursor event only when cursor advances |
| `AcceptArtifact`, `RejectArtifact`, `SupersedeArtifact` | `artifact:{id}`; validation/acceptance owners | exact artifact events, never agent-authored |
| `SuppressRecipient`, `SuppressBusiness`, `EnableGlobalSuppression`, `DeactivateSuppression` | target scope; `SuppressionCommandService` | `suppression.created.v1`/`suppression.deactivated.v1`, `lead.suppressed.v1` for each lead transition, safe audit/outbox |
| internal `RecordRecipientStopSignal` | `recipient-signal:{source}:{source_record_id}`; `RecipientSignalSuppressionService` -> `SuppressionCommandService.record_observed_signal` | observation/reply or public token result, active recipient suppression, lead/pre-call-message transitions, provably-uncalled intent closure/release, canonical events/audit/outbox and Gmail cursor commit atomically |
| `RepairIncident` | `incident:{id}:repair`; `RecoveryCommandService` | `repair_actions`, correction/audit/existing canonical transition event; never user SQL |

### Campaign readiness, finite stage, and workflow cancellation commands

`CreateCampaignVersion` accepts only BACKEND-02's strict `membership_mode="ALL_CURRENTLY_ELIGIBLE"` snapshot request. `CampaignCommandService` locks the expected experiment version, validates exact same-experiment offer/version and policy, recomputes `campaign.eligibility.v1` from all current qualified/unsuppressed leads and exact accepted compliance artifacts, byte-matches the expected snapshot hash/count, and requires the complete set to fit the request and signed experiment member caps. It inserts the immutable campaign and every sorted member in one transaction, then independently recounts/rehashes before commit. The request has no member/lead-ID list and there is no preliminary lead-list command or endpoint. Zero, overflow, drift, stale evidence, subset, duplicate, or cross-experiment input fails with no partial rows.

`ReadyCampaignRequestV1` locks exact `(campaign_id,campaign_version)` in `DRAFT`, verifies its immutable offer/policy references, at least one exact `ELIGIBLE` member, and every draft/approval requirement recorded, then atomically commits `READY`, `campaign.ready.v1`, `campaign.state_changed.v1`, audit/outbox/idempotent `CampaignVersionResponseV1`. It cannot activate, create an intent, or start a run. `ActivateCampaign` remains separate.

`StartOutreachAndReplyRequestV1` requires latest experiment `If-Match`, `READY_FOR_OUTREACH`, exact active campaign ID/version/state, current M1/M6 evidence IDs, correct isolated-test or separately enabled product control, accepted artifacts, no suppression/ambiguity/blocking incident, and workflow budget/caps. It atomically creates one finite `OUTREACH_AND_REPLY` run and transitions the experiment to `OUTREACH_ACTIVE`; receipt carries the new `workflow_run_id`. `StartExperimentEvaluationRequestV1` requires latest experiment ETag and either no-send `READY_FOR_OUTREACH` evidence or closed-outreach `EVALUATING` evidence, exact metric snapshot/evidence bundle/rule versions, and creates one finite `EXPERIMENT_EVALUATION` run; no decision is recorded. Active-run uniqueness rejects duplicates.

`CancelWorkflowRunRequestV1` maps only to internal `CancelRun`: lock nonterminal run in exact expected state, verify its aggregate permits cancellation, commit `CANCEL_REQUESTED`/audit/outbox/idempotent receipt, then signal runtime. It never infers experiment/campaign cancellation. The resulting run remains queryable through `getWorkflowRun`; acknowledgement later commits `CANCELLED` and `workflow.run_cancelled.v1`.

### Suppression command and query contract

`createSuppression` maps the strict target union to exactly one registered command: `GLOBAL -> EnableGlobalSuppression`, `BUSINESS -> SuppressBusiness`, `RECIPIENT -> SuppressRecipient`. The RECIPIENT arm accepts only safe opaque `recipient_source_ref_id=campaign_member_id`; `recipient_target_ref_id` is output/projection identity and cannot be supplied to create. Server forces `source=OPERATOR`, locks and resolves the member to the restricted deterministic SHA-256 lookup only inside `SuppressionCommandService`, allocates one random UUIDv4 target ref for a new row, inserts active version 1, emits `suppression.created.v1` with that ref, transitions every matching nonarchived lead with `lead.suppressed.v1`, writes safe audit/outbox/result, and invalidates final-SEND dequeue facts before commit. Same scope/key/hash returns the stored result/ref; a different command for the same active lookup returns 409. Provider/public creation uses its locked message/member binding and the same create-or-return primitive. No address/hash/ciphertext/digest crosses API, event, report, log or export.

The persisted target ref has no source-member foreign key and is immutable across deactivation, member removal, allowed retention purge, list projection rebuild, event delivery and command replay. Query/replay code must read `suppression_entries.recipient_target_ref_id`; resolving it from `recipient_hash`, looking up a removed member, accepting hash-like HTTP input, or emitting a null ref for RECIPIENT is a contract violation. GLOBAL/BUSINESS responses carry null target ref. `SuppressionCommandService` remains the only row writer and lookup-material reader.

Provider-observed reply/unsubscribe/hard-bounce/complaint/soft-bounce-limit and public unsubscribe POST do not impersonate the operator command. They create strict internal `RecordRecipientStopSignalV1={source,source_actor_type,provider_observation_id?,reply_id?,public_token_result_hash?,campaign_member_id,message_id,mailbox_id,observed_at,reason_code}`; the source-specific union is extra-forbid and never contains a target ref, recipient hash, address ciphertext, or lookup digest. `RecipientSignalSuppressionService` claims the source-derived key and coordinates the single DB-03 transaction through `SuppressionCommandService.record_observed_signal`; its stored result includes the resulting durable target ref for exact replay. Unknown source/actor, mismatched observation/reply/message/mailbox, stale public token, or partial command state rejects. If the transaction or Gmail sync cannot prove the atomic stop bundle, a separate fail-closed system command disables `PRODUCT_OUTREACH`, opens the registered incident and prevents acknowledgement until repair.

`DeactivateSuppression` requires `If-Match`, `expected_active=true`, authenticated operator reason, both send controls false, no matching nonterminal message/intent/attempt, no ambiguity/reconciliation, and no blocking incident. It locks target and matching authority rows, increments version, sets inactive/deactivated UTC, emits `suppression.deactivated.v1`, and audits. It never automatically requalifies a lead, reactivates a campaign, or enables a control. `listSuppressions` bypasses caches; the gateway always reads locked PostgreSQL suppression rows after dequeue and never trusts UI/query cache.

### Artifact read, acceptance, and rejection contract

`getArtifact`, `listArtifactEvidence`, and `getEvaluationResult` are read-only query owners over DB-04 allowlisted fields. Restricted content/capture refs, prompts, source excerpts, addresses, and provider payloads never serialize. `AcceptArtifact` requires exact ID/version/content hash, locked `VALIDATED` status, latest deterministic validation with `schema_valid=true`, `provenance_valid=true`, no reason codes, complete evidence links, non-superseded version, authenticated operator reason, and idempotency; it writes acceptance/status, `artifact.accepted.v1`, audit/outbox/result atomically. `RejectArtifact` requires exact version/hash and `PRODUCED` or `VALIDATED`, reason, no acceptance/materialization/dependent authority, then writes `REJECTED`, `artifact.rejected.v1`, audit/outbox/result. Stale/hash/superseded/terminal races fail without mutation.

### FastAPI operator-session boundary

`startOperatorAuthorization`, `completeOperatorAuthorization`, `getOperatorSession`, and `endOperatorSession` belong to BACKEND-02 `OperatorSessionService`, not the business command registry and not Gmail OAuth. They may authenticate/revoke only the configured operator subject; session/flow handles and provider tokens never become command payloads or agent/workflow/provider authority. Every business command actor is resolved from the server-side session before command hashing; Origin/CSRF failure prevents registry entry and audit records only safe denial metadata.

### OAuth callback command exception

`CompleteGmailAuthorization` is the only browser GET mutation without caller `Idempotency-Key`. Verified signed/encrypted state yields preallocated `oauth_flow_id`/`mailbox_id`; the handler derives scope `gmail.oauth.complete:{oauth_flow_id}` and key `oauth-flow:{oauth_flow_id}`. `api.complete_gmail_authorization.request.v1` hashes flow ID, state-token hash, authorization-code hash, and fixed redirect ID only. `IdempotentCommandExecutor` commits `IN_PROGRESS` before exchange; correlation remains metadata.

OAuth `IN_PROGRESS` is resumable only through the registered handler after secret-store CAS grants expired/free `oauth-handler:{oauth_flow_id}` lease. Same live lease returns 409 `STATE_TRANSITION_DENIED` reason `COMMAND_IN_PROGRESS`; same scope/key/request with a different hash is `IDEMPOTENCY_HASH_CONFLICT`. A resume reads only the flow-indexed secret object and never invokes exchange after `EXCHANGE_STARTED`.

`GmailOAuthSagaService` then performs the exact PROVIDER-01 states: one exchange, idempotent STAGE, idempotent ACTIVATE, and signed `ActiveCredentialProofV1` under a 30-second bind lease. STAGED/ACTIVE before DB is not command success and is not product-addressable. `GmailMailboxCommandService` validates proof signature/expiry and atomically writes the exact DB-03 flow/account/scope/handle/version/key/generation tuple, ACTIVE mailbox, safe audit, and `SUCCEEDED` 303 result. Success cannot precede ACTIVE. Post-commit bind marking is idempotent metadata repair; crash after DB replays the stored redirect.

Crash before exchange resumes and exchanges once. Crash after exchange with no STAGED object performs three strong reads then stores a `SUCCEEDED` command result with typed `outcome=FAILURE`, reason `OAUTH_EXCHANGE_NOT_DURABLE`, and fixed `oauth_restart_required`, and never exchanges again. Crash after STAGED or ACTIVE resumes without exchange. Clean dependency exhaustion while a resumable object exists leaves command `IN_PROGRESS` and returns safe 503 `DEPENDENCY_UNAVAILABLE`/`Retry-After`; it never converts resumable state into false failure.

`OAuthCredentialGarbageCollector` may CAS an orphan to `GC_CLAIMED` only after 24 hours, no handler/bind lease, and one repeatable-read DB snapshot proving no exact mailbox and no matching `IN_PROGRESS` command; it rechecks before revoke/delete. GC and callback have one CAS winner. A stuck resumable IN_PROGRESS saga is never deleted by age; typed `RepairIncident(ABORT_OAUTH_SAGA)` first proves no lease/mailbox, stores the fixed SUCCEEDED failure-outcome result, and closes the flow. Any DB/secret tuple mismatch makes `GmailCredentialConsistencyService` deny token access, disable mailbox/controls, record safe incident/audit, and require authenticated repair or fresh authorization. This exception adds no credential product table and never admits query secrets, token material, or provider text to PostgreSQL/logs.

API route-to-command mapping is one-to-one with BACKEND-02 operation IDs. Workflow step commands use key `workflow:{workflow_run_id}:step:{step_name}:v{step_version}` and actor type `WORKFLOW`; they can request only registered transitions for their frozen run. Provider observations enter provider capture services with actor type `PROVIDER`; they cannot invoke arbitrary commands. Agents never appear as command actors.

### Exact approval authority and lifecycle

`RequestApproval` loads the exact DB-03 outreach-message/campaign/`campaign_member_id`/lead/mailbox/artifact composite and constructs strict `PolicyScopeV1`/`ApprovalBasisScopeV1` with experiment, campaign ID/version/member, lead, message ID/version/content hash, mailbox/provider-account hash, artifact version references, exact recipient-identity/jurisdiction/consent-or-counsel-exception/legal-review/legal-policy/disclosure-sender-template/Google-policy artifact ID-version-hash references, intended operation `SEND`, cap one, and expiry. `scope_hash` uses `policy.scope.approval_basis.v1`; artifact refs use `approval.artifact_refs.v1`.

The command evaluates a new `APPROVAL_ELIGIBILITY` policy scope that excludes ApprovalRule and every mutable send fact. Only an allowed eligibility result may, in the same transaction, insert a `PENDING` approval containing `eligibility_policy_decision_id`, eligibility version/facts hash/allowed flag, the immutable basis hash, `approval.requested.v1`, safe audit/idempotent result/outbox, and `DRAFT -> APPROVAL_PENDING`. Eligibility denial creates no approval/event and maps to 403 `POLICY_DENIED`. It can never create an intent, consume approval, reserve rate, enqueue, or send.

`ApproveApproval` is manual-only. It requires an authenticated operator with step-up reauthentication no older than five minutes, `PENDING`, exact unchanged/unexpired basis and eligibility binding, a reason code, and BACKEND-02's fresh opaque preview receipt. `ApprovalPreviewService` verifies the receipt, locks and re-materializes the exact recipient address, subject, body, rendered RFC 822 bytes, experiment/campaign/version/member/lead/message/version/content/mailbox/account/scope/artifact tuple, and requires its RFC 8785 SHA-256 to byte-equal the receipt. The transaction stores only `previewed_by_operator_id`, `preview_materialization_hash`, `preview_receipt_hash`, preview timestamps, and the decision; enters `APPROVED`; emits `approval.decided.v1`; and moves the message to `APPROVED`. No agent, workflow, policy, system actor, campaign rule, batch command, or timer can approve. `DenyApproval` enters `DENIED` and message `CANCELLED` without requiring or accepting a preview receipt. `RevokeApproval` changes only `APPROVED -> REVOKED`; `ExpireApproval` changes overdue `PENDING/APPROVED -> EXPIRED`. All preserve the original eligibility decision/basis and any preview proof. `ConsumeApproval` is legal only inside `RecordSendIntent`, changes `APPROVED -> CONSUMED`, and the unique preview-bound `send_intents.approval_id` proves which intent consumed it; it has no standalone API.

`RecordSendIntent` validates the exact campaign member and approved basis plus stored preview materialization hash, re-renders the same recipient/content/mailbox tuple, requires an exact hash match and unexpired approval, reserves budget, consumes approval, copies message version/content/preview hashes into the intent, writes the stable RFC identity, and queues. It does not create/reuse a SEND decision. `ExecuteSendAttempt` later locks/rereads that manually previewed, uniquely intent-consumed tuple and copies the preview hash into the attempt, plus current recipient identity, jurisdiction, consent-or-exception, legal review/policy, disclosure/sender template, Google compatibility, reply/unsubscribe/bounce/complaint/soft-bounce-limit, suppression, control, budget, rate and ambiguity facts; it copies the same `scope_hash` and writes its own current `send_policy_facts_hash`. Every missing preview or dedicated compliance/signal denial stops before rate reservation/attempt/credential access/provider call.

Changed immutable message/campaign/member/lead/mailbox/content/artifact/basis/expiry fields revoke or expire the old approval and require a new UUID/eligibility decision. Mutable suppression/control/budget/rate/jurisdiction changes do not rewrite the approval; they are final-SEND inputs. Approval grants no outreach, budget, rate, jurisdiction, or provider authority by itself.


### Controls, retries, and recovery authority

`DisableSystemControl` accepts exactly two internal actor arms. `OPERATOR` requires the active authenticated operator and is the only arm exposed by BACKEND-02. `SYSTEM` is internal-only, requires one closed actor ID from DB-01 plus exact canonical reason/evidence, may only change `true -> false` (or replay the same false result), and never fabricates an operator UUID. Suppression, Gmail ambiguity, telemetry blindness, backup witness, credential consistency, and send-authority guards invoke that system arm through `ControlCommandService` in the same fail-closed unit of work or before further dequeue. Both arms commit row/event/audit/idempotent result/outbox before worker signals. `EnableSystemControl` rejects every non-operator actor; `PRODUCT_OUTREACH` additionally requires verified retained M1 and M6 gate IDs/hashes, no open blocking incident/unresolved ambiguity, current compliance/security evidence, and explicit reason/evidence. Success changes a control only; it creates no campaign/member/message/intent/queue/reservation. `EnableSystemControl(TEST_INBOX_SENDING)` requires the M6 owned-alias manifest and cannot alter product control.

Pause/cancel requested versus acknowledged states follow WF-06 exactly. `RetryExperimentStage` creates a new workflow run; it never resumes a terminal run. `RetrySend` is internal to `SendRecoveryService` and requires either an explicit provider rejection or signed local pre-write proof that request bytes never left the process, plus all ARCH-03 guards; timeout, age, negative search/history, conflict, and operator assertion are ineligible. `ReconcileSendAttempt` may only read the immutable authorized mailbox. `RepairIncident` accepts a registered repair kind, expected before hash, desired after hash/evidence; before command claim it byte-matches the exact `incident.catalog.v1` trigger/alert/runbook route and validates resolution applicability plus repair/runbook applicability. Residual-risk acceptance rejects for HIGH/CRITICAL and every OBS-05 non-waivable trigger. PostgreSQL repeats route/resolution enforcement; the command records `repair_actions` and executes an existing typed transition. Arbitrary field patch and SQL strings are rejected.

### Errors, telemetry, fixtures, and example

Every final-SEND compliance/signal denial maps to 403 `POLICY_DENIED` with its dedicated BACKEND-03 code; generic jurisdiction/authority codes and free text cannot substitute.

Handlers return only BACKEND-02 `error_code` values with exact safe reasons: `ELIGIBILITY_POLICY_DENIED` and final mutable policy denials map to 403 `POLICY_DENIED`; `APPROVAL_BASIS_MISMATCH` and `CAMPAIGN_MEMBER_MISMATCH` map to 409 `VERSION_CONFLICT`; OAuth replay conflict maps internally to 409 `IDEMPOTENCY_HASH_CONFLICT`, while invalid/uncertain OAuth maps to 400 `OAUTH_CALLBACK_INVALID` or 503 `DEPENDENCY_UNAVAILABLE` and fixed opaque redirects. `CAMPAIGN_NOT_DRAFT`, `CAMPAIGN_READINESS_GUARD_FAILED`, `WORKFLOW_RUN_STATE_MISMATCH`, `SUPPRESSION_TARGET_IN_FLIGHT`, `SUPPRESSION_CONTROLS_NOT_DISABLED`, `ARTIFACT_NOT_VALIDATED`, `ARTIFACT_SUPERSEDED`, `COMMAND_IN_PROGRESS`, `APPROVAL_NOT_PENDING`, `APPROVAL_EXPIRED`, `APPROVAL_ALREADY_CONSUMED`, and `RUNTIME_ACK_PENDING` are reason codes under 409 `STATE_TRANSITION_DENIED`; `ARTIFACT_VERSION_MISMATCH`, `ARTIFACT_HASH_MISMATCH`, and `APPROVAL_SCOPE_MISMATCH` are reasons under 409 `VERSION_CONFLICT`; `ACTOR_NOT_ALLOWED` maps to 403 `AUTHORIZATION_DENIED`; `CONTROL_GATE_MISSING` maps to 403 `POLICY_DENIED`; `REPAIR_KIND_NOT_ALLOWED` maps to 400 `VALIDATION_FAILED`; and an unregistered internal command is 500 `INTERNAL_ERROR` and opens an incident. No command-only alias escapes in API `error_code`; every safe denial is audited.

Fixtures contain exact request/result schema versions/payloads/hashes, actor/scope/key, initial rows, expected rows/events/audit/outbox, runtime/provider call count, and replay outcome. Telemetry contains safe command/actor-type/aggregate IDs, versions, replay, status/error/reasons, duration, runtime signal status, and correlation—not approval content, address, credentials, raw facts, or command sensitive payload.

```json
{"schema_version":"api.decide_approval.request.v1","expected_state":"PENDING","reason_code":"OPERATOR_REVIEWED_EXACT_SCOPE","preview_receipt":"opaque-sign-then-encrypt-value"}
```

## Ordered implementation tasks

- [ ] **Implement command envelope/registry/executor —** Input: DB-01/05 hashes/tables and registry above. Operation: encode strict commands, actor rules, scopes, atomic replay/result semantics, and safe errors. Output: command bus. Test evidence: schema/registry/concurrency/failure-injection matrix. Failure behavior: unregistered/invalid command never calls service.
- [ ] **Implement eligibility-bound manual approval lifecycle —** Input: exact message/campaign/member/mailbox/artifact basis plus step-up preview receipt. Operation: evaluate eligibility without ApprovalRule, request, render sensitive preview, manually decide, revoke/expire/consume while preserving and rechecking the materialization. Output: one immutable preview-proven approval basis, never SEND authority. Test evidence: eligibility->preview->manual approval->fresh-SEND, auto-actor denial, member/recipient/content splice, stale/replayed receipt, mutable-fact, command replay, and expiry matrices. Failure behavior: no approval/intent/provider call.
- [ ] **Implement stage/control/runtime handlers —** Input: authenticated/API or frozen workflow commands. Operation: commit product intent first, signal runtime after commit, record acknowledgement/failure visibly. Output: canonical states/events. Test evidence: kill/restart at request/signal/ack boundaries. Failure behavior: keep controls closed/request pending.
- [ ] **Implement all-current-eligible campaign snapshot creation —** Input: expected experiment/offer/query/hash/count/caps only. Operation: lock, recompute, compare, insert every sorted eligible member, recount/rehash, and commit atomically. Output: one immutable complete membership snapshot. Test evidence: zero/overflow/drift/subset/duplicate/cross-experiment/concurrent-qualification negatives and exact-set positive. Failure behavior: no campaign/member row.
- [ ] **Implement send/recovery/control enable gates —** Input: M1/M6 evidence, intent/attempt/control/incident facts. Operation: route only exact owners and enforce separate test/product authority. Output: safe queued/reconcile/retry/control result. Test evidence: missing/stale gate, ambiguity, suppression, and repair matrices. Failure behavior: no send/enable.
- [ ] **Prove OAuth saga, callback, and operator workflows —** Input: versioned flow/credential objects, ACTIVE proofs, command/OpenAPI fixtures. Operation: execute six kill points, exact replay, bind/GC CAS race, mismatch disable, and redaction scans. Output: M6/M7 saga evidence with no success-before-ACTIVE. Test evidence: executable state-machine, browser replay, DB proof tuple, TTL/GC, incident fixtures. Failure behavior: release blocked.

## Test strategy

- **Idempotency `test_same_command_hash_replays_and_different_hash_conflicts`:** no second event/runtime/provider call.
- **OAuth `test_complete_gmail_oauth_claims_command_before_exchange_and_replays_stored_redirect`:** same flow exchanges once; different code conflicts.
- **OAuth saga `test_oauth_staged_and_active_pre_db_resume_without_second_exchange_or_replayable_success`:** exact ACTIVE proof precedes DB result.
- **OAuth kill matrix `test_oauth_cleanup_race_and_all_six_kill_points_have_one_safe_outcome`:** no success without active handle; only exchange-to-stage gap restarts.
- **Approval `test_changed_any_basis_field_including_campaign_member_invalidates_approval_and_requires_new_uuid`:** every tuple column.
- **Policy sequence `test_approval_eligibility_excludes_approval_rule_and_final_send_has_independent_facts`:** no circular lifecycle.
- **Concurrency `test_two_approval_decisions_or_consumptions_have_one_winner`:** PostgreSQL optimistic/unique enforcement.
- **Controls `test_system_actor_can_only_disable_with_closed_identity_reason_evidence_and_operator_alone_enables`:** exhaustive valid/invalid actor-state matrix; no fake operator row or public system arm.
- **Preview `test_approval_requires_step_up_exact_sensitive_preview_and_matching_materialization_receipt`:** standard views redact; content never reaches telemetry/cache; every stale/cross-session/operator/approval/content/recipient/hash receipt fails before approval.
- **Manual-only `test_no_agent_workflow_system_rule_or_batch_path_can_enter_approved`:** only the authenticated previewing operator can commit `PENDING -> APPROVED`.
- **Control `test_product_outreach_enable_requires_m1_m6_and_grants_no_campaign_recipient_spend`:** exact negative proof.
- **Runtime `test_signal_failure_leaves_requested_state_visible_and_no_false_ack`:** restart-safe.
- **Authority `test_agent_provider_and_frontend_cannot_register_or_execute_business_commands`:** graph/runtime object test.
- **Registry `test_all_66_api_operations_map_to_exact_query_session_or_registered_command_owner`:** no missing/alias command; public unsubscribe GET is read-only and POST maps only to observed suppression.
- **Signals `test_recipient_stop_signal_atomic_bundle_and_failure_disable_are_exact`:** every source, crash boundary, duplicate/concurrent delivery and gateway race proves suppression/cursor/no-next-SEND or product-off.
- **Campaign `test_create_ready_activate_start_outreach_are_four_separate_guarded_commits`:** exact state/events/runs.
- **Suppression `test_deactivation_requires_controls_off_no_inflight_and_fresh_version`:** gateway never trusts cache.
- **Artifact `test_accept_reject_lock_exact_version_hash_validation_and_terminal_state`:** stale/superseded fail.
- **Session `test_oidc_session_resolves_only_configured_operator_before_command_claim`:** no browser token/CSRF bypass.

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
