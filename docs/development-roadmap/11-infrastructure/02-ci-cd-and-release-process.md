# CI, Artifact Promotion, Release, and Rollback Process

**Document ID:** INFRA-02
**Status:** Planned M8 release discipline; current GitHub Actions builds/tests the foundation but does not publish signed images or deploy
**Milestone:** M1-M8 gate automation; M8 private release
**Owner:** Solo operator; GitHub Actions produces candidates, and the operator performs the separate VPS promotion ceremony
**Prerequisites:** TEST-01..06, INFRA-01, current CI, immutable migration/release contracts, SEC-01 supply-chain controls, OBS-04/05
**Outputs:** Staged CI gates, SBOM/provenance/image digests, signed release manifest, operator-led deployment, migration compatibility, rollback and upgrade evidence
**Unlocks:** INFRA-03 private VPS promotion and M8 release evidence
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Every release is an immutable, signed candidate tied to source, lockfiles, generated API, migrations, schemas/configs, tests, SBOM, vulnerability decisions and rollback target. CI never directly enables controls or public routes. The operator promotes exact image digests from the private VPS and can roll back application/config pointers without rewriting PostgreSQL history.

## Current repository state

GitHub Actions currently has `security`, `backend`, `frontend`, and `containers` jobs with pinned action SHAs, read-only repository permission, secret scan, PostgreSQL 18 migration/tests, OpenAPI drift, lint/typecheck/build, Compose image build and disposable smoke. Images are local CI artifacts only. There is no registry push, SBOM, signature/attestation, release manifest, environment approval, migration compatibility matrix, VPS deployment command, public-route manifest gate, staged rollout, rollback drill, or upgrade policy implementation.

## Scope and non-goals

In scope: PR/scheduled/release lanes, exact test evidence freshness, dependency/secret/license/vulnerability scans, SBOM/provenance/signing, immutable image registry, release manifest, additive migration ordering, operator promotion, health/soak verification, rollback, key/dependency/base-image/PostgreSQL upgrades and evidence. Non-goals: auto-deploy from untrusted PR, long-lived SSH/cloud keys in CI, mutable `latest`, automatic schema downgrade, rollout that enables Gmail/public ingress, or a second CI platform.

## Exact planned implementation surfaces

Extend `.github/workflows/ci.yml`; add `.github/workflows/release.yml`, `infra/release/release-manifest.schema.json`, `scripts/release/{build_manifest,verify_manifest,preflight,apply,rollback}.sh`, SBOM/provenance generation, and private GitHub Container Registry packages addressed as `ghcr.io/alonbenpro/alon-ai-{backend,frontend,public-edge}@sha256:<digest>`. Workflows keep `permissions: contents: read` by default; only the release job receives minimal `packages: write` and `id-token: write` for GitHub artifact attestation, protected environment approval and no runtime/VPS credential. Operator deployment uses the VPS console/private Tailscale network to pull and verify exact digests, avoiding a permanent CI-to-VPS key.

| Stage | Required checks/evidence | Trigger | Failure action |
| --- | --- | --- | --- |
| PR deterministic | current format/lint/typecheck/unit/integration/generated/client/secret plus TEST-02 impacted contracts | every PR/push | block merge/candidate |
| PR containers | Compose config/build/migrate/smoke, non-root, controls false, image filesystem scan | every PR/push | block merge/candidate |
| scheduled deep | TEST-03 recovery, TEST-05 browser/accessibility, TEST-06 security/chaos subset, dependency/license/vulnerability drift | scheduled and before release | open defect; no release |
| provider gate | signed M1/M6 or agent-capture evidence from isolated authorized lane | only when relevant component changes | affected gate stale/failed; controls false |
| release build | clean checkout, locked build once, SBOM, provenance, signature, image/config/migration/API hashes, test evidence refs | signed tag/operator dispatch | candidate manifest only |
| VPS promotion | verify candidate/target/pre-backup/capacity/active runs/ambiguities/controls, additive migration, start/health/soak | explicit operator command on private VPS | retain prior release; rollback/restore path |

`ReleaseManifestV1` includes release ID, commit/tree/dirty=false, Python/npm lock hashes, action/workflow hashes, backend/frontend/public-edge image digests, SBOM/provenance/signature refs, migration head/compatibility range, OpenAPI 66/64+2 and incident/policy/provider manifest hashes, DBOS/Temporal runtime version, active agent promotion refs, config/KMS/secret generations without values, test evidence IDs/freshness/applicability, previous release/rollback digest, backup/restore proof IDs and intended route/control states. Any missing/mismatched field rejects.

Promotion sequence:

1. `preflight --release <id>` resolves exact VPS, database system ID, current release, controls, public-route flag, active/nonterminal workflows, unresolved attempts/incidents, disk/RAM and newest verified backup.
2. Pull images by digest and verify signature/SBOM/provenance; never execute an unverified candidate.
3. Run schema compatibility check. Deploy additive migration before new writers; stop/drain workers for declared incompatible changes. No destructive migration runs without a separately proven restore and zero/compatible unresolved work.
4. Start candidate API/frontend with workers/dequeues stopped; prove liveness/readiness, exact route partition, config/secret compatibility and controls false.
5. Start worker only after schema/runtime version checks; run private synthetic smoke and bounded soak. Do not call Gmail/provider or enable public ingress.
6. Record signed promotion result. Enabling any control/public route is a separate authenticated/versioned task with its own gate evidence.

