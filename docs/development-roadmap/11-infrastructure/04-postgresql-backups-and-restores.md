# PostgreSQL Backups, PITR, Retention, and Clean Restores

**Document ID:** INFRA-04
**Status:** Planned M8 backup/restore system; current local PostgreSQL volume has no configured archive, off-host backup, PITR, or restore drill
**Milestone:** M8
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `INFRA-04-T01 <- INFRA-03-T04; INFRA-04-T02 <- INFRA-04-T01; INFRA-04-T03 <- INFRA-04-T02,SEC-06-T02; INFRA-04-T04 <- INFRA-04-T03,SEC-06-T02,DB-06-T05; INFRA-04-T05 <- INFRA-04-T04; INFRA-04-T06 <- INFRA-04-T05,INFRA-05-T06; INFRA-04-T07 <- INFRA-04-T06; INFRA-04-T08 <- INFRA-04-T07`
**Outputs:** application-encrypted R2 base backups/WAL, signed manifests, bounded retention, isolated PITR/full restore, measured RPO/RTO and restore evidence
**Unlocks:** INFRA-05 disaster recovery and M8 acceptance
**Risk:** Critical
**Complexity:** L

## Outcome

PostgreSQL product/security state can be restored on a clean host without starting writers/providers, reviving sessions/controls, losing unresolved Gmail/calendar authority, or silently resurrecting data that should remain deleted/suppressed.

The **pre-revenue backup topology is one application-encrypted Cloudflare R2 repository** plus off-host recovery material. Multi-cloud repositories, deletion witnesses, managed KMS and Object-Lock-style enterprise controls are deferred until revenue or an architecture review proves they are needed.

A single provider is not treated as magically infallible: restore readiness depends on cryptographic integrity, versioned manifests, clean-host drills, off-host decryption/bootstrap material, provider-account recovery evidence, and local export/recovery procedures. But pre-revenue M8 does not require paying for a second cloud solely as a witness.

## Backup contract

Required:

- PostgreSQL 18-compatible continuous backup/WAL strategy (pgBackRest or equivalent proven tool);
- client/application-side encryption before bytes leave the VPS;
- R2 bucket/object configuration with least-privilege credentials and versioned retention settings;
- content-addressed/signed backup manifest with DB schema/release/config/offer/strategy/stage/control generations needed for recovery verification;
- off-host encrypted recovery package containing independently usable backup-decryption material, exact repository configuration, pinned restore-tool/version hashes and R2 read credentials or recovery steps;
- bounded retention that respects SEC-06 deletion/hold rules;
- clean-host latest/PITR restore exercises;
- restore verification before any application writer/provider authority is enabled.

Provider-side encryption/versioning may be enabled as defense in depth but never substitutes for application encryption or restore evidence.

## Recovery safety

A restored environment starts with product outreach, calendar writes, background workers, strategy activation and stage admission **off**. It then verifies:

- migration/schema and data invariants;
- immutable artifacts/evidence hashes;
- current suppression/tombstone/legal-policy state;
- campaign/stage/tranche membership and checkpoint generations;
- offer/economics/strategy activation attribution;
- conversation/negotiation/booking state;
- send/booking attempts including unresolved provider ambiguity;
- idempotency/outbox/event sequences and current kill controls;
- backup manifest/decryption/repository identity and restore cutoff.

Possibly-called Gmail/calendar actions reconcile against providers before any retry/re-enable. Restore cannot create another send, booking, stage, strategy activation, or commercial commitment.

## Retention and deletion

Backup retention has explicit classes and expiry windows owned by SEC-06/DB-06. A deletion/hold workflow records signed tombstone/hold evidence and ensures future restored data is re-filtered against authoritative deletion/suppression/hold state before use. The pre-revenue design does **not** depend on an AWS deletion-witness bucket.

Deletion from old encrypted backup generations is bounded and audited. Missing/corrupt/ambiguous repository truth blocks positive restore/re-enable evidence instead of inventing success.

## RPO/RTO

Initial RPO/RTO are measured objectives, not provider promises. The small-VPS/R2 system should target a practical <=15-minute database RPO where WAL/upload economics support it and <=4-hour clean private-service RTO, but the retained drills own the actual accepted values. A cheaper/less frequent setting may be selected only if the signed M0/M8 risk/economic decision accepts the measured exposure.

## Ordered implementation tasks

