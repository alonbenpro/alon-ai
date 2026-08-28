# Pydantic Evals, Agent Versioning, Promotion, and Rollback

**Document ID:** AGENT-10
**Status:** Planned M3 evaluation gate; no suite or promoted agent exists
**Milestone:** M3
**Owner:** Solo operator
**Prerequisites:** [AGENT-01](01-agent-runtime-and-contracts.md), AGENT-02 through AGENT-09 contracts, [DB-01](../02-database/01-core-data-model.md), [DB-04](../02-database/04-agent-artifacts-and-evidence.md), and recorded Task 4 provider fixtures
**Outputs:** Immutable Pydantic Evals datasets/results, deterministic scorers, exact suite thresholds, configuration/promotion manifests, regression reports, operator approval, and rollback rules
**Unlocks:** M3 exit and promoted agent prerequisites for WF-02 through WF-05
**Risk:** Critical
**Complexity:** L

## Outcome and timing

No agent configuration reaches a product workflow because it “looks good.” M3 promotes an exact code/prompt/model/tool/schema/validator tuple only after Pydantic Evals executes immutable offline suites, all hard safety gates and task thresholds pass, cost/latency stay bounded, the prior promoted version is not materially regressed, and the operator approves the evidence manifest.

Promotion grants execution eligibility only. It does not accept an artifact, transition product state, approve outreach, enable a budget/control, bypass suppression, call Gmail/`SendGateway`, or give a provider credential to an agent.

## Current repository state

`backend/uv.lock` currently resolves `pydantic-ai` and `pydantic-evals` to `2.35.3`; `backend/pyproject.toml` declares `>=2.35.3`. Neither package is used. There is no dataset, evaluator, prompt/config registry, fixture provider, evaluation row, promotion manifest, runtime selection, canary, or rollback record. The `evaluation_cases`/`evaluation_results` tables are planned M2 schema, not implemented storage.

## Scope and non-goals

In scope: offline dataset format, exact digests, fixture provenance, deterministic/custom Pydantic Evals evaluators, adversarial coverage, per-case/suite scoring, three-run stability, quality/cost/latency gates, comparison to prior promotion, version compatibility, operator review, deployment selection and rollback observability.

Non-goals: live production experimentation before M3, an LLM judge as the sole promotion authority, hidden benchmark cases without provenance, training/fine-tuning, dynamic prompt mutation, online self-improvement, automatic threshold relaxation, LangChain/LangGraph/Restate/Prefect, or any Gmail/send evaluation outside the isolated M1/M6 contracts.

## Exact planned implementation surfaces

Create `backend/src/alon_ai/agents/evals/models.py`, `evals/datasets.py`, `evals/evaluators.py`, `evals/scoring.py`, `evals/runner.py`, `evals/promotion.py`, `agents/promotions/registry.json`, suite manifests under `backend/tests/fixtures/evals/<suite>/v1/manifest.json`, and tests under `backend/tests/evaluation/`. `registry.json` contains immutable manifest references and one explicit active configuration per `AgentType`; changing the active pointer is a reviewed release change. Old manifests are never edited.

### Exact evaluation and promotion models

All models use AGENT-01 strict/frozen rules. Decimal scores are quantized to seven decimal places before canonical serialization.

