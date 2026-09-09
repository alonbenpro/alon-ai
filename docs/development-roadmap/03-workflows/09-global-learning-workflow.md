# Global Checkpoint Learning and Boundary Activation Workflow

**Document ID:** WF-09
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-09-T01 -> WF-09-T02 -> WF-09-T03 -> WF-09-T04`; cross-document task Inputs `WF-09-T01 <- WF-08-T03,AGENT-12-T04,AGENT-10-T06,ARCH-03-T01,BACKEND-01-T10`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [runtime selection](00-dbos-selection-and-temporal-fallback.md).
**Outputs:** Finite typed inputs/results, immutable artifact/state handoffs, idempotency and recovery evidence
**Unlocks:** Global strategy promotion/activation/rollback evidence for M9
**Risk:** Critical
**Complexity:** L

## Outcome and timing

One learning run starts only from a closed checkpoint. The newly completed campaign/stage is primary evidence, similar campaigns provide secondary evidence, and relevant history/failures/incidents provide guardrails. Conversation memory is operational state and cannot trigger learning.

## Current repository state and planned surfaces

No product workflow, persistent artifact/aggregate or provider implementation described here exists. Plan `backend/src/alon_ai/workflows/global_learning.py` and application-owned command interfaces, fixture/contract tests and durable recovery simulations. Workflows never mutate ORM rows, call concrete adapters or own Gmail/calendar credentials.

## Exact workflow contract

### Proposal, promotion and activation

| Boundary | Required input | Result and owner |
| --- | --- | --- |
| claim trigger | unique closed checkpoint/bundle ID/hash and applicable agent registry | GlobalLearningState PENDING -> EVALUATING; immutable evidence partition |
| evaluate agents | minimized primary/secondary/guardrail evidence and current configuration/activation | GlobalLearningEngine produces exactly one AgentLearningProposal per applicable agent |
| record result | per-agent evidence and closed result enum | exactly PROMOTE, KEEP, ROLLBACK or INSUFFICIENT_EVIDENCE |
| promotion gate | minimum evidence, immutable lineage, current-version offline comparison, protected holdouts, cross-campaign guardrails, expected metrics/confidence and rollback rules | StrategyActivationService approves/rejects immutable GlobalStrategyPackage |
| schedule activation | approved compatible package and each campaign's checkpoint state | pending StrategyActivation with target boundary/prior activation/generation |
| activate | eligible checkpoint and frozen-cohort CAS | campaign/cohort-specific activation then admission; no process-global mid-cohort pointer change |
| rollback | stored deterioration rule and prior approved compatible version | pause affected future actions, close current checkpoint, validate and activate rollback at boundary; immutable history |

KEEP means evidence supports retention; INSUFFICIENT_EVIDENCE means no justified change. Both perform no strategy mutation; NO_CHANGE is explanatory text only. A proposed PROMOTE cannot bypass offline comparison or holdouts. Safety/legal-policy/suppression/source/commercial bounds are not learnable, and learned messaging cannot add commercial terms to OfferPackage.

The triggering campaign adopts only at its next cohort boundary after CONTINUE. Other active campaigns wait for their own next checkpoint. Future campaigns start with the newest approved package. Active cohorts freeze offer, strategy, qualification criteria, causal variables and evidence definitions. Each individual agent call, policy decision, draft, send, negotiation, booking, checkpoint and learning decision retains exact governing strategy/activation.

### Finite failure, replay and concurrency

Learning run keys bind closed checkpoint, evidence partition hashes, agent registry and strategy version. One result per applicable agent/run is unique. Missing agents, invalid lineage or failed evaluation cannot be silently converted to promotion. Bounded failures retain current strategy and fail the run; a retry creates a linked run, never a new uncontrolled trigger.

Promotion and activation are separate transactions/authorities. Compare-and-swap protects prior activation and checkpoint/control generation against concurrent campaign starts, promotions, rollbacks and dequeue. Outbox replay cannot duplicate package promotion or activate twice. A pause preserves proposals/evidence; resume revalidates eligibility and does not regenerate accepted paid results.

Stored deterioration rules immediately block affected future actions. During an active cohort, rollback waits for checkpoint closure and remains blocked if compatibility/evidence fails. Historical action attribution, prior checkpoints and promoted package bytes are never rewritten. Global metrics use approved minimized transforms and never raw contact/message/calendar content or sensitive inferred attributes.

## Ordered implementation tasks

<!-- roadmap-task id=WF-09-T01 milestone=M6 depends_on=WF-08-T03,AGENT-12-T04,AGENT-10-T06,ARCH-03-T01,BACKEND-01-T10 mode=parallel locks=workflow-runtime,agent-artifacts -->
- [ ] **Encode checkpoint-only learning trigger —** Input: closed checkpoint/bundle and GlobalLearningEngine contract. Operation: pin primary/secondary/guardrail evidence and applicable-agent set. Output: finite learning run contract. Test evidence: open checkpoint, duplicate trigger, missing agent and invalid evidence denial. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-09-T02 milestone=M6 depends_on=WF-09-T01 mode=parallel locks=workflow-runtime,agent-artifacts -->
- [ ] **Implement deterministic proposal gate —** Input: AgentLearningProposal and StrategyActivationService interface. Operation: validate exact results, minimum evidence, offline/holdout/transfer gates and immutable bounds. Output: approved/rejected GlobalStrategyPackage handoff. Test evidence: weak evidence, unsafe mutation and self-certified promotion failures. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-09-T03 milestone=M6 depends_on=WF-09-T02 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Implement campaign-boundary activation and rollback —** Input: approved package, checkpoint decisions and stored rollback rule. Operation: CAS activation only at eligible campaign boundary; block/pause/close before rollback. Output: StrategyActivation and preserved historical lineage. Test evidence: mid-cohort race, cross-campaign timing, future initialization and rollback compatibility. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-09-T04 milestone=M6 depends_on=WF-09-T03 mode=serial locks=workflow-runtime,milestone-gate -->
- [ ] **Retain global learning simulation —** Input: multiple synthetic campaigns and all result/rollback paths. Operation: crash/replay trigger, result, promotion, activation and rollback boundaries. Output: M6 learning/activation evidence. Test evidence: no lost result, duplicate promotion, fifth result or historical mutation. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.

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
