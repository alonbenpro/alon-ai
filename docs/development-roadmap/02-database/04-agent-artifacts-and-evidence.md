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

### Exact DDL-equivalent artifact and evidence contract

```sql
CREATE TABLE agent_runs (
    agent_run_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    workflow_run_id uuid NOT NULL,
    agent_type text NOT NULL,
    agent_version text NOT NULL,
    prompt_version text NOT NULL,
    model_provider text NOT NULL,
    model_name text NOT NULL,
    model_version text NOT NULL,
    toolset_version text NOT NULL,
    input_snapshot_hash char(64) NOT NULL,
    state text NOT NULL DEFAULT 'PENDING',
    abstained boolean NOT NULL DEFAULT false,
    abstention_reason text NULL,
    input_tokens integer NOT NULL DEFAULT 0,
    output_tokens integer NOT NULL DEFAULT 0,
    tool_call_count integer NOT NULL DEFAULT 0,
    cost_minor bigint NOT NULL DEFAULT 0,
    currency char(3) NOT NULL,
    error_code text NULL,
    correlation_id uuid NOT NULL,
    started_at timestamptz NULL,
    finished_at timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_agent_runs PRIMARY KEY (agent_run_id),
    CONSTRAINT fk_agent_runs_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_agent_runs_workflow_input FOREIGN KEY (workflow_run_id, input_snapshot_hash) REFERENCES workflow_runs (workflow_run_id, input_hash) ON DELETE RESTRICT,
    CONSTRAINT uq_agent_runs_input UNIQUE (workflow_run_id, agent_type, input_snapshot_hash, agent_version),
    CONSTRAINT ck_agent_runs_hash CHECK (input_snapshot_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_agent_runs_state CHECK (state IN ('PENDING','RUNNING','SUCCEEDED','FAILED')),
    CONSTRAINT ck_agent_runs_usage CHECK (input_tokens >= 0 AND output_tokens >= 0 AND tool_call_count >= 0 AND cost_minor >= 0 AND currency ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_agent_runs_abstention CHECK ((NOT abstained AND abstention_reason IS NULL) OR (abstained AND abstention_reason IS NOT NULL)),
    CONSTRAINT ck_agent_runs_terminal CHECK ((state IN ('SUCCEEDED','FAILED')) = (finished_at IS NOT NULL)),
    CONSTRAINT ck_agent_runs_error CHECK (state <> 'FAILED' OR error_code IS NOT NULL)
);
CREATE INDEX ix_agent_runs_workflow_created ON agent_runs (workflow_run_id, created_at DESC);
CREATE INDEX ix_agent_runs_type_state ON agent_runs (agent_type, state, created_at DESC);
CREATE INDEX ix_agent_runs_correlation ON agent_runs (correlation_id);

CREATE TABLE artifacts (
    artifact_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    artifact_type text NOT NULL,
    schema_version integer NOT NULL,
    artifact_version integer NOT NULL,
    status text NOT NULL DEFAULT 'PRODUCED',
    agent_run_id uuid NULL,
    content_json jsonb NOT NULL,
    content_hash char(64) NOT NULL,
    confidence numeric(8,7) NULL,
    abstention_reason text NULL,
    supersedes_artifact_id uuid NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_artifacts PRIMARY KEY (artifact_id),
    CONSTRAINT fk_artifacts_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_artifacts_agent_run FOREIGN KEY (agent_run_id) REFERENCES agent_runs (agent_run_id) ON DELETE RESTRICT,
    CONSTRAINT fk_artifacts_supersedes FOREIGN KEY (supersedes_artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT,
    CONSTRAINT uq_artifacts_version UNIQUE (experiment_id, artifact_type, artifact_version),
    CONSTRAINT uq_artifacts_content UNIQUE (artifact_type, schema_version, content_hash),
    CONSTRAINT ck_artifacts_versions CHECK (schema_version > 0 AND artifact_version > 0),
    CONSTRAINT ck_artifacts_status CHECK (status IN ('PRODUCED','VALIDATED','REJECTED','ACCEPTED','SUPERSEDED')),
    CONSTRAINT ck_artifacts_content CHECK (jsonb_typeof(content_json) = 'object' AND content_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_artifacts_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT ck_artifacts_abstention CHECK (abstention_reason IS NULL OR confidence IS NULL)
);
CREATE INDEX ix_artifacts_experiment_type_status ON artifacts (experiment_id, artifact_type, status, artifact_version DESC);
CREATE INDEX ix_artifacts_agent_run ON artifacts (agent_run_id) WHERE agent_run_id IS NOT NULL;

CREATE TABLE evidence_items (
    evidence_item_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    evidence_type text NOT NULL,
    source_uri text NOT NULL,
    source_provider text NOT NULL,
    retrieved_at timestamptz NOT NULL,
    published_at timestamptz NULL,
    content_hash char(64) NOT NULL,
    capture_ref text NOT NULL,
    mime_type text NOT NULL,
    language text NOT NULL,
    license_basis text NOT NULL,
    retention_class text NOT NULL DEFAULT 'SENSITIVE_SHORT',
    redaction_state text NOT NULL DEFAULT 'RAW_RESTRICTED',
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_evidence_items PRIMARY KEY (evidence_item_id),
    CONSTRAINT fk_evidence_items_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT uq_evidence_items_capture UNIQUE (source_provider, source_uri, content_hash),
    CONSTRAINT ck_evidence_items_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_evidence_items_uri CHECK (source_uri ~ '^https://'),
    CONSTRAINT ck_evidence_items_retention CHECK (retention_class = 'SENSITIVE_SHORT'),
    CONSTRAINT ck_evidence_items_redaction CHECK (redaction_state IN ('RAW_RESTRICTED','REDACTED','PURGED'))
);
CREATE INDEX ix_evidence_items_experiment_retrieved ON evidence_items (experiment_id, retrieved_at DESC);
CREATE INDEX ix_evidence_items_source ON evidence_items (source_provider, source_uri);

CREATE TABLE artifact_evidence_links (
    artifact_id uuid NOT NULL,
    evidence_item_id uuid NOT NULL,
    claim_pointer text NOT NULL,
    relationship text NOT NULL,
    source_excerpt_hash char(64) NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_artifact_evidence_links PRIMARY KEY (artifact_id, evidence_item_id, claim_pointer, relationship),
    CONSTRAINT fk_artifact_evidence_links_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT,
    CONSTRAINT fk_artifact_evidence_links_evidence FOREIGN KEY (evidence_item_id) REFERENCES evidence_items (evidence_item_id) ON DELETE RESTRICT,
    CONSTRAINT ck_artifact_evidence_links_relationship CHECK (relationship IN ('SUPPORTS','CONTRADICTS','CONTEXT')),
    CONSTRAINT ck_artifact_evidence_links_pointer CHECK (claim_pointer LIKE '/%'),
    CONSTRAINT ck_artifact_evidence_links_hash CHECK (source_excerpt_hash IS NULL OR source_excerpt_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_artifact_evidence_links_evidence ON artifact_evidence_links (evidence_item_id, artifact_id);

CREATE TABLE artifact_validations (
    artifact_validation_id uuid NOT NULL,
    artifact_id uuid NOT NULL,
    validator_version text NOT NULL,
    schema_valid boolean NOT NULL,
    provenance_valid boolean NOT NULL,
    reason_codes text[] NOT NULL,
    facts_hash char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_artifact_validations PRIMARY KEY (artifact_validation_id),
    CONSTRAINT fk_artifact_validations_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT,
    CONSTRAINT uq_artifact_validations_inputs UNIQUE (artifact_id, validator_version, facts_hash),
    CONSTRAINT ck_artifact_validations_reasons CHECK ((schema_valid AND provenance_valid AND cardinality(reason_codes) = 0) OR (NOT (schema_valid AND provenance_valid) AND cardinality(reason_codes) > 0)),
    CONSTRAINT ck_artifact_validations_hash CHECK (facts_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_artifact_validations_artifact_created ON artifact_validations (artifact_id, created_at DESC);

CREATE TABLE artifact_acceptances (
    artifact_acceptance_id uuid NOT NULL,
    artifact_id uuid NOT NULL,
    acceptance_mode text NOT NULL,
    operator_id uuid NULL,
    gate_version text NOT NULL,
    scope_hash char(64) NOT NULL,
    command_idempotency_key text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_artifact_acceptances PRIMARY KEY (artifact_acceptance_id),
    CONSTRAINT fk_artifact_acceptances_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT,
    CONSTRAINT fk_artifact_acceptances_operator FOREIGN KEY (operator_id) REFERENCES operators (operator_id) ON DELETE RESTRICT,
    CONSTRAINT uq_artifact_acceptances_scope UNIQUE (artifact_id, scope_hash),
    CONSTRAINT uq_artifact_acceptances_command UNIQUE (command_idempotency_key),
    CONSTRAINT ck_artifact_acceptances_mode CHECK (acceptance_mode IN ('OPERATOR','DETERMINISTIC_GATE')),
    CONSTRAINT ck_artifact_acceptances_operator CHECK ((acceptance_mode = 'OPERATOR') = (operator_id IS NOT NULL)),
    CONSTRAINT ck_artifact_acceptances_hash CHECK (scope_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_artifact_acceptances_created ON artifact_acceptances (created_at DESC);

CREATE TABLE evaluation_cases (
    evaluation_case_id uuid NOT NULL,
    suite_name text NOT NULL,
    suite_version text NOT NULL,
    case_key text NOT NULL,
    input_schema_version text NOT NULL,
    input_snapshot jsonb NOT NULL,
    input_hash char(64) NOT NULL,
    expected_schema_version text NOT NULL,
    expected_snapshot jsonb NOT NULL,
    expected_hash char(64) NOT NULL,
    rubric_schema_version integer NOT NULL,
    rubric_json jsonb NOT NULL,
    sensitivity_class text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_evaluation_cases PRIMARY KEY (evaluation_case_id),
    CONSTRAINT uq_evaluation_cases_key UNIQUE (suite_name, suite_version, case_key),
    CONSTRAINT ck_evaluation_cases_versions CHECK (input_schema_version ~ '^[a-z0-9][a-z0-9._-]{0,63}$' AND expected_schema_version ~ '^[a-z0-9][a-z0-9._-]{0,63}$' AND rubric_schema_version > 0),
    CONSTRAINT ck_evaluation_cases_json CHECK (jsonb_typeof(input_snapshot) = 'object' AND jsonb_typeof(expected_snapshot) = 'object' AND jsonb_typeof(rubric_json) = 'object'),
    CONSTRAINT ck_evaluation_cases_hashes CHECK (input_hash ~ '^[0-9a-f]{64}$' AND expected_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_evaluation_cases_sensitivity CHECK (sensitivity_class IN ('SYNTHETIC','REDACTED','RESTRICTED'))
);
CREATE INDEX ix_evaluation_cases_suite ON evaluation_cases (suite_name, suite_version, created_at DESC);

CREATE TABLE evaluation_results (
    evaluation_result_id uuid NOT NULL,
    evaluation_case_id uuid NOT NULL,
    agent_run_id uuid NOT NULL,
    evaluator_version text NOT NULL,
    scores_schema_version integer NOT NULL,
    scores_json jsonb NOT NULL,
    scores_hash char(64) NOT NULL,
    passed boolean NOT NULL,
    reason_codes text[] NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_evaluation_results PRIMARY KEY (evaluation_result_id),
    CONSTRAINT fk_evaluation_results_case FOREIGN KEY (evaluation_case_id) REFERENCES evaluation_cases (evaluation_case_id) ON DELETE RESTRICT,
    CONSTRAINT fk_evaluation_results_agent_run FOREIGN KEY (agent_run_id) REFERENCES agent_runs (agent_run_id) ON DELETE RESTRICT,
    CONSTRAINT uq_evaluation_results_run UNIQUE (evaluation_case_id, agent_run_id, evaluator_version),
    CONSTRAINT ck_evaluation_results_schema CHECK (scores_schema_version > 0 AND jsonb_typeof(scores_json) = 'object' AND scores_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_evaluation_results_reasons CHECK ((passed AND cardinality(reason_codes) = 0) OR (NOT passed AND cardinality(reason_codes) > 0))
);
CREATE INDEX ix_evaluation_results_agent_passed ON evaluation_results (agent_run_id, passed);
```

