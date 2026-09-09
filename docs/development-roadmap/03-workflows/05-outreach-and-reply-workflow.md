# Autonomous Email, Reply Evaluation, and Bounded Negotiation Workflow

**Document ID:** WF-05
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-05-T01 -> WF-05-T02 -> WF-05-T03 -> WF-05-T04 -> WF-05-T05 -> WF-05-T06`; cross-document task Inputs `WF-05-T01 <- TEST-03-T03,SEC-05-T03,BACKEND-05-T06,PROVIDER-01-T03,SEC-02-T04,LAUNCH-01-T03,WF-00-T04,AGENT-08-T04,BACKEND-04-T04; WF-05-T02 <- BACKEND-05-T03,WF-04-T04,AGENT-07-T04; WF-05-T03 <- SEC-05-T03,BACKEND-04-T04; WF-05-T04 <- PROVIDER-02-T04,AGENT-08-T04,SEC-05-T02; WF-05-T05 <- BACKEND-04-T05,SEC-05-T04,WF-06-T04,LAUNCH-01-T03; WF-05-T06 <- TEST-04-T06,WF-07-T04,WF-08-T04,WF-09-T04`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [runtime selection](00-dbos-selection-and-temporal-fallback.md).
**Outputs:** Finite typed inputs/results, immutable artifact/state handoffs, idempotency and recovery evidence
**Unlocks:** M6 owned-resource evidence and later earned M9 autonomy
**Risk:** Critical
**Complexity:** L

## Outcome and timing

M6 proves automatic draft -> deterministic policy -> guarded send and finite inbound-response/negotiation loops using operator-owned inboxes. TEST_INBOX_SENDING is scoped to the exact owned alias allowlist while PRODUCT_OUTREACH stays false. Real campaigns require later launch, source/legal/provider/deliverability/budget evidence.

## Current repository state and planned surfaces

No product workflow, persistent artifact/aggregate or provider implementation described here exists. Plan `backend/src/alon_ai/workflows/outreach.py` and application-owned command interfaces, fixture/contract tests and durable recovery simulations. Workflows never mutate ORM rows, call concrete adapters or own Gmail/calendar credentials.

## Exact workflow contract

### Exact automatic send and conversation sequence

| Step | Inputs / fresh check | Durable result and owner |
| --- | --- | --- |
| write | OfferPackage, dossier, FINAL qualification, strategy/activation, full sanitized thread; responses require exact ReplyEvaluation objective and NegotiationDecision | EmailWritingAgent produces ConversationStrategy and EmailDraft; deterministic services validate/accept |
| authorize | exact content/materialization hash, recipient/thread, campaign/cohort/member, offer, strategy, commercial/policy facts, expiry and current generation | ActionAuthorizationService creates immutable ActionAuthorityScopeV1; no routine manual approval |
| record intent | accepted exact scope and immutable mailbox/RFC identity | consume authorization once; durable SendIntent plus cost reservation/queue result |
| final admission | fresh suppression, signals, identity, cohort/capacity, thread/counters, draft freshness, claims, commercial bounds, jurisdiction/provider policy, budgets/rates and all kill switches | SendGateway records fresh SEND decision and consumed mailbox rate reservation with attempt before network |
| send/reconcile | only SendGateway receives GmailWritePort | positive provider evidence -> SENT; uncertain acceptance -> AMBIGUOUS/RECONCILING, quarantined |
| ingest inbound | complete bounded thread observations and mailbox history identity | atomic observation/reply, cold-sequence cancellation, stale-authority invalidation, events/outbox and cursor |
| evaluate reply | accepted offer/strategy/draft, full sanitized thread, current limits and evidenced signals | ReplyEvaluation gives exact next objective; CommercialPolicyEngine computes allowed NegotiationDecision |
| respond | accepted permitted objective/terms, nonterminal state and remaining limits | writer creates new draft; fresh authorization and gateway checks repeat |
| hand off | qualified buying intent and explicit CALL_NEXT_STEP agreement | accepted BookingIntent via WF-07; no purchase acceptance is required to book a discussion |
| close | sample/window/terminal conversation or checkpoint stop | close admission and enter WF-08; effects stay reconciled or explicitly quarantined |

The authorization and final SEND share the immutable action scope/hash but use independent fresh facts hashes. Every call/decision/draft/send/negotiation binds exact OfferPackage, GlobalStrategyPackage and StrategyActivation. Cohort admission binds the exact increment SHADOW/REVIEW_20/QUALIFIED_50/SCALE_100_TO_300 and cumulative cap 0/20/50/explicitly-authorized-100-to-300. Follow-up messages stay with the same original member and never increase the unique delivered-recipient denominator. Prefetch cannot cross a checkpoint or bypass a kill switch.

Any inbound reply stops the cold sequence and cancels only provably uncalled cold work. It does not automatically create suppression. RecipientSignalSuppressionService requires DurableSuppressionTriggerV1 evidence: EXPLICIT_OPT_OUT, COMPLAINT, HARD_BOUNCE, SOFT_BOUNCE_LIMIT_REACHED or LEGAL_STOP with known identity/scope. Clear offer rejection closes persuasion; it cannot be relabeled as a negotiable objection. Positive intent, questions and genuine objections may enter INTERESTED/NEGOTIATING and the bounded response loop. Ambiguity pauses; DECLINED, OPTED_OUT, CLOSED end the loop; BOOKED ends sales outreach. New inbound messages cannot erase a terminal stop.

### Commercial boundaries and finite reply control

CommercialPolicyEngine calculates taxes, fees, delivery cost, FX, rounding, discounts and contribution margin from stored versions. Allowed objectives explain the offer, answer supported objections, select approved variants/pilots/discount bands, adjust allowed timing/bundles/payment schedules, ask missing decision information or propose a call. The writer receives exact objective/claim/proposal references.

STATED/INFERRED/UNKNOWN budget assertions retain currency/range/span/confidence/time; only STATED can satisfy a stated-budget condition. Below-floor price/margin, unauthorized scope/deliverables/legal terms, unsupported guarantees, invented urgency/facts/familiarity and unaccepted commitments fail closed into exceptions. PURCHASE_PROPOSAL acceptance and CALL_NEXT_STEP evidence are distinct. A call agreement does not prove purchase acceptance or slot confirmation.

The pre-run policy registers positive maximum rounds/messages, frequency limits and finite response/negotiation windows. Persist counters and deadlines with conversation/control version. Out-of-order/duplicate replies cannot add a round twice, and a concurrent newer reply invalidates queued stale responses. Exhaustion terminates or pauses according to the stored rule; no timer restarts the cold sequence or manufactures a new proposal.

### Durable queues, ambiguity and recovery

Finite IDs bind campaign/cohort/member/conversation, input snapshot and action/attempt identities. `alon-ai-outreach-v1` and `alon-ai-send-v1` begin at concurrency 1; initial M6 send limiter is 1 start per 30 seconds, with stricter current policy taking precedence. Reconciliation uses read-only bounded runs; mailbox sync serializes per mailbox.

An attempt and rate consumption commit before Gmail call. Crash/timeout/malformed success/connection loss enters ambiguity. Zero/multiple/conflicting Sent results never prove non-send or allow retry; 300 seconds is an escalation threshold only. Preserve consumed leases and immutable mailbox/RFC identity until positive reconciliation. Only explicit provider rejection or signed pre-write proof can reach FAILED_RETRYABLE, under immutable max_attempts/deadline and fresh SEND checks; exhaustion becomes FAILED_PERMANENT.

At every write boundary, pause/cancel closes admission before acknowledgement, invalidates generation and cancels only provably uncalled work. Started writes retain their provider truth and reconciliation path. Atomic history/cold-stop/cursor failure rolls back the whole page and closes unsafe admission; model failure cannot delay a deterministic opt-out or erase thread history.

## Ordered implementation tasks

<!-- roadmap-task id=WF-05-T01 milestone=M6 depends_on=TEST-03-T03,SEC-05-T03,BACKEND-05-T06,PROVIDER-01-T03,SEC-02-T04,LAUNCH-01-T03,WF-00-T04,AGENT-08-T04,BACKEND-04-T04 mode=serial locks=gmail-side-effects,workflow-runtime,live-environment -->
- [ ] **Bind isolated M6 campaign entry —** Input: signed owned-project/mailbox/alias caps and complete pilot authorization. Operation: verify controls/rates/launch evidence and initialize finite cohort/conversation context. Output: owned-inbox campaign fixture. Test evidence: real recipient, missing evidence and stale control denials. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-05-T02 milestone=M6 depends_on=WF-05-T01,BACKEND-05-T03,WF-04-T04,AGENT-07-T04 mode=parallel locks=workflow-runtime,backend-domain -->
- [ ] **Implement automatic draft and action authorization —** Input: accepted writer artifacts and action/policy service interfaces. Operation: freeze content/recipient/thread/offer/activation and create deterministic scope plus intent. Output: authorized immutable send chain. Test evidence: content/phase/thread/offer splice and no per-message approval path. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-05-T03 milestone=M6 depends_on=WF-05-T02,SEC-05-T03,BACKEND-04-T04 mode=serial locks=gmail-side-effects,workflow-runtime,live-environment -->
- [ ] **Connect sole gateway and reconciliation —** Input: durable intent/current policy/rate reservation. Operation: execute owned-inbox send and reconcile all ambiguous boundaries. Output: idempotent attempt/result trace. Test evidence: kill matrix, negative-search quarantine and retry exhaustion. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-05-T04 milestone=M6 depends_on=WF-05-T03,PROVIDER-02-T04,AGENT-08-T04,SEC-05-T02 mode=serial locks=gmail-side-effects,workflow-runtime -->
- [ ] **Implement finite reply and negotiation loop —** Input: complete sanitized thread, reply objective and CommercialPolicyEngine interface. Operation: stop cold sequence, apply exact suppression predicates, compute permitted proposal, invoke writer and fresh guarded send. Output: bounded conversation/negotiation history. Test evidence: positive response, objection/rejection, budget/floor/terminal limits and stale response races. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-05-T05 milestone=M6 depends_on=WF-05-T04,BACKEND-04-T05,SEC-05-T04,WF-06-T04,LAUNCH-01-T03 mode=serial locks=gmail-side-effects,milestone-gate,live-environment -->
- [ ] **Verify controls and recovery —** Input: owned-inbox traces and immutable action lineage. Operation: exercise pause/cancel/restart/disable at every durable boundary. Output: M6 control/recovery evidence. Test evidence: no lost reply, repeated round, duplicate send or premature terminal effect. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-05-T06 milestone=M6 depends_on=WF-05-T05,TEST-04-T06,WF-07-T04,WF-08-T04,WF-09-T04 mode=serial locks=milestone-gate -->
- [ ] **Retain full M6 conversation-to-learning gate —** Input: inbox, negotiation, test booking and checkpoint/global-learning simulations. Operation: bind all retained contract/recovery evidence and costs. Output: complete synthetic/owned-resource gate bundle. Test evidence: end-to-end finite campaign simulation; no real demand claim. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.

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
