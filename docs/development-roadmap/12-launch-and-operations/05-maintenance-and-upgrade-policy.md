# Maintenance and Upgrade Policy

**Document ID:** LAUNCH-05
**Status:** Planned M8-M9 operating control; current foundation CI/locks exist, but no production release, advisory automation, canary, backup, AWS witness, legal refresh or maintenance evidence exists
**Milestone:** M8 private operations and M9 bounded real-recipient maintenance
**Owner:** Solo operator; qualified counsel owns legal conclusions and each provider owner supplies external change evidence
**Prerequisites:** [INFRA-02 release process](../11-infrastructure/02-ci-cd-and-release-process.md), [INFRA-04 backup/restore](../11-infrastructure/04-postgresql-backups-and-restores.md), [INFRA-05 monitoring/DR](../11-infrastructure/05-monitoring-and-disaster-recovery.md), [OBS-04 evaluations](../09-observability-and-evaluation/04-agent-and-workflow-evaluations.md), SEC-03/04/06 and exact Task 7 command registry
**Outputs:** Dependency/advisory cadence, pinned-candidate protocol, schema/runtime/model/prompt/provider/legal change gates, canary/rollback/restore rules, end-of-life decisions, evidence retention and solo-operator emergency path
**Unlocks:** Continued use of only the exact release/capability whose evidence remains current; no maintenance action grants send, legal, approval, public-ingress or autonomy authority
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Maintenance prevents a green launch from rotting into an unexamined liability. Every change creates a new immutable candidate bound to locks, images, migrations, API/catalog hashes, agent/runtime/provider configurations, tests, backup/restore evidence and rollback target. A version bump is not clerical: it is a new safety claim with a defined blast radius.

Cadences below are operational controls, not fake delivery estimates. Missing a required review expires the affected evidence and disables or freezes that capability; it never creates an “accepted risk by silence.” A solo operator is allowed to keep a capability off instead of racing an unsafe patch.

## Current repository state

The foundation pins Python packages in `backend/uv.lock`, npm packages in `frontend/package-lock.json`, uv `0.11.26`, Next.js `16.3.3`, DBOS `2.31.0`, and Pydantic AI/Evals `2.35.3`; Python is constrained to `>=3.13,<3.14` and Node to `>=24,<25`. CI uses PostgreSQL `18`, and Dockerfiles currently use floating `python:3.13-slim-bookworm` and `node:24-alpine` base tags; production release digests do not exist. No automated SBOM/advisory decision, signed exception, canary, production migration, model/provider capture, legal-source refresh, AWS account/bucket, restore drill or end-of-life record exists.

## Scope and non-goals

In scope: Python/npm/OS/container/PostgreSQL dependencies; GitHub Actions; DBOS/Pydantic AI/Evals; model/prompt/tool/schema/validator; six provider capability contracts and Gmail API/policies; FastAPI/OpenAPI/Next.js; application and DBOS system migrations; AWS S3 witness/data semantics; legal/policy/source review; SBOM/advisories; canary/rollback/restore; secret/key rotation; end-of-life; retention and emergency operations.

Non-goals: automatic dependency merging/deployment, mutable tags in release evidence, direct production experiments with unreviewed versions, weakening a test to fit an upgrade, migration downgrade as normal rollback, live model traffic as the only evaluation, provider status as business authority, legal conclusions from an RSS feed, or keeping an unsupported component active because replacement is inconvenient.

## Exact planned implementation surfaces

No new product endpoint, table, event, artifact, provider capability, service, metric, incident, DR scenario or Task 7 command is introduced. Maintenance uses existing lockfiles/workflows; `ReleaseManifestV1`, `PromotionManifestV1`, `BackupManifestV1` and signed gate records; the 24 Task 7 command IDs; 46/66/39/18/14/6/`DR01..DR11` set hashes; and canonical release/incident/repair owners. Planned INFRA-02 release scripts own candidate/preflight/apply/rollback; AGENT-10/OBS-04 own agent/provider evaluation; INFRA-04/05 own restore/AWS witness/DR.

### Dated primary-source advisory baseline

This snapshot was reviewed on 2026-08-29 and must be replaced by fresh source evidence at each cadence; it is not proof a deployment is patched.