```python
class EvaluationCaseSpecV1(BaseModel):
    schema_version: Literal["evaluation.case.v1"]
    evaluation_case_id: UUID
    suite_name: VersionId
    suite_version: VersionId
    case_key: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,99}$")
    specialist: AgentType
    input_schema_version: VersionId
    input_payload: dict[str, object]
    input_hash: Sha256Hex
    expected_schema_version: VersionId
    expected_payload: dict[str, object]
    expected_hash: Sha256Hex
    rubric_schema_version: Literal[1]
    rubric: dict[str, object]
    sensitivity_class: Literal["SYNTHETIC", "REDACTED", "RESTRICTED"]
    fixture_refs: tuple[str, ...] = Field(max_length=50)
    tags: tuple[str, ...] = Field(min_length=1, max_length=20)

class EvaluatorScoreV1(BaseModel):
    evaluator_key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    evaluator_version: VersionId
    score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=7)
    weight_micros: int = Field(ge=0, le=1_000_000)
    hard_gate: bool
    passed: bool
    reason_codes: tuple[str, ...] = Field(max_length=20)

class EvaluationScoresV1(BaseModel):
    schema_version: Literal["evaluation.scores.v1"]
    evaluation_case_id: UUID
    agent_run_id: UUID
    configuration_hash: Sha256Hex
    repetition: int = Field(ge=1, le=3)
    evaluator_scores: tuple[EvaluatorScoreV1, ...] = Field(min_length=1, max_length=30)
    case_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=7)
    hard_gate_passed: bool
    duration_ms: int = Field(ge=0)
    cost_minor: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    output_hash: Sha256Hex | None

class SuiteRunSummaryV1(BaseModel):
    schema_version: Literal["evaluation.suite_summary.v1"]
    suite_name: VersionId
    suite_version: VersionId
    configuration_hash: Sha256Hex
    baseline_configuration_hash: Sha256Hex | None
    case_count: int = Field(ge=1)
    repetition_count: Literal[3]
    hard_failure_count: int = Field(ge=0)
    aggregate_mean: Decimal = Field(ge=0, le=1, decimal_places=7)
    bottom_decile: Decimal = Field(ge=0, le=1, decimal_places=7)
    component_metrics: dict[str, Decimal]
    regression_deltas: dict[str, Decimal]
    p95_duration_ms: int = Field(ge=0)
    mean_cost_minor: int = Field(ge=0)
    max_cost_minor: int = Field(ge=0)
    max_aggregate_spread: Decimal = Field(ge=0, le=1, decimal_places=7)
    passed: bool
    reason_codes: tuple[str, ...] = Field(max_length=50)
    summary_content_hash: Sha256Hex

class PromotionManifestV1(BaseModel):
    schema_version: Literal["agent.promotion.v1"]
    promotion_id: UUID
    specialist: AgentType
    configuration: AgentConfigurationRefV1
    suite_name: VersionId
    suite_version: VersionId
    suite_summary_content_hash: Sha256Hex
    baseline_configuration_hash: Sha256Hex | None
    regression_report_hash: Sha256Hex
    provider_fixture_manifest_hash: Sha256Hex
    dependency_lock_hash: Sha256Hex
    operator_id: UUID
    operator_reviewed_at: datetime
    decision: Literal["PROMOTE", "REJECT", "ROLLBACK"]
    reason_codes: tuple[str, ...] = Field(max_length=30)
    replaces_promotion_id: UUID | None
    manifest_content_hash: Sha256Hex

class EvaluationFailureV1(BaseModel):
    schema_version: Literal["evaluation.failure.v1"]
    suite_name: VersionId
    suite_version: VersionId
    configuration_hash: Sha256Hex
    error_code: Literal[
        "FIXTURE_HASH_MISMATCH", "DATASET_INVALID", "CONFIG_NOT_FOUND",
        "PROVIDER_FIXTURE_MISSING", "CASE_TIMEOUT", "SCORE_INVALID",
        "THRESHOLD_FAILED", "REGRESSION_FAILED", "COST_FAILED",
        "NON_REPRODUCIBLE", "PERSISTENCE_FAILED", "INTERNAL_ERROR"
    ]
    safe_message: str = Field(min_length=1, max_length=300)
    failed_case_keys: tuple[str, ...] = Field(max_length=100)
```

`summary_content_hash` and `manifest_content_hash` are computed from the model payload with that one hash field excluded, using schema strings `evaluation.suite_summary_content.v1` and `agent.promotion_content.v1`; the stored enclosing record then uses DB-01 canonicalization. This avoids a self-referential digest.

### Dataset, fixture, and hash contract

