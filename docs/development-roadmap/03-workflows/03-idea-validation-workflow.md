# Idea, Market Research, and Offer Workflow

**Document ID:** WF-03
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M4 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-03-T01 -> WF-03-T02 -> WF-03-T03 -> WF-03-T04 -> WF-03-T05`; cross-document task Inputs `WF-03-T01 <- AGENT-10-T05,DB-02-T03,DB-02-T04,PRODUCT-02-T01; WF-03-T02 <- PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,OBS-03-T02,BACKEND-01-T01,DB-04-T04,BACKEND-01-T04; WF-03-T03 <- DB-04-T04,BACKEND-01-T04,AGENT-02-T03,AGENT-03-T03,AGENT-04-T03; WF-03-T04 <- WF-02-T03`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [runtime selection](00-dbos-selection-and-temporal-fallback.md).
**Outputs:** Finite typed inputs/results, immutable artifact/state handoffs, idempotency and recovery evidence
**Unlocks:** WF-04 discovery and final qualification
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Both discovered and user-supplied ideas produce the same accepted IdeaBrief. Market Research always runs next, then Offer Design consumes both upstream artifacts. M4 verifies the complete no-send path using synthetic/recorded evidence.

## Current repository state and planned surfaces

No product workflow, persistent artifact/aggregate or provider implementation described here exists. Plan `backend/src/alon_ai/workflows/idea_validation.py` and application-owned command interfaces, fixture/contract tests and durable recovery simulations. Workflows never mutate ORM rows, call concrete adapters or own Gmail/calendar credentials.

## Exact workflow contract

### Ordered artifact transactions

| Step | Inputs | Result / deterministic guard |
| --- | --- | --- |
| freeze scope | ExperimentBrief/version/hash, source/economic bounds, baseline strategy activation | immutable workflow input; reject missing/broad scope |
| resolve idea origin | Exactly DISCOVERED or USER_SUPPLIED | agent creates IdeaBrief or IdeaBriefMaterializer creates the same shape with user provenance/bypass record |
| accept IdeaBrief | Produced brief and provenance | deterministic validation/acceptance; no manual selection requirement |
| research market | Accepted IdeaBrief ID/version/hash | MarketResearchReport with source/time/citation/unknown/contradiction evidence |
| accept research | Produced report and captured evidence | missing or conflicting required evidence blocks Offer Design |
| design offer | Accepted IdeaBrief AND MarketResearchReport, pre-run economics | complete OfferPackage; deterministic evidence/economics/qualification/negotiation-bound checks |
| finish | All three accepted artifact refs and output hashes | RESEARCHING -> READY_FOR_LEADS; bounded result snapshot and canonical events |

OfferPackage never supplies input upstream. This workflow creates only IdeaBrief, MarketResearchReport and OfferPackage from the canonical registry. ExperimentBrief, metric records and runtime recommendations remain product/run records outside the fifteen-artifact registry.

Application ArtifactCommandService, ArtifactValidationService, ArtifactAcceptanceService, IdeaBriefMaterializer and the experiment service own their writes. Agent cost reservations/recording/evidence ingestion are separate owned commands. Each accepted artifact retains exact source refs, producer strategy/activation, its own input snapshot and output hash.

### Durability and bounded execution

Queue `alon-ai-research-v1` starts at concurrency 2. Keys `workflow:{run_id}:step:{idea|research|offer}:v1` bind origin, expected accepted input refs and configuration. The origin choice is immutable for the experiment version; duplicate USER_SUPPLIED submits return the same materialized brief. No workflow retry may switch origin, skip research or reuse an incompatible offer.

Stop before and after every paid provider/agent boundary. Persist/recover each accepted result before starting its consumer. Missing evidence, exceeded budget, cancellation or stale input ends/pauses the finite run; a rejected artifact cannot drive the next step. Revision creates new immutable inputs and invalidates later artifacts; an active cohort cannot mutate.

## Ordered implementation tasks

<!-- roadmap-task id=WF-03-T01 milestone=M4 depends_on=AGENT-10-T05,DB-02-T03,DB-02-T04,PRODUCT-02-T01 mode=parallel locks=workflow-runtime -->
- [ ] **Freeze origin and input contracts —** Input: canonical IdeaBrief and accepted scope. Operation: implement DISCOVERED/USER_SUPPLIED discriminated origin with one validated shape. Output: immutable input/origin contract. Test evidence: origin exclusivity, duplicate bypass and provenance checks. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-03-T02 milestone=M4 depends_on=WF-03-T01,PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,OBS-03-T02,BACKEND-01-T01,DB-04-T04,BACKEND-01-T04 mode=parallel locks=workflow-runtime,backend-domain,agent-artifacts -->
- [ ] **Implement idea then research —** Input: typed origin, IdeaBriefMaterializer and source fixtures. Operation: accept IdeaBrief and pass its exact version/hash into Market Research. Output: accepted IdeaBrief and MarketResearchReport handoff. Test evidence: bypass equivalence, missing idea, stale source and injection cases. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-03-T03 milestone=M4 depends_on=WF-03-T02,DB-04-T04,BACKEND-01-T04,AGENT-02-T03,AGENT-03-T03,AGENT-04-T03 mode=parallel locks=workflow-runtime,backend-domain,agent-artifacts -->
- [ ] **Implement authoritative offer handoff —** Input: both accepted upstream artifacts and frozen economics. Operation: validate and accept complete OfferPackage, then persist terminal readiness. Output: accepted commercial package and READY_FOR_LEADS. Test evidence: reversed order, incomplete economics and downstream authority denial. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-03-T04 milestone=M4 depends_on=WF-03-T03,WF-02-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Prove crash and cancel recovery —** Input: stored step outputs and workflow versions. Operation: inject failures before/after every model/evidence/acceptance/transition boundary. Output: finite recovery traces. Test evidence: no repeated paid call, double materialization or stale consumer. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-03-T05 milestone=M4 depends_on=WF-03-T04 mode=serial locks=workflow-runtime,milestone-gate -->
- [ ] **Retain the synthetic M4 gate —** Input: complete discovered/bypass scenarios. Operation: verify artifact lineage, costs, evidence and zero write capability. Output: M4 gate bundle. Test evidence: both origins complete exactly idea -> research -> offer. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.

## Test strategy

Contract tests cover exact accepted-artifact version/hash lineage and state ownership. Real isolated PostgreSQL tests inject failure before/after each aggregate/artifact/event/audit/outbox/idempotency transaction. Recorded providers and owned-resource gates cover duplicate/out-of-order delivery, cancellation, stale generation and ambiguity. Required scenarios appear per task; no fake/synthetic evidence counts as real demand.

## Safety, privacy, compliance, observability and cost

Every run pins schema/configuration, producer strategy, GlobalStrategyPackage/StrategyActivation, deadline and finite attempt/tool/token/cost ceilings. Application services reserve paid-call budgets before execution and reconcile all usage. Retention follows DB-06 per record/field purpose and sensitivity; minimized evidence is required before learning reuse.

Telemetry includes safe IDs, hashes, versions, counts, durations, outcomes and costs. It excludes raw recipients, message/calendar content, sensitive budget spans, credentials and hidden reasoning. Source and email content are untrusted data; deterministic legal/provider/suppression/commercial gates and scoped write ports remain mandatory.

## Failure, rollback, recovery and acceptance

Pause closes admission before acknowledgement and retains the exact resume target, accepted inputs, counters/capacity and control generation. Cancel drains only provably uncalled work; uncertain external outcomes remain quarantined with durable evidence. Terminal runs never resume. A valid failed-stage retry creates a new linked finite run; changed inputs create superseding artifacts outside active cohorts.

- [ ] Every boundary has a named deterministic owner and accepted version/hash input.
- [ ] No workflow has direct Gmail/calendar write authority or routine per-message approval.
- [ ] Every replay, pause, terminal stop and ambiguous outcome has a finite coordinator outcome with no blind retry.
- [ ] Cohort and strategy boundaries preserve capacity, immutable evidence and historical attribution.
- [ ] Required contract/recovery/gate evidence is retained before later product use.

Retain schema/transition snapshots, command/artifact/activation lineage, source/provider fixture hashes, full crash matrices, safe audit/event traces, cost reconciliation and gate results.
