# Controlled Internal Stack Launch

**Document ID:** LAUNCH-02
**Status:** Planned M8 private-operations gate; no product stack, private VPS, Cloudflare Access/Tunnel ingress, encrypted R2 backup, monitoring, operator auth, or internal launch exists today
**Milestone:** M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `LAUNCH-02-T01 <- LAUNCH-01-T06,INFRA-02-T04,INFRA-04-T06,OBS-02-T05,INFRA-05-T07,ARCH-01-T05,TEST-01-T02,TEST-01-T05,INFRA-03-T08; LAUNCH-02-T02 <- LAUNCH-02-T01,INFRA-02-T02,INFRA-04-T02; LAUNCH-02-T03 <- LAUNCH-02-T02; LAUNCH-02-T04 <- LAUNCH-02-T03,INFRA-03-T04,INFRA-04-T06,INFRA-05-T06,TEST-06-T04; LAUNCH-02-T05 <- LAUNCH-02-T04,WF-07-T04,WF-08-T04,WF-09-T04,TEST-05-T02`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
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

In scope: one signed release on one private VPS, exact PostgreSQL 18 target, private operator session, product API/UI/worker with provider egress and both send controls off, synthetic/internal workflows, exact instrument/incident observability closure, all 24 Task 7 command owners, `DR01..DR11`, application-encrypted Cloudflare R2 repository acceptance, off-host recovery material, clean restore, alert paths, upgrades/rollback, operator runbooks and evidence retention.

Non-goals: real recipients, Gmail sends, public unsubscribe publication, external users, performance theater beyond the registered load profile, multi-cloud compute/backup as a pre-revenue requirement, provider-side encryption as sole backup protection, automatic failover, agent policy/control decisions, concurrent experiment portfolio, or converting a private green dashboard into a production claim.

## Exact planned implementation surfaces

This phase creates no new endpoint, table, event, agent artifact, provider capability, service, incident, metric, DR scenario, or Task 7 command ID. It consumes exact canonical sets: complete declared product table set and owners, complete API/UI operation registry partitioned private plus the two still-absent public unsubscribe operations, registered metrics, 18 incident trigger/alert/runbook tuples, 24 Task 7 commands, 14 final-SEND denials, registered provider capability families and `DR01..DR11`. Cloudflare R2 is the sole required pre-revenue off-host repository and must pass the real `T7-R2-RECOVERY-ACCEPT` encrypted backup/restore/account-recovery matrix before M8. No second-cloud witness is an M8 prerequisite.

### Entry manifest and prerequisites

The signed immutable entry record binds literal phase `CONTROLLED_INTERNAL_STACK`, clean source/release/image/config/migration/OpenAPI/canonical-catalog hashes, `ReleaseManifestV1`, active agent `PromotionManifestV1` references, DBOS or mandatory Temporal runtime decision/version, exact model/prompt/tool/provider versions, VPS/database system identity, private ingress/auth/session configuration, secret/encryption generations without values, R2 account/bucket/credential-policy/encryption hashes, latest `BackupManifestV1`, off-host recovery-package hash, Task 7 command/profile/fixture hashes, M0-M7 gate refs, budgets/caps, expected controls/routes, operator signature, and start/expiry UTC.

| Entry prerequisite | Required evidence | Failure behavior |
| --- | --- | --- |
| Product gates | current M0-M7 records including LAUNCH-01, exact M1 runtime decision, table/operation/metric/incident/command/policy/provider/DR set-equality and no unresolved roadmap-contract blocker | no M8 entry |
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

The operator verifies the target and signed release, performs pre-backup and migration/runtime compatibility checks, promotes with workers/dequeues/provider egress off, confirms exact private routes and public absence, starts API/UI, then compatible workers with send paths denied. Each window records authoritative health, registered metrics, 18 routes, budgets/cost, backup/WAL/witness freshness, queue/run states, local-versus-sink counts and zero Gmail/public evidence. During the phase the operator executes the required load/security/chaos, alert, clean-restore and all applicable `DR01..DR11` rows on isolated targets, then rolls back and forward once by signed digest without data-history edits.