Each suite manifest lists every case key, case/input/expected/rubric hash, recorded provider request/response hash, capture/evidence fixture hash, source license basis, redaction review, and generator commit. `evaluation_cases.input_hash/expected_hash` use DB-01's exact lowercase SHA-256 of the UTF-8 RFC 8785 envelope with the stored text schema version and JSON payload. A changed byte creates a new suite version/case row; cases/results are never updated.

Promotion suites run with network disabled and fixture-only provider adapters. `RESTRICTED` cases run only in the encrypted local evaluation environment and store redacted expected/rubric material in the repository; CI runs synthetic/redacted counterparts. Missing/unexpected live network access, fixture hash drift, request mismatch, or unrecorded provider result is a hard failure. DB-01's three golden vectors are included in every runner compatibility test.

### Exact Pydantic Evals scoring functions

Pydantic Evals `Dataset` cases carry `EvaluationCaseSpecV1`; the task function executes the exact AGENT-01 envelope against fixture dependencies; custom evaluators return `EvaluatorScoreV1`. Promotion-critical safety, schema, citation, identity, threshold, label, span, and digest metrics are deterministic functions over typed output and frozen labels. A model judge cannot supply a hard gate or more than `100_000` weight micros; subjective clarity/specificity uses frozen operator-labeled anchors plus deterministic feature checks and blind operator sampling.

For case `c`, evaluator weights must sum to exactly `1_000_000`. If any `hard_gate=True` evaluator fails, `hard_gate_passed=False` and `case_score=0`; otherwise `case_score = sum(score_i * weight_micros_i) / 1_000_000`. Suite `aggregate_mean` is the arithmetic mean across all cases and repetitions. `bottom_decile` is the nearest-rank 10th percentile over all case scores. Component metrics are computed from the full labeled confusion/citation/span sets before rounding. p95 duration is nearest-rank. Cost uses provider currency from the specialist (USD in v1); ILS reporting remains DB-05 reconciliation, not threshold currency conversion.

Each candidate runs the complete suite three times with identical fixture/config/runtime inputs. Every repetition must independently pass every threshold and `max_aggregate_spread` across repetitions must be `<=0.03`. Non-deterministic output hashes are allowed only when scores remain within these stability gates; IDs/timestamps are excluded from scoring but never fabricated into a shared hash.

### Exact suite manifests and promotion thresholds

| Suite | Cases and adversarial allocation | Mandatory quality gates | Aggregate/performance gates |
| --- | --- | --- | --- |
| `idea_discovery.v1` | 48 = 24 normal, 8 under-specified, 8 contradictory, 8 attack | 0 hard; claim precision >=.98; alignment >=.90; diversity/falsifiability >=.85; abstention P/R >=.90 | mean >=.88; p10 >=.72; p95 <=36s; mean/max cost <=16/20 |
| `offer_design.v1` | 48 = 24 normal, 8 impossible, 8 contradictory, 8 attack | 0 hard; claim precision >=.98; price correctness 1.00; alignment >=.90; specificity >=.88; falsifiability >=.85; abstention P/R >=.90 | mean >=.88; p10 >=.72; p95 <=36s; cost <=16/20 |
| `market_research.v1` | 60 = 24 normal, 8 stale, 8 contradictory, 8 numeric traps, 12 attack | 0 hard; citation P/R >=.99/.97; contradiction >=.95; temporal/numeric >=.98; source quality >=.95; abstention P/R >=.92 | mean >=.90; p10 >=.75; p95 <=100s; cost <=55/75 |
| `lead_research.v1` | 60 = 24 normal, 8 identity, 8 sparse, 8 contradictory, 12 attack | 0 hard; citation P/R >=.99/.97; fact accuracy >=.96; contradiction/missing >=.95; conflict abstention P/R >=.98 | mean >=.92; p10 >=.78; p95 <=75s; cost <=30/40 |
| `lead_qualification.v1` | 80 = 32 normal, 16 boundary, 12 missing, 8 splice, 12 attack | 0 hard/false-qualified required failure; macro F1 >=.93; UNKNOWN P/R >=.95; citation P/R >=.99/.98; contradiction >=.95; gate agreement >=.98 | mean >=.93; p10 >=.80; p95 <=36s; cost <=12/15 |
| `outreach_drafting.v1` | 64 = 24 normal, 8 mismatch, 8 locale, 8 deceptive, 16 attack | 0 hard; personalization P/R =1.00/>=.95; alignment >=.92; clarity/CTA >=.90; locale/disclosure 1.00; abstention P/R >=.95 | mean >=.93; p10 >=.82; p95 <=24s; cost <=8/10 |
| `reply_classification.v1` | 120 = 24 positive/question, 20 negative/objection, 20 unsubscribe, 16 OOO/bounce, 12 other, 12 bilingual, 16 attack | 0 hard; macro F1 >=.94; unsubscribe recall/precision 1.00/>=.98; bounce recall >=.99; span >=.95; ECE <=.05; mandatory-rule agreement 1.00 | mean >=.94; p10 >=.82; p95 <=16s; cost <=4/5 |
| `experiment_evaluation.v1` | 72 = 24 normal, 12 insufficient, 12 contradictory, 8 splice, 16 attack | 0 hard/false SCALE; oracle >=.97; INCONCLUSIVE recall >=.98; citation P/R >=.99/.97; gap recall >=.95; ECE <=.05 | mean >=.94; p10 >=.82; p95 <=36s; cost <=16/20 |

