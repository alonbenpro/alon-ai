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

1. turn the hypothesis into an explicit product `ExperimentBrief` record;
2. produce cited `IdeaCandidate`, `OfferHypothesis`, and `MarketEvidence` artifacts;
3. find and deduplicate prospective businesses into `LeadEvidence` records;
4. qualify each lead with an explainable `QualificationAssessment`;
5. create a typed `OutreachDraft` without granting the model send authority;
6. ask deterministic policy and operator approval layers for authority;
7. send only through `SendGateway`, then reconcile Gmail and synchronize replies; and
8. calculate an `ExperimentDecision` whose evidence supports `SCALE`, `REVISE`, `KILL`, or `INCONCLUSIVE`.

The promise is control and better evidence, not guaranteed revenue. If an experiment cannot state what would disprove it, the system must reject it as not ready.

## Canonical vocabulary and ownership

These names are frozen downstream inputs for database, workflow, agent, API, and frontend roadmap files; M0 consumes those catalogs and may not invent aliases.

| Record or artifact | Minimum meaning | Created by | Authority |
| --- | --- | --- | --- |
| `ExperimentBrief` product record | customer segment, problem, jurisdiction, budget, sample cap, success/kill rules | operator command | Defines bounds; does not send and is not an agent artifact |
| `IdeaCandidate` | problem hypothesis and evidence questions | typed agent, operator-reviewed | Advisory |
| `OfferHypothesis` | outcome, scope, price hypothesis, exclusions, proof needed | typed agent, operator-reviewed | Advisory |
| `MarketEvidence` | claims tied to retrievable sources and capture times | typed agent plus provider fixtures | Advisory |
| `LeadEvidence` | business identity, fit facts, provenance, dedupe keys | deterministic discovery plus typed research | Advisory |
| `QualificationAssessment` | criterion-level labels, confidence, evidence, exclusion reason | typed agent | Advisory; deterministic gate decides eligibility |
| `OutreachDraft` | subject, body, claims, and source artifact versions; never recipient identity/address | typed agent | No Gmail authority; application code binds a recipient later |
| `ReplyClassification` | intent, sentiment, requested action, confidence, quoted evidence span | typed agent, operator-correctable | Advisory |
| `ExperimentDecision` | advisory `SCALE`, `REVISE`, `KILL`, or `INCONCLUSIVE` recommendation with cited inputs | typed agent | Advisory; operator/application service owns the authoritative product decision |
| `MetricSnapshot` product record | immutable calculated metric observations and cutoff | deterministic metric service | Decision input; not an agent artifact |
| `EvidenceBundle` deterministic artifact | exact accepted artifact/evidence membership and hashes | application service | Provenance only |
| `PolicyDecision`, `Approval`, `SendIntent` product records | deterministic rule result, manual grant/denial, and immutable side-effect intent | deterministic services/operator command | Can deny or bound later work; none is an agent artifact or provider call |

The Task 3 agent-artifact set is exactly `{IdeaCandidate, OfferHypothesis, MarketEvidence, LeadEvidence, QualificationAssessment, OutreachDraft, ReplyClassification, ExperimentDecision}`. Every agent artifact is typed, versioned, immutable after creation, attributable to prompt/model/tool versions, and superseded rather than edited in place. The deterministic compliance-artifact registry is exactly `{CompliancePolicyV1, RecipientIdentityEvidenceV1, RecipientJurisdictionEvidenceV1, AffirmativeConsentEvidenceV1, CounselExceptionRecordV1, LegalReviewRecordV1, DisclosureSenderTemplateV1, GooglePolicyReviewV1}`; agents never create or accept those records.

### Signed operator-time evidence without another product table

`OperatorTimeEvidenceV1` is release/experiment evidence, not a product record and not a 47th table or new API resource. Its exact RFC 8785 JSON object is `{schema_version:"operator_time_evidence.v1", evidence_id, experiment_id, interval_start, interval_end, duration_seconds, activity_code, source_kind, source_ref, recorded_at, operator_id, key_id}` where UUIDs are lowercase canonical text, instants are UTC RFC 3339 with exactly six fractional digits and `Z`, `duration_seconds` is a positive integer equal to the half-open interval length and at most `86400`, `activity_code` is one of `DISCOVERY|BUILD|RESEARCH|OUTREACH_REVIEW|DELIVERY|OPERATIONS`, and `source_kind` is `MANUAL_TIMER|SIGNED_IMPORT`. JSON null, unknown keys, overlapping intervals for one operator, future intervals, and mutable/free-text activity are invalid.

