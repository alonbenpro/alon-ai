# Agent, Conversation, and Checkpoint Learning Evaluation

**Document ID:** OBS-04
**Status:** Planned roadmap requirements; product implementation and live evidence are not claimed
**Milestone:** M8
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `OBS-04-T01 <- AGENT-10-T01; OBS-04-T02 <- OBS-04-T01; OBS-04-T03 <- OBS-04-T02,AGENT-10-T04,AGENT-10-T05; OBS-04-T04 <- OBS-04-T03,ARCH-03-T01,DB-05-T01,ARCH-02-T01,BACKEND-01-T04,WF-00-T01,PROVIDER-01-T02,PROVIDER-02-T01,PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,PROVIDER-06-T01,WF-02-T05,WF-03-T05,WF-04-T05,WF-06-T05,PROVIDER-01-T01,TEST-03-T03,TEST-03-T04,TEST-03-T06,TEST-04-T06,WF-05-T05,WF-01-T03,TEST-04-T05,WF-07-T04,WF-08-T04,WF-09-T04,BACKEND-01-T08,BACKEND-01-T09,BACKEND-01-T10; OBS-04-T05 <- OBS-04-T04`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Versioned implementation contracts, closed coverage and retained verification evidence
**Unlocks:** Dependent acceptance gates only; never automatic live release or provider authority
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Evaluation is planned; no agent suite, accepted product artifact, durable sales workflow or global strategy has implementation credit from this roadmap. The foundation tests and selected dependencies do not establish product readiness. Use AGENT-10's exact ten suites and 692 cases, three fresh candidate captures per case (2,076), frozen allocations/thresholds and two independent offline scorers. Do not duplicate weaker thresholds or retain historical eight-agent names.

## Evaluation authority and execution

M3 reviewed PromotionManifestV1 registers baseline code/prompt/model/tool/schema eligibility and protected evaluation rules. It is release evidence, not an additional inter-agent artifact. Runtime learning is one mechanism: closed CheckpointEvidenceBundle → GlobalLearningEngine proposals → StrategyActivationService deterministic gate → GlobalStrategyPackage → campaign-boundary StrategyActivation. Ordinary in-envelope checkpoint learning is automatic; the operator may tighten/stop protected controls. No arbitrary prompt editing, policy relaxation or model self-certification is allowed.

EvaluationSuiteCommandService owns evaluation_cases; AgentRunRecordingService alone starts/closes agent_runs; EvaluationExecutionService orchestrates and writes evaluation_results; ProviderCostReconciliationService owns billed usage. Verify exact suite/case/rubric/configuration/fixture/schema/provider/dependency hashes and reserve the full three-repetition maximum before capture. Only candidate model network is allowed; every non-model capability uses signed fixtures. Scoring has zero network. Capture/run/result/ledger identity and signatures must reconcile before any gate passes.

Each of the three repetitions independently passes exact quality, evidence, hard-safety, duration, mean/p95/max cost and regression gates. Use unrounded Decimal/Fraction golden vectors, NFC code-point spans, SUCCESS-only ECE population, nearest-rank percentiles, missing-prediction/zero-denominator rules and bounded baseline age from AGENT-10. Averages never rescue a hard failure, missing capture or failed repetition. Hard failures include false CONTINUE, false qualification, invented identity/claims/budget/commitment, opt-out false negative, illegal scope/economics, unconfirmed booking, authority/PII leak or uncontrolled provider network.

## Exact evaluation matrix

