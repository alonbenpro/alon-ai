# Migrations, Deterministic Seeds, Retention, Backup, and Restore

**Document ID:** DB-06
**Status:** Planned M2 schema-lifecycle gate
**Milestone:** M2, exercised continuously through M8
**Owner:** Solo operator
**Prerequisites:** [DB-01](01-core-data-model.md) through [DB-05](05-audit-events-and-idempotency.md)
**Outputs:** Ordered Alembic chain, empty/product seed policy, retention classes, purge/redaction workflow, backup compatibility, and fresh restore evidence
**Unlocks:** M2 exit and safe M3-M9 schema evolution
**Risk:** Critical
**Complexity:** L

## Outcome and timing

M2 is not complete when migrations merely apply on a developer database. It exits only when a blank PostgreSQL instance upgrades, constraints match the design, deterministic non-sensitive seeds apply, representative data survives backup/restore, rollback limitations are known, and retention operations cannot erase unresolved safety evidence.

## Current repository state

Alembic is configured and container tests assert migration tooling exists, but there is no product revision, seed command, fixture manifest, retention policy, purge job, encrypted backup, restore drill, compatibility test, or product data. M1 spike data, if created later, must be exported as evidence and its schema dropped; it is not a seed.

## Scope and non-goals

In scope: revision order, expand/migrate/contract discipline, deterministic operator/control/test seeds, retention class assignment, legal/incident holds, data minimization, purge/redaction audit, backup/restore compatibility, and evidence manifests. Non-goals: production deployment claims, destructive automatic downgrades, seeding real recipients/secrets/provider IDs, indefinite raw evidence retention, rewriting immutable history, or using migrations to import the M1 harness.

## Exact planned implementation surfaces

Create M2 revisions under `backend/alembic/versions/`, `persistence/seeding.py`, `application/retention.py`, CLI/admin commands, and tests/fixtures. Revision order is: core ownership/control/workflow tables; experiment/offer/metric; artifacts/evidence; lead/campaign/message; event/audit/idempotency/outbox/policy/cost; deferred cross-domain FKs; named indexes/triggers. Each revision declares minimum compatible application version and whether downgrade is data-lossy.

The deferred-FK revision is normative and DDL-equivalent to the following statements (all names are stable migration API):

```sql
ALTER TABLE experiments ADD CONSTRAINT fk_experiments_active_brief FOREIGN KEY (experiment_id, active_brief_version) REFERENCES experiment_briefs (experiment_id, brief_version) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE budget_reservations ADD CONSTRAINT fk_budget_reservations_cost_entry FOREIGN KEY (cost_entry_id) REFERENCES cost_entries (cost_entry_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ideas ADD CONSTRAINT fk_ideas_source_artifact FOREIGN KEY (source_artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT;
ALTER TABLE offer_hypotheses ADD CONSTRAINT fk_offer_hypotheses_source_artifact FOREIGN KEY (source_artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT;
ALTER TABLE experiment_decisions ADD CONSTRAINT fk_experiment_decisions_evidence_bundle FOREIGN KEY (evidence_bundle_artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT;
ALTER TABLE leads ADD CONSTRAINT fk_leads_suppression FOREIGN KEY (suppression_entry_id) REFERENCES suppression_entries (suppression_entry_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE lead_assessments ADD CONSTRAINT fk_lead_assessments_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT;
ALTER TABLE outreach_messages ADD CONSTRAINT fk_outreach_messages_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT;
ALTER TABLE approvals ADD CONSTRAINT fk_approvals_eligibility_policy_authority FOREIGN KEY (eligibility_policy_decision_id, eligibility_policy_scope, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, eligibility_policy_version, scope_hash, eligibility_facts_hash, eligibility_policy_allowed) REFERENCES policy_decisions (policy_decision_id, scope, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, policy_version, scope_hash, facts_hash, allowed) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE send_intents ADD CONSTRAINT fk_send_intents_eligibility_policy_authority FOREIGN KEY (eligibility_policy_decision_id, eligibility_policy_scope, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, eligibility_policy_version, scope_hash, eligibility_facts_hash, eligibility_policy_allowed) REFERENCES policy_decisions (policy_decision_id, scope, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, policy_version, scope_hash, facts_hash, allowed) ON DELETE RESTRICT;
ALTER TABLE send_attempts ADD CONSTRAINT fk_send_attempts_send_policy_authority FOREIGN KEY (send_policy_decision_id, send_policy_scope, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, approval_id, send_policy_version, scope_hash, send_policy_facts_hash, send_policy_allowed) REFERENCES policy_decisions (policy_decision_id, scope, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, approval_id, policy_version, scope_hash, facts_hash, allowed) ON DELETE RESTRICT;
ALTER TABLE replies ADD CONSTRAINT fk_replies_classification_artifact FOREIGN KEY (classification_artifact_id) REFERENCES artifacts (artifact_id) ON DELETE RESTRICT;
```

