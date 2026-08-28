# Typed Lead Research Agent

**Document ID:** AGENT-05
**Status:** Planned M3 specialist; no implementation exists
**Milestone:** M3; first workflow use at M5
**Owner:** Solo operator
**Prerequisites:** [AGENT-01](01-agent-runtime-and-contracts.md), DB-03/DB-04, passing M4 evidence, and Task 4 recorded business/search/extraction capabilities
**Outputs:** Business-level `LeadEvidence` `PRODUCED` artifact, source captures, abstention/failure results, fixtures, scores, and promotion evidence
**Unlocks:** [AGENT-06](06-lead-qualification-agent.md) and WF-04 research step
**Risk:** Critical
**Complexity:** L

## Outcome and timing

The agent assembles minimal, public, business-level evidence for one already discovered candidate. Deterministic `BusinessIdentityService` owns identity/deduplication/conflict; `LeadCommandService` owns state; the agent neither creates/merges a business/lead nor finds/guesses personal contact data.

## Current repository state

No business/lead tables, discovery provider, enrichment adapter, identity service, research agent, prompt, fixture, or evaluation exists. No real/test lead has been researched by the product.

## Scope and non-goals

In scope: organization facts relevant to the frozen offer/criteria, provenance, contradictions, missing facts, freshness, minimization, and abstention. Non-goals: contact discovery, email/phone/person names, buying/scraping lists, auto-merge, qualification, suppression decisions, message drafting, Gmail, or unbounded enrichment.

## Exact typed contract and implementation surfaces

Create `agents/lead_research.py`, `agents/prompts/lead_research/v1.md`, `LeadEvidenceValidatorV1`, and `backend/tests/fixtures/evals/lead_research/v1/`.

```python
class LeadResearchInputV1(BaseModel):
    schema_version: Literal["lead.research.input.v1"]
    experiment_id: UUID
    lead_id: UUID
    business_id: UUID
    business_identity_key: Sha256Hex
    canonical_name: str = Field(min_length=2, max_length=200)
    canonical_domain: str | None = Field(default=None, max_length=253)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    discovery_evidence_item_ids: tuple[UUID, ...] = Field(min_length=1, max_length=10)
    offer_artifact_id: UUID
    offer_content_hash: Sha256Hex
    research_questions: tuple[str, ...] = Field(min_length=1, max_length=12)
    allowed_domains: tuple[str, ...] = Field(min_length=1, max_length=20)
    source_limit: int = Field(ge=1, le=6)
    as_of: datetime

class BusinessFactV1(BaseModel):
    fact_key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,40}$")
    value: str = Field(min_length=1, max_length=500)
    evidence_item_ids: tuple[UUID, ...] = Field(min_length=1, max_length=4)
    observed_at: datetime | None = None
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)

class LeadEvidenceArtifactV1(BaseModel):
    schema_version: Literal["artifact.lead_evidence.v1"]
    artifact_type: Literal["LeadEvidence"]
    lead_id: UUID
    business_id: UUID
    business_identity_key: Sha256Hex
    facts: tuple[BusinessFactV1, ...] = Field(min_length=1, max_length=20)
    question_findings: tuple[str, ...] = Field(min_length=1, max_length=12)
    contradictions: tuple[str, ...] = Field(max_length=10)
    missing_facts: tuple[str, ...] = Field(max_length=12)
    source_count: int = Field(ge=1, le=6)
    overall_confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)
```

Fields named or containing personal name, job title tied to a person, email, phone, social handle, mailbox, recipient, or inferred demographic are schema-forbidden. `LeadEvidenceAbstentionV1` reasons: `IDENTITY_CONFLICT`, `NO_ELIGIBLE_SOURCE`, `INSUFFICIENT_BUSINESS_FACTS`, `PERSONAL_DATA_ONLY`, `MATERIAL_CONTRADICTION`, `BUDGET_EXHAUSTED`. DB artifact confidence is `NULL` on abstention. Execution failure uses AGENT-01 taxonomy.

## Dependencies, tools, evidence, and authority

Injected dependencies: AGENT-01 context/clock/cancellation, `EvidenceReadPort`, `BusinessSearchPort`, `BusinessDetailsPort`, `PageExtractionPort`, and promoted model. Allowed tools: `evidence.read` <=2; `business.search` <=2 for confirming the supplied organization only; `business.details` <=2 for one supplied business identity; `page.extract` <=2 from allowed organization/authoritative domains; total <=8 and `source_count <= source_limit`.

Forbidden: contact/person search, arbitrary query terms unrelated to the supplied business, cross-business merge, unrestricted HTTP/browser/login, repository/command services, `BusinessIdentityService`, qualification/policy/approval/budget/suppression decisions, Gmail/`SendGateway`, credentials, and source-authored instructions. A tool returning personal data is redacted/quarantined before model exposure where possible and is never copied into output.

Every fact links exact captured evidence. Confidence over `0.80` requires two independent sources or one authoritative first-party/registry source. The immutable input identity key must match output exactly; any possible collision/conflict causes abstention for deterministic/operator resolution. Missing facts remain explicit; the agent cannot infer them from adjacent facts.

## Ceilings, cancellation, deterministic validation, and persistence

Ceilings: `timeout_seconds=90`, 9000 input tokens, 1800 output tokens, 8 tool calls, 2 model requests (JSON repair only), and 40 USD minor. Tool deadlines: evidence/details 6s, search 8s, extraction 12s; model <=40s within global deadline. Provider reservations precede calls and cancellation stops the next call.

