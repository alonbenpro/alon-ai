# Experiment, Idea, Offer, Metric, and Decision Schema

**Document ID:** DB-02
**Status:** Planned M2 product schema
**Milestone:** M2; first consumed by M4
**Owner:** Solo operator
**Prerequisites:** [DB-01](01-core-data-model.md), [product scope](../00-product-strategy/01-product-scope.md), [success metrics](../00-product-strategy/02-success-metrics.md), and [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md)
**Outputs:** Immutable experiment briefs, ideas, offer hypotheses, metric plans/snapshots, and operator decisions
**Unlocks:** WF-02 experiment lifecycle, WF-03 idea validation, M4 synthetic experiment
**Risk:** High
**Complexity:** L

## Outcome and timing

This schema makes the product bet reproducible before an agent or workflow can elaborate it. Mutable experiment state stays on `experiments`; briefs, ideas, offers, metric definitions, snapshots, and decisions are immutable versioned evidence. M2 creates the structure, M3 produces typed artifacts, and M4 exercises it without outreach.

## Current repository state

The roadmap defines `ExperimentBrief`, `IdeaCandidate`, `OfferHypothesis`, `MetricSnapshot`, `EvidenceBundle`, and `ExperimentDecision`, but none is implemented or persisted. No current table, migration, API, agent, workflow, or UI may be described as providing them.

## Scope and non-goals

In scope: exact normalized records for scope versions, idea candidates, offer hypotheses, success/kill metrics, immutable snapshots, and decisions. Non-goals: free-form editable blobs as aggregate truth, agent-authored decisions, automatic `SCALE`, billing/pricing engines, product catalog, multi-experiment portfolio optimization, or outreach activation.

## Exact planned implementation surfaces

Create `domain/experiments.py`, `domain/offers.py`, `domain/metrics.py`, `persistence/models/experiments.py`, repositories, and an M2 migration.

### Exact DDL-equivalent experiment contract

