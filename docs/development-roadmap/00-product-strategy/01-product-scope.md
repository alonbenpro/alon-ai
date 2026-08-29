# Product Scope and Bounded Bet

**Document ID:** PRODUCT-01
**Status:** Planned gate definition
**Milestone:** M0
**Owner:** Solo operator
**Prerequisites:** Approved roadmap design and [master milestone order](../README.md#authoritative-milestone-order)
**Outputs:** Product job, actor, artifact vocabulary, scope boundary, experiment brief, and non-goals
**Unlocks:** PRODUCT-02 success metrics and PRODUCT-03 risk gate
**Risk:** High
**Complexity:** M

## Outcome and timing

M0 defines a falsifiable product bet before infrastructure expands. Alon AI is a private operating system for one operator to turn a narrow service idea into evidence, a qualified prospect set, controlled Gmail conversations, and a recorded `SCALE`, `REVISE`, or `KILL` decision. It is not an autonomous sales company and it is not a multi-customer SaaS platform.

The primary actor is a software-developer solopreneur operating from Israel. The product must conserve that operator's attention, cash, and reputation. It should make one experiment inspectable and stoppable before it makes anything broad or automatic.

## Current repository state

Implemented today: a readiness dashboard, health API, database connection boundary, empty migration base, idle worker, default-off outreach configuration, and typed guarded-send interfaces. Missing today: every product record and workflow named in this document, research/model integrations, lead discovery, Gmail OAuth/adapter/history sync, operator controls beyond readiness, authentication, deployment, and real-experiment evidence.

The headline copy on the current page describes intended value. It is not proof that the workflow exists.

## Product job and user promise

Given a clearly bounded customer and problem hypothesis, Alon AI helps the operator:

1. turn the hypothesis into an explicit `ExperimentBrief`;
2. produce a cited `IdeaBrief`, `OfferHypothesis`, and `MarketEvidenceBundle`;
3. find and deduplicate prospective businesses into `LeadEvidence` records;
4. qualify each lead with an explainable `QualificationAssessment`;
5. create a typed `OutreachDraft` without granting the model send authority;
6. ask deterministic policy and operator approval layers for authority;
7. send only through `SendGateway`, then reconcile Gmail and synchronize replies; and
8. calculate an `ExperimentDecision` whose evidence supports `SCALE`, `REVISE`, `KILL`, or `INCONCLUSIVE`.

The promise is control and better evidence, not guaranteed revenue. If an experiment cannot state what would disprove it, the system must reject it as not ready.

## Canonical product artifacts

These names are stable inputs for database, workflow, agent, API, and frontend roadmap files:

| Artifact | Minimum meaning | Created by | Authority |
| --- | --- | --- | --- |
| `ExperimentBrief` | customer segment, problem, jurisdiction, budget, sample cap, success/kill rules | operator command | Defines bounds; does not send |
| `IdeaBrief` | problem hypothesis and evidence questions | typed agent, operator-reviewed | Advisory |
| `OfferHypothesis` | outcome, scope, price hypothesis, exclusions, proof needed | typed agent, operator-reviewed | Advisory |
| `MarketEvidenceBundle` | claims tied to retrievable sources and capture times | typed agent plus provider fixtures | Advisory |
| `LeadEvidence` | business identity, fit facts, provenance, dedupe keys | deterministic discovery plus typed research | Advisory |
| `QualificationAssessment` | criterion-level labels, confidence, evidence, exclusion reason | typed agent | Advisory; deterministic gate decides eligibility |
| `OutreachDraft` | recipient, subject, body, claims, source artifact versions | typed agent | No Gmail authority |
| `PolicyDecision` | allowed/denied, rule codes, policy version, facts used | deterministic policy code | Can deny; cannot itself send |
| `ApprovalDecision` | operator identity, scope, expiration, decision, reason | operator command | Bounded grant or denial |
| `SendIntent` | immutable draft reference, recipient, idempotency key, campaign and budget context | deterministic application service | Eligible for queueing only |
| `ReplyClassification` | intent, sentiment, requested action, confidence, quoted evidence span | typed agent, operator-correctable | Advisory |
| `ExperimentDecision` | `SCALE`, `REVISE`, `KILL`, or `INCONCLUSIVE`, metric snapshot, reasoning, operator decision | deterministic metrics plus advisory agent artifact | Operator owns final decision |

Every agent artifact is typed, versioned, immutable after creation, attributable to prompt/model/tool versions, and superseded rather than edited in place.

## Scope by vertical milestone

| Milestone | In scope | Explicitly outside the gate |
| --- | --- | --- |
| M0 | one customer/problem bet, baseline, metrics, budget, authority, stop rules | provider implementation or outreach |
| M1 | DBOS production acceptance using operator-owned Gmail test inboxes and the smallest disposable recovery schema | product schema, real prospects, polished UI |
| M2 | first product data model, audit history, idempotency, restore | agents and external providers |
| M3 | offline provider contracts, typed agent fixtures, quality/cost promotion | live model or Gmail dependence in required tests |
| M4 | synthetic idea-to-offer-to-evidence workflow | lead outreach |
| M5 | evidence-backed lead discovery, qualification, and dedupe | sending |
| M6 | operator-owned inbox sends, reconciliation, reply sync, suppression, kill/restart evidence | real prospects |
| M7 | one-operator control/approval/diagnostic dashboard | customer-facing application |
| M8 | private access, VPS operations, monitoring, encrypted backup and restore | public launch |
| M9 | one pre-registered, capped real experiment | autonomous scaling or concurrent portfolio |

## M0 experiment brief

Before M1 begins, create one versioned `ExperimentBrief` with all of these fields:

| Field | Required content |
| --- | --- |
| `experiment_code` | stable human-readable code, unique in the repository evidence bundle |
| `customer_segment` | a narrow business type and geography; broad labels such as “SMBs” fail validation |
| `problem_hypothesis` | observable costly problem, who experiences it, and current workaround |
| `offer_hypothesis` | bounded service outcome, exclusions, delivery assumptions, and price hypothesis |
| `operator_advantage` | why one Israeli software developer can credibly deliver or test it |
| `jurisdictions` | operator and recipient jurisdictions; unknown jurisdiction blocks sending |
| `baseline_method` | current manual time/cost/quality measurements or an explicit zero-history baseline |
| `budget_caps` | total ILS cash cap, model/search/enrichment cap, and operator-hours cap |
| `sample_caps` | maximum researched, qualified, contacted, and concurrently active leads |
| `authority_level` | no-send through M5; test-inbox-only in M6; bounded real recipients only after M8 |
| `success_rule` | demand, delivery-feasibility, and economics thresholds from PRODUCT-02 |
| `kill_rule` | product and safety triggers from PRODUCT-03 |
| `decision_date_condition` | evidence condition such as completed sample or elapsed reply window, not a fictional build date |

Store no actual Gmail secret, prospect personal data, or unverified legal conclusion in the M0 brief.

## Scope and non-goals

### In scope for the first product loop

- one operator and one privately controlled deployment;
- finite experiments with explicit budgets and sample caps;
- business-to-business evidence gathering with source provenance;
- operator-reviewed artifacts and corrections;
- deterministic policy, state transitions, side effects, and audit history;
- Gmail sending only after test-inbox evidence and only within earned authority;
- replies synchronized into the experiment record; and
- decision support that preserves raw counts and uncertainty.

### Non-goals before M9 evidence

- multi-tenancy, teams, public sign-up, billing, subscription management, or any general-purpose public API; the sole later exception is BACKEND-02's two scanner-safe M9-gated unsubscribe operations, while the operator product remains private;
- a generic CRM, marketing automation suite, inbox client, or agent-building platform;
- unrestricted data scraping, mass-email volume, purchased lists, or consumer outreach;
- legal-compliance automation presented as legal advice;
- autonomous pricing, spending, sending, deleting, or experiment-scaling decisions;
- immortal agents, direct agent access to Gmail, or unbounded retries;
- infrastructure introduced for hypothetical scale; and
- vanity analytics without a decision consequence.

## Exact implementation surfaces this scope drives

Planned backend modules: `alon_ai/domain/experiments.py`, `alon_ai/domain/artifacts.py`, `alon_ai/domain/leads.py`, `alon_ai/domain/messaging.py`, `alon_ai/application/commands/`, `alon_ai/application/queries/`, and `alon_ai/application/sending.py`. Planned API scope is `/api/v1/experiments` plus nested artifact, lead, approval, message, event, metric, and decision resources. Planned frontend scope is `/experiments`, `/experiments/new`, and `/experiments/{experiment_id}` control, evidence, leads, approvals, messages, costs, and decision views.

Those paths do not exist today. Their detailed contracts belong to later roadmap files and may not contradict the artifacts and authority rules above.

## Ordered implementation tasks

- [ ] **Capture the M0 bet —** Input: operator interview notes and any prior manual evidence. Operation: create the versioned `ExperimentBrief` with every required field, marking absence as `zero-history baseline` rather than inventing data. Output: reviewable brief. Test evidence: schema validation plus operator signature. Failure behavior: block M1 when any scope, budget, jurisdiction, success, or kill field is missing.
- [ ] **Run the narrowness test —** Input: the brief. Operation: ask whether one person can name the customer, problem, offer, evidence channel, and cap without “and/or” branches. Output: pass or a smaller brief. Test evidence: completed M0 scope checklist. Failure behavior: split the hypothesis; never build one workflow for multiple untested markets.
- [ ] **Register artifact and authority vocabulary —** Input: artifact table above. Operation: map each planned producer, consumer, authority, and immutable version key. Output: vocabulary crosswalk consumed by M2-M7. Test evidence: exact-name scan across roadmap files. Failure behavior: reject aliases that obscure ownership.
- [ ] **Freeze non-goals for the first experiment —** Input: operator wishlist. Operation: classify each item as required by the next gate or deferred. Output: signed non-goal list. Test evidence: every planned feature points to a milestone gate. Failure behavior: remove work that has no next-gate evidence purpose.

## Test strategy

- **Contract test `test_experiment_brief_rejects_unbounded_scope`:** broad customer segments, absent budget, absent jurisdiction, or absent stop rules fail validation.
- **Contract test `test_agent_artifacts_have_no_side_effect_authority`:** every artifact schema lacks provider credentials and send methods.
- **Traceability test `test_scope_artifacts_have_single_canonical_name`:** roadmap and later schema/API documents use the artifact names in this file.
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

Retain the signed `ExperimentBrief`, scope checklist, assumption log, and artifact crosswalk. Passing this document unlocks [success metrics](02-success-metrics.md); it does not unlock sending.
