# Product Scope and Bounded Bet

**Document ID:** PRODUCT-01
**Status:** Planned gate definition
**Milestone:** M0 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PRODUCT-01-T01 -> PRODUCT-01-T02 -> PRODUCT-01-T03 -> PRODUCT-01-T04`; cross-document task Inputs `none`. Descriptive source authorities/resources (not whole-document completion dependencies): Approved roadmap design and [master milestone order](../README.md#authoritative-milestone-order)
**Outputs:** Canonical autonomous sales contract, ordered artifact authority, commercial and learning boundaries, experiment brief, and non-goals
**Unlocks:** PRODUCT-02 success metrics and PRODUCT-03 risk gate
**Risk:** High
**Complexity:** M

## Outcome and timing

M0 defines a falsifiable product bet before infrastructure expands. Alon AI is a private, bounded autonomous sales-validation system for one Israeli software-developer solopreneur. It turns a discovered or user-supplied idea into market evidence, an authoritative offer, qualified prospects, evidence-backed email conversations and negotiation, qualified commitments, confirmed booked calls, checkpoint decisions, and reversible global strategy improvements.

The product must conserve the operator's attention, cash, and reputation. Its autonomy is earned through retained M0-M9 evidence and bounded by deterministic policy. Normal in-envelope actions do not wait for individual operator approval. Unsafe, ambiguous, stale, or out-of-envelope cases enter an exception and incident queue.

## Current repository state

Implemented today: a readiness dashboard, health API, database connection boundary, empty migration base, idle worker, default-off outreach configuration, and typed guarded-send interfaces. Missing today: every product record and workflow named in this document, research/model integrations, lead discovery, Gmail OAuth/adapter/history sync, operator controls beyond readiness, authentication, deployment, and real-experiment evidence.

The headline copy on the current page describes intended value. It is not proof that the workflow exists.

## Product job and user promise

Given a clearly bounded customer and problem hypothesis, Alon AI helps the operator:

1. register experiment bounds in an `ExperimentBrief` product record;
2. discover or materialize a user-supplied idea into `IdeaBrief`;
3. research the market before designing one immutable `OfferPackage`;
4. discover businesses through approved sources and admit preliminarily qualified candidates to deep research;
5. apply final qualification using immutable offer filters and the accepted dossier;
6. write initial emails and responses without giving the writer send capability;
7. authorize sends deterministically, evaluate replies, and negotiate inside the commercial envelope;
8. book qualified calls after explicit timezone-aware slot confirmation;
9. evaluate every closed cohort through a deterministic checkpoint decision; and
10. learn from immutable checkpoint evidence and activate approved global strategies only at eligible boundaries.

The promise is control and better evidence, not guaranteed revenue. If an experiment cannot state what would disprove it, the system must reject it as not ready.

## Canonical autonomous sales contract

This single machine-readable block is the authority consumed by roadmap validation and the generated execution fingerprint. Array order is normative. `provider` names the responsible agent or application service; gate-backed outputs become usable only after their deterministic owner accepts them. `inputs` are accepted artifact references. Conditional conversation/booking paths and concurrent per-lead execution cannot violate provider-before-consumer order.

```json
{
  "schema_version": "autonomous_sales_contract.v1",
  "responsibilities": [
    {"order": 1, "name": "Idea Discovery", "kind": "agent", "provider": "IdeaDiscoveryAgent", "optional": true, "inputs": [], "outputs": ["IdeaBrief"]},
    {"order": 2, "name": "Market Research", "kind": "agent", "provider": "MarketResearchAgent", "inputs": ["IdeaBrief"], "outputs": ["MarketResearchReport"]},
    {"order": 3, "name": "Offer Design", "kind": "agent", "provider": "OfferDesignAgent", "inputs": ["IdeaBrief", "MarketResearchReport"], "outputs": ["OfferPackage"]},
    {"order": 4, "name": "Lead Discovery and Preliminary Qualification", "kind": "agent_with_deterministic_gate", "provider": "LeadDiscoveryAgent", "gate_owner": "QualificationService", "inputs": ["OfferPackage"], "outputs": ["LeadDiscoveryCandidate", "QualificationDecision"]},
    {"order": 5, "name": "Deep Lead Research", "kind": "agent", "provider": "LeadResearchAgent", "input_phases": {"QualificationDecision": "PRELIMINARY"}, "inputs": ["OfferPackage", "LeadDiscoveryCandidate", "QualificationDecision"], "outputs": ["LeadResearchDossier"]},
    {"order": 6, "name": "Final Lead Qualification", "kind": "agent_with_deterministic_gate", "provider": "LeadQualificationAgent", "gate_owner": "QualificationService", "inputs": ["OfferPackage", "LeadResearchDossier"], "outputs": ["QualificationDecision"]},
    {"order": 7, "name": "Personalized Email Writing", "kind": "agent", "provider": "EmailWritingAgent", "input_phases": {"QualificationDecision": "FINAL"}, "inputs": ["OfferPackage", "LeadResearchDossier", "QualificationDecision"], "outputs": ["ConversationStrategy", "EmailDraft"]},
    {"order": 8, "name": "Deterministic Email Sending", "kind": "application_service", "provider": "SendGateway", "inputs": ["OfferPackage", "ConversationStrategy", "EmailDraft"], "outputs": []},
    {"order": 9, "name": "Reply Evaluation, Negotiation, and Conversation Control", "kind": "agent_with_deterministic_gate", "provider": "ReplyEvaluationAgent", "gate_owner": "CommercialPolicyEngine", "inputs": ["OfferPackage", "ConversationStrategy", "EmailDraft"], "outputs": ["ReplyEvaluation", "NegotiationDecision"]},
    {"order": 10, "name": "Call Booking", "kind": "application_service", "provider": "BookingGateway", "inputs": ["OfferPackage", "ReplyEvaluation", "NegotiationDecision"], "outputs": ["BookingIntent"]},
    {"order": 11, "name": "Checkpoint Experiment Evaluation", "kind": "agent_with_deterministic_gate", "provider": "ExperimentEvaluationAgent", "gate_owner": "CheckpointEvaluationService", "inputs": ["OfferPackage"], "outputs": ["CheckpointEvidenceBundle"]},
    {"order": 12, "name": "Global Checkpoint Learning", "kind": "agent_with_deterministic_gate", "provider": "GlobalLearningEngine", "gate_owner": "StrategyActivationService", "inputs": ["CheckpointEvidenceBundle"], "outputs": ["AgentLearningProposal", "GlobalStrategyPackage", "StrategyActivation"]}
  ],
  "artifacts": [
    {"name": "IdeaBrief", "producer": "IdeaDiscoveryAgent", "responsibility_order": 1},
    {"name": "MarketResearchReport", "producer": "MarketResearchAgent", "responsibility_order": 2},
    {"name": "OfferPackage", "producer": "OfferDesignAgent", "responsibility_order": 3},
    {"name": "LeadDiscoveryCandidate", "producer": "LeadDiscoveryAgent", "responsibility_order": 4},
    {"name": "LeadResearchDossier", "producer": "LeadResearchAgent", "responsibility_order": 5},
    {"name": "QualificationDecision", "producer": "QualificationService", "responsibility_order": [4, 6], "phases": ["PRELIMINARY", "FINAL"]},
    {"name": "ConversationStrategy", "producer": "EmailWritingAgent", "responsibility_order": 7},
    {"name": "EmailDraft", "producer": "EmailWritingAgent", "responsibility_order": 7},
    {"name": "ReplyEvaluation", "producer": "ReplyEvaluationAgent", "responsibility_order": 9},
    {"name": "NegotiationDecision", "producer": "CommercialPolicyEngine", "responsibility_order": 9},
    {"name": "BookingIntent", "producer": "BookingGateway", "responsibility_order": 10},
    {"name": "CheckpointEvidenceBundle", "producer": "CheckpointEvaluationService", "responsibility_order": 11},
    {"name": "AgentLearningProposal", "producer": "GlobalLearningEngine", "responsibility_order": 12},
    {"name": "GlobalStrategyPackage", "producer": "StrategyActivationService", "responsibility_order": 12},
    {"name": "StrategyActivation", "producer": "StrategyActivationService", "responsibility_order": 12}
  ],
  "idea_origins": ["DISCOVERED", "USER_SUPPLIED"],
  "idea_bypass_materializer": "IdeaBriefMaterializer",
  "commercial_authority": "OfferPackage",
  "checkpoint_decisions": ["CONTINUE", "REVISE", "KILL", "INCONCLUSIVE", "SAFETY_STOP"],
  "learning_results": ["PROMOTE", "KEEP", "ROLLBACK", "INSUFFICIENT_EVIDENCE"],
  "no_mutation_learning_results": ["KEEP", "INSUFFICIENT_EVIDENCE"],
  "cohort_increments": [100, 200, 300, 400],
  "cohort_cumulative_maxima": [100, 300, 600, 1000],
  "recipient_ceiling": 1000,
  "send_writer": "SendGateway",
  "booking_writer": "BookingGateway",
  "strategy_activation_boundary": "CHECKPOINT_ONLY",
  "learning_trigger": "CLOSED_CHECKPOINT",
  "active_cohort_mutation": false
}
```

The fifteen-artifact registry includes agent proposals and deterministic outputs. `QualificationService` materializes phased decisions from discovery/final-qualification proposals; `CommercialPolicyEngine` materializes negotiation decisions. `CheckpointEvaluationService` freezes evidence before the evaluation agent reads it and commits the result after evaluating its recommendation. `StrategyActivationService` validates/promotes packages and materializes activations; the learning agent has no mutation authority. These services operate within their numbered responsibility and cannot reverse runtime order.

The optional user-supplied idea is the only normal pipeline bypass: `IdeaBriefMaterializer` creates the same validated immutable shape with `USER_SUPPLIED` origin, user provenance, and a bypass record. Market Research always consumes `IdeaBrief`; Offer Design consumes both upstream artifacts. The resulting `OfferPackage` provides no input upstream to Idea Discovery or Market Research.

Every artifact carries immutable ID, schema version, producer, producer strategy version, input snapshot ID/hash, output hash, evidence references, creation timestamp, disposition, and supersession linkage. Consumers pin accepted provider versions/hashes. Per-agent snapshots differ when their inputs differ; workflow lineage does not require snapshot equality. Every action records its governing offer, global strategy version, and activation. An approved baseline supplies strategy attribution before the first learning checkpoint.

## Commercial, conversation, and learning authority

`OfferPackage` is the sole downstream commercial authority: target customer, problem, solution, positioning, scope, deliverables, base price, cost assumptions, currency/rounding version, minimum price, margin floor, discount bands, payment terms, qualification filters, approved pilots/scope variants, negotiation options, exclusions, proof, claim-to-evidence mappings, outreach claims, booking constraints, validity interval, version, and content hash. The operator may configure or tighten pre-run economics, source allowlist, commercial envelope, legal-policy facts, budgets, and kill switches. Downstream agents cannot independently redefine those terms.

Discovery uses approved adapters and source-specific scopes, initially Google Maps and reviewed public business sources. Social/directory sources require their own adapter, terms review, and evidence tests. Candidates retain identity/provenance, source time, query/filter version, deduplication keys, preliminary facts, unknowns, and preliminary qualification. Deep research runs only for preliminarily qualified candidates; business, decision-maker, services, size, problems, events, technologies, reputation, and personalization fields are `FACT`, `ESTIMATE`, or `UNKNOWN` with source/confidence. Names, roles, contacts, and linkages are never fabricated. Final qualification reapplies the immutable offer filters; identity, suppression, legal-policy, capacity, and cohort admission remain separate deterministic gates.

`ConversationStrategy` selects permitted messaging objectives and references the offer. The writer receives accepted dossier/final qualification, sanitized complete thread state, offer/strategy versions, and precise reply-evaluation instructions. It has no credentials or write capability. Any inbound reply atomically stops the cold sequence; it does not itself create permanent suppression. Positive intent, questions, and genuine objections can continue inside registered round, frequency, message, and time limits. Opt-out, complaint, applicable rejection, bounce, and legal signals create the appropriate stop/suppression; ambiguous or unsafe intent pauses into the exception queue.

`CommercialPolicyEngine` computes allowed proposals: explain the offer, answer supported objections, select approved variants/pilots/discounts, adjust timing/bundle/payment schedule within the package, request missing decision information, or propose a call. Stored versions govern taxes, fees, delivery cost, FX, rounding, margin, and discounts. Budget assertions are `STATED`, `INFERRED`, or `UNKNOWN` with currency/range, source span, confidence, and time; only `STATED` satisfies a stated-budget condition. Unsupported claims, unauthorized legal terms/deliverables/guarantees, below-floor economics, fabricated urgency/budget/familiarity, and unaccepted commitments are forbidden.

`ActionAuthorizationService` creates immutable `ActionAuthorityScopeV1` binding action/content, recipient/thread, campaign/cohort/member, offer, strategy activation, policy/commercial decision, expiry, and control generation. Fresh deterministic checks precede each send and booking write. `SendGateway` alone invokes Gmail writes; `BookingGateway` alone creates/reschedules/cancels calendar events after qualified buying intent and explicit slot confirmation. Bounded timezone-aware availability and Gmail history/Sent reads have separate ports from writes. Google Calendar is the first planned calendar adapter; ambiguity requires reconciliation before retry.

One global learning mechanism runs only when a checkpoint closes. The new stage's immutable `CheckpointEvidenceBundle` is primary evidence; similar campaigns are secondary; relevant history, failures, and incidents provide guardrails. Every applicable agent receives exactly `PROMOTE`, `KEEP`, `ROLLBACK`, or `INSUFFICIENT_EVIDENCE`. `KEEP` and `INSUFFICIENT_EVIDENCE` perform no mutation; `NO_CHANGE` is explanatory behavior, never another serialized result. Promotion requires minimum evidence, immutable lineage, offline comparison, protected holdouts, cross-campaign guardrails, expected metrics/confidence, and rollback rules. Safety, legal-policy, suppression, source, and commercial bounds are not learnable.

The triggering campaign adopts an approved strategy at its next cohort boundary only after `CONTINUE`; other active campaigns wait for their own next checkpoint; future campaigns use the newest approved global version. A running cohort freezes offer, strategy, qualification criteria, causal variables, and evidence definitions. Deterioration triggers automatic rollback for future actions, never historical rewriting; if triggered during a cohort, pause affected actions and close its checkpoint before rollback activation. Operational conversation memory is not learning.

`ExperimentBrief`, metrics, policy decisions, send intents/attempts, provider observations, and incidents are product records outside the fifteen-artifact registry. The deterministic compliance registry remains `{CompliancePolicyV1, RecipientIdentityEvidenceV1, RecipientJurisdictionEvidenceV1, AffirmativeConsentEvidenceV1, CounselExceptionRecordV1, LegalReviewRecordV1, DisclosureSenderTemplateV1, GooglePolicyReviewV1}`; agents never author or accept protected legal-policy evidence. Source/jurisdiction-specific requirements fail closed.

### Signed operator-time evidence without another product table

`OperatorTimeEvidenceV1` is release/experiment evidence, not a product record or new API resource. Its exact RFC 8785 JSON object is `{schema_version:"operator_time_evidence.v1", evidence_id, experiment_id, interval_start, interval_end, duration_seconds, activity_code, source_kind, source_ref, recorded_at, operator_id, key_id}` where UUIDs are lowercase canonical text, instants are UTC RFC 3339 with exactly six fractional digits and `Z`, `duration_seconds` is a positive integer equal to the half-open interval length and at most `86400`, `activity_code` is one of `DISCOVERY|BUILD|RESEARCH|OUTREACH_REVIEW|DELIVERY|OPERATIONS`, and `source_kind` is `MANUAL_TIMER|SIGNED_IMPORT`. JSON null, unknown keys, overlapping intervals for one operator, future intervals, and mutable/free-text activity are invalid.

Canonical bytes are UTF-8 RFC 8785 JSON. `payload_sha256` is lowercase SHA-256 of those bytes. The operator signs `UTF8("alon-ai:operator-time-evidence:v1\n") || hex_decode(payload_sha256)` with Ed25519; the retained envelope is `{payload,payload_sha256,signature_algorithm:"Ed25519",signature_base64url,key_id}`. The solo operator owns the signing key; the release/evidence verifier owns key-status lookup and signature validation. Valid envelopes enter only the existing content-addressed audit/evidence paths referenced by the experiment/release bundle; they never create a product row or raw-time API. Aggregation deduplicates by `evidence_id` plus payload hash, sorts by `(interval_start,evidence_id)`, rejects any overlap/hash reuse/signature/key/clock mismatch, sums exact `duration_seconds`, and converts to hours only for presentation using decimal division by `3600`. Missing intervals or an invalid envelope make operator-time cost `UNAVAILABLE` and block any economics success claim; they are never imputed.

## Scope by vertical milestone

| Milestone | In scope | Explicitly outside the gate |
| --- | --- | --- |
| M0 | one customer/problem bet, baseline, metrics, budget, authority, stop rules | provider implementation or outreach |
| M1 | DBOS production acceptance using operator-owned Gmail test inboxes and the smallest disposable recovery schema | product schema, real prospects, polished UI |
| M2 | first product data model, audit history, idempotency, restore | agents and external providers |
| M3 | offline provider contracts, typed agent fixtures, quality/cost promotion | live model or Gmail dependence in required tests |
| M4 | synthetic idea → market research → offer workflow | lead outreach |
| M5 | approved discovery, preliminary qualification, deep research, final qualification, and dedupe | sending |
| M6 | owned-inbox conversations, objection/negotiation simulation, test calendar bookings, reconciliation, suppression, kill/restart evidence | real prospects |
| M7 | offer, conversation, negotiation, booking, checkpoint, strategy, and exception dashboard | customer-facing application |
| M8 | private access, VPS operations, monitoring, encrypted backup and restore | public launch |
| M9 | controlled real cohorts, then earned bounded sending/negotiation/booking and checkpoint learning | unregistered cohort, new market/source/legal authority, payment collection |

## M0 experiment brief

Before M1 begins, create one versioned `ExperimentBrief` with all of these fields:

| Field | Required content |
| --- | --- |
| `experiment_code` | stable human-readable code, unique in the repository evidence bundle |
| `customer_segment` | a narrow business type and geography; broad labels such as “SMBs” fail validation |
| `problem_hypothesis` | observable costly problem, who experiences it, and current workaround |
| `idea_origin` | exactly `DISCOVERED` or `USER_SUPPLIED`, with accepted `IdeaBrief` and bypass provenance where applicable |
| `offer_hypothesis` | pre-run hypothesis/economic constraints; downstream commercial terms come only from the accepted `OfferPackage` |
| `operator_advantage` | why one Israeli software developer can credibly deliver or test it |
| `jurisdictions` | operator and recipient jurisdictions; unknown jurisdiction blocks sending |
| `baseline_method` | current manual time/cost/quality measurements or an explicit zero-history baseline |
| `budget_caps` | total ILS cash cap, model/search/enrichment cap, and operator-hours cap |
| `sample_caps` | maximum researched, qualified, contacted, and concurrently active leads |
| `authority_level` | no-send through M5, isolated owned resources at M6, bounded real recipients only after all M8/M9 evidence; no per-message approval |
| `cohort_program` | increments `100/200/300/400`, cumulative maxima `100/300/600/1,000`, unique membership, frozen cohort versions and checkpoint ownership |
| `conversation_booking_policy` | round/message/frequency/time limits, terminal stops, permitted calendar/timezones, explicit confirmation and exception conditions |
| `strategy_baseline` | accepted global strategy version and activation, applicable agents, checkpoint learning/rollback rules |
| `success_rule` | demand, delivery-feasibility, and economics thresholds from PRODUCT-02 |
| `kill_rule` | product and safety triggers from PRODUCT-03 |
| `decision_date_condition` | evidence condition such as completed sample or elapsed reply window, not a fictional build date |

Store no actual Gmail secret, prospect personal data, or unverified legal conclusion in the M0 brief.

## Scope and non-goals

### In scope for the first product loop

- one operator and one privately controlled deployment;
- finite experiments with explicit budgets and sample caps;
- business-to-business evidence gathering with source provenance;
- deterministically accepted artifacts, pre-run operator configuration, and auditable exception corrections;
- deterministic policy, state transitions, side effects, and audit history;
- Gmail sending only after test-inbox evidence and only within earned authority;
- complete redacted conversations, bounded negotiation, and explicitly confirmed bookings;
- deterministic checkpoint decisions and global learning from closed evidence; and
- decision support that preserves raw counts and uncertainty.

### Non-goals before M9 evidence

- multi-tenancy, teams, public sign-up, billing, subscription management, or any general-purpose public API; the sole later exception is BACKEND-02's two scanner-safe M9-gated unsubscribe operations, while the operator product remains private;
- a generic CRM, marketing automation suite, inbox client, or agent-building platform;
- unrestricted data scraping, mass-email volume, purchased lists, or consumer outreach;
- legal-compliance automation presented as legal advice;
- commercial terms outside the immutable offer envelope, unbounded spending, unregistered campaign expansion, and autonomous sensitive-data deletion;
- immortal agents, direct agent access to Gmail/calendar writes, uncontrolled prompt rewriting, or unbounded retries;
- payment collection; version one ends at qualified commitments and confirmed booked calls;
- infrastructure introduced for hypothetical scale; and
- vanity analytics without a decision consequence.

## Exact implementation surfaces this scope drives

The canonical contract above provides downstream authority. DB-01..06 owns the complete table, foreign-key, lineage, and retention inventories; BACKEND-01..06 owns deterministic services, commands, queries, and API operations; FRONTEND-01 owns the route/consumer inventory. Every closed inventory must be updated atomically for offer economics, discovery/evidence/qualification, conversations/negotiation, booking, checkpoint learning, and strategy attribution. No obsolete exact count limits the approved system.

The dashboard exposes idea origin, research, offer/economics, approved sources, dossiers and phased qualification, automatic-send blocks, a redacted conversation/negotiation/booking timeline, `INTERESTED`, `NEGOTIATING`, `COMMITTED`, `BOOKED`, calendar, checkpoint evidence/results, per-agent learning/evidence/activations/rollback, and exceptions/incidents. The server owns policy, capacity, economics, and authority. The public unsubscribe pair remains FastAPI-owned and independently gated.

These implementation surfaces are planned. Their consumers may not invent extra artifacts, pricing authority, write paths, or learning mechanisms.

## Ordered implementation tasks

<!-- roadmap-task id=PRODUCT-01-T01 milestone=M0 depends_on=- mode=parallel locks=product-contracts -->
- [ ] **Capture the M0 bet —** Input: operator interview notes and any prior manual evidence. Operation: create the versioned `ExperimentBrief` with every required field, marking absence as `zero-history baseline` rather than inventing data. Output: reviewable brief. Test evidence: schema validation plus operator signature. Failure behavior: block M1 when any scope, budget, jurisdiction, success, or kill field is missing.
<!-- roadmap-task id=PRODUCT-01-T02 milestone=M0 depends_on=PRODUCT-01-T01 mode=parallel locks=product-contracts -->
- [ ] **Run the narrowness test —** Input: the brief. Operation: ask whether one person can name the customer, problem, offer, evidence channel, and cap without “and/or” branches. Output: pass or a smaller brief. Test evidence: completed M0 scope checklist. Failure behavior: split the hypothesis; never build one workflow for multiple untested markets.
<!-- roadmap-task id=PRODUCT-01-T03 milestone=M0 depends_on=PRODUCT-01-T02 mode=parallel locks=product-contracts,architecture-contracts -->
- [ ] **Register artifact and authority vocabulary —** Input: the canonical JSON contract and accepted design. Operation: register the exact twelve responsibilities, fifteen artifacts, producer/gate ownership, inputs, offer authority, cohort schedule, decisions, and checkpoint-only strategy activation. Output: immutable vocabulary crosswalk consumed by architecture, data, agents, workflows, providers, services, and UI. Test evidence: parsed exact-set/order and provider-before-consumer tests; reject extra artifacts/results, downstream commercial invention, agent side effects, and active-cohort mutation. Failure behavior: M0 remains open and M1 is blocked.
<!-- roadmap-task id=PRODUCT-01-T04 milestone=M0 depends_on=PRODUCT-01-T03 mode=parallel locks=product-contracts -->
- [ ] **Freeze non-goals for the first experiment —** Input: operator wishlist. Operation: classify each item as required by the next gate or deferred. Output: signed non-goal list. Test evidence: every planned feature points to a milestone gate. Failure behavior: remove work that has no next-gate evidence purpose.

## Test strategy

- **Contract test `test_experiment_brief_rejects_unbounded_scope`:** broad customer segments, absent budget, absent jurisdiction, or absent stop rules fail validation.
- **Contract test `test_agent_artifacts_have_no_side_effect_authority`:** every artifact schema lacks provider credentials and send methods.
- **Traceability test `test_scope_vocabulary_equals_canonical_sales_contract`:** the exact responsibility order/kinds, fifteen artifact names/producers, phased qualification, offer authority, decision/result sets, cohorts, side-effect writers, and strategy boundaries equal the canonical contract.
- **Evidence test `test_operator_time_evidence_signature_interval_dedupe_and_failure_are_closed`:** independent golden bytes/signature/hash pass; null/unknown keys, overlap, gap, replay with changed bytes, invalid/revoked key, bad clock/duration and imputation fail closed without a product row.
- **Contract test `test_checkpoint_learning_activation_and_rollback_are_bounded`:** weak evidence cannot mutate strategies, active cohorts cannot change, cross-campaign activation waits for each checkpoint, and rollback retains historical attribution.
- **Review test `test_m0_brief_is_operator_signed`:** retained evidence contains version, timestamp, hash, and explicit approval.

## Safety, privacy, compliance, observability, and cost

Outreach is disabled throughout M0-M5. The experiment brief stores budgets and jurisdiction facts but does not claim those facts establish legal compliance. Before real outreach, the operator must document the applicable rules for the chosen recipient jurisdictions and obtain qualified legal advice when the interpretation is uncertain. Logs record identifiers, versions, decisions, and counts; they must not copy secrets, full message bodies, or unnecessary personal data. Every cash and operator-time cap is denominated explicitly, with ILS as the reporting currency and original provider currency retained for reconciliation.

## Failure, rollback, and recovery

If the bet is too broad, evidence-free, unaffordable, legally uncertain, or operationally beyond one person, park it before M1. Recovery is a new immutable brief version with the changed assumption and a link to the rejected version. Never rewrite the rejected brief because the change history is product evidence.

## Acceptance and retained evidence

- [ ] One operator, customer segment, problem, offer, jurisdiction set, budget, sample cap, success rule, and kill rule are explicit.
- [ ] Each canonical artifact has one producer, authority boundary, and versioning rule.
- [ ] Non-goals exclude platform work and direct agent side effects.
- [ ] The current-state section remains accurate against source and tests.

Retain the signed `ExperimentBrief`, canonical contract hash, scope checklist, assumption log, artifact crosswalk, offer bounds, and initial strategy activation. Passing this document unlocks [success metrics](02-success-metrics.md); it does not unlock sending.
