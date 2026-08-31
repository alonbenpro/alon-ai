# Typed Lead Qualification Agent

**Document ID:** AGENT-06
**Status:** Planned M3 specialist; no implementation exists
**Milestone:** M3; first workflow use at M5
**Owner:** Solo operator
**Prerequisites:** [AGENT-01](01-agent-runtime-and-contracts.md), promoted [AGENT-05](05-lead-research-agent.md), DB-03/DB-04, and a frozen deterministic criteria version
**Outputs:** Evidence-linked `QualificationAssessment` `PRODUCED` artifact, abstention/failure results, labeled fixtures, scores, and promotion evidence
**Unlocks:** WF-04 deterministic qualification gate
**Risk:** Critical
**Complexity:** M

## Outcome and timing

The agent maps accepted `LeadEvidence` to explicit per-criterion findings. It does not calculate the authoritative weighted score, set `gate_passed`, emit `lead.qualified.v1`/`lead.disqualified.v1`, or change `LeadState`. `LeadQualificationService` deterministically applies frozen weights, completeness, threshold, suppression and reason rules after validation.

## Current repository state

There is no criteria registry, qualification agent, labeled dataset, lead assessment, deterministic gate, or lead state. All are planned.

## Scope and non-goals

In scope: criterion-by-criterion `MET`/`NOT_MET`/`UNKNOWN`, evidence references, contradictions, confidence, missing evidence, and abstention. Non-goals: authoritative scoring/gating, default qualification, criteria invention, suppression/policy/compliance decisions, contact research, drafting, Gmail, state mutation, or autonomous re-research.

## Exact typed contract and implementation surfaces

Create `agents/lead_qualification.py`, `agents/prompts/lead_qualification/v1.md`, `QualificationAssessmentValidatorV1`, and `backend/tests/fixtures/evals/lead_qualification/v1/`.

```python
class QualificationCriterionInputV1(StrictAgentModel):
    criterion_key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,40}$")
    description: str = Field(min_length=10, max_length=500)
    evidence_requirement: str = Field(min_length=10, max_length=500)
    weight_micros: int = Field(ge=0, le=1_000_000)
    required: bool

class LeadQualificationInputV1(StrictAgentModel):
    schema_version: Literal["lead.qualification.input.v1"]
    experiment_id: UUID
    lead_id: UUID
    business_id: UUID
    business_identity_key: Sha256Hex
    lead_evidence_artifact_id: UUID
    lead_evidence_content_hash: Sha256Hex
    criteria_version: VersionId
    criteria_hash: Sha256Hex
    criteria: tuple[QualificationCriterionInputV1, ...] = Field(min_length=1, max_length=20)
    evidence_item_ids: tuple[UUID, ...] = Field(min_length=1, max_length=50)

class CriterionFindingV1(StrictAgentModel):
    criterion_key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,40}$")
    status: Literal["MET", "NOT_MET", "UNKNOWN"]
    rationale: str = Field(min_length=10, max_length=500)
    evidence_item_ids: tuple[UUID, ...] = Field(max_length=5)
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)

class QualificationAssessmentArtifactV1(StrictAgentModel):
    schema_version: Literal["artifact.qualification_assessment.v1"]
    artifact_type: Literal["QualificationAssessment"]
    lead_id: UUID
    business_id: UUID
    business_identity_key: Sha256Hex
    criteria_version: VersionId
    criteria_hash: Sha256Hex
    findings: tuple[CriterionFindingV1, ...] = Field(min_length=1, max_length=20)
    contradictions: tuple[str, ...] = Field(max_length=10)
    missing_evidence: tuple[str, ...] = Field(max_length=20)
    overall_confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)

class QualificationAssessmentAbstentionV1(StrictAgentModel):
    schema_version: Literal["lead.qualification.abstention.v1"]
    intended_artifact_type: Literal["QualificationAssessment"]
    reason_code: Literal["CRITERIA_INVALID", "IDENTITY_CONFLICT", "EVIDENCE_MISSING", "MATERIAL_CONTRADICTION", "ALL_FINDINGS_UNKNOWN"]
    safe_detail: TrimmedStr = Field(min_length=10, max_length=300)
    evidence_item_ids: tuple[Uuid4, ...] = Field(max_length=20)

LeadQualificationTerminalResultV1: TypeAlias = AgentTerminalResultV1[
    QualificationAssessmentArtifactV1, QualificationAssessmentAbstentionV1
]

```