| Family | Required evidence and independent pass |
| --- | --- |
| artifact/order | all fifteen canonical names; accepted immutable provider refs; USER_SUPPLIED uses the same IdeaBrief; research before offer; preliminary before deep research; final before drafting; no circular acceptance/authority hash |
| discovery/research | approved multi-source adapters/scopes, duplicate identity precision/recall, conflict/unknown abstention, FACT/ESTIMATE/UNKNOWN, claim/evidence coverage and unsupported person/contact/role denial |
| writing/reply | writer has no send credentials; exact sanitized full thread and objective; inbound cold stop before classification; rejection versus genuine objection; durable suppression only from qualifying signal; bounded round/message/window and terminal behavior |
| commercial | accepted OfferPackage authority; STATED/INFERRED/UNKNOWN; exact min-price/margin/tax/fee/FX/rounding vectors; allowed variant/pilot/discount/payment/bundle; no guarantee/legal-term invention |
| booking | qualified CALL_NEXT_STEP without purchase acceptance, explicit timezone/slot confirmation, DST, expiry, conflicts, notifications, create/reschedule/cancel idempotency and ambiguous positive reconciliation |
| checkpoint | frozen newly closed stage as primary evidence; exact CONTINUE/REVISE/KILL/INCONCLUSIVE/SAFETY_STOP; missing costs/denominators and safety overrides; increments 100/200/300/400, cumulative 100/300/600/1,000 and no fifth cohort |
| global learning | every applicable agent gets PROMOTE/KEEP/ROLLBACK/INSUFFICIENT_EVIDENCE; minimum evidence, offline comparison, protected holdout, transfer/guardrail/confidence and stored rollback rules; weak evidence changes nothing |
| activation | trigger campaign next boundary only after CONTINUE; other active campaigns at their own checkpoint; future campaigns newest approved baseline; frozen offer/strategy/qualification/causal/evidence definitions never change mid-cohort |
| recovery | M1 K0–K8/eight disqualifiers, finite transactions/outbox/cancel/pause/version drain, Gmail six-point OAuth/fourteen-step gateway and history ambiguity, booking/checkpoint/learning kill points, restore and tombstone replay |
| privacy/cost | minimized transform-only global evidence; raw threads/contact/calendar/budget/holdout denial; all billed failures/retries retained; complete cost/operator-time evidence before commercial/checkpoint success |

## Cadence, global evidence, and rollback

On each relevant code/config/model/provider/schema change run affected deterministic contracts and full applicable capture/gate suites before eligibility. At each closed checkpoint freeze triggering campaign/stage evidence as primary, similar campaigns as secondary and all relevant historical failures/incidents as guardrails. Evaluate every applicable agent and record immutable lineage/expected metrics/confidence/reversibility. Runtime output scoring uses independent delayed labels; it can inform the next checkpoint bundle only through approved minimized transforms.

KEEP means evidence supports retaining the strategy; INSUFFICIENT_EVIDENCE means change is unjustified. Both are no-mutation results; NO_CHANGE is explanatory text, never serialized. Running-cohort offer/strategy/qualification/causal/evidence definitions freeze. Deterioration blocks affected future actions immediately, pauses/closes the current checkpoint, then applies compatible rollback at the boundary. A failed rollback remains blocked. Historical attribution never changes.

Use AGENT-10 exact rolling populations: every chronological terminal invocation under the active configuration, including billed failures; order by finished_at/agent_run_id; N=20 or N=30 according to specialist; two adjacent non-overlapping windows and stored max-cost/hard-safety rules. No favorable-run reset or post-hoc exclusions. Weekly synthetic smoke and release/restore evidence remain separate from real demand. OBS-02 displays complete suite/capture sets, per-agent results, cohort/version/activation comparisons and cross-campaign transfer without claiming causation from correlation.

Every required workflow matrix is executed on isolated PostgreSQL and the selected accepted runtime. Any M1 DBOS disqualifier forces the Temporal acceptance path; later tests cannot waive it. No evaluation suite directly writes Gmail/calendar or accepts its own artifact.

## Ordered implementation tasks

