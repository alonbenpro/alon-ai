# Action Authorization, Exceptions, and Idempotent Commands

**Document ID:** BACKEND-05
**Status:** Planned M2/M6 command layer; no product commands, action authorizations, authentication, or handlers exist today
**Milestone:** M6, M7 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `BACKEND-05-T01 -> BACKEND-05-T02 -> BACKEND-05-T03 -> BACKEND-05-T04 -> BACKEND-05-T05 -> BACKEND-05-T06 -> BACKEND-05-T07`; cross-document task Inputs `BACKEND-05-T01 <- DB-05-T02,DB-01-T01,DB-01-T02; BACKEND-05-T02 <- SEC-02-T04,SEC-02-T05,SEC-03-T01,DB-03-T04,PROVIDER-01-T02; BACKEND-05-T03 <- BACKEND-03-T03; BACKEND-05-T05 <- DB-03-T03; BACKEND-05-T06 <- SEC-05-T02; BACKEND-05-T07 <- SEC-03-T01,PROVIDER-01-T03,BACKEND-02-T03,BACKEND-02-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [BACKEND-01](01-domain-services.md), [BACKEND-02](02-api-contracts.md), [BACKEND-03](03-policy-engine.md), DB-03/05, and ARCH-03/WF-06 control states
**Outputs:** Exact command registry, replay/concurrency semantics, immutable ActionAuthorityScopeV1, runtime/provider handoff, controls, and operator recovery commands
**Unlocks:** M6 safe pilot and M7 exception/control UI
**Risk:** Critical
**Complexity:** XL


## Outcome and current repository state

Normal permitted actions use immutable ActionAuthorityScopeV1 and deterministic fresh checks. Operator commands handle pre-run configuration, exceptions, incidents, kill/recovery, protected legal decisions and explicit strategy controls. No routine send, response, negotiation, checkpoint or booking waits for per-message approval. No product command/auth/authority service described here is implemented today.

Every mutation enters a registered strict handler with authenticated service/operator scope, expected versions, exact request hash and idempotency key. Agents cannot be command actors. A command may ask the responsible deterministic owner to act; it cannot supply authority or a provider client.

## Exact planned implementation surfaces

Create application/command_bus.py, application/action_authorization.py, application/exceptions.py, application/controls.py, application/recovery.py and typed application/contracts modules. Preserve IdempotentCommandExecutor and sole table owners. SensitivePreviewService is an optional purpose-scoped operator inspection path, never part of routine action creation.

### Shared command and replay contract

`CommandEnvelopeV1` contains literal text request schema version, command type/scope, idempotency key, actor type/ID, expected aggregate type/ID/version where applicable, correlation/causation UUIDv4, issued UTC, and strict payload. Request hash is DB-01 RFC 8785/SHA-256 over the exact schema/payload. `CommandResultV1` uses the route/command's exact result schema/payload/hash and maps to BACKEND-02 `CommandReceiptV1` or resource.

The executor transaction is exact: insert/lock `(command_scope,idempotency_key)` as `IN_PROGRESS`; compare request schema/hash on replay; load/lock expected versions/authority; call one handler/service; write aggregate plus exact domain/audit/outbox bundle; store `SUCCEEDED` result triplet or typed `FAILED` error with SQL-null result triplet; commit. Same hash replays; a live `IN_PROGRESS` returns 409/retry-safe status and never starts another handler; stale orphan inspection compares aggregate/events before an authenticated recovery claim. Different hash is `IDEMPOTENCY_HASH_CONFLICT`.

Provider calls never occur in the command transaction. A committed command may enqueue an outbox/internal durable start signal. Direct runtime control signaling occurs only after the requested product state commits; signal failure leaves the request visible (`PAUSE_REQUESTED`/`CANCEL_REQUESTED`), records safe failure/incident, and retries the signal idempotently—it does not roll back product intent or claim acknowledgement.


### Exact command registry and authority

| Commands | Owner / key scope | Result |
| --- | --- | --- |
| CreateExperiment, ApproveExperimentScope, ConfigureOfferEnvelope, ReviseExperiment | ExperimentCommandService and brief owner; experiment ID/version | immutable pre-run scope and canonical experiment events |
| MaterializeSuppliedIdea, AcceptOfferPackage | IdeaBriefMaterializer / OfferMaterializationService; experiment + artifact version/hash | accepted validated canonical record; cannot skip Market Research or change active cohort |
| StartResearch, StartLeadQualification, StartOutreachAndReply | stage service; experiment/campaign/cohort/version | finite workflow; only registered next cohort after prior CONTINUE, no direct effect |
| CompleteWorkflowRun, FailWorkflowRun, CancelRun, RetryExperimentStage | WorkflowRunProjectionService / experiment owner | finite requested/acknowledged state; terminal run never resumes |
| CreateCampaignVersion, ReadyCampaign, ActivateCampaign, PauseCampaign, ResumeCampaign, CancelCampaign | CampaignCommandService; campaign/version | immutable scope, exact canonical state/events |
| FreezeCohortMembership | CampaignAdmissionService; campaign/stage/generation | all server-selected currently eligible candidate members fitting smaller applicable cap; exact sorted set/hash, recipient uniqueness and stage tuple |
| AuthorizeAction, RevokeActionAuthority, ExpireActionAuthority, ConsumeActionAuthority | ActionAuthorizationService; action ID/version/scope_hash | immutable ActionAuthorityScopeV1 plus state/receipt; consumption internal-only within one intent/action transaction |
| RecordSendIntent, ExecuteSendAttempt | SendGateway; message or intent/attempt | durable intent, unique authority consumption, fresh SEND, one provider attempt protocol |
| ReconcileSendAttempt, RetrySend, AbortSendRetry | SendRecoveryService; intent/attempt | read reconciliation or guarded conclusive-failure retry; no ambiguity retry |
| RecordReplyObservation, EvaluateConversationTransition, PauseConversation | Gmail/history owners and ConversationService; provider message/conversation version | atomic cold-stop/full message/cursor; accepted response objective or terminal/exception |
| EvaluateCommercialProposal | CommercialPolicyEngine + CommercialDecisionService; proposal/input/rule hash | deterministic immutable NegotiationDecision |
| RecordBookingIntent, ProposeBookingSlots, ConfirmBookingSlot, CreateBookingEvent, RescheduleBookingEvent, CancelBookingEvent, ReconcileBookingAction | BookingGateway; booking/action/version/calendar key | separate buying-intent/call/slot evidence; durable kind-specific action/attempt/result and reconciliation |
| CloseCheckpoint, FreezeCheckpointEvidence, RecordCheckpointDecision | CheckpointEvaluationService; cohort/checkpoint/generation | immutable bundle, five-way decision and unique learning outbox trigger |
| EvaluateLearningProposals, PromoteGlobalStrategy, ScheduleStrategyActivation, ActivateStrategyAtBoundary, RequestStrategyRollback | StrategyActivationService; checkpoint/package/campaign-boundary/generation | validated per-agent result/evidence, approved package and boundary-only activation/rollback |
| OpenException, ResolveException, DismissException | ExceptionCommandService; exception/version | safe blocked reason/evidence/correction; resolution cannot waive bounds or authorize a side effect |
| EnableSystemControl, DisableSystemControl, DisableScopedActionControl | ControlCommandService; control/scope/generation | independent test/product Gmail/calendar/scoped controls; enable has fresh evidence and operator authority, never enqueue |
| CompleteGmailAuthorization, SyncGmailMailbox, RevokeGmailAuthorization | Gmail OAuth/mailbox/history owners; flow/mailbox key | exact ACTIVE proof/opaque redirect or finite sync/revoke |
| ConnectCalendarAccount, RevokeCalendarAuthorization | CalendarAccountService; configured calendar identity/generation | scoped credential proof or revocation; no write authority |
| AcceptArtifact, RejectArtifact, SupersedeArtifact | ArtifactAcceptanceService after deterministic validator/materializer | exact immutable receipt/event; routine accepted artifacts use service actor; protected legal evidence remains qualified operator/counsel only |
| SuppressRecipient, SuppressBusiness, EnableGlobalSuppression, DeactivateSuppression | SuppressionCommandService; target/version | opaque recipient target ref and exact canonical suppression transitions |
| RecordRecipientStopSignal | RecipientSignalSuppressionService coordinates designated writers; source message/token-derived key | atomic cold stop for each inbound message; durable suppression only when DurableSuppressionTriggerV1 is satisfied |
| RepairIncident | RecoveryCommandService; incident/repair/before hash | exact registered correction and immutable repair evidence, never SQL/unchecked resend |

Authoritative runtime RecordCheckpointDecision replaces the former operator runtime decision. Operator milestone-gate reviews remain separate release evidence. StartOutreachAndReply derives the next ordinal, validates prior CONTINUE and completed learning/retained baseline decision, and admits no unapproved post-scale stage at 1,000. A UI cannot submit member IDs or a smaller cherry-picked subset to improve metrics: the deterministic query/policy picks the eligible bounded set, freezes query/version/order/hash and rejects drift.

ReadyCampaign and workflow start validate accepted offer, initial/boundary strategy activation, final qualification, source/legal/economic envelope and current safety/capacity. Readiness grants no provider call. Pause/cancel commits requested state before runtime signal and preserves ambiguous effects.

### Action authority lifecycle

AuthorizeAction loads the exact immutable artifact/content/member/recipient/thread/offer/strategy/activation/commercial tuple, verifies claim coverage, policy evidence and current generation, hashes ActionProposalScopeV1 first, then evaluates ACTION_CREATION. Only afterward does it attach the creation decision/facts and compute ActionAuthorityScopeV1's final scope_hash; no digest includes itself. Allowed creates PENDING -> AUTHORIZED with action.authorization_created.v1; denied creates DENIED/exception evidence with no intent. The full scope bytes/hash never change.

Changed content/recipient/thread/offer/activation/evidence/generation requires a new authorization ID. Revoke/expire records lifecycle evidence without rewriting original scope. ConsumeActionAuthority is only called inside the corresponding RecordSendIntent or booking-action transaction and inserts one immutable consumption receipt; unique authorization ID and typed-target constraint prevent duplicate or cross-provider consumption.

RecordSendIntent materializes exact RFC822 content with deterministic renderer and hashes recipient/subject/body/mailbox/thread/notification-context, requires byte equality with authorized materialization, reserves budget, consumes authority and creates stable mailbox idempotency/RFC identity before queue. Fresh SEND later rechecks consumed authority and all current facts; no creation-time policy decision is reused as final authority.

Booking actions similarly bind confirmed slot, calendar/event/version, attendee set and notification mode. Changing any of them creates new authority. Confirmation authorizes only its exact CREATE/RESCHEDULE action; a cancel is a new explicit request/policy action. No cancellation compensates an ambiguous create until exact provider truth is known.

### Exception inspection and suppression

SensitivePreviewService requires authenticated operator, registered purpose/exception ID, step-up no older than five minutes, exact scope/materialization hash and no-store response. Opaque receipt is sign-then-encrypt and session/operator/action/version-bound with short expiry. It can support a concrete exception correction or investigation but cannot approve a routine send or override legal/commercial bounds.

Suppression RECIPIENT creation accepts only opaque recipient_source_ref_id=campaign_member_id. The sole suppression writer resolves restricted lookup material under lock, creates/idempotently returns the active entry and durable random recipient_target_ref_id, and returns only that ref. It survives source purge and no API/event/export/report derives it from the hash. GLOBAL/BUSINESS have null recipient target refs.

Observed signals keep authenticated provider/system provenance. Every reply atomically records full message/cold stop/generation/cursor; durable suppression requires the exact PRODUCT-01 predicate and evidence. Positive replies/questions/objections can enter fresh bounded response authority. Decline closes persuasion; negative sentiment/ambiguous intent pauses to exception. Clear unsubscribe, complaint, hard bounce, qualifying no-future-contact or legal/registered bounce trigger commits suppression/no-next-action in that transaction. Failure independently disables product effects.

DeactivateSuppression requires expected version, both send controls false plus affected calendar/scoped controls closed, no matching unresolved action or incident, and protected counsel/evidence where required. It never requalifies, creates authority or enables control.

### FastAPI operator-session boundary

`startOperatorAuthorization`, `completeOperatorAuthorization`, `getOperatorSession`, and `endOperatorSession` belong to BACKEND-02 `OperatorSessionService`, not the business command registry and not Gmail OAuth. They may authenticate/revoke only the configured operator subject; session/flow handles and provider tokens never become command payloads or agent/workflow/provider authority. Every business command actor is resolved from the server-side session before command hashing; Origin/CSRF failure prevents registry entry and audit records only safe denial metadata.

### OAuth callback command exception

`CompleteGmailAuthorization` is the only browser GET mutation without caller `Idempotency-Key`. Verified signed/encrypted state yields preallocated `oauth_flow_id`/`mailbox_id`; the handler derives scope `gmail.oauth.complete:{oauth_flow_id}` and key `oauth-flow:{oauth_flow_id}`. `api.complete_gmail_authorization.request.v1` hashes flow ID, state-token hash, authorization-code hash, and fixed redirect ID only. `IdempotentCommandExecutor` commits `IN_PROGRESS` before exchange; correlation remains metadata.

OAuth `IN_PROGRESS` is resumable only through the registered handler after secret-store CAS grants expired/free `oauth-handler:{oauth_flow_id}` lease. Same live lease returns 409 `STATE_TRANSITION_DENIED` reason `COMMAND_IN_PROGRESS`; same scope/key/request with a different hash is `IDEMPOTENCY_HASH_CONFLICT`. A resume reads only the flow-indexed secret object and never invokes exchange after `EXCHANGE_STARTED`.

`GmailOAuthSagaService` then performs the exact PROVIDER-01 states: one exchange, idempotent STAGE, idempotent ACTIVATE, and signed `ActiveCredentialProofV1` under a 30-second bind lease. STAGED/ACTIVE before DB is not command success and is not product-addressable. `GmailMailboxCommandService` validates proof signature/expiry and atomically writes the exact DB-03 flow/account/scope/handle/version/key/generation tuple, ACTIVE mailbox, safe audit, and `SUCCEEDED` 303 result. Success cannot precede ACTIVE. Post-commit bind marking is idempotent metadata repair; crash after DB replays the stored redirect.

Crash before exchange resumes and exchanges once. Crash after exchange with no STAGED object performs three strong reads then stores a `SUCCEEDED` command result with typed `outcome=FAILURE`, reason `OAUTH_EXCHANGE_NOT_DURABLE`, and fixed `oauth_restart_required`, and never exchanges again. Crash after STAGED or ACTIVE resumes without exchange. Clean dependency exhaustion while a resumable object exists leaves command `IN_PROGRESS` and returns safe 503 `DEPENDENCY_UNAVAILABLE`/`Retry-After`; it never converts resumable state into false failure.

`OAuthCredentialGarbageCollector` may CAS an orphan to `GC_CLAIMED` only after 24 hours, no handler/bind lease, and one repeatable-read DB snapshot proving no exact mailbox and no matching `IN_PROGRESS` command; it rechecks before revoke/delete. GC and callback have one CAS winner. A stuck resumable IN_PROGRESS saga is never deleted by age; typed `RepairIncident(ABORT_OAUTH_SAGA)` first proves no lease/mailbox, stores the fixed SUCCEEDED failure-outcome result, and closes the flow. Any DB/secret tuple mismatch makes `GmailCredentialConsistencyService` deny token access, disable mailbox/controls, record safe incident/audit, and require authenticated repair or fresh authorization. This exception adds no credential product table and never admits query secrets, token material, or provider text to PostgreSQL/logs.

API route-to-command mapping is one-to-one with BACKEND-02 operation IDs. Workflow step commands use key `workflow:{workflow_run_id}:step:{step_name}:v{step_version}` and actor type `WORKFLOW`; they can request only registered transitions for their frozen run. Provider observations enter provider capture services with actor type `PROVIDER`; they cannot invoke arbitrary commands. Agents never appear as command actors.

### Controls, retries, and recovery authority

`DisableSystemControl` accepts exactly two internal actor arms. `OPERATOR` requires the active authenticated operator and is the only arm exposed by BACKEND-02. `SYSTEM` is internal-only, requires one closed actor ID from DB-01 plus exact canonical reason/evidence, may only change `true -> false` (or replay the same false result), and never fabricates an operator UUID. Suppression, Gmail ambiguity, telemetry blindness, backup witness, credential consistency, and send-authority, calendar-authority and strategy-deterioration guards invoke that system arm through `ControlCommandService` in the same fail-closed unit of work or before further dequeue. Both arms commit row/event/audit/idempotent result/outbox before worker signals. `EnableSystemControl` rejects every non-operator actor; `PRODUCT_OUTREACH` additionally requires verified retained M1 and M6 gate IDs/hashes, no open blocking incident/unresolved ambiguity, current compliance/security evidence, and explicit reason/evidence. Success changes a control only; it creates no campaign/member/message/intent/booking/queue/reservation. `EnableSystemControl(TEST_INBOX_SENDING)` requires the M6 owned-alias manifest and cannot alter product control.

Pause/cancel requested versus acknowledged states follow WF-06 exactly. `RetryExperimentStage` creates a new workflow run; it never resumes a terminal run. `RetrySend` is internal to `SendRecoveryService` and requires either an explicit provider rejection or signed local pre-write proof that request bytes never left the process, plus all ARCH-03 guards; timeout, age, negative search/history, conflict, and operator assertion are ineligible. `ReconcileSendAttempt` may only read the immutable authorized mailbox. `RepairIncident` accepts a registered repair kind, expected before hash, desired after hash/evidence; before command claim it byte-matches the exact `incident.catalog.v1` trigger/alert/runbook route and validates resolution applicability plus repair/runbook applicability. Residual-risk acceptance rejects for HIGH/CRITICAL and every OBS-05 non-waivable trigger. PostgreSQL repeats route/resolution enforcement; the command records `repair_actions` and executes an existing typed transition. Arbitrary field patch and SQL strings are rejected.


### Errors, verification and recovery

Use BACKEND-02 typed HTTP errors and BACKEND-03 bounded denial reasons. IDENTITY/CONTENT/GENERATION mismatches fail before credential access. Routine artifact acceptance cannot be replaced by a per-artifact operator gate; explicit protected legal/configuration decisions keep their existing qualified authority.

Retain strict command schemas/registry hashes, same-key/same-hash and changed-hash replay, two-consumer races, scope splice/expiry/generation and exception no-bypass cases, provider and runtime request/ack crash boundaries, OAuth bind/GC proof, cold-stop/suppression cursor atomicity, call/slot confirmation and checkpoint/strategy CAS. No claim of exactly-once network behavior is permitted. Audit/logs contain safe command/actor/state/reasons/IDs/hash/generation, never plaintext content, credentials or raw sensitive facts.

## Ordered implementation tasks

<!-- roadmap-task id=BACKEND-05-T01 milestone=M6 depends_on=DB-05-T02,DB-01-T01,DB-01-T02 mode=parallel locks=backend-domain -->
- [ ] **Implement command envelope/registry/executor —** Input: DB-01/05 hashes/tables and registry above. Operation: encode strict commands, actor rules, scopes, atomic replay/result semantics, and safe errors. Output: command bus. Test evidence: schema/registry/concurrency/failure-injection matrix. Failure behavior: unregistered/invalid command never calls service.
<!-- roadmap-task id=BACKEND-05-T02 milestone=M6 depends_on=BACKEND-05-T01,SEC-02-T04,SEC-02-T05,SEC-03-T01,DB-03-T04,PROVIDER-01-T02 mode=serial locks=backend-domain,security-runtime -->
- [ ] **Implement authenticated exception inspection and receipt service —** Input: SEC-02 session/reauthentication, SEC-03 signing/encryption, DB-03 content and PROVIDER-01 deterministic MIME construction. Operation: implement SensitivePreviewService for explicit exception/incident inspection with five-minute step-up, exact scope hash, opaque sign-then-encrypt receipt and no-store response; no normal action depends on this read. Output: purpose-scoped sensitive inspection interface. Test evidence: cross-session/recipient/content/stale/replay/cache/telemetry negatives. Failure behavior: expose no sensitive content and grant no effect authority.
<!-- roadmap-task id=BACKEND-05-T03 milestone=M6 depends_on=BACKEND-05-T02,BACKEND-03-T03 mode=parallel locks=backend-domain -->
- [ ] **Implement ActionAuthorizationService —** Input: ActionAuthorityScopeV1, accepted offer/strategy/activation/member/thread/evidence, deterministic commercial result, current policy facts and generations. Operation: materialize immutable scope/hash, evaluate ACTION_CREATION, authorize/deny, expire/revoke, and consume exactly once inside the owning intent/action transaction. Output: implemented ActionAuthorizationService with immutable authority and append-only consumption receipts; gateways still rebuild fresh facts. Test evidence: normal in-envelope action without operator preview, all one-field scope/expiry/generation splices, consumption race, commercial denial and stale reply tests. Failure behavior: no authorization/intent/provider call; append exception evidence.
<!-- roadmap-task id=BACKEND-05-T04 milestone=M6 depends_on=BACKEND-05-T03 mode=parallel locks=backend-domain,workflow-runtime -->
- [ ] **Implement stage/control/runtime and exception handlers —** Input: authenticated/API or frozen workflow commands. Operation: commit product intent first, signal runtime after commit, record acknowledgement/failure visibly. Output: implemented versioned authenticated stage/control/runtime command-handler interfaces plus canonical control states/events. Test evidence: kill/restart at request/signal/ack boundaries. Failure behavior: keep controls closed/request pending.
<!-- roadmap-task id=BACKEND-05-T05 milestone=M6 depends_on=BACKEND-05-T04,DB-03-T03 mode=parallel locks=backend-domain -->
- [ ] **Implement all-current-eligible campaign snapshot creation —** Input: expected experiment/offer/query/hash/count/caps, exact stage/strategy activation and prior checkpoint only. Operation: lock, recompute, compare, insert every sorted eligible member in the selected registered cohort, recount/rehash, and commit atomically. Output: one immutable cohort membership snapshot. Test evidence: zero/overflow/drift/subset/duplicate/cross-experiment/concurrent-qualification negatives and exact-set positive. Failure behavior: no campaign/member row.
<!-- roadmap-task id=BACKEND-05-T06 milestone=M6 depends_on=BACKEND-05-T05,SEC-05-T02 mode=parallel locks=backend-domain -->
- [ ] **Implement send/recovery/control enable gates —** Input: frozen M1/M6 evidence-verification and separated-control decision contracts, intent/attempt/control/incident fixtures, and existing suppression authority. Operation: route only exact owners and enforce separate test/product authority; implement against signed accepted/rejected fixtures now and require fresh real gate records at each later live invocation, never require its own completed M6 gate to build the service. Output: implemented versioned send/recovery/control-enable command-gate interfaces plus safe queued/reconcile/retry/control result. Test evidence: missing/stale gate, ambiguity, suppression, and repair matrices. Failure behavior: no send/enable.
<!-- roadmap-task id=BACKEND-05-T07 milestone=M7 depends_on=BACKEND-05-T06,SEC-03-T01,PROVIDER-01-T03,BACKEND-02-T03,BACKEND-02-T05 mode=serial locks=openapi-contract,milestone-gate -->
- [ ] **Prove OAuth saga, callback, and operator workflows —** Input: versioned flow/credential objects, ACTIVE proofs, command/OpenAPI fixtures; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: execute six kill points, exact replay, bind/GC CAS race, mismatch disable, and redaction scans; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: M6/M7 saga evidence with no success-before-ACTIVE. Test evidence: executable state-machine, browser replay, DB proof tuple, TTL/GC, incident fixtures. Failure behavior: release blocked.

## Acceptance and retained evidence

Retain command/actor/authority registries, exact replay and scope/generation/consumption tests, complete OAuth proof/GC fixtures, exception no-bypass evidence and gateway boundary traces. All normal in-envelope actions must pass without per-message operator preview; all protected legal, incident, kill/recovery and strategy controls preserve their authenticated deterministic guards. No unresolved provider action may be retried by an operator command.
