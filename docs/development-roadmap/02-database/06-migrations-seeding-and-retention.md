# Migrations, Deterministic Seeds, Retention, Backup, and Restore

**Document ID:** DB-06
**Status:** Planned M2 schema-lifecycle gate
**Milestone:** M2, M3, M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `DB-06-T01 -> DB-06-T02 -> DB-06-T03 -> DB-06-T04 -> DB-06-T05`; cross-document task Inputs `DB-06-T01 <- DB-01-T02,DB-02-T02,DB-03-T04,DB-04-T02,DB-05-T02; DB-06-T05 <- SEC-06-T02`. Descriptive source authorities/resources (not whole-document completion dependencies): [DB-01](01-core-data-model.md) through [DB-05](05-audit-events-and-idempotency.md)
**Outputs:** Ordered Alembic chain, empty/product seed policy, retention classes, purge/redaction workflow, backup compatibility, and fresh restore evidence
**Unlocks:** M2 exit and safe M3-M9 schema evolution
**Risk:** Critical
**Complexity:** L


## Outcome and current repository state

Only the empty Alembic base exists. This plan creates the DB-01..05 product records in ordered M2 revisions with deterministic catalog names, exact composite references, explicit retention and tested restore. M1 m1_spike tables remain disposable and never migrate into product data. The manifest is the table-name set below, not a historical fixed count.

## Migration sequence and exact foreign-key contract

The revision order is core -> experiment/offer -> identity/cohorts/conversation/booking -> artifacts/evidence/checkpoint/strategy -> audit/policy/cost -> deferred cross-domain constraints -> fail-closed seeds. Tables may be created before dependencies, but no migration head is accepted until every typed reference is installed and introspected. SQL tables and DB-02..05 normative record tables are equally binding; record shorthand must expand to physical typed columns before implementation. A JSON value or application-only lookup cannot replace an FK.

All FK deletes default RESTRICT; no cascade may erase audit, suppression, unresolved effects or historical attribution. Common immutable authority tuples use named unique constraints. Where the discriminator can reference more than one typed table, a deferred constraint trigger selects an exact allowlisted target and checks all scope/version/hash fields; unknown discriminators fail. Never publish a mutable current state/version as a historical parent key.

