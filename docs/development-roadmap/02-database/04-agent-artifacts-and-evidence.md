# Agent Artifacts, Evidence, Provenance, and Evaluation Records

**Document ID:** DB-04
**Status:** Planned M2 persistence; populated from M3
**Milestone:** M2 schema, M3 agent promotion, M4-M9 evidence use
**Owner:** Solo operator
**Prerequisites:** [DB-01](01-core-data-model.md), [DB-02](02-experiment-and-offer-schema.md), [ARCH-02](../01-architecture/02-module-boundaries.md), and [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md)
**Outputs:** Typed agent-run envelope, immutable artifacts, source evidence, provenance edges, validation/acceptance, and evaluation records
**Unlocks:** M3 typed agents/evaluations and evidence-backed M4/M5 workflows
**Risk:** High
**Complexity:** L

## Outcome and timing

M2 creates an immutable evidence substrate before any live model is trusted. M3 writes recorded-fixture and model outputs into it. Agents may produce `PRODUCED` artifacts only; deterministic validators or the operator control every later `ArtifactStatus`. Accepted artifacts can be referenced by transitions but never mutate state themselves.

## Current repository state

The `agents/` package is empty and Pydantic AI is unused. There is no `AgentArtifactEnvelope`, agent run, prompt/model/tool version, evidence item, source capture, provenance graph, validation, acceptance, cost, or evaluation table. Roadmap artifact names are planned vocabulary only.

## Scope and non-goals

In scope: immutable typed output, schema version, producer identity, input snapshot, citations/source captures, tool/model/prompt versions, abstention/confidence, token/cost data, deterministic validation, operator acceptance, supersession, and evaluation datasets/results. Non-goals: storing chain-of-thought, treating confidence as truth, allowing an agent to approve itself, unbounded page archives, opaque provider objects, vector storage without a benchmark, or direct agent state/provider side effects.

## Exact planned implementation surfaces

Create `domain/artifacts.py`, `agents/contracts.py`, `application/artifacts.py`, `persistence/models/artifacts.py`, repositories, and M2 migration tables:

| Table | Required columns/keys | Required constraints/indexes | Owner/event |
| --- | --- | --- | --- |
| `agent_runs` | `agent_run_id uuid PK`, `experiment_id FK`, `workflow_run_id FK`, `agent_type`, `agent_version`, `prompt_version`, `model_provider`, `model_name`, `model_version`, `toolset_version`, `input_snapshot_hash`, `state`, `abstained bool`, usage/cost fields, `correlation_id`, timestamps | unique `(workflow_run_id,agent_type,input_snapshot_hash,agent_version)`; state `PENDING/RUNNING/SUCCEEDED/FAILED`; nonnegative usage/cost; terminal timestamp checks; indexes workflow/type/state | agent runtime reports; no aggregate transition |
| `artifacts` | `artifact_id uuid PK`, `experiment_id FK`, `artifact_type`, `schema_version int`, `artifact_version int`, `status text`, `agent_run_id FK null`, `content_json jsonb`, `content_hash`, `confidence numeric null`, `abstention_reason text null`, `supersedes_artifact_id FK self null`, timestamps | `status in ('PRODUCED','VALIDATED','REJECTED','ACCEPTED','SUPERSEDED')`; unique `(experiment_id,artifact_type,artifact_version)` and `(artifact_type,schema_version,content_hash)`; confidence 0..1; immutable content; indexes experiment/type/status | artifact service; exact artifact catalog events |
| `evidence_items` | `evidence_item_id uuid PK`, `experiment_id FK`, `evidence_type`, `source_uri`, `source_provider`, `retrieved_at`, `published_at null`, `content_hash`, `capture_ref`, `mime_type`, `language`, `license_basis`, `retention_class`, `redaction_state`, timestamps | unique `(source_provider,source_uri,content_hash)`; supported scheme/type/size; immutable capture metadata; indexes experiment/retrieved/source | evidence ingest service |
| `artifact_evidence_links` | `artifact_id FK`, `evidence_item_id FK`, `claim_pointer text`, `relationship text`, `source_excerpt_hash text null`, composite PK | relationship `SUPPORTS/CONTRADICTS/CONTEXT`; unique claim/source edge; no raw excerpt required | artifact validator |
| `artifact_validations` | `artifact_validation_id uuid PK`, `artifact_id FK`, `validator_version`, `schema_valid bool`, `provenance_valid bool`, `reason_codes text[]`, `facts_hash`, `created_at` | unique `(artifact_id,validator_version,facts_hash)`; immutable | validator emits validated/rejected event and transition |
| `artifact_acceptances` | `artifact_acceptance_id uuid PK`, `artifact_id FK`, `acceptance_mode`, `operator_id FK null`, `gate_version`, `scope_hash`, `command_idempotency_key`, `created_at` | one acceptance per artifact/scope; mode `OPERATOR/DETERMINISTIC_GATE`; operator required for operator mode; unique command key | artifact service emits `artifact.accepted.v1` |
| `evaluation_cases` | `evaluation_case_id uuid PK`, `suite_name`, `suite_version`, `case_key`, `input_ref`, `expected_schema_version`, `rubric_json`, `sensitivity_class`, `created_at` | unique `(suite_name,suite_version,case_key)`; immutable/versioned | evaluation owner |
| `evaluation_results` | `evaluation_result_id uuid PK`, `evaluation_case_id FK`, `agent_run_id FK`, `evaluator_version`, `scores_json`, `passed bool`, `reason_codes text[]`, `created_at` | unique `(evaluation_case_id,agent_run_id,evaluator_version)`; immutable; index pass/suite via case | evaluation service |