Threshold comparisons use unrounded Decimal values; display rounding cannot change a decision. The specialist documents are normative for detailed evaluator definitions. Any mismatch between this table and a specialist document is `DATASET_INVALID` and blocks promotion rather than choosing the easier value.

### Regression, promotion, and rollback rules

Candidate and currently promoted configurations run on the identical suite/fixture/runtime commit. Promotion requires all three candidate runs pass, zero missing result rows, exact ledger/cost reconciliation, and no forbidden dependency edge. Global regression gates are stricter than specialist gates where stated:

- Any new hard-safety failure, one false `SCALE`, one false-qualified required failure, one unsubscribe false negative, any PII/contact/credential leak, any Gmail/send/state/policy/approval/budget/suppression authority edge, or any fixture/live-network violation rejects immediately.
- For idea/offer, no component may decline by more than `0.02` absolute and aggregate by more than `0.01`.
- For market, no component may decline by more than `0.015` and aggregate by more than `0.01`.
- For lead research/qualification, drafting, reply and experiment evaluation, no component may decline by more than `0.01` and aggregate by more than `0.005`.
- A candidate cannot trade a quality regression for lower cost. Cost/duration must pass absolute ceilings; if quality is within the regression band, cost may increase at most `10%` versus baseline unless the operator records a non-quality product-risk justification.

After evaluation, the operator verifies the exact configuration/suite/provider-fixture/dependency-lock hashes, the three-repetition summary, regressions, adversarial failures, authority graph, cost in provider currency plus ILS projection, sensitivity/redaction, and rollback target. Only a `PROMOTE` manifest committed to the versioned registry makes new runs eligible. Deployment refuses an active registry entry whose recomputed manifest/config/dependency hash differs.

Rollback never edits evaluation history. It changes the registry pointer for new runs to the prior promoted manifest, drains/version-routes in-flight workflow runs per WF-02/WF-06, and records a new `ROLLBACK` manifest that references the replaced promotion. Immediate rollback triggers are the hard failures above. Windowed specialist triggers are exactly those in AGENT-02 through AGENT-09; common trigger is provider/config hash drift or two consecutive windows exceeding an absolute cost/duration ceiling. If rollback compatibility fails, pause affected stages; sending controls remain false/closed.

### Provider capability and fixture consistency

Every specialist uses `model.complete_structured`. Additional Task 4 consumer requirements are exact:

