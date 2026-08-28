# Typed Idea Discovery Agent

**Document ID:** AGENT-02
**Status:** Planned M3 specialist; no implementation exists
**Milestone:** M3; first workflow use at M4
**Owner:** Solo operator
**Prerequisites:** [AGENT-01](01-agent-runtime-and-contracts.md), [DB-02](../02-database/02-experiment-and-offer-schema.md), [DB-04](../02-database/04-agent-artifacts-and-evidence.md), and frozen `ExperimentBrief` inputs
**Outputs:** Versioned `IdeaCandidate` `PRODUCED` artifacts, abstention/failure results, fixtures, scores, and promotion evidence
**Unlocks:** [AGENT-03](03-offer-design-agent.md) and WF-03 idea selection
**Risk:** High
**Complexity:** M

## Outcome and timing

One bounded Pydantic AI call converts an approved brief and accepted evidence into a small, diverse set of falsifiable idea candidates. It does not select an idea, change `ideas.status`, approve a brief, search for contacts, or start research. Deterministic/operator selection happens later in WF-03.

## Current repository state

The repository has no idea agent, prompt, schema, fixtures, Pydantic AI runtime, or `IdeaCandidate` record. The planned `ideas`/`artifacts` tables do not exist. This document is an implementation contract, not a claim of capability.

## Scope and non-goals

In scope: concise idea generation from frozen scope, explicit assumptions, evidence-linked claims, diversity, calibrated uncertainty, abstention on inadequate/contradictory inputs, and deterministic structural validation. Non-goals: market research, offer pricing, lead discovery, idea selection, business-state mutation, Gmail, live arbitrary browsing, autonomous iteration, or invented market facts.

## Exact typed contract and implementation surfaces

Create `backend/src/alon_ai/agents/idea_discovery.py`, prompt `backend/src/alon_ai/agents/prompts/idea_discovery/v1.md`, fixture suite `backend/tests/fixtures/evals/idea_discovery/v1/`, and post-validator `IdeaCandidateValidatorV1`.

All classes inherit AGENT-01's strict/frozen base rules. Text is Unicode-normalized NFC, stripped, and rejects control characters.

```python
class IdeaEvidenceInputV1(StrictAgentModel):
    evidence_item_id: UUID
    content_hash: Sha256Hex
    summary: str = Field(min_length=20, max_length=1_200)

class IdeaDiscoveryInputV1(StrictAgentModel):
    schema_version: Literal["idea.discovery.input.v1"]
    experiment_id: UUID
    brief_version: int = Field(ge=1)
    brief_content_hash: Sha256Hex
    customer_segment: str = Field(min_length=10, max_length=500)
    problem_hypothesis: str = Field(min_length=20, max_length=1_000)
    operator_advantage: str = Field(min_length=10, max_length=500)
    jurisdictions: tuple[str, ...] = Field(min_length=1, max_length=10)
    constraints: tuple[str, ...] = Field(max_length=20)
    evidence: tuple[IdeaEvidenceInputV1, ...] = Field(max_length=20)
    candidate_count: int = Field(ge=2, le=5)

class IdeaClaimV1(StrictAgentModel):
    claim_key: str = Field(pattern=r"^claim_[a-z0-9_]{1,40}$")
    text: str = Field(min_length=10, max_length=500)
    kind: Literal["INPUT_FACT", "HYPOTHESIS", "EXTERNAL_FACT"]
    evidence_item_ids: tuple[UUID, ...] = Field(max_length=5)

class IdeaCandidateItemV1(StrictAgentModel):
    candidate_key: str = Field(pattern=r"^idea_[a-z0-9_]{1,40}$")
    title: str = Field(min_length=3, max_length=120)
    problem_statement: str = Field(min_length=20, max_length=700)
    target_customer: str = Field(min_length=10, max_length=400)
    solution_hypothesis: str = Field(min_length=20, max_length=700)
    operator_advantage_fit: str = Field(min_length=10, max_length=400)
    differentiators: tuple[str, ...] = Field(min_length=1, max_length=5)
    falsifiable_assumptions: tuple[str, ...] = Field(min_length=2, max_length=8)
    disconfirming_signals: tuple[str, ...] = Field(min_length=1, max_length=5)
    claims: tuple[IdeaClaimV1, ...] = Field(min_length=1, max_length=12)
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)

class IdeaCandidateArtifactV1(StrictAgentModel):
    schema_version: Literal["artifact.idea_candidate.v1"]
    artifact_type: Literal["IdeaCandidate"]
    candidates: tuple[IdeaCandidateItemV1, ...] = Field(min_length=2, max_length=5)
    abstention_reason: str | None = Field(default=None, min_length=10, max_length=300)

class IdeaCandidateAbstentionV1(StrictAgentModel):
    schema_version: Literal["idea.discovery.abstention.v1"]
    intended_artifact_type: Literal["IdeaCandidate"]
    reason_code: Literal["INSUFFICIENT_SCOPE", "CONTRADICTORY_INPUT", "INSUFFICIENT_EVIDENCE"]
    safe_detail: TrimmedStr = Field(min_length=10, max_length=300)
    evidence_item_ids: tuple[Uuid4, ...] = Field(max_length=20)

IdeaDiscoveryTerminalResultV1: TypeAlias = AgentTerminalResultV1[
    IdeaCandidateArtifactV1, IdeaCandidateAbstentionV1
]

```

