# Risk Register and Kill Criteria

**Document ID:** PRODUCT-03
**Status:** Planned gate definition
**Milestone:** M0, M1, M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PRODUCT-03-T01 -> PRODUCT-03-T02 -> PRODUCT-03-T03 -> PRODUCT-03-T04`; cross-document task Inputs `PRODUCT-03-T01 <- PRODUCT-01-T02,PRODUCT-02-T01; PRODUCT-03-T03 <- WF-01-T03; PRODUCT-03-T04 <- SEC-05-T04,OBS-05-T02,OBS-05-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): [PRODUCT-01 scope](01-product-scope.md) and [PRODUCT-02 metrics](02-success-metrics.md)
**Outputs:** Ranked risks, deterministic stop triggers, recovery rules, and engine/product kill decisions
**Unlocks:** M1 DBOS production-acceptance gate
**Risk:** Critical
**Complexity:** M

## Outcome and timing

This register makes stopping cheaper than rationalizing. A solo operator cannot absorb a reputation incident, uncontrolled cloud bill, credential leak, or week of infrastructure theater. M0 therefore pre-commits the project to pause, rollback, replace, park, or kill actions before sunk cost distorts the decision.

## Current repository state

Implemented controls are limited to outreach defaulting off, complete Gmail configuration being required before the flag can be enabled, secret-aware logging and scanning, a deterministic `SendGateway` contract, and unit tests proving disabled/denied requests do not reach the provider mock. There is no real provider, suppression list, policy implementation, kill switch, durable idempotency record, encryption, authentication, incident runbook, budget ledger, or regulatory decision record.

The existing guard is useful but insufficient: a Boolean environment flag cannot stop an in-flight send, reconcile an ambiguous Gmail outcome, enforce a campaign cap, or prove who authorized an action.

## Risk scale

`Critical` means one occurrence can create external harm, credential/data compromise, uncontrolled spend, or irrecoverable audit uncertainty. `High` threatens the experiment decision or consumes material solo-operator capacity. `Medium` is recoverable within one milestone without external harm. `Low` is local inconvenience.

## Risk register