| Surface and repository truth | Current primary source signal reviewed | Required disposition before M8/M9 |
| --- | --- | --- |
| Python `>=3.13,<3.14`; floating `python:3.13-slim-bookworm` | [Python 3.13.15](https://www.python.org/downloads/release/python-31315/) is the 2026-08-05 maintenance release | select exact supported patch/base-image digest, SBOM/signature/compatibility tests; floating tag cannot enter `ReleaseManifestV1` |
| Node `>=24,<25`; floating `node:24-alpine` | [Node 24.17.0](https://nodejs.org/en/blog/release/v24.17.0) is a security release and the [Node vulnerability feed](https://nodejs.org/en/blog/vulnerability/) is authoritative | select exact supported patch/base digest and rerun npm/build/browser/container evidence |
| Next.js lock `16.3.3` | official [August 2026 security release](https://nextjs.org/blog) names `16.3.3` as the Active-LTS patch for two Critical issues | retain exact lock/image/SBOM evidence; any downgrade or changed advisory scope blocks release |
| PostgreSQL major tag `18` | official [PostgreSQL 18 security page](https://www.postgresql.org/support/security/18/) and [18.6 notes](https://www.postgresql.org/docs/current/release-18-6.html) list current fixes and post-update checks | pin exact minor/image digest for a candidate; run real PostgreSQL 18 migration/backup/PITR/extension/index checks before promotion |
| Pydantic AI/Evals lock `2.35.3` | official [project advisories](https://github.com/pydantic/pydantic-ai/security/advisories) include 2026 URL/telemetry/UI adapter issues; the August telemetry advisory is fixed in `2.27.1` or later | map every advisory to used features, prove version range, scan prior traces where applicable, rerun all affected eight-suite cases × three captures and privacy tests |
| DBOS lock `2.31.0` | official [DBOS Python releases](https://github.com/dbos-inc/dbos-transact-py/releases) are the change source; security/advisory absence is never inferred from a stale search | review every intervening runtime/schema/recovery change and rerun M1 plus affected workflow/version/queue matrix; any canonical disqualifier mandates Temporal |
| Gmail | official [Gmail release notes](https://developers.google.com/workspace/gmail/release-notes), [quota page](https://developers.google.com/workspace/gmail/api/reference/quota) and [Workspace API user-data policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy) show current quota/policy changes | reapprove scopes/use/terms/quotas/Google review, adapter fixtures and budgets; uncertainty keeps mailbox/product off |
| AWS S3 witness/repo 2 | [AWS security bulletins](https://aws.amazon.com/security/security-bulletins/rss/) and [S3 security guidance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security.html) are current inputs | rerun the real `eu-central-1` acceptance matrix after SDK/IAM/policy/Object-Lock/conditional-write/account changes; emulator evidence never counts |

The GitHub Advisory Database, OS/base-image vendor advisories, lockfile ecosystem audits and signed SBOM scanner results supplement these primary owners but do not override them. An “unaffected” decision records component/version, reachable feature/path, advisory/CVE/GHSA, source access time, reviewer, evidence and expiry.

### Cadence and severity response

| Cadence/trigger | Exact control | Failure/expiry action |
| --- | --- | --- |
| every PR/commit | locked resolve, secret/license/vulnerability/SBOM diff, generated API drift, impacted deterministic/contract tests, action SHA and base-image digest review | no candidate |
| daily while operated | backup/WAL/telemetry/control/cost/incident freshness; AWS authority head read every 5 minutes and readiness expires after 15 minutes | affected controls/public/restore/purge authority off per canonical runbook |
| weekly | dependency/advisory/release/source review; full deterministic fixture/workflow smoke; supported-runtime/EOL horizon | open maintenance record; freeze affected promotion/release if overdue |
| monthly | alert path exercise; provider price/quota/API/model drift; legal/Google/source-access review; dependency/license exception review | current policy/provider evidence expires; affected capability disabled |
| quarterly | IR/contact/channel rotation, key/custody recovery, destructive DR rotation and clean restore at least once every 90 days | M8 evidence expires; M9 and restore/cutover blocked |
| Critical or known exploitation/authority/privacy impact | triage in the same operator session before any further affected use; immediately disable/contain, then patch/rollback or keep off | no grace period and no exception while exposed |
| High | triage within 48 hours; patch through the full affected gate within 7 days or disable the component | signed disable is safer than an unverified emergency deploy |
| Medium | triage in the next weekly review and resolve in the next monthly candidate or record scoped expiring exception | exception cannot cover send/authority/privacy/restore invariants |
| Low | triage quarterly; batch only with independent rollback/evidence | unsupported/EOL status still overrides Low severity |
| provider/model/prompt/API/policy notice or observed drift | invalidate affected fixtures/evals/approvals immediately and open a new candidate regardless of cadence | no new affected runs/sends until requalified |

### Change classes, canary, rollback and restore

| Change | Required evidence before promotion | Rollback/recovery rule |
| --- | --- | --- |
| ordinary Python/npm/OS/container dependency | new locks/image digest/SBOM/provenance, advisory/license decision, full build plus affected tests and private canary | prior signed digest/config if schema-compatible; otherwise stay stopped |
| PostgreSQL minor | isolated clone, migration/extension/index/update-note checks, backup/PITR/46-table integrity and old/new application compatibility | application rollback only if DB compatibility proven; restore is incident path, not downgrade |
| PostgreSQL major | parallel clean target, `pg_upgrade` or dump/restore plan, full restore/DR/performance/invariant evidence and cutover rehearsal | no in-place guess; retain old cluster read-only until signed cutover/rollback expiry |
| application/product migration | expand/migrate/contract discipline, old/new writers, active workflow drain/version routing, pre-backup and row/constraint/event hashes | roll back binaries/config with forward-compatible schema; never reverse destructive history automatically |
| DBOS/runtime | isolated DBOS system-schema migration, M1 `K0..K8`, all eight criteria, queue/rate/version/recovery and application-level Gmail ambiguity matrix | any disqualifying DBOS result permanently selects Temporal before product workflow work |
| Pydantic AI/model/prompt/tool/schema/validator/provider | all affected exact suites × three fresh captures, deterministic scoring twice, provider fixture/result/ledger/cost/privacy parity, operator `PromotionManifestV1` | prior compatible promoted pointer; pause stage when compatibility uncertain |
| Gmail/search/page/enrichment API or terms/price/quota | recorded fixture refresh, exact six-family contract, scope/terms/legal/cost review, zero-hidden-retry and bounded live capture where authorized | select `DISABLED`/prior operation for new runs; preserve observations and reconcile possible calls |
| AWS S3 SDK/IAM/bucket/Object-Lock/conditional-write/account | full non-emulator `T7-AWS-WITNESS-ACCEPT`, repo-2 backup/WAL/restore, package/account-lockout and head ambiguity matrix | no fallback authority; unavailable=`30`, integrity=`40`, remain off |
| legal/policy/source/disclosure/consent schema | counsel-scoped review, fresh sources/access dates, new immutable policy/templates and reapproval of affected messages/cohort | product control false; old policy remains historical only |

Every candidate first runs deterministic/offline lanes, then isolated real-database/recovery lanes, then private canary with both send controls/public off. A Gmail/provider canary uses only explicitly authorized owned test resources; it creates no M9 evidence. A real-recipient version change requires a new LAUNCH-03 entry and individual approvals, never an in-place canary.

### End-of-life, retention and solo-operator emergency path

Support/EOL dates are recorded for language/runtime/database/OS/base image/framework/provider API/model and critical actions. At 180 days before known EOL, open a replacement candidate; at 90 days, block unrelated feature promotion; at EOL, disable or isolate the unsupported component unless a signed upstream-supported extension exists. A self-written exception is not vendor support.

Maintenance evidence follows SEC-06 classes and incident/legal/accounting holds. Superseded locks/images/configs/manifests/signatures/migration/restore/authority proofs remain long enough to reproduce and roll back the supported window; raw personal/provider content is minimized independently. No maintenance cleanup may delete unresolved attempt, suppression, complaint, incident, audit, cost, promotion, deletion-authority or restore evidence. The audited `SAFETY_LONG` versus 30-day terminated-session conflict must be canonically resolved before session pruning or M8 retention acceptance.

If the operator is unavailable, automated freshness guards may only reduce authority: set affected controls false, stop schedules/dequeues, leave the public pair available only when its suppression dependency remains proven, spool/page through the independent path and preserve evidence. Offline recovery uses the VPS/provider consoles, separately held recovery material and exact incident/DR runbook. Emergency work never skips target guards, performs blind provider retry, edits SQL, raises a cap, accepts legal risk, deletes evidence, restores/cuts over without fresh AWS head proof, or re-enables automatically. If safe repair exceeds solo capacity, keep the capability off and engage the appropriate vendor, security specialist or counsel.

## Ordered implementation tasks

- [ ] **Build the advisory and inventory review —** Input: locks, image/action digests, SBOM, primary owner feeds and EOL registry. Operation: correlate reachable components, record affected/unaffected evidence and severity deadline. Output: complete maintenance queue. Test evidence: stale feed, transitive dependency, false-unaffected and missing-SBOM cases. Failure behavior: affected candidate/capability blocked.
- [ ] **Produce pinned immutable candidates —** Input: approved change set and prior rollback target. Operation: update exact locks/digests, build once, sign SBOM/provenance/`ReleaseManifestV1` and keep controls/public off. Output: reproducible candidate. Test evidence: floating/mutable tag, dirty tree, missing signature/license/advisory decision rejection. Failure behavior: prior version remains.
- [ ] **Run class-specific migrations/evaluations —** Input: candidate and change-class matrix. Operation: execute exact PostgreSQL/runtime/agent/provider/legal/AWS gates and record all command exits/artifacts. Output: scoped promotion evidence. Test evidence: unavailable, partial, stale, incompatible and hard-safety negatives. Failure behavior: disable or reject; never average away.
- [ ] **Canary, promote and prove rollback/restore —** Input: signed candidate, clean target, backup and rollback target. Operation: deterministic then isolated then private canary, promote by digest, soak, rollback/forward and restore where required. Output: signed acceptance or rejection. Test evidence: mid-migration/deploy, schema/runtime drift, alert, backup and authority-head failures. Failure behavior: stopped/prior release and incident.
- [ ] **Operate cadence, EOL and emergency controls —** Input: daily/weekly/monthly/quarterly schedule, notices and freshness. Operation: expire evidence, reduce authority, execute drills/rotations and escalate beyond solo capacity. Output: current supported operating bound. Test evidence: missed cadence, operator-unavailable, EOL and automatic-reenable negatives. Failure behavior: capability remains off.

## Test strategy

- **Inventory `test_every_lock_image_action_provider_model_policy_and_runtime_has_owner_source_version_and_eol`.**
- **Advisory `test_critical_high_medium_low_cadence_expires_or_disables_exact_affected_capability`.**
- **Migration `test_postgresql_application_dbos_and_agent_changes_run_their_complete_distinct_gates`.**
- **Provider `test_model_prompt_tool_gmail_api_or_policy_change_invalidates_fixture_promotion_and_message_approval`.**
- **AWS `test_witness_change_requires_real_eu_central_1_acceptance_and_never_accepts_emulator_or_gcs_substitution`.**
- **Emergency `test_solo_operator_absence_can_only_reduce_authority_and_never_auto_reenable_or_delete_evidence`.**

## Security, privacy, compliance, idempotency, observability, and cost

Update automation receives read-only discovery and candidate-build authority, never deployment/runtime/provider secrets or business authority. Advisory and SBOM outputs exclude secrets/PII; exceptions are signed, scoped and expiring. Candidate/promotion commands are idempotent by exact source/target/version and reject replay against drift. Telemetry measures review freshness, candidate/gate outcome, vulnerable reachability, rollback/restore and spend with bounded labels. Every upgrade reserves direct provider/cloud/operator-time budget; sunk upgrade cost cannot waive a gate.

## Failure, rollback, and operator recovery

On compromised supply chain, incompatible migration, failing evaluation, provider drift, bad canary, new alert, restore/AWS uncertainty or legal-policy expiry: stop promotion, disable affected capability/controls/public path as required, preserve artifacts and use the prior signed compatible pointer. Revoke CI/registry/provider credentials when exposed. Restore only through INFRA-04/05 and reconcile all side effects first. Never force a version, stamp migration history, mutate an image/tag, suppress a scanner finding without reachability evidence, or delete the evidence that explains rollback.

## Acceptance and retained evidence

- [ ] Every maintained surface has an exact source/version/owner/cadence/severity/EOL and change-class gate.
- [ ] Candidates are pinned, signed, tested and canaried with compatible rollback/restore before promotion.
- [ ] DBOS/Pydantic AI/model/prompt/provider/API/AWS/legal changes invalidate exactly the affected evidence and never widen authority.
- [ ] Cadence expiry and solo emergency response reduce authority, preserve evidence and require separate re-entry.

Retain inventory/SBOM/provenance/lock/image/action hashes, advisory/source snapshots and decisions, exceptions/expiry, migration/eval/provider/legal/AWS matrices, command outputs, backup/restore/canary/soak/rollback evidence, costs, incidents, credential rotations, EOL plans and operator/vendor/counsel approvals. Retention conflicts fail closed rather than choosing a convenient duration.

## Dependencies and next deliverable

LAUNCH-05 governs every operated level from M8 onward and can revoke evidence for LAUNCH-02/03/04. There is no final “maintenance complete” state: the only unlocked outcome is continued bounded operation of a currently supported, exactly evidenced version.