| Named constraint family | Exact child -> immutable parent requirement |
| --- | --- |
| fk_experiments_active_brief | (experiment_id,active_brief_version) -> experiment_briefs(experiment_id,brief_version), DEFERRABLE INITIALLY DEFERRED |
| fk_offer_packages_idea; fk_offer_packages_research; fk_offer_packages_artifact | same-experiment ideas(id,version,hash), accepted MarketResearchReport and accepted OfferPackage respectively; accepted receipts bind exact artifact ID/type/version/hash |
| fk_offer_economics_package; fk_offer_variants_package; fk_offer_discount_bands_package | exact (offer_id,experiment_id,offer_version,offer_content_hash) and normalized permitted variant/band references |
| fk_contact_identities_person; fk_leads_business; fk_lead_assessments_identity | immutable business_identity_results(identity_result_id,business_id,result_hash) and accepted business/person identity and source evidence; QualificationService cannot alter identity; known person belongs to same business |
| fk_lead_assessments_artifact; fk_campaign_members_qualification | accepted QualificationDecision with PRELIMINARY/FINAL phase guard; cohort member requires FINAL against identical offer/filter and lead |
| fk_campaigns_supersedes | prior campaign_version_id resolves same campaign/experiment and campaign_version - 1; no self, skip or cross-program predecessor |
| fk_cohorts_campaign; fk_cohorts_prior_decision; fk_campaign_members_cohort | exact CohortRef plus prior same-campaign immediately preceding CONTINUE; matching immutable membership hash/ordinal/snapshot; no duplicate recipient across experiment |
| fk_campaign_members_recipient_identity/jurisdiction/consent/exception/legal/disclosure/google | each exact accepted protected evidence tuple with recipient/business scope, schema/version/hash and required expiry; exactly one consent/exception arm |
| fk_artifacts_input_snapshot; fk_agent_runs_workflow; fk_agent_runs_input_snapshot; fk_snapshot_input_dependencies_source | normalized accepted predecessor/product references and distinct application/agent snapshot references; workflow FK only (workflow_run_id,experiment_id), distinct per-agent snapshot ID/hash FK; never workflow input hash equality |
| fk_artifact_evidence_links_artifact/evidence; fk_artifact_acceptances_validation | exact artifact and evidence immutable version/hash tuples; acceptance requires exact passed validation/producer authority; later disposition appends receipt |
| fk_action_authorizations_creation_policy; fk_action_authorizations_offer/activation/member | creation policy's action_basis_hash/action/content/facts/rules; final ActionAuthorityScopeV1 hash is computed after attaching the decision and complete accepted MemberRef/OfferRef/strategy activation/generations; no preview/manual-approval dependency |
| fk_action_consumption_target | one authorization consumed exactly once by matching send_intent OR booking_action of correct action_kind, with same full scope_hash and action tuple |
| fk_send_intents_authority; fk_send_attempts_intent_authority | authorization ID/scope_hash, complete MemberRef, message/version/content/materialization, mailbox/RFC/idempotency and governing attribution; immutable target keys exclude mutable cancellation/state |
| fk_send_attempts_send_policy_authority | exact policy_decision_id, scope SEND, action_id/kind, cohort/member, scope_hash, fresh facts_hash, policy_version, allowed=true and attribution |
| fk_send_attempts_rate_reservation | reservation_id,send_intent_id,mailbox_id,rate_policy_version,window_start,slot_number,concurrency_lease_token,consumed_at; consumed_at non-null immutable; RESERVED row cannot back attempt |
| fk_provider_results_attempt_identity; fk_replies_observation_identity; fk_gmail_history_cursors_observation_identity | same attempt/mailbox/RFC; same observation/mailbox/Gmail message/thread; same observation/mailbox/message/history respectively |
| fk_booking_confirmations_slot/lead; fk_booking_actions_authority; fk_booking_attempts_action/policy | exact confirmed slot/hash/timezone and lead span; exact action kind/version/calendar/event/attendees/notifications; fresh BOOKING policy and current authority/generation; no CREATE/RESCHEDULE without confirmation |
| fk_booking_results_attempt; fk_calendar_observations_account | same booking attempt/action/calendar/provider_call_id; same authorized calendar; callback change identity unique |
| fk_checkpoint_cohort; fk_checkpoint_bundle; fk_experiment_decisions_checkpoint/snapshot/bundle | same campaign/cohort/generation/cutoff and accepted CheckpointEvidenceBundle; one authoritative versioned decision, snapshots never mix cohorts |
| fk_learning_run_checkpoint; fk_learning_results_run; fk_strategy_versions_evaluation; fk_strategy_activations_boundary | closed checkpoint, exact evidence partitions/all-agent registry; approved comparison/holdout/guardrail evidence; target campaign's eligible boundary plus compatible approved strategy |
| fk_strategy_agent_versions_package/configuration; fk_strategy_rollbacks_activation | exact package and immutable configuration manifest, prior/target compatible approved strategy and closed checkpoint; historical attribution untouched |
| fk_action_attributions_target/strategy/activation | exact typed action/version and its recorded offer/cohort/strategy/activation; no campaign-only attribution or cross-cohort splice |
| fk_budget_reservations_cost; fk_cost_entries_agent_run/provider_result/booking_result | cost_id/experiment/currency; agent_id/experiment/workflow; Gmail result/attempt/call/provider; booking result/attempt/call respectively; disjoint provenance branches |
| fk_domain_events_supersedes; fk_outbox_messages_event; fk_outbox_deliveries_event; fk_repair_actions_incident | exact append-only scope/event and closed incident catalog route tuple; no cross-scope repair or duplicate consumer/event receipt |

For physical names, scalar PK/FK/UQ names follow pk_<table>, fk_<table>_<parent_role>, uq_<table>_<key_role>; logical tuple ordering is specified above and DB-02..05. The implemented migration publishes machine-readable columns/types/nullability/default/check/index/trigger/FK target tuples. Introspection compares set/value equality to all source record fields, not only table totals.

## Required triggers and transactional guards

Install trg_<table>_immutable_identity for every immutable version/artifact/scope/IO/attribution/evidence/ledger tuple. Content redaction is possible only through RetentionCommandService's separately granted routine and records tombstones; ordinary application roles cannot UPDATE/DELETE bytes. Lifecycle columns have explicit one-way owner transitions.

trg_action_authorization_consumption_once rejects two intents/actions for one authority and any mismatching scope. trg_send_intent_cancellation_once permits only true-to-false closure with timestamp/reason and proof of no started attempt; attempt insertion locks the same intent and rejects cancelled state. Do not encode open_for_attempt as a mutable FK parent token that would prevent preserving old attempts.