`LeadEvidenceValidatorV1` checks exact lead/business/identity tuple, allowed-domain and source bounds, capture hashes/redaction, business-only field allowlist, PII detector, fact citation/cardinality/confidence, contradiction/missing-fact honesty, injection markers, no qualification/send/authority fields, and ledger totals. Application services persist evidence captures, `agent_runs`, `LeadEvidence` `PRODUCED` schema `1`, links/cost, and `artifact.produced.v1`. Later deterministic acceptance may append `lead.evidence_recorded.v1` and move `RESEARCH_PENDING -> RESEARCHED`; the agent cannot.

## Offline evaluation and operator review

Suite `lead_research.v1` has exactly 60 recorded cases: 24 clear organizations, 8 ambiguous identity cases, 8 sparse/no-source cases, 8 contradictory/outdated cases, and 12 PII/contact/injection/cross-business/authority attacks. It makes zero live calls. Scores: hard identity/PII/authority/domain/schema safety, fact citation precision/recall, business-fact accuracy, contradiction recall, missing-fact honesty, identity-conflict abstention.

Promotion requires 60/60 schema-valid; zero identity splice, PII/contact, authority, domain, or injection hard failures; citation precision `>=0.99`, recall `>=0.97`, fact accuracy `>=0.96`, contradiction recall `>=0.95`, missing-fact honesty `>=0.95`, conflict abstention precision/recall each `>=0.98`, aggregate `>=0.92`, bottom decile `>=0.78`, p95 `<=75s`, mean cost `<=30`, max `<=40` USD minor. Any component regression `>0.01` or aggregate `>0.005` blocks promotion.

Operator review is mandatory for identity conflict, any PII quarantine, confidence `<0.75`, contradiction, or fact that materially changes qualification. Other artifacts may use deterministic validation/acceptance but still cannot qualify. Immediate rollback follows any PII/contact leak, identity splice/merge, authority, or injection violation; otherwise two consecutive 20-run windows with invalid citation `>1%`, post-validation failure `>1%`, operator factual correction `>5%`, or p95 ceiling breach trigger rollback.

## Ordered implementation tasks

- [ ] **Encode minimized schemas/source policy —** Input: DB-03 identity and M5 questions. Operation: implement exact business-only models, prompt/config, PII denylist and source rules. Output: typed contract. Test evidence: schema/PII/boundary snapshots. Failure behavior: invalid input blocks providers.
- [ ] **Implement bounded business tools —** Input: verified identity/evidence/reservations. Operation: expose only exact candidate-scoped capabilities and structured output. Output: evidence/abstention/failure plus ledger. Test evidence: recorded timeout/cancel/cross-business matrix. Failure behavior: quarantine/stop without merge.
- [ ] **Implement capture/validator/persistence handoff —** Input: provider results/output. Operation: redact/hash/link, enforce tuple/PII/citation rules, persist only `PRODUCED`. Output: immutable evidence chain. Test evidence: PII and atomicity injection. Failure behavior: artifact cannot attach to lead.
- [ ] **Build and gate 60-case suite —** Input: frozen recorded cases. Operation: Pydantic Evals and exact threshold/regression comparison. Output: promotion decision. Test evidence: deterministic offline rerun. Failure behavior: prior version stays.

## Test strategy

- **Schema `test_lead_research_models_forbid_personal_contact_fields`.**
- **Identity `test_output_lead_business_identity_tuple_must_equal_input`.**
- **Provenance `test_every_business_fact_requires_exact_capture_hash`.**
- **Adversarial `test_provider_content_cannot_trigger_merge_qualification_or_send`.**
- **Privacy `test_personal_data_fixture_is_quarantined_and_not_logged_or_persisted`.**
- **Evaluation `test_lead_research_v1_thresholds_regression_and_offline_only`.**

## Security, privacy, compliance, idempotency, observability, and cost

Minimize to public business facts. Raw captures are `SENSITIVE_SHORT`; evidence IDs/hashes persist per DB-04. No addresses/content/credentials/source text/chain-of-thought are logged. Request/config hashes prevent repeats. Metrics include safe IDs/identity hash, sources/facts/missing/contradictions, PII quarantine, abstention/reasons, time/tokens/currency cost and ILS projection.

Retention follows AGENT-01 and DB-04/05/06 exactly: run/evaluation evidence is `EVALUATION_VERSIONED`, product artifacts/links are `BUSINESS_ACTIVE`, captures are `SENSITIVE_SHORT`, validation/acceptance/cost/event evidence is `SAFETY_LONG`, and only `RetentionCommandService` purges or redacts.

## Failure, rollback, and operator recovery

Identity/PII/source/evidence/systemic provider failure quarantines the bounded lead and never relaxes criteria. Compromised evidence pauses dependent acceptance. Recovery inspects immutable run/captures/ledger/validator/events and uses audited identity resolution or a new run/config; it never auto-merges or edits prior evidence.

## Acceptance and retained evidence

- [ ] Exact models, scoped provider capabilities, PII/evidence/confidence/abstention, ceilings, cancellation, failures, validator and persistence/event mapping are implemented.
- [ ] All 60 offline cases meet numeric promotion/regression/rollback gates.
- [ ] Agent produces only immutable business-level `LeadEvidence` `PRODUCED`; application services own identity, lead state, acceptance, and events.
- [ ] No person/contact, merge, qualification, suppression, policy/approval/budget, state, Gmail/send, credential, or arbitrary browser authority exists.

Retain source/provider/PII policy manifests, fixture/capture/config/schema/prompt hashes, eval/adversarial reports, ledger/cost, validators/events, reviews, and promotion/rollback records.

## Dependencies and next deliverable

A promoted AGENT-05 unlocks [AGENT-06](06-lead-qualification-agent.md) and WF-04 evidence validation. It does not emit `lead.evidence_recorded.v1`, research/qualify, or create send eligibility.