Input weights must sum exactly `1_000_000`. Output finding keys must equal input keys exactly once. `MET`/`NOT_MET` require at least one cited evidence ID; `UNKNOWN` may have none and cannot be converted to `MET` by confidence. `QualificationAssessmentAbstentionV1` reasons are `CRITERIA_INVALID`, `IDENTITY_CONFLICT`, `EVIDENCE_MISSING`, `MATERIAL_CONTRADICTION`, or `ALL_FINDINGS_UNKNOWN`; DB confidence is `NULL`. Execution failures use AGENT-01 taxonomy.

`LeadQualificationTerminalResultV1` is the only execution return type. Its `outcome` discriminator is exactly `SUCCESS`, `ABSTAIN`, or `FAILED`; every branch carries the exact `AgentConfigurationRefV1`, `AgentUsageV1`, and `ProviderUseLedgerEntryV1` tuple, while only success carries the product artifact and only failure carries `AgentFailureArtifactV1`.

## Dependencies, tools, evidence, and authority

Injected dependencies: AGENT-01 context/clock/cancellation, `EvidenceReadPort`, and promoted model. Only `evidence.read` is allowed, maximum two calls for declared IDs. No search, page, business/contact, HTTP, repository/command/lead service, criteria/score gate, suppression/policy/approval/budget/control, Gmail/`SendGateway`, provider credential, or retry planner is reachable.

Evidence must be accepted, hash-matched, and linked to the same lead/business identity. Contradiction is surfaced, never silently resolved. The agent must use `UNKNOWN`/abstention when evidence does not satisfy the frozen requirement. Confidence is descriptive and not an input to authoritative score unless the frozen deterministic criteria explicitly names a non-model numeric rule; v1 does not.

## Ceilings, cancellation, deterministic validation, and persistence

Ceilings: `timeout_seconds=45`, 7000 input tokens, 1500 output tokens, 2 tool calls, 2 model requests (JSON repair only), and 15 USD minor. Evidence deadline 5s; model <=35s within the global deadline. AGENT-01 cancellation/timeout rules apply.

`QualificationAssessmentValidatorV1` checks exact identity/criteria tuples, weight sum, one finding per criterion, evidence ownership/hash/citation, required-evidence behavior, contradiction/missing-evidence honesty, no authoritative score/gate/state/send fields, and ledger totals. Ownership handoff follows DB-04: `AgentRunRecordingService` alone stores/closes `agent_runs`; `EvidenceIngestService` alone stores any new `evidence_items`; `ArtifactCommandService` writes only the `PRODUCED` artifact row plus `artifact.produced.v1`; `ProviderCostReconciliationService` owns `cost_entries`; and only the later `ArtifactValidationService` transaction writes `artifact_evidence_links`, `artifact_validations`, validation status, and `artifact.validated.v1`/`artifact.rejected.v1`. `LeadQualificationService` then independently consumes only a validated/accepted artifact, computes DB-03 `lead_assessments.score/reason_codes/gate_passed`, applies suppression, transitions state, and emits canonical `lead.qualified.v1` or `lead.disqualified.v1`.

## Offline evaluation and operator review

Suite `lead_qualification.v1` has exactly 80 labeled cases: 32 clearly meeting/not meeting mixed criteria, 16 threshold-boundary cases, 12 missing/contradictory cases, 8 identity/criteria-splice cases, and 12 injection/default-qualify/suppression/send-authority attacks. Scores: hard schema/identity/authority safety; per-criterion macro F1 excluding expected `UNKNOWN`; `UNKNOWN` precision/recall; citation precision/recall; contradiction recall; deterministic-gate agreement after applying the frozen scoring function.

Promotion follows AGENT-10 two-phase evaluation: generate three independently signed, network-enabled candidate-model captures per case while every non-model capability uses frozen fixtures and no product authority exists; then disable all network and score each repetition independently. Replaying an identical model fixture cannot count as a capture. The rolling rollback population uses two adjacent non-overlapping `30`-invocation windows exactly as AGENT-10 defines.

Promotion requires 80/80 schema-valid; zero hard failures; macro F1 `>=0.93`; `UNKNOWN` precision/recall each `>=0.95`; citation precision `>=0.99` and recall `>=0.98`; contradiction recall `>=0.95`; deterministic-gate agreement `>=0.98` with zero false-qualified cases on required-criterion failures; aggregate `>=0.93`; bottom decile `>=0.80`; p95 duration `<=36s`; mean/p95/max cost `<=12/14/15 USD minor`. Any safety/gate false-positive regression blocks; any other component regression `>0.01` or aggregate `>0.005` blocks.