trg_cohort_frozen_configuration forbids offer, strategy, activation, filters, causal variables, membership and evidence-definition changes after opening; counters/state remain owner-controlled. trg_checkpoint_decision_once and unique checkpoint-owned outbox key prevent double decision/learning trigger. trg_strategy_activation_boundary checks campaign checkpoint closure and control generation under CAS; no mid-cohort activation. trg_authority_current_generation guards every new effect intent/attempt.

Gmail lease uniqueness, consumed evidence, ambiguity quarantine and positive-evidence reconciliation remain DB-03/BACKEND-04 authority. Calendar writes use calendar-side-effects plus a single unresolved action lease per calendar and provider conditional version/ETag; clock expiry is never conclusive absence.

## Deterministic seeds

Seed only explicit operator bootstrap, all effect controls false (PRODUCT_OUTREACH, TEST_INBOX_SENDING, CALENDAR_WRITES, TEST_CALENDAR_WRITES), denied/default scoped controls, exact four-stage program, synthetic fixture IDs and strict policy/schema registries. Seed a validated evaluation baseline but no real accepted offer, prospect identity, consent, credential, active calendar/mailbox, fabricated commitment/booking or live strategy activation. The approved baseline package is materialized from retained configuration evidence; EXPERIMENT_BASELINE activation precedes research, and COHORT baseline activation is materialized by deterministic cohort admission. Neither is fabricated learning evidence or an in-cohort activation.

Same seed version/hash replays; different bytes conflict. No seed reads external providers or imports disposable M1 data. Test resources and real demand evidence are labelled independently.

## Complete product-table retention manifest

Each listed table has one exclusive normal writer in DB-01..05 and one purge/redaction owner below. Payload retention can be shorter than its row class. security_runtime.oidc_flows/operator_sessions, engine histories and external credential objects are separately inventoried operational data, never product-table aliases. Any new/removed record requires atomic schema/FK/retention/access changes.