```sql
CREATE TABLE experiment_briefs (
    experiment_brief_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    brief_version integer NOT NULL,
    experiment_code text NOT NULL,
    customer_segment text NOT NULL,
    problem_hypothesis text NOT NULL,
    offer_hypothesis text NOT NULL,
    operator_advantage text NOT NULL,
    jurisdictions_schema_version integer NOT NULL,
    jurisdictions jsonb NOT NULL,
    baseline_method text NOT NULL,
    total_cash_cap_ils_minor bigint NOT NULL,
    provider_cash_cap_ils_minor bigint NOT NULL,
    operator_hours_cap numeric(8,2) NOT NULL,
    max_researched_leads integer NOT NULL,
    max_qualified_leads integer NOT NULL,
    max_contacted_leads integer NOT NULL,
    max_concurrently_active_leads integer NOT NULL,
    authority_level text NOT NULL,
    success_rule_schema_version integer NOT NULL,
    success_rule jsonb NOT NULL,
    kill_rule_schema_version integer NOT NULL,
    kill_rule jsonb NOT NULL,
    decision_date_condition text NOT NULL,
    content_hash char(64) NOT NULL,
    created_by_operator_id uuid NOT NULL,
    supersedes_brief_id uuid NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_experiment_briefs PRIMARY KEY (experiment_brief_id),
    CONSTRAINT fk_experiment_briefs_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_experiment_briefs_operator FOREIGN KEY (created_by_operator_id) REFERENCES operators (operator_id) ON DELETE RESTRICT,
    CONSTRAINT fk_experiment_briefs_supersedes FOREIGN KEY (supersedes_brief_id) REFERENCES experiment_briefs (experiment_brief_id) ON DELETE RESTRICT,
    CONSTRAINT uq_experiment_briefs_version UNIQUE (experiment_id, brief_version),
    CONSTRAINT uq_experiment_briefs_code UNIQUE (experiment_code),
    CONSTRAINT uq_experiment_briefs_hash UNIQUE (experiment_id, content_hash),
    CONSTRAINT ck_experiment_briefs_versions CHECK (brief_version > 0 AND jurisdictions_schema_version > 0 AND success_rule_schema_version > 0 AND kill_rule_schema_version > 0),
    CONSTRAINT ck_experiment_briefs_json CHECK (jsonb_typeof(jurisdictions) = 'array' AND jsonb_typeof(success_rule) = 'object' AND jsonb_typeof(kill_rule) = 'object'),
    CONSTRAINT ck_experiment_briefs_caps CHECK (total_cash_cap_ils_minor >= 0 AND provider_cash_cap_ils_minor >= 0 AND provider_cash_cap_ils_minor <= total_cash_cap_ils_minor AND operator_hours_cap > 0 AND max_researched_leads >= 0 AND max_qualified_leads BETWEEN 0 AND max_researched_leads AND max_contacted_leads BETWEEN 0 AND max_qualified_leads AND max_concurrently_active_leads BETWEEN 0 AND max_contacted_leads),
    CONSTRAINT ck_experiment_briefs_authority CHECK (authority_level IN ('NO_SEND','TEST_INBOX_ONLY','BOUNDED_REAL_RECIPIENTS')),
    CONSTRAINT ck_experiment_briefs_hash CHECK (content_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_experiment_briefs_experiment_created ON experiment_briefs (experiment_id, created_at DESC);

CREATE TABLE ideas (
    idea_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    idea_version integer NOT NULL,
    title text NOT NULL,
    problem_statement text NOT NULL,
    target_customer text NOT NULL,
    status text NOT NULL DEFAULT 'PROPOSED',
    source_artifact_id uuid NULL,
    content_hash char(64) NOT NULL,
    supersedes_idea_id uuid NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_ideas PRIMARY KEY (idea_id),
    CONSTRAINT fk_ideas_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_ideas_supersedes FOREIGN KEY (supersedes_idea_id) REFERENCES ideas (idea_id) ON DELETE RESTRICT,
    CONSTRAINT uq_ideas_version UNIQUE (experiment_id, idea_version),
    CONSTRAINT uq_ideas_hash UNIQUE (experiment_id, content_hash),
    CONSTRAINT ck_ideas_version CHECK (idea_version > 0),
    CONSTRAINT ck_ideas_status CHECK (status IN ('PROPOSED','SELECTED','REJECTED','SUPERSEDED')),
    CONSTRAINT ck_ideas_hash CHECK (content_hash ~ '^[0-9a-f]{64}$')
);
CREATE UNIQUE INDEX uq_ideas_one_selected ON ideas (experiment_id) WHERE status = 'SELECTED';
CREATE INDEX ix_ideas_experiment_status ON ideas (experiment_id, status);

CREATE TABLE offer_hypotheses (
    offer_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    idea_id uuid NOT NULL,
    offer_version integer NOT NULL,
    name text NOT NULL,
    promise text NOT NULL,
    deliverables_schema_version integer NOT NULL,
    deliverables jsonb NOT NULL,
    price_minor bigint NOT NULL,
    currency char(3) NOT NULL,
    assumptions_schema_version integer NOT NULL,
    assumptions jsonb NOT NULL,
    risk_reversals_schema_version integer NOT NULL,
    risk_reversals jsonb NOT NULL,
    status text NOT NULL DEFAULT 'PROPOSED',
    source_artifact_id uuid NOT NULL,
    content_hash char(64) NOT NULL,
    supersedes_offer_id uuid NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_offer_hypotheses PRIMARY KEY (offer_id),
    CONSTRAINT fk_offer_hypotheses_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_offer_hypotheses_idea FOREIGN KEY (idea_id) REFERENCES ideas (idea_id) ON DELETE RESTRICT,
    CONSTRAINT fk_offer_hypotheses_supersedes FOREIGN KEY (supersedes_offer_id) REFERENCES offer_hypotheses (offer_id) ON DELETE RESTRICT,
    CONSTRAINT uq_offer_hypotheses_version UNIQUE (experiment_id, offer_version),
    CONSTRAINT uq_offer_hypotheses_hash UNIQUE (experiment_id, content_hash),
    CONSTRAINT ck_offer_hypotheses_versions CHECK (offer_version > 0 AND deliverables_schema_version > 0 AND assumptions_schema_version > 0 AND risk_reversals_schema_version > 0),
    CONSTRAINT ck_offer_hypotheses_json CHECK (jsonb_typeof(deliverables) = 'array' AND jsonb_typeof(assumptions) = 'array' AND jsonb_typeof(risk_reversals) = 'array'),
    CONSTRAINT ck_offer_hypotheses_price CHECK (price_minor > 0 AND currency ~ '^[A-Z]{3}$'),
    CONSTRAINT ck_offer_hypotheses_status CHECK (status IN ('PROPOSED','VALIDATED','ACCEPTED','REJECTED','SUPERSEDED')),
    CONSTRAINT ck_offer_hypotheses_hash CHECK (content_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_offer_hypotheses_experiment_status ON offer_hypotheses (experiment_id, status);
CREATE INDEX ix_offer_hypotheses_idea ON offer_hypotheses (idea_id);

CREATE TABLE metric_definitions (
    metric_definition_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    metric_name text NOT NULL,
    definition_version integer NOT NULL,
    unit text NOT NULL,
    direction text NOT NULL,
    success_threshold numeric NOT NULL,
    kill_threshold numeric NULL,
    target_min numeric NULL,
    target_max numeric NULL,
    sample_floor integer NOT NULL,
    window_start timestamptz NOT NULL,
    window_end timestamptz NOT NULL,
    query_version text NOT NULL,
    rule_schema_version integer NOT NULL,
    rule_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_metric_definitions PRIMARY KEY (metric_definition_id),
    CONSTRAINT fk_metric_definitions_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT uq_metric_definitions_version UNIQUE (experiment_id, metric_name, definition_version),
    CONSTRAINT ck_metric_definitions_version CHECK (definition_version > 0 AND rule_schema_version > 0),
    CONSTRAINT ck_metric_definitions_direction CHECK (direction IN ('HIGHER_IS_BETTER','LOWER_IS_BETTER','TARGET_RANGE')),
    CONSTRAINT ck_metric_definitions_target CHECK ((direction <> 'TARGET_RANGE' AND target_min IS NULL AND target_max IS NULL) OR (direction = 'TARGET_RANGE' AND target_min IS NOT NULL AND target_max IS NOT NULL AND target_min <= target_max)),
    CONSTRAINT ck_metric_definitions_sample CHECK (sample_floor >= 0),
    CONSTRAINT ck_metric_definitions_window CHECK (window_start < window_end),
    CONSTRAINT ck_metric_definitions_rule CHECK (jsonb_typeof(rule_json) = 'object')
);
CREATE INDEX ix_metric_definitions_experiment_name ON metric_definitions (experiment_id, metric_name, definition_version DESC);

CREATE TABLE metric_observations (
    metric_observation_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    metric_definition_id uuid NOT NULL,
    metric_name text NOT NULL,
    definition_version integer NOT NULL,
    window_start timestamptz NOT NULL,
    window_end timestamptz NOT NULL,
    observed_value numeric NOT NULL,
    numerator numeric NULL,
    denominator numeric NULL,
    unit text NOT NULL,
    source_event_ids uuid[] NOT NULL,
    computed_at timestamptz NOT NULL,
    query_version text NOT NULL,
    original_currency char(3) NULL,
    original_amount numeric NULL,
    fx_rate_to_ils numeric NULL,
    fx_rate_source text NULL,
    fx_rate_date date NULL,
    amount_ils numeric NULL,
    correlation_id uuid NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_metric_observations PRIMARY KEY (metric_observation_id),
    CONSTRAINT fk_metric_observations_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_metric_observations_definition FOREIGN KEY (metric_definition_id) REFERENCES metric_definitions (metric_definition_id) ON DELETE RESTRICT,
    CONSTRAINT uq_metric_observations_source UNIQUE (metric_definition_id, query_version, source_event_ids),
    CONSTRAINT ck_metric_observations_window CHECK (window_start < window_end),
    CONSTRAINT ck_metric_observations_ratio CHECK ((numerator IS NULL AND denominator IS NULL) OR (numerator IS NOT NULL AND denominator > 0)),
    CONSTRAINT ck_metric_observations_sources CHECK (cardinality(source_event_ids) > 0),
    CONSTRAINT ck_metric_observations_currency CHECK ((original_currency IS NULL AND original_amount IS NULL AND fx_rate_to_ils IS NULL AND fx_rate_source IS NULL AND fx_rate_date IS NULL AND amount_ils IS NULL) OR (original_currency ~ '^[A-Z]{3}$' AND original_amount IS NOT NULL AND fx_rate_to_ils > 0 AND fx_rate_source IS NOT NULL AND fx_rate_date IS NOT NULL AND amount_ils IS NOT NULL))
);
CREATE INDEX ix_metric_observations_experiment_computed ON metric_observations (experiment_id, computed_at DESC);
CREATE INDEX ix_metric_observations_correlation ON metric_observations (correlation_id);

CREATE TABLE metric_snapshots (
    metric_snapshot_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    snapshot_version integer NOT NULL,
    definition_set_hash char(64) NOT NULL,
    observation_cutoff_at timestamptz NOT NULL,
    values_schema_version integer NOT NULL,
    values_json jsonb NOT NULL,
    values_hash char(64) NOT NULL,
    computed_by_rule_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_metric_snapshots PRIMARY KEY (metric_snapshot_id),
    CONSTRAINT fk_metric_snapshots_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT uq_metric_snapshots_version UNIQUE (experiment_id, snapshot_version),
    CONSTRAINT uq_metric_snapshots_inputs UNIQUE (experiment_id, definition_set_hash, observation_cutoff_at),
    CONSTRAINT ck_metric_snapshots_version CHECK (snapshot_version > 0 AND values_schema_version > 0),
    CONSTRAINT ck_metric_snapshots_json CHECK (jsonb_typeof(values_json) = 'object'),
    CONSTRAINT ck_metric_snapshots_hashes CHECK (definition_set_hash ~ '^[0-9a-f]{64}$' AND values_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_metric_snapshots_experiment_created ON metric_snapshots (experiment_id, created_at DESC);

CREATE TABLE experiment_decisions (
    experiment_decision_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    experiment_version bigint NOT NULL,
    decision_kind text NOT NULL,
    metric_snapshot_id uuid NOT NULL,
    evidence_bundle_artifact_id uuid NOT NULL,
    rule_version text NOT NULL,
    operator_id uuid NOT NULL,
    command_idempotency_key text NOT NULL,
    rationale text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_experiment_decisions PRIMARY KEY (experiment_decision_id),
    CONSTRAINT fk_experiment_decisions_experiment_version FOREIGN KEY (experiment_id, experiment_version) REFERENCES experiments (experiment_id, version) ON DELETE RESTRICT,
    CONSTRAINT fk_experiment_decisions_snapshot FOREIGN KEY (metric_snapshot_id) REFERENCES metric_snapshots (metric_snapshot_id) ON DELETE RESTRICT,
    CONSTRAINT fk_experiment_decisions_operator FOREIGN KEY (operator_id) REFERENCES operators (operator_id) ON DELETE RESTRICT,
    CONSTRAINT uq_experiment_decisions_version UNIQUE (experiment_id, experiment_version),
    CONSTRAINT uq_experiment_decisions_command UNIQUE (operator_id, command_idempotency_key),
    CONSTRAINT ck_experiment_decisions_kind CHECK (decision_kind IN ('SCALE','REVISE','KILL','INCONCLUSIVE')),
    CONSTRAINT ck_experiment_decisions_version CHECK (experiment_version > 0)
);
CREATE INDEX ix_experiment_decisions_snapshot ON experiment_decisions (metric_snapshot_id);
```

