# Multi-Source Discovery, Research, and Qualification Workflow

**Document ID:** WF-04
**Status:** Planned finite workflow; no implementation exists
**Milestone:** M5 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-04-T01 -> WF-04-T02 -> WF-04-T03 -> WF-04-T04 -> WF-04-T05`; cross-document task Inputs `WF-04-T01 <- WF-03-T05,DB-02-T03,WF-03-T03; WF-04-T02 <- PROVIDER-08-T03,AGENT-11-T04; WF-04-T03 <- PROVIDER-06-T01,PROVIDER-06-T03,PROVIDER-05-T04,AGENT-05-T04; WF-04-T04 <- AGENT-06-T04,BACKEND-01-T04; WF-04-T05 <- WF-02-T03,PROVIDER-08-T04`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [runtime selection](00-dbos-selection-and-temporal-fallback.md).
**Outputs:** Finite typed inputs/results, immutable artifact/state handoffs, idempotency and recovery evidence
**Unlocks:** M5 preparation and WF-05 conversation admission
**Risk:** Critical
**Complexity:** L

## Outcome and timing

M5 produces a deduplicated, evidence-backed prospect pool for the next registered cohort plus a bounded reserve. Cheap preliminary qualification controls access to expensive research. Final qualification reapplies the immutable OfferPackage filters; neither phase grants send authority.

## Current repository state and planned surfaces

No product workflow, persistent artifact/aggregate or provider implementation described here exists. Plan `backend/src/alon_ai/workflows/lead_qualification.py` and application-owned command interfaces, fixture/contract tests and durable recovery simulations. Workflows never mutate ORM rows, call concrete adapters or own Gmail/calendar credentials.

## Exact workflow contract

### Per-lead flow and authoritative results

| Step | Required accepted input | State/result and owner |
| --- | --- | --- |
| source discovery | OfferPackage/filter refs, provider allowlist/terms and bounded query | LeadDiscoveryAgent proposes LeadDiscoveryCandidate; approved adapters capture provenance |
| identity admission | Candidate/source business IDs/domain/location/evidence | BusinessIdentityService checks duplicates/conflicts; DISCOVERED -> PRELIMINARY_QUALIFICATION_PENDING |
| preliminary gate | Candidate and immutable inexpensive offer filters | QualificationService materializes PRELIMINARY QualificationDecision -> PRELIMINARILY_QUALIFIED or DISQUALIFIED |
| deep research | Accepted preliminary decision, candidate and OfferPackage | bounded LeadResearchAgent -> LeadResearchDossier; RESEARCH_PENDING -> RESEARCHED |
| final gate | Accepted dossier and identical OfferPackage/filter version | QualificationService materializes FINAL QualificationDecision -> QUALIFIED or DISQUALIFIED |
| preparation exit | accepted phase/identity/provenance, sample/cost gates | experiment READY_FOR_OUTREACH; no cohort membership or action authority yet |

Discovery uses Google Maps and reviewed public business sources through approved LeadDiscoveryProvider adapters. Each source records adapter/terms/query/filter version, source time, capture/hash and dedupe keys; no arbitrary social crawling is assumed. A person/owner/role/contact/link cannot be fabricated. Identity conflicts quarantine without auto-merge; unavailable required facts are UNKNOWN.

Dossier fields distinguish FACT, ESTIMATE and UNKNOWN with citations/confidence. Required fact filters cannot use estimates as facts. Final gate never creates a new rubric, price threshold or source authorization; offer filters are immutable. Suppression, recipient identity, legal-policy, cost/capacity and cohort admission remain independent deterministic gates. PRODUCT-01 DurableSuppressionTriggerV1 controls suppression, not agent sentiment.

### Concurrency, idempotency and recovery

Queue `alon-ai-qualification-v1` begins at concurrency 2. One source run pins result/page caps, source/query/offer/strategy versions and deadline. Per-lead keys bind workflow/business/phase/input hash; duplicate provider pages/cross-source candidates cannot duplicate the business, lead, spend reservation or phase decision.

Per-lead stages may run concurrently across different leads, never before that lead's accepted provider artifact. Stop before discovery pages, paid research, qualification acceptance and preparation transition; reload suppression/control/current source authority at each admission. A candidate rejected at PRELIMINARY cannot incur deep research. Corrections append evidence/new decisions and may re-enter only under ARCH-03 outside an active frozen cohort. Resume preserves accepted lineage and remaining query/cost/sample capacity.

## Ordered implementation tasks

<!-- roadmap-task id=WF-04-T01 milestone=M5 depends_on=WF-03-T05,DB-02-T03,WF-03-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Freeze source and offer-filter plan —** Input: accepted OfferPackage and source scopes. Operation: pin query/filter/candidate/research budgets and phase schemas. Output: bounded M5 plan. Test evidence: missing/changed offer and unapproved-source denial. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-04-T02 milestone=M5 depends_on=WF-04-T01,PROVIDER-08-T03,AGENT-11-T04 mode=parallel locks=workflow-runtime -->
- [ ] **Implement discovery and preliminary admission —** Input: approved multi-source fixtures and LeadDiscoveryCandidate. Operation: deduplicate businesses, retain conflicts/provenance and materialize PRELIMINARY QualificationDecision. Output: cheap candidate gate. Test evidence: cross-source duplicates, false identity and preliminary rejection cost checks. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-04-T03 milestone=M5 depends_on=WF-04-T02,PROVIDER-06-T01,PROVIDER-06-T03,PROVIDER-05-T04,AGENT-05-T04 mode=parallel locks=workflow-runtime -->
- [ ] **Research only admitted candidates —** Input: accepted preliminary artifacts and bounded evidence ports. Operation: capture factual/estimated/unknown dossier fields with confidence and source spans. Output: accepted LeadResearchDossier. Test evidence: no research before preliminary pass and identity/source conflict cases. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-04-T04 milestone=M5 depends_on=WF-04-T03,AGENT-06-T04,BACKEND-01-T04 mode=parallel locks=workflow-runtime -->
- [ ] **Apply final immutable filters —** Input: dossier and governing OfferPackage. Operation: materialize FINAL decision then run separate preparation/suppression/capacity checks. Output: qualified/rejected pool and readiness. Test evidence: required UNKNOWN/FAIL, phase splice and qualification-without-send authority. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.
<!-- roadmap-task id=WF-04-T05 milestone=M5 depends_on=WF-04-T04,WF-02-T03,PROVIDER-08-T04 mode=serial locks=workflow-runtime,milestone-gate -->
- [ ] **Retain M5 end-to-end recovery evidence —** Input: source activation record and finite pool scenarios. Operation: verify yield, duplicates, cost, factual precision and crash replay at each boundary. Output: M5 gate bundle. Test evidence: no duplicate decision/spend or active-cohort mutation. Failure behavior: stop unsafe admission, retain immutable evidence and expose a typed blocked/failed outcome; no provider retry or state change by inference.

## Test strategy

Contract tests cover exact accepted-artifact version/hash lineage and state ownership. Real isolated PostgreSQL tests inject failure before/after each aggregate/artifact/event/audit/outbox/idempotency transaction. Recorded providers and owned-resource gates cover duplicate/out-of-order delivery, cancellation, stale generation and ambiguity. Required scenarios appear per task; no fake/synthetic evidence counts as real demand.

## Safety, privacy, compliance, observability and cost

Every run pins schema/configuration, producer strategy, GlobalStrategyPackage/StrategyActivation, deadline and finite attempt/tool/token/cost ceilings. Application services reserve paid-call budgets before execution and reconcile all usage. Retention follows DB-06 per record/field purpose and sensitivity; minimized evidence is required before learning reuse.

Telemetry includes safe IDs, hashes, versions, counts, durations, outcomes and costs. It excludes raw recipients, message/calendar content, sensitive budget spans, credentials and hidden reasoning. Source and email content are untrusted data; deterministic legal/provider/suppression/commercial gates and scoped write ports remain mandatory.

## Failure, rollback, recovery and acceptance

Pause closes admission before acknowledgement and retains the exact resume target, accepted inputs, counters/capacity and control generation. Cancel drains only provably uncalled work; uncertain external outcomes remain quarantined with durable evidence. Terminal runs never resume. A valid failed-stage retry creates a new linked finite run; changed inputs create superseding artifacts outside active cohorts.

- [ ] Every boundary has a named deterministic owner and accepted version/hash input.
- [ ] No workflow has direct Gmail/calendar write authority or routine per-message approval.
- [ ] Every replay, pause, terminal stop and ambiguous outcome has a finite coordinator outcome with no blind retry.
- [ ] Cohort and strategy boundaries preserve capacity, immutable evidence and historical attribution.
- [ ] Required contract/recovery/gate evidence is retained before later product use.

Retain schema/transition snapshots, command/artifact/activation lineage, source/provider fixture hashes, full crash matrices, safe audit/event traces, cost reconciliation and gate results.
