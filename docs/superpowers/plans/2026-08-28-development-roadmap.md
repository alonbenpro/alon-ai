# Alon AI Development Roadmap Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the complete subsystem-organized, milestone-ordered Alon AI development roadmap.

**Architecture:** The roadmap is a documentation system: subsystem folders provide reference detail while the root README owns global vertical sequencing. Every file follows one contract so dependencies, exit gates, tests, rollback, and evidence remain comparable.

**Tech Stack:** Markdown, the existing Python/FastAPI/Pydantic/DBOS/PostgreSQL backend, Next.js/TypeScript frontend, Docker Compose, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-08-28-development-roadmap-design.md`

## Global Constraints

- Preserve the exact milestone order M0 through M9 from the spec.
- Select Pydantic AI for typed agents and DBOS for durable workflows on PostgreSQL; M1 is a DBOS production-acceptance gate, and Temporal is mandatory after any disqualifying failure.
- Optimize for one Israeli solo operator and a private deployment before platform features.
- Agents produce typed artifacts and never call Gmail directly.
- Deterministic policy plus `SendGateway` owns all Gmail side effects.
- Outreach remains disabled until the M1 and M6 evidence gates pass.
- PostgreSQL remains the application system of record.
- Use checkbox tasks, exact interfaces and evidence, no placeholders, no fake calendar estimates.
- Use `S/M/L/XL` complexity and `Low/Medium/High/Critical` risk.
- Distinguish current repository behavior from planned behavior.
- Before broad repository discovery, follow the Graphify-first protocol in `AGENTS.md`; use targeted text search only after the graph, and update Graphify after tracked documentation changes.
- LangChain, LangGraph, Restate, and Prefect are excluded from the initial runtime stack; record their layer and reconsideration triggers without planning their implementation.

---

### Task 1: Master roadmap, product strategy, and architecture

**Files:**
- Create: `AGENTS.md`
- Create: `docs/engineering/graphify-first-navigation.md`
- Rename: `docs/decisions/0002-provisional-dbos.md` to `docs/decisions/0002-dbos-workflow-runtime.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/superpowers/specs/2026-08-28-alon-ai-foundation-design.md`
- Modify: `docs/superpowers/plans/2026-08-28-alon-ai-foundation.md`
- Create: `docs/development-roadmap/README.md`
- Create: `docs/development-roadmap/00-product-strategy/01-product-scope.md`
- Create: `docs/development-roadmap/00-product-strategy/02-success-metrics.md`
- Create: `docs/development-roadmap/00-product-strategy/03-risk-register-and-kill-criteria.md`
- Create: `docs/development-roadmap/01-architecture/01-target-system-architecture.md`
- Create: `docs/development-roadmap/01-architecture/02-module-boundaries.md`
- Create: `docs/development-roadmap/01-architecture/03-domain-events-and-state-machines.md`

**Interfaces:**
- Consumes: Approved spec, current `README.md`, `docs/architecture.md`, ADRs 0001-0003, and the existing Graphify graph.
- Produces: Selected Pydantic AI/DBOS responsibilities, Temporal fallback criteria, Graphify-first agent navigation, milestone vocabulary, document template, dependency rules, product gates, architecture boundaries, and state/event names used by all later tasks.

- [ ] **Step 1:** Use Graphify first to inventory the current implemented and missing boundaries, then validate the graph-selected source and architecture locations with targeted reads.
- [ ] **Step 2:** Record Pydantic AI plus DBOS as the selected stack, Temporal as the mandatory fallback, the M1 production-acceptance gate, and the unchanged Gmail ambiguity safeguards across the ADR, foundation documents, architecture, and repository README.
- [ ] **Step 3:** Add root agent instructions and the engineering guide with exact Graphify bootstrap, reflect, vocabulary expansion, query, targeted-search, memory, update, hook, and exception rules.
- [ ] **Step 4:** Write the root roadmap index with M0-M9 order, phase gates, file manifest, dependency map, and “what not to build yet.”
- [ ] **Step 5:** Write product scope, metrics, risk, kill criteria, target architecture, module dependency rules, core state machines, and domain-event catalog.
- [ ] **Step 6:** Run placeholder, broken-link, milestone-order, stale-architecture, agent-instruction, and current/future-truth scans over these files.
- [ ] **Step 7:** Commit exactly these files with message `docs: select stack and define roadmap architecture`.

### Task 2: Database and durable workflows

**Files:**
- Create: `docs/development-roadmap/02-database/01-core-data-model.md`
- Create: `docs/development-roadmap/02-database/02-experiment-and-offer-schema.md`
- Create: `docs/development-roadmap/02-database/03-leads-campaigns-and-messages.md`
- Create: `docs/development-roadmap/02-database/04-agent-artifacts-and-evidence.md`
- Create: `docs/development-roadmap/02-database/05-audit-events-and-idempotency.md`
- Create: `docs/development-roadmap/02-database/06-migrations-seeding-and-retention.md`
- Create: `docs/development-roadmap/03-workflows/00-dbos-selection-and-temporal-fallback.md`
- Create: `docs/development-roadmap/03-workflows/01-dbos-production-acceptance-spike.md`
- Create: `docs/development-roadmap/03-workflows/02-experiment-lifecycle.md`
- Create: `docs/development-roadmap/03-workflows/03-idea-validation-workflow.md`
- Create: `docs/development-roadmap/03-workflows/04-lead-qualification-workflow.md`
- Create: `docs/development-roadmap/03-workflows/05-outreach-and-reply-workflow.md`
- Create: `docs/development-roadmap/03-workflows/06-pause-cancel-resume-and-recovery.md`

**Interfaces:**
- Consumes: M0-M9, architecture boundaries, state machines, domain-event names.
- Produces: Exact PostgreSQL entities, keys, constraints, transition ownership, DBOS workflow IDs, queue semantics, production-acceptance evidence, and the documented Temporal fallback trigger.

- [ ] **Step 1:** Define normalized schemas, identifiers, constraints, indexes, ownership, and retention for every product record.
- [ ] **Step 2:** Define event, audit, artifact, provenance, idempotency, outbox, and reconciliation records.
- [ ] **Step 3:** Record why DBOS was selected, classify adjacent frameworks and competing runtimes accurately, and define evidence-based reconsideration triggers without reopening the initial stack.
- [ ] **Step 4:** Specify the DBOS Gmail production-acceptance spike including kill points, ambiguous-outcome reconciliation, disqualifying failures, and the mandatory Temporal migration handoff.
- [ ] **Step 5:** Specify finite workflows for experiments, ideas, leads, outreach, replies, pause/cancel/resume, and recovery.
- [ ] **Step 6:** Cross-check every workflow read/write against a defined table and every state change against the state machine.
- [ ] **Step 7:** Commit exactly these files with message `docs: plan persistence and durable workflows`.

### Task 3: Typed agents and evaluations

**Files:**
- Create: `docs/development-roadmap/04-agents/01-agent-runtime-and-contracts.md`
- Create: `docs/development-roadmap/04-agents/02-idea-discovery-agent.md`
- Create: `docs/development-roadmap/04-agents/03-offer-design-agent.md`
- Create: `docs/development-roadmap/04-agents/04-market-research-agent.md`
- Create: `docs/development-roadmap/04-agents/05-lead-research-agent.md`
- Create: `docs/development-roadmap/04-agents/06-lead-qualification-agent.md`
- Create: `docs/development-roadmap/04-agents/07-outreach-drafting-agent.md`
- Create: `docs/development-roadmap/04-agents/08-reply-classification-agent.md`
- Create: `docs/development-roadmap/04-agents/09-experiment-evaluation-agent.md`
- Create: `docs/development-roadmap/04-agents/10-agent-evals-and-versioning.md`

**Interfaces:**
- Consumes: Artifact/evidence schema, workflow steps, product metrics, provider boundaries.
- Produces: Typed input/output models, allowed tools, forbidden actions, evaluation datasets, thresholds, prompt/model versioning, cost caps, and operator-review rules.

- [ ] **Step 1:** Define shared agent execution envelope, dependency injection, provenance, cost, timeout, and tool-authority contracts.
- [ ] **Step 2:** Specify each specialist with exact typed inputs, outputs, tools, evidence rules, confidence behavior, and failure result.
- [ ] **Step 3:** Define offline fixtures, adversarial cases, scoring functions, regression thresholds, and promotion/rollback rules.
- [ ] **Step 4:** Verify no agent can transition business state or call Gmail directly.
- [ ] **Step 5:** Commit exactly these files with message `docs: plan typed agents and evaluations`.

### Task 4: Providers and backend application services

**Files:**
- Create: `docs/development-roadmap/05-providers/01-gmail-oauth-and-adapter.md`
- Create: `docs/development-roadmap/05-providers/02-gmail-history-sync.md`
- Create: `docs/development-roadmap/05-providers/03-model-provider.md`
- Create: `docs/development-roadmap/05-providers/04-search-provider.md`
- Create: `docs/development-roadmap/05-providers/05-page-fetching-and-extraction.md`
- Create: `docs/development-roadmap/05-providers/06-enrichment-provider.md`
- Create: `docs/development-roadmap/06-backend/01-domain-services.md`
- Create: `docs/development-roadmap/06-backend/02-api-contracts.md`
- Create: `docs/development-roadmap/06-backend/03-policy-engine.md`
- Create: `docs/development-roadmap/06-backend/04-send-gateway.md`
- Create: `docs/development-roadmap/06-backend/05-approval-and-command-handling.md`
- Create: `docs/development-roadmap/06-backend/06-reporting-and-query-services.md`

**Interfaces:**
- Consumes: Database records, workflow commands/events, typed agent contracts.
- Produces: Provider protocols and error taxonomies, OAuth lifecycle, Gmail reconciliation behavior, deterministic services/policies, OpenAPI endpoints, commands, approvals, and projections.

- [ ] **Step 1:** Specify every provider contract, timeout, retry class, credential boundary, fixture, and replacement seam.
- [ ] **Step 2:** Specify Gmail OAuth, send, Sent-mail reconciliation, history cursor, replay, and expiry recovery.
- [ ] **Step 3:** Specify domain services, policy composition, `SendGateway`, approvals, commands, reports, and API shapes.
- [ ] **Step 4:** Trace each external side effect through intent, policy, execution, audit, and reconciliation.
- [ ] **Step 5:** Commit exactly these files with message `docs: plan providers and backend services`.

### Task 5: Operator frontend

**Files:**
- Create: `docs/development-roadmap/07-frontend/01-information-architecture.md`
- Create: `docs/development-roadmap/07-frontend/02-experiment-creation-flow.md`
- Create: `docs/development-roadmap/07-frontend/03-experiment-control-center.md`
- Create: `docs/development-roadmap/07-frontend/04-evidence-and-agent-artifacts.md`
- Create: `docs/development-roadmap/07-frontend/05-lead-and-campaign-management.md`
- Create: `docs/development-roadmap/07-frontend/06-approval-inbox.md`
- Create: `docs/development-roadmap/07-frontend/07-message-and-reply-timeline.md`
- Create: `docs/development-roadmap/07-frontend/08-cost-funnel-and-decision-analytics.md`
- Create: `docs/development-roadmap/07-frontend/09-error-recovery-and-accessibility.md`

**Interfaces:**
- Consumes: OpenAPI commands/queries, state machine, approval model, artifacts, events, reporting projections.
- Produces: Route map, page/component responsibilities, exact states and actions, data-fetch/mutation behavior, accessibility, responsive, and end-to-end acceptance flows.

- [ ] **Step 1:** Define the smallest operator information architecture that exposes every required command and failure state.
- [ ] **Step 2:** Specify each workflow screen with routes, components, query keys, mutations, optimistic behavior, empty/loading/error/stale states, and permissions.
- [ ] **Step 3:** Specify accessibility, responsive breakpoints, keyboard flows, destructive confirmations, and recovery UX.
- [ ] **Step 4:** Map every screen field/action to a defined backend contract; reject invented endpoints.
- [ ] **Step 5:** Commit exactly these files with message `docs: plan the operator frontend`.

### Task 6: Security, compliance, observability, and evaluation operations

**Files:**
- Create: `docs/development-roadmap/08-security-and-compliance/01-threat-model.md`
- Create: `docs/development-roadmap/08-security-and-compliance/02-authentication-and-private-access.md`
- Create: `docs/development-roadmap/08-security-and-compliance/03-secrets-and-oauth-token-security.md`
- Create: `docs/development-roadmap/08-security-and-compliance/04-outreach-compliance.md`
- Create: `docs/development-roadmap/08-security-and-compliance/05-suppression-budgets-and-kill-switch.md`
- Create: `docs/development-roadmap/08-security-and-compliance/06-data-privacy-and-retention.md`
- Create: `docs/development-roadmap/09-observability-and-evaluation/01-structured-events-and-correlation.md`
- Create: `docs/development-roadmap/09-observability-and-evaluation/02-metrics-tracing-and-alerting.md`
- Create: `docs/development-roadmap/09-observability-and-evaluation/03-provider-cost-accounting.md`
- Create: `docs/development-roadmap/09-observability-and-evaluation/04-agent-and-workflow-evaluations.md`
- Create: `docs/development-roadmap/09-observability-and-evaluation/05-incident-response.md`

**Interfaces:**
- Consumes: Every side effect, credential, table, event, agent run, workflow state, and operator command.
- Produces: Threat controls, private-access model, policy requirements, retention rules, telemetry schema, SLO signals, cost ledger, evaluation operations, and incident actions.

- [ ] **Step 1:** Threat-model assets, trust boundaries, abuse cases, and controls.
- [ ] **Step 2:** Specify single-operator access, credential encryption/rotation, compliance configuration, suppression, budgets, and kill-switch behavior.
- [ ] **Step 3:** Specify correlation, logs, traces, metrics, alerts, costs, evaluations, and incident workflows without secret/PII leakage.
- [ ] **Step 4:** Cross-check that every Critical threat and failure has a deterministic prevention or detection path.
- [ ] **Step 5:** Commit exactly these files with message `docs: plan security and observability`.

### Task 7: Testing and infrastructure

**Files:**
- Create: `docs/development-roadmap/10-testing/01-testing-strategy.md`
- Create: `docs/development-roadmap/10-testing/02-contract-and-integration-tests.md`
- Create: `docs/development-roadmap/10-testing/03-workflow-recovery-tests.md`
- Create: `docs/development-roadmap/10-testing/04-gmail-side-effect-tests.md`
- Create: `docs/development-roadmap/10-testing/05-end-to-end-browser-tests.md`
- Create: `docs/development-roadmap/10-testing/06-load-security-and-chaos-tests.md`
- Create: `docs/development-roadmap/11-infrastructure/01-local-development.md`
- Create: `docs/development-roadmap/11-infrastructure/02-ci-cd-and-release-process.md`
- Create: `docs/development-roadmap/11-infrastructure/03-private-vps-deployment.md`
- Create: `docs/development-roadmap/11-infrastructure/04-postgresql-backups-and-restores.md`
- Create: `docs/development-roadmap/11-infrastructure/05-monitoring-and-disaster-recovery.md`

**Interfaces:**
- Consumes: All acceptance criteria, provider boundaries, workflows, security controls, deployment topology, and telemetry.
- Produces: Test pyramid and fixtures, crash matrix, Gmail sandbox rules, browser journeys, security/load tests, local topology, CI gates, deployment, backups, monitoring, and restore evidence.

- [ ] **Step 1:** Define test ownership, isolation, fixtures, commands, CI placement, and evidence retention.
- [ ] **Step 2:** Specify contract, integration, recovery, side-effect, browser, load, security, and chaos matrices.
- [ ] **Step 3:** Specify local, CI, VPS, backup, monitoring, upgrade, rollback, and disaster-recovery procedures.
- [ ] **Step 4:** Require restore and recovery drills that prove the procedures, not merely document them.
- [ ] **Step 5:** Commit exactly these files with message `docs: plan testing and infrastructure`.

### Task 8: Launch operations and whole-roadmap audit

**Files:**
- Create: `docs/development-roadmap/12-launch-and-operations/01-test-inbox-pilot.md`
- Create: `docs/development-roadmap/12-launch-and-operations/02-controlled-internal-launch.md`
- Create: `docs/development-roadmap/12-launch-and-operations/03-first-real-experiment.md`
- Create: `docs/development-roadmap/12-launch-and-operations/04-earned-autonomy.md`
- Create: `docs/development-roadmap/12-launch-and-operations/05-maintenance-and-upgrade-policy.md`
- Modify: `docs/development-roadmap/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: All earlier deliverables and gates.
- Produces: Operator launch checklists, evidence promotion ladder, real-experiment constraints, autonomy criteria, maintenance policy, and an audited master index.

- [ ] **Step 1:** Specify test-inbox, internal, and first-real-experiment promotion gates with exact abort conditions.
- [ ] **Step 2:** Specify earned-autonomy levels, authority limits, demotion triggers, and permanent forbidden actions.
- [ ] **Step 3:** Specify dependency/security maintenance, migrations, model/prompt upgrades, provider changes, and rollback policy.
- [ ] **Step 4:** Update the master README file manifest, milestone map, and critical path after every file exists.
- [ ] **Step 5:** Add a concise repository README link to `docs/development-roadmap/README.md` without duplicating the roadmap.
- [ ] **Step 6:** Run repository-wide placeholder, empty-file, heading-contract, link, milestone, dependency, endpoint/table/artifact naming, selected-stack, Graphify-instruction, and current/future truth scans.
- [ ] **Step 7:** Run `make generate lint typecheck test build`; confirm generated contracts do not drift.
- [ ] **Step 8:** Commit exactly the launch files and any audited README corrections with message `docs: complete the development roadmap`.