Immutable identity is enforced in PostgreSQL, not only by application convention. The trigger raises `23514` before any protected value changes; the migration installs it on approvals, intents, rate reservations, and attempts with the exact experiment/campaign/member/lead/message/mailbox/approval/eligibility/final-SEND/rate/RFC fields named in DB-03/05. `send_intents` alone permits `attempt_count` and a one-way cancellation pair; a second trigger forbids clearing/changing cancellation. Equivalent table-specific invocations protect immutable version/evidence rows.

```sql
CREATE FUNCTION reject_immutable_columns() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF to_jsonb(NEW) - TG_ARGV <> to_jsonb(OLD) - TG_ARGV THEN
    RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = TG_TABLE_NAME || ' immutable identity cannot change';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_campaigns_immutable_version BEFORE UPDATE ON campaigns
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns('state','updated_at');
CREATE TRIGGER trg_outreach_messages_immutable_authority BEFORE UPDATE ON outreach_messages
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns('state','version','updated_at');
CREATE TRIGGER trg_approvals_immutable_authority BEFORE UPDATE ON approvals
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns('state','operator_id','reason_code','decided_at');
CREATE TRIGGER trg_campaign_members_immutable_authority BEFORE UPDATE ON campaign_members
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns('status','removed_at');
CREATE TRIGGER trg_send_intents_immutable_identity BEFORE UPDATE ON send_intents
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns('attempt_count','open_for_attempt','cancelled_at','cancellation_reason');
CREATE FUNCTION enforce_send_intent_cancellation_once() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT OLD.open_for_attempt AND (NEW.open_for_attempt, NEW.cancelled_at, NEW.cancellation_reason) IS DISTINCT FROM (OLD.open_for_attempt, OLD.cancelled_at, OLD.cancellation_reason) THEN
    RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'send intent cancellation is immutable';
  END IF;
  IF OLD.open_for_attempt AND NOT NEW.open_for_attempt AND (NEW.cancelled_at IS NULL OR NEW.cancellation_reason IS NULL) THEN
    RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'send intent cancellation reason required';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_send_intent_cancellation_once BEFORE UPDATE ON send_intents
FOR EACH ROW EXECUTE FUNCTION enforce_send_intent_cancellation_once();
CREATE TRIGGER trg_send_rate_reservations_immutable_identity BEFORE UPDATE ON send_rate_reservations
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns('state','consumed_at','released_at','expired_at');
CREATE TRIGGER trg_send_attempts_immutable_identity BEFORE UPDATE ON send_attempts
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns('state','provider_called_at','completed_at','error_code','error_fingerprint','retry_class','reconciliation_strategy_version');
CREATE TRIGGER trg_provider_results_append_only BEFORE UPDATE ON provider_results
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns();
CREATE TRIGGER trg_provider_observations_append_only BEFORE UPDATE ON provider_observations
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns();
CREATE TRIGGER trg_policy_decisions_append_only BEFORE UPDATE ON policy_decisions
FOR EACH ROW EXECUTE FUNCTION reject_immutable_columns();
```

### Seed manifest

| Seed | Environment | Rule |
| --- | --- | --- |
| one operator subject placeholder | local/test only | deterministic UUID, no real email/password; production bootstrap comes from authenticated subject |
| `PRODUCT_OUTREACH=false` and `TEST_INBOX_SENDING=false` | every environment | mandatory separate fail-closed singletons; never seed `true`; test authority never promotes product authority |
| metric/criteria/evaluation fixtures | test | versioned and hashed; synthetic business/message content |
| operator-owned inbox aliases | M1/M6 harness config only | never in product migration or repository fixture |
| suppression/control/provider records | none by default | production values require authenticated commands and audit |