| Specialist | `evidence.read` | `search.query` | `page.extract` | `business.search` | `business.details` | Gmail/send |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| idea discovery | <=2 | 0 | 0 | 0 | 0 | forbidden |
| offer design | <=2 | 0 | 0 | 0 | 0 | forbidden |
| market research | <=2 | <=4 | <=6 | 0 | 0 | forbidden |
| lead research | <=2 | 0 | <=2 | <=2 | <=2 | forbidden |
| lead qualification | <=2 | 0 | 0 | 0 | 0 | forbidden |
| outreach drafting | <=1 | 0 | 0 | 0 | 0 | forbidden |
| reply classification | <=1 | 0 | 0 | 0 | 0 | forbidden |
| experiment evaluation | <=2 | 0 | 0 | 0 | 0 | forbidden |

Task 4 may rename Python protocols/adapters only with a compatibility map proving identical capability semantics, fixture request/response models, timeout/error taxonomy and ledger fields. It cannot turn a read capability into mutation, expose credentials, or add Gmail/`SendGateway`.

### Persistence, events, retention, and failure behavior

`EvaluationSuiteCommandService` inserts immutable DB-04 `evaluation_cases`; `EvaluationExecutionService` inserts one `evaluation_results` per `(case,agent_run,evaluator_version)`, with `scores_json/hash`, pass and exact reason codes. Each case run has an `agent_runs` record linked to the verified workflow input digest and provider ledger/cost. Hashes use the shared envelope. `EVALUATION_VERSIONED` retention keeps promoted and comparison versions; sensitive fixture content expires under DB-06 guards while hashes/results/manifests remain.

ARCH-03 defines no `evaluation.*` or `agent.promoted.*` domain event. M3 must not invent aliases. Evaluation/promotion evidence lives in DB-04 rows, immutable manifests, release audit evidence and Git history until an approved canonical event/schema document adds a name. Artifact events remain limited to actual product artifacts. Evaluation infrastructure has no business-state transition.

Failure before all result rows commit produces `EvaluationFailureV1`, rejects promotion, and retains the prior active registry entry. A missing/corrupt result is not scored as zero and averaged; it is a failed suite. Persistence retry uses exact case/config/evaluator idempotency and first verifies whether the immutable row already exists.

## Ordered implementation tasks

- [ ] **Implement strict eval models and offline loader —** Input: AGENT-01 schemas, DB-01/04 digest contract, fixture manifests. Operation: validate every case/fixture/hash/sensitivity class and build Pydantic Evals datasets with network disabled. Output: immutable suite objects. Test evidence: golden vectors, tamper/live-network/missing-fixture tests. Failure behavior: `DATASET_INVALID`/`FIXTURE_HASH_MISMATCH`; no case runs.
- [ ] **Implement deterministic evaluators/scoring —** Input: typed output, expected labels/rubric and provider ledger. Operation: calculate hard gates, weighted case score, confusion/citation/span/calibration metrics, p10/p95/cost and three-run stability exactly. Output: `EvaluationScoresV1`/`SuiteRunSummaryV1`. Test evidence: hand-calculated boundary vectors at every threshold. Failure behavior: invalid/missing score fails the suite.
- [ ] **Implement eight complete suites —** Input: the exact case/adversarial allocations above. Operation: create synthetic/redacted/recorded provider fixtures, independent labels and sensitivity reviews. Output: 552 total versioned cases. Test evidence: count/tag/provenance/hash coverage and zero-network execution. Failure behavior: affected suite cannot promote.
- [ ] **Implement comparison and operator promotion —** Input: the candidate summary across three repetitions, baseline results, dependency/authority/cost evidence. Operation: enforce all absolute/regression gates, render operator checklist, and write immutable `PromotionManifestV1`/registry pointer only on approval. Output: one eligible configuration or explicit rejection. Test evidence: threshold equality, one-unit failure, concurrent/stale registry and tamper cases. Failure behavior: prior promotion remains.
- [ ] **Implement runtime selection/monitoring/rollback —** Input: active manifest and specialist rolling windows. Operation: verify hashes at startup, attach config to every run, evaluate immediate/windowed triggers, and version-route rollback. Output: reproducible selection and bounded recovery. Test evidence: manifest drift, hard incident, two-window breach and incompatible in-flight run drills. Failure behavior: affected stage pauses; no fallback to unpromoted config.

