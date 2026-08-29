# PostgreSQL Backups, PITR, Retention, and Clean Restores

**Document ID:** INFRA-04
**Status:** Planned M8 backup/restore system; current local PostgreSQL volume has no configured archive, off-host backup, PITR, manifest signing, or restore drill
**Milestone:** M2 restore contract; M8 private operations and DR gate
**Owner:** Solo operator
**Prerequisites:** [DB-06 migrations/retention](../02-database/06-migrations-seeding-and-retention.md), SEC-03/06, TEST-02/06, INFRA-02/03, OBS-02/05, and the complete 46-table schema
**Outputs:** Encrypted base backups, continuous WAL archive, immutable signed manifests, bounded retention/tombstone replay, isolated PITR/full restore procedures, measured RPO/RTO, and restore evidence
**Unlocks:** INFRA-05 disaster recovery and M8 acceptance
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

PostgreSQL product and `security_runtime` state can be recovered on a clean host to an exact target time without starting writers/providers, reviving sessions/controls, losing unresolved Gmail authority, or resurrecting purged data into use. Initial objective is database RPO <=5 minutes and complete private-service RTO <=4 hours, proven by drills rather than inferred from backup-job success.

PostgreSQL 18 documents base backups, continuous WAL/PITR and `pg_verifybackup`; the official [backup chapter](https://www.postgresql.org/docs/18/backup.html), [`pg_basebackup`](https://www.postgresql.org/docs/18/app-pgbasebackup.html), and [`pg_verifybackup`](https://www.postgresql.org/docs/18/app-pgverifybackup.html) were accessed 2026-08-29. PostgreSQL explicitly warns that verification cannot replace a real restore, so both are mandatory here.

## Current repository state

`infra/compose.yaml` uses one local named PostgreSQL 18 volume and Alembic migration. DB-06 plans encrypted backups and a fresh restore test, but no backup role, `wal_level/archive_mode/archive_command`, archive spool, object store, KMS envelope, signed backup catalog, retention job, PITR configuration, restore host, tombstone replay, monitoring or drill exists. No current RPO/RTO claim is valid.

## Scope and non-goals

In scope: explicit `PGDATA`, data checksums, dedicated backup role, daily full base backup, WAL archival with maximum five-minute switch, off-host immutable object storage, backup-specific KMS generation, signed manifest/catalog, verification, retention, restore to latest/time/LSN, 46-table/invariant/event/send-chain checks, sessions/flows/control safety, deletion tombstones, drills, corruption/key-loss cases. Non-goals: copying a live volume, same-host-only backup, unencrypted dump, assuming provider snapshots are application-consistent, restoring into live writers, using restore as normal rollback, or deleting old backup/WAL before dependency proof.

## Exact planned implementation surfaces

Create `infra/postgres/postgresql.conf`, `pg_hba.conf`, `backup-role.sql`, `scripts/backup/{archive_wal,base_backup,verify,prune}.sh`, `scripts/restore/{preflight,restore,verify}.sh`, `backup-manifest.schema.json`, and a Google Cloud Storage lifecycle/retention policy for an EU multi-region bucket in a separate backup project. Set explicit `PGDATA` in production Compose so backup/restore never guesses image-version paths. Use PostgreSQL 18 matching client binaries; `wal_level=replica`, `archive_mode=on`, `archive_timeout=300s`, and an `archive_command` wrapper that returns success only after the exact WAL filename is envelope-encrypted under the backup KMS generation, durably uploaded as a generation-addressed Cloud Storage object and checksum/head-verified. Re-upload of identical bytes succeeds; conflicting bytes under the same WAL name fails Critical. Cloud Storage Object Retention Lock is irreversible when locked, so its signed configuration and deletion tests precede locking; the official [Object Retention Lock](https://cloud.google.com/storage/docs/using-object-lock) and [Object Versioning](https://cloud.google.com/storage/docs/object-versioning) references were accessed 2026-08-29.

Daily `pg_basebackup` uses a dedicated least-privilege replication connection, plain format, fast checkpoint only within measured I/O budget, streamed WAL and SHA-256 backup manifest. It writes to a run-specific staging directory, runs matching `pg_verifybackup`, encrypts each object under a random DEK wrapped by the backup KMS generation, uploads to an immutable off-host bucket, verifies remote size/hash, then signs/publishes `BackupManifestV1` last. Partial staging/upload is not a backup.

`BackupManifestV1` binds backup ID, cluster system identifier, PostgreSQL major/minor and data checksum status, database/role/schema/Alembic/runtime versions, start/end/checkpoint/timeline/LSN/WAL range, file count/bytes/PostgreSQL manifest hash, per-object plaintext/ciphertext hash, KMS/wrapping generation, object bucket/version/immutability expiry, release/config/46-table/retention-policy hashes, unresolved attempt/incident/control snapshot hash, command output hashes and signature. Values/keys/PII are excluded.

Retention starts with 14 daily and 4 weekly base-backup recovery chains, never exceeding 35 days unless a signed incident/legal hold requires it. WAL is retained until every recovery chain that depends on it and its hold has expired. Prune performs dry-run dependency graph and remote-version listing, signs candidates, requires explicit backup-set IDs, deletes only after a newer clean-restore proof, and records tombstones. Product row retention still follows DB-06/SEC-06 independently.

The upstream terminated-session duration conflict is not resolved here: SEC-02 describes minimized terminated session storage as `SAFETY_LONG`, while SEC-06 specifies terminated session detail 30 days. Backup/prune/restore code must read the authoritative signed `RetentionPolicyV1` at execution time, replay its tombstones before validation, and keep restored sessions revoked/expired. Until Task 6 reconciles the manifest, tests accept neither an infrastructure-hardcoded 30-day nor `SAFETY_LONG` duration.

Restore procedure:

1. `restore/preflight` resolves a new isolated host/network/empty target directory, target backup ID/time/LSN, object versions, PostgreSQL system ID, KMS generation and no provider credentials/routes; it refuses live mount/writer/ambiguous target.
2. Fetch/decrypt to a run-specific directory, verify signature/object hashes and `pg_verifybackup`; reconstruct required WAL archive without overwriting objects.
3. Set `restore_command`, exact `recovery_target_time` or LSN/timeline and `recovery_target_action='pause'`; create `recovery.signal`; start PostgreSQL with network limited to the verifier role.
4. At recovery pause/end, record reached timeline/LSN/time; run `amcheck` where applicable, Alembic/catalog exact 46-table/FK/check/index/trigger/privilege equality, row/hash/event/audit/idempotency/outbox/workflow snapshot/incident/send-attempt-result-observation/cost/retention checks.
5. Expire/revoke every restored session/flow, force both controls false, keep public profile absent, replay retention/rights tombstones and reconcile all unresolved Gmail/provider/cost facts using recorded fixtures/read-only procedures; provider-call spy must remain zero.
6. Only after signed verification may a new production host receive the database. Enabling workers, providers, controls or public ingress is separate and requires INFRA-05/incident gates.

## Ordered implementation tasks

- [ ] **Configure exact backup identities and WAL archiving —** Input: explicit cluster/system ID, backup role, KMS/object store and 5-minute objective. Operation: enable checksums/archive settings and idempotent verified WAL upload. Output: continuous immutable WAL chain. Test evidence: duplicate/conflict/network/full-disk/KMS/clock/timeline cases. Failure behavior: alert, product controls false before disk safety is threatened, never discard WAL.
- [ ] **Implement signed daily base backups —** Input: live cluster and backup policy. Operation: stage `pg_basebackup`, verify, encrypt/upload/head-check and commit manifest last. Output: restorable recovery chain. Test evidence: interrupted/corrupt/wrong-version/missing-WAL/manifest/key cases. Failure behavior: invalid partial set and previous backup remains authoritative.
- [ ] **Implement hold-aware pruning —** Input: exact recovery dependency graph, DB-06/SEC-06 policy and holds. Operation: dry-run explicit IDs, require newer restore proof, delete object versions/WAL safely and emit tombstones. Output: bounded backup retention. Test evidence: active hold, chain dependency, wrong bucket/ID and partial-delete replay. Failure behavior: retain data and alert.
- [ ] **Implement isolated PITR/full restore —** Input: signed backup ID and target time/LSN. Operation: resolve target, decrypt/verify, recover paused, prove 46-table/business/runtime/safety invariants and tombstones. Output: signed restore report with measured loss/time. Test evidence: latest/point-in-time/corrupt/key-loss/expired-session/unresolved-attempt variants. Failure behavior: target remains isolated and writers off.
- [ ] **Exercise clean-host recovery every 90 days —** Input: newest eligible chain and clean host. Operation: rebuild through INFRA-05, compare RPO/RTO and run affected gates. Output: M8/ongoing restore evidence. Test evidence: no provider call, controls/public off and exact data/runtime compatibility. Failure behavior: Critical backup/restore incident and no release/authority increase.

## Test strategy

- **Archive `test_wal_upload_is_idempotent_conflict_detecting_remote_verified_and_meets_five_minute_rpo`.**
- **Backup `test_base_backup_manifest_signature_hash_key_wal_and_system_identity_are_complete`.**
- **Prune `test_explicit_hold_aware_dependency_prune_requires_newer_restore_proof`.**
- **PITR `test_restore_reaches_exact_timeline_lsn_time_and_preserves_46_table_invariants`.**
- **Safety `test_restore_revokes_sessions_controls_public_routes_and_calls_no_provider`.**
- **Deletion `test_retention_tombstones_prevent_purged_payload_from_reappearing_after_restore`.**
- **Policy `test_session_retention_is_loaded_from_authoritative_manifest_not_hardcoded`.**

## Security, privacy, compliance, idempotency, observability, and cost

Backups are client-side envelope encrypted plus object-store protected, immutable/versioned, off-host and inaccessible to API/worker. Backup/wrapping keys are separate; two encrypted recovery copies remain off-host. Manifests/logs contain hashes/IDs only. Upload/prune/restore use exact IDs and replay safely. Emit canonical backup/restore age/result metrics and alerts without object paths. Storage/egress/KMS/restore-test cost is measured before retention expansion. Holds/counsel decisions override pruning.

## Failure, rollback, and operator recovery

On archive gap, hash/signature/key/system-ID mismatch, missed RPO, failed verify/restore, full disk, unintended prune, tombstone failure or provider call: stop pruning/writers/workers as needed, set both controls false, preserve surviving backup/WAL/object versions and open IR-08/T10 incident. Restore only to a new isolated target and rotate/re-authorize lost secrets. Never alter a manifest, force recovery past corruption, delete WAL for space without dependency proof, or mount the failed target as production.

## Acceptance and retained evidence

- [ ] Encrypted off-host base/WAL chains meet the measured <=5-minute RPO and are manifest-last/tamper-evident.
- [ ] Clean latest/PITR restores meet <=4-hour service RTO and exact 46-table/runtime/safety invariants.
- [ ] Holds, backup expiry and restored deletion/session/control rules are executable and evidence-bearing.
- [ ] `pg_verifybackup` is paired with a real restore; unavailable object/KMS/VPS paths are never false-passed.

Retain PostgreSQL/object/KMS configs without values, WAL/base/verification/prune manifests, object version/immutability evidence, restore commands/timelines/catalog/row hashes, RPO/RTO measurements, tombstone/session/control/provider-call proof, cost records and incidents.

## Dependencies and next deliverable

INFRA-04 consumes INFRA-03 topology and supplies the recovery primitive to [INFRA-05 monitoring/DR](05-monitoring-and-disaster-recovery.md). The unresolved session-retention conflict must be reconciled upstream before production retention acceptance; restore mechanics remain fail-closed meanwhile.