| Product table | Retention class | Purge/redaction owner |
| --- | --- | --- |
| operators | BUSINESS_ACTIVE | RetentionCommandService |
| experiments | BUSINESS_ACTIVE | RetentionCommandService |
| budget_accounts | BUSINESS_ACTIVE | RetentionCommandService |
| experiment_briefs | BUSINESS_ACTIVE | RetentionCommandService |
| ideas | BUSINESS_ACTIVE | RetentionCommandService |
| offer_packages | BUSINESS_ACTIVE | RetentionCommandService |
| offer_economics | BUSINESS_ACTIVE | RetentionCommandService |
| offer_variants | BUSINESS_ACTIVE | RetentionCommandService |
| offer_discount_bands | BUSINESS_ACTIVE | RetentionCommandService |
| metric_definitions | BUSINESS_ACTIVE | RetentionCommandService |
| metric_observations | BUSINESS_ACTIVE | RetentionCommandService |
| metric_snapshots | BUSINESS_ACTIVE | RetentionCommandService |
| businesses | BUSINESS_ACTIVE | RetentionCommandService |
| leads | BUSINESS_ACTIVE | RetentionCommandService |
| lead_discovery_candidates | BUSINESS_ACTIVE | RetentionCommandService |
| lead_assessments | BUSINESS_ACTIVE | RetentionCommandService |
| campaigns | BUSINESS_ACTIVE | RetentionCommandService |
| campaign_cohorts | BUSINESS_ACTIVE | RetentionCommandService |
| workflow_runs | SAFETY_LONG | RetentionCommandService |
| system_controls | SAFETY_LONG | RetentionCommandService |
| action_controls | SAFETY_LONG | RetentionCommandService |
| budget_reservations | SAFETY_LONG | RetentionCommandService |
| incidents | SAFETY_LONG | RetentionCommandService |
| experiment_decisions | SAFETY_LONG | RetentionCommandService |
| gmail_mailboxes | SAFETY_LONG | RetentionCommandService |
| action_authorizations | SAFETY_LONG | RetentionCommandService |
| action_authorization_consumptions | SAFETY_LONG | RetentionCommandService |
| suppression_entries | SAFETY_LONG | RetentionCommandService |
| send_intents | SAFETY_LONG | RetentionCommandService |
| send_rate_reservations | SAFETY_LONG | RetentionCommandService |
| send_attempts | SAFETY_LONG | RetentionCommandService |
| provider_results | SAFETY_LONG | RetentionCommandService |
| gmail_history_cursors | SAFETY_LONG | RetentionCommandService |
| negotiation_decisions | SAFETY_LONG | RetentionCommandService |
| calendar_accounts | SAFETY_LONG | RetentionCommandService |
| booking_intents | SAFETY_LONG | RetentionCommandService |
| booking_actions | SAFETY_LONG | RetentionCommandService |
| booking_attempts | SAFETY_LONG | RetentionCommandService |
| booking_provider_results | SAFETY_LONG | RetentionCommandService |
| checkpoints | SAFETY_LONG | RetentionCommandService |
| checkpoint_evidence_members | SAFETY_LONG | RetentionCommandService |
| global_learning_runs | SAFETY_LONG | RetentionCommandService |
| agent_learning_results | SAFETY_LONG | RetentionCommandService |
| global_strategy_versions | SAFETY_LONG | RetentionCommandService |
| strategy_agent_versions | SAFETY_LONG | RetentionCommandService |
| strategy_activations | SAFETY_LONG | RetentionCommandService |
| strategy_rollbacks | SAFETY_LONG | RetentionCommandService |
| artifact_validations | SAFETY_LONG | RetentionCommandService |
| artifact_acceptances | SAFETY_LONG | RetentionCommandService |
| domain_events | SAFETY_LONG | RetentionCommandService |
| audit_events | SAFETY_LONG | RetentionCommandService |
| command_idempotency | SAFETY_LONG | RetentionCommandService |
| outbox_messages | SAFETY_LONG | RetentionCommandService |
| outbox_deliveries | SAFETY_LONG | RetentionCommandService |
| policy_decisions | SAFETY_LONG | RetentionCommandService |
| cost_entries | SAFETY_LONG | RetentionCommandService |
| repair_actions | SAFETY_LONG | RetentionCommandService |
| action_attributions | SAFETY_LONG | RetentionCommandService |
| exception_cases | SAFETY_LONG | RetentionCommandService |
| business_identity_results | BUSINESS_ACTIVE | RetentionCommandService |
| people | SENSITIVE_SHORT | RetentionCommandService |
| contact_identities | SENSITIVE_SHORT | RetentionCommandService |
| lead_sources | SENSITIVE_SHORT | RetentionCommandService |
| campaign_members | SENSITIVE_SHORT | RetentionCommandService |
| outreach_messages | SENSITIVE_SHORT | RetentionCommandService |
| provider_observations | SENSITIVE_SHORT | RetentionCommandService |
| conversations | SENSITIVE_SHORT | RetentionCommandService |
| conversation_messages | SENSITIVE_SHORT | RetentionCommandService |
| replies | SENSITIVE_SHORT | RetentionCommandService |
| budget_assertions | SENSITIVE_SHORT | RetentionCommandService |
| negotiation_proposals | SENSITIVE_SHORT | RetentionCommandService |
| booking_slot_sets | SENSITIVE_SHORT | RetentionCommandService |
| booking_slots | SENSITIVE_SHORT | RetentionCommandService |
| booking_confirmations | SENSITIVE_SHORT | RetentionCommandService |
| calendar_observations | SENSITIVE_SHORT | RetentionCommandService |
| evidence_items | SENSITIVE_SHORT | RetentionCommandService |
| agent_io_snapshots | SENSITIVE_SHORT | RetentionCommandService |
| artifact_input_snapshots | SENSITIVE_SHORT | RetentionCommandService |
| snapshot_input_dependencies | BUSINESS_ACTIVE | RetentionCommandService |
| agent_runs | EVALUATION_VERSIONED | RetentionCommandService |
| evaluation_cases | EVALUATION_VERSIONED | RetentionCommandService |
| evaluation_results | EVALUATION_VERSIONED | RetentionCommandService |
| artifacts | BUSINESS_ACTIVE | RetentionCommandService |
| artifact_evidence_links | BUSINESS_ACTIVE | RetentionCommandService |

## Field access, purpose, deletion and backup contract

