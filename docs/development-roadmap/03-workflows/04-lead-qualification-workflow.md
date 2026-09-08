# Evidence-Backed Lead Discovery and Qualification Workflow

**Document ID:** WF-04
**Status:** Planned no-send workflow
**Milestone:** M5 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-04-T01 -> WF-04-T02 -> WF-04-T03 -> WF-04-T04 -> WF-04-T05`; cross-document task Inputs `WF-04-T01 <- WF-03-T05,DB-02-T03,WF-03-T03; WF-04-T02 <- PROVIDER-06-T02; WF-04-T03 <- PROVIDER-06-T01,PROVIDER-06-T03,PROVIDER-05-T01,AGENT-05-T03; WF-04-T04 <- AGENT-06-T03,BACKEND-01-T04; WF-04-T05 <- WF-02-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): passing M4 evidence, [WF-02](02-experiment-lifecycle.md), DB-03/04/05, and promoted M3 lead research/qualification agents/providers
**Outputs:** Deduplicated businesses/leads, accepted lead evidence, immutable assessments, qualified/disqualified states, and `READY_FOR_OUTREACH` preparation state
**Unlocks:** M5 exit and M6 preparation; not send authority
**Risk:** Critical
**Complexity:** L

## Outcome and timing

M5 produces an evidence-backed, deduplicated prospect pool large enough to supply the next registered cohort plus its bounded reserve without sending. It may prepare candidates for the full staged program, but `QUALIFIED` and experiment `READY_FOR_OUTREACH` mean preparation passed only. They do not assign a stage, override suppression/compliance/approvals/budgets, open a barrier, or create `SendGateway` authority.

## Current repository state

No lead/business/provider/enrichment record, identity service, criteria, lead agent, dedupe, suppression implementation, campaign, contact store, or workflow exists. No real or test recipient has been discovered by the product.

## Scope and non-goals

In scope: bounded candidate discovery, business identity, conflict quarantine, source provenance, research, frozen qualification criteria, deterministic score/completeness gate, suppression-before/after qualification, sample gate, and finite completion. Non-goals: buying/scraping contact dumps, automatic conflict merge, guessing personal data, direct enrichment proliferation, sending/drafting, qualification by model confidence alone, or promoting `QUALIFIED` into a send intent.

## Exact planned implementation surfaces

Create `workflows/lead_qualification.py`, identity/lead application services, and M5 evaluation/recovery tests. Runtime ID uses stage `LEAD_QUALIFICATION`. Queue `alon-ai-qualification-v1` starts with global concurrency `2`, worker concurrency `2`; discovery/provider start rates are separately pinned to provider terms/budget. One lead subtask key is `workflow:{run_id}:lead:{business_identity_key}:step:{research|qualify}:v1`.

Exact product tables touched through application commands are `experiments`, `workflow_runs`, `businesses`, `leads`, `lead_assessments`, `suppression_entries`, `agent_runs`, `artifacts`, `evidence_items`, `artifact_evidence_links`, `artifact_validations`, `artifact_acceptances`, `budget_reservations`, `cost_entries`, `command_idempotency`, `domain_events`, `audit_events`, and `outbox_messages`.

### Lead and experiment transition/data map

| Action | Required state/reads | Atomic writes/constraint | Exact event/state result |
| --- | --- | --- | --- |
| start M5 | experiment `READY_FOR_LEADS`, accepted offer/evidence, criteria version | create run, transition experiment `QUALIFYING_LEADS`, command/event/audit/outbox | `workflow.run_started.v1`, `experiment.state_changed.v1` |
| discover candidate | provider evidence + identity inputs | upsert `businesses.identity_key`; insert unique `(experiment_id,business_id)` lead + evidence/source refs | `lead.discovered.v1`; state `DISCOVERED`; conflict emits `lead.identity_conflict_detected.v1` and quarantines |
| queue/research | `DISCOVERED`, provenance, no active suppression | state `RESEARCH_PENDING`; agent run/evidence/artifact commands under uniques | accepted `LeadEvidence` produces `lead.evidence_recorded.v1` and `RESEARCHED` |
| queue/qualify | `RESEARCHED`, frozen criteria, accepted evidence | state `QUALIFICATION_PENDING`; insert unique assessment/config hash | deterministic gate emits `lead.qualified.v1` -> `QUALIFIED` or `lead.disqualified.v1` -> `DISQUALIFIED` |
| suppress | any non-archived lead + active suppression match | insert/link `suppression_entries`, update lead version/state | `lead.suppressed.v1` -> `SUPPRESSED`; wins over approval/qualification |
| complete M5 | sample/quality/provenance/dedupe gates; no unresolved conflicts | close run, transition experiment `READY_FOR_OUTREACH`; safety transaction records | `workflow.run_completed.v1`, `experiment.state_changed.v1` |
| fail M5 | bounded exhaustion/nonretryable error | run `FAILED`; experiment `FAILED` fields/version | `workflow.run_failed.v1`, `experiment.failed.v1`, `experiment.state_changed.v1` |

Identity conflict never overwrites/merges. A corrected evidence/criteria version re-enters `RESEARCHED` or `QUALIFICATION_PENDING` only through an audited application command, using the exact ARCH-03 rule. Workflow steps do not update ORM rows directly.

## Ordered implementation tasks