| Decision point | Exact rule |
| --- | --- |
| Success | all seven windows valid; at least 20 terminal runs; every applicable Task 7/M8 row exit `0`; fresh restore/AWS/alert/DR evidence; zero Critical/High unresolved incident; no authority/public/Gmail/data/cost violation |
| Immediate abort | control/public/route/catalog drift; any send/provider authority edge; wrong target; schema/runtime incompatibility; backup/R2 recovery ambiguity; restore/DR/alert failure; telemetry blindness; secret/PII leak; unreconciled cost; budget breach; or roadmap blocker discovered |
| Rollback/demotion | stop dequeues/workers, keep controls/public off, preserve evidence, return to prior signed release/config if compatible or isolated restore, open canonical incident and invalidate affected windows |
| Re-entry | exact incident/repair closure, new signed candidate/entry, rerun of every affected command, fresh restore/witness proof and seven new complete windows; prior green windows cannot be cherry-picked |
| Downstream unlock | M8 operational eligibility only; LAUNCH-03 still needs all recipient/legal/campaign/public-ingress evidence and a separate operator decision |

## Internal sales-state and six-phase evidence gate

M8 internal launch consumes all first six ordered sales evidence phases: synthetic pipeline, recorded providers, owned conversations, simulated objections/negotiation, owned test calendar, and checkpoint/global-learning/full campaign simulation. Require WF-07-T04, WF-08-T04, WF-09-T04, complete LAUNCH-01/TEST-04 evidence and TEST-05-T02 before signing the M8 exit. Earlier implementation fixtures do not replace their ordered phase execution.

The recovery/release evidence must bind the accepted OfferPackage/economics/claim hashes; approved agent configurations and GlobalStrategyPackage/StrategyActivation/rollback lineage; campaign/cohort ordinals, membership/query/hash, caps and frozen qualification/causal/evidence/metric versions; CheckpointEvidenceBundle/cutoff/decision/learning triggers; full conversation/reply/negotiation state and counters; BookingIntent/slot/confirmation/action/attempt/result/observation/notification state; current suppression/tombstones/legal-policy; immutable action authorizations/consumptions; costs/reservations; and all current control/checkpoint generations.

Internal deployment may run the complete synthetic funnel/dashboard/exception/calendar/strategy simulation with all real provider writes denied. Product and test Gmail/calendar controls remain false outside their separately signed isolated fixture windows. M8 does not count synthetic/owned evidence as real demand or authorize phase-7 real recipients.

Exercise release/rollback/restore with pending send/calendar attempts, checkpoint/learning triggers and cross-campaign activations. Preserve suppression/tombstones, commercial evidence and remaining capacities; no health check, deploy, restore, exception resolution or current strategy pointer can reopen admission. Sign exact table/API/provider/artifact/metric/event/incident/command sets from their owning manifests, with no obsolete fixed count shortcut. Retain Cloudflare Access/Tunnel private ingress, encrypted R2 recovery, DR01..DR11, paging, command and no-public-product-ingress safeguards.

## Ordered implementation tasks

<!-- roadmap-task id=LAUNCH-02-T01 milestone=M8 depends_on=LAUNCH-01-T06,INFRA-02-T04,INFRA-04-T06,OBS-02-T05,INFRA-05-T07,ARCH-01-T05,TEST-01-T02,TEST-01-T05,INFRA-03-T08 mode=serial locks=milestone-gate -->
- [ ] **Freeze the internal entry and authority-zero target —** Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: verify exact hashes/identities/caps and sign entry with both controls false/public absent; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: one immutable internal entry. Test evidence: stale, wrong-target, catalog drift, open incident and authority-edge negatives. Failure behavior: no promotion.
<!-- roadmap-task id=LAUNCH-02-T02 milestone=M8 depends_on=LAUNCH-02-T01,INFRA-02-T02,INFRA-04-T02 mode=serial locks=live-environment,milestone-gate -->
- [ ] **Promote the private candidate safely —** Input: signed candidate, additive migration and current backup; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: preflight, migrate, start API/UI then compatible workers with provider/send/public paths denied; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: private stack at exact digest. Test evidence: mid-promotion crash, incompatible workflow/schema, stale backup and rollback. Failure behavior: prior release or stopped state.
<!-- roadmap-task id=LAUNCH-02-T03 milestone=M8 depends_on=LAUNCH-02-T02 mode=serial locks=live-environment,milestone-gate -->
- [ ] **Run bounded synthetic/internal operations —** Input: immutable briefs/configs and exact budgets; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: schedule at most the envelope, produce typed artifacts/evaluations and compare authoritative state/metrics/cost daily; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: seven-window operational record. Test evidence: cap/concurrency/replay/cost/privacy/zero-Gmail assertions. Failure behavior: abort and invalidate affected windows.
<!-- roadmap-task id=LAUNCH-02-T04 milestone=M8 depends_on=LAUNCH-02-T03,INFRA-03-T04,INFRA-04-T06,INFRA-05-T06,TEST-06-T04 mode=serial locks=backup-restore,live-environment,milestone-gate -->
- [ ] **Prove restore, witness, alerts and DR —** Input: Task-7 profiles, isolated targets, accepted AWS S3 identity, INFRA-04 restore evidence, INFRA-05 DR harness/report, and TEST-06 recovery-time/data-loss measurements; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: execute clean restore, split-stage alert paths, load/security/chaos and exactly `DR01..DR11`; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed M8 recovery bundle. Test evidence: provider unavailable=`30`, integrity=`40`, unsafe target=`50`, partial external=`60` all reject. Failure behavior: M8 remains blocked.
<!-- roadmap-task id=LAUNCH-02-T05 milestone=M8 depends_on=LAUNCH-02-T04,WF-07-T04,WF-08-T04,WF-09-T04,TEST-05-T02 mode=serial locks=ci-release,live-environment,milestone-gate -->
- [ ] **Close rollback and M8 exit —** Input: all windows/commands/incidents/cost and release pointers; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: exercise signed rollback/forward, prove data/history/control/public invariants and sign pass/block; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: M8 gate record. Test evidence: missing/stale/larger-authority and automatic-enable negatives. Failure behavior: no M9 eligibility.