<!-- roadmap-task id=INFRA-04-T01 milestone=M8 depends_on=INFRA-03-T04 mode=serial locks=backup-restore -->
- [ ] **Configure exact encrypted R2 WAL/base-backup repository —** Input: INFRA-03 accepted R2/encryption bootstrap and PostgreSQL target. Operation: configure backup role, repository, client-side encryption, bounded WAL/base schedule and zero-writer restore mode. Output: one signed pre-revenue repository configuration. Test evidence: plaintext-object denial, wrong repository/key, WAL gap, credential-scope and upload/retry cases. Failure behavior: backup/recovery gate fails.
<!-- roadmap-task id=INFRA-04-T02 milestone=M8 depends_on=INFRA-04-T01 mode=serial locks=backup-restore -->
- [ ] **Implement signed encrypted backups and manifests —** Input: live private database and repository config. Operation: create encrypted backups/WAL plus manifest/hash/metadata and verify repository reads independently. Output: retained backup chain. Test evidence: corrupt/truncated/wrong-key/version/config mismatch. Failure behavior: affected chain not restore-eligible.
<!-- roadmap-task id=INFRA-04-T03 milestone=M8 depends_on=INFRA-04-T02,SEC-06-T02 mode=serial locks=backup-restore -->
- [ ] **Implement deletion/hold evidence ledger without multi-cloud witness —** Input: accepted backup chain and SEC-06 inventory. Operation: record signed PREPARED/AUTHORIZED/COMMITTED retention/deletion/hold decisions locally plus in retained encrypted audit evidence. Output: auditable deletion/hold lineage. Test evidence: stale authorization, replay, concurrent prune/restore and missing audit proof. Failure behavior: no destructive prune.
<!-- roadmap-task id=INFRA-04-T04 milestone=M8 depends_on=INFRA-04-T03,SEC-06-T02,DB-06-T05 mode=serial locks=backup-restore -->
- [ ] **Implement policy-bounded pruning —** Input: retention rules, holds, restore dependencies and signed deletion ledger. Operation: remove only eligible backup/WAL objects while preserving required restore chains/evidence. Output: bounded repository state. Test evidence: hold/active-chain/tombstone/replay/race cases. Failure behavior: retain data rather than break recovery.
<!-- roadmap-task id=INFRA-04-T05 milestone=M8 depends_on=INFRA-04-T04 mode=serial locks=backup-restore,live-environment -->
- [ ] **Implement isolated PITR/full restore —** Input: encrypted R2 repository plus off-host recovery package. Operation: restore onto a fresh isolated host with all writers/providers disabled, apply migrations/verification/tombstones and reconcile possibly-called actions. Output: verified restored snapshot. Test evidence: latest/time/LSN, wrong key, provider unavailable, stale suppression and unresolved send/booking attempts. Failure behavior: no re-enable.
<!-- roadmap-task id=INFRA-04-T06 milestone=M8 depends_on=INFRA-04-T05,INFRA-05-T06 mode=serial locks=backup-restore,live-environment -->
- [ ] **Exercise clean-host recovery every 90 days —** Input: current release and independently retained recovery package. Operation: restore without relying on VPS-local state, measure RPO/RTO and complete invariant/action reconciliation. Output: signed drill evidence. Test evidence: missing local host/credential/config scenarios. Failure behavior: M8/re-enable freshness expires.
<!-- roadmap-task id=INFRA-04-T07 milestone=M8 depends_on=INFRA-04-T06 mode=serial locks=backup-restore -->
- [ ] **Exercise R2 credential/key rotation and provider-account recovery —** Input: current repository and off-host recovery package. Operation: rotate credentials/encryption generation and prove old/new chain restore plus account-recovery procedure. Output: rotation/recovery evidence. Test evidence: lost VPS, revoked old key, wrong generation and account-access outage. Failure behavior: backup credit blocked until repaired.
<!-- roadmap-task id=INFRA-04-T08 milestone=M8 depends_on=INFRA-04-T07 mode=serial locks=backup-restore -->
- [ ] **Close backup/restore command ownership and deferred-upgrade inventory —** Input: all backup/retention/restore requirements. Operation: prove exact command/evidence mapping and explicitly classify multi-cloud/KMS/Object-Lock witness controls as post-revenue upgrades. Output: signed coverage. Test evidence: orphan/duplicate command, unencrypted backup, hidden second-cloud prerequisite. Failure behavior: M8 remains blocked.

## Acceptance

- [ ] One application-encrypted R2 repository is the pre-revenue off-host backup target.
- [ ] Off-host recovery material can restore without VPS-local keys/config.
- [ ] Clean-host restore proves data/control/send/booking/strategy integrity before re-enable.
- [ ] Retention/holds/deletion are auditable without requiring a second cloud witness.
- [ ] Multi-cloud backup, managed KMS and enterprise retention controls are deferred upgrade paths, not M8 prerequisites.