<!-- roadmap-task id=WF-04-T01 milestone=M5 depends_on=WF-03-T05,DB-02-T03,WF-03-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Freeze criteria and candidate bounds —** Input: experiment/offer versions and WF-03 authoritative product records with provenance supplying the evidence versions, source/provider allowlist, `100/200/300/400` staged demand, bounded reserve, and time/cost caps. Operation: store the exact text schema version/payload and SHA-256 of DB-01's UTF-8 RFC 8785 envelope; require cross-stage dedupe and preserve subsegment allocation without assigning SEND authority. Output: reproducible M5 manifest capable of supplying the next stage. Test evidence: drift/overscope/schema-type/encoding, duplicate identity, and insufficient-next-cohort rejection. Failure behavior: no discovery call or weaker criteria.
<!-- roadmap-task id=WF-04-T02 milestone=M5 depends_on=WF-04-T01,PROVIDER-06-T02 mode=parallel locks=workflow-runtime -->
- [ ] **Implement deterministic business identity —** Input: normalized domain/name/country/source facts. Operation: derive identity key, insert/upsert under unique constraints, and quarantine conflicts. Output: one business/lead or visible conflict. Test evidence: normalization vectors and concurrent duplicates. Failure behavior: no auto-merge/qualification.
<!-- roadmap-task id=WF-04-T03 milestone=M5 depends_on=WF-04-T02,PROVIDER-06-T01,PROVIDER-06-T03,PROVIDER-05-T01,AGENT-05-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Implement research/evidence subtask —** Input: lead/provenance, read-only bounded tools, budget; implemented lead-research typed capability contract and produced research artifacts. Operation: record agent/evidence/artifact, validate and attach accepted evidence. Output: `RESEARCHED`. Test evidence: malicious/contradictory/missing source and restart fixtures. Failure behavior: reject/abstain; no fabricated completeness.
<!-- roadmap-task id=WF-04-T04 milestone=M5 depends_on=WF-04-T03,AGENT-06-T03,BACKEND-01-T04 mode=parallel locks=workflow-runtime -->
- [ ] **Implement qualification gate —** Input: frozen criteria + accepted evidence + typed assessment; AGENT-06 typed assessment and frozen specialist qualification contract; implemented LeadQualificationService and tested qualification-artifact/weighted-gate handoff contract. Operation: compute deterministic completeness/score result, insert immutable assessment, and apply exact transition/event. Output: qualified/disqualified reasoned state. Test evidence: labeled evaluation and threshold boundary tests. Failure behavior: disqualify or retain pending with explicit error; never default qualify.
<!-- roadmap-task id=WF-04-T05 milestone=M5 depends_on=WF-04-T04,WF-02-T03 mode=serial locks=workflow-runtime,milestone-gate -->
- [ ] **Complete M5 and prove no-send —** Input: bounded qualified pool, cross-stage identity proof, all conflicts/tasks terminal, and the WF-02 versioned atomic completion-handler interface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: produce gate evidence and invoke WF-02 completion; retain this gate's signed decision review while granting only preparation for later stage admission. Output: complete versioned finite WF-04 workflow contract plus `READY_FOR_OUTREACH` preparation state. Test evidence: synthetic E2E, restart, suppression, cross-stage dedupe, and import/call graph. Failure behavior: M5 blocked; no M6 workflow start or cohort authority.

## Test strategy

- **Identity `test_name_domain_country_variants_deduplicate_or_conflict_explicitly`:** no silent merge.
- **Concurrency `test_two_discoveries_create_one_experiment_business_lead`:** named uniques.
- **Evaluation `test_qualification_threshold_and_abstention_match_labeled_suite`:** quality gate.
- **Suppression `test_suppression_wins_before_during_and_after_qualification`:** state/event proof.
- **Recovery `test_restart_each_lead_step_does_not_repeat_paid_call_or_assessment`:** command keys.
- **Static `test_m5_workflow_cannot_import_gmail_send_or_create_intent`:** no-send boundary.

## Security, privacy, compliance, idempotency, observability, and cost

Collect minimal business/contact data from approved sources and record lawful-purpose/configuration facts for later review; this is not a legal-compliance claim. Encrypt contact details, hash dedupe/suppression keys, and keep raw captures short-lived. Per-lead step keys, provider result hashes, and unique assessments prevent repeats. Metrics include source coverage, conflicts, dedupe rate, abstention/quality, suppression, provider cost, operator review time, and safe error codes.

## Failure, rollback, and operator recovery

Provider/source/identity/criteria failures stop or quarantine only bounded work; they do not relax thresholds. Pause the experiment on systemic provenance/privacy failure. Roll back agent/provider/criteria by a new run/version; never rewrite assessments. Operator resolves conflict through an audited command with evidence. A failed experiment uses ARCH-03 retry/revise/cancel and a new run.

## Acceptance and retained evidence

- [ ] Candidate discovery is bounded, source-backed, minimized, deduplicated, and conflict-visible.
- [ ] Every lead transition/read/write uses DB-03/04/05 constraints and ARCH-03 names/events.
- [ ] Qualification is deterministic over accepted typed evidence and frozen criteria.
- [ ] Suppression always wins and can act at any non-archived state.
- [ ] `READY_FOR_OUTREACH`/`QUALIFIED` confer no send authority and M5 has no Gmail edge.

Retain run/criteria/provider hashes, identity vectors/races, source/evidence captures, labeled evaluation, assessment/event fixtures, suppression/restart/no-send results, and M5 gate bundle.

## Dependencies and next deliverable

WF-04 depends on M4, M2 persistence, and M3 promoted lead contracts. Passing M5 unlocks preparation for [WF-05 outreach/reply](05-outreach-and-reply-workflow.md), which still requires all M6 provider/policy/security/test-inbox prerequisites.