### Retention classes

| Class | Records | Planned default and deletion guard |
| --- | --- | --- |
| `SAFETY_LONG` | domain/audit events, command keys/results hashes, send intent/attempt/result hashes, suppression, incidents/repairs, gate decisions | retain for the approved safety/legal period; never purge unresolved incident/ambiguity/active suppression; redact payload fields separately |
| `BUSINESS_ACTIVE` | experiments, briefs, offers, leads, campaigns, decisions, metric snapshots | retain while experiment is active and for approved post-close period; preserve minimum decision/audit references |
| `SENSITIVE_SHORT` | encrypted recipient/message content, raw provider/evidence captures | shortest operational/legal period; delete payload/capture while retaining non-reversible hash, dates, reason, and safety linkage |
| `EVALUATION_VERSIONED` | evaluation cases/results, schema/prompt/model metadata | retain promoted and comparison versions needed to reproduce gates; expire unused sensitive fixture content |
| `RUNTIME_ENGINE` | DBOS/Temporal engine histories | runtime-specific retention after application terminal/reconciliation evidence is complete; never the sole audit copy |
| `M1_DISPOSABLE` | `m1_spike.spike_runs`, `m1_spike.spike_send_attempts` | export signed evidence, verify export, then drop entire schema; no M2 migration |

Exact durations are approved with the later privacy/legal decision for the chosen jurisdictions; until approved, the system fails closed by disabling automated purge, not by retaining raw sensitive data without review. Every table receives one class in a versioned manifest; missing classification blocks migration acceptance.

### Complete product-table retention manifest

This manifest is exhaustive for the 46 M2 product tables in DB-01 through DB-05, including the last-mile `send_rate_reservations` safety ledger. External OAuth flow/credential objects are not product tables: PROVIDER-01 owns their 10-minute authorization, 24-hour replay/orphan, reference-checked GC, and encrypted-token deletion lifecycle; the mailbox row retains only the exact safe ACTIVE proof tuple. `RetentionCommandService` exclusively owns purge/redaction writes. Every row defaults to held when a legal, incident, unresolved-provider, suppression, or dependency hold applies. "Keep minimum" means retain only non-sensitive identity/hash/state evidence for the approved policy-versioned duration; "redact" is an audited payload replacement before any later FK-safe purge.

