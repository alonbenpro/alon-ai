# Typed Market Research Agent

**Document ID:** AGENT-04
**Status:** Planned M3 specialist; no implementation exists
**Milestone:** M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `AGENT-04-T01 -> AGENT-04-T02 -> AGENT-04-T03 -> AGENT-04-T04`; cross-document task Inputs `AGENT-04-T01 <- DB-02-T03; AGENT-04-T02 <- AGENT-01-T01,AGENT-01-T02; AGENT-04-T03 <- BACKEND-01-T01,DB-04-T04,OBS-03-T02,AGENT-01-T04,DB-04-T03; AGENT-04-T04 <- AGENT-10-T01,AGENT-10-T03,AGENT-10-T04`. Descriptive source authorities/resources (not whole-document completion dependencies): [AGENT-01](01-agent-runtime-and-contracts.md), promoted [AGENT-03](03-offer-design-agent.md), DB-04 evidence records, and Task 4 recorded search/extraction capabilities
**Outputs:** Cited `MarketEvidence` `PRODUCED` artifact, captured evidence requests, abstention/failure results, fixtures, scores, and promotion evidence
**Unlocks:** WF-03 market-evidence and evidence-bundle steps
**Risk:** High
**Complexity:** L

## Outcome and timing

The agent builds a bounded, contradiction-aware market evidence artifact for one offer. It may request read-only search and extraction capabilities, but only application/provider services capture `evidence_items`; the agent cannot browse arbitrarily, claim legal compliance, decide market viability, or transition the experiment.

## Current repository state

There is no market agent, search/page adapter, evidence ingest service, capture store, prompt, fixture, or evaluation. Provider capabilities below are Task 3 consumer requirements only; Task 4 owns their exact protocols/adapters without changing semantics.

## Scope and non-goals

In scope: bounded query plan, source-quality/recency labeling, cited claims, contradictions, gaps, confidence and abstention, and minimal evidence capture. Non-goals: unrestricted crawling, paywall/login/browser action, contact collection, authoritative total-addressable-market estimates from weak inputs, legal conclusions, offer acceptance, leads, Gmail, or autonomous query loops.

## Exact typed contract and implementation surfaces

Create `agents/market_research.py`, `agents/prompts/market_research/v1.md`, `MarketEvidenceValidatorV1`, and `backend/tests/fixtures/evals/market_research/v1/`.

```python
class MarketResearchInputV1(StrictAgentModel):
    schema_version: Literal["market.research.input.v1"]
    experiment_id: UUID
    offer_artifact_id: UUID
    offer_content_hash: Sha256Hex
    customer_segment: str = Field(min_length=10, max_length=500)
    problem_hypothesis: str = Field(min_length=20, max_length=700)
    offer_summary: str = Field(min_length=20, max_length=1_000)
    jurisdictions: tuple[str, ...] = Field(min_length=1, max_length=10)
    allowed_domains: tuple[str, ...] = Field(min_length=1, max_length=50)
    blocked_domains: tuple[str, ...] = Field(max_length=50)
    query_limit: int = Field(ge=1, le=6)
    page_limit: int = Field(ge=1, le=8)
    evidence_item_ids: tuple[UUID, ...] = Field(max_length=30)
    as_of: datetime

class MarketClaimV1(StrictAgentModel):
    claim_key: str = Field(pattern=r"^claim_[a-z0-9_]{1,40}$")
    text: str = Field(min_length=10, max_length=700)
    evidence_item_ids: tuple[UUID, ...] = Field(min_length=1, max_length=5)
    source_count: int = Field(ge=1, le=5)
    quality: Literal["PRIMARY", "AUTHORITATIVE_SECONDARY", "OTHER_SECONDARY"]
    temporal_fit: Literal["CURRENT", "DATED_BUT_RELEVANT", "UNKNOWN"]
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)

class MarketEvidenceArtifactV1(StrictAgentModel):
    schema_version: Literal["artifact.market_evidence.v1"]
    artifact_type: Literal["MarketEvidence"]
    research_questions: tuple[str, ...] = Field(min_length=2, max_length=6)
    claims: tuple[MarketClaimV1, ...] = Field(min_length=2, max_length=20)
    contradictions: tuple[str, ...] = Field(max_length=10)
    evidence_gaps: tuple[str, ...] = Field(max_length=10)
    market_signals: tuple[str, ...] = Field(min_length=1, max_length=10)
    disconfirming_signals: tuple[str, ...] = Field(min_length=1, max_length=10)
    overall_confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)

class MarketEvidenceAbstentionV1(StrictAgentModel):
    schema_version: Literal["market.research.abstention.v1"]
    intended_artifact_type: Literal["MarketEvidence"]
    reason_code: Literal["NO_ELIGIBLE_SOURCES", "MATERIAL_CONTRADICTION", "SOURCE_QUALITY_TOO_LOW", "BUDGET_EXHAUSTED"]
    safe_detail: TrimmedStr = Field(min_length=10, max_length=300)
    evidence_item_ids: tuple[Uuid4, ...] = Field(max_length=20)

MarketResearchTerminalResultV1: TypeAlias = AgentTerminalResultV1[
    MarketEvidenceArtifactV1, MarketEvidenceAbstentionV1
]

```

