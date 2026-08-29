# Deterministic Domain and Application Services

**Document ID:** BACKEND-01
**Status:** Planned M2-M6 application layer; only foundation send/policy protocols exist today
**Milestone:** M2 core, M4-M5 no-send services, M6 controlled side effects
**Owner:** Solo operator
**Prerequisites:** [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), DB-01 through DB-06, and accepted runtime/provider contracts
**Outputs:** Exact service ownership, deterministic command/query boundaries, unit-of-work rules, and complete external-side-effect trace
**Unlocks:** [BACKEND-02 API](02-api-contracts.md), policy, SendGateway, commands/approvals, and reports
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Business truth is produced by deterministic Python services over PostgreSQL, never by FastAPI routes, Next.js, DBOS/Temporal, agents, or provider adapters. A command verifies immutable inputs and expected versions, calls a pure transition/policy function, and commits the aggregate/event/audit/idempotency/outbox result atomically. External calls occur only after committed intent/reservation and are reconciled afterward.

## Current repository state

Implemented today: FastAPI health composition, PostgreSQL health, request logging, idle worker, SQLAlchemy/Alembic wiring, minimal `SendPolicy`, `GmailProvider`, and guarded `SendGateway`. Missing: product domain models/tables, unit of work, services below, commands, policies, artifacts, workflows, providers, authentication, reports, or product endpoints. Current shortcuts in `domain/sending.py` are not the target dependency direction.

## Scope and non-goals

In scope: pure invariants/transitions, application service ownership, optimistic concurrency, exact table/event writes, provider intent/result handoffs, replay, cancellation, audit/cost, and deterministic clocks/IDs. Non-goals: a generic CRUD/repository layer exposed to routes, ORM entities crossing boundaries, provider calls inside transactions, event sourcing, direct workflow writes, model-authored commands, duplicate business logic in Next.js, or service aliases with overlapping ownership.

## Exact planned implementation surfaces

Create `domain/identifiers.py`, `domain/events.py`, `domain/experiments.py`, `domain/leads.py`, `domain/artifacts.py`, `domain/messaging.py`, `domain/approvals.py`, `domain/controls.py`, `domain/offers.py`, `domain/metrics.py`; `application/uow.py`, `application/commands.py`, `application/experiments.py`, `application/artifacts.py`, `application/leads.py`, `application/campaigns.py`, `application/approvals.py`, `application/controls.py`, `application/recovery.py`, `application/gmail_mailboxes.py`, `application/gmail_sync.py`, and `application/reporting.py`; plus persistence adapters named by DB-01 through DB-05. Domain imports only standard library/domain values. Application imports domain plus inward ports. Persistence/providers/runtime/FastAPI import inward, never the reverse.

### Exact write owners and responsibilities

The table owners below are canonical; no route/workflow/provider/agent writes their tables directly.

