# Checkpoint Evidence and Experiment Evaluation Workflow

**Document ID:** WF-08
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-08-T01 -> WF-08-T02 -> WF-08-T03 -> WF-08-T04`; cross-document task Inputs `WF-08-T01 <- WF-05-T04,AGENT-09-T04,ARCH-03-T01,BACKEND-01-T09`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [runtime selection](00-dbos-selection-and-temporal-fallback.md).
**Outputs:** Finite typed inputs/results, immutable artifact/state handoffs, idempotency and recovery evidence
**Unlocks:** WF-09 global learning and deterministic next-stage eligibility
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Every cohort closes into one immutable CheckpointEvidenceBundle and one authoritative checkpoint result. M6 proves the machinery with frozen synthetic/owned-resource evidence. M9 supplies controlled real campaign evidence later; it is not an implementation prerequisite.

## Current repository state and planned surfaces

No product workflow, persistent artifact/aggregate or provider implementation described here exists. Plan `backend/src/alon_ai/workflows/checkpoint_evaluation.py` and application-owned command interfaces, fixture/contract tests and durable recovery simulations. Workflows never mutate ORM rows, call concrete adapters or own Gmail/calendar credentials.

## Exact workflow contract

### Checkpoint closure and decision

| Boundary | Required evidence | Durable result / owner |
| --- | --- | --- |
| close admission | exact campaign/cohort ordinal, member hash, cutoff and generation | CheckpointEvaluationService moves OPEN -> CLOSING and stops/drains stage actions |
| freeze evidence | campaign/stage primary source observations, terminal/reconciled outcomes or explicit unresolved safety flags, frozen offer/strategy/metric/cost definitions | CheckpointEvidenceBundle ID/version/hash; EVIDENCE_FROZEN and checkpoint.evidence_frozen.v1 |
| bounded evaluation | frozen bundle and rules, accepted OfferPackage and agent configuration | ExperimentEvaluationAgent returns recommendation/reasons only; no live evidence mutation |
| deterministic decision | immutable rule/metric/cost values, completeness and safety flags, prior decision and recommendation | exactly CONTINUE, REVISE, KILL, INCONCLUSIVE or SAFETY_STOP; DECIDED and checkpoint.decision_recorded.v1 |
| learning trigger | closed cohort/checkpoint and accepted frozen bundle | unique checkpoint-owned outbox trigger for WF-09 |
| next-stage eligibility | CONTINUE, next registered stage, completed learning/promotion decision or retained unchanged strategy, current safety/capacity controls | boundary activation then unique next cohort freeze/admission; no direct send authority |

The increments are 100/200/300/400 with cumulative maxima 100/300/600/1,000. Only CONTINUE at stages 1-3 may proceed. At stage 4 CONTINUE is a positive terminal result with no fifth cohort. REVISE, KILL, INCONCLUSIVE and SAFETY_STOP close further admission. Weak evidence never becomes continuation because the agent is confident.

The bundle freezes newly completed stage evidence as primary, with cutoff, member/delivered-recipient denominators, replies/commitments/bookings, negotiation/economics, costs, failures/incidents, causal variables, offer, strategy and activation refs. It distinguishes missing, unresolved, synthetic/test and real demand evidence. Follow-up messages do not add new recipients. Operator-time evidence must verify under PRODUCT-01; missing cost evidence cannot be imputed as success.

### Replay, late evidence and safety

Closure/decision uniques bind campaign/cohort and expected generation; duplicate triggers return the same checkpoint. Stage admission closes before evidence freezes. Model failure cannot block a deterministic safety stop. Incomplete or ambiguous safety facts force the applicable INCONCLUSIVE/SAFETY_STOP and preserve quarantine; they cannot make started writes terminal.

Late observations append to their owning records and attribution, never mutate the frozen bundle or historical decision. An authorized correction creates linked new evidence/decision lineage under canonical state guards and cannot retroactively reopen a closed cohort. Pause/cancel during freeze/evaluation preserves cutoff/hash, remaining budget and pending action truth. Resume verifies all hashes and reuses recorded recommendation/decision. Closing a paused cohort for rollback does not grant next-stage admission.

## Ordered implementation tasks

<!-- roadmap-task id=WF-08-T01 milestone=M6 depends_on=WF-05-T04,AGENT-09-T04,ARCH-03-T01,BACKEND-01-T09 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Encode finite closure and evidence interfaces —** Input: canonical checkpoint states/rules and CheckpointEvaluationService interface. Operation: bind cohort/cutoff/member/offer/strategy/metric/cost versions and stop admission. Output: checkpoint coordinator contract. Test evidence: unknown ordinal, duplicate closure and incomplete outcome cases. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-08-T02 milestone=M6 depends_on=WF-08-T01 mode=parallel locks=workflow-runtime,agent-artifacts -->
- [ ] **Implement immutable evidence freeze —** Input: synthetic stage observations and minimized transforms. Operation: create one CheckpointEvidenceBundle then evaluate its pinned version. Output: frozen bundle and recommendation handoff. Test evidence: late observation, hash splice, missing cost and denominator cases. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-08-T03 milestone=M6 depends_on=WF-08-T02 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Commit deterministic decision and learning trigger —** Input: frozen rules/recommendation/safety facts. Operation: record exact five-way result and checkpoint outbox trigger atomically. Output: authoritative decision/eligibility interface. Test evidence: only CONTINUE advances, terminal 1,000 ceiling and replay uniqueness. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-08-T04 milestone=M6 depends_on=WF-08-T03 mode=serial locks=workflow-runtime,milestone-gate -->
- [ ] **Retain checkpoint recovery simulation —** Input: all four cohorts and safety/incomplete variants. Operation: crash/replay close, freeze, evaluate, decide and trigger boundaries. Output: M6 checkpoint evidence. Test evidence: no fifth cohort, lost trigger, mutable evidence or double decision. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.

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
