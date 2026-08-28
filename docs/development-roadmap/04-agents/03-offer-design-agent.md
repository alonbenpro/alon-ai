# Typed Offer Design Agent

**Document ID:** AGENT-03
**Status:** Planned M3 specialist; no implementation exists
**Milestone:** M3; first workflow use at M4
**Owner:** Solo operator
**Prerequisites:** [AGENT-01](01-agent-runtime-and-contracts.md), promoted [AGENT-02](02-idea-discovery-agent.md), DB-02/DB-04, and one operator-selected idea
**Outputs:** Versioned `OfferHypothesis` `PRODUCED` artifact, abstention/failure results, fixtures, scores, and promotion evidence
**Unlocks:** [AGENT-04](04-market-research-agent.md) and WF-03 offer review
**Risk:** High
**Complexity:** M

## Outcome and timing

The agent converts one selected idea plus frozen brief/evidence into a concrete, falsifiable offer proposal. Price is a hypothesis, not billing logic; claims are evidence-bound; and the agent cannot validate/accept/materialize the offer or authorize outreach.

## Current repository state

No offer agent, prompt, schema, fixtures, or `offer_hypotheses` record exists. Pydantic AI is installed but unused, and DB-02/04 are planned.

## Scope and non-goals

In scope: promise, deliverables, price hypothesis, assumptions, risk reversals, exclusions, evidence-linked claims, and abstention. Non-goals: accepting an offer, changing `offer_hypotheses.status`, payment processing, legal guarantees, market research, lead work, campaign/message creation, Gmail, or iterative autonomous optimization.

## Exact typed contract and implementation surfaces

Create `agents/offer_design.py`, `agents/prompts/offer_design/v1.md`, `OfferHypothesisValidatorV1`, and `backend/tests/fixtures/evals/offer_design/v1/`.

```python
class OfferDesignInputV1(BaseModel):
    schema_version: Literal["offer.design.input.v1"]
    experiment_id: UUID
    brief_version: int = Field(ge=1)
    brief_content_hash: Sha256Hex
    selected_idea_artifact_id: UUID
    selected_idea_content_hash: Sha256Hex
    customer_segment: str = Field(min_length=10, max_length=500)
    problem_statement: str = Field(min_length=20, max_length=700)
    solution_hypothesis: str = Field(min_length=20, max_length=700)
    operator_advantage: str = Field(min_length=10, max_length=500)
    allowed_currencies: tuple[str, ...] = Field(min_length=1, max_length=5)
    price_floor_minor: int = Field(ge=1)
    price_ceiling_minor: int = Field(ge=1)
    evidence_item_ids: tuple[UUID, ...] = Field(max_length=30)

class OfferClaimV1(BaseModel):
    claim_key: str = Field(pattern=r"^claim_[a-z0-9_]{1,40}$")
    text: str = Field(min_length=10, max_length=500)
    kind: Literal["HYPOTHESIS", "SUPPORTED_FACT"]
    evidence_item_ids: tuple[UUID, ...] = Field(max_length=5)

class OfferHypothesisArtifactV1(BaseModel):
    schema_version: Literal["artifact.offer_hypothesis.v1"]
    artifact_type: Literal["OfferHypothesis"]
    name: str = Field(min_length=3, max_length=120)
    promise: str = Field(min_length=20, max_length=500)
    deliverables: tuple[str, ...] = Field(min_length=1, max_length=10)
    exclusions: tuple[str, ...] = Field(min_length=1, max_length=10)
    price_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    pricing_rationale: str = Field(min_length=20, max_length=700)
    assumptions: tuple[str, ...] = Field(min_length=2, max_length=10)
    risk_reversals: tuple[str, ...] = Field(min_length=1, max_length=6)
    validation_questions: tuple[str, ...] = Field(min_length=2, max_length=8)
    claims: tuple[OfferClaimV1, ...] = Field(min_length=1, max_length=15)
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)
```

`price_ceiling_minor >= price_floor_minor`; output currency must be allowed and price within bounds. The registered `OfferHypothesisAbstentionV1` has reason `MISSING_SELECTED_IDEA`, `CONTRADICTORY_CONSTRAINTS`, or `INSUFFICIENT_EVIDENCE`, produces DB confidence `NULL`, and contains no offer fields. Execution failure is AGENT-01's failure artifact.

## Dependencies, tools, evidence, and authority

Dependencies are AGENT-01 context/cancellation/clock, `EvidenceReadPort`, and promoted structured-model access. Only `evidence.read` is allowed, maximum two calls and only declared IDs. Search/page/business tools, unrestricted HTTP, repositories/commands, billing/payments, Gmail/`SendGateway`, policy/approval/control/budget/suppression services, and credentials are forbidden.

Every `SUPPORTED_FACT` has a matching accepted capture; `HYPOTHESIS` has none and must not be worded as certainty. Promise, pricing rationale, and risk reversal cannot make legal/compliance/performance guarantees unsupported by input. Evidence conflict or impossible price/currency constraints causes abstention. Confidence is advisory and cannot produce `VALIDATED`, `ACCEPTED`, or DB-02 `offer_hypotheses` status.

## Ceilings, cancellation, deterministic validation, and persistence

Ceilings are `45s`, 6000 input tokens, 1800 output tokens, two tool calls, two model requests (second only JSON repair), and 20 USD minor. Tool deadline is 5s; model deadline is at most 35s. AGENT-01 cancellation/timeout behavior is mandatory.

