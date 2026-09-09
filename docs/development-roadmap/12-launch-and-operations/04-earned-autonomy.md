# Earned Bounded Autonomous Sending, Negotiation, and Booking

**Document ID:** LAUNCH-04
**Status:** Planned roadmap requirements; product implementation and live evidence are not claimed
**Milestone:** M9
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `LAUNCH-04-T01 <- AGENT-01-T01,PROVIDER-02-T01,PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,PROVIDER-06-T01,SEC-05-T03,WF-02-T05,WF-03-T05,WF-04-T05,PROVIDER-01-T01; LAUNCH-04-T02 <- LAUNCH-04-T01; LAUNCH-04-T03 <- LAUNCH-04-T02,LAUNCH-03-T05,AGENT-10-T05,LAUNCH-02-T05,OBS-04-T05,OBS-05-T06,INFRA-02-T04,BACKEND-01-T08,BACKEND-01-T10,WF-09-T04; LAUNCH-04-T04 <- LAUNCH-04-T03; LAUNCH-04-T05 <- LAUNCH-04-T04`; descriptive sources do not imply whole-document dependencies
**Outputs:** Bounded autonomous execution contract, cost/model/source controls, retained authority and rollback evidence
**Unlocks:** No larger automatic recipient population; future expansion requires a new explicitly authorized program
**Risk:** Critical
**Complexity:** L

## Outcome

Earned autonomy permits deterministic in-envelope writing, sending, reply handling, bounded negotiation, explicitly confirmed booking, checkpoint evaluation and checkpoint-only global learning **inside the population already authorized by LAUNCH-03**. It does not create a new scale stage.

The launch ladder relevant to real demand is cost-first: `SHADOW -> REVIEW_20 -> QUALIFIED_50 -> SCALE_100_TO_300`. The 100–300 stage exists only when an exact operator-signed ScaleAuthorization was already earned from the 50-stage evidence. There is no pre-revenue automatic 600/1,000 continuation path.

## Evidence ladder before autonomy

1. synthetic agent pipeline;
2. recorded provider/model/discovery fixtures;
3. owned test-inbox conversations;
4. simulated objections and negotiation;
5. test calendar bookings;
6. checkpoint/global-learning simulation;
7. shadow mode with current cost/source/model policies and no real sends;
8. manually reviewed real businesses (`REVIEW_20`);
9. final-qualified real businesses (`QUALIFIED_50`);
10. optional explicitly authorized `SCALE_100_TO_300` tranche when meetings/revenue/economics justify it;
11. earned autonomous operation only within the currently authorized stage/tranche.

Earlier phases never count as real demand. Missing/unavailable evidence blocks the next phase. M1/M6/M8/M9 safety/legal/provider/recovery gates remain independently mandatory.

## Frozen autonomous envelope

Autonomy binds exact campaign/program, stage/tranche and membership hash; OfferPackage/economics/claim hashes; Brave Place Search source policy; ModelRoutingPolicy; agent configurations; GlobalStrategyPackage/StrategyActivation; mailbox/calendar identity; legal-policy evidence; finite conversation/frequency/rate/provider/model/cash/time caps; checkpoint/evidence definitions; and rollback target.

A running stage/tranche freezes those values. A tighter kill/cost limit may stop work immediately but no provider/agent/browser can expand scope or change strategy halfway through the active membership set.

## What bounded execution permits

| Responsibility | Agent role | Deterministic owner/bound |
| --- | --- | --- |
| discovery | propose from approved observations | automated v1 source is Brave Place Search only; BusinessIdentityService/QualificationService own accepted identity/preliminary qualification |
| model work | request registered task capability | ModelRoutingPolicy chooses NO_AI/NANO/MINI/PREMIUM and REALTIME/BATCH; agents cannot escalate tier |
| writing | evidence-backed draft/response | EmailWritingAgent has no Gmail credentials; ActionAuthorizationService/SendGateway own final authority |
| negotiation | propose supported objective/options | CommercialPolicyEngine enforces price/margin/scope/terms/budget truth |
| booking | propose qualified call objective | BookingGateway alone writes calendar after explicit slot/timezone confirmation |
| checkpoint | evaluate frozen evidence | CheckpointEvaluationService owns final decision and stage closure |
| learning | analyze closed checkpoint evidence | StrategyActivationService owns PROMOTE/KEEP/ROLLBACK/INSUFFICIENT_EVIDENCE and boundary-only activation |
| scale | none | ScaleAuthorization is operator-signed experiment-scope authority; no agent/checkpoint result alone creates a 100–300 population |

Premium models are default-denied and require exact bounded approval. Non-urgent eligible research uses Batch when supported. Avoidable Mini/Premium or real-time usage is a cost/economic signal and may block further scale.

## Permanent boundaries

Autonomy never grants direct agent/provider Gmail/calendar writes, arbitrary scraping/social automation, fabricated claims/urgency/budget, below-floor pricing, legal-term mutation, suppression deactivation, uncontrolled prompt rewriting, budget/cap increase, public-route changes, release/restore cutover, incident closure, payment collection, or a new experiment/population.