## Test strategy

- **Entry `test_internal_launch_requires_current_m0_through_m7_and_exact_closed_catalogs`.**
- **Authority `test_internal_stack_has_zero_real_recipient_gmail_send_and_public_operations`.**
- **Window `test_only_seven_complete_unchanged_windows_with_twenty_runs_can_exit_m8`.**
- **Recovery `test_real_aws_acceptance_clean_restore_and_dr01_through_dr11_all_fail_closed`.**
- **Visibility `test_exact_metric_incident_sets_direct_signal_and_ack_watchdog_match_authoritative_truth`.**
- **Rollback `test_signed_prior_digest_recovers_without_history_edit_control_enable_or_public_publish`.**

## Security, privacy, compliance, idempotency, observability, and cost

Private ingress, OIDC/session, secrets/KMS, release signatures and least provider roles are mandatory. Synthetic/internal data contains no real recipient or secret and cannot become consent/legal authority. Idempotent commands and finite workflows preserve state under restart; notifications never mutate product truth. Metrics/logs/pages use safe bounded fields, never recipient hashes, addresses, content, credentials or AWS object paths. All paid calls reserve/reconcile original currency and ILS evidence; missing price/FX/invoice truth blocks work. AWS S3 witness evidence is read-only operational authority and never a business/send authority.

## Failure, rollback, and operator recovery

Contain first: both controls false, public DNS/edge absent, dequeue/provider egress stopped, affected credentials revoked, evidence preserved. Determine truth from PostgreSQL, signed release/backup/R2 manifests and provider records rather than dashboards alone. Roll back application/config pointers only when schema/runtime compatibility is proven; otherwise remain stopped and use the exact DR row. No provider-side metadata can substitute for the signed application retention/deletion ledger or successful encrypted R2 restore evidence. Never use direct SQL, mutable tags, skipped windows, a stale restore, or a green foundation CI run to claim M8.

## Acceptance and retained evidence

- [ ] Entry binds exact release/target/runtime/config/provider/recovery identities and all canonical set hashes.
- [ ] Seven unchanged windows and at least 20 bounded runs retain zero real-recipient, Gmail-send, public-route or authority evidence.
- [ ] Real AWS S3 acceptance, clean restore, alert paths, all 24 command owners and `DR01..DR11` pass with honest unavailable/error semantics.
- [ ] Rollback/forward and exit leave both controls false, public pair absent, costs reconciled and no unresolved Critical/High incident.

Retain signed entry/exit, release/SBOM/provenance/image/config/migration hashes, per-window state/metric/cost comparisons, private-auth evidence, command manifests/exits, load/security/chaos traces, alerts/acks, backup/WAL/AWS head versions/ETags/checksums, restore/DR/rollback results, incidents and operator decisions. Retention follows SEC-06 after its audited duration conflict is resolved; until then affected expiry/prune actions fail closed.

## Dependencies and next deliverable

LAUNCH-02 consumes the full M0-M8 private stack. Passing it makes [LAUNCH-03](03-first-real-experiment.md) entry assembly eligible; it does not enable `PRODUCT_OUTREACH`, publish the public pair, establish legal compliance, prove recipient consent, or authorize Gmail.