Rollback pins the prior image/config/agent/runtime-compatible digest, stops new work, drains/version-routes in-flight workflows, and runs forward-compatible schema. Database restore is not normal application rollback and is used only under INFRA-04/05 after authoritative reconciliation.

## Ordered implementation tasks

- [ ] **Extend deterministic/deep CI gates —** Input: TEST coverage manifest and current jobs. Operation: add exact affected/full suites, strict skip policy, evidence upload and freshness checks. Output: reproducible PR/scheduled decisions. Test evidence: skipped/stale/tampered/missing lane negatives. Failure behavior: candidate blocked.
- [ ] **Build immutable supply-chain candidate —** Input: clean commit and locked dependencies. Operation: build once, scan, create SBOM/provenance/signatures and signed `ReleaseManifestV1`. Output: digest-addressed candidate. Test evidence: modified lock/image/manifest/signature and mutable-tag rejection. Failure behavior: publish no promotable manifest.
- [ ] **Implement safe migration/promotion ceremony —** Input: verified candidate, exact target, backup and runtime state. Operation: resolve target, verify compatibility, migrate/add, start without workers, smoke/soak, then start compatible worker. Output: signed promotion record. Test evidence: wrong target, stale backup, low disk, active ambiguity, incompatible runtime and migration-failure cases. Failure behavior: keep prior release/controls and stop candidate.
- [ ] **Implement application rollback —** Input: prior signed digest/config/runtime map. Operation: stop new work, route/drain, restore prior binaries/config and verify authoritative DB compatibility. Output: signed rollback release. Test evidence: mid-promotion crash and incompatible in-flight run cases. Failure behavior: stay stopped/degraded; invoke DR rather than force schema/history.
- [ ] **Exercise upgrade policy —** Input: dependency/base image/PostgreSQL/provider/model/KMS change. Operation: new lock/SBOM/contract/eval/recovery/restore evidence and canary promotion. Output: reviewed upgrade or rejection. Test evidence: PostgreSQL major upgrade clone, secret generation rotation, provider schema drift and rollback. Failure behavior: old supported version remains; affected capability paused if security support expires.

## Test strategy

- **CI `test_required_lane_skip_failure_or_stale_evidence_cannot_create_release_candidate`.**
- **Supply `test_release_manifest_rejects_dirty_tree_mutable_tag_bad_signature_sbom_or_provenance`.**
- **Manifest `test_release_binds_exact_46_66_64_plus_2_policy_incident_provider_runtime_and_agent_hashes`.**
- **Migration `test_additive_old_new_compatibility_and_worker_drain_precede_contract_change`.**
- **Promotion `test_vps_preflight_resolves_target_backup_capacity_controls_runs_and_ambiguities`.**
- **Rollback `test_prior_digest_restores_service_without_database_history_edit_or_provider_call`.**
- **Authority `test_release_or_rollback_never_enables_send_control_or_public_ingress`.**

## Security, privacy, compliance, idempotency, observability, and cost

CI tokens are least-privilege and short-lived; fork code receives no release/provider secret. Artifacts contain no `.env`, secret, PII or provider capture. Release/promotion uses idempotent release ID and target/current-version checks. Logs use digests/safe IDs only. Build/registry/scanner cost is measured; a vulnerability exception is signed, scoped and expiring and cannot waive a Critical authority/privacy/send/restore issue.

## Failure, rollback, and operator recovery

On compromised dependency/runner, signature failure, route drift, migration uncertainty, failed smoke/soak, new Critical alert or runtime mismatch: stop promotion, revoke CI/registry credentials if needed, retain prior release and both controls false, preserve signed evidence and execute IR-07/09. Roll back application digest/config; restore data only through INFRA-04. Never force-push a tag, mutate an image, stamp a migration or enable authority to test the candidate.

## Acceptance and retained evidence

- [ ] PR, scheduled, provider and release gates are explicit, complete and cannot false-pass unavailable infrastructure.
- [ ] Every promoted binary/config is digest-addressed, signed and bound to SBOM/provenance/contracts/tests/rollback.
- [ ] Promotion and rollback handle migrations/runtime versions/in-flight work without data-history mutation.
- [ ] CI/release has no path to send, publish the public pair or enable controls.

Retain workflow/action hashes, CI results, SBOM/provenance/signatures, scans/exceptions, release manifests, registry digests, target/preflight/migration/smoke/soak outputs, promotion/rollback/upgrade drill evidence and incidents.

## Dependencies and next deliverable

INFRA-02 consumes all TEST evidence and produces candidates for [INFRA-03 private VPS](03-private-vps-deployment.md). Successful promotion still needs INFRA-04/05 operational evidence for M8 and never grants M9 outreach/public ingress.
