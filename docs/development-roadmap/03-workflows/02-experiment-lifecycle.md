# Finite Autonomous Experiment Lifecycle

**Document ID:** WF-02
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M4, M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-02-T01 -> WF-02-T02 -> WF-02-T03 -> WF-02-T04 -> WF-02-T05`; cross-document task Inputs `WF-02-T01 <- BACKEND-01-T04,AGENT-10-T05,PROVIDER-03-T06,PROVIDER-04-T05,PROVIDER-05-T05,WF-01-T05,WF-00-T04; WF-02-T05 <- BACKEND-05-T01,WF-06-T03`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [runtime selection](00-dbos-selection-and-temporal-fallback.md).
**Outputs:** Finite typed inputs/results, immutable artifact/state handoffs, idempotency and recovery evidence
**Unlocks:** WF-03 idea/research/offer, WF-04 leads, WF-05 conversation and WF-07..09 booking/checkpoint/learning
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Each experiment stage is a finite durable run. Application services own product transitions; workflows pass immutable IDs/versions/hashes and idempotent commands. The experiment outlives its runs; a failed-stage retry creates a new workflow_run_id. Runtime artifact/state dependencies enforce the sequence even when per-lead stages execute concurrently.

## Current repository state and planned surfaces

No product workflow, persistent artifact/aggregate or provider implementation described here exists. Plan `backend/src/alon_ai/workflows/experiment_lifecycle.py` and application-owned command interfaces, fixture/contract tests and durable recovery simulations. Workflows never mutate ORM rows, call concrete adapters or own Gmail/calendar credentials.

## Exact workflow contract

### Stage and authority map

| Finite stage | Required input/provider | Completion and deterministic owner |
| --- | --- | --- |
| IDEA_VALIDATION | ExperimentBrief; optional IdeaDiscoveryAgent or IdeaBriefMaterializer | accepted IdeaBrief -> MarketResearchReport -> OfferPackage; ExperimentCommandService moves RESEARCHING -> READY_FOR_LEADS |
| LEAD_QUALIFICATION | Accepted OfferPackage; approved discovery | candidate -> PRELIMINARY QualificationDecision -> dossier -> FINAL QualificationDecision; readiness is preparation only |
| OUTREACH_AND_REPLY | Frozen cohort, accepted draft/strategy/final qualification and current authority | SendGateway, complete thread ingestion, bounded reply/objective/negotiation/writer/send loop; closed sample/window enters EVALUATING |
| BOOKING | Qualified buying intent and CALL_NEXT_STEP agreement | BookingGateway requires exact slot confirmation and reconciled provider event; purchase acceptance is optional |
| CHECKPOINT_EVALUATION | Closed-stage admission/cutoff and immutable evidence | CheckpointEvaluationService freezes CheckpointEvidenceBundle and records one exact result |
| GLOBAL_LEARNING | Closed checkpoint and frozen bundle | GlobalLearningEngine proposes; StrategyActivationService promotes/activates only at eligible boundaries |

The campaign program is STAGE_1_SIGNAL(100), STAGE_2_CONFIRM(200), STAGE_3_REPEAT(300), STAGE_4_ESTIMATE(400); cumulative maxima are 100/300/600/1,000. Unique membership, offer, strategy/activation, qualification, causal variables and evidence definitions freeze before each cohort starts. Only CONTINUE at stages 1-3 can make the next cohort eligible. Final CONTINUE closes positively with no fifth cohort; REVISE, KILL, INCONCLUSIVE and SAFETY_STOP cannot open more admission.

Normal artifact acceptance, in-envelope sends/replies/negotiations/bookings and checkpoint decisions do not wait for per-message approval. Unsafe/stale/ambiguous/out-of-envelope inputs pause into exceptions. Source/legal/provider/launch authority, current budget/rate/capacity and kill switches still gate each action.

### Durable identity and transition rules

Runtime ID: `experiment:{experiment_id}:{stage}:v{workflow_version}:run:{workflow_run_id}`; command key: `workflow:{workflow_run_id}:step:{step}:v{step_version}`. Queue `alon-ai-experiment-v1` starts at global/worker concurrency 2. Partial unique active-run constraints exclude overlapping same-stage runs. Per-lead work has distinct business/member identity and finite caps.

Store DB-01 RFC 8785 schema/payload hashes for workflow inputs/results; each agent has its own input snapshot with accepted upstream references. Replaying an existing step verifies its stored result and never redoes accepted paid calls. Success records bounded result/version/hash atomically with run completion, domain/audit/outbox and command result. Failed/cancelled runs have no successful result triplet.

ARCH-03 owns every transition, including FAILED exits and PAUSED resume target. READY_FOR_OUTREACH grants no sending permission. Stage closure stops admission and drains actions; unresolved Gmail/calendar writes remain quarantined/paused, never falsely terminal. Checkpoint decision and activation CAS bind cohort/control generation so a stale timer cannot reopen a stage.

## Ordered implementation tasks

<!-- roadmap-task id=WF-02-T01 milestone=M4 depends_on=BACKEND-01-T04,AGENT-10-T05,PROVIDER-03-T06,PROVIDER-04-T05,PROVIDER-05-T05,WF-01-T05,WF-00-T04 mode=parallel locks=workflow-runtime -->
- [ ] **Encode finite stage registry —** Input: canonical states/accepted runtime. Operation: freeze stage input/result schemas, per-stage dependency guards and run IDs. Output: registry and typed transitions. Test evidence: provider-before-consumer and missing-artifact failures. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-02-T02 milestone=M4 depends_on=WF-02-T01 mode=parallel locks=workflow-runtime -->
- [ ] **Implement idempotent start and completion —** Input: versioned command/run fixtures. Operation: atomically commit run/aggregate/events/audit/outbox and stored replay results. Output: finite lifecycle coordinator. Test evidence: duplicate start, transaction crash and hash-splice matrix. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-02-T03 milestone=M4 depends_on=WF-02-T02 mode=parallel locks=workflow-runtime -->
- [ ] **Implement failure and resume guards —** Input: ARCH-03 transition matrix. Operation: retain pause targets and retry limits; create new failed-stage runs and reject terminal restart. Output: closed recovery mapping. Test evidence: all legal/illegal exits and stale generation cases. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-02-T04 milestone=M4 depends_on=WF-02-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Verify no-send lifecycle —** Input: synthetic accepted artifact fixtures. Operation: execute idea and lead stage handoffs without write ports. Output: M4 coordinator evidence. Test evidence: finite completion/cancellation and zero Gmail/calendar access. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-02-T05 milestone=M6 depends_on=WF-02-T04,BACKEND-05-T01,WF-06-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Bind conversation/checkpoint controls —** Input: current product control and cohort fixtures. Operation: close admission, persist stage/checkpoint identity and require boundary eligibility for continuation. Output: M6 lifecycle control contract. Test evidence: pause/replay/ceiling/final-CONTINUE tests. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.

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
