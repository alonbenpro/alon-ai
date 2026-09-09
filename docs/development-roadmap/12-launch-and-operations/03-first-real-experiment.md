# Cost-First Controlled Real Sales-Validation Program

**Document ID:** LAUNCH-03
**Status:** Planned roadmap requirements; product implementation and live evidence are not claimed
**Milestone:** M9
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `LAUNCH-03-T01 <- LAUNCH-02-T05,SEC-01-T05,TEST-05-T05,DB-02-T03,BACKEND-05-T05,PROVIDER-01-T03,SEC-04-T02,SEC-05-T03,PRODUCT-02-T04,SEC-04-T05; LAUNCH-03-T02 <- LAUNCH-03-T01,INFRA-03-T06,BACKEND-02-T05,SEC-04-T04,SEC-04-T05; LAUNCH-03-T03 <- LAUNCH-03-T02,SEC-04-T02,BACKEND-05-T03,BACKEND-03-T04,SEC-05-T03,SEC-04-T06,SEC-05-T05,TEST-06-T06; LAUNCH-03-T04 <- LAUNCH-03-T03,INFRA-04-T07,INFRA-05-T07,BACKEND-01-T08,WF-07-T04; LAUNCH-03-T05 <- LAUNCH-03-T04,BACKEND-01-T09,BACKEND-01-T10,WF-08-T04,WF-09-T04`; descriptive sources do not imply whole-document dependencies
**Outputs:** Shadow/20/50/100–300 launch contracts, scope authorizations, retained real-validation evidence, checkpoint/learning boundaries
**Unlocks:** Dependent autonomy gates only; never automatic population expansion
**Risk:** Critical
**Complexity:** L

## Outcome

M9 runs one tightly bounded pre-revenue validation program after earlier technical, legal, provider, security, recovery, conversation, negotiation, booking and learning simulations pass. The objective is to learn whether meetings and revenue/economics justify further outreach without spending for a 1,000-recipient experiment before the product has evidence.

The exact launch order is:

1. `SHADOW` — real pipeline configuration and current provider/model/cost rules, but **no real recipient sends**.
2. `REVIEW_20` — up to 20 businesses, each manually reviewed before admission.
3. `QUALIFIED_50` — up to 50 finally qualified businesses under the same bounded program.
4. `SCALE_100_TO_300` — one operator-signed concrete tranche between 100 and 300 unique businesses, only if meetings plus revenue/paid-commitment or strong contribution-economic evidence justify the spend.

The former automatic 100/200/300/400 progression and 600/1,000 continuation path are removed from the pre-revenue program. Reaching a count never creates authority to enlarge the campaign.

## Entry authority

Program entry binds exact offer/economics/claims, Brave source policy, model-routing policy and tier budgets, release/runtime/schema, strategy activation, one campaign/mailbox/calendar generation, legal/provider/disclosure evidence, metric/evidence definitions, Cloudflare/R2 recovery state, controls/kill generations, signed stage and expiry.

The first real-recipient stage still uses the strictest applicable SEC-04 path. Research/qualification alone is not legal recipient authority. A smaller legal/provider/reputation/budget cap always overrides the stage maximum.

## Stage registry and checkpoints

| Stage | Real population | Entry | Exit |
| --- | ---: | --- | --- |
| `SHADOW` | 0 | M0–M8 + launch simulation gates | provider/model/policy/cost/booking/checkpoint simulation passes; no demand claim; no demand learning |
| `REVIEW_20` | <=20 | shadow exit + current legal/provider/source/recovery evidence | complete outcomes/costs/incidents; checkpoint closes before expansion |
| `QUALIFIED_50` | <=50 | REVIEW_20 checkpoint `CONTINUE` + unchanged/approved program version | all members final-qualified; meetings/bookings/commitments/revenue/cost evidence frozen; checkpoint closes |
| `SCALE_100_TO_300` | exact signed tranche 100..300 | QUALIFIED_50 checkpoint plus explicit `ScaleAuthorization` | terminal pre-revenue checkpoint for this program; no automatic larger stage |