RetentionPolicyV1 in [SEC-06](../08-security-and-compliance/06-data-privacy-and-retention.md#exact-retention-policy-overlay) is the exact duration/key/backup authority. BUSINESS_ACTIVE, SAFETY_LONG, SENSITIVE_SHORT and EVALUATION_VERSIONED inherit its clocks and holds without alternate periods. Immutable content does not mean indefinite payload retention.

DataInventoryV1 is the mechanically compiled field projection of [data.inventory.rules.v1](../08-security-and-compliance/data-inventory-rules.v1.json), not a future classification exercise. That checked-in rule schema has an exact entry for every table in the manifest, both security_runtime tables and external object classes; every entry names its exact create/update writer, internal/query readers, purpose, retention class and scope clock. Each physical column and recursively declared JSON/array/composite leaf receives the first matching ordered field profile, merged with its exact table policy and all shared field axes. The terminal restricted-content rule makes the mapping total; it never grants a new reader or model capability. Unknown tables, source-schema hash drift, unexpanded nested schemas or unregistered transmitted objects block collection/release.

The resolution order and [read-only contract checker](../08-security-and-compliance/verify-data-inventory-contract.py) are binding. Resolve exact table -> first field rule -> profile -> exact owner/readers -> shortest applicable payload/table retention -> named transform intersection. Raw model and telemetry access default deny. A matching transform selector grants only its projected output to its explicitly listed consumers; no selector means no model access. Query access is the intersection of the exact table query principal, field profile and already declared BACKEND-02/06 DTO field; no DTO match means deny. Free text never becomes a safe enum by naming convention: STATE_TIME is valid only for schema-bounded enum/bool/numeric/time types, otherwise restricted-content applies. Containers are resolved leaf-by-leaf; whole-blob grants are forbidden.

Every resolved field row contains table/path/type, rules/source-schema hashes, purpose and immutable source scope/terms evidence reference, sensitivity, encryption/key purpose, redaction, exact normal/retention writers and readers, query/model/telemetry decisions, retention trigger/maximum and duration authority, deletion dependency/order, hold authority/review/expiry, backup expiry and restore behavior. A missing source-scope/terms reference denies provider-derived content use. Safe metadata cannot extend its sensitive payload's lifetime. Clock calculation takes the latest terminal/reconciled timestamp of every transitive reference; an active/unresolved reference is NOT_ELIGIBLE, never an invented close date. Content/lookup/secret fields use the shortest applicable payload class; UTC calendar-month addition clamps to month-end. Payload copies are erased before tombstones, then FK leaves; strongly connected reference-only components wait until all dependents expire. Holds are field-specific signed records, never a model judgment, and cannot extend secret/session/token/backup maxima.

All fields inherit encrypted storage/WAL and exact OPERATIONAL_BACKUP_CHAINS: 14 daily plus 4 weekly chains with absolute 35-day recoverability and no hold extension. Restore replays tombstones, revokes sessions and forces every effect control false before any reader/worker. Only duration approval/shortening remains for counsel; changing purpose, class, reader, encryption, transform or deletion rule requires an explicit versioned contract change and new coverage proof, not ad-hoc implementation judgment.

## Hold, purge, migration and restore protocol

Hold precedence is legal/regulator, incident/security, unresolved external action, active suppression/opt-out, rights dispute, decision/gate, dependency, then expiry. A hold has target/authority/review/expiry evidence, applies only to required fields and cannot extend non-extendable backup/session/token maxima. Deferred purge requires review within 24 hours and safe resolution/escalation within 72; missed clocks disable affected processing.

Compute the purge plan from introspected exact FKs. Close admission; lock target generation/holds; redact sensitive provider/body/IO/object payloads and append tombstones; retain minimum immutable authority/suppression refs; delete only dependency leaves after safe projection verification. Crash/replay is idempotent. Never delete unresolved Gmail/calendar attempts, active suppression lookup/ref or their minimum proof. Source removal cannot regenerate authority.

Every later migration supplies schema diff, old/new reader compatibility, active-run/attempt/activation inventory, drain/version plan, rollback limits, and tested encrypted restore. Do not stamp migration head manually. Destructive downgrade is blocked while retained authority references exist; rollback application code or use a forward repair.

Restore before readiness: verify backup/witness/key availability; restore isolated with network off; apply all authoritative tombstones, revoke sessions/flows, force all controls false, validate exact table/FK/trigger/owner/catalog sets and provider identities; reconcile uncertain Gmail/calendar effects through read ports; verify cohort/strategy/attribution generations without activating anything. No deleted payload, stale activation or prior authorized action may become live merely because it existed in backup.

## Ordered implementation tasks

<!-- roadmap-task id=DB-06-T01 milestone=M2 depends_on=DB-01-T02,DB-02-T02,DB-03-T04,DB-04-T02,DB-05-T02 mode=serial locks=database-schema,migration-head -->
- [ ] **Author the M2 revision chain —** Input: DB-01 through DB-05 exact tables/constraints. Operation: build ordered transactional revisions with deterministic constraint names and deferred FK stage. Output: fresh schema. Test evidence: upgrade from base and downgrade where declared safe; compile every pg_catalog column and nested typed-schema leaf through data.inventory.rules.v1, assert exact table/field set equality and all privacy axes, reject unknown table/source hash drift/unexpanded JSON and any broadened reader/model grant. Failure behavior: rollback current revision; do not stamp head manually.
<!-- roadmap-task id=DB-06-T02 milestone=M2 depends_on=DB-06-T01 mode=parallel locks=database-schema -->
- [ ] **Implement deterministic seeding —** Input: seed manifest/environment. Operation: upsert by stable keys with content hashes and prohibit secrets/real recipients/provider identities. Output: repeatable local/test foundation plus outreach-off production control. Test evidence: two-run no-diff and secret/PII scan. Failure behavior: abort seed transaction.
<!-- roadmap-task id=DB-06-T03 milestone=M2 depends_on=DB-06-T02 mode=serial locks=database-schema,backup-restore,milestone-gate -->
- [ ] **Prove backup and fresh restore —** Input: representative M2 database and an operator-attested external encrypted backup procedure identifying the pinned backup/restore commands and versions, isolated target identity, encryption/key-custody references, artifact/checksum manifest, and successful procedure preflight; absent attestation blocks execution; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: restore to a clean PostgreSQL instance, migrate if required, verify counts/hashes/constraints, force outreach off, then run read/reconciliation checks; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed restore report. Test evidence: automated `test_m2_backup_restores_to_fresh_postgres`. Failure behavior: M2/M8 blocked; no worker start.
<!-- roadmap-task id=DB-06-T04 milestone=M3 depends_on=DB-06-T03 mode=serial locks=database-schema,migration-head,ci-release,milestone-gate -->
- [ ] **Implement the later-migration evidence gate —** Input: the current repository migration registry and the closed compatibility/active-run/ambiguity/rollback/restore evidence schema; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: install a validator/CI rule requiring every later migration to declare and verify those artifacts before release; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: CI-enforced future-migration contract. Test evidence: missing, stale, mixed-version, schema-diff, and rollback-negative fixtures. Failure behavior: hold release and keep the prior version.
<!-- roadmap-task id=DB-06-T05 milestone=M8 depends_on=DB-06-T04,SEC-06-T02 mode=serial locks=database-schema,backend-domain,security-runtime,compliance-policy -->
- [ ] **Implement the database retention engine and recovery graph —** Input: SEC-06 authoritative `retention.policy.v1`, mechanically resolved DataInventoryV1 field rules, exact table/field set equality, cutoffs, holds, and the current database dependency graph. Operation: dry-run bounded counts/IDs; require operator confirmation; redact/delete bounded batches; append audit/outbox evidence; retain the independent suppression target ref when permitted member/source rows are removed; publish the versioned recovery/retention dependency graph and live-record holds. A dependency/receipt/policy mismatch enters exact `DEFERRED_REVIEW`, assigns owner review within 24 hours and resolution-or-escalation within 72 hours, retains data without partial mutation, and closes affected controls on missed SLA. Output: versioned database retention/recovery graph plus minimized data or explicitly owned deferral. Test evidence: fixture matrix for holds, unresolved ambiguity, 24/72 clocks/escalation, missed-SLA control closure, no-partial-mutation, suppression target-ref/list/replay stability after source purge, foreign-key closure, replay, and restore. Failure behavior: stop the batch; retain the safety record and all data; close affected controls on missed SLA; open an incident on partial external deletion.


## Verification and acceptance

Run `python3 docs/development-roadmap/08-security-and-compliance/verify-data-inventory-contract.py` to prove source-table coverage, total field resolution, exact service ownership, safe transform intersection, source-schema hashes and adversarial privacy denials. This roadmap checker does not claim a migrated schema exists; DB-06-T01 must additionally prove physical catalog/nested-schema equality.

Test fresh PostgreSQL migration and catalog equality for every table/column/type/constraint/index/trigger/owner/FK tuple; no hard-coded obsolete count. Exercise one-field authority splices, cancelled intent race, consumed rate evidence, mailbox/calendar leases, per-agent distinct hashes, global strategy scope, exact cohort/checkpoint ownership and all fifteen artifact producers.

Restore an encrypted backup into an empty isolated instance, verify constraints and tombstone propagation, disabled controls/sessions, safe suppression projection after source purge, 35-day expiry and missing-key failure. Crash every purge/restore/deferred-review boundary. Retain schema/introspection manifests, migration/rollback/restore logs, signed fixture hashes, privacy field inventory, purge/tombstone evidence and provider reconciliation traces. Missing/unclassified fields or held dependencies block release and live collection.
