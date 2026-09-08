# Campaign, Cohort, and Checkpoint Control Center

**Document ID:** FRONTEND-03
**Status:** Planned product frontend; current implementation is limited to the readiness foundation and generated health client
**Milestone:** M4, M7
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `FRONTEND-03-T01 <- FRONTEND-02-T03,FRONTEND-01-T01; FRONTEND-03-T02 <- FRONTEND-03-T01; FRONTEND-03-T03 <- FRONTEND-03-T02,FRONTEND-01-T05,BACKEND-02-T05,BACKEND-06-T04,BACKEND-05-T04,WF-06-T03; FRONTEND-03-T04 <- FRONTEND-03-T03,BACKEND-01-T09,WF-08-T04; FRONTEND-03-T05 <- FRONTEND-03-T04,BACKEND-06-T04,BACKEND-02-T05,BACKEND-01-T10,WF-09-T04`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Server-authoritative sales control-plane views, guarded typed commands and browser evidence
**Unlocks:** M7 integrated dashboard and M8/M9 acceptance evidence; no live authority
**Risk:** Critical
**Complexity:** XL

## Outcome and planned surfaces

The control center renders the server's finite stage/run state, frozen artifact refs, timers, consumed/reserved budgets, stop reasons and available typed commands. It never advances a workflow from a local progress percentage. Admission uses increments 100/200/300/400 and cumulative maxima 100/300/600/1,000, narrowed by legal/provider/reputation/budget/configuration limits. Display current and prior checkpoints beside the exact cohort ordinal, member_count/hash, eligibility snapshot, offer, strategy, activation, qualification/causal/evidence/metric versions and control generation.

At closure, admission stops before the immutable CheckpointEvidenceBundle freezes. Display exactly CONTINUE, REVISE, KILL, INCONCLUSIVE or SAFETY_STOP. Only CONTINUE can make stages 1–3 eligible for the next registered cohort; at cumulative 1,000 it is a positive terminal result and cannot open a fifth cohort. The UI offers no manual decision substitution or free-form scale action. Late observations appear as separately attributed evidence, never silently alter the frozen bundle.

The strategy panel shows GlobalStrategyPackage lineage, primary triggering stage evidence, secondary similar-campaign evidence, historical failure/incident guardrails, every applicable agent's PROMOTE/KEEP/ROLLBACK/INSUFFICIENT_EVIDENCE, comparison/holdout/transfer summaries, expected metrics/confidence and rollback rule. KEEP and INSUFFICIENT_EVIDENCE perform no mutation; NO_CHANGE is explanatory prose only.

The triggering campaign adopts an approved version only at its next cohort boundary after CONTINUE; other active campaigns wait for their own next checkpoint; future campaigns begin on the newest approved global version. Active cohorts freeze offer, strategy, qualification criteria, causal variables and evidence definitions. A deterioration rule blocks affected future actions immediately, pauses and closes the current checkpoint, then applies compatible rollback at the boundary. requestStrategyRollback follows that same path; it does not update a live pointer. History retains original attribution.

Controls remain safety interventions. Disable/pause acknowledgement reflects server admission fencing, including SendGateway and BookingGateway call entry, and cannot be shown as complete while the command is unresolved. Cancel does not erase possibly-called actions; recovery links preserve their ambiguity.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-03-T01 milestone=M4 depends_on=FRONTEND-02-T03,FRONTEND-01-T01 mode=serial locks=frontend-client -->
- [ ] **Render the accepted experiment chain —** Input: M4 creation receipts and workflow projections. Operation: show idea, research, offer and exact pending provider/consumer states. Output: no-send stage view. Test evidence: missing provider artifact prevents consumer affordance. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-03-T02 milestone=M4 depends_on=FRONTEND-03-T01 mode=serial locks=frontend-client -->
- [ ] **Implement guarded basic controls —** Input: canonical control commands and expected versions. Operation: submit pause/resume/cancel/retry with one command identity and reconcile receipts. Output: M4 safe control component. Test evidence: pause acknowledgement, stale generation and terminal-resume tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-03-T03 milestone=M7 depends_on=FRONTEND-03-T02,FRONTEND-01-T05,BACKEND-02-T05,BACKEND-06-T04,BACKEND-05-T04,WF-06-T03 mode=serial locks=frontend-client -->
- [ ] **Integrate cohort and conversation control —** Input: M7 client, workflow controls and reporting services. Operation: show frozen cohort tuple/membership, automatic-send blocks and INTERESTED/NEGOTIATING/COMMITTED/BOOKED states. Output: campaign control center. Test evidence: cold-reply races and server-only eligibility tests. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-03-T04 milestone=M7 depends_on=FRONTEND-03-T03,BACKEND-01-T09,WF-08-T04 mode=serial locks=frontend-client -->
- [ ] **Render checkpoint evidence and decision —** Input: CheckpointEvaluationService/WF-08 projections. Operation: show bundle/cutoff/denominators/economics and exact five-way result plus next-stage eligibility. Output: checkpoint panel. Test evidence: weak evidence, late evidence and terminal 1,000 cases. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.
<!-- roadmap-task id=FRONTEND-03-T05 milestone=M7 depends_on=FRONTEND-03-T04,BACKEND-06-T04,BACKEND-02-T05,BACKEND-01-T10,WF-09-T04 mode=serial locks=frontend-client -->
- [ ] **Expose strategy activation and rollback —** Input: StrategyActivationService/WF-09 projections. Operation: show per-agent results, evidence, pending campaign boundary and stored rollback actions. Output: global-learning control panel. Test evidence: cross-campaign activation timing and no mid-cohort mutation. Failure behavior: retain canonical blocked/unknown state; no authority, retry, success or admission is inferred.

## Test strategy and acceptance

- [ ] Each displayed state, amount, membership, decision and allowed action comes from an exact generated server DTO and accepted version.
- [ ] Strict unknown-field/schema/version, stale generation, command replay, timeout, auth, privacy and keyboard tests pass against the owning service contract.
- [ ] Automatic sends use fresh ActionAuthorityScopeV1 through SendGateway; calendar writes use BookingGateway. The frontend owns neither capability.
- [ ] Browser fixtures retain safe screenshots/traces, request/response schema hashes, command IDs, server denial evidence and zero unauthorized provider-call counts.
- [ ] This document plans implementation and evidence; it does not claim any product UI or live gate has passed.

## Privacy, failure and recovery

Use redacted no-store projections for conversations/calendar/exception detail and approved minimized learning evidence. Telemetry contains registered outcomes and safe correlation only; no PII/content/credentials, inferred sensitive attributes or provider payloads. Preserve immutable history across refresh, rollback and recovery. Missing contracts block the affected surface until its backend owner supplies them; no browser fallback may invent an operation or bypass policy.

## Dependencies and next deliverable

Consume [canonical sales authority](../00-product-strategy/01-product-scope.md), [API contracts](../06-backend/02-api-contracts.md), [query owners](../06-backend/06-reporting-and-query-services.md), [action authority](../06-backend/05-approval-and-command-handling.md), [booking](../03-workflows/07-booking-workflow.md), [checkpoint evaluation](../03-workflows/08-checkpoint-evaluation-workflow.md) and [global learning](../03-workflows/09-global-learning-workflow.md). Hand retained browser evidence to [TEST-05](../10-testing/05-end-to-end-browser-tests.md); release and live operation remain independently gated.