Deferred M2 foreign keys `fk_ideas_source_artifact`, `fk_offer_hypotheses_source_artifact`, and `fk_experiment_decisions_evidence_bundle` reference `artifacts(artifact_id)` after DB-04 exists. Metric observations instead reference their exact immutable `source_event_ids` catalog set and do not claim an artifact FK. `fk_experiments_active_brief` maps `experiments(experiment_id,active_brief_version)` to `experiment_briefs(experiment_id,brief_version)` and is `DEFERRABLE INITIALLY DEFERRED`. Exact statements are in DB-06.

| Table | Exclusive write owner | Canonical events | Retention class / retention owner |
| --- | --- | --- | --- |
| `experiment_briefs` | `ExperimentBriefCommandService` | `experiment.created.v1`, `experiment.scope_approved.v1`, `experiment.revision_started.v1` | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `ideas` | `IdeaMaterializationService` | source artifact events plus audited selection | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `offer_hypotheses` | `OfferMaterializationService` | source artifact events | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `metric_definitions` | `MetricDefinitionCommandService` | audit record on version approval | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `metric_observations` | `MetricObservationService` | source domain events referenced in `source_event_ids` | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `metric_snapshots` | `MetricSnapshotService` | referenced by `experiment.decision_recorded.v1` | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `experiment_decisions` | `ExperimentCommandService` | `experiment.decision_recorded.v1`, `experiment.state_changed.v1` | `SAFETY_LONG` / `RetentionCommandService` |

