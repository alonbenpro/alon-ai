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

PostgreSQL product and `security_runtime` state can be recovered on a clean host to an exact target time without starting writers/providers, reviving sessions/controls, losing unresolved Gmail authority, or resurrecting purged data into use. Initial objective for an intact live provider is database RPO <=5 minutes and complete private-service RTO <=4 hours. A Google-wide outage has database RPO <=5 minutes only when the independently verified B2 WAL chain is current, isolated-data recovery RTO <=8 hours, and full-service RTO explicitly `N/A—not claimed` until alternate compute is separately vetted. Every value is proven by drills, never inferred from upload success.

PostgreSQL 18 documents continuous archiving and point-in-time recovery in the official [backup chapter](https://www.postgresql.org/docs/18/backup.html), accessed 2026-08-29. It is the database recovery contract; pgBackRest supplies the selected repository implementation below, and only a real isolated restore supplies gate evidence.

## Current repository state

`infra/compose.yaml` uses one local named PostgreSQL 18 volume and Alembic migration. DB-06 plans encrypted backups and a fresh restore test, but no backup role, `wal_level/archive_mode/archive_command`, archive spool, object store, KMS envelope, signed backup catalog, retention job, PITR configuration, restore host, tombstone replay, monitoring or drill exists. No current RPO/RTO claim is valid.

## Scope and non-goals

In scope: explicit `PGDATA`, data checksums, dedicated backup role, pgBackRest 2.59.1, daily full backup, WAL archival with maximum five-minute switch, primary immutable Google Cloud Storage repository, exactly one off-provider private Backblaze B2 EU Central S3-compatible Object-Lock repository, client-side repository encryption, off-Google recovery custody, signed manifest/catalog, verification, retention, restore to latest/time/LSN, 46-table/invariant/event/send-chain checks, sessions/flows/control safety, an independently retained signed deletion-tombstone chain, drills, divergence/corruption/key-loss cases. Non-goals: copying a live volume, same-host-only backup, unencrypted dump, hot multi-cloud production, alternate compute claims, assuming provider snapshots are application-consistent, restoring into live writers, using restore as normal rollback, or deleting old backup/WAL before dependency proof.

## Exact planned implementation surfaces

Create `infra/postgres/{postgresql.conf,pg_hba.conf,backup-role.sql,pgbackrest.conf}`, `scripts/backup/{check,backup,verify,prune}.sh`, `scripts/retention/{prepare_bundle,verify_receipts,commit_purge}.sh`, `scripts/restore/{preflight,bootstrap_dr,restore,replay_tombstones,verify}.sh`, `backup-manifest.schema.json`, `deletion-tombstone-bundle.schema.json`, and immutable policies for both repositories. Pin pgBackRest `2.59.1` and require exact client/server binary and configuration hashes; pgBackRest documents exact-version agreement, client-side repository encryption, multiple repositories, independently scheduled per-repository backups, repository selection for restore, and S3-compatible storage in its official [user guide](https://pgbackrest.org/user-guide.html), accessed 2026-08-29. Backblaze documents the [S3-compatible API](https://www.backblaze.com/docs/cloud-storage-s3-compatible-api), [Object Lock operations](https://www.backblaze.com/docs/cloud-storage-enable-object-lock-with-the-s3-compatible-api), and EU Central Amsterdam [data region](https://www.backblaze.com/computer-backup/docs/data-centers-and-data-regions), accessed 2026-08-29. These sources establish provider capabilities, not configured-state evidence.

The signed non-secret configuration is exact:

```ini
[global]
repo1-type=gcs
repo1-gcs-bucket=alon-ai-prod-backup-eu
repo1-gcs-key-type=auto
repo1-path=/pgbackrest/alon-ai
repo1-retention-full=14
repo1-cipher-type=aes-256-cbc
repo2-type=s3
repo2-s3-endpoint=s3.eu-central-003.backblazeb2.com
repo2-s3-region=eu-central-003
repo2-s3-bucket=alon-ai-dr-eu-central
repo2-s3-uri-style=host
repo2-s3-key-type=shared
repo2-path=/pgbackrest/alon-ai
repo2-retention-full=14
repo2-cipher-type=aes-256-cbc
archive-async=y
spool-path=/var/spool/pgbackrest
start-fast=y
[alon-ai]
pg1-path=/var/lib/postgresql/18/main
```

Both repository cipher passes and the B2 `repo2-s3-key`/`repo2-s3-key-secret` values are injected into a root/backup-role-readable tmpfs credential include from scoped secret references and never appear in the signed config, process list or evidence; repo 1 uses the GCE instance service account through `repo1-gcs-key-type=auto`. `repo1` uses the separately governed GCS object-retention project; `repo2` is the sole off-provider repository and is created only after the M8 legal/transfer/terms/region/Object-Lock/cost decision. B2 Object Lock is enabled at bucket creation with governance retention, and the application key cannot delete locked versions. Exact bucket/account/endpoint IDs, default retention and a failed delete-before-retain-until test are signed. Two encrypted recovery packages held outside Google and the VPS contain read-only B2 credentials, `repo2` cipher pass, pinned pgBackRest binary/image digest, config hash and verification public keys; the B2 write key is not in the packages. Rotation writes a new package generation, verifies a full isolated repo-2 restore, then revokes the old credential. Loss, custody disagreement or simultaneous loss of repository and packages makes recovery unavailable (`30`), never green.

PostgreSQL uses `wal_level=replica`, `archive_mode=on`, `archive_timeout=300s`, and exact `archive_command='pgbackrest --stanza=alon-ai archive-push %p'`; pgBackRest must verify both repositories before returning success. Daily commands are `sudo -u postgres pgbackrest --stanza=alon-ai --repo=1 --type=full backup` and the same with `--repo=2`; hourly differentials are scheduled independently. `sudo -u postgres pgbackrest --stanza=alon-ai --repo=1 check`, `--repo=2 check`, and per-repository `info --output=json` must agree on stanza/system ID/timeline and required WAL coverage. A success in one repository never masks failure in the other: backup publication records `HEALTHY_BOTH`, `DIVERGENT`, or `UNAVAILABLE`; only `HEALTHY_BOTH` meets the dual-repository gate. Conflicting WAL, missing Object Lock, chain divergence or missed five-minute coverage sets controls false before spool exhaustion and opens IR-08. Primary-only recovery may continue for an ordinary B2 outage, but no purge may commit without both tombstone receipts and provider-outage readiness is stale until healed.

`BackupManifestV1` binds backup ID, repository number/provider/region/object versions and retention, cluster system identifier, PostgreSQL/pgBackRest exact versions and data checksum status, database/role/schema/Alembic/runtime versions, start/end/checkpoint/timeline/LSN/WAL range, file count/bytes/repository checksum, repository cipher/key generation IDs without values, release/config/46-table/retention-policy hashes, unresolved attempt/incident/control snapshot hash, command/artifact hashes and signature. A partial upload or repository disagreement is not a backup.

### Authoritative deletion-tombstone ledger

`RetentionCommandService` implements a two-phase idempotent purge. In phase 1, one PostgreSQL transaction locks the canonical delete graph, verifies holds/policy, and creates `DeletionTombstoneBundleV1` without deleting or redacting a row. Its exact logical payload is `{schema_version:"retention.deletion_tombstone_bundle.v1",sequence:uint64,previous_bundle_hash:hex64|"GENESIS",command_id:uuid,idempotency_key:uuid,policy_manifest_hash:hex64,policy_version:string,prepared_at_utc:RFC3339,cutoff_utc:RFC3339,lookup_key_generation:string,entries:[{table_code:closed_enum,opaque_row_ref:base64url43,action:"DELETE"|"REDACT",record_generation:uint64}]}`. Entries are sorted by `(table_code,opaque_row_ref,action,record_generation)` and duplicates reject. `opaque_row_ref=base64url(HMAC-SHA-256(lookup_key_generation, RFC8785({table_code,primary_key_columns})))`; primary keys are read only inside the retention/restore process, never written to the bundle, and canonical IDs may not be reused. `record_generation` is the canonical row version named by the signed 46-table retention map, or literal `0` for a non-versioned row with a never-reused stable primary key; no new product column/table is implied.

The signature preimage is the ASCII domain `alon-ai:retention-tombstone:v1\n`, followed by 32 decoded bytes of `previous_bundle_hash` (32 zero bytes for `GENESIS`), followed by RFC 8785 bytes of the logical payload. `bundle_hash=hex(SHA-256(preimage))`; `signature=base64url(Ed25519-Sign(tombstone_signing_key_generation, decoded_bundle_hash))`. The stored envelope is `{payload,bundle_hash,signing_key_generation,signature}`. It contains no PII, address, recipient hash, ciphertext, raw personal data or provider value. Object names are only `retention-ledger/v1/bundles/{sequence-as-20-digits}.bin`; object metadata is the fixed content type and schema version, with no row/hash/dynamic label. Each plaintext envelope is client-side AES-256-GCM encrypted using a random DEK and constant domain AAD, with the DEK wrapped separately for repo 1 and the off-Google recovery generation; ciphertext is the storage representation, not a field in the logical tombstone payload.

Phase 2 uploads the encrypted bundle and signed `DeletionTombstoneReceiptV1` to repo 1 and repo 2, performs authenticated GET using a distinct read credential, decrypts, verifies object version/retention, length, bundle hash, signature, previous hash and exact bytes, then mirrors the signed pair of repository receipts beside the bundle in **both** repositories. The receipt is `{schema_version,sequence,bundle_hash,repository:"GCS_PRIMARY"|"B2_DR",bucket_account_id,object_version,retain_until_utc,verified_at_utc,verifier_key_generation}` plus signature; it contains no object secret/path or row data. A signed dual-attested head in both repositories advances only when the contiguous chains and mirrored receipt pairs agree. Only then does a new PostgreSQL transaction reacquire every target, verify unchanged generation/hold/policy, execute the canonical purge/redaction graph, record both receipts and advance `purge_watermark` to the highest contiguous committed sequence. Crash before two verified external receipts performs no purge. Crash after receipts/head but before purge leaves a conservative pending bundle; retry with the same idempotency key re-verifies the immutable bundle and commits the purge once. One receipt, chain divergence, target mutation or policy change performs no purge and alerts.

The signed external head `{schema_version:"retention.ledger_head.v1",highest_contiguous_sequence,bundle_hash,gcs_receipt_hash,b2_receipt_hash,updated_at_utc}` in each repository is authoritative outside the PostgreSQL timeline. Normal restore retrieves both heads and requires identical contiguous chains. If exactly one provider is unavailable, the surviving repository is sufficient only when every post-watermark bundle contains both valid immutable receipt signatures and its dual-attested head is contiguous; because no purge commits without a B2 receipt, the B2 mirror is independently authoritative during a Google-wide outage. While isolated/offline and before any service starts, `replay_tombstones` recomputes opaque row references by scanning only closed table/PK mappings with the required lookup-key generation, executes each bundle in sequence in one transaction, records receipts, advances `purge_watermark`, and proves no target at or below the deleted generation remains. Its last transaction writes `RestoreCutoverV1={restore_id,restored_watermark,external_head_sequence,replayed_first_sequence,replayed_last_sequence,post_replay_row_absence_hash}`; `restore_cutover_watermark=external_head_sequence` is the only service-start input and must equal a freshly re-read surviving head immediately before cutover. A target PITR immediately before prepare, between two receipts, after both receipts/before purge, and after purge are mandatory fixtures. Missing key/object/signature/receipt, a chain gap/fork, available-head disagreement, unknown table/action/generation, a head advanced after replay, or a post-target bundle that cannot be replayed leaves PostgreSQL paused, controls/public absent and all services off; it never accepts possible resurrection.

Retention starts with 14 daily and 4 weekly base-backup recovery chains in each repository, never exceeding 35 days unless a signed incident/legal hold requires it. WAL is retained until every recovery chain that depends on it and its hold has expired. Prune performs per-repository dry-run dependency graphs and object-version listings, signs candidates, requires explicit backup-set IDs, deletes only after a newer clean restore from that repository, and never prunes the deletion ledger before the authoritative retention/rights horizon plus every backup chain capable of predating it. Product row retention still follows DB-06/SEC-06 independently.

The upstream terminated-session duration conflict is not resolved here: SEC-02 describes minimized terminated session storage as `SAFETY_LONG`, while SEC-06 specifies terminated session detail 30 days. Backup/prune/restore code must read the authoritative signed `RetentionPolicyV1` at execution time, replay its tombstones before validation, and keep restored sessions revoked/expired. Until Task 6 reconciles the manifest, tests accept neither an infrastructure-hardcoded 30-day nor `SAFETY_LONG` duration.

Restore procedure:

1. `restore/preflight` resolves a new isolated host/network/empty target directory, target backup ID/time/LSN, selected repository, PostgreSQL system ID and zero provider credentials/routes/writers; it refuses a live mount, unresolved target or absent destructive confirmation. Repo-2 bootstrap starts from a clean non-Google host with the offline recovery package, verifies its custody signatures and pinned pgBackRest image before contacting B2.
2. For primary recovery run exact `pgbackrest --stanza=alon-ai --repo=1 --delta=n --type=time --target="$TARGET_UTC" --target-action=pause restore`; for off-provider recovery run the identical argv with literal `--repo=2`. The signed scenario may replace `--type=time --target="$TARGET_UTC"` only with literal `--type=lsn --target="$TARGET_LSN"` or `--type=immediate`; `PGDATA` remains the resolved empty target. Verify repository checksum/signature/object versions and required WAL before start.
3. Start PostgreSQL with network limited to the verifier role. At recovery pause/end, record timeline/LSN/time and restored `purge_watermark`; keep API, workers, SendGateway, Gmail credentials, public proxy and normal KMS/secret access absent.
4. Retrieve/authenticate both external tombstone heads; replay every verified contiguous bundle after the restored watermark in sequence in isolated transactions. No application service starts if both ledgers cannot be proved identical. Then revoke every restored session/flow, force both controls false and keep public profile absent.
5. Run `amcheck` where applicable; Alembic/catalog exact 46-table/FK/check/index/trigger/privilege equality; row/hash/event/audit/idempotency/outbox/workflow snapshot/incident/send-attempt-result-observation/cost/retention/tombstone checks; and recorded-fixture-only unresolved Gmail reconciliation with provider-call spy zero.
6. Only after signed verification may a new production host receive the database. Enabling workers, providers, controls or public ingress is separate and requires INFRA-05/incident gates. A Google-wide drill ends after independently decryptable isolated-data evidence; it does not claim full-service recovery.

Backup/restore command ownership is closed: archive/check/primary backup requirements map to `T7-BACKUP-PRIMARY`; repo-2/B2/Object-Lock/divergence requirements to `T7-BACKUP-DR`; two-phase purge to destructive `T7-TOMBSTONE-PURGE`; primary restores to destructive `T7-RESTORE-PRIMARY`; and off-Google restores to destructive `T7-RESTORE-DR`. Exact invocations and exit semantics are in the [TEST-01 command registry](../10-testing/01-testing-strategy.md#closed-command-manifest). Destructive target manifests bind host/network/empty `PGDATA`, database/system ID, repository/object versions, target time/LSN, zero writers/credentials and confirmation digest. Unavailable=`30`, integrity/chain=`40`, unsafe target=`50`, partial external receipt=`60`; none passes.

## Ordered implementation tasks

- [ ] **Configure exact dual-repository WAL archiving —** Input: explicit cluster/system ID, pgBackRest 2.59.1, backup role, GCS repo 1, approved B2 repo 2, client keys and five-minute objective. Operation: verify both repositories/Object Lock/config, archive to both and compare system/timeline/WAL coverage. Output: continuous dual immutable WAL chain. Test evidence: duplicate/conflict/divergence/network/full-disk/key/clock/timeline/Object-Lock cases. Failure behavior: alert, controls false before spool danger, never discard WAL or mask one-repo failure.
- [ ] **Implement signed per-repository backups —** Input: live cluster and dual-repository policy. Operation: run exact repo-1/repo-2 pgBackRest backups, verify info/check/object retention and publish manifest last. Output: two independently restorable encrypted chains. Test evidence: interrupted/corrupt/wrong-version/missing-WAL/manifest/key/repository-divergence cases. Failure behavior: invalid partial set; prior verified set remains authoritative.
- [ ] **Implement the two-phase deletion ledger —** Input: retention command, authoritative policy, locked canonical delete graph and two healthy repositories. Operation: prepare exact signed/hash-chained opaque bundle, upload/authenticate both immutable receipts, then purge once and advance contiguous watermark. Output: privacy deletion that survives older PITR. Test evidence: crash before receipts, between receipts, after receipts/before purge, target mutation, replay and chain-fork fixtures. Failure behavior: before two receipts no purge; after receipts retry conservatively; any mismatch keeps services off.
- [ ] **Implement hold-aware pruning —** Input: exact recovery dependency graph, DB-06/SEC-06 policy and holds. Operation: dry-run explicit IDs, require newer restore proof, delete object versions/WAL safely and emit tombstones. Output: bounded backup retention. Test evidence: active hold, chain dependency, wrong bucket/ID and partial-delete replay. Failure behavior: retain data and alert.
- [ ] **Implement isolated PITR/full restore —** Input: signed backup ID and target time/LSN. Operation: resolve target, decrypt/verify, recover paused, prove 46-table/business/runtime/safety invariants and tombstones. Output: signed restore report with measured loss/time. Test evidence: latest/point-in-time/corrupt/key-loss/expired-session/unresolved-attempt variants. Failure behavior: target remains isolated and writers off.
- [ ] **Exercise clean-host recovery every 90 days —** Input: newest eligible chain and clean host. Operation: rebuild through INFRA-05, compare RPO/RTO and run affected gates. Output: M8/ongoing restore evidence. Test evidence: no provider call, controls/public off and exact data/runtime compatibility. Failure behavior: Critical backup/restore incident and no release/authority increase.
- [ ] **Exercise off-Google bootstrap and key rotation —** Input: repo-2 chain, offline package generations and clean non-Google isolated compute approved only for the drill. Operation: authenticate custody, materialize secrets on tmpfs, restore/decrypt/replay tombstones, rotate package, repeat, then destroy the isolated target. Output: independent data-recovery proof, not a live service. Test evidence: Google KMS/Secret Manager/GCS unavailable, old/new/lost key, B2 Object-Lock and simultaneous-failure matrix. Failure behavior: provider-outage readiness failed; service/send/public remain off and full-service RTO stays N/A.
- [ ] **Close backup/restore command ownership —** Input: every archive/backup/purge/restore/drill requirement. Operation: prove exact mapping to the five owning Task 7 commands, profiles, guards, inputs, artifacts and exit semantics. Output: signed set-equality report. Test evidence: orphan/duplicate/unavailable/integrity/unsafe/partial negatives. Failure behavior: no backup, purge or restore gate credit.

## Test strategy

- **Archive `test_wal_upload_is_idempotent_conflict_detecting_remote_verified_and_meets_five_minute_rpo`.**
- **Backup `test_pgbackrest_2591_repositories_are_independently_encrypted_restorable_and_wal_equal`.**
- **Object lock `test_b2_eu_central_private_bucket_lock_and_failed_early_delete_are_verified`.**
- **Prune `test_explicit_hold_aware_dependency_prune_requires_newer_restore_proof`.**
- **PITR `test_restore_reaches_exact_timeline_lsn_time_and_preserves_46_table_invariants`.**
- **Safety `test_restore_revokes_sessions_controls_public_routes_and_calls_no_provider`.**
- **Deletion `test_retention_tombstones_prevent_purged_payload_from_reappearing_after_restore`.**
- **Tombstone schema `test_bundle_rfc8785_preimage_hash_chain_signature_receipts_and_watermark_are_exact`.**
- **Tombstone crash `test_two_phase_purge_crashes_never_delete_before_dual_receipts_and_replay_is_idempotent`.**
- **Restore targets `test_pitr_before_prepare_between_receipts_before_purge_and_after_purge_never_resurrects`.**
- **Provider outage `test_off_google_repo2_bootstrap_decrypt_restore_and_key_rotation_need_no_google_service`.**
- **Policy `test_session_retention_is_loaded_from_authoritative_manifest_not_hardcoded`.**

## Security, privacy, compliance, idempotency, observability, and cost

Backups are pgBackRest client-side encrypted plus object-store protected, immutable/versioned, off-host and inaccessible to API/worker. Repository, tombstone lookup/signing and recovery keys are purpose-separated; two encrypted recovery packages remain outside Google/VPS. Tombstone payloads/object names/metadata contain no PII, address, recipient hash, ciphertext field or raw data. Manifests/logs contain safe hashes/IDs only. Upload/prune/restore use exact IDs and replay safely. Emit canonical backup/restore age/result metrics and alerts without object paths. B2 legal/transfer/terms/region/Object-Lock/storage/egress and restore-test cost evidence precedes provisioning or retention expansion. Holds/counsel decisions override pruning.

## Failure, rollback, and operator recovery

On archive gap, hash/signature/key/system-ID mismatch, missed RPO, failed verify/restore, full disk, unintended prune, tombstone failure or provider call: stop pruning/writers/workers as needed, set both controls false, preserve surviving backup/WAL/object versions and open IR-08/T10 incident. Restore only to a new isolated target and rotate/re-authorize lost secrets. Never alter a manifest, force recovery past corruption, delete WAL for space without dependency proof, or mount the failed target as production.

## Acceptance and retained evidence

- [ ] Encrypted repo-1 and off-provider repo-2 base/WAL chains meet measured <=5-minute RPO when healthy, are manifest-last/tamper-evident, and have exact divergence behavior.
- [ ] Clean latest/PITR restores meet <=4-hour intact-provider service RTO and exact 46-table/runtime/safety invariants; Google-wide recovery proves <=8-hour isolated data only and full-service RTO is N/A.
- [ ] Holds, backup expiry and restored deletion/session/control rules are executable and evidence-bearing.
- [ ] No purge occurs before two immutable authenticated receipts; every restore replays the complete signed post-watermark chain before any service start.
- [ ] pgBackRest repository checksum/check evidence is paired with a real restore from each repository; unavailable object/key/VPS paths are never false-passed.

Retain PostgreSQL/pgBackRest/repository configs without values, source access-date record, WAL/backup/verification/prune manifests, GCS/B2 object-version/Object-Lock evidence, encrypted-package custody/rotation/loss results, restore commands/timelines/catalog/row hashes, RPO/RTO applicability/measurements, exact tombstone bundles/receipts/heads/watermarks/crash fixtures, session/control/provider-call proof, cost/legal decision IDs and incidents.

## Dependencies and next deliverable

INFRA-04 consumes INFRA-03 topology and supplies the recovery primitive to [INFRA-05 monitoring/DR](05-monitoring-and-disaster-recovery.md). The unresolved session-retention conflict must be reconciled upstream before production retention acceptance; restore mechanics remain fail-closed meanwhile.