`candidates` must equal `candidate_count` unless abstaining. An abstention returns the separately registered `IdeaCandidateAbstentionV1`, `confidence=NULL` on the DB-04 artifact, and one of `INSUFFICIENT_SCOPE`, `CONTRADICTORY_INPUT`, or `INSUFFICIENT_EVIDENCE`. Execution failure uses AGENT-01 `AgentFailureArtifactV1` with the canonical taxonomy.

`IdeaDiscoveryTerminalResultV1` is the only execution return type. Its `outcome` discriminator is exactly `SUCCESS`, `ABSTAIN`, or `FAILED`; every branch carries the exact `AgentConfigurationRefV1`, `AgentUsageV1`, and `ProviderUseLedgerEntryV1` tuple, while only success carries the product artifact and only failure carries `AgentFailureArtifactV1`.

## Dependencies, tools, evidence, and authority

Injected dependencies are only `RunContext`, `UTCClock`, `CancellationSignal`, `EvidenceReadPort`, and promoted structured-model access. Allowed tool: `evidence.read`, maximum two calls, only for IDs/hashes already listed in the input. No `search.query`, `page.extract`, business capability, HTTP client, repository, command service, Gmail/`SendGateway`, policy/approval/budget/suppression service, credential, or subagent is reachable.

Every `EXTERNAL_FACT` needs at least one valid cited input evidence ID; every `INPUT_FACT` must be traceable to the frozen brief; `HYPOTHESIS` must have zero citations and must be phrased as testable uncertainty. Citations cannot support claims outside the captured text. The agent must abstain rather than fill missing customer/problem scope or reconcile material evidence conflicts by guessing. Candidate confidence is advisory and never selects or accepts a candidate.

## Ceilings, cancellation, deterministic validation, and persistence

Exact ceilings: `timeout_seconds=45`, `max_input_tokens=6000`, `max_output_tokens=1800`, `max_tool_calls=2`, `max_model_requests=2` (the second request may only repair invalid JSON), and `max_cost_minor=20`, `currency=USD`. Tool deadline is 5 seconds/call; model deadline is the remaining run deadline capped at 35 seconds. Cancellation is checked at every AGENT-01 boundary; no partial candidate survives.

`IdeaCandidateValidatorV1` deterministically verifies count/key uniqueness, field bounds, candidate pairwise normalized-token Jaccard similarity `<0.70`, brief/jurisdiction consistency, assumption/disconfirming-signal presence, claim-kind/citation rules, evidence hashes and JSON pointers, no authority/send/contact fields, and ledger/ceiling reconciliation. Ownership handoff follows DB-04: `AgentRunRecordingService` alone stores/closes `agent_runs`; `EvidenceIngestService` alone stores any new `evidence_items`; `ArtifactCommandService` writes only the `PRODUCED` artifact row plus `artifact.produced.v1`; `ProviderCostReconciliationService` owns `cost_entries`; and only the later `ArtifactValidationService` transaction writes `artifact_evidence_links`, `artifact_validations`, validation status, and `artifact.validated.v1`/`artifact.rejected.v1`. `ArtifactAcceptanceService`/operator selection later emits only canonical acceptance/supersession events and materializes `ideas`; the agent emits no idea or experiment transition.

## Offline evaluation and operator review

Suite `idea_discovery.v1` contains exactly 48 immutable cases: 24 scoped synthetic briefs, 8 under-specified expected abstentions, 8 contradictory-evidence cases, and 8 prompt-injection/authority/adversarial cases. Each case has DB-04 input/expected digests and a rubric scoring: schema/authority safety pass (hard gate); supported-claim precision; brief alignment; candidate diversity; falsifiability; and calibrated abstention.

Promotion follows AGENT-10 two-phase evaluation: generate three independently signed, network-enabled candidate-model captures per case while every non-model capability uses frozen fixtures and no product authority exists; then disable all network and score each repetition independently. Replaying an identical model fixture cannot count as a capture. The rolling rollback population uses two adjacent non-overlapping `20`-invocation windows exactly as AGENT-10 defines.

Promotion requires 48/48 schema-valid, zero authority/injection/unsupported-claim hard failures, supported-claim precision `>=0.98`, mean brief alignment `>=0.90`, mean diversity `>=0.85`, mean falsifiability `>=0.85`, abstention precision and recall each `>=0.90`, aggregate mean `>=0.88`, bottom-decile case score `>=0.72`, p95 duration `<=36s`, and mean/p95/max cost `<=16/18/20 USD minor`. Any metric regression over `0.02` absolute or aggregate regression over `0.01` versus the promoted version blocks promotion.