| Service | Exclusive authoritative writes / deterministic responsibility |
| --- | --- |
| `OperatorSessionService` | FastAPI-owned Google OIDC flow/session issue, rotation, expiry, revocation, logout, configured-subject authentication; no product-table or Gmail authority |
| `AuthenticationCommandService` | `operators`; configured authenticated-subject lifecycle only |
| `ExperimentCommandService` | `experiments`, `experiment_decisions`; ARCH-03 transitions/decision bundle |
| `ExperimentBriefCommandService` | immutable `experiment_briefs`; scope versions |
| `IdeaMaterializationService`, `OfferMaterializationService` | `ideas`, `offer_hypotheses` after accepted artifact gates |
| `MetricDefinitionCommandService`, `MetricObservationService`, `MetricSnapshotService` | their exact DB-02 metric tables and reproducible cutoffs |
| `WorkflowRunProjectionService` | application `workflow_runs`; runtime only reports observations |
| `ControlCommandService`, `IncidentCommandService` | `system_controls`, `incidents` |
| `BudgetService` | `budget_accounts`, `budget_reservations`; serial admission/release/reconcile state |
| `BusinessIdentityService` | `businesses`; identity insert/conflict quarantine, never auto-merge |
| `LeadCommandService`, `LeadQualificationService` | `leads`, `lead_assessments`; exact ARCH-03 lead transitions |
| `GmailOAuthSagaService`, `OAuthCredentialGarbageCollector` | external versioned flow/credential objects; idempotent STAGE/ACTIVATE/bind leases, safe orphan GC; no product-table writes |
| `GmailMailboxCommandService`, `GmailCredentialConsistencyService` | `gmail_mailboxes`; exact ACTIVE proof tuple commit, mismatch disable/incident; no secret payload writes |
| `CampaignCommandService`, `CampaignAdmissionService` | immutable `campaigns` versions and `campaign_members`; exact `ReadyCampaign` DRAFT -> READY owner |
| `MessageCommandService` | `outreach_messages` except SendGateway/Recovery-owned documented send transitions |
| `ApprovalCommandService` | `approvals`; exact campaign-member approval basis, eligibility-decision binding, lifecycle, and consumption; never final SEND authority |
| `SuppressionCommandService`, `SuppressionQueryService`, `RecipientSignalSuppressionService` | versioned `suppression_entries` create/fail-closed deactivate; uncached safe reads; observed signal coordinator may invoke only `SuppressionCommandService.record_observed_signal` inside the exact Gmail/public-token transaction; suppression always overrides eligibility/approval |
| `PolicyEvaluationService` | append-only `policy_decisions`; separate `APPROVAL_ELIGIBILITY` and fresh final `SEND` compositions with shared basis/independent facts hashes |
| application `SendGateway` | eligibility-bound `send_intents`; fresh-SEND pre-call `send_attempts`; last-mile `QUEUED -> SUPPRESSED`/intent cancellation; documented transitions under BACKEND-04 |
| `SendRateReservationService` | `send_rate_reservations`; unique mailbox/window slot and one active lease under gateway/recovery transactions |
| `SendRecoveryService` | disjoint retry/reconciliation transitions on `send_attempts`/messages; never initial provider call |
| `GmailResultCaptureService`, `GmailObservationService`, `GmailReplySyncService`, `GmailHistorySyncService` | respectively `provider_results`, `provider_observations`, `replies`, `gmail_history_cursors` |
| `AgentRunRecordingService`, `ArtifactCommandService`, `EvidenceIngestService` | respectively `agent_runs`, `artifacts(PRODUCED)` plus event, and `evidence_items` |
| `ArtifactValidationService`, `ArtifactAcceptanceService`, `ArtifactEvidenceQueryService` | links/validations plus validated/rejected event; exact version/hash accept/reject plus events; allowlisted artifact/evidence/evaluation reads |
| `EvaluationSuiteCommandService`, `EvaluationExecutionService` | `evaluation_cases`; `evaluation_results` while delegating all `agent_runs` writes |
| application `UnitOfWork`, `AuditRecorder`, `IdempotentCommandExecutor` | `domain_events`/`outbox_messages`; `audit_events`; `command_idempotency` |
| each named internal consumer | business writes plus `outbox_deliveries` in one PostgreSQL transaction |
| `ProviderCostReconciliationService`, `RecoveryCommandService`, `RetentionCommandService` | `cost_entries`; `repair_actions`; every policy-versioned purge/redaction |

When two services touch one aggregate, their legal transitions are disjoint and encoded in one shared domain transition table; they do not become co-writers of arbitrary columns. Provider adapters return observations only. Agents may request only a `PRODUCED` artifact through `ArtifactCommandService`; they are never DB-05 actors.

### Command, digest, transaction, and concurrency contract

After `OperatorSessionService` verifies the opaque cookie, configured subject, expiry, Origin, fetch metadata, and CSRF intent, every application command is a strict frozen `CommandEnvelopeV1` with `command_type`, `command_scope`, idempotency key, authenticated actor (or operator/flow binding verified from signed OAuth state for `CompleteGmailAuthorization`), expected aggregate version where applicable, correlation/causation UUIDv4, text `request_schema_version`, JSON payload, and DB-01 lowercase SHA-256 of RFC 8785 UTF-8 `{"schema_version":version,"payload":payload}`. IDs and UTC clock are injected; no service reads global time/randomness.

The exact aggregate transaction is: begin; claim `(command_scope,idempotency_key)`; verify request bytes/schema against prior claim; lock/load or optimistic-version-check; load all named authority rows; call pure transition/policy; update the sole-writer row; insert the specific ARCH-03 event and aggregate `*.state_changed.v1` where defined; insert safe audit; insert outbox; store the complete result envelope/hash; commit. A same-key/same-hash replay returns the stored status/body without another version/event. Same key/different hash is `IDEMPOTENCY_HASH_CONFLICT`. Version loss is `VERSION_CONFLICT`. Denial records safe audit/policy evidence but no aggregate mutation unless the canonical transition itself is denial/suppression.