JSON fields have versioned Pydantic schemas and GIN indexes only after query evidence justifies them. They cannot hold identities, state, foreign keys, money, or fields that require independent retention/deletion.

## Ordered implementation tasks

- [ ] **Encode immutable brief and decision models —** Input: M0 artifact/metric contracts. Operation: define complete schemas, hashes, version links, and canonical decision enum. Output: domain values and migration model. Test evidence: `test_brief_requires_every_m0_field` and immutability tests. Failure behavior: reject incomplete record and block scope approval.
- [ ] **Migrate normalized experiment records —** Input: table contract. Operation: create tables, FKs, constraints, partial uniques, immutable triggers, and indexes. Output: empty M2 schema. Test evidence: real-PostgreSQL constraint matrix. Failure behavior: rollback entire revision.
- [ ] **Implement version append repositories —** Input: expected experiment version and new content. Operation: insert a new immutable version and link predecessor; never update content. Output: versioned brief/idea/offer. Test evidence: `test_concurrent_offer_version_append_has_one_winner`. Failure behavior: conflict with no version gap.
- [ ] **Implement deterministic metric snapshot —** Input: frozen definition versions and cutoff. Operation: select eligible observations, compute values, hash inputs, and persist immutable snapshot. Output: reproducible decision input. Test evidence: `test_metric_snapshot_recomputes_byte_equivalent`. Failure behavior: mark insufficient evidence; do not synthesize zero.
- [ ] **Record operator decision atomically —** Input: `EVALUATING` experiment, snapshot, evidence bundle, rule version, idempotency key. Operation: validate, insert immutable decision, transition to `DECIDED`, and append event/audit/outbox. Output: authoritative decision. Test evidence: command replay and two-writer race. Failure behavior: typed denial; no partial decision.