A clear rejection closes persuasion; an ordinary reply stops the cold sequence; durable suppression remains independently evidenced. BOOKED terminates sales outreach for that buying path as defined by the conversation state machine.

## Learning and rollback

Closed `REVIEW_20`, `QUALIFIED_50`, and authorized scale-tranche checkpoints can trigger global learning. `SHADOW` contributes offline evaluation evidence only. Weak evidence must resolve to KEEP/INSUFFICIENT_EVIDENCE, not a strategy mutation.

The triggering program adopts an approved strategy only at a next eligible stage/tranche boundary after continuation/scope authority. Other active campaigns wait for their own checkpoint; future campaigns may use the newest approved baseline. Deterioration blocks future actions and activates compatible rollback only at a safe boundary without rewriting history.

## Cost deterioration

Immediately stop/pause when model/discovery/provider spend exceeds registered caps, Premium is called without approval, Mini lacks shortlist evidence, batch-only work is repeatedly forced real-time without retained justification, Brave discovery economics deteriorate beyond the registered threshold, or acquisition economics become incompatible with the stage budget. Cost stops cannot be overridden by model confidence.

## Ordered implementation tasks

<!-- roadmap-task id=LAUNCH-04-T01 milestone=M9 depends_on=AGENT-01-T01,PROVIDER-02-T01,PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,PROVIDER-06-T01,SEC-05-T03,WF-02-T05,WF-03-T05,WF-04-T05,PROVIDER-01-T01 mode=serial locks=milestone-gate -->
- [ ] **Freeze bounded autonomy contract —** Input: canonical authorities and cost-first launch ladder. Operation: register exact stage/tranche scope, Brave source, model-routing tiers/modes, finite envelopes and immutable evidence population. Output: deny-by-default autonomous execution contract. Test evidence: legacy 600/1,000 expansion, new source/program, unregistered action, model-tier escalation and cap expansion deny. Failure behavior: affected capability remains off.
<!-- roadmap-task id=LAUNCH-04-T02 milestone=M9 depends_on=LAUNCH-04-T01 mode=serial locks=milestone-gate -->
- [ ] **Calculate evidence and economics without selection bias —** Input: pre-registered stage population and all admitted outcomes/provider/model/operator costs. Operation: verify set equality, missing evidence, meetings/revenue/commitments, contribution economics, routing mix and uncertainty. Output: reviewable autonomy/scale evidence calculation. Test evidence: post-hoc exclusion, stale cost, shadow-as-demand, unexplained Premium/Mini and missing revenue/economic evidence cannot pass. Failure behavior: no authority increase.
<!-- roadmap-task id=LAUNCH-04-T03 milestone=M9 depends_on=LAUNCH-04-T02,LAUNCH-03-T05,AGENT-10-T05,LAUNCH-02-T05,OBS-04-T05,OBS-05-T06,INFRA-02-T04,BACKEND-01-T08,BACKEND-01-T10,WF-09-T04 mode=serial locks=milestone-gate,calendar-side-effects -->
- [ ] **Enable only earned in-envelope execution —** Input: current LAUNCH-03 stage/tranche authority and retained safety/recovery/strategy evidence. Operation: permit deterministic actions only for exact current membership, offer, strategy, source and model-routing envelope. Output: bounded autonomous sending/negotiation/booking eligibility. Test evidence: no per-message gate, sole gateways intact, no mid-stage mutation, no population expansion and no Premium bypass. Failure behavior: affected action denied/quarantined.
<!-- roadmap-task id=LAUNCH-04-T04 milestone=M9 depends_on=LAUNCH-04-T03 mode=serial locks=security-runtime,milestone-gate -->
- [ ] **Prove permanent authority boundaries —** Input: call/import/tool/HTTP graphs and current controls. Operation: exercise direct/indirect writes, fabricated economics/confirmation, source/social/model-routing/legal/suppression/strategy bypass attempts. Output: zero unauthorized effects with exact audit reasons. Test evidence: agents/browser/provider wrappers cannot bypass deterministic owners. Failure behavior: stop capability and retain incident evidence.
<!-- roadmap-task id=LAUNCH-04-T05 milestone=M9 depends_on=LAUNCH-04-T04 mode=serial locks=ci-release,milestone-gate -->
- [ ] **Operate automatic deterioration and boundary rollback —** Input: stored safety/cost/performance rules, action attribution and prior compatible package. Operation: block future actions, pause/close current stage if required, activate rollback at boundary and preserve history. Output: automatic rollback/re-entry evidence. Test evidence: cross-campaign race, weak evidence, model/discovery cost deterioration, crash/replay and incompatible rollback remain safe. Failure behavior: stay blocked; no automatic larger stage.

## Acceptance

- [ ] Autonomous authority is limited to the current signed cost-first stage/tranche.
- [ ] No automatic 600/1,000 or unregistered next population exists.
- [ ] Brave-only automated discovery, cost-first model routing and premium approval remain enforced.
- [ ] Only SendGateway and BookingGateway perform external writes.
- [ ] Weak evidence cannot promote strategy or increase population.
- [ ] Cost/safety deterioration can stop and roll back without rewriting historical attribution.