External calls and runtime signals never occur in that transaction. The OAuth callback is an explicit pre-transaction saga, not an exception to this rule: `GmailOAuthSagaService` exchanges once, makes the external credential ACTIVE, and supplies signed short-lived `ActiveCredentialProofV1`; the PostgreSQL transaction validates only that proof and copies its exact safe tuple. A 30-second secret-store bind lease plus 5-second database timeout prevents GC during commit. Only after ACTIVE proof may `GmailMailboxCommandService` atomically insert ACTIVE mailbox and SUCCEEDED command result. Outbox internal consumers atomically commit their business writes and `outbox_deliveries`; they cannot issue external effects. PostgreSQL named unique/composite FKs and immutable triggers from DB-01/03/05/06 are last-line enforcement, not optional application validation.

### Deterministic service flow by milestone

| Flow | Input -> deterministic operation -> output | Exact state/event authority |
| --- | --- | --- |
| experiment stage | approved brief/gates/version -> start/finish/fail finite run -> stored run/result/aggregate bundle | WF-02 states; `workflow.run_*`, `experiment.*` exact `.v1` events |
| artifact | verified run/config/provider ledger -> `PRODUCED` -> later validate/link -> later accept/materialize | DB-04 owners; `artifact.produced/validated/rejected/accepted/superseded.v1` |
| lead | accepted evidence + identity/criteria -> conflict/research/assessment/suppression -> lead state | `lead.discovered/identity_conflict_detected/evidence_recorded/qualified/disqualified/suppressed.v1` |
| campaign/approval | frozen campaign/member/message/artifact basis -> eligibility without ApprovalRule -> request/approve/deny/revoke -> exact basis only | complete campaign family plus `policy.evaluated.v1` and `approval.requested/decided/revoked.v1`; no send authority |
| Gmail OAuth | claimed command/flow -> one exchange -> idempotent STAGED -> ACTIVE -> signed bind proof -> mailbox+SUCCEEDED transaction -> post-commit bind marker | audit-only OAuth lifecycle; no domain-event alias and no success without exact ACTIVE generation |
| control/recovery | authenticated command + current evidence -> pure control/repair decision -> requested/acknowledged state | WF-06 exact experiment/run/campaign/control/send events |
| decision/report | frozen metrics/evidence/rule + operator -> immutable decision; queries read snapshots/events | `experiment.decision_recorded.v1`; `SCALE` grants no new authority |

### Complete external side-effect trace

For model/search/page/business calls: verified workflow/config/input -> budget reservation -> provider capability request hash/call ID -> cancellation/deadline/rate gate -> external read/model call -> exact Task 3 result and provider ledger -> evidence ingestion where applicable -> `ProviderCostReconciliationService` -> agent deterministic validation -> only then `PRODUCED` artifact and later separate validation/acceptance. Failures cannot transition aggregates merely because a provider returned data.

For Gmail: allowed eligibility decision -> exact campaign/version/`campaign_member_id`/message/mailbox/compliance-evidence approval basis -> operator approval -> eligibility-bound immutable `send_intents` plus stable mailbox idempotency/RFC ID -> queue after commit -> BACKEND-04 fresh final SEND decision over all current compliance/signal facts -> suppression terminal/no-call bundle or atomic consumed `send_rate_reservations` + `send_attempts` commit -> one `SendGateway -> GmailProvider.send` network call -> `GmailResultCaptureService` -> direct `send.provider_accepted.v1`, conclusive `send.failed.v1`, or `send.outcome_ambiguous.v1` -> mailbox-bound PROVIDER-02 reconciliation before retry -> cost/budget reconcile -> history page where ordinary observations commit normally but every reply/unsubscribe/bounce/complaint/soft-limit invokes one `RecipientSignalSuppressionService` transaction that stores observation/reply, suppression, pre-call intent closure/events and cursor together. Public unsubscribe POST enters the same transaction with a stored token result; GET never mutates. Every step carries correlation/causation and safe audit. No agent/workflow/provider chooses a transition.

## Ordered implementation tasks