| ID | Risk | Level | Prevention | Detection / trigger | Mandatory response |
| --- | --- | --- | --- | --- | --- |
| R01 | duplicate or unintended Gmail send | Critical | durable idempotency, deterministic policy, test-recipient allowlist, `SendGateway`, permanent ambiguity quarantine | any recipient receives duplicate content for one intent; any send lacks intent/audit record | engage global kill switch, revoke queue authority, reconcile all in-flight intents, preserve evidence, return to M1/M6 |
| R02 | Gmail call succeeds but local completion is absent | Critical | stable RFC message identifier, idempotency key, `AMBIGUOUS` state, positive-evidence Sent reconciliation; negative search never authorizes retry | timeout/crash between provider acceptance and durable completion | prohibit retry/replacement indefinitely, reconcile, require operator investigation for zero/multiple/conflicting candidates |
| R03 | selected DBOS runtime fails production acceptance | Critical | DBOS kill-point spike and acceptance scorecard | failed restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency | migrate to Temporal before product workflows |
| R04 | suppression, jurisdiction, campaign, budget, rate, or kill policy bypass | Critical | versioned deterministic policy composition rechecked immediately before provider call | any mismatch between policy facts and actual send | stop all sends, classify incident, correct data/policy, replay policy against intents before re-enable |
| R05 | Gmail OAuth or provider credential compromise | Critical | encryption at rest, least scopes, private access, rotation and revocation runbook | secret scan, unauthorized access, provider alert, unexplained token use | revoke tokens, disable provider, rotate secrets, assess affected data and legal obligations |
| R06 | personal or message data leaks through logs/artifacts | Critical | field allowlists, redaction, least retention, sanitized exception paths | secret/PII scan or incident alert finds disallowed content | stop affected telemetry/provider path, preserve restricted evidence, purge according to approved incident procedure |
| R07 | outreach violates applicable law or provider policy | Critical | jurisdiction record, documented lawful basis/rules, suppression, honest identity, protected legal-policy review, qualified advice for uncertainty | unknown jurisdiction, missing required identity/opt-out, complaint, provider warning, unresolved legal interpretation | block that jurisdiction/campaign; do not infer compliance from software checks |
| R08 | agent invents evidence or misleading claims | High | retrievable citations, claim-level provenance, offline adversarial evals, deterministic evidence validation | unsupported material claim or altered quotation | reject artifact version, prevent promotion/sending, expand fixture and re-evaluate |
| R09 | wrong business is matched or duplicated | High | deterministic normalization/dedupe, source identity, conflict review | duplicate eligible lead or ambiguous identity | quarantine affected leads; never merge automatically when evidence conflicts |
| R10 | product looks busy but produces no demand evidence | High | pre-registered sample/decision rule and `INCONCLUSIVE` outcome | M9 kill condition or repeated revise cycles without stronger evidence | kill or park the offer; do not add providers/features to manufacture activity |
| R11 | delivery economics are negative | High | price and direct-time baseline, cost caps, contribution-margin query | projected contribution margin <= `0` at tested price | kill or redesign delivery/price before scaling |
| R12 | provider/model cost escapes budget | High | per-run and experiment caps, reservation before calls, authoritative cost reconciliation | cap reached, cost feed absent, or unexplained variance > `10%` | pause new calls, reconcile ledger, require explicit new budget version |
| R13 | solo operator becomes the hidden bottleneck | High | measure review/recovery/delivery time, bounded concurrent work, usable runbooks | operator-hours cap reached or unresolved critical queue grows beyond one session | pause intake/sends; simplify workflow before adding automation |
| R14 | backup exists but cannot restore | Critical | encrypted automated backup plus fresh-target restore drill | restore or integrity check fails | block M9/deployment promotion, repair and repeat drill |
| R15 | dashboard hides stale or failed state | High | freshness markers, immutable history, no optimistic success for external actions | UI disagrees with event/system-of-record query | stop affected commands, expose degraded status, recover from backend evidence |
| R16 | architecture scope creep delays learning | High | vertical gates and explicit non-goals | work item cannot name the next gate/evidence it serves | delete or park the work item; return to critical path |
| R17 | later cohort opens without sufficient evidence | High | immutable four-stage rule and immutable checkpoint decision before admission | any Stage 2-4 member is admitted without the immediately prior authoritative `CONTINUE` | stop admission/sending, close the stage as `SAFETY_STOP`, reconcile all affected work, open an incident |
| R18 | recipient is reused across stages or caps race | Critical | unique experiment-version recipient identity plus serializable stage/cumulative admission | duplicate identity, stage increment exceeded, or cumulative count above `1,000` | engage global kill switch, reconcile attempts, preserve evidence, require root-cause review before a new version |
| R19 | causal variables or attribution change during a cohort | High | freeze offer/strategy/qualification/allocation/evidence definitions; checkpoint-only activation | governing version or causal variable changes before checkpoint closure | pause affected actions, close checkpoint with supported decision, preserve attribution; do not pool contaminated observations |
| R20 | negotiation violates price, margin, scope, or payment bounds | Critical | sole immutable `OfferPackage`; pure `CommercialPolicyEngine`; stored cost/FX/rounding versions | unauthorized deliverable/term, below-floor result, stale offer, or model-calculated commercial authority | reject action, pause conversation, open incident, replay boundary vectors |
| R21 | inferred budget or invented urgency/familiarity becomes a claim | High | `STATED\|INFERRED\|UNKNOWN` assertions with spans/confidence; evidence-backed writing | inferred/unknown budget satisfies stated condition or unsupported assertion reaches draft | reject artifact/action; retain minimized evidence and expand evaluations |
| R22 | bounded conversation becomes harassment or an endless loop | Critical | any reply stops cold sequence; explicit terminal signals; round/frequency/message/window limits | post-rejection/opt-out response, exceeded limit, ambiguous intent, or stale thread action | close cold admission and rejected persuasion; suppress only when PRODUCT-01's [DurableSuppressionTriggerV1](01-product-scope.md#rejection-and-durable-suppression-trigger) passes; pause ambiguity and cancel provably-uncalled work |
| R23 | booking creates wrong, duplicate, or unconfirmed calendar event | Critical | separate read/write ports, sole `BookingGateway`, explicit slot confirmation, identity/timezone/availability recheck | unexpected attendee/timezone, duplicate event, DST mismatch, provider conflict, or notification surprise | stop calendar writes, reconcile before retry, correct through audited idempotent reschedule/cancel |
| R24 | incomplete or biased checkpoint evidence promotes a harmful strategy | High | closed immutable checkpoint bundle; primary/secondary/guardrail evidence; minimum evidence, holdouts and cross-campaign tests | weak evidence mutates production, invalid lineage, untested package, or transfer regression | reject promotion; use `INSUFFICIENT_EVIDENCE` when warranted; trigger stored rollback rule on deterioration |
| R25 | strategy activation or rollback races running actions | Critical | `CHECKPOINT_ONLY`, generation checks, immutable activation and action attribution | mid-cohort mutation, wrong-campaign activation, historical reattribution, or stale authorized write | pause affected actions, close checkpoint, revoke stale authority, activate rollback only for future actions |
| R26 | scraped web/email instructions escape tool or privacy boundaries | Critical | untrusted-input isolation, typed snapshots, least-authority tools, provenance, redaction, deterministic post-model validation | injected command influences a provider write or raw contact/message/calendar data reaches telemetry/global learning | disable affected path, retain restricted incident evidence, repair transforms/capabilities and rerun adversarial fixtures |
| R27 | source adapter or learning retention exceeds approved purpose | Critical | source-specific contracts and per-field purpose/access/retention/deletion/backup rules | unreviewed source, fabricated linkage, expired sensitive record, or unminimized global evidence | stop collection/learning, quarantine records, execute approved deletion/restore controls |

