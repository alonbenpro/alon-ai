# Idea Validation and Offer-Evidence Workflow

**Document ID:** WF-03
**Status:** Planned no-send workflow
**Milestone:** M4
**Owner:** Solo operator
**Prerequisites:** [WF-02](02-experiment-lifecycle.md), DB-02/DB-04/DB-05, and promoted M3 idea/offer/research agents plus recorded provider fixtures
**Outputs:** Accepted idea, offer hypothesis, market evidence, metric/evidence bundle, and `READY_FOR_LEADS` experiment state
**Unlocks:** Synthetic M4 gate and WF-04 lead qualification
**Risk:** High
**Complexity:** L

## Outcome and timing

M4 turns one approved brief into operator-reviewable idea/offer/evidence artifacts without discovering contacts or sending email. Weak evidence stops the workflow; Gmail is not used to compensate for an unvalidated offer.

## Current repository state

No product schema, agent implementation, model/search/page adapter, fixture evaluation, evidence capture, or workflow exists. The frontend headline is not evidence that idea validation works. All agents/providers named here are later M3 prerequisites.

## Scope and non-goals

In scope: frozen brief input, typed idea/offer/market-evidence agent runs, bounded provider calls, provenance/validation, operator/deterministic acceptance, reproducible metric/evidence bundle, and finite completion/failure. Non-goals: lead/contact discovery, Gmail, autonomous selection/decision, unrestricted web crawl, uncited market claims, looping until a model agrees, or mutable artifacts.

## Exact planned implementation surfaces

Create `workflows/idea_validation.py` and application commands in `application/artifacts.py`/`experiments.py`. Runtime ID follows WF-02 with stage `IDEA_VALIDATION`. Queue `alon-ai-research-v1` starts at global concurrency `2`, worker concurrency `2`; model/search provider rate limits are separate pinned queues or adapter quotas and budget reservations still gate every paid call. Workflow step keys are `workflow:{run_id}:step:{idea|offer|research|bundle}:v1`.

Exact product tables touched through application commands are `experiments`, `experiment_briefs`, `metric_definitions`, `workflow_runs`, `agent_runs`, `artifacts`, `artifact_validations`, `artifact_acceptances`, `ideas`, `offer_hypotheses`, `evidence_items`, `artifact_evidence_links`, `budget_reservations`, `cost_entries`, `command_idempotency`, `domain_events`, `audit_events`, and `outbox_messages`.

### Ordered flow and data/event reconciliation

| Step | Reads | Application writes/constraints | Events/failure |
| --- | --- | --- | --- |
| freeze input/start | `experiments(RESEARCHING)`, active `experiment_briefs`, `metric_definitions`, `workflow_runs` | text `input_schema_version`, bounded JSONB payload, and lowercase SHA-256 of DB-01's UTF-8 RFC 8785 envelope; command/event/audit/outbox bundle | existing WF-02 start events; byte/vector/schema mismatch or stale version fails closed |
| generate idea candidates | brief snapshot, budget | `agent_runs`; `artifacts(ArtifactStatus=PRODUCED,type=IdeaCandidate)`; cost/reservation | `artifact.produced.v1`; typed failure closes run |
| validate/select idea | candidate artifact/evidence | `artifact_validations`, accepted artifact, materialized `ideas` version | validated/rejected/accepted events; deterministic/operator selection audit |
| design offer | selected idea + brief + accepted evidence | agent run, `OfferHypothesis` artifact, validations/acceptance, `offer_hypotheses` | artifact events; invalid claim/provenance blocks |
| capture market evidence | offer/brief, bounded providers | `evidence_items`, links, `MarketEvidence` artifact, provider cost | artifact events; unsafe/missing source rejects |
| build evidence bundle | accepted versions, metric rules | `EvidenceBundle` artifact and links, optional metric observations/snapshot | artifact events; insufficient evidence is explicit |
| complete/fail | all required accepted artifacts and run | WF-02 terminal run + `experiments` update + transaction safety tables | `workflow.run_completed.v1` + `experiment.state_changed.v1` to `READY_FOR_LEADS`, or workflow/experiment failure events |