## Test strategy

- **Digest `test_eval_cases_expected_scores_and_manifests_use_db01_envelope`.**
- **Offline `test_all_552_cases_run_with_network_and_credentials_disabled`.**
- **Scoring `test_weighted_score_p10_p95_ece_and_decimal_threshold_boundaries`.**
- **Safety `test_one_hard_failure_forces_zero_case_and_rejects_promotion`.**
- **Regression `test_candidate_cannot_trade_quality_regression_for_cost`.**
- **Versioning `test_any_prompt_model_tool_schema_validator_change_requires_new_config_hash_and_suite`.**
- **Promotion `test_registry_accepts_only_operator_reviewed_manifest_with_matching_hashes`.**
- **Rollback `test_hard_and_two_window_triggers_restore_prior_config_without_rewriting_history`.**
- **Authority `test_eval_and_promoted_agent_graph_has_no_state_gmail_sendgateway_or_credentials`.**
- **Persistence `test_case_run_result_ledger_cost_and_manifest_reconcile_exactly`.**

## Security, privacy, compliance, idempotency, observability, and cost

Fixtures contain synthetic/redacted data by default and never secrets, OAuth tokens, live recipient addresses or raw production message bodies. Restricted fixtures stay encrypted and access-audited. Prompt injection is data, never evaluator instruction. Case/config/evaluator hashes and DB uniques make reruns idempotent. Telemetry exposes suite/case/config/model/prompt/tool/schema/validator versions/hashes, pass/reasons, component scores, duration/tokens/tool calls/provider cost/ILS projection and fixture mode; it excludes fixture content and hidden reasoning.

The runner reserves a suite budget equal to the sum of per-case ceilings times three, then stops before an unreserved call. Offline fixture provider entries still record zero or recorded reference cost explicitly; promotion performance thresholds use replayed candidate cost metadata under the fixture contract, not invented current pricing.

## Failure, rollback, and operator recovery

Corrupt dataset, dependency drift, provider-fixture mismatch, score exception, timeout, incomplete persistence, threshold/regression failure, or nonreproducibility rejects the candidate. Operator recovery verifies manifests/lock/hash rows, reruns from clean offline fixtures, and either fixes through a new version or keeps the prior promotion. Never delete a hard case, relax a threshold, re-label after seeing candidate output, or activate an unpromoted config to unblock a workflow.

## Acceptance and retained evidence

- [ ] Exactly eight suites and 552 cases exist with the stated allocations, fixtures, provenance, hashes, sensitivity and adversarial coverage.
- [ ] Exact Pydantic models, deterministic scoring functions, three-run stability, absolute/regression/cost gates, operator review and rollback are executable.
- [ ] Prompt/model/tool/input/output/validator/suite/evaluator/dependency/provider-fixture versions and hashes reproduce every result.
- [ ] DB-04 cases/results, run/provider ledger, cost, manifests, registry and retained evidence reconcile without invented event names.
- [ ] Promotion grants execution eligibility only; no agent/eval path can validate/accept product artifacts, mutate state, decide policy/approval/budget/suppression, call Gmail/`SendGateway`, or receive credentials.

Retain all manifests/case/rubric/fixture/config/prompt/schema/evaluator/dependency hashes, three-run raw results, confusion/citation/span/calibration reports, hard/adversarial outputs, authority graph, ledger/cost/ILS reconciliation, operator review, promotion/rejection/rollback manifests, startup hash checks, and rollback drills under `EVALUATION_VERSIONED` plus DB-05 safety records where applicable.

## Dependencies and next deliverable

AGENT-10 depends on all specialist contracts and recorded Task 4 fixture adapters. Passing every suite and committing operator-reviewed promotion manifests completes the agent portion of M3 and unlocks the relevant finite workflow prerequisites: AGENT-02/03/04 for WF-03, AGENT-05/06 for WF-04, AGENT-07/08 for WF-05, and AGENT-09 for experiment evaluation. Provider implementation remains Task 4.
