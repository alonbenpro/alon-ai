# Module Boundaries and Dependency Rules

**Document ID:** ARCH-02
**Status:** Planned target with current exceptions declared
**Milestone:** M2, M3, M6, M7 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `ARCH-02-T01 -> ARCH-02-T02 -> ARCH-02-T03 -> ARCH-02-T04 -> ARCH-02-T05`; cross-document task Inputs `ARCH-02-T01 <- ARCH-03-T01,DB-01-T02; ARCH-02-T02 <- ARCH-03-T01; ARCH-02-T03 <- PROVIDER-03-T04,PROVIDER-04-T04,PROVIDER-05-T04,PROVIDER-06-T03,TEST-04-T01; ARCH-02-T04 <- DB-01-T05,DB-05-T05,PROVIDER-01-T02,PROVIDER-01-T04; ARCH-02-T05 <- BACKEND-02-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [ARCH-01 target architecture](01-target-system-architecture.md) and ADR 0001
**Outputs:** Package responsibilities, allowed imports, ports, transaction ownership, and boundary tests
**Unlocks:** M2 schema/repositories, M3 agents/providers, M4 application services
**Risk:** High
**Complexity:** L

## Outcome and timing

The modular monolith stays cheap only if dependencies point toward stable business contracts and framework/provider details remain replaceable. M0 names the target; M2 enforces it when product modules first exist. Directory shape is not an implementation sequence.

## Current repository state and debt

Current boundaries are intentionally thin. `api/` owns health routes and composition, `db/` owns engine/readiness, and `worker/` owns safe startup. `agents/` and `workflows/` contain only package markers. `policies/sending.py` defines an async protocol. `providers/gmail.py` defines Gmail-flavored value types and a protocol but no adapter. `domain/sending.py` contains `SendGateway` and imports both provider and policy modules.

That last direction is a known foundation shortcut, not the target: a domain module currently depends on outward integration/policy namespaces. M2 moves neutral value contracts inward; M6 places the orchestrating gateway under `application/`. No refactor is justified before the relevant vertical milestone.

## Target package map

| Package | Responsibility | Allowed first-party dependencies | Forbidden dependencies |
| --- | --- | --- | --- |
| `alon_ai.domain` | IDs, immutable values, aggregates, invariants, transition decisions, domain event intents | other `domain` modules | FastAPI, SQLAlchemy, DBOS/engine SDK, provider SDKs, `api`, `worker`, `persistence`, `agents` |
| `alon_ai.application` | command/query handlers, units of work, ports, orchestration, `SendGateway`, `BookingGateway`, action authorization, checkpoint and strategy services | `domain`, narrow `policies`, abstract ports | FastAPI request/response types, concrete adapters, engine SDK in business handlers |
| `alon_ai.policies` | pure/versioned rule composition, `PolicyDecision`, `CommercialPolicyEngine` and authoritative commercial calculations | `domain`, read-only policy fact types | provider calls, sessions, workflow SDK, agent output as authority |
| `alon_ai.workflows` | DBOS finite durable coordination, queues, schedules, timers, retries, and runtime adapter | `application` commands/ports, `domain` IDs/artifact refs | concrete provider adapter, FastAPI, SQLAlchemy model mutation, direct Gmail/calendar writes |
| `alon_ai.agents` | Pydantic AI typed artifact schemas/runners, model/tool ports, provenance, cost, and evaluation hooks | artifact contracts, abstract evidence-provider ports | application commands that mutate state, Gmail/calendar write ports, sessions, workflow control |
| `alon_ai.providers` | concrete external adapters and provider error mapping | `domain`/application port DTOs, provider libraries | cross-provider business orchestration, state transitions, policy decisions |
| `alon_ai.persistence` | SQLAlchemy mappings, repositories, unit of work, outbox/audit/idempotency implementation | `domain`, application persistence ports | FastAPI, frontend, agents, provider business calls |
| `alon_ai.api` | auth/context, validation, OpenAPI routes, error/status mapping, composition | `application`, query DTOs, config/composition | direct SQLAlchemy queries in routes, providers, agents, workflow SDK business logic |
| `alon_ai.worker` | process lifecycle and composition root | `workflows`, `application`, config/composition | duplicate business logic, HTTP route concerns |
| `alon_ai.observability` | safe log/metric/trace adapters and correlation | neutral telemetry contracts | product state ownership, secrets/full message copies |
| `alon_ai.config` | validated environment configuration | Pydantic settings | product state or mutable runtime controls |

External package imports are additionally constrained: FastAPI only in `api/`; DBOS SDK only in workflow adapter/composition; Temporal SDK only after a disqualifying M1 decision and only in its replacement adapter/composition; Pydantic AI only in agent runtime/composition; SQLAlchemy only in `persistence/`, migration code, and existing `db/` health bootstrap; Gmail SDK only in the Gmail adapter; calendar SDK only in the calendar adapter; model/search/extraction SDKs only in corresponding adapters. LangChain, LangGraph, Restate, and Prefect are not initial dependencies.

## Canonical ports and ownership

These are planned interfaces; their detailed fields arrive in the named milestones.

| Port | Consumer | Implementer | Rule |
| --- | --- | --- | --- |
| `UnitOfWork` | application handlers, workflow command handlers | PostgreSQL persistence | one command transaction owns aggregate change, event/audit append, idempotency result, and outbox enqueue |
| `ExperimentRepository` | application | PostgreSQL persistence | aggregate-version optimistic concurrency required |
| `ArtifactRepository` | application/agents via handler | PostgreSQL persistence | agents return artifacts; handler persists them |
| `EvidenceSearchProvider` | agent runner | search adapter/fixture | returns captured provenance, never business authority |
| `PageExtractionProvider` | agent runner | extraction adapter/fixture | bounded content/type/size/time and safe fetch policy |
| `ModelProvider` | agent runner | model adapter/fixture | typed response, usage, model/version, timeout/error taxonomy |
| `GmailReadPort` | Gmail history/thread sync and Sent reconciliation services | Gmail read adapter/fixture | bounded observations and cursors; no send method |
| `GmailWritePort` | `application.sending.SendGateway` only | Gmail write adapter/fixture | send primitive, provider attempt/result evidence; no reads or policy |
| `CalendarReadPort` | bounded availability and booking reconciliation services | calendar read adapter/fixture; Google Calendar first | bounded availability and event observations; no event mutation |
| `CalendarWritePort` | `application.booking.BookingGateway` only | calendar write adapter/fixture; Google Calendar first | idempotent create/reschedule/cancel; explicit notification behavior |
| `LeadDiscoveryProvider` | discovery runner through bounded read tool | approved source adapter/fixture | source-specific scope, query/filter version, provenance, identity facts/unknowns; no unrestricted crawling |
| `WorkflowRuntime` | application composition and operator commands | DBOS adapter; Temporal adapter is mandatory only after a disqualifying M1 failure | finite start/pause/resume/cancel/status; no business rules |
| `Clock` / `IdGenerator` | domain/application | production and deterministic test adapters | removes hidden time/randomness from tests |
| `Telemetry` | application/workflows/adapters | observability adapter | safe structured fields only |

The foundation `GmailProvider` is split into independent read/write capabilities before product composition. Only `SendGateway` receives `GmailWritePort`; only `BookingGateway` receives `CalendarWritePort`. Read adapters cannot reveal/write credentials or return a client with hidden mutation methods. Agents, workflows, API routes, frontend, and generic provider wrappers cannot receive either write capability. Agent read tools expose minimized business evidence, never complete mailbox/calendar clients.

| Deterministic owner | Inputs | Output and authority boundary |
| --- | --- | --- |
| `IdeaBriefMaterializer` | authenticated user idea/provenance | validated `IdeaBrief` with bypass origin; does not skip market research |
| `QualificationService` | discovery/final-qualification proposals, offer filters, evidence and current admission facts | phased `QualificationDecision`; agent cannot override identity/suppression/legal/capacity |
| `CommercialPolicyEngine` | accepted `OfferPackage`, proposal, cost/FX/tax/fee/rounding versions and `STATED\|INFERRED\|UNKNOWN` budget evidence | pure `NegotiationDecision`; cannot mutate package or call providers |
| `ActionAuthorizationService` | exact action/content, offer, strategy/activation, campaign/cohort/member, recipient/thread, policy/commercial facts, expiry, generation | immutable `ActionAuthorityScopeV1`; fresh gateway checks still required |
| `BookingGateway` | accepted `BookingIntent`, explicit confirmation, fresh availability/identity/context/control facts | sole event-write intent/attempt/result protocol and reconciliation |
| `CheckpointEvaluationService` | frozen completed-stage evidence, agent recommendation and registered rules | `CheckpointEvidenceBundle`, exact checkpoint result, deterministic next-stage eligibility |
| `StrategyActivationService` | `AgentLearningProposal`, offline/holdout/transfer evidence, immutable rules, checkpoint/control state | promoted `GlobalStrategyPackage`, boundary-only `StrategyActivation`, stored-rule rollback; no historical mutation |

The registry's supervising responsibility and its deterministic materializer may differ: a proposal is not authority. The runtime calls the writer again after accepted reply objectives; this bounded runtime loop does not create a cyclic implementation dependency. Shared evaluation/versioning infrastructure precedes all specialist promotion.

## Transaction and concurrency rules

1. API and workflow handlers call one application command with one command idempotency key.
2. The application unit of work locks or checks the aggregate version, applies a valid transition, appends domain and audit events, records the command result, and enqueues durable follow-up in one PostgreSQL transaction.
3. External network calls never run while holding a long database transaction.
4. Side-effect intent is committed before a provider call. Provider outcome is committed in a second transaction under the same idempotency/correlation identity.
5. A crash between those transactions creates an ambiguous/reconcilable state, not permission to retry.
6. Projection lag never authorizes an action; command handlers read authoritative state.
7. Retry classification belongs to adapter/application error taxonomy, while the durable engine schedules allowed retries.
8. Reply ingestion atomically records observation, stops cold admission, invalidates stale response/send authority, and advances its cursor. Durable suppression requires the applicable terminal signal, not merely any reply.
9. Cohort admission, checkpoint closure, strategy activation, rollback and action generation use transactional compare-and-swap/locks. A running cohort cannot change its offer/strategy/qualification/causal variables/evidence definition. If deterioration requires rollback, pause affected future actions and close the checkpoint before activation.
10. Calendar mutations serialize under the `calendar-side-effects` resource lock with idempotency and fresh availability/identity/confirmation checks. Duplicate callbacks and ambiguous writes reconcile before retries; cancellation/rescheduling cannot bypass the writer.

## API and frontend boundary

FastAPI request models map into application commands. Routes contain no SQL text, provider client, agent prompt, policy expression, or workflow state mutation. HTTP errors are stable mappings from typed application failures. Mutations accept `Idempotency-Key` or an equivalent typed command key and return authoritative command/state identifiers.

Next.js uses `frontend/openapi.json` and `frontend/src/lib/api/schema.d.ts`, generated from FastAPI. Server or client components may shape display data but do not reimplement eligibility, pricing, suppression, state transitions, or decision rules. A dashboard action is pending until the authoritative response/event confirms it.

## Workflow and agent boundary

Workflows coordinate finite application commands and wait on durable timers/events. They store stable IDs and artifact references, not live SDK clients or opaque model objects. Every run has an explicit terminal outcome and bounded retry/cost policy.

Agents consume typed input snapshots and injected read-only tools. They return one `AgentArtifactEnvelope[T]` containing artifact schema/version, provenance, confidence/abstention, usage/cost, and prompt/model/tool versions, immutable input snapshot ID/hash, output hash, producer strategy version, and governing `GlobalStrategyPackage`/`StrategyActivation`. Each agent has its own input snapshot; workflow lineage does not force all hashes equal. Deterministic application code validates, stores, and decides whether the artifact permits a transition. Agent exception text is not a domain decision.

## Scope and non-goals

In scope: dependency direction, ports, composition, transaction ownership, concurrency, generated contract, and test enforcement. Non-goals: splitting deployable services, generic dependency-injection frameworks, repository-per-table patterns, event sourcing every read, a shared enterprise message bus, or abstraction without a current/tested second implementation or critical safety seam.

## Exact file migration plan

At M2, introduce `backend/src/alon_ai/application/`, `domain/experiments.py`, `domain/events.py`, `persistence/`, and import-rule tests. Neutral send DTOs move from `providers/gmail.py` to `domain/messaging.py` or an application port module. At M6, move `SendGateway` orchestration from `domain/sending.py` to `application/sending.py`; `providers/gmail.py` implements separated read/write ports. Add `application/booking.py`, `application/action_authorization.py`, `application/checkpoints.py`, `application/strategy_activation.py`, and pure `policies/commercial.py`; a calendar adapter translates provider-neutral contracts. Compatibility re-exports may exist for one milestone only and must emit no alternate authority path.

Existing `db/engine.py` may remain the low-level engine bootstrap until persistence composition absorbs it. Generated frontend contracts remain at their current paths.

## Ordered implementation tasks

<!-- roadmap-task id=ARCH-02-T01 milestone=M2 depends_on=ARCH-03-T01,DB-01-T02 mode=parallel locks=architecture-contracts,backend-domain -->
- [ ] **Create inward contracts at M2 —** Input: ARCH-03 names and M2 schema. Operation: define domain values/events and application persistence/workflow/provider ports without framework imports. Output: stable interfaces. Test evidence: type checks and forbidden-import scan. Failure behavior: block concrete adapters.
<!-- roadmap-task id=ARCH-02-T02 milestone=M2 depends_on=ARCH-02-T01,ARCH-03-T01 mode=parallel locks=architecture-contracts,database-schema,backend-domain -->
- [ ] **Implement PostgreSQL unit of work —** Input: domain aggregates, events, idempotent command envelope. Operation: atomically persist state, version, audit/domain events, command result, and outbox item. Output: M2 transaction boundary. Test evidence: real-PostgreSQL rollback/concurrency/replay tests. Failure behavior: reject command with typed conflict/unavailable error.
<!-- roadmap-task id=ARCH-02-T03 milestone=M3 depends_on=ARCH-02-T02,PROVIDER-03-T04,PROVIDER-04-T04,PROVIDER-05-T04,PROVIDER-06-T03,TEST-04-T01 mode=parallel locks=architecture-contracts,provider-contracts -->
- [ ] **Wrap every provider-neutral recorded path at M3 —** Input: the model, search, page, enrichment, approved discovery, Gmail read/write, and calendar read/write ports plus deterministic recorded fixtures and the Gmail simulator. Operation: implement translation, timeout, error taxonomy, cost/provenance capture, and replaceable composition against recorded paths; live provider activation remains in the provider-owned later tasks. Output: replaceable M3 provider adapter boundaries with no live authority. Test evidence: each contract suite passes against its signed fixture/simulator and a fake replacement adapter. Failure behavior: no provider-specific object crosses a port and every live adapter remains disabled.
<!-- roadmap-task id=ARCH-02-T04 milestone=M6 depends_on=ARCH-02-T03,DB-01-T05,DB-05-T05,PROVIDER-01-T02,PROVIDER-01-T04 mode=serial locks=architecture-contracts,provider-contracts,gmail-side-effects,calendar-side-effects,backend-domain,security-runtime -->
- [ ] **Enforce gateway orchestration boundaries at M6 —** Input: current contract, persistence, policies, separate Gmail/calendar read/write ports. Operation: define and enforce import/port authority constraints and forbidden-call rules for the guarded Gmail/calendar paths against pure contract fixtures; BACKEND-04 alone implements product send transactions; backend booking services own calendar transactions and live integration is proven later. Output: enforceable guarded-path architecture/port contract with no duplicate product transaction writer. Test evidence: import graph plus mock and isolated inbox/calendar call-path proof. Failure behavior: keep outreach disabled.
<!-- roadmap-task id=ARCH-02-T05 milestone=M7 depends_on=ARCH-02-T04,BACKEND-02-T05 mode=serial locks=architecture-contracts,openapi-contract,frontend-client -->
- [ ] **Enforce frontend/API boundary at M7 —** Input: OpenAPI and route needs. Operation: add FastAPI contracts first, regenerate clients, and implement UI against them. Output: no invented endpoint or business rule. Test evidence: generation drift, contract, and E2E tests. Failure behavior: remove UI action until backend contract exists.

## Test strategy

- **Static `test_domain_has_no_outward_imports`:** inspect import graph for the table above.
- **Static `test_agents_cannot_import_provider_write_capabilities`:** direct and transitive forbidden imports fail CI.
- **Static `test_fastapi_and_sqlalchemy_are_confined`:** framework imports stay in allowed modules.
- **Integration `test_command_commit_is_atomic`:** injected failure at each write rolls back all command effects.
- **Concurrency `test_aggregate_version_rejects_lost_update`:** simultaneous commands cannot silently overwrite.
- **Contract `test_all_gmail_sends_pass_through_gateway`:** adapter send has one production caller.
- **Contract `test_all_calendar_writes_pass_through_booking_gateway`:** create/reschedule/cancel each have one production caller; read ports lack write methods.
- **Contract `test_commercial_and_checkpoint_strategy_services_are_deterministic`:** offers, budgets, promotion evidence and cohort activation cannot be overridden by model output.
- **Contract `test_frontend_schema_is_generated_from_openapi`:** generated artifacts match committed output.

## Security, privacy, compliance, idempotency, observability, and cost

Ports expose least authority: read tools cannot mutate, Gmail credentials cannot cross composition, and query DTOs minimize personal data. Idempotency is enforced inside the transaction boundary, not left to HTTP/workflow retries. Telemetry records correlation, type, version, status, duration, and safe IDs. Provider results include usage/cost and provenance. Compliance facts are deterministic inputs, not agent prose.

## Failure, rollback, and recovery

If a boundary rule blocks legitimate work, amend this document and the import test with a narrow justification; do not add broad ignore lists. Adapter rollback selects the prior implementation at composition. Command conflicts are retried only after reloading authoritative state. A partial refactor keeps a temporary compatibility export but only one production implementation/call path.

## Acceptance and retained evidence

- [ ] Every package has one responsibility and explicit allowed dependencies.
- [ ] Domain, agents, workflows, API, and frontend cannot bypass deterministic application authority.
- [ ] Transactions and external calls cannot leave an unreconcilable silent gap.
- [ ] Current dependency debt and its vertical repair point are explicit.

Retain import graph reports, interface/type checks, real-PostgreSQL transaction tests, provider contract results, OpenAPI drift checks, and the call-path proof. This boundary contract unlocks [ARCH-03](03-domain-events-and-state-machines.md) and the M2 implementation documents.
