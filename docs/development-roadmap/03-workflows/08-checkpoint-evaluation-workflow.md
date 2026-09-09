# Checkpoint Evidence and Experiment Evaluation Workflow

**Document ID:** WF-08
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M6
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-08-T01 -> WF-08-T02 -> WF-08-T03 -> WF-08-T04`; cross-document task Inputs `WF-08-T01 <- WF-05-T04,AGENT-09-T04,ARCH-03-T01,BACKEND-01-T09`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [PRODUCT-02](../00-product-strategy/02-success-metrics.md), architecture/state docs.
**Outputs:** immutable stage/tranche evidence bundles, deterministic checkpoint results, learning trigger, replay/recovery evidence
**Unlocks:** WF-09 global learning and next-stage eligibility
**Risk:** Critical
**Complexity:** L

## Outcome

Every real-validation stage or explicitly authorized scale tranche closes into one immutable `CheckpointEvidenceBundle` and one authoritative decision. M6 proves the mechanism with synthetic/owned resources; M9 supplies real evidence later.

The exact pre-revenue launch sequence is `SHADOW -> REVIEW_20 -> QUALIFIED_50 -> SCALE_100_TO_300`.

- `SHADOW` has zero real recipients. It may exercise checkpoint machinery and offline evaluation but is not real-demand learning evidence.
- `REVIEW_20` closes after up to 20 manually reviewed businesses.
- `QUALIFIED_50` closes after up to 50 finally qualified businesses.
- `SCALE_100_TO_300` is one explicitly authorized tranche with exact signed size from 100 through 300. There is no automatic 600/1,000 progression.

## Closure and decision contract

| Boundary | Required evidence | Durable result / owner |
| --- | --- | --- |
| close admission | exact campaign/stage/tranche, membership hash, cutoff, generation and signed scale authorization where applicable | CheckpointEvaluationService moves OPEN -> CLOSING and stops/drains stage actions |
| freeze evidence | terminal/reconciled outcomes or unresolved safety flags, offer/strategy/model-routing/source/metric/cost definitions, meetings/bookings/revenue/economics | immutable CheckpointEvidenceBundle |
| bounded evaluation | frozen bundle and accepted rules/configuration | ExperimentEvaluationAgent recommendation only |
| deterministic decision | immutable metric/cost/safety/completeness values | exactly CONTINUE, REVISE, KILL, INCONCLUSIVE or SAFETY_STOP |
| learning trigger | closed real-demand checkpoint (`REVIEW_20`, `QUALIFIED_50`, scale tranche) | unique checkpoint-owned WF-09 trigger |
| next-stage eligibility | CONTINUE + next registered stage + current safety + learning result/unchanged strategy; scale additionally needs exact `ScaleAuthorization` | boundary activation then next stage/tranche membership freeze |

`CONTINUE` at `QUALIFIED_50` does not itself admit 100–300 businesses. `ScaleAuthorization` must bind exact tranche size, spend caps, market/offer/source/strategy versions, evidence window and expiry after meetings/economic evidence justify scale.

`CONTINUE` at `SCALE_100_TO_300` is terminal for the current pre-revenue program and cannot auto-open a larger population.

## Evidence semantics

The bundle freezes the newly completed stage/tranche as primary evidence: exact member denominator, delivered/replied/qualified/meeting/booking/revenue outcomes, negotiation economics, provider/model costs and routing-tier mix, operator time, incidents, source/offer/strategy versions and causal variables. Missing or unresolved evidence stays explicit.

Shadow/test evidence is tagged and cannot become real demand. Late observations append to their owning records but never mutate a frozen bundle/decision. A correction creates linked new evidence lineage under canonical guards; it does not silently reopen a stage.

## Replay, pause and safety

Closure/decision keys bind campaign/stage/tranche/generation. Duplicate triggers return the same checkpoint. Admission closes before evidence freezes. Incomplete/ambiguous safety facts produce INCONCLUSIVE/SAFETY_STOP as applicable. Pause/cancel preserves cutoff, counters, reservations and unresolved provider truth. Resume verifies hashes and reuses recorded recommendation/decision.

Strategy/offer/qualification/evidence definitions never mutate halfway through a stage/tranche.

## Ordered implementation tasks

<!-- roadmap-task id=WF-08-T01 milestone=M6 depends_on=WF-05-T04,AGENT-09-T04,ARCH-03-T01,BACKEND-01-T09 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Encode finite closure and evidence interfaces —** Input: cost-first stage registry and CheckpointEvaluationService. Operation: bind stage/tranche/cutoff/member/offer/strategy/source/model-routing/metric/cost versions and stop admission. Output: checkpoint coordinator contract. Test evidence: unknown stage, missing manual-review/scale authorization, duplicate closure, incomplete outcomes. Failure behavior: stop unsafe admission and retain blocked evidence.
<!-- roadmap-task id=WF-08-T02 milestone=M6 depends_on=WF-08-T01 mode=parallel locks=workflow-runtime,agent-artifacts -->
- [ ] **Implement immutable evidence freeze —** Input: synthetic stage observations and minimized transforms. Operation: create one CheckpointEvidenceBundle and evaluate pinned version. Output: frozen bundle/recommendation handoff. Test evidence: late observation, hash splice, missing cost, wrong denominator and shadow-as-demand cases. Failure behavior: no continuation by inference.
<!-- roadmap-task id=WF-08-T03 milestone=M6 depends_on=WF-08-T02 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Commit deterministic decision and learning trigger —** Input: frozen rules/recommendation/safety facts. Operation: record exact five-way result and emit learning trigger only for eligible closed real-demand stage/tranche. Output: decision/eligibility interface. Test evidence: only CONTINUE progresses; scale requires separate exact authorization; no 600/1,000 path. Failure behavior: further admission remains closed.
<!-- roadmap-task id=WF-08-T04 milestone=M6 depends_on=WF-08-T03 mode=serial locks=workflow-runtime,milestone-gate -->
- [ ] **Retain checkpoint recovery simulation —** Input: SHADOW, REVIEW_20, QUALIFIED_50, authorized scale tranche and safety/incomplete variants. Operation: crash/replay close/freeze/evaluate/decide/trigger boundaries. Output: M6 checkpoint evidence. Test evidence: shadow no-demand trigger, 20/50 limits, scale authorization, no automatic larger tranche, double-decision prevention. Failure behavior: gate blocked.

## Acceptance

- [ ] Stage registry is exactly SHADOW, REVIEW_20, QUALIFIED_50, SCALE_100_TO_300.
- [ ] Shadow cannot masquerade as real demand.
- [ ] Scale requires a signed exact 100–300 authorization after the 50 checkpoint.
- [ ] No 600/1,000 automatic path exists.
- [ ] Replay/pause/late data cannot mutate frozen evidence or duplicate actions.
- [ ] Strategy activation remains checkpoint-boundary-only.