- [ ] **Implement pure domain values/transitions —** Input: ARCH-03 enums/guards/events and DB constraints. Operation: encode exhaustive pure functions with injected actor/time/IDs and typed denials. Output: deterministic decisions/event intents. Test evidence: exhaustive state/guard/property snapshots. Failure behavior: no mutation intent.
- [ ] **Implement unit of work/idempotent executor —** Input: strict command envelope and expected version. Operation: execute the exact atomic bundle and replay semantics. Output: one committed command result. Test evidence: real-PostgreSQL concurrency/failure injection at every write. Failure behavior: whole transaction rollback or typed replay conflict.
- [ ] **Implement sole-writer services vertically —** Input: M2 schema then each milestone gate. Operation: add only services needed for M2, M4, M5, then M6, preserving owners/table/events. Output: product operations without provider leakage. Test evidence: table-writer/import rules and integration cases. Failure behavior: milestone blocked at missing owner.
- [ ] **Implement side-effect orchestration —** Input: committed intent/reservation and strict provider ports. Operation: call outside transaction, capture result/cost/evidence, and reconcile exact failure semantics. Output: complete audit chain. Test evidence: kill/cancel/provider status matrix. Failure behavior: visible unresolved state; no blind replay.
- [ ] **Prove boundary and current-truth gates —** Input: import/call graph, OpenAPI/workflow/provider composition, repository truth. Operation: assert routes/workflows/agents/providers cannot write or decide outside their ports and planned surfaces are not claimed implemented. Output: architecture evidence. Test evidence: static graph plus integration spies. Failure behavior: release blocked.

## Test strategy

- **Unit `test_every_arch03_transition_has_one_owner_guard_event_and_denial`:** exact catalog.
- **Atomicity `test_command_state_events_audit_idempotency_outbox_commit_together`:** each boundary injected.
- **Concurrency `test_unique_and_composite_constraints_are_final_authority`:** stale/spliced rows fail.
- **Boundary `test_routes_workflows_agents_and_providers_cannot_write_product_tables`:** import/runtime graph.
- **Side effect `test_each_provider_effect_has_intent_result_cost_and_recovery`:** six capabilities plus Gmail.
- **OAuth saga `test_mailbox_success_requires_exact_active_proof_and_each_pre_db_state_resumes_without_reexchange`:** six kill points and GC race.
- **Digest `test_all_command_workflow_provider_results_reproduce_rfc8785_vectors`:** validate before upcast/use.

## Security, privacy, compliance, idempotency, observability, and cost

Authenticated actor and exact authority are explicit. Decrypted sensitive content exists only in bounded provider/application memory, never domain events/logs. Commands/providers use stable hashes/keys; external exactly-once is never claimed. Correlation spans HTTP, command, workflow, agent, provider, cost, Gmail attempt, and repair. Reservations occur before paid/reputation-bearing work; original currency plus ILS reporting evidence is retained. Retention and holds are exactly DB-06.

## Failure, rollback, and operator recovery

Unknown state/event/runtime mapping, impossible composite authority, OAuth DB/secret mismatch, partial-write suspicion, provider-result disagreement, or cost overrun blocks mutation, closes applicable controls, and opens an incident. Roll back code/config, preserve immutable history, compare aggregate/events/provider/runtime, then execute typed `RecoveryCommandService`; direct SQL is forbidden. Restore into an isolated database when invariants cannot be proven.

## Acceptance and retained evidence

- [ ] Every product table has the DB-defined sole writer and every transition/event has one deterministic owner.
- [ ] Commands are byte-hashed, optimistic, idempotent, atomic, and framework/runtime/provider independent.
- [ ] Every external effect traces intent, policy, budget, execution, result/cost/audit, and recovery.
- [ ] Agents/providers/workflows/frontend cannot decide or mutate business truth.
- [ ] Current implemented-versus-planned truth remains explicit.

Retain service/owner registry, import/call graph, transition/event snapshots, PostgreSQL concurrency/atomicity traces, provider side-effect matrices, digest fixtures, safe telemetry/cost/retention evidence, and current-truth scan.

## Dependencies and next deliverable

BACKEND-01 consumes ARCH/DB/WF/AGENT/provider contracts. It unlocks the exact [FastAPI contract](02-api-contracts.md), [policy engine](03-policy-engine.md), [SendGateway](04-send-gateway.md), [command/approval handlers](05-approval-and-command-handling.md), and [reporting services](06-reporting-and-query-services.md).
