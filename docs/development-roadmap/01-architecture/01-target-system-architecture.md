# Target System Architecture

**Document ID:** ARCH-01
**Status:** Planned target; current boundaries called out explicitly
**Milestone:** M1, M2, M3, M5, M7, M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `ARCH-01-T01 -> ARCH-01-T02 -> ARCH-01-T03 -> ARCH-01-T04 -> ARCH-01-T05 -> ARCH-01-T06`; cross-document task Inputs `ARCH-01-T01 <- WF-01-T01,WF-01-T02,WF-01-T03; ARCH-01-T02 <- ARCH-02-T01,ARCH-03-T01; ARCH-01-T03 <- ARCH-02-T01,AGENT-10-T05,DB-04-T05,ARCH-02-T03; ARCH-01-T04 <- WF-03-T05,WF-04-T05,PROVIDER-06-T03,WF-00-T04; ARCH-01-T05 <- BACKEND-03-T03,PROVIDER-01-T03,DB-03-T06,WF-01-T01,TEST-04-T06,BACKEND-02-T05,FRONTEND-03-T05,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-08-T04,FRONTEND-09-T04,FRONTEND-01-T05,FRONTEND-03-T03; ARCH-01-T06 <- INFRA-03-T07,INFRA-04-T06,INFRA-05-T07,OBS-05-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): [master roadmap](../README.md), PRODUCT-01 through PRODUCT-03, ADRs 0001-0003
**Outputs:** Selected Pydantic AI/DBOS topology, component ownership, data/side-effect paths, and production-acceptance gate
**Unlocks:** ARCH-02 dependency rules, ARCH-03 states/events, and M1 DBOS acceptance design
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Alon AI remains a modular monolith: one Python package, separate API and worker processes, one PostgreSQL system of record, replaceable external adapters, and a Next.js operator dashboard that consumes FastAPI's OpenAPI contract. This is the least architecture that can make externally visible work durable and auditable for one operator.

The architecture grows by vertical risk gates. M1 proves the dangerous Gmail recovery primitive with disposable records. M2 creates the first product model. Later milestones add only components needed by the next product gate.

## Current repository state

The current runtime is Next.js -> FastAPI `/health/ready` -> PostgreSQL plus a separate idle Python worker. FastAPI composes settings, request logging, CORS, and database health. The frontend consumes generated OpenAPI types for readiness. The package has empty `agents/` and `workflows/` boundaries, an engine helper in `db/`, and minimal send/policy/provider protocols. Alembic has no product revision.

The intended diagram below is not the current runtime. Pydantic AI and DBOS are selected, and their dependencies are installed, but no agent or workflow invokes them and DBOS is not production-accepted. Gmail settings fields exist but no OAuth flow or Gmail adapter exists. Compose is local foundation topology, not a private production deployment.

## Target topology

```mermaid
flowchart TB
    Operator["One authenticated operator"] --> UI["Next.js dashboard"]
    UI -->|"generated OpenAPI client"| API["FastAPI API process"]
    API --> APP["Application commands and queries"]
    WORKER["Worker process"] --> WF["DBOS finite durable workflows"]
    WF --> APP
    APP --> DOMAIN["Domain models and deterministic transitions"]
    APP --> POLICY["Deterministic policies"]
    APP --> PERSIST["Persistence repositories and unit of work"]
    PERSIST --> PG[("PostgreSQL system of record")]
    APP --> PROVIDERPORTS["Typed provider/tool ports"]
    POLICY --> DOMAIN
    APP --> AGENTS["Pydantic AI typed agents: advisory artifacts only"]
    AGENTS --> READTOOLS["Injected bounded read-only tools"]
    READTOOLS --> PROVIDERPORTS
    PROVIDERPORTS --> MODEL["Model/search/extraction/enrichment adapters"]
    APP --> SEND["SendGateway"]
    SEND --> POLICY
    SEND --> GMAILPORT["GmailProvider port"]
    GMAILPORT --> GMAIL["Gmail API"]
    GMAIL --> RECON["Sent reconciliation and history sync"]
    RECON --> APP
    API --> OBS["Logs, metrics, traces, alerts"]
    WORKER --> OBS