## Immediate global kill triggers

Any trigger below sets planned `system_controls` outreach authority to `DISABLED`, blocks new send intents and provider calls, and requires an incident record before re-enable:

- any real recipient outside the approved experiment/allowlist is contacted;
- any uncontrolled duplicate send or suppression violation occurs;
- any provider call occurs after a confirmed global stop or campaign cancellation;
- Gmail/OAuth credentials may be compromised;
- required send audit or reconciliation records cannot be trusted;
- applicable jurisdiction or provider-policy requirements are unresolved for queued recipients;
- authoritative spend cannot be determined or a hard budget cap is exceeded; or
- monitoring required to observe sends, policy decisions, and reconciliation is unavailable;
- a stage admits above its exact `100/200/300/400` increment, cumulative delivery exceeds `1,000`, or a recipient identity is reused across stages; or
- any later cohort is admitted without the immediately prior authoritative `CONTINUE` checkpoint;
- a commercial action violates the accepted offer or a send/booking uses stale offer/strategy/control authority;
- calendar credentials are compromised or an event is created without explicit confirmation; or
- strategy activation mutates a running cohort or corrupts historical attribution.

The equivalent calendar/provider/conversation controls stop their write paths before acknowledgement. An incident pause is not permission to retry an unknown external outcome. Positive replies alone stop cold outreach and do not trigger global suppression. Healthy unsubscribe obligations remain available in `SUPPRESSION_ONLY`; unsafe public/suppression processing follows `DISABLED_UNSAFE` and its retained incident/alternate-channel procedure.

In M1, the equivalent stop is implemented in the disposable isolated harness rather than a product control table; it may send only to operator-owned test inboxes. This does not authorize an M1 product schema or product outreach. Product outreach remains disabled until both M1 and M6 evidence gates pass.

## DBOS production-acceptance failure criteria

DBOS is selected, but production use remains blocked. M1 disqualifies DBOS and mandates Temporal if it cannot reproducibly demonstrate every item below:

1. restart recovery at every defined worker-termination kill point;
2. cancellation with unambiguous pause/resume behavior and no post-cancel provider call;
3. permanent quarantine and positive-evidence reconciliation of every ambiguous Gmail outcome through the outbound-attempt ledger and provider-result capture, with zero-result searches forbidden as retry evidence;
4. duplicate-send prevention with zero uncontrolled duplicate messages;
5. workflow versioning with safe rollout and recovery of in-flight executions;
6. observability of workflow, queue, policy, attempt, provider, and recovery evidence;
7. operator control that fits one private PostgreSQL-centered deployment; and
8. rate-limit enforcement under restart and concurrency.

Any failure of restart recovery, cancellation, ambiguous Gmail outcome reconciliation, duplicate-send prevention, workflow versioning, observability, operator control, or rate-limit enforcement under restart and concurrency is disqualifying and forces migration to Temporal before workflow product work continues. Dependency convenience, sunk implementation cost, existing lockfile presence, or familiarity cannot waive a failure. Pydantic AI remains the selected typed-agent layer; LangGraph and LangChain are excluded second agent-orchestration abstractions, while Restate and Prefect are excluded runtime/pipeline alternatives recorded only as decision history.

