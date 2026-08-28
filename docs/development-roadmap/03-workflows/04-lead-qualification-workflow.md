# Evidence-Backed Lead Discovery and Qualification Workflow

**Document ID:** WF-04
**Status:** Planned no-send workflow
**Milestone:** M5
**Owner:** Solo operator
**Prerequisites:** passing M4 evidence, [WF-02](02-experiment-lifecycle.md), DB-03/04/05, and promoted M3 lead research/qualification agents/providers
**Outputs:** Deduplicated businesses/leads, accepted lead evidence, immutable assessments, qualified/disqualified states, and `READY_FOR_OUTREACH` preparation state
**Unlocks:** M5 exit and M6 preparation; not send authority
**Risk:** Critical
**Complexity:** L

## Outcome and timing

M5 produces a small evidence-backed prospect set without sending. `QUALIFIED` and experiment `READY_FOR_OUTREACH` mean preparation passed only. They do not override suppression, compliance facts, approvals, budgets, M1/M6 gates, global/test-inbox controls, or `SendGateway`.

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

- [ ] **Freeze criteria and candidate bounds —** Input: experiment/offer/evidence versions, source/provider allowlist, sample/time/cost caps. Operation: hash the run input and criteria. Output: reproducible M5 manifest. Test evidence: drift/overscope rejection. Failure behavior: no discovery call.
- [ ] **Implement deterministic business identity —** Input: normalized domain/name/country/source facts. Operation: derive identity key, insert/upsert under unique constraints, and quarantine conflicts. Output: one business/lead or visible conflict. Test evidence: normalization vectors and concurrent duplicates. Failure behavior: no auto-merge/qualification.
- [ ] **Implement research/evidence subtask —** Input: lead/provenance, read-only bounded tools, budget. Operation: record agent/evidence/artifact, validate and attach accepted evidence. Output: `RESEARCHED`. Test evidence: malicious/contradictory/missing source and restart fixtures. Failure behavior: reject/abstain; no fabricated completeness.
- [ ] **Implement qualification gate —** Input: frozen criteria + accepted evidence + typed assessment. Operation: compute deterministic completeness/score result, insert immutable assessment, and apply exact transition/event. Output: qualified/disqualified reasoned state. Test evidence: labeled evaluation and threshold boundary tests. Failure behavior: disqualify or retain pending with explicit error; never default qualify.
- [ ] **Complete M5 and prove no-send —** Input: bounded sample and all conflicts/tasks terminal. Operation: produce gate evidence and invoke WF-02 completion. Output: `READY_FOR_OUTREACH` preparation state. Test evidence: synthetic E2E, restart, suppression, and import/call graph. Failure behavior: M5 blocked; no M6 workflow start.

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
