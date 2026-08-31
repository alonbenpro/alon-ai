# Controlled Internal Stack Launch

**Document ID:** LAUNCH-02
**Status:** Planned M8 private-operations gate; no product stack, VPS, AWS witness, backup, monitoring, operator auth, or internal launch exists today
**Milestone:** M8
**Owner:** Solo operator
**Prerequisites:** Passing M0-M7 including [LAUNCH-01](01-test-inbox-pilot.md); [release process](../11-infrastructure/02-ci-cd-and-release-process.md); [private VPS](../11-infrastructure/03-private-vps-deployment.md); [backup/restore](../11-infrastructure/04-postgresql-backups-and-restores.md); [monitoring/DR](../11-infrastructure/05-monitoring-and-disaster-recovery.md); all Task 7 command and canonical-contract audits
**Outputs:** Signed private-stack entry and M8 exit records, synthetic/internal run evidence, operational observation windows, restore/DR/security/alert results, rollback proof, and explicit M9 block or eligibility decision
**Unlocks:** Eligibility to assemble [LAUNCH-03 first-real-experiment](03-first-real-experiment.md) entry evidence; never Gmail or recipient authority
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

The controlled internal launch proves that one Israeli operator can privately deploy, observe, stop, upgrade, restore, and diagnose the complete stack without a real recipient. It is an operational launch, not a public or commercial launch. Both send controls remain false, the sole public unsubscribe pair remains absent, and all data/addresses/test resources remain operator-controlled or synthetic.

The observation window is seven consecutive complete 24-hour evidence windows after the last release, restore, configuration, model/prompt/provider, policy, or topology change. This is an operational stability control, not a delivery estimate. Any invalidated window restarts the seven-window count after correction and a new signed entry.

## Current repository state

Only the foundation application, CI and Compose exist. Product DBOS/Gmail/schema/API/UI, private authentication, VPS topology, Google/AWS storage, backups, public edge, telemetry, paging, Task 7 runner and DR execution remain planned. The immutable green foundation CI run at commit `8081008d13adfc7e8a09ee104e2bf54c37187e0b` is unchanged-product baseline evidence only; it did not test this roadmap branch or any planned M8 product system.

## Scope and non-goals

In scope: one signed release on one private VPS, exact PostgreSQL 18 target, private operator session, product API/UI/worker with provider egress and both send controls off, synthetic/internal workflows, 39-instrument/18-incident observability closure, all 24 Task 7 command owners, `DR01..DR11`, encrypted GCS plus selected AWS S3 `eu-central-1` repository/witness acceptance, clean restore, alert paths, upgrades/rollback, operator runbooks and evidence retention.

Non-goals: real recipients, Gmail sends, public unsubscribe publication, external users, performance theater beyond the registered load profile, hot multi-cloud compute, GCS as deletion authority, automatic failover, agent policy/control decisions, concurrent experiment portfolio, or converting a private green dashboard into a production claim.

## Exact planned implementation surfaces

This phase creates no new endpoint, table, event, agent artifact, provider capability, service, incident, metric, DR scenario, or Task 7 command ID. It consumes exact canonical sets: 46 product tables and owners, 66 API/UI operations partitioned 64 private plus the two still-absent public unsubscribe operations, 39 metrics, 18 incident trigger/alert/runbook tuples, 24 Task 7 commands, 14 final-SEND denials, six provider capability families and `DR01..DR11`. AWS S3 is the sole off-Google repo-2/deletion witness and must pass the real, non-emulator `T7-AWS-WITNESS-ACCEPT` matrix in `eu-central-1` before M8.

### Entry manifest and prerequisites

The signed immutable entry record binds literal phase `CONTROLLED_INTERNAL_STACK`, clean source/release/image/config/migration/OpenAPI/canonical-catalog hashes, `ReleaseManifestV1`, active agent `PromotionManifestV1` references, DBOS or mandatory Temporal runtime decision/version, exact model/prompt/tool/provider versions, VPS/database system identity, private ingress/auth/session configuration, secret/KMS generations without values, GCS/AWS account-region-bucket-policy/IAM hashes, latest `BackupManifestV1`, sole AWS authority-head exact version/ETag/checksum, Task 7 command/profile/fixture hashes, M0-M7 gate refs, budgets/caps, expected controls/routes, operator signature, and start/expiry UTC.