## Product kill and park criteria

| Scope | Trigger | Decision |
| --- | --- | --- |
| Idea/offer | Stage 1 closes with `0` positive replies and `0` qualified conversations after `100` unique delivered recipients and the full window, with deliverability `>=0.90` | `KILL` or `REVISE` only when evidence names one correctable hypothesis; never open Stage 2 automatically |
| Economics | projected contribution margin <= `0` at the tested price after measured delivery effort | `KILL` or redesign before any scale claim |
| Segment access | the next fixed cohort cannot be filled with new evidence-qualified policy-eligible recipients without weakening criteria or reusing an identity | `INCONCLUSIVE` or `PARK` the channel/segment; do not buy a broad list |
| Research quality | M3 unsupported-claim or citation gate fails after two materially different prompt/model approaches | `PARK` automation and use a deterministic/manual step if still economical |
| Qualification | precision remains below `0.80` on at least 50 labeled fixtures after two criterion revisions | `PARK` automated qualification; do not proceed to sending |
| Operator load | review/recovery effort exceeds the registered operator-hours cap in two consecutive synthetic runs | simplify or `PARK`; adding agents is not the default response |
| Strategy churn | three consecutive `REVISE` decisions produce no qualified commitment or stronger demand evidence | `KILL` or explicitly re-baseline as a new hypothesis |
| Compliance uncertainty | qualified advice or provider rules do not support the proposed contact method/jurisdiction | `KILL` that route regardless of commercial upside |

Counts are deduplicated and derived from reconciled records. The fixed staged authority is `100/200/300/400` new recipients and `100/300/600/1,000` cumulative maximum; a smaller lawful sample produces `INCONCLUSIVE`, not a fabricated pass, and the `1,000` ceiling is never a quota.

## Scope and non-goals

In scope: product, engine, side-effect, credential, privacy, compliance, cost, recovery, and solopreneur-capacity risks through M9. Non-goals: claiming zero risk, replacing qualified legal/security advice, enterprise risk bureaucracy, risks for hypothetical multi-tenancy or public scale, and a re-enable path that bypasses retained incident evidence.

## Exact implementation surfaces

The database and backend catalogs own controls, campaigns, conversations, suppression, incidents/exceptions, budget reservations, action authorization, offer economics, booking state, checkpoint evidence, strategies/activations, and immutable audits. Deterministic services own fail-closed controls, `CommercialPolicyEngine`, `ActionAuthorizationService`, `SendGateway`, `BookingGateway`, `CheckpointEvaluationService`, and `StrategyActivationService`. Commands must support disable, pause/cancel, revoke stale action authority, reconcile send/booking, and controlled recovery. Only the gateways invoke provider writes; no command treats zero search results as proof an ambiguous write did not occur.

None of these implementations exists today. ADR 0003's current `SendGateway` is a minimal contract and will be expanded only after persistence and policy gates.

## Ordered implementation tasks