Canonical bytes are UTF-8 RFC 8785 JSON. `payload_sha256` is lowercase SHA-256 of those bytes. The operator signs `UTF8("alon-ai:operator-time-evidence:v1\n") || hex_decode(payload_sha256)` with Ed25519; the retained envelope is `{payload,payload_sha256,signature_algorithm:"Ed25519",signature_base64url,key_id}`. The solo operator owns the signing key; the release/evidence verifier owns key-status lookup and signature validation. Valid envelopes enter only the existing content-addressed audit/evidence paths referenced by the experiment/release bundle; they never create a product row or raw-time API. Aggregation deduplicates by `evidence_id` plus payload hash, sorts by `(interval_start,evidence_id)`, rejects any overlap/hash reuse/signature/key/clock mismatch, sums exact `duration_seconds`, and converts to hours only for presentation using decimal division by `3600`. Missing intervals or an invalid envelope make operator-time cost `UNAVAILABLE` and block any economics success claim; they are never imputed.

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

Planned implementation surfaces are only the frozen downstream catalogs: DB-01..05's 46 product tables, BACKEND-02's exact 66 operations, BACKEND-05's command catalog, BACKEND-06's three experiment reports, and FRONTEND-01's route/consumer map. There are no generic nested artifact/lead/metric/cost/decision endpoints beyond BACKEND-02 and no standalone `/metrics`, `/costs`, or `/decisions` pages. The Next.js product routes are exactly those owned by FRONTEND-01; the public unsubscribe confirmation is FastAPI-owned HTML, not a Next.js route.

Those paths do not exist today. Their detailed contracts belong to later roadmap files and may not contradict the artifacts and authority rules above.

## Ordered implementation tasks

- [ ] **Capture the M0 bet —** Input: operator interview notes and any prior manual evidence. Operation: create the versioned `ExperimentBrief` with every required field, marking absence as `zero-history baseline` rather than inventing data. Output: reviewable brief. Test evidence: schema validation plus operator signature. Failure behavior: block M1 when any scope, budget, jurisdiction, success, or kill field is missing.
- [ ] **Run the narrowness test —** Input: the brief. Operation: ask whether one person can name the customer, problem, offer, evidence channel, and cap without “and/or” branches. Output: pass or a smaller brief. Test evidence: completed M0 scope checklist. Failure behavior: split the hypothesis; never build one workflow for multiple untested markets.
- [ ] **Register artifact and authority vocabulary —** Input: the frozen catalogs and tables above. Operation: map each planned producer, consumer, authority, and immutable version key without creating aliases. Output: vocabulary crosswalk consumed by M2-M7. Test evidence: exact-name/set-equality scan across M0, DB-04, AGENT-02..09, BACKEND-02/05/06, and FRONTEND-01; reject `IdeaBrief`, `MarketEvidenceBundle`, recipient-bearing `OutreachDraft`, phantom table/route/command names, and any ninth agent artifact. Failure behavior: M0 remains open and M1 is blocked.
- [ ] **Freeze non-goals for the first experiment —** Input: operator wishlist. Operation: classify each item as required by the next gate or deferred. Output: signed non-goal list. Test evidence: every planned feature points to a milestone gate. Failure behavior: remove work that has no next-gate evidence purpose.

## Test strategy

- **Contract test `test_experiment_brief_rejects_unbounded_scope`:** broad customer segments, absent budget, absent jurisdiction, or absent stop rules fail validation.
- **Contract test `test_agent_artifacts_have_no_side_effect_authority`:** every artifact schema lacks provider credentials and send methods.
- **Traceability test `test_scope_vocabulary_equals_frozen_downstream_catalogs`:** the exact agent/compliance/product-record sets and 46-table/66-operation/route/command/report names equal the frozen downstream catalogs; phantom aliases and surfaces fail.
- **Evidence test `test_operator_time_evidence_signature_interval_dedupe_and_failure_are_closed`:** independent golden bytes/signature/hash pass; null/unknown keys, overlap, gap, replay with changed bytes, invalid/revoked key, bad clock/duration and imputation fail closed without a product row.
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