| Table | Class | Retention owner | Default hold / purge behavior |
| --- | --- | --- | --- |
| `operators` | `BUSINESS_ACTIVE` | `RetentionCommandService` | deactivate, then purge after reference closure |
| `experiments` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge only after terminal close and FK closure |
| `workflow_runs` | `SAFETY_LONG` | `RetentionCommandService` | hold until terminal/reconciled; keep identity and hashes |
| `system_controls` | `SAFETY_LONG` | `RetentionCommandService` | keep the versioned safety minimum |
| `budget_accounts` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge only after all reservations reconcile |
| `budget_reservations` | `SAFETY_LONG` | `RetentionCommandService` | hold until cost reconciliation; keep safety minimum |
| `incidents` | `SAFETY_LONG` | `RetentionCommandService` | incident hold until resolved; keep safety minimum |
| `experiment_briefs` | `BUSINESS_ACTIVE` | `RetentionCommandService` | hold active version; purge after experiment close |
| `ideas` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge after experiment close and FK closure |
| `offer_hypotheses` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge after experiment close and FK closure |
| `metric_definitions` | `BUSINESS_ACTIVE` | `RetentionCommandService` | preserve decision-referenced versions |
| `metric_observations` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge after snapshot and experiment closure |
| `metric_snapshots` | `BUSINESS_ACTIVE` | `RetentionCommandService` | preserve decision-referenced snapshots |
| `experiment_decisions` | `SAFETY_LONG` | `RetentionCommandService` | keep immutable decision minimum |
| `businesses` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge after dependent lead closure |
| `leads` | `BUSINESS_ACTIVE` | `RetentionCommandService` | suppression/incident hold; redact then purge |
| `lead_assessments` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge after lead/experiment close |
| `gmail_mailboxes` | `SAFETY_LONG` | `RetentionCommandService` | hold while send/reply chains refer; keep safe OAuth flow/account/scope/credential-handle hash/version/key/generation identity, never token/ciphertext |
| `campaigns` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge after all messages are terminal |
| `campaign_members` | `SENSITIVE_SHORT` | `RetentionCommandService` | suppression/incident hold; redact then purge |
| `outreach_messages` | `SENSITIVE_SHORT` | `RetentionCommandService` | ambiguity/incident hold; redact content, retain hash |
| `approvals` | `SAFETY_LONG` | `RetentionCommandService` | keep immutable exact-version authority tuple |
| `suppression_entries` | `SAFETY_LONG` | `RetentionCommandService` | active suppression is an unconditional hold |
| `send_intents` | `SAFETY_LONG` | `RetentionCommandService` | ambiguity/incident hold; keep mailbox/member/eligibility authority chain and cancellation evidence |
| `send_rate_reservations` | `SAFETY_LONG` | `RetentionCommandService` | hold active leases; retain consumed slot identity with attempt/result/recovery evidence |
| `send_attempts` | `SAFETY_LONG` | `RetentionCommandService` | ambiguity/incident hold; keep final SEND decision and consumed rate slot minimum |
| `provider_results` | `SAFETY_LONG` | `RetentionCommandService` | ambiguity/incident hold; keep provider IDs and hashes |
| `provider_observations` | `SENSITIVE_SHORT` | `RetentionCommandService` | ambiguity hold; redact capture, retain fingerprint |
| `replies` | `SENSITIVE_SHORT` | `RetentionCommandService` | legal/incident hold; redact body, retain identity hash |
| `gmail_history_cursors` | `SAFETY_LONG` | `RetentionCommandService` | mailbox/incident hold; retain latest safe cursor |
| `agent_runs` | `EVALUATION_VERSIONED` | `RetentionCommandService` | hold promoted gates; purge unused superseded versions |
| `artifacts` | `BUSINESS_ACTIVE` | `RetentionCommandService` | acceptance/incident hold; purge with provenance closure |
| `evidence_items` | `SENSITIVE_SHORT` | `RetentionCommandService` | gate/incident hold; redact payload, retain content hash |
| `artifact_evidence_links` | `BUSINESS_ACTIVE` | `RetentionCommandService` | purge only with both closed parents |
| `artifact_validations` | `SAFETY_LONG` | `RetentionCommandService` | gate/incident hold; keep safety minimum |
| `artifact_acceptances` | `SAFETY_LONG` | `RetentionCommandService` | gate/incident hold; keep safety minimum |
| `evaluation_cases` | `EVALUATION_VERSIONED` | `RetentionCommandService` | hold promoted/comparison versions; purge unused versions |
| `evaluation_results` | `EVALUATION_VERSIONED` | `RetentionCommandService` | hold promoted/comparison versions; purge unused versions |
| `domain_events` | `SAFETY_LONG` | `RetentionCommandService` | aggregate/incident hold; keep event minimum |
| `audit_events` | `SAFETY_LONG` | `RetentionCommandService` | legal/incident hold; keep audit minimum |
| `command_idempotency` | `SAFETY_LONG` | `RetentionCommandService` | hold active commands; purge after replay horizon |
| `outbox_messages` | `SAFETY_LONG` | `RetentionCommandService` | hold undelivered messages; purge after all receipts |
| `outbox_deliveries` | `SAFETY_LONG` | `RetentionCommandService` | purge only with source event/message |
| `policy_decisions` | `SAFETY_LONG` | `RetentionCommandService` | send/approval hold; keep facts hash and mailbox scope |
| `cost_entries` | `SAFETY_LONG` | `RetentionCommandService` | finance/incident hold; keep cost minimum |
| `repair_actions` | `SAFETY_LONG` | `RetentionCommandService` | incident hold; keep immutable repair chain |

### Safe migration protocol

Additive nullable/backfilled columns and new tables deploy before writers. Backfills are resumable by primary-key range with a migration-run id and invariant counters. Readers tolerate old/new representation during the compatibility window. Constraints become validated only after backfill proof. Destructive contract revisions run after old code drains, backup succeeds, restore is proven, and unresolved workflows are zero or explicitly compatible. Workers stay stopped during a restore until schema, control-off state, event chains, and ambiguity queries pass.

## Ordered implementation tasks

