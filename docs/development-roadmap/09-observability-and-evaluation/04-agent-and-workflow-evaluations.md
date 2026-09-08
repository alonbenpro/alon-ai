# Agent and Durable-Workflow Evaluation Operations

**Document ID:** OBS-04
**Status:** Planned M3-M8 evaluation operations; no Pydantic AI agents/evals, DBOS workflows, evaluation cases/results, capture runner, promotion registry, shadow monitor, or rollback automation exists today
**Milestone:** M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `OBS-04-T01 -> OBS-04-T02 -> OBS-04-T03 -> OBS-04-T04 -> OBS-04-T05`; cross-document task Inputs `OBS-04-T01 <- AGENT-10-T01; OBS-04-T03 <- AGENT-10-T04,AGENT-10-T05; OBS-04-T04 <- ARCH-03-T01,DB-05-T01,ARCH-02-T01,BACKEND-01-T04,WF-00-T01,PROVIDER-01-T02,PROVIDER-02-T01,PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,PROVIDER-06-T01,WF-02-T05,WF-03-T05,WF-04-T05,WF-06-T05,PROVIDER-01-T01,TEST-03-T03,TEST-03-T04,TEST-03-T06,TEST-04-T06,WF-05-T05,WF-01-T03,TEST-04-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): AGENT-01 through [AGENT-10](../04-agents/10-agent-evals-and-versioning.md), WF-00/01/02/05/06, DB-04/05, six provider contracts, SEC-01/03/06, and OBS-01/02/03
**Outputs:** Evaluation execution cadence, immutable datasets/captures/results/manifests, workflow recovery suites, promotion/rollback operations, shadow/production monitoring, and evidence retention
**Unlocks:** M3 agent configuration promotion, M1/M6 workflow acceptance, and M8 regression detection
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Every agent configuration and workflow/runtime version earns execution eligibility through frozen, reproducible, privacy-reviewed evaluation evidence. Promotion changes only a versioned registry pointer for future runs. Evaluation grants no artifact acceptance, policy, approval, suppression, budget, compliance, state-transition, Gmail or `SendGateway` authority. A hard-safety failure rejects or rolls back regardless of average quality/cost.

## Current repository state

Pydantic AI/Pydantic Evals and DBOS are selected dependencies, but agent/workflow packages are empty and M1 is unrun. DB-04 tables and AGENT-10 models/functions/suites are planned only. There are no 552 cases, three-capture manifests, scorers, promotion/rollback registry, workflow crash suite, shadow execution, production window, dashboard or alert. Foundation unit tests do not constitute agent/workflow evaluation.

## Scope and non-goals

In scope: dataset/case governance; eight exact agent suites; candidate capture/scoring/promotion/rollback; six provider fixture consistency; prompt injection/privacy/safety cases; workflow determinism/versioning/crash/recovery/control/send ambiguity; continuous/shadow monitoring; cost/latency/quality drift; operator review; and retained evidence.

Non-goals: online self-training, changing labels after candidate output, model-as-sole-evaluator, reducing hard cases, using production recipients by default, networking during deterministic scoring, reusing model captures, trading quality/safety for cost, agents evaluating their own authority, or inventing `evaluation.*`/`agent.promoted.*` domain events absent ARCH-03.

## Exact planned implementation surfaces

Create `evaluations/datasets.py`, `evaluations/capture.py`, `evaluations/scoring.py`, `evaluations/manifests.py`, `evaluations/promotion.py`, `evaluations/runtime_monitor.py`, `evaluations/workflows/`, isolated runner configuration, registry storage, and tests. Persist exactly through DB-04/05 owners: `EvaluationSuiteCommandService` writes `evaluation_cases`; `AgentRunRecordingService` alone starts/closes `agent_runs`; `EvaluationExecutionService` orchestrates and writes only `evaluation_results`; `ProviderCostReconciliationService` writes costs. Signed capture/manifests are versioned encrypted objects under SEC-03/06.

### Frozen agent evaluation contract

AGENT-10 remains fully normative:

- exactly eight suites: `idea_discovery.v1` 48, `offer_design.v1` 48, `market_research.v1` 60, `lead_research.v1` 60, `lead_qualification.v1` 80, `outreach_drafting.v1` 64, `reply_classification.v1` 120, and `experiment_evaluation.v1` 72—552 cases total;
- exact normal/underspecified/contradictory/attack and specialist allocations, weights, hard gates, precision/recall/F1/ECE/citation/span/abstention/quality thresholds, p10/p95 duration and mean/p95/max native-cost ceilings from AGENT-10; no copied weaker threshold here;
- three fresh independent candidate `model.complete_structured` network captures per case: 1,656 candidate captures; all five non-model capabilities resolve only from signed fixtures; deterministic scoring has zero network;
- exact strict models, NFC Unicode code-point spans, `SUCCESS`-only ECE population, unrounded Decimal comparisons, nearest-rank percentiles, candidate/baseline regression bands, signature/hash/provider ledger/cost reconciliation, and three independently passing repetition summaries;
- any hard failure, false `SCALE`, false-qualified required failure, unsubscribe false negative, PII/contact/credential leak, authority edge, or fixture/live-network violation rejects immediately;
- no quality regression may be traded for lower cost; one max-cost breach is immediate incident/rollback; exact consecutive non-overlapping rolling windows remain normative.

Dataset changes are reviewed independently from candidate output and create a new suite version. Every case has stable key, source/provenance, frozen input/expected/rubric hashes, sensitivity class, attack tags, labeler/reviewer reference, and change reason. Synthetic/redacted data is default. A production-derived case requires SEC-06 purpose/consent/minimization, encrypted restricted access, no live address/token/body beyond the minimum transformed fact, and expiry.

### Exact execution and ownership sequence

1. Verify suite/case/rubric/fixture/config/prompt/model/tool/schema/validator/evaluator/dependency/release hashes and reserve the complete three-repetition native cost maximum.
2. `EvaluationExecutionService` selects case/config/repetition and asks `AgentRunRecordingService` to insert/start one run; it never writes `agent_runs` itself.
3. Isolated capture runner enables only exact candidate `model.complete_structured` network; denies Gmail/SendGateway/product DB/state and every live non-model call; stores signed `CandidateGenerationCaptureV1` plus provider ledger.
4. `AgentRunRecordingService` closes terminal run and reconciles cost. Then `EvaluationExecutionService` writes one immutable result per `(case,agent_run,evaluator_version)`.
5. Offline scorer verifies every signature/hash and computes exact deterministic case/repetition/suite/regression/cost reports with no network.
6. Operator reviews three complete repetition summaries, authority graph, privacy scan, cost/ILS evidence and rollback target; only a signed `PROMOTE` manifest changes the registry pointer. Startup recomputes the active manifest/config/dependency hash.
7. Rollback appends a `ROLLBACK` manifest, points new runs to the prior promoted config, and drains/version-routes in-flight workflows. It never edits cases/results/history.

ARCH-03 defines no evaluation/promotion domain events. Operational telemetry uses OBS-01 `evaluation.operation.completed`; release audit/Git/manifests hold promotion facts until an upstream canonical event/schema is approved.

### Workflow/runtime evaluation matrix

| Suite | Required coverage and hard pass |
| --- | --- |
| M1 DBOS acceptance | exact WF-00 eight disqualifiers and WF-01 kill points, signed two-table NDJSON/RFC 8785/Ed25519 evidence; any disqualifier forces Temporal before product workflow work |
| finite lifecycle | every legal/illegal ARCH-03 experiment/run/campaign transition, finite deadlines/retries, snapshot hash/version verify-before-use, one sole writer/event bundle |
| internal delivery | outbox at-least-once with business write + `outbox_deliveries` atomic; poison/dead-letter incident; external effects forbidden |
| provider/agent | six typed capability success/failure/time/cancel/budget/result-hash/fixture contracts; no mutation/credential/Gmail edge |
| control/recovery | pause/cancel requested/ack, resume revalidation, new-run retry, runtime mapping/version drain, kill at every boundary, no SQL repair |
| Gmail/OAuth | PROVIDER-01 six OAuth kill points/CAS/GC, exact 14-step SendGateway kill/concurrency/suppression/rate/result matrix, ambiguity never retry, mailbox-only history reconciliation/cursor atomicity |
| backup/restore | restore 46 product tables/events/snapshots/attempt chains, sessions revoked, controls false, no provider call, runtime version compatibility |
| security/privacy/cost | injection/SSRF/exfiltration/redaction/canary/supply-chain, retention/rights, reservation/original currency/ILS/overage, telemetry failure |

Workflow version promotion requires the relevant matrix on real PostgreSQL and the selected runtime. DBOS product eligibility exists only after all M1 passes; a disqualifying DBOS result is not waived by later green tests and triggers a signed Temporal migration decision. Temporal then runs the same application-level Gmail/authority/recovery matrix because runtime change cannot remove external ambiguity.

### Cadence, shadow execution, drift, and rollback

| Trigger | Required evaluation |
| --- | --- |
| every commit/PR | deterministic schema/scorer/golden/authority/import tests, selected impacted synthetic fixtures, no network, privacy/secret scan |
| prompt/model/tool/provider/schema/validator/dependency/config change | all affected eight-suite cases × three fresh captures; all exact gates; operator promotion |
| workflow/runtime/application state/event/side-effect change | complete affected workflow matrix plus M1/M6 gates where applicable; crash/replay/version tests |
| release | active manifest/dependency/release hash, Critical security and restore evidence freshness, no unresolved hard alert |
| weekly while operating | full deterministic fixture/workflow smoke; no model network unless budgeted candidate/shadow run is approved |
| rolling runtime | exact AGENT-10 populations/windows over every chronological terminal invocation under active config; provider/cost/latency and hard-safety detections |
| monthly or provider/policy notice | review source/price/model/version/fixture drift and schedule a shadow candidate if needed |

Shadow agent runs use synthetic/redacted approved inputs, have no artifact acceptance/materialization/business transition/Gmail path, reserve budget, and are visibly `fixture/shadow` in ledgers. Production outputs may be scored only with delayed, independently accepted labels/evidence and never feed automated promotion. Drift indicators are prompts for evaluation, not automatic model judgment.

Immediate rollback/pause: any AGENT-10 hard failure, production secret/PII leak, authority edge, false unsubscribe handling, false `SCALE`/qualification, manifest/hash drift, max-cost breach, two consecutive exact rolling latency/cost windows, workflow duplicate/unauthorized/suppressed send, snapshot/replay/version invariant, or restore failure. When agent rollback compatibility is uncertain, pause affected experiment stage; send controls remain false where outreach is involved.

### Evaluation telemetry and evidence

OBS-01 logs case/result IDs, suite/agent/config/evaluator/prompt/model/tool/schema/validator versions/hashes where allowlisted, repetition, pass/hard reason enum, duration/usage/cost entry, fixture/shadow mode, correlation—never fixture/prompt/output/expected/rubric content. OBS-02 metric labels use suite/agent/repetition/pass/hard only. Dashboards show 552/1,656 completeness, three repetition status, hard failures, components, regression, p10/p95, mean/p95/max native cost plus separately evidenced ILS, active/rollback manifests, rolling windows and workflow matrices.

## Ordered implementation tasks

<!-- roadmap-task id=OBS-04-T01 milestone=M8 depends_on=AGENT-10-T01 mode=parallel locks=agent-artifacts -->
- [ ] **Implement governed datasets/manifests —** Input: eight exact suites, specialist cases/rubrics/fixtures and sensitivity review. Operation: create 552 immutable cases, signed hashes, independent labels and change protocol. Output: reproducible dataset. Test evidence: count/allocation/provenance/hash/attack/privacy scans. Failure behavior: suite invalid; no capture/promotion.
<!-- roadmap-task id=OBS-04-T02 milestone=M8 depends_on=OBS-04-T01 mode=serial locks=agent-artifacts,live-environment -->
- [ ] **Implement isolated capture and exact ownership —** Input: candidate config/case/repetition/reserved budget. Operation: delegate run rows, permit only candidate model network, sign capture/ledger, close run, then write result. Output: 1,656 complete captures/results. Test evidence: network/authority spy, kill/replay/missing/tamper/cost matrix. Failure behavior: full repetition/promotion fails.
<!-- roadmap-task id=OBS-04-T03 milestone=M8 depends_on=OBS-04-T02,AGENT-10-T04,AGENT-10-T05 mode=serial locks=agent-runtime,agent-artifacts,milestone-gate -->
- [ ] **Implement deterministic scoring/promotion/rollback —** Input: signed captures and exact AGENT-10 functions/gates; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: invoke the versioned AGENT-10 scorer twice offline, compare baseline through the AGENT-10 gate interface, render the operator review, and request any approved promotion/rollback exclusively through the existing AGENT-10 owner; OBS-04 never writes a competing registry pointer; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: promoted/rejected/rollback manifest. Test evidence: threshold equality/rounding/ECE/span/percentile/hard/regression/concurrency. Failure behavior: prior config remains.
<!-- roadmap-task id=OBS-04-T04 milestone=M8 depends_on=OBS-04-T03,ARCH-03-T01,DB-05-T01,ARCH-02-T01,BACKEND-01-T04,WF-00-T01,PROVIDER-01-T02,PROVIDER-02-T01,PROVIDER-03-T01,PROVIDER-04-T01,PROVIDER-05-T01,PROVIDER-06-T01,WF-02-T05,WF-03-T05,WF-04-T05,WF-06-T05,PROVIDER-01-T01,TEST-03-T03,TEST-03-T04,TEST-03-T06,TEST-04-T06,WF-05-T05,WF-01-T03,TEST-04-T05 mode=serial locks=workflow-runtime,backup-restore,milestone-gate -->
- [ ] **Implement workflow evaluation suites —** Input: canonical state/event/owner/runtime/provider/Gmail/recovery contracts; implemented M1 crash harness, finite-workflow failure-injection suite, Gmail workflow execution/control contract, Gmail history/suppression suite and typed-repair/restore runner; separately signed M1/M6 gate evidence and exact scenario/command manifests; implemented original M1 crash harness and completed executable Gmail history/suppression suite; signed M1/M6 gate bundles remain evidence, not runner implementations; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: consolidate and re-execute the completed owner-supplied M1/M6/restore failure-injection suites against the M8 real-DB/runtime candidate, retaining exact original scenario identities and signed results; do not redefine or retroactively supply the earlier M1/M6 gates; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: runtime/workflow gate evidence. Test evidence: exact matrix above. Failure behavior: block milestone; Temporal after DBOS disqualifier.
<!-- roadmap-task id=OBS-04-T05 milestone=M8 depends_on=OBS-04-T04 mode=parallel locks=telemetry-catalog -->
- [ ] **Operate shadow/drift/rolling gates —** Input: active manifest and terminal runtime population. Operation: schedule bounded synthetic shadow, exact rolling windows, alerts and manual review. Output: continuous evidence/rollback trigger. Test evidence: hard event, two-window breach, provider drift, alert/outage. Failure behavior: rollback or pause; no unpromoted fallback.

## Test strategy

- **Completeness `test_exact_eight_suites_552_cases_three_fresh_captures_and_all_manifests_exist`.**
- **Isolation `test_capture_only_model_network_scoring_no_network_and_eval_has_no_product_gmail_or_credential_authority`.**
- **Ownership `test_evaluation_execution_never_writes_agent_runs_and_result_waits_for_terminal_owned_run`.**
- **Scoring `test_all_agent10_golden_functions_thresholds_regressions_and_native_costs_match_independent_implementations`.**
- **Workflow `test_every_state_event_side_effect_kill_replay_version_and_recovery_boundary_has_exact_result`.**
- **Runtime `test_any_dbos_disqualifier_produces_temporal_migration_gate_not_waiver`.**
- **Rollback `test_hard_and_exact_rolling_triggers_restore_prior_manifest_and_pause_incompatible_runs`.**
- **Privacy `test_evaluation_artifacts_telemetry_and_graphify_exclude_secret_pii_and_hidden_reasoning`.**

## Security, privacy, compliance, idempotency, observability, and cost

Evaluation objects are encrypted/versioned/access-audited and synthetic/redacted by default. Case/config/evaluator hashes and DB uniqueness provide idempotency; a retry never substitutes a prior model capture. Exact OBS telemetry/cost applies. Legal/compliance labels come only from retained counsel/policy evidence; an evaluator/model cannot declare a real recipient lawful. Evaluation spend is pre-reserved and cannot buy authority.

## Failure, rollback, and operator recovery

Missing/corrupt/tampered case/capture/result/ledger/cost/manifest, scorer disagreement, network/authority leak, hard failure, threshold regression, runtime replay mismatch or incomplete persistence rejects the candidate. Stop affected runner/config/workflow, preserve restricted evidence, rotate leaked credentials, restore prior registry for new runs, drain/version-route or pause in-flight work, and open incident. Never delete a hard case, relabel after output, average missing as zero, relax a threshold, or activate unpromoted config.

## Acceptance and retained evidence

- [ ] AGENT-10 exact eight/552/three-capture/scoring/gate/promotion/rollback contracts run without weaker aliases.
- [ ] Workflow matrices prove runtime, state/event/sole-writer, provider/Gmail/control/recovery/restore behavior at every failure boundary.
- [ ] Continuous cadence/windows/alerts use exact populations and cannot auto-promote or grant product authority.
- [ ] Every result/capture/ledger/cost/manifest is reproducible, privacy-safe and owner-correct.

Retain datasets/rubrics/fixture/config/prompt/model/tool/schema/validator/evaluator/dependency hashes, 1,656 candidate captures/provider ledgers, results/repetition/suite/regression/cost reports, authority/network/privacy scans, promotion/rollback registry history, M1/M6/workflow/restore crash traces, rolling-window alerts, and operator reviews.

## Dependencies and next deliverable

OBS-04 consumes Task 2-4 evaluation/runtime contracts and OBS-03 cost. Passing agent suites unlocks only M3 execution eligibility; passing workflow suites unlocks the relevant milestone gate. Incidents/rollbacks flow to [OBS-05](05-incident-response.md); no evaluation result authorizes real outreach.