`MarketEvidenceAbstentionV1` uses `NO_ELIGIBLE_SOURCES`, `MATERIAL_CONTRADICTION`, `SOURCE_QUALITY_TOO_LOW`, or `BUDGET_EXHAUSTED` and persists DB confidence `NULL`. A numeric market-size claim is permitted only when its capture states units, geography, time period, and method; derived arithmetic is deterministic application code, not model arithmetic. Execution failure uses AGENT-01 taxonomy.

`MarketResearchTerminalResultV1` is the only execution return type. Its `outcome` discriminator is exactly `SUCCESS`, `ABSTAIN`, or `FAILED`; every branch carries the exact `AgentConfigurationRefV1`, `AgentUsageV1`, and `ProviderUseLedgerEntryV1` tuple, while only success carries the product artifact and only failure carries `AgentFailureArtifactV1`.

## Dependencies, tools, evidence, and authority

Injected dependencies: AGENT-01 context/clock/cancellation, `EvidenceReadPort`, `MarketSearchPort`, `PageExtractionPort`, and promoted structured-model access. Allowed capability tools are `evidence.read` (up to 2), `search.query` (up to 4 and no more than `query_limit`), and `page.extract` (up to 6 and no more than `page_limit`), total maximum 12. Search/extract receive approved domain/scheme/type/size/time policies and return capture metadata/evidence IDs, never credentials or raw provider objects.

Forbidden: arbitrary URL/tool creation, login/click/forms/scripts, unrestricted HTTP, personal/contact discovery, business enrichment, repository/command/state services, policy/approval/budget/suppression decisions, Gmail/`SendGateway`, OAuth/API credentials, source instructions, and recursive research loops.

Every claim has at least one captured ID/hash and a valid DB-04 link; confidence over `0.80` requires either one primary/official source or two independent eligible sources. Contradictions must be surfaced, not averaged away. Unknown publication date becomes `UNKNOWN`. The agent abstains if fewer than two eligible claims remain or a material claim depends solely on blocked/unsupported content.

## Ceilings, cancellation, deterministic validation, and persistence

Ceilings: `timeout_seconds=120`, `max_input_tokens=12000`, `max_output_tokens=2500`, `max_tool_calls=12`, `max_model_requests=2` (second only JSON repair), `max_cost_minor=75`, `currency=USD`. Search deadline is 8s, extraction 12s, evidence read 5s, and model 45s within the shared deadline. The workflow reserves cost before each provider call; cancellation stops before another call and discards uncaptured partial output.

`MarketEvidenceValidatorV1` verifies allow/block-domain rules, HTTPS/capture existence/hash/redaction, claim/source cardinality and independence, confidence rule, publication/retrieval timestamps, numeric-claim dimensions, contradictions/gaps, prompt-injection markers, no contact/authority fields, and ledger totals. Ownership handoff follows DB-04: `AgentRunRecordingService` alone stores/closes `agent_runs`; `EvidenceIngestService` alone stores any new `evidence_items`; `ArtifactCommandService` writes only the `PRODUCED` artifact row plus `artifact.produced.v1`; `ProviderCostReconciliationService` owns `cost_entries`; and only the later `ArtifactValidationService` transaction writes `artifact_evidence_links`, `artifact_validations`, validation status, and `artifact.validated.v1`/`artifact.rejected.v1`. Validators/acceptance services alone emit later artifact events; no lead/experiment/provider event is agent-authored.