`OfferHypothesisValidatorV1` checks price/currency bounds; uniqueness/non-overlap of deliverables/exclusions; at least two falsifiable assumptions/questions; supported-fact citation validity; no guarantee, billing/send/contact/authority fields; exact selected-idea/brief/evidence hashes; and ledger ceilings. Application services persist `agent_runs`, `OfferHypothesis` `PRODUCED` schema `1`, links/cost, and `artifact.produced.v1`. Only later services emit canonical validation/acceptance/supersession events and materialize DB-02.

## Offline evaluation and operator review

Suite `offer_design.v1` has exactly 48 cases: 24 viable ideas across service price bands, 8 impossible/missing constraints requiring abstention, 8 contradictory evidence cases, and 8 injection/guarantee/send-authority adversarial cases. Rubric: hard schema/authority/unsupported-guarantee safety; supported-claim precision; idea/segment alignment; deliverable specificity; price-bound correctness; falsifiability; abstention calibration.

Promotion requires 48/48 schema-valid, zero hard failures, supported-claim precision `>=0.98`, price-bound correctness `=1.00`, mean alignment `>=0.90`, specificity `>=0.88`, falsifiability `>=0.85`, abstention precision/recall each `>=0.90`, aggregate `>=0.88`, bottom decile `>=0.72`, p95 `<=36s`, mean cost `<=16` and max `<=20` USD minor. Any component regression `>0.02` or aggregate regression `>0.01` blocks promotion.

Operator review is always required before offer acceptance/materialization and shows all claims/citations, assumptions, exclusions, price bounds/currency, confidence, validator reasons, versions/hashes, and cost. Immediate rollback follows any authority/guarantee/unsupported-claim leak; otherwise two consecutive 20-run windows with post-validation failure `>2%`, operator rejection `>15%` for rubric reasons, or p95 cost/duration over ceiling trigger rollback.

## Ordered implementation tasks

- [ ] **Encode offer schemas/prompt/config —** Input: selected idea and DB-02 fields. Operation: implement exact models, hashes, registry, prompt. Output: typed agent contract. Test evidence: schema/boundary snapshots. Failure behavior: invalid input blocks model.
- [ ] **Implement bounded execution —** Input: verified envelope/evidence IDs. Operation: expose only `evidence.read`, one structured call plus JSON repair, ceilings/cancellation. Output: offer, abstention, or failure. Test evidence: fake provider boundary matrix. Failure behavior: no partial artifact.
- [ ] **Implement post-validation/persistence —** Input: output/ledger. Operation: verify bounds, citations, specificity, authority and persist only `PRODUCED`. Output: immutable artifact/event/cost. Test evidence: adversarial and atomicity cases. Failure behavior: WF-03 remains blocked.
- [ ] **Build and gate 48-case suite —** Input: frozen cases/rubrics. Operation: run Pydantic Evals, persist hashes/scores, compare thresholds/prior version. Output: promotion decision. Test evidence: deterministic rerun. Failure behavior: retain prior version.

## Test strategy

- **Schema `test_offer_models_reject_price_currency_and_collection_bounds`.**
- **Provenance `test_supported_offer_claim_requires_matching_capture`.**
- **Adversarial `test_offer_agent_rejects_guarantee_send_and_payment_instructions`.**
- **Abstention `test_impossible_constraints_abstain_without_offer`.**
- **Authority `test_offer_agent_cannot_accept_materialize_campaign_or_send`.**
- **Evaluation `test_offer_design_v1_exact_thresholds_and_regression`.**

## Security, privacy, compliance, idempotency, observability, and cost

No contact/payment/credential data enters the prompt. Source text is untrusted and not logged. Input/config hashes and command keys prevent duplicate execution. Telemetry is safe IDs/hashes, citation/deliverable counts, abstention/validator reasons, tokens, duration, USD cost and reconciled ILS projection.

Retention follows AGENT-01 and DB-04/05/06 exactly: run/evaluation evidence is `EVALUATION_VERSIONED`, product artifacts/links are `BUSINESS_ACTIVE`, captures are `SENSITIVE_SHORT`, validation/acceptance/cost/event evidence is `SAFETY_LONG`, and only `RetentionCommandService` purges or redacts.

## Failure, rollback, and operator recovery

Invalid price/currency, unsupported promise, evidence conflict, timeout, or cost breach returns abstention/failure with no materialization. Corrections are new workflow/config/artifact versions. Operator inspects immutable input, run, evidence, validator, ledger, eval, and event records, then rolls back configuration or selects a different idea.

## Acceptance and retained evidence

- [ ] Exact contract, tools, evidence, confidence/abstention, ceilings, failure, post-validation, persistence, and observability are implemented.
- [ ] All 48 cases meet numeric promotion/regression/rollback gates.
- [ ] Agent produces only an immutable `OfferHypothesis` `PRODUCED`; operator/deterministic services retain all authority.
- [ ] No state, campaign, payment, Gmail/send, policy, approval, budget, suppression, repository, or credential path exists.

Retain schemas/prompts/configs/hashes, fixtures/digests, eval outputs, adversarial results, provider ledger/cost, validator/events, operator review, promotion, and rollback evidence.

## Dependencies and next deliverable

A promoted AGENT-03 unlocks [AGENT-04](04-market-research-agent.md) and WF-03 offer review/materialization. It grants neither `ACCEPTED` status nor outreach authority.