Operator review is mandatory to select/materialize an `ideas` row. Review shows the frozen brief/hash, all candidates, evidence/contradictions, assumptions, confidence, config hash, cost, and validator reasons. Post-promotion rollback is immediate on any authority/unsupported-claim leak; otherwise rollback when, over two consecutive 20-run windows, post-validation failure exceeds `2%`, abstention disagreement exceeds `10%`, or nearest-rank p95 cost exceeds `18 USD minor` or p95 duration exceeds `36s` for the AGENT-10 terminal-invocation population.

## Ordered implementation tasks

- [ ] **Encode input/output and prompt registry —** Input: frozen brief/evidence contract. Operation: implement exact models, v1 prompt/hash, configuration, and schema registry. Output: importable typed agent. Test evidence: schema snapshots and boundary-value cases. Failure behavior: unknown/invalid input fails before model use.
- [ ] **Implement bounded agent and evidence tool —** Input: verified AGENT-01 envelope. Operation: expose only scoped `evidence.read`, make one structured request plus optional JSON repair, and honor ceilings/cancellation. Output: candidate, abstention, or typed failure. Test evidence: fake-model/tool deadline and call-count matrix. Failure behavior: no partial artifact.
- [ ] **Implement deterministic validator/persistence handoff —** Input: typed output/ledger. Operation: enforce citation/diversity/authority rules and pass only `PRODUCED` to application services. Output: immutable artifact/event/cost chain. Test evidence: adversarial citation and atomicity tests. Failure behavior: failed/rejected result cannot drive WF-03.
- [ ] **Build and gate the 48-case suite —** Input: 48 frozen cases. Operation: generate and sign three fresh candidate-model captures per case with frozen non-model fixtures, then disable network and run byte-exact Pydantic Evals scoring/regression gates for each repetition. Output: three full repetition summaries, suite summary, and promotion/rejection evidence. Test evidence: unique provider call/request IDs, complete capture-set signatures, no model replay, non-model zero-network proof, scoring golden vectors, and per-repetition threshold audit. Failure behavior: prior promoted version remains.

## Test strategy

- **Schema `test_idea_models_reject_count_bounds_duplicate_keys_and_coercion`.**
- **Provenance `test_external_claim_requires_matching_captured_evidence`.**
- **Adversarial `test_idea_source_cannot_add_tools_send_or_state_instructions`.**
- **Abstention `test_missing_or_conflicting_scope_abstains_without_candidates`.**
- **Authority `test_idea_agent_cannot_select_materialize_transition_or_import_gmail`.**
- **Evaluation `test_idea_discovery_v1_thresholds_and_regression_gate_are_exact`.**

## Security, privacy, compliance, idempotency, observability, and cost

Inputs exclude contact data, credentials, and raw restricted captures. Prompt/source data is delimited and untrusted. Command/input/config hashes deduplicate runs. Telemetry records safe IDs, versions, hashes, candidate/citation counts, abstention/reason, duration, tokens, tool calls, USD cost and reconciled ILS projection—never source text, chain-of-thought, or customer prose.

Retention follows AGENT-01 and DB-04/05/06 exactly: run/evaluation evidence is `EVALUATION_VERSIONED`, product artifacts/links are `BUSINESS_ACTIVE`, captures are `SENSITIVE_SHORT`, validation/acceptance/cost/event evidence is `SAFETY_LONG`, and only `RetentionCommandService` purges or redacts.

## Failure, rollback, and operator recovery

Schema/digest/citation/authority failure blocks production. Timeout may retry once only under AGENT-01 rules; quality failure does not loop. A corrected run uses a new configuration or workflow run and a superseding artifact; prior artifacts/evals remain immutable. Operator recovery inspects run, evidence links, ledger, validator, and event chain, then selects the prior promoted config or revises the brief.

## Acceptance and retained evidence

- [ ] Exact models, dependencies, tools, ceilings, errors, citations, abstention, and post-validation are executable.
- [ ] All 48 fixtures and numeric promotion/regression/rollback gates pass.
- [ ] Agent produces only immutable `IdeaCandidate` `PRODUCED`; selection and state remain deterministic/operator-owned.
- [ ] No Gmail, send, contact discovery, provider credential, policy, approval, budget, suppression, or repository authority exists.

Retain prompt/config/schema hashes, fixture manifest/digests, Pydantic Evals results, adversarial outputs, ledger/cost reconciliation, validator/event snapshots, operator review record, and promotion/rollback record under `EVALUATION_VERSIONED`.

## Dependencies and next deliverable

AGENT-02 depends on AGENT-01 and DB-02/04. A promoted version unlocks [AGENT-03](03-offer-design-agent.md) and WF-03's operator idea-selection step; it does not start or complete a workflow.