`evidence_gaps=()` is the canonical valid representation when the bounded research found no identified gap; it is not padded with invented text. One through ten nonempty normalized gap strings are also valid. More than ten, empty-string members, duplicates, or a claimed complete result whose validator detects a missing required evidence dimension fails validation.

## Offline evaluation and operator review

Suite `market_research.v1` has exactly 60 cases: 24 normal recorded search/extraction sets, 8 stale-source cases, 8 contradictory sets, 8 numeric-unit/geography traps, and 12 injection/blocked-domain/contact/authority cases. All non-model responses are frozen immutable fixtures; only isolated candidate-model capture is network enabled. Scores: hard schema/authority/domain/injection safety, citation precision/recall, source-quality labeling, contradiction recall, temporal/numeric correctness, gap/abstention calibration.

Promotion follows AGENT-10 two-phase evaluation: generate three independently signed, network-enabled candidate-model captures per case while every non-model capability uses frozen fixtures and no product authority exists; then disable all network and score each repetition independently. Replaying an identical model fixture cannot count as a capture. The rolling rollback population uses two adjacent non-overlapping `20`-invocation windows exactly as AGENT-10 defines.

Promotion requires 60/60 schema-valid; zero hard failures; citation precision `>=0.99`, citation recall `>=0.97`, contradiction recall `>=0.95`, temporal/numeric correctness `>=0.98`, source-quality accuracy `>=0.95`, abstention precision/recall each `>=0.92`, aggregate `>=0.90`, bottom decile `>=0.75`, p95 duration `<=100s`, mean/p95/max cost `<=55/65/75 USD minor`. A component regression `>0.015` or aggregate regression `>0.01` blocks promotion.

Operator review is mandatory for material contradictions, any `OTHER_SECONDARY` source supporting a decision-critical claim, confidence below `0.70`, or numeric market sizing; otherwise deterministic acceptance may be configured but cannot materialize an offer/decision. Immediate rollback follows a domain/contact/authority/injection/unsupported-claim leak. Otherwise rollback after two consecutive 20-run windows with invalid citation `>1%`, post-validation failure `>2%`, operator source-quality reversal `>10%`, or nearest-rank p95 cost `>65 USD minor` or p95 duration `>100s` over the AGENT-10 terminal-invocation population.

## Ordered implementation tasks

<!-- roadmap-task id=AGENT-04-T01 milestone=M3 depends_on=DB-02-T03 mode=parallel locks=agent-runtime -->
- [ ] **Encode market schemas and source policy —** Input: offer/jurisdiction/provider requirements. Operation: implement exact models, prompt/config registry, domain/source rules. Output: typed contract. Test evidence: boundary/schema/source-policy snapshots. Failure behavior: invalid scope blocks tools.
<!-- roadmap-task id=AGENT-04-T02 milestone=M3 depends_on=AGENT-04-T01,AGENT-01-T01,AGENT-01-T02 mode=parallel locks=agent-runtime -->
- [ ] **Implement bounded read-only tool flow —** Input: verified envelope/reservations; AGENT-01 importable envelope contracts and immutable AgentDependenciesV1. Operation: execute finite allowed searches/extractions/evidence reads and one structured synthesis. Output: evidence, abstention, or failure plus ledger. Test evidence: recorded provider timeout/cancel/cap matrix. Failure behavior: no further call or partial artifact.
<!-- roadmap-task id=AGENT-04-T03 milestone=M3 depends_on=AGENT-04-T02,BACKEND-01-T01,DB-04-T04,OBS-03-T02,AGENT-01-T04,DB-04-T03 mode=parallel locks=agent-artifacts,backend-domain -->
- [ ] **Implement evidence ingest/post-validation/persistence —** Input: captures/output/ledger; implemented M3 recorder/PRODUCED insertion, validation/acceptance, cost-reconciliation and terminal-handoff interfaces; signed fixture rows, never later product commands; implemented EvidenceIngestService sole-writer interface. Operation: let `EvidenceIngestService` validate/hash/redact captures, let `ArtifactCommandService` persist only `PRODUCED`, then let `ArtifactValidationService` write link/validation records and enforce citation/contradiction rules. Output: immutable evidence chain, with the immutable specialist implementation/configuration identity and its frozen typed capability contract. Test evidence: malicious URI/content/type and atomicity fixtures; execute these checks against signed M3 fixture rows and actual M3 services; later lead/reply/approval/product transitions remain mandatory at their existing product owners. Failure behavior: quarantine capture and reject dependent output.
<!-- roadmap-task id=AGENT-04-T04 milestone=M3 depends_on=AGENT-04-T03,AGENT-10-T01,AGENT-10-T03,AGENT-10-T04 mode=serial locks=agent-runtime,agent-artifacts,live-environment -->
- [ ] **Build and gate 60-case suite —** Input: frozen recorded fixtures/rubrics; AGENT-10 signed fresh capture-set and deterministic scoring package/repetition summaries. Operation: select this specialist's exact frozen-case subset from the AGENT-10 capture set, independently verify three fresh candidate calls per case and all signatures/configuration/fixture hashes, invoke the shared deterministic scorer and evaluate every original specialist component/duration/cost/regression gate; retain the full repetition and suite summaries without a second capture or promotion writer. Output: three full repetition summaries, suite summary, and promotion/rejection evidence. Test evidence: unique provider call/request IDs, complete capture-set signatures, no model replay, non-model zero-network proof, scoring golden vectors, and per-repetition threshold audit. Failure behavior: prior promoted version remains.