## Test strategy

- **Unit `test_authority_level_does_not_enable_outreach`:** stored brief authority is input, never the global gate.
- **Migration `test_immutable_tables_reject_update_and_delete`:** only retention procedure may redact/delete eligible evidence.
- **Property `test_content_hash_is_canonical`:** key order/timezone formatting cannot create false versions.
- **Integration `test_decision_and_experiment_transition_commit_together`:** failure injection leaves neither alone.
- **Contract `test_decision_kind_matches_arch03_and_openapi`:** one canonical enum.
- **Recovery `test_revised_failed_experiment_preserves_rejected_brief`:** revision appends, never rewrites.

## Security, privacy, compliance, idempotency, observability, and cost

Briefs store jurisdiction facts and legal-review references, not claims of compliance. Sensitive research belongs in evidence records with narrower retention. Command and content hashes deduplicate exact replays. Logs expose IDs/hashes, not rationale or customer text. Price and budget retain original currency; ILS reporting is a separate metric/cost projection.

## Failure, rollback, and operator recovery

An invalid metric, missing source, stale artifact, or content-hash conflict blocks the transition. Roll back code, not history. Correct a brief/offer/metric through a new version and supersession link. An erroneous decision is not edited: cancel that experiment version if legally/operationally required, preserve the event chain, and start a revised experiment under an audited operator command.

## Acceptance and retained evidence

- [ ] Every M0 brief field has a typed column or versioned schema location.
- [ ] Agent output can propose an idea/offer but cannot select, accept, decide, or activate outreach.
- [ ] Metric snapshots are reproducible from frozen definitions and observations.
- [ ] `DECIDED` has one immutable operator decision for the experiment version.
- [ ] Versions/supersession preserve negative evidence.

Retain schema snapshots, constraint output, canonical-hash vectors, snapshot recomputation, decision concurrency traces, and event payload fixtures.

## Dependencies and next deliverable

DB-02 depends on DB-01 and M0 product/metric definitions. It unlocks [WF-02](../03-workflows/02-experiment-lifecycle.md), [WF-03](../03-workflows/03-idea-validation-workflow.md), and M4 synthetic execution; it does not unlock outreach.