`evaluation_cases.input_hash` and `expected_hash` use DB-01's canonical RFC 8785 envelope algorithm with their respective text schema versions and JSON payloads. `agent_runs.input_snapshot_hash` is not a new digest: its composite FK requires the exact verified `workflow_runs.input_hash`. Evaluation fixtures include DB-01's golden vectors; schema migration validates the old digest before an in-memory upcast and writes a new immutable evaluation-case version rather than mutating bytes.

| Table | Exclusive write owner | Retention class / retention owner |
| --- | --- | --- |
| `agent_runs` | `AgentRunRecordingService` | `EVALUATION_VERSIONED` / `RetentionCommandService` |
| `artifacts` | `ArtifactCommandService`; agents may request only the `PRODUCED` insert path | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `evidence_items` | `EvidenceIngestService` | `SENSITIVE_SHORT` / `RetentionCommandService` |
| `artifact_evidence_links` | `ArtifactValidationService` | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `artifact_validations` | `ArtifactValidationService` | `SAFETY_LONG` / `RetentionCommandService` |
| `artifact_acceptances` | `ArtifactAcceptanceService` | `SAFETY_LONG` / `RetentionCommandService` |
| `evaluation_cases` | `EvaluationSuiteCommandService` | `EVALUATION_VERSIONED` / `RetentionCommandService` |
| `evaluation_results` | `EvaluationExecutionService` | `EVALUATION_VERSIONED` / `RetentionCommandService` |

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