## Test strategy

- **Schema `test_market_models_reject_bad_bounds_dates_quality_and_confidence`.**
- **Gap `test_market_evidence_gaps_accepts_empty_tuple_without_fabrication_and_rejects_empty_members_or_eleven_items`.**
- **Provenance `test_market_claims_require_eligible_capture_and_exact_hash`.**
- **Adversarial `test_extracted_page_cannot_add_tools_contacts_send_or_commands`.**
- **Numeric `test_market_size_requires_unit_geography_period_and_method`.**
- **Cancellation `test_market_cancel_stops_before_next_provider_call`.**
- **Evaluation `test_market_research_v1_capture_scoring_thresholds_and_regression`.**

## Security, privacy, compliance, idempotency, observability, and cost

Source content is hostile; capture limits and redaction follow DB-04 `SENSITIVE_SHORT`. No personal data/credentials/chain-of-thought enter artifact or telemetry. Idempotency uses workflow/config/provider request hashes. Traces expose safe run/call/evidence IDs, domain hash, source class, counts, outcome/reasons, time/tokens/currency cost and ILS projection.

Retention follows AGENT-01 and DB-04/05/06 exactly: run/evaluation evidence is `EVALUATION_VERSIONED`, product artifacts/links are `BUSINESS_ACTIVE`, captures are `SENSITIVE_SHORT`, validation/acceptance/cost/event evidence is `SAFETY_LONG`, and only `RetentionCommandService` purges or redacts.

## Failure, rollback, and operator recovery

Provider/source/schema/provenance/cost failure stops bounded work. Accepted prior captures remain immutable but do not force artifact success. Quarantined/compromised evidence blocks dependent acceptance and triggers audited revocation/pause. Recovery uses recorded fixtures/config rollback or a new run; no live replay is assumed safe.

## Acceptance and retained evidence

- [ ] Exact models/tools/capability semantics, evidence/citation/confidence/abstention, ceilings, cancellation, failures, validator and event map are implemented.
- [ ] All 60 evaluation cases meet numeric promotion/regression/rollback gates.
- [ ] Agent produces only cited immutable `MarketEvidence` `PRODUCED`; deterministic services own capture, validation, acceptance, and transitions.
- [ ] No contact, business merge, policy/approval/budget/suppression, state, Gmail/send, credential, or arbitrary browser authority exists.

Retain recorded response/capture hashes, source-policy manifest, schemas/prompts/configs, eval reports, adversarial outputs, ledger/cost, validators/events, reviews, and promotion/rollback records.

## Dependencies and next deliverable

A promoted AGENT-04 unlocks WF-03 market-evidence/bundle validation and M4 synthetic execution. It does not accept evidence or make the experiment `READY_FOR_LEADS`.