| Entry prerequisite | Required evidence | Failure behavior |
| --- | --- | --- |
| Product gates | current M0-M7 records including LAUNCH-01, exact M1 runtime decision, 46/66/39/18/24/14/6/DR set-equality and no unresolved roadmap-contract blocker | no M8 entry |
| Release/target | signed digest-addressed candidate, additive migration compatibility, exact clean target, private identity and capacity preflight | prior release remains; no promotion |
| Data recovery | current dual-repository backup evidence, accepted real AWS S3 witness, independent recovery packages and a successful clean isolated restore no older than 90 days | services/workers/controls/public stay off |
| Visibility/recovery | direct Critical signal, collector-to-PagerDuty acknowledgement watchdog, local offline path, exact incident routes and DR prerequisites | no worker start; M8 blocked |
| Authority boundary | `TEST_INBOX_SENDING=false`, `PRODUCT_OUTREACH=false`, provider/Gmail send egress denied, public pair absent, no real-address fixture | unsafe target refusal before mutation |

### Execution envelope and operator steps

| Bound | Exact internal-launch value |
| --- | --- |
| Target | one signed release, one private VPS, one PostgreSQL system, one configured operator identity |
| Observation | seven consecutive complete 24-hour windows; at least 20 synthetic/internal terminal workflow runs |
| Work cap | at most 10 internal workflow starts per window, 40 total and 2 concurrently active |
| Recipients/Gmail | zero real recipients and zero Gmail send calls; owned aliases from M6 are not reused as M8 evidence |
| Public surface | zero public operations published; the scanner-safe GET/POST pair remains disabled and absent |
| Provider/cost | only entry-manifest allowlisted research/evaluation calls under exact per-call/run/experiment/product reservations; no paid-call admission with unknown price/FX/cost |
| Controls | both send controls false at startup, restore, every window boundary and exit |

The operator verifies the target and signed release, performs pre-backup and migration/runtime compatibility checks, promotes with workers/dequeues/provider egress off, confirms exact private routes and public absence, starts API/UI, then compatible workers with send paths denied. Each window records authoritative health, 39 metrics, 18 routes, budgets/cost, backup/WAL/witness freshness, queue/run states, local-versus-sink counts and zero Gmail/public evidence. During the phase the operator executes the required load/security/chaos, alert, clean-restore and all applicable `DR01..DR11` rows on isolated targets, then rolls back and forward once by signed digest without data-history edits.

| Decision point | Exact rule |
| --- | --- |
| Success | all seven windows valid; at least 20 terminal runs; every applicable Task 7/M8 row exit `0`; fresh restore/AWS/alert/DR evidence; zero Critical/High unresolved incident; no authority/public/Gmail/data/cost violation |
| Immediate abort | control/public/route/catalog drift; any send/provider authority edge; wrong target; schema/runtime incompatibility; backup/AWS witness ambiguity; restore/DR/alert failure; telemetry blindness; secret/PII leak; unreconciled cost; budget breach; or roadmap blocker discovered |
| Rollback/demotion | stop dequeues/workers, keep controls/public off, preserve evidence, return to prior signed release/config if compatible or isolated restore, open canonical incident and invalidate affected windows |
| Re-entry | exact incident/repair closure, new signed candidate/entry, rerun of every affected command, fresh restore/witness proof and seven new complete windows; prior green windows cannot be cherry-picked |
| Downstream unlock | M8 operational eligibility only; LAUNCH-03 still needs all recipient/legal/campaign/public-ingress evidence and a separate operator decision |

## Ordered implementation tasks