<!-- roadmap-task id=OBS-04-T01 milestone=M8 depends_on=AGENT-10-T01 mode=parallel locks=agent-artifacts -->
- [ ] **Freeze complete governed suite manifests —** Input: AGENT-10 exact suite/rubric/provider sets. Operation: materialize all ten suites and 692 cases with independently reviewed provenance and protected holdouts. Output: immutable dataset/fixture manifest. Test evidence: exact set/count/hash/privacy and unknown-agent negatives. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=OBS-04-T02 milestone=M8 depends_on=OBS-04-T01 mode=serial locks=agent-artifacts,live-environment -->
- [ ] **Execute isolated capture ownership —** Input: eligible candidate manifest, case/repetition and reserved budget. Operation: capture three fresh model results per case with non-model network denied and sole-owner run/result/cost writes. Output: 2,076 signed candidate captures and reconciled results. Test evidence: crash/replay/missing/tamper/provider-network cases. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=OBS-04-T03 milestone=M8 depends_on=OBS-04-T02,AGENT-10-T04,AGENT-10-T05 mode=serial locks=agent-runtime,agent-artifacts,milestone-gate -->
- [ ] **Apply deterministic scoring and strategy gates —** Input: AGENT-10 scorer and StrategyActivationService promotion interface. Operation: compare all repetitions/baseline/holdouts/transfer and produce exact per-agent results. Output: reproducible accepted/rejected package evidence. Test evidence: weak evidence, immutable-bound and favorable-average denial. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=OBS-04-T04 milestone=M8 depends_on=OBS-04-T03,ARCH-03-T01,DB-05-T01,ARCH-02-T01,BACKEND-01-T04,WF-00-T01,PROVIDER-01-T02,PROVIDER-02-T01,PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,PROVIDER-06-T01,WF-02-T05,WF-03-T05,WF-04-T05,WF-06-T05,PROVIDER-01-T01,TEST-03-T03,TEST-03-T04,TEST-03-T06,TEST-04-T06,WF-05-T05,WF-01-T03,TEST-04-T05,WF-07-T04,WF-08-T04,WF-09-T04,BACKEND-01-T08,BACKEND-01-T09,BACKEND-01-T10 mode=serial locks=workflow-runtime,backup-restore,milestone-gate -->
- [ ] **Verify every durable sales workflow —** Input: WF-07/08/09 and existing M1/Gmail/restore harnesses. Operation: execute complete artifact/conversation/commercial/booking/checkpoint/activation crash matrices. Output: signed workflow and global-learning simulation evidence. Test evidence: every durable boundary and no duplicate side effect. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.
<!-- roadmap-task id=OBS-04-T05 milestone=M8 depends_on=OBS-04-T04 mode=parallel locks=telemetry-catalog -->
- [ ] **Operate attributed deterioration monitoring —** Input: frozen action attribution and exact rolling rule populations. Operation: detect hard/window drift, block affected actions and request compatible boundary rollback. Output: automatic rollback/exception evidence. Test evidence: cross-campaign timing, mid-cohort blocking and unchanged historical hashes. Failure behavior: stop the affected capability/gate, preserve immutable evidence and quarantine uncertainty; no blind retry, admission or success claim.

## Test strategy, acceptance and recovery

- [ ] Every required positive/negative/concurrent case has a fixture identity, versioned owner, command, evidence hash and fail action; missing or unavailable evidence is not passing.
- [ ] Only SendGateway invokes Gmail writes and only BookingGateway invokes calendar create/reschedule/cancel. Crash/replay cannot duplicate effects.
- [ ] Cohorts remain 100/200/300/400 with cumulative 100/300/600/1,000 and no active-cohort mutation or fifth cohort.
- [ ] Decision sets remain CONTINUE/REVISE/KILL/INCONCLUSIVE/SAFETY_STOP and PROMOTE/KEEP/ROLLBACK/INSUFFICIENT_EVIDENCE; weak evidence cannot promote or continue.
- [ ] Retain signed case/result/command/fixture/schema/provider/strategy/activation hashes, call counts, costs, immutable action history and safe failure traces. Raw PII, message/calendar content, sensitive inferred attributes and credentials are excluded from ordinary telemetry/global learning.

Preserve first failures and resolve root cause; never average away safety failures or rewrite labels/history. Restore/rollback keeps admission off, applies current suppression/tombstones and reconciles possibly-called effects before any separately authorized re-entry. Use [canonical product authority](../00-product-strategy/01-product-scope.md), [booking](../03-workflows/07-booking-workflow.md), [checkpoints](../03-workflows/08-checkpoint-evaluation-workflow.md), [global learning](../03-workflows/09-global-learning-workflow.md), [shared evaluation](../04-agents/12-agent-evals-and-versioning.md), [API](../06-backend/02-api-contracts.md) and [privacy](../08-security-and-compliance/06-data-privacy-and-retention.md) as exact contracts.