- [ ] **Author the M2 revision chain —** Input: DB-01 through DB-05 exact tables/constraints. Operation: build ordered transactional revisions with deterministic constraint names and deferred FK stage. Output: fresh schema. Test evidence: upgrade from base and downgrade where declared safe. Failure behavior: rollback current revision; do not stamp head manually.
- [ ] **Implement deterministic seeding —** Input: seed manifest/environment. Operation: upsert by stable keys with content hashes and prohibit secrets/real recipients/provider identities. Output: repeatable local/test foundation plus outreach-off production control. Test evidence: two-run no-diff and secret/PII scan. Failure behavior: abort seed transaction.
- [ ] **Implement retention classifier and hold-aware purge —** Input: approved policy version, table class, cutoff, holds. Operation: dry-run counts/IDs, require operator confirmation, redact/delete bounded batches, append audit/outbox evidence. Output: minimized data. Test evidence: fixture matrix for holds, unresolved ambiguity, suppression, FK closure, and replay. Failure behavior: stop batch; retain safety record; open incident on partial external deletion.
- [ ] **Prove backup and fresh restore —** Input: representative M2 database and encrypted backup procedure. Operation: restore to a clean PostgreSQL instance, migrate if required, verify counts/hashes/constraints, force outreach off, then run read/reconciliation checks. Output: signed restore report. Test evidence: automated `test_m2_backup_restores_to_fresh_postgres`. Failure behavior: M2/M8 blocked; no worker start.
- [ ] **Gate every later migration —** Input: compatibility declaration, active run/ambiguity query, rollback/restore plan. Operation: run old/new app compatibility and schema-diff review. Output: release evidence. Test evidence: mixed-version and rollback drill. Failure behavior: hold release and keep prior version.

## Test strategy

- **Migration `test_upgrade_empty_database_to_head`:** exactly 46 tables plus every named constraint/index/trigger.
- **Constraint `test_approval_eligibility_intent_final_send_and_rate_composites_reject_one_column_splices`:** campaign member, decision, approval, hash, mailbox, rate slot, and allowed-flag negatives.
- **Migration `test_upgrade_from_each_supported_revision`:** no skipped compatibility edge.
- **Seed `test_seed_is_idempotent_and_contains_no_secret_or_real_recipient`:** deterministic hash.
- **Retention `test_purge_refuses_unresolved_ambiguous_send_and_active_hold`:** safety first.
- **Restore `test_backup_restore_preserves_event_and_attempt_chain`:** counts plus hashes/foreign keys.
- **Recovery `test_worker_start_requires_restored_control_off_and_schema_head`:** fail closed.

## Security, privacy, compliance, idempotency, observability, and cost

Backups are encrypted, access-limited, off-host at M8, and tested rather than assumed. Seeds and migration logs exclude secrets/PII. Retention/purge commands are authenticated, idempotent, dry-run-first, bounded, and audited. Metrics expose revision, backfill progress, purge class/count, backup age, restore result, and storage growth. Storage/provider cost is measured before increasing retention.

## Failure, rollback, and operator recovery

Never force a migration stamp, drop a column/table, or delete a backup to silence a failure. Stop API writes/workers, keep outreach disabled, preserve logs, restore the last proven backup into a separate database, compare constraints/events/unresolved attempts, and choose forward repair or code rollback. A failed purge retries by command idempotency key and batch cursor. Legal/incident holds override automated deletion; approval to lift a hold is audited.

## Acceptance and retained evidence

- [ ] Blank, prior-supported, backup-restored, and representative databases reach the same schema invariants.
- [ ] Seeds are deterministic, non-sensitive, environment-scoped, and never enable outreach.
- [ ] Every table has a retention class and unresolved safety records cannot be purged.
- [ ] M1 evidence is exported and `m1_spike` is dropped rather than promoted.
- [ ] Restore proof includes constraints, hashes, event/attempt chains, and worker-start fail-closed checks.

Retain revision graph/schema diff, constraint introspection, seed hash/scan, retention dry-run/purge audits, encrypted-backup metadata, fresh-restore report, and mixed-version test output.

## Dependencies and next deliverable

DB-06 closes the six-file M2 database contract. Passing its migration/restore/retention evidence completes the persistence portion of M2 and unlocks M3 agent/provider work plus product workflows [WF-02](../03-workflows/02-experiment-lifecycle.md) onward.