Agents can create `PRODUCED` rows only. Deterministic validators verify typed schema, provenance completeness, source safety, budget/cost, and cross-artifact version consistency. Operator selection/acceptance is an idempotent command. No step reads provider secrets from an artifact or stores opaque SDK objects.

## Ordered implementation tasks

- [ ] **Freeze M4 fixture/input contract —** Input: approved brief/metric versions and M3 promoted configs. Operation: encode the DB-01 RFC 8785 version/payload envelope, reproduce its golden SHA-256 vectors independently, and verify before every resumed step. Output: stable run input snapshot. Test evidence: `test_resume_rejects_changed_brief_hash_schema_type_or_json_null_without_new_run`. Failure behavior: fail run; operator revises/restarts explicitly.
- [ ] **Implement typed artifact steps —** Input: frozen refs/read-only provider ports/budget. Operation: run each promoted agent once per command key and persist envelope/artifact/cost. Output: produced candidates/evidence. Test evidence: recorded fixture, schema, timeout, retry, and cost tests. Failure behavior: bounded retry only for classified no-side-effect provider failures.
- [ ] **Implement validation/acceptance/materialization —** Input: produced artifact and source links. Operation: validate and accept/reject, then materialize normalized idea/offer under expected version. Output: authoritative product records with provenance. Test evidence: adversarial citation and concurrency tests. Failure behavior: retain rejection; do not transition.
- [ ] **Complete evidence bundle and stage —** Input: all accepted required artifacts/metrics. Operation: build immutable bundle, recheck versions, and invoke WF-02 completion. Output: `READY_FOR_LEADS`. Test evidence: end-to-end synthetic fixture and restart at every step. Failure behavior: `FAILED` with closed ARCH-03 exits.
- [ ] **Prove no-send boundary —** Input: full M4 composition/import graph. Operation: assert no Gmail/send port is registered or reachable. Output: M4 evidence. Test evidence: `test_m4_workflow_has_no_gmail_or_sendgateway_edge`. Failure behavior: M4 blocked.

## Test strategy

- **Contract `test_every_agent_output_matches_registered_artifact_schema`:** typed envelope/version.
- **Provenance `test_offer_claims_link_to_captured_evidence_or_abstain`:** no invented certainty.
- **Recovery `test_kill_after_each_artifact_commit_does_not_duplicate_agent_call_or_version`:** command replay.
- **Integration `test_accepted_artifacts_and_ready_for_leads_transition_are_consistent`:** gate recheck.
- **Adversarial `test_untrusted_page_cannot_instruct_agent_or_workflow_to_send_or_mutate`:** tool/authority isolation.
- **Cost `test_provider_budget_exhaustion_fails_before_call`:** reservation first.

## Security, privacy, compliance, idempotency, observability, and cost

Fetchers enforce URL/domain/type/size/time rules and treat content as untrusted. Store citations/capture hashes and minimal content under DB-04 retention. Step/config/input hashes prevent duplicate calls. Traces include safe artifact/evidence IDs and versions, provider duration/usage/cost, validation reasons, and abstention; no chain-of-thought, secrets, or unnecessary source content is logged.

## Failure, rollback, and operator recovery

Provider, schema, provenance, cost, or quality failure stops at the affected step; accepted earlier artifacts remain immutable evidence but do not force completion. Roll back to prior promoted agent/provider config by starting a new run with an explicit version. Correct outputs through superseding artifacts. Exhausted/nonretryable run failure follows ARCH-03 retry/revise/cancel, never an immortal loop.

## Acceptance and retained evidence

- [ ] One synthetic approved brief produces accepted typed idea, offer, market evidence, and evidence bundle.
- [ ] Every step read/write maps to DB-02/04/05 and every stage event maps to ARCH-03.
- [ ] Provider calls are bounded, idempotent where possible, costed, and provenance-complete.
- [ ] Agents cannot accept/materialize/transition/send.
- [ ] The entire M4 path has no Gmail authority.

Retain fixture/config hashes, artifact/evidence schemas, evaluation promotion refs, source captures/hashes, restart traces, cost ledger, no-send import proof, and synthetic run bundle.

## Dependencies and next deliverable

WF-03 depends on WF-02, M2 persistence, and M3 promotion gates. It unlocks [WF-04 lead qualification](04-lead-qualification-workflow.md); it does not unlock outreach.