`ScaleAuthorization` binds exact tranche size, population query/membership rules, offer/source/model-routing/strategy versions, provider/model cash cap, operator-time cap, observation window, reason/evidence and expiry. It requires current meetings evidence and either verified revenue/paid-commitment evidence or a retained justification that observed commitments/bookings plus contribution economics warrant the next bounded tranche. It is experiment-scope approval, not per-message approval.

## Bounded live conversation and booking

CampaignAdmissionService validates FINAL qualification, identity, suppression, current Brave source/legal/offer/strategy/stage capacity. ActionAuthorizationService binds exact content/recipient/thread/stage/member/offer/strategy/policy/commercial/expiry/control generation. SendGateway alone writes Gmail; provider uncertainty remains quarantined and reconciled before retry.

Inbound replies stop the cold sequence. Eligible positive/question/objection conversations continue within deterministic round/frequency/time/commercial limits. Rejection closes persuasion. Durable suppression still requires qualifying opt-out/complaint/bounce/legal evidence.

CommercialPolicyEngine alone materializes allowed commercial decisions from OfferPackage. BookingGateway alone performs calendar writes after explicit timezone-aware slot confirmation and reconciles ambiguous outcomes before retry.

## Model and discovery cost controls during launch

Automated discovery uses Brave Place Search only. Social profiles can be manually reviewed evidence, never automated discovery/scraping paths.

Every model call uses current deterministic ModelRoutingPolicy: no AI for deterministic work; Nano for extraction/initial scoring; Mini only for shortlisted leads/registered deeper work; Premium only with exact explicit approval; non-urgent eligible research uses Batch. Stage entry includes provider/model spend caps; unexplained Mini/Premium usage or avoidable real-time cost can block CONTINUE/ScaleAuthorization.

## Checkpoint and global learning

At each real stage/tranche end, CheckpointEvaluationService closes admission and freezes the immutable CheckpointEvidenceBundle. Decision is exactly `CONTINUE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP`.

`SHADOW` is offline/technical evidence and cannot be treated as demand evidence. `REVIEW_20`, `QUALIFIED_50`, and the authorized scale tranche can trigger GlobalLearningEngine from their closed evidence. Every applicable agent receives `PROMOTE|KEEP|ROLLBACK|INSUFFICIENT_EVIDENCE`; weak early samples may not promote. Strategy activation remains boundary-only and never mutates an active stage/tranche.

A `QUALIFIED_50` CONTINUE does not itself open scale: explicit ScaleAuthorization is additionally required. A scale-stage CONTINUE is terminal for the current pre-revenue program and creates no 600/1,000 or new-market authority.

## Public unsubscribe route

The scanner-safe public unsubscribe route remains independently gated and isolated from the operator product. Abort immediately disables product outreach; delivered-recipient opt-out obligations remain supported through the safe public/reply paths as defined by SEC-04. Cloudflare operator Access/Tunnel and the public unsubscribe route are separate policies/hostnames and must not share private-route authority.

## Abort and re-entry

Immediately stop affected admission/actions on wrong identity, duplicate/ambiguous effects, suppression uncertainty, complaint/bounce/legal stop, commercial floor breach, unauthorized source/model escalation, cost/control violation, unsafe provider drift, privacy/audit/recovery failure or public suppression dependency failure. Re-entry requires root-cause resolution, provider reconciliation, current evidence and a separately authorized equal-or-smaller stage/tranche; never revive an aborted membership set by inference.

## Ordered implementation tasks

