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

### Safe migration protocol

Additive nullable/backfilled columns and new tables deploy before writers. Backfills are resumable by primary-key range with a migration-run id and invariant counters. Readers tolerate old/new representation during the compatibility window. Constraints become validated only after backfill proof. Destructive contract revisions run after old code drains, backup succeeds, restore is proven, and unresolved workflows are zero or explicitly compatible. Workers stay stopped during a restore until schema, control-off state, event chains, and ambiguity queries pass.

## Ordered implementation tasks

- [ ] **Author the M2 revision chain —** Input: DB-01 through DB-05 exact tables/constraints. Operation: build ordered transactional revisions with deterministic constraint names and deferred FK stage. Output: fresh schema. Test evidence: upgrade from base and downgrade where declared safe. Failure behavior: rollback current revision; do not stamp head manually.
- [ ] **Implement deterministic seeding —** Input: seed manifest/environment. Operation: upsert by stable keys with content hashes and prohibit secrets/real recipients/provider identities. Output: repeatable local/test foundation plus outreach-off production control. Test evidence: two-run no-diff and secret/PII scan. Failure behavior: abort seed transaction.
- [ ] **Implement retention classifier and hold-aware purge —** Input: approved policy version, table class, cutoff, holds. Operation: dry-run counts/IDs, require operator confirmation, redact/delete bounded batches, append audit/outbox evidence. Output: minimized data. Test evidence: fixture matrix for holds, unresolved ambiguity, suppression, FK closure, and replay. Failure behavior: stop batch; retain safety record; open incident on partial external deletion.
- [ ] **Prove backup and fresh restore —** Input: representative M2 database and encrypted backup procedure. Operation: restore to a clean PostgreSQL instance, migrate if required, verify counts/hashes/constraints, force outreach off, then run read/reconciliation checks. Output: signed restore report. Test evidence: automated `test_m2_backup_restores_to_fresh_postgres`. Failure behavior: M2/M8 blocked; no worker start.
- [ ] **Gate every later migration —** Input: compatibility declaration, active run/ambiguity query, rollback/restore plan. Operation: run old/new app compatibility and schema-diff review. Output: release evidence. Test evidence: mixed-version and rollback drill. Failure behavior: hold release and keep prior version.

## Test strategy

- **Migration `test_upgrade_empty_database_to_head`:** exact tables/constraints/indexes.
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