```

## Component ownership

| Component | Owns | Must not own | First needed |
| --- | --- | --- | --- |
| Next.js dashboard | operator rendering, accessible interactions, generated API client, local presentation state | business rules, provider credentials, direct database/Gmail calls, a second backend | current readiness; M7 product control |
| FastAPI API | authentication boundary, OpenAPI, idempotent commands, read projections, composition | durable long-running work, provider-specific business logic | current health; M4 product API |
| Worker | DBOS workflow runner, queues/schedules, background sync composition | alternate domain rules or unbounded loops | current idle boundary; M1/M4 execution |
| Domain | identifiers, immutable values, invariants, transition specifications, event intents | SQLAlchemy sessions, HTTP, workflow SDK, provider SDK, logging globals | M2 |
| Application | commands, queries, transaction boundaries, gateway orchestration, deterministic state changes | framework-specific request objects or model-authored authority | M2-M4 |
| Policies | versioned deterministic allow/deny decisions and reason codes | provider calls or state mutation | current protocol; M6 implementation |
| DBOS workflows | finite durable sequencing, queues, schedules, timers, retries, compensation/recovery commands | policy invention, direct Gmail calls, immortal agent loops | M1 acceptance; M4 product flows |
| Pydantic AI agents | typed immutable advisory artifacts with model/tool boundaries, provenance, evaluation, and cost | business state transitions, Gmail/send tools, unrestricted credentials | M1 typed acceptance fixture; M3 agent promotion |
| Persistence adapters | PostgreSQL mappings, repositories, outbox/audit/idempotency transactions | business decisions | M2 |
| Provider adapters | typed translation, timeout/error taxonomy, external request/response evidence | cross-provider orchestration or policy decisions | M3/M6 |
| `SendGateway` | last-mile outreach-enabled check, policy recheck, durable intent/attempt protocol, sole Gmail invocation path | content generation or direct model control | current minimal contract; M6 full path |
| Observability | safe correlation, metrics, traces, alerts, cost/evaluation outputs | source-of-truth state or secrets/PII copies | current request logs; M6-M8 expansion |

## Authoritative data flow

### Command and artifact flow

1. The dashboard sends an idempotent command to FastAPI.
2. FastAPI authenticates the operator, validates the OpenAPI model, and delegates to an application handler.
3. The handler loads PostgreSQL state, applies a deterministic transition, commits domain/audit events and any workflow command transactionally, then returns the authoritative result.
4. A finite workflow invokes typed agents through injected ports. Agents return versioned artifacts; they do not mutate experiment state.
5. Deterministic application code validates artifact eligibility, records the artifact, and performs any allowed transition.
6. Query services build projections from PostgreSQL. The dashboard never infers business success from a pending HTTP call.

### External side-effect flow

1. Deterministic code commits immutable `SendIntent` and outbound `SendAttempt` ledger records with a unique idempotency key and exact artifact/recipient/campaign versions before any provider call.
2. Policy evaluation records all facts, rule codes, policy version, and allow/deny outcome.
3. Queue admission reserves budget/rate capacity and records an audit event.
4. Immediately before Gmail, `SendGateway` rechecks outreach mode, suppression, approval, jurisdiction configuration, campaign/experiment state, budget, rate limit, and intent status.
5. The Gmail adapter sends a stable RFC message identifier and returns Gmail message/thread identifiers when known.
6. The attempt commits `SENT`; a timeout/crash instead leaves or marks `AMBIGUOUS`.
7. Reconciliation resolves ambiguity only from one positive authorized Gmail Sent match. Zero/multiple/conflicting candidates retain permanent quarantine; retry/replacement is forbidden unless explicit rejection or local pre-write proof establishes that Gmail could not have received bytes.
8. Gmail history sync advances its cursor only in the same transaction as recorded provider observations and emits reply/bounce events.

Every external model/search/extraction/enrichment call follows the same general intent, timeout, cost, provenance, and audit discipline, but only Gmail has reputation-bearing send authority.

## Persistence boundaries and the M1/M2 ruling

PostgreSQL is the application system of record from M2 onward. Business truth is derived from product tables plus immutable audit/domain events; provider systems remain evidence sources, not silent substitutes.

M1 is DBOS production acceptance, not product-schema development. It may use DBOS system tables and one disposable PostgreSQL schema named `m1_spike` with only:

- `spike_runs(run_id, scenario_name, workflow_version, state, started_at, finished_at)`; and
- `spike_send_attempts(idempotency_key, run_id, recipient_alias, state, rfc_message_id, gmail_message_id, gmail_thread_id, attempted_at, reconciled_at)`.

Test-recipient aliases are operator-owned inbox aliases, not prospects. The schema is dropped after evidence export and cannot be promoted or migrated into the product. If a scenario needs more product-like data, the spike harness uses immutable fixture files. M2 independently designs the first product tables, constraints, events, retention, and migrations.

## DBOS production acceptance and Temporal fallback

Pydantic AI plus DBOS on PostgreSQL is the selected architecture, as recorded in the [master stack decision](../README.md#selected-agent-and-durable-workflow-stack). M1 does not reopen selection; it production-accepts DBOS. Only the isolated disposable M1 harness may send, and only to operator-owned test inboxes. Product outreach remains disabled until both M1 and M6 evidence gates pass. Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues. Pydantic AI owns typed agent execution, while DBOS/Temporal owns durable execution mechanics; neither owns send policy, business transitions, or Gmail ambiguity decisions.

The runtime interface planned at the application boundary exposes finite start, pause, resume, cancel, status, queue, schedule, and correlation capabilities without leaking DBOS/Temporal handles into domain, agents, providers, API models, or frontend contracts. A mandatory Temporal migration changes composition/workflow adapters, not product state vocabulary.

## Deployment and trust boundaries

The M8 target is one private operator deployment: TLS ingress/private access -> frontend and API; worker and PostgreSQL are not public; backups are encrypted off-host; secrets and OAuth tokens are injected from a protected store; operator access is strongly authenticated; logs/metrics avoid message bodies, secrets, and unnecessary recipient data. API and worker may share one image/package but run separately and can be stopped independently. The only recipient-facing Internet surface is a later M9 exception of exactly two scanner-safe unsubscribe operations; it is disabled/unpublished before M9, partitioned from the 64 private-deployment operations by route/WAF/rate policy, and never exposes health/operator/Gmail/product routes or creates a webhook surface.

This is not a claim that the current Compose file satisfies production security, backup, monitoring, or availability requirements.

## Scope and non-goals

In scope: modular boundaries, one PostgreSQL authority, finite workflows, provider ports, typed artifacts, deterministic side effects, operator control, recovery, and private operations. Non-goals: microservices, shared event bus, Kubernetes, public multi-region availability, customer tenancy, generalized plugin platform, direct browser-to-provider access, and using an agent framework as a safety boundary.

## Exact planned implementation surfaces

Planned package additions: `alon_ai/application/`, expanded `domain/`, `persistence/`, implemented `workflows/`, `agents/`, `providers/`, `policies/`, and `observability/`. Composition stays in `alon_ai/api/app.py` and `alon_ai/worker/main.py` or narrowly focused composition modules they call. Product migrations live under `backend/alembic/versions/` starting M2. FastAPI remains the OpenAPI source; `frontend/openapi.json` and `frontend/src/lib/api/schema.d.ts` remain generated artifacts.

Current `alon_ai/domain/sending.py` imports policy and provider types, which is acceptable only as a foundation shortcut. By M2/M6, value types and provider ports move to inward-facing contract modules and the orchestrating gateway belongs in application code, so the target dependency direction in ARCH-02 is enforceable.

## Ordered implementation tasks

<!-- roadmap-task id=ARCH-01-T01 milestone=M1 depends_on=WF-01-T01,WF-01-T02,WF-01-T03 mode=serial locks=architecture-contracts,workflow-runtime,gmail-side-effects,milestone-gate -->
- [ ] **Run M1 DBOS production acceptance —** Input: disposable `m1_spike` schema, Pydantic AI typed fixture, test-inbox fixtures, and kill-point matrix; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: exercise DBOS against every acceptance criterion using only operator-owned inboxes; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: DBOS acceptance record and evidence export. Test evidence: restart, cancellation, ambiguity, duplicate-send, workflow-version, observability, operator-control, and rate-limit-under-restart/concurrency results. Failure behavior: retain a complete signed first-failure/runtime-rejection result with controls off for mandatory fallback; missing, corrupt or incomplete evidence remains a blocker and never counts as runtime acceptance.
<!-- roadmap-task id=ARCH-01-T02 milestone=M2 depends_on=ARCH-01-T01,ARCH-02-T01,ARCH-03-T01 mode=serial locks=architecture-contracts,database-schema,migration-head,milestone-gate -->
- [ ] **Build the M2 product core —** Input: ARCH-02/03 contracts; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: add domain/application/persistence modules, first product migrations, immutable events, idempotency, and repositories; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: PostgreSQL-backed system of record. Test evidence: migration, constraints, transitions, concurrency, audit, and fresh-restore tests. Failure behavior: block providers and agents.
<!-- roadmap-task id=ARCH-01-T03 milestone=M3 depends_on=ARCH-01-T02,ARCH-02-T01,AGENT-10-T05,DB-04-T05,ARCH-02-T03 mode=parallel locks=architecture-contracts,agent-runtime,agent-artifacts,provider-contracts -->
- [ ] **Add offline intelligence vertically —** Input: product records and provider ports; completed immutable promotion decision, persisted registry evidence and replaceable recorded provider boundaries. Operation: implement one typed artifact path with fixtures/evals before adding each specialist. Output: M3-promoted artifacts. Test evidence: schema, provenance, adversarial quality, cost, and regression reports. Failure behavior: rollback version.
<!-- roadmap-task id=ARCH-01-T04 milestone=M5 depends_on=ARCH-01-T03,WF-03-T05,WF-04-T05,PROVIDER-06-T03,WF-00-T04 mode=serial locks=architecture-contracts,workflow-runtime,agent-artifacts,backend-domain,milestone-gate -->
- [ ] **Adjudicate the M4/M5 no-send architecture —** Input: M3-promoted artifacts, the signed selected-runtime decision, complete WF-03 M4 no-send evidence, the complete WF-04 M5 finite-workflow contract, and reproducible enrichment evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: retain WF-03's independently gated M4 evidence, then compose and adjudicate the M5 lead-discovery/qualification slice without Gmail authority; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed M5 architecture record that references distinct retained M4 and M5 no-send evidence. Test evidence: complete synthetic M4 and M5 runs, restart, provenance, cost, state, and zero-send assertions. Failure behavior: remain at the last passing no-send gate and do not enable Gmail.
<!-- roadmap-task id=ARCH-01-T05 milestone=M7 depends_on=ARCH-01-T04,BACKEND-03-T03,PROVIDER-01-T03,DB-03-T06,WF-01-T01,TEST-04-T06,BACKEND-02-T05,FRONTEND-03-T05,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-08-T04,FRONTEND-09-T04,FRONTEND-01-T05,FRONTEND-03-T03 mode=serial locks=architecture-contracts,gmail-side-effects,openapi-contract,frontend-client,security-runtime,milestone-gate -->
- [ ] **Adjudicate the M6/M7 private-operator architecture —** Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact disabled-public 64+2 manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: retain the independently gated M6 send/reconcile/control bundle, then compose and adjudicate the M7 private authenticated API, generated client, reports, approvals, messages, recovery, and administration surfaces without public ingress; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed M7 private-operator architecture gate referencing distinct retained M6 and M7 evidence. Test evidence: Gmail authority, generated-client drift, session, accessibility, exhaustive-state, recovery, and browser-journey suites. Failure behavior: keep product outreach false; M7 and later deployment remain blocked.
<!-- roadmap-task id=ARCH-01-T06 milestone=M8 depends_on=ARCH-01-T05,INFRA-03-T07,INFRA-04-T06,INFRA-05-T07,OBS-05-T03 mode=serial locks=architecture-contracts,compose-topology,backup-restore,live-environment,milestone-gate -->
- [ ] **Prove private operations —** Input: complete private product; measured private deployment/load-rehearsal limits, clean restore evidence, current monitoring readiness and implemented full incident recovery services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: deploy, monitor, back up, restore, and exercise incidents; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: M8 evidence. Test evidence: fresh-server restore and incident drills. Failure behavior: block M9.

## Test strategy

- **Architecture `test_forbidden_imports`:** automated import rules enforce ARCH-02.
- **Contract `test_openapi_generated_client_has_no_drift`:** FastAPI remains API truth.
- **Integration `test_command_state_event_outbox_commit_atomically`:** product state and durable command evidence cannot diverge.
- **Recovery `test_each_side_effect_has_ambiguity_reconciliation`:** kill after provider acceptance does not cause blind retry.
- **Security `test_public_surface_excludes_worker_database_and_credentials`:** deployment topology and probes expose only approved ingress.
- **E2E `test_operator_controls_complete_experiment`:** one operator can create, inspect, pause, resume, cancel, and decide without database edits.

## Security, privacy, compliance, idempotency, observability, and cost

Authority flows inward from authenticated commands and outward through narrow ports. Credentials stay inside provider composition. Side-effect and command idempotency keys are unique and retained. All process/event/provider activity shares correlation IDs without copying sensitive payloads. Provider calls reserve and record costs. Applicable outreach rules are deterministic configuration plus operator/legal review, not model judgment.

## Failure, rollback, and recovery

Every provider can be disabled independently. Outreach has a global fail-closed control. Agent/model/prompt/provider versions roll back by selecting a previously promoted immutable version. Workflow changes require in-flight compatibility or drain/cancel/restart procedures. Schema changes use forward-safe migrations and tested restore. Mandatory DBOS-to-Temporal migration preserves application ports and canonical product state; M1 spike records are discarded after export.

## Acceptance and retained evidence

- [ ] Current and target topology are distinguishable.
- [ ] Every external side effect has one deterministic authority path and reconciliation.
- [ ] M1 uses only disposable spike records; M2 owns the first product data model.
- [ ] DBOS is selected but runtime production acceptance remains blocked on M1; every one of the eight disqualifying failures mandates Temporal.
- [ ] M1 sends are isolated-test-inbox-only, and product outreach remains disabled until both M1 and M6 evidence gates pass.
- [ ] The target remains operable by one person.

Retain architecture decisions, import-boundary reports, DBOS acceptance scorecard, crash/ambiguity traces, OpenAPI drift checks, migration/restore reports, and deployment trust-boundary evidence. This file unlocks [module boundaries](02-module-boundaries.md) and [states/events](03-domain-events-and-state-machines.md).