Operator review is mandatory for identity/criteria conflict, contradiction, any required `UNKNOWN`, score within `0.05` of the deterministic threshold, or any proposed `QUALIFIED` lead before M6 campaign admission. Immediate rollback follows any false-qualified required failure, identity splice, suppression/send authority, or injection violation; otherwise two consecutive 30-run windows with deterministic disagreement `>2%`, post-validation failure `>1%`, operator correction `>5%`, or nearest-rank p95 cost `>14 USD minor` or p95 duration `>36s` over the AGENT-10 terminal-invocation population trigger rollback.

## Ordered implementation tasks

- [ ] **Encode frozen criteria/assessment schemas —** Input: criteria registry and DB-03 assessment fields. Operation: implement exact strict models, prompt/config/hash registry. Output: typed contract. Test evidence: weight/key/identity boundary snapshots. Failure behavior: invalid criteria blocks model.
- [ ] **Implement bounded evidence classification —** Input: verified envelope/accepted evidence. Operation: expose only `evidence.read`, one structured call plus JSON repair, ceilings/cancellation. Output: assessment/abstention/failure. Test evidence: fake-model/evidence boundary matrix. Failure behavior: no assessment row/state.
- [ ] **Implement validator and deterministic gate handoff —** Input: output/ledger/frozen criteria. Operation: validate tuple/citations then hand to separate weighted gate/application command. Output: `PRODUCED` artifact followed by independent accepted/rejected assessment/state. Test evidence: threshold, suppression, and transaction/event tests. Failure behavior: pending/disqualified per explicit deterministic rule, never default qualify.
- [ ] **Build and gate 80-case labeled suite —** Input: frozen labels/rubric. Operation: generate and sign three fresh candidate-model captures per case with frozen non-model fixtures, then disable network and run byte-exact Pydantic Evals scoring/regression gates for each repetition. Output: three full repetition summaries, suite summary, and promotion/rejection evidence. Test evidence: unique provider call/request IDs, complete capture-set signatures, no model replay, non-model zero-network proof, scoring golden vectors, and per-repetition threshold audit. Failure behavior: prior promoted version remains.

## Test strategy

- **Schema `test_qualification_requires_exact_criteria_keys_and_weight_sum`.**
- **Evidence `test_met_or_not_met_requires_same_lead_capture`.**
- **Boundary `test_unknown_and_threshold_cases_never_default_qualify`.**
- **Authority `test_agent_cannot_score_gate_suppress_transition_or_send`.**
- **Adversarial `test_criteria_or_evidence_cannot_instruct_default_qualification`.**
- **Evaluation `test_qualification_v1_labeled_thresholds_and_zero_false_positive_gate`.**

## Security, privacy, compliance, idempotency, observability, and cost

The prompt receives minimized business evidence, no contact/credential/content. Sources are untrusted. Input/config hashes make runs reproducible. Telemetry includes safe IDs/hashes, finding/unknown/contradiction counts, validator/gate disagreement, abstention, duration/tokens/cost and ILS projection; no source text or hidden reasoning.

Retention follows AGENT-01 and DB-04/05/06 exactly: run/evaluation evidence is `EVALUATION_VERSIONED`, product artifacts/links are `BUSINESS_ACTIVE`, captures are `SENSITIVE_SHORT`, validation/acceptance/cost/event evidence is `SAFETY_LONG`, and only `RetentionCommandService` purges or redacts.

## Failure, rollback, and operator recovery

Invalid criteria/identity/evidence, timeout, or cost failure cannot create an assessment/state. Disagreement remains visible and may retain `QUALIFICATION_PENDING` or deterministically disqualify according to the frozen rule. Correction uses new criteria/config/artifact/assessment versions; operator reviews immutable traces and rolls back to the prior promoted config.

## Acceptance and retained evidence

- [ ] Exact models, tools, evidence/confidence/abstention, ceilings/cancellation, failure, validator, deterministic gate, persistence/event mapping are implemented.
- [ ] All 80 cases meet numeric promotion/regression/rollback thresholds, including zero hard false-qualified failures.
- [ ] Agent produces only immutable `QualificationAssessment` `PRODUCED`; `LeadQualificationService` alone scores/gates/transitions.
- [ ] No criteria invention, identity merge, contact/search, suppression/policy/approval/budget, state, Gmail/send, repository, or credential authority exists.

Retain criteria/schema/prompt/config hashes, labeled fixtures/digests, eval/confusion matrices, adversarial outputs, ledger/cost, validator/gate/event traces, operator review, promotion/rollback records.

## Dependencies and next deliverable

A promoted AGENT-06 unlocks WF-04's deterministic qualification gate and M5 evaluation. `QUALIFIED` still grants no send authority and does not unlock Gmail by itself.
