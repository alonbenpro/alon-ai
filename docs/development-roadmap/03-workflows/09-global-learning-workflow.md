# Global Checkpoint Learning and Boundary Activation Workflow

**Document ID:** WF-09
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M6
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-09-T01 -> WF-09-T02 -> WF-09-T03 -> WF-09-T04`; cross-document task Inputs `WF-09-T01 <- WF-08-T03,AGENT-12-T04,AGENT-10-T06,ARCH-03-T01,BACKEND-01-T10`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [PRODUCT-02](../00-product-strategy/02-success-metrics.md), architecture/state docs.
**Outputs:** checkpoint-only learning proposals, global strategy promotion/activation/rollback evidence
**Unlocks:** Global strategy evidence for M9
**Risk:** Critical
**Complexity:** L

## Outcome

One learning run starts only from an eligible **closed real-demand checkpoint**. The newly completed stage/tranche is primary evidence; similar campaigns are secondary; relevant history/failures/incidents are guardrails. Operational conversation memory is not learning.

`SHADOW` is excluded from real-demand learning. It may feed offline agent/provider evaluation, but it cannot teach the production global strategy from supposed market demand.

Eligible pre-revenue learning triggers are closed `REVIEW_20`, closed `QUALIFIED_50`, and each explicitly authorized closed `SCALE_100_TO_300` tranche.

## Proposal, promotion and activation

| Boundary | Required input | Result and owner |
| --- | --- | --- |
| claim trigger | unique eligible closed checkpoint/bundle and applicable agent registry | GlobalLearningState PENDING -> EVALUATING |
| evaluate agents | minimized primary/secondary/guardrail evidence and current config/activation | exactly one AgentLearningProposal per applicable agent |
| record result | per-agent evidence | exactly PROMOTE, KEEP, ROLLBACK or INSUFFICIENT_EVIDENCE |
| promotion gate | minimum evidence, immutable lineage, offline comparison, protected holdouts, transfer/guardrail checks, expected metrics/confidence and rollback rules | StrategyActivationService approves/rejects GlobalStrategyPackage |
| schedule activation | approved compatible package and campaign checkpoint state | pending StrategyActivation at next eligible stage/tranche boundary |
| activate | eligible boundary and frozen-stage CAS | campaign-specific activation before next admission; no mid-stage pointer change |
| rollback | deterioration rule and prior compatible approved version | block future actions, close/pause affected stage, activate rollback at boundary |

`KEEP` and `INSUFFICIENT_EVIDENCE` mutate nothing. Early 20/50 samples are expected to produce insufficient evidence frequently; small sample size is never a reason to force promotion.

Safety/legal-policy/suppression/source/commercial bounds are not learnable. Learned strategy cannot add a new discovery source, permit social scraping, raise a model tier, approve Premium spend, enlarge a launch tranche, change OfferPackage economics, or grant side-effect authority.

## Activation semantics

The triggering campaign adopts an approved strategy only at its next registered boundary after `CONTINUE`. For the transition from `QUALIFIED_50` to `SCALE_100_TO_300`, strategy eligibility and **ScaleAuthorization** are independent gates: a promoted strategy cannot itself authorize scale.

Other active campaigns wait for their own next checkpoint. Future campaigns may start with the newest approved global package. Active stages/tranches freeze offer, strategy, qualification criteria, source/model-routing policy, causal variables and evidence definitions.

Every agent call, model-routing decision, provider call, policy decision, draft, send, negotiation, booking, checkpoint and learning decision retains exact governing strategy/activation.

## Finite failure, replay and concurrency

Learning keys bind closed checkpoint, evidence partition hashes, agent registry and strategy version. Missing agents, invalid lineage, weak evidence or failed evaluation cannot convert to promotion. Retry is linked/idempotent and does not create uncontrolled new triggers.

Promotion and activation are separate authorities. CAS protects current activation and checkpoint/control generation against concurrent stage starts, promotions and rollbacks. Outbox replay cannot promote/activate twice.

Deterioration immediately blocks affected future actions. During an active stage/tranche, rollback waits for closure; historical attribution/checkpoints/package bytes are never rewritten.

## Ordered implementation tasks

<!-- roadmap-task id=WF-09-T01 milestone=M6 depends_on=WF-08-T03,AGENT-12-T04,AGENT-10-T06,ARCH-03-T01,BACKEND-01-T10 mode=parallel locks=workflow-runtime,agent-artifacts -->
- [ ] **Encode checkpoint-only learning trigger —** Input: closed checkpoint/bundle and GlobalLearningEngine contract. Operation: accept only eligible real-demand stage/tranche closures, pin primary/secondary/guardrail evidence and applicable agents; reject SHADOW as demand learning. Output: finite learning run. Test evidence: shadow/open checkpoint, duplicate trigger, missing agent, invalid evidence. Failure behavior: retain current strategy; no mutation.
<!-- roadmap-task id=WF-09-T02 milestone=M6 depends_on=WF-09-T01 mode=parallel locks=workflow-runtime,agent-artifacts -->
- [ ] **Implement deterministic proposal gate —** Input: AgentLearningProposal and StrategyActivationService. Operation: validate results, minimum evidence, offline/holdout/transfer gates and immutable non-learnable bounds including source/model/spend/tranche rules. Output: approved/rejected GlobalStrategyPackage. Test evidence: weak 20/50 evidence, source expansion, Premium escalation, tranche enlargement and self-certified promotion fail. Failure behavior: no strategy mutation.
<!-- roadmap-task id=WF-09-T03 milestone=M6 depends_on=WF-09-T02 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Implement stage-boundary activation and rollback —** Input: approved package, checkpoint decisions, ScaleAuthorization where applicable and rollback rule. Operation: CAS activation only at eligible stage/tranche boundary; scale authorization remains separate. Output: StrategyActivation plus preserved lineage. Test evidence: mid-stage race, 50→scale without authorization, cross-campaign timing, future initialization and rollback compatibility. Failure behavior: activation blocked.
<!-- roadmap-task id=WF-09-T04 milestone=M6 depends_on=WF-09-T03 mode=serial locks=workflow-runtime,milestone-gate -->
- [ ] **Retain global learning simulation —** Input: synthetic campaigns covering shadow/20/50/scale and all results/rollback paths. Operation: crash/replay trigger, proposal, promotion, activation and rollback boundaries. Output: M6 learning evidence. Test evidence: no shadow demand learning, weak-evidence mutation, duplicate promotion, history rewrite or mid-stage activation. Failure behavior: gate blocked.

## Acceptance

- [ ] Learning starts only from eligible closed real-demand checkpoints.
- [ ] Shadow is offline-evaluation evidence, not demand learning.
- [ ] Weak 20/50 evidence naturally yields KEEP/INSUFFICIENT_EVIDENCE.
- [ ] Strategy cannot expand discovery source, model tier/spend, commercial limits or launch tranche.
- [ ] Scale authorization and strategy promotion are independent gates.
- [ ] Activation/rollback remain immutable boundary-only operations.