- [ ] **Freeze the internal entry and authority-zero target —** Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs. Operation: verify exact hashes/identities/caps and sign entry with both controls false/public absent. Output: one immutable internal entry. Test evidence: stale, wrong-target, catalog drift, open incident and authority-edge negatives. Failure behavior: no promotion.
- [ ] **Promote the private candidate safely —** Input: signed candidate, additive migration and current backup. Operation: preflight, migrate, start API/UI then compatible workers with provider/send/public paths denied. Output: private stack at exact digest. Test evidence: mid-promotion crash, incompatible workflow/schema, stale backup and rollback. Failure behavior: prior release or stopped state.
- [ ] **Run bounded synthetic/internal operations —** Input: immutable briefs/configs and exact budgets. Operation: schedule at most the envelope, produce typed artifacts/evaluations and compare authoritative state/metrics/cost daily. Output: seven-window operational record. Test evidence: cap/concurrency/replay/cost/privacy/zero-Gmail assertions. Failure behavior: abort and invalidate affected windows.
- [ ] **Prove restore, witness, alerts and DR —** Input: Task 7 profiles, isolated targets and real accepted AWS S3 identity. Operation: execute clean restore, split-stage alert paths, load/security/chaos and exactly `DR01..DR11`. Output: signed M8 recovery bundle. Test evidence: provider unavailable=`30`, integrity=`40`, unsafe target=`50`, partial external=`60` all reject. Failure behavior: M8 remains blocked.
- [ ] **Close rollback and M8 exit —** Input: all windows/commands/incidents/cost and release pointers. Operation: exercise signed rollback/forward, prove data/history/control/public invariants and sign pass/block. Output: M8 gate record. Test evidence: missing/stale/larger-authority and automatic-enable negatives. Failure behavior: no M9 eligibility.

## Test strategy

- **Entry `test_internal_launch_requires_current_m0_through_m7_and_exact_closed_catalogs`.**
- **Authority `test_internal_stack_has_zero_real_recipient_gmail_send_and_public_operations`.**
- **Window `test_only_seven_complete_unchanged_windows_with_twenty_runs_can_exit_m8`.**
- **Recovery `test_real_aws_acceptance_clean_restore_and_dr01_through_dr11_all_fail_closed`.**
- **Visibility `test_39_metrics_18_routes_direct_signal_and_ack_watchdog_match_authoritative_truth`.**
- **Rollback `test_signed_prior_digest_recovers_without_history_edit_control_enable_or_public_publish`.**

## Security, privacy, compliance, idempotency, observability, and cost

Private ingress, OIDC/session, secrets/KMS, release signatures and least provider roles are mandatory. Synthetic/internal data contains no real recipient or secret and cannot become consent/legal authority. Idempotent commands and finite workflows preserve state under restart; notifications never mutate product truth. Metrics/logs/pages use safe bounded fields, never recipient hashes, addresses, content, credentials or AWS object paths. All paid calls reserve/reconcile original currency and ILS evidence; missing price/FX/invoice truth blocks work. AWS S3 witness evidence is read-only operational authority and never a business/send authority.

## Failure, rollback, and operator recovery

Contain first: both controls false, public DNS/edge absent, dequeue/provider egress stopped, affected credentials revoked, evidence preserved. Determine truth from PostgreSQL, signed release/backup/AWS manifests and provider records rather than dashboards alone. Roll back application/config pointers only when schema/runtime compatibility is proven; otherwise remain stopped and use the exact DR row. GCS data cannot vote on or reconstruct AWS deletion commitment. Never use direct SQL, mutable tags, skipped windows, a stale restore, or a green foundation CI run to claim M8.

## Acceptance and retained evidence

- [ ] Entry binds exact release/target/runtime/config/provider/recovery identities and all canonical set hashes.
- [ ] Seven unchanged windows and at least 20 bounded runs retain zero real-recipient, Gmail-send, public-route or authority evidence.
- [ ] Real AWS S3 acceptance, clean restore, alert paths, all 24 command owners and `DR01..DR11` pass with honest unavailable/error semantics.
- [ ] Rollback/forward and exit leave both controls false, public pair absent, costs reconciled and no unresolved Critical/High incident.

Retain signed entry/exit, release/SBOM/provenance/image/config/migration hashes, per-window state/metric/cost comparisons, private-auth evidence, command manifests/exits, load/security/chaos traces, alerts/acks, backup/WAL/AWS head versions/ETags/checksums, restore/DR/rollback results, incidents and operator decisions. Retention follows SEC-06 after its audited duration conflict is resolved; until then affected expiry/prune actions fail closed.

## Dependencies and next deliverable

LAUNCH-02 consumes the full M0-M8 private stack. Passing it makes [LAUNCH-03](03-first-real-experiment.md) entry assembly eligible; it does not enable `PRODUCT_OUTREACH`, publish the public pair, establish legal compliance, prove recipient consent, or authorize Gmail.