<!-- roadmap-task id=LAUNCH-03-T01 milestone=M9 depends_on=LAUNCH-02-T05,SEC-01-T05,TEST-05-T05,DB-02-T03,BACKEND-05-T05,PROVIDER-01-T03,SEC-04-T02,SEC-05-T03,PRODUCT-02-T04,SEC-04-T05 mode=serial locks=milestone-gate -->
- [ ] **Freeze cost-first real-program entry —** Input: shadow/technical exits, M0–M8 gates and exact legal/provider/economic/model-routing/source envelope. Operation: bind `SHADOW -> REVIEW_20 -> QUALIFIED_50 -> SCALE_100_TO_300`, stage limits and ScaleAuthorization semantics while controls remain off. Output: signed M9 program scope. Test evidence: legacy 600/1,000 path, missing manual-review stage, larger/unbounded scale, second program and raw identity exposure deny. Failure behavior: no real admission.
<!-- roadmap-task id=LAUNCH-03-T02 milestone=M9 depends_on=LAUNCH-03-T01,INFRA-03-T06,BACKEND-02-T05,SEC-04-T04,SEC-04-T05 mode=serial locks=live-environment,milestone-gate -->
- [ ] **Publish scanner-safe suppression ingress —** Input: signed M9 route authorization, staged Cloudflare edge and current SEC-04 implementation. Operation: activate only exact unsubscribe operations and verify isolation from Cloudflare Access/private product routes. Output: public opt-out capability/recovery evidence. Test evidence: route set equality, scanner write-zero, explicit POST replay and unsafe-dependency fallback. Failure behavior: unpublish route; product off.
<!-- roadmap-task id=LAUNCH-03-T03 milestone=M9 depends_on=LAUNCH-03-T02,SEC-04-T02,BACKEND-05-T03,BACKEND-03-T04,SEC-05-T03,SEC-04-T06,SEC-05-T05,TEST-06-T06 mode=serial locks=gmail-side-effects,milestone-gate -->
- [ ] **Execute bounded current-stage conversations —** Input: fresh authority/offer/strategy/stage/member facts, Brave evidence and model-routing budget. Operation: admit only current signed membership and run initial/reply/negotiation through SendGateway with exact routing/cost attribution. Output: real-stage outcomes. Test evidence: >20 pre-review, >50 pre-scale, unapproved scale, Premium escalation, source/policy denials and final-slot races. Failure behavior: stop/quarantine; no blind retry or extra admission.
<!-- roadmap-task id=LAUNCH-03-T04 milestone=M9 depends_on=LAUNCH-03-T03,INFRA-04-T07,INFRA-05-T07,BACKEND-01-T08,WF-07-T04 mode=serial locks=gmail-side-effects,live-environment,milestone-gate,calendar-side-effects -->
- [ ] **Operate booking, recipient stops, costs and exceptions —** Input: reply/calendar/provider/model observations and controls. Operation: apply cold-stop/suppression, confirmed booking, model/discovery cost monitoring and bounded containment. Output: safe meeting/commercial/cost/incident evidence. Test evidence: booking ambiguity/DST, rejection-vs-opt-out, floor/kill and model-budget races. Failure behavior: stop affected capability and preserve evidence.
<!-- roadmap-task id=LAUNCH-03-T05 milestone=M9 depends_on=LAUNCH-03-T04,BACKEND-01-T09,BACKEND-01-T10,WF-08-T04,WF-09-T04 mode=serial locks=gmail-side-effects,milestone-gate -->
- [ ] **Close stage checkpoints and gate scale/learning —** Input: frozen current-stage outcomes, meetings/revenue/economics, provider/model/operator costs and global-learning owners. Operation: record checkpoint, all-agent learning, and when leaving QUALIFIED_50 require separate ScaleAuthorization before any 100..300 membership creation. Output: immutable decision/package/activation/scale evidence. Test evidence: weak evidence, shadow-as-demand, cross-campaign timing, mid-stage mutation, scale without approval and 600/1,000 admission denial. Failure behavior: next stage remains closed.

## Acceptance

- [ ] Launch order is exactly SHADOW → REVIEW_20 → QUALIFIED_50 → explicitly authorized SCALE_100_TO_300.
- [ ] No automatic 600/1,000 pre-revenue path exists.
- [ ] Only SendGateway/BookingGateway own Gmail/calendar writes.
- [ ] Brave-only automated discovery and deterministic model routing remain enforced.
- [ ] Weak evidence cannot expand population or mutate global strategy.
- [ ] Every stage/tranche retains exact membership, cost, offer, strategy and checkpoint attribution.