Artifact types use the product names from PRODUCT-01: `ExperimentBrief`, `IdeaCandidate`, `OfferHypothesis`, `MarketEvidence`, `LeadEvidence`, `QualificationAssessment`, `OutreachDraft`, `ReplyClassification`, `MetricSnapshot`, `EvidenceBundle`, and `ExperimentDecision` where appropriate. A business table remains authoritative when a corresponding artifact is accepted and materialized; the artifact is retained as provenance, not a competing aggregate.

## Ordered implementation tasks

- [ ] **Define typed envelopes and artifact registry —** Input: canonical artifact names and Pydantic AI boundary. Operation: register schema/version, producer, validator, and allowed consumers for each type. Output: serializable contracts. Test evidence: `test_every_artifact_type_has_schema_validator_and_owner`. Failure behavior: reject unknown type/version.
- [ ] **Migrate immutable run/artifact/evidence tables —** Input: table contract. Operation: create constraints, indexes, immutable triggers, and retention classes. Output: M2 schema. Test evidence: real-PostgreSQL migration/constraint tests. Failure behavior: rollback revision.
- [ ] **Implement evidence capture and linking —** Input: bounded provider result. Operation: validate URI/type/size, hash capture, redact, store restricted reference, and link claims. Output: provenance-complete evidence. Test evidence: malicious URI/content/type fixtures. Failure behavior: quarantine evidence and reject dependent artifact.
- [ ] **Implement validation and acceptance transitions —** Input: `PRODUCED` artifact and frozen validator/gate. Operation: append validation, apply ARCH-03 state, and emit exact event atomically. Output: eligible accepted artifact or retained rejection. Test evidence: exhaustive artifact-state matrix and command replay. Failure behavior: no workflow eligibility.
- [ ] **Gate agent promotion on evaluations —** Input: immutable suite/version and agent configuration. Operation: run recorded cases, persist scores/cost, compare frozen thresholds, and record promotion evidence. Output: promoted or rejected version. Test evidence: deterministic fixture rerun. Failure behavior: retain prior promoted version.

## Test strategy

- **Unit `test_agent_can_only_produce_produced_status`:** agent code cannot select later state.
- **Schema `test_artifact_payload_matches_registered_version`:** unknown/invalid JSON is rejected.
- **Provenance `test_claim_requires_valid_source_link`:** missing/quarantined evidence blocks validation.
- **Integration `test_validation_status_event_commit_atomically`:** no status/event split.
- **Security `test_chain_of_thought_and_secrets_are_never_persisted`:** allowlist serialization and scan.
- **Evaluation `test_promotion_requires_quality_and_cost_thresholds`:** failing either retains prior version.

## Security, privacy, compliance, idempotency, observability, and cost

Evidence capture follows scheme/domain/type/size/time limits and treats fetched content as untrusted. Store only task inputs/outputs needed for audit, never hidden reasoning. Sensitive captures use restricted object references, redaction state, and deletion class. Idempotency uses input/config hashes. Telemetry records run/artifact/source IDs, versions, duration, usage, and cost without copying content. Provider cost is reconciled through DB-05.

## Failure, rollback, and operator recovery

Invalid schema/provenance, tool timeout, prompt injection signal, cost overrun, or unsupported source produces a rejected artifact or failed run without aggregate transition. Rollback selects the prior promoted agent/config; artifacts remain immutable. A corrected artifact is a new version linked by `supersedes_artifact_id`. Compromised evidence is quarantined, dependent acceptances revoked through audited commands, and affected transitions paused for operator review.

## Acceptance and retained evidence

- [ ] Agent, artifact, evidence, validation, acceptance, and evaluation records are normalized and immutable.
- [ ] Every artifact has exact producer, schema/version, provenance, validator, consumer, and retention class.
- [ ] Agents cannot accept artifacts, mutate aggregates, call Gmail, or gain provider credentials.
- [ ] Quality and cost gates are reproducible from retained suites/results.

Retain schema snapshots, artifact registry, constraint output, adversarial evidence fixtures, validation transition traces, redaction scans, evaluation reports, and promotion/rollback record.

## Dependencies and next deliverable

DB-04 depends on DB-01/02 and ARCH-02/03. It unlocks M3 agent documents and [WF-03](../03-workflows/03-idea-validation-workflow.md)/[WF-04](../03-workflows/04-lead-qualification-workflow.md); no artifact unlocks sending by itself.