<!-- roadmap-task id=PRODUCT-03-T01 milestone=M0 depends_on=PRODUCT-01-T02,PRODUCT-02-T01 mode=serial locks=product-contracts,compliance-policy,milestone-gate -->
- [ ] **Approve M0 risk posture —** Input: scope, metrics, risk table. Operation: mark each Critical/High risk accepted for the next gate, mitigated by a named deliverable, or rejected. Output: signed risk register. Test evidence: no Critical/High risk lacks owner, trigger, and response. Failure behavior: block M1.
<!-- roadmap-task id=PRODUCT-03-T02 milestone=M0 depends_on=PRODUCT-03-T01 mode=serial locks=product-contracts,milestone-gate -->
- [ ] **Review sunk-cost exposure at every gate —** Input: spend, time, failed gates, product signals. Operation: perform the initial M0 continue/revise/park/kill review against signed spend/time/failed-gate/product-signal snapshots and freeze the same recurring review procedure for every later gate. Output: signed initial M0 continue/revise/park/kill record and the recurring gate-review procedure; later records are created at their actual gates. Test evidence: operator signature linked to metric snapshot. Failure behavior: no work on the next milestone.
<!-- roadmap-task id=PRODUCT-03-T03 milestone=M1 depends_on=PRODUCT-03-T02,WF-01-T03 mode=serial locks=security-runtime,compliance-policy -->
- [ ] **Encode the reusable fail-closed stop interface —** Input: the signed risk register, WF-01 reproducible crash harness, and the document-local active-trigger catalog. Operation: implement a versioned `StopControlV1` interface, the M1 baseline disable path, and an evidence-preserving incident path; later milestone control owners integrate through this interface without changing its semantics. Output: exercised M1 kill baseline plus a versioned stop-control interface. Test evidence: the M1 harness proves disable-before-effect, retained evidence, idempotent acknowledgement, and no automatic re-enable. Failure behavior: provider calls and outreach remain disabled.
<!-- roadmap-task id=PRODUCT-03-T04 milestone=M8 depends_on=PRODUCT-03-T03,SEC-05-T04,OBS-05-T02,OBS-05-T03 mode=serial locks=security-runtime,milestone-gate -->
- [ ] **Exercise integrated operator recovery —** Input: synthetic incident scenarios R01-R27 plus SEC-05 bounded-stop evidence and OBS-05 typed containment/recovery services; completed IR-01..13 typed recovery/restore/rollback runbook services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: detect, stop, scope, reconcile, recover, and decide `re-enable|replace|kill` for every scenario; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: complete M8 drill record. Test evidence: event timelines prove no unauthorized action after stop. Failure behavior: a failed drill blocks promotion.

## Test strategy

- **Unit `test_kill_switch_denies_before_policy_and_provider`:** global stop short-circuits all downstream work.
- **Integration `test_cancelled_campaign_cannot_create_or_execute_send_intent`:** both creation and execution gates deny.
- **Recovery `test_ambiguous_send_is_permanently_quarantined_without_positive_sent_evidence`:** timeout/crash transitions to reconciliation; zero/multiple/conflicting searches at and beyond 300 seconds cannot retry, create a replacement intent, or enter either failure state.
- **Security `test_credential_incident_revokes_provider_authority`:** provider construction fails after token revocation state.
- **Cost `test_missing_authoritative_cost_feed_fails_closed`:** new paid calls pause when caps cannot be verified.
- **Commercial `test_negotiation_cannot_cross_offer_or_budget_truth_bounds`:** min price/margin, scope, terms, currency, rounding, and stated-budget constraints are immutable.
- **Conversation `test_reply_stops_cold_sequence_without_suppressing_eligible_thread`:** duplicate replies, terminal signals and bounded response limits preserve correct authority.
- **Booking `test_unconfirmed_or_ambiguous_booking_cannot_retry_or_duplicate`:** DST, conflict, reschedule/cancel and crash/replay cannot bypass confirmation/reconciliation.
- **Learning `test_weak_evidence_and_mid_cohort_activation_cannot_mutate`:** cross-campaign guardrails and rollback preserve action attribution.
- **Audit `test_reenable_requires_resolved_incident_and_operator_command`:** configuration restart alone cannot re-enable sending.

## Security, privacy, compliance, idempotency, observability, and cost

The kill path must be locally available to the authenticated operator, auditable, and independent of agent output. Suppression and incident records receive the strictest practical access and retention controls. Command idempotency prevents repeated stop/recovery actions from corrupting state. Alerts contain safe identifiers and rule codes, not secrets or full recipient/message data. Costs are reserved before paid calls and reconciled afterward.

## Failure, rollback, and operator recovery

Default recovery sequence: disable globally, stop dequeueing, preserve immutable evidence, revoke affected credentials/action authority, reconcile every in-flight external action, scope affected recipients/data/cost, correct the deterministic control, run the relevant fixture and recovery matrix, obtain explicit operator re-enable, and promote gradually through test inboxes. When evidence cannot establish what happened, remain disabled.

## Acceptance and retained evidence

- [ ] Every Critical/High risk has prevention, detection, trigger, owner, and mandatory response.
- [ ] Immediate global kills are explicit and fail closed.
- [ ] DBOS production-acceptance failure criteria mandate Temporal and cannot be waived by convenience.
- [ ] Product kill/park rules protect time, cash, and reputation.
- [ ] Current controls are not described as production safety.

Retain signed risk versions, incident/drill timelines, DBOS acceptance scorecards, risk acceptances, kill/re-enable commands, and product gate decisions. Passing M0 scope, metrics, and risk review unlocks M1; it does not authorize DBOS production use or outreach.
