# Product Scope and Bounded Bet

**Document ID:** PRODUCT-01
**Status:** Planned gate definition
**Milestone:** M0 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PRODUCT-01-T01 -> PRODUCT-01-T02 -> PRODUCT-01-T03 -> PRODUCT-01-T04`; cross-document task Inputs `none`. Descriptive source authorities/resources (not whole-document completion dependencies): [approved cost-first design](../../superpowers/specs/2026-09-09-cost-optimized-validation-roadmap-design.md) and [master milestone order](../README.md#authoritative-milestone-order)
**Outputs:** Canonical autonomous sales contract, ordered artifact authority, commercial and learning boundaries, cost-first launch program, experiment brief, and non-goals
**Unlocks:** PRODUCT-02 success metrics and PRODUCT-03 risk gate
**Risk:** High
**Complexity:** M

## Outcome and timing

M0 defines a falsifiable product bet before infrastructure or provider spend expands. Alon AI is a private, bounded autonomous sales-validation system for one solopreneur. It turns a discovered or user-supplied idea into market evidence, an authoritative offer, qualified prospects, evidence-backed conversations and negotiation, qualified commitments, confirmed booked calls, checkpoint decisions, and reversible global strategy improvements.

The product must conserve operator attention, cash, and reputation. Autonomy is earned through retained evidence and deterministic policy. Normal in-envelope actions do not wait for per-message approval. Unsafe, ambiguous, stale, or out-of-envelope cases enter the exception/incident queue.

The pre-revenue operating posture is deliberately cheap: Brave Place Search is the only automated v1 place/business discovery source; obvious filters use no model; model work is routed from Nano to Mini with premium models default-denied; infrastructure starts on one small private VPS with Cloudflare private ingress and encrypted R2 backups; launch expands only from shadow mode to 20 reviewed businesses, then 50 qualified businesses, then an explicitly authorized 100–300 tranche if meetings/revenue/economics justify it.

## Current repository state

Implemented today: readiness dashboard, health API, database connection boundary, empty migration base, idle worker, default-off outreach configuration, and typed guarded-send interfaces. Missing today: the product records/workflows named below, research/model integrations, Brave place discovery adapter, Gmail OAuth/adapter/history sync, complete operator controls, deployment, and real-experiment evidence. This document is roadmap authority, not implementation evidence.

## Product job and user promise

Given a bounded customer/problem hypothesis, Alon AI helps the operator:

1. register experiment bounds in an `ExperimentBrief`;
2. discover or materialize a user-supplied idea into `IdeaBrief`;
3. research the market before designing one immutable `OfferPackage`;
4. discover businesses using the approved Brave Place Search adapter and apply inexpensive preliminary qualification before deep research;
5. apply final qualification using immutable offer filters and accepted evidence;
6. write personalized initial/reply messages without giving the writer send capability;
7. authorize sends deterministically, evaluate replies, and negotiate inside the commercial envelope;
8. book qualified calls after explicit timezone-aware slot confirmation;
9. evaluate every closed real-validation stage/tranche through a deterministic checkpoint decision; and
10. learn from immutable checkpoint evidence and activate approved global strategies only at eligible stage boundaries.

The promise is control and better evidence, not guaranteed revenue.

## Canonical autonomous sales contract

This single machine-readable block is the authority consumed by roadmap validation and the generated execution fingerprint. Array order is normative. `provider` names the responsible agent or deterministic application service; gate-backed outputs become usable only after their deterministic owner accepts them.

```json
{
  "schema_version": "autonomous_sales_contract.v2",
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
  "automated_discovery_provider": "BRAVE_PLACE_SEARCH",
  "manual_evidence_sources": ["SOCIAL_PROFILE", "PUBLIC_BUSINESS_PAGE"],
  "model_routing_tiers": ["NO_AI", "NANO", "MINI", "PREMIUM"],
  "premium_model_requires_explicit_approval": true,
  "batch_for_non_urgent_research": true,
  "launch_stages": [
    {"name": "SHADOW", "max_real_businesses": 0, "manual_review_required": false, "real_demand_learning": false},
    {"name": "REVIEW_20", "max_real_businesses": 20, "manual_review_required": true, "real_demand_learning": true},
    {"name": "QUALIFIED_50", "max_real_businesses": 50, "manual_review_required": false, "real_demand_learning": true},
    {"name": "SCALE_100_TO_300", "min_real_businesses": 100, "max_real_businesses": 300, "manual_review_required": false, "real_demand_learning": true, "explicit_operator_authorization": true}
  ],
  "pre_revenue_recipient_ceiling": 300,
  "send_writer": "SendGateway",
  "booking_writer": "BookingGateway",
  "strategy_activation_boundary": "CHECKPOINT_ONLY",
  "learning_trigger": "CLOSED_CHECKPOINT",
  "active_cohort_mutation": false
}
```

The optional user-supplied idea remains the only normal pipeline bypass. `OfferPackage` remains the sole downstream commercial authority. Every artifact/action retains immutable version/hash/evidence lineage and governing strategy activation.

## Cost-first discovery and model authority

Automated v1 place/business discovery uses `BravePlaceSearchAdapter` only. Google Maps, Instagram, TikTok, social networks, directories, and arbitrary crawling are not automated discovery targets. A social profile may be attached only as manually reviewed evidence with source URL/capture, reviewer/time, permitted fields, provenance, retention, and redaction; it never expands provider capability or supplies an unevidenced owner/contact identity.

`ModelRoutingPolicy` is deterministic application policy. Agents may request a declared task capability but cannot choose a model tier.

- `NO_AI`: obvious filtering, dedupe, arithmetic, policy/commercial checks, and deterministic eligibility.
- `NANO`: structured extraction, normalization, classification, and initial scoring where code is insufficient.
- `MINI`: only after shortlist/preliminary admission for deeper synthesis/research or higher-value writing/reasoning.
- `PREMIUM`: default denied. It requires explicit operator approval binding exact task/run, model/config, maximum spend, expiry, and reason. Approval never weakens safety/artifact gates.
- `BATCH`: non-urgent research uses provider batch processing when the selected provider/tier supports it and no user-facing latency requirement applies.

Every model call retains routing decision/reason, tier, batch/urgency mode, configuration, usage/cost, and strategy attribution.

## Commercial, conversation, booking, and learning authority

`CommercialPolicyEngine` deterministically computes allowed commercial proposals from `OfferPackage`; agents cannot go below minimum price/margin, invent budget, create unsupported claims/deliverables/legal terms, or represent an unaccepted proposal as a deal.

`ActionAuthorizationService` binds exact action/content/recipient/thread/campaign/stage/member/offer/strategy/policy/commercial facts/expiry/control generation. `SendGateway` alone invokes Gmail writes. Provider ambiguity remains quarantined and reconciled before retry.

`BookingGateway` alone creates/reschedules/cancels calendar events after qualified intent and explicit timezone-aware slot confirmation. Ambiguous provider outcomes reconcile before retry.

Global learning runs only from closed checkpoint evidence. `SHADOW` can feed offline agent/provider evaluation but is not real-demand evidence. `REVIEW_20`, `QUALIFIED_50`, and each explicitly authorized `SCALE_100_TO_300` tranche close an immutable checkpoint. Weak evidence yields `KEEP` or `INSUFFICIENT_EVIDENCE`; it cannot promote strategy. A running stage/tranche freezes offer, strategy, qualification criteria, evidence definitions, and admission membership until closure.

## Pre-revenue infrastructure posture

M8 targets one provider-neutral **2-vCPU / 4-GB Linux VPS** with resource-limited modular-monolith containers and PostgreSQL. Operator access is through **Cloudflare Tunnel + Cloudflare Access**. Product API/UI/database/SSH are not exposed directly to the Internet. PostgreSQL/application state uses encrypted local VPS storage. Backups are encrypted by the application/backup tooling before upload to **Cloudflare R2** and must pass clean-host restore drills. Recovery key/config material is stored off-host under operator control.

Managed KMS/Secret Manager, multi-provider backup witnesses, dedicated 160-GB data disks, larger hosts, and enterprise hardening are deferred until revenue or measured capacity/recovery evidence justifies an architecture amendment. They are not M8 prerequisites.

## Cost-first first-real-validation program

The former automatic `100/200/300/400` and cumulative `100/300/600/1,000` program is superseded.

| Stage | Real-business bound | Entry/exit authority |
| --- | ---: | --- |
| `SHADOW` | `0` | Full pipeline and policy/cost simulation; no real sends; no real-demand learning. |
| `REVIEW_20` | up to `20` | Every business is manually reviewed before admission. Stage closes and records a checkpoint before expansion. |
| `QUALIFIED_50` | up to `50` | Only finally qualified businesses under the same bounded program. Stage closes before expansion. |
| `SCALE_100_TO_300` | one explicitly authorized tranche `100..300` | Entry requires the 50-stage to justify scale using meetings, revenue/paid-commitment evidence where available, contribution economics, provider cost, operator time, deliverability/reputation, and all safety gates. The operator signs the exact tranche size. No automatic 600/1,000 path exists pre-revenue. |

Checkpoint decisions remain exactly `CONTINUE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP`. `CONTINUE` alone never manufactures the next population: the scale stage additionally requires explicit operator scope authorization. A smaller cap always wins.

## M0 experiment brief

Before M1, create one versioned `ExperimentBrief` containing at least: experiment code; narrow customer/problem hypothesis; idea origin; jurisdictions; baseline method; total/model/discovery/operator-time budget caps; research/qualification/contact/concurrency caps; accepted model-routing policy version; automated discovery source `BRAVE_PLACE_SEARCH`; manual-evidence policy; launch program `SHADOW -> REVIEW_20 -> QUALIFIED_50 -> SCALE_100_TO_300`; conversation/booking limits; accepted baseline strategy; success/economic rules; kill rules; and evidence-based decision condition.

Store no Gmail secret, unnecessary personal data, or unverified legal conclusion in the brief.

## Scope by vertical milestone

| Milestone | In scope | Explicitly outside the gate |
| --- | --- | --- |
| M0 | one customer/problem bet, baseline, metrics, budgets, source/model/launch authority, stop rules | provider implementation or outreach |
| M1 | durable-workflow production acceptance using operator-owned Gmail test inboxes | product schema and real prospects |
| M2 | first product data model, audit history, idempotency, restore | agents and external providers |
| M3 | offline provider contracts, typed agent fixtures, model-routing and quality/cost promotion | product outreach |
| M4 | synthetic idea → market research → offer workflow | lead outreach |
| M5 | Brave place discovery, preliminary qualification, deep research, final qualification, dedupe | sending |
| M6 | owned-inbox conversations, negotiation simulation, test bookings, reconciliation, suppression, kill/restart evidence | real prospects |
| M7 | operator dashboard for offers/leads/conversations/booking/checkpoints/strategy/cost | public customer application |
| M8 | small private VPS, monitoring, encrypted local data, encrypted R2 backup/restore | enterprise-scale infrastructure |
| M9 | shadow → reviewed 20 → qualified 50 → explicitly authorized 100–300 scale tranche and earned bounded autonomy | automatic 600/1,000 expansion, new market/source/legal authority, payment collection |

## Scope and non-goals

In scope: one operator/private deployment; finite experiments; Brave-based business discovery with provenance; deterministic acceptance/policy/state/side effects; Gmail only through SendGateway after earned gates; complete bounded conversations/negotiation/bookings; checkpoint decisions/global learning; raw counts/uncertainty/cost attribution.

Non-goals before revenue evidence: multi-tenancy/public signup/billing; generic CRM/agent platform; automated social scraping; purchased lists/consumer outreach; unrestricted premium-model use; infrastructure for hypothetical scale; managed KMS/multi-cloud backup requirements; automatic expansion beyond an explicitly approved 100–300 tranche; payment collection; or any direct agent Gmail/calendar write.

## Ordered implementation tasks

<!-- roadmap-task id=PRODUCT-01-T01 milestone=M0 depends_on=- mode=parallel locks=product-contracts -->
- [ ] **Capture the M0 bet —** Input: operator interview notes and prior evidence. Operation: create the versioned `ExperimentBrief` including cost-first source/model/infrastructure/launch policy, marking absence as `zero-history baseline` rather than inventing data. Output: reviewable brief. Test evidence: schema validation plus operator signature. Failure behavior: block M1 when required scope, budget, jurisdiction, success, kill, source, model-routing, or stage fields are missing.
<!-- roadmap-task id=PRODUCT-01-T02 milestone=M0 depends_on=PRODUCT-01-T01 mode=parallel locks=product-contracts -->
- [ ] **Run the narrowness test —** Input: the brief. Operation: verify one operator can name customer, problem, offer, evidence channel, source, model budget, launch stage, and cap without branching into multiple untested markets. Output: pass or smaller brief. Test evidence: completed M0 checklist. Failure behavior: split the hypothesis.
<!-- roadmap-task id=PRODUCT-01-T03 milestone=M0 depends_on=PRODUCT-01-T02 mode=parallel locks=product-contracts,architecture-contracts -->
- [ ] **Register artifact and authority vocabulary —** Input: canonical JSON contract and approved design. Operation: register exact responsibilities/artifacts/producers/gates, Brave discovery authority, deterministic model-routing tiers, cost-first launch stages, decisions, side-effect writers, and checkpoint-only activation. Output: immutable vocabulary crosswalk. Test evidence: parsed exact-set/order/authority tests and rejection of legacy cohort semantics, automated social discovery, model-tier self-escalation, or active-stage mutation. Failure behavior: M0 remains open.
<!-- roadmap-task id=PRODUCT-01-T04 milestone=M0 depends_on=PRODUCT-01-T03 mode=parallel locks=product-contracts -->
- [ ] **Freeze non-goals for the first experiment —** Input: operator wishlist. Operation: classify each item as next-gate required, post-revenue upgrade, or deferred. Output: signed non-goal list including managed KMS/multi-cloud/larger-host/automated-social/premium-by-default exclusions. Test evidence: every planned feature points to a gate. Failure behavior: remove work with no next-gate evidence purpose.

## Test strategy and acceptance

- `test_scope_vocabulary_equals_canonical_sales_contract`: exact 12 responsibilities, 15 artifacts, authority, Brave source, model routing, launch stages, sole writers, decisions/results, and checkpoint boundaries match the JSON contract.
- `test_cost_first_launch_rejects_legacy_600_1000_or_unapproved_scale`: no old cohort progression and no scale population without explicit size/evidence approval.
- `test_model_routing_cannot_self_escalate`: agents cannot choose Mini/Premium and premium approval is exact/expiring/cost-bounded.
- `test_discovery_source_is_brave_and_social_is_manual_evidence_only`: automated source set is exact.
- `test_agent_artifacts_have_no_side_effect_authority`: artifacts contain no write credentials/capability.
- `test_checkpoint_learning_activation_and_rollback_are_bounded`: shadow is not demand learning, weak evidence cannot mutate strategy, and active stages cannot change.

Retain the signed `ExperimentBrief`, canonical contract hash, scope checklist, assumption log, artifact crosswalk, offer bounds, model-routing/source policy versions, launch-stage authorization, and initial strategy activation. Passing this document unlocks [success metrics](02-success-metrics.md); it does not unlock sending.
