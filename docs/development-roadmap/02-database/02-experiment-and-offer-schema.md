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

| Table | Required columns and keys | Required constraints/indexes | Transition/event relationship |
| --- | --- | --- | --- |
| `experiment_briefs` | `experiment_brief_id uuid PK`, `experiment_id FK`, `brief_version int`, customer/problem/offer/evidence-channel text, `jurisdictions jsonb`, `authority_level text`, cash/time/sample/success/kill fields, `content_hash text`, `created_by_operator_id FK`, `supersedes_brief_id FK self null`, `created_at` | unique `(experiment_id,brief_version)` and `(experiment_id,content_hash)`; `brief_version>0`; positive caps; `authority_level in ('NO_SEND','TEST_INBOX_ONLY','BOUNDED_REAL_RECIPIENTS')`; immutable trigger | `experiment.created.v1`, `experiment.scope_approved.v1`, `experiment.revision_started.v1` |
| `ideas` | `idea_id uuid PK`, `experiment_id FK`, `idea_version int`, `title`, `problem_statement`, `target_customer`, `status text`, `source_artifact_id uuid null`, `content_hash`, `supersedes_idea_id FK self null`, timestamps | unique `(experiment_id,idea_version)`; unique `(experiment_id,content_hash)`; `status in ('PROPOSED','SELECTED','REJECTED','SUPERSEDED')`; one partial-unique `SELECTED` per experiment | selection is audited; artifact events remain on linked artifact |
| `offer_hypotheses` | `offer_id uuid PK`, `experiment_id FK`, `idea_id FK`, `offer_version int`, `name`, `promise`, `deliverables jsonb`, `price_minor`, `currency char(3)`, `assumptions jsonb`, `risk_reversals jsonb`, `status text`, `source_artifact_id uuid`, `content_hash`, `supersedes_offer_id FK self null`, timestamps | unique `(experiment_id,offer_version)`; positive price; `status in ('PROPOSED','VALIDATED','ACCEPTED','REJECTED','SUPERSEDED')`; immutable trigger; indexes `(experiment_id,status)` and `idea_id` | accepted offer artifact enables research completion but does not send |
| `metric_definitions` | `metric_definition_id uuid PK`, `experiment_id FK`, `metric_key text`, `definition_version int`, `unit text`, `direction text`, `success_threshold numeric`, `kill_threshold numeric null`, `sample_floor int`, `window_start/end`, `rule_json jsonb`, timestamps | unique `(experiment_id,metric_key,definition_version)`; `direction in ('HIGHER_IS_BETTER','LOWER_IS_BETTER','TARGET_RANGE')`; nonnegative sample; window ordering; immutable | inputs to deterministic evaluation |
| `metric_observations` | `metric_observation_id uuid PK`, `experiment_id FK`, `metric_definition_id FK`, `observed_value numeric`, `numerator/denominator numeric null`, `source_type text`, `source_ref text`, `observed_at`, `recorded_at`, `correlation_id uuid` | unique `(metric_definition_id,source_type,source_ref)`; denominator positive when present; source check; index `(experiment_id,observed_at)` | append-only evidence, no transition alone |
| `metric_snapshots` | `metric_snapshot_id uuid PK`, `experiment_id FK`, `snapshot_version int`, `definition_set_hash`, `observation_cutoff_at`, `values_json jsonb`, `computed_by_rule_version`, `created_at` | unique `(experiment_id,snapshot_version)` and `(experiment_id,definition_set_hash,observation_cutoff_at)`; immutable | referenced by `experiment.decision_recorded.v1` |
| `experiment_decisions` | `experiment_decision_id uuid PK`, `experiment_id FK`, `decision_kind text`, `metric_snapshot_id FK`, `evidence_bundle_artifact_id uuid`, `rule_version text`, `operator_id FK`, `command_idempotency_key text`, `rationale text`, `created_at` | ARCH-03 decision-kind check; unique `(experiment_id)` for terminal experiment version; unique `(operator_id,command_idempotency_key)`; immutable | commits `experiment.decision_recorded.v1` and `EVALUATING -> DECIDED` |

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
