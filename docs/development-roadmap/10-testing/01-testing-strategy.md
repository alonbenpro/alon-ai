# Whole-System Testing Strategy and Evidence Ownership

**Document ID:** TEST-01
**Status:** Planned M8 testing program; current unit, readiness-integration, generated-contract, build, secret-scan, and Compose CI checks cover only the foundation
**Milestone:** M1-M8 evidence consolidation; M8 release gate
**Owner:** Solo operator; the same person may execute and review, but generated evidence and signed manifests must make self-review reproducible
**Prerequisites:** M0-M7 canonical contracts, [OBS-04 evaluation operations](../09-observability-and-evaluation/04-agent-and-workflow-evaluations.md), [OBS-05 incident exercises](../09-observability-and-evaluation/05-incident-response.md), and current CI/Compose foundation
**Outputs:** Test taxonomy, environment/isolation rules, fixture provenance, coverage registry, deterministic command lanes, evidence retention, and release-blocking ownership
**Unlocks:** TEST-02 through TEST-06, INFRA-02 promotion gates, and the M8 private-operations evidence bundle
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Every canonical contract has one named test owner, one environment, one authoritative fixture source, one executable command, one retained result, and one fail-closed release action. Passing a later or broader suite cannot waive a failed earlier gate. M1 DBOS acceptance, M6 Gmail safety, M8 restore/security, and M9 legal/public-ingress evidence remain separate necessary gates and never grant send authority by themselves.

## Current repository state

Implemented today: backend pytest unit/integration markers, Ruff, Pyright, Alembic upgrade, frontend Vitest/Testing Library, ESLint/TypeScript/build, generated OpenAPI drift rejection, tracked-secret scan, and a GitHub Actions Compose build/smoke job. The local Compose stack is PostgreSQL/API/idle worker/frontend on loopback with outreach false. There is no 46-table product schema, DBOS workflow, Temporal adapter, Gmail/OAuth implementation, agent/evaluation runtime, product UI, browser E2E runner, load/chaos harness, backup/PITR system, public unsubscribe ingress, VPS, KMS/secret manager, or exercised DR. Planned test names below are acceptance contracts, not passing claims.

## Scope and non-goals

In scope: strict schemas/digests, all database objects, API 64+2 partition, policies and 14 dedicated final-SEND denials, finite workflows, runtime kill/replay/version behavior, providers/agents/evals, Gmail/OAuth, browser/accessibility, load/rate/budget, security/privacy/supply chain, backup/restore, fixture governance, flake handling, and evidence. Non-goals: mocking PostgreSQL where constraints matter, treating code coverage as assurance, live provider calls in ordinary CI, retrying flaky safety tests until green, production-data fixtures, destructive tests against shared/live targets, or inventing a second contract registry.

## Exact planned implementation surfaces

Create `tests/README.md`, `tests/manifests/coverage.v1.json`, `tests/fixtures/README.md`, `tests/evidence/schema.v1.json`, backend `tests/{contract,integration,recovery,security,load}`, frontend `tests/{contract,e2e,accessibility}`, `scripts/test_manifest.py`, and CI lanes from TEST-02..06. `coverage.v1.json` uses keys `{requirement_id,canonical_source,owner,suite,environment,fixture_manifest,command,evidence_schema,retention_class,release_action}`; `requirement_id` is stable and duplicates/missing sources fail.

| Lane | Environment and isolation | Network/provider rule | Required evidence | Failure action |
| --- | --- | --- | --- | --- |
| PR deterministic | ephemeral PostgreSQL 18 database per job; network denied after dependency install | signed synthetic/recorded fixtures only | JUnit, schema/manifest diffs, seed, commit and dependency hashes | block PR |
| PR container | disposable Compose project and volume with random project name | health endpoints only; no provider credential | image digests, service health, migration head, outreach-off proof | block PR |
| scheduled recovery/security | dedicated runner; fresh database/schema and disposable secret fixture store | allow only explicit local fault endpoints | kill matrix, row/event/call counts, canary scans | open test incident; block release |
| M1/M6 controlled provider | isolated Google project, owned aliases, separate credentials/schema, hard send cap | Gmail only through canonical gateway; M1 exact two-table harness | signed canonical evidence defined by WF-01/M6 | controls false; Temporal after any M1 disqualifier |
| release/M8 | clean restore host distinct from writers plus immutable candidate image | no Gmail/provider during restore; managed telemetry test only | release/SBOM/provenance, restore, runbook, browser and capacity bundle | no promotion |
| M9 public boundary | disposable public hostname/ruleset; synthetic opaque tokens | only exact unsubscribe GET/POST exposed | 64/2 route diff, scanner/abuse/WAF/redaction traces | public pair absent; product outreach false |

Fixture manifests bind schema version, source type `SYNTHETIC|RECORDED_REDACTED|OWNED_PROVIDER_CAPTURE`, generator commit, canonical request/result hashes, capture UTC, source/license/policy reference, sensitivity, redaction review, signing key ID and signature. Any byte change creates a new fixture version. CI rejects real addresses, credentials, raw provider bodies, unsigned captures, and fixture use outside its permitted lane.

Evidence directories are run-scoped and immutable after signing: `evidence/{gate}/{UTC}-{commit}-{run_id}/manifest.json`. The manifest records exact commands/exit codes, OS/runtime/dependency/image/schema/config hashes, environment classification, fixture IDs, test counts/skips/retries, artifact hashes, start/end UTC and operator signature. A skip, xfail, retry, missing artifact, clock anomaly, or partial upload is a non-pass unless the owning canonical requirement explicitly declares it inapplicable.

### Closed command manifest

`tests/manifests/task7-commands.v1.json` is the sole planned executable-command registry. Every row has `{command_id,argv,cwd,owner,lane,profile,fixture_manifest,target_guard,required_inputs,evidence_files,destructive,exit_semantics}`; `cwd` is the script-derived repository root, `argv` is an array executed without a shell, and the manifest plus every referenced fixture/profile is content-addressed in the run evidence. `scripts/task7/run` is planned, not currently present. It accepts only a listed command and invokes it from the manifest; unknown IDs, changed argv, an unavailable dependency/provider, or a missing artifact cannot pass.

Every row's `argv[0]` is the canonical absolute real path formed from the lane's signed checkout identity plus `/scripts/task7/run`; relative invocation is invalid. The remaining exact argv is `--manifest tests/manifests/task7-commands.v1.json --command COMMAND_ID --run-id "$TASK7_RUN_ID" --evidence-root "$TASK7_EVIDENCE_ROOT" --profile PROFILE --target-manifest "$TASK7_TARGET_MANIFEST"`; destructive rows append `--confirm "$TASK7_CONFIRMATION"`. `COMMAND_ID` and `PROFILE` are the literal values in one table row. The physical runner derives root only from the canonical absolute `${BASH_SOURCE[0]}`, rejects any symlink/noncanonical/escape, calculates the physical directory two levels above itself, runs `git -C "$SCRIPT_DERIVED_ROOT" rev-parse --show-toplevel`, and requires exact equality. It then verifies the signed `tests/manifests/repository-identity.v1.json`, expected commit and exact profile/fixture hashes before reading a target manifest or opening any target connection. Caller cwd plus `TASK7_REPO_ROOT|REPO_ROOT|GIT_DIR|GIT_WORK_TREE` cannot select a root.

Profile and fixture paths are exactly `tests/profiles/task7/PROFILE.v1.json` and `tests/fixtures/task7/PROFILE.v1.json` under that derived root (a signed `NO_EXTERNAL_FIXTURE` manifest when none is needed). Required environment is immutable: `TASK7_RUN_ID` matches `^[A-Z0-9][A-Z0-9_-]{7,63}$`; `TASK7_EVIDENCE_ROOT` is a new absolute run-owned directory; the signed target manifest names environment, host, database, PostgreSQL system identifier, Compose project or release digest, or literal target kind `STATIC_NO_TARGET`; and confirmation is lowercase SHA-256 of RFC 8785 JSON `{command_id,run_id,target_kind,target_id,target_system_id}`. Credentials are secret references, never environment values. The guard independently queries every live target and requires exact manifest equality, a disposable/isolated classification for destructive tests, outreach false, and zero active writers; static rows require the signed no-target manifest and perform no cleanup. Exit codes are closed: `0` complete pass; `10` assertion failure; `20` preflight/root/identity/config failure; `30` dependency/provider unavailable (**not a pass**); `40` evidence/integrity failure; `50` unsafe or unconfirmed target refusal; `60` partial/ambiguous external outcome requiring recovery. Signals or any other exit code fail. Only `0` with every row's declared artifact counts.

| Command ID | Owner / lane | Profile and exact invocation substitution | Required artifact |
| --- | --- | --- | --- |
| `T7-DOC-CONTRACT` | operator / PR deterministic | `DOCS_LOCKED`; substitute `COMMAND_ID=T7-DOC-CONTRACT`, `PROFILE=DOCS_LOCKED` | source-anchor/link/terminology/count/command equality, sole-B2-authority/head/provider-survival equality, plus Bash/cwd/symlink/root/commit/profile-negative JSON |
| `T7-CONTRACT-INTEGRATION` | operator / PR deterministic | `PG_EPHEMERAL`; `T7-CONTRACT-INTEGRATION`, `PG_EPHEMERAL` | catalog/OpenAPI/policy/incident JUnit plus hashes |
| `T7-WORKFLOW-RECOVERY` | operator / scheduled recovery | `DBOS_EPHEMERAL`; `T7-WORKFLOW-RECOVERY`, `DBOS_EPHEMERAL` | finite-state/kill-point/version/Temporal evidence |
| `T7-GMAIL-OFFLINE` | operator / PR deterministic | `GMAIL_RECORDED`; `T7-GMAIL-OFFLINE`, `GMAIL_RECORDED` | union/ambiguity/reconciliation/OAuth-saga JUnit |
| `T7-GMAIL-LIVE` | operator / M6 controlled provider | `GMAIL_OWNED_ALIAS`; `T7-GMAIL-LIVE`, `GMAIL_OWNED_ALIAS` | signed capped provider transcript and call/send counts |
| `T7-BROWSER-PRIVATE` | operator / release M8 | `BROWSER_PRIVATE`; `T7-BROWSER-PRIVATE`, `BROWSER_PRIVATE` | Playwright, axe, viewport, trace and screenshot bundle |
| `T7-BROWSER-PUBLIC` | operator / M9 public boundary | `BROWSER_PUBLIC_M9`; `T7-BROWSER-PUBLIC`, `BROWSER_PUBLIC_M9` | scanner/GET-write-zero/POST/WAF/redaction evidence |
| `T7-LOAD` | operator / release M8 | `LOAD_ISOLATED`; `T7-LOAD`, `LOAD_ISOLATED` | workload, latency/error, database/rate/budget and stop proof |
| `T7-SECURITY-CHAOS` | operator / scheduled recovery/security | `SECURITY_CHAOS_ISOLATED`; `T7-SECURITY-CHAOS`, `SECURITY_CHAOS_ISOLATED` | secret/PII/hash-enumeration/chaos/SBOM results |
| `T7-LOCAL-SMOKE` | operator / local | `LOCAL_COMPOSE`; `T7-LOCAL-SMOKE`, `LOCAL_COMPOSE` | image/config hashes, health and outreach-off proof |
| `T7-LOCAL-RESET` | operator / local destructive | `LOCAL_DISPOSABLE`; destructive form with `COMMAND_ID=T7-LOCAL-RESET`, `PROFILE=LOCAL_DISPOSABLE` | target identity, backup-not-required attestation, reset and post-health |
| `T7-RELEASE-CANDIDATE` | operator / release M8 | `RELEASE_IMMUTABLE`; `T7-RELEASE-CANDIDATE`, `RELEASE_IMMUTABLE` | signed image/SBOM/provenance/gate manifest |
| `T7-RELEASE-PROMOTE` | operator / manual release destructive | `PRIVATE_PRODUCTION`; destructive form, `T7-RELEASE-PROMOTE`, `PRIVATE_PRODUCTION` | preflight, candidate digest, migration/health and pointer evidence |
| `T7-RELEASE-ROLLBACK` | operator / manual release destructive | `PRIVATE_PRODUCTION`; destructive form, `T7-RELEASE-ROLLBACK`, `PRIVATE_PRODUCTION` | incident, compatible schema, prior digest and health evidence |
| `T7-VPS-VERIFY` | operator / release M8 | `PRIVATE_PRODUCTION_READONLY`; `T7-VPS-VERIFY`, `PRIVATE_PRODUCTION_READONLY` | topology/firewall/TLS/secret/identity/capacity evidence |
| `T7-PUBLIC-EDGE-VERIFY` | operator / M9 public boundary | `PUBLIC_M9_READONLY`; `T7-PUBLIC-EDGE-VERIFY`, `PUBLIC_M9_READONLY` | exact two-route edge/DNS/TLS/WAF/abuse evidence |
| `T7-BACKUP-PRIMARY` | operator / scheduled backup | `BACKUP_REPO1`; `T7-BACKUP-PRIMARY`, `BACKUP_REPO1` | pgBackRest repo-1 check/backup/info and immutable receipt |
| `T7-BACKUP-DR` | operator / scheduled backup | `BACKUP_REPO2_B2`; `T7-BACKUP-DR`, `BACKUP_REPO2_B2` | pgBackRest repo-2 check/backup/info/Object-Lock receipt |
| `T7-TOMBSTONE-PURGE` | retention owner / manual destructive | `RETENTION_PRODUCTION`; destructive form, `T7-TOMBSTONE-PURGE`, `RETENTION_PRODUCTION` | PREPARED receipts, irreversible DB authorization/fences, GCS marker mirror/receipt, B2 certificate/read receipt/sole head CAS receipt, applied transaction/watermark/ack |
| `T7-RESTORE-PRIMARY` | operator / quarterly destructive drill | `RESTORE_ISOLATED_REPO1`; destructive form, `T7-RESTORE-PRIMARY`, `RESTORE_ISOLATED_REPO1` | repo-1 PITR, independent B2 authority-head/certificate replay, validations and destroy receipt |
| `T7-RESTORE-DR` | operator / quarterly destructive drill | `RESTORE_ISOLATED_REPO2`; destructive form, `T7-RESTORE-DR`, `RESTORE_ISOLATED_REPO2` | off-Google bootstrap/decrypt/PITR plus sole B2 authority-head/certificate replay and destroy receipt |
| `T7-MONITOR-VERIFY` | operator / scheduled monitoring | `MONITOR_SYNTHETIC`; `T7-MONITOR-VERIFY`, `MONITOR_SYNTHETIC` | collector/sink/policy/dashboard/receipt matrix |
| `T7-CRITICAL-PAGE-VERIFY` | operator / daily paging synthetic | `CRITICAL_E2E`; `T7-CRITICAL-PAGE-VERIFY`, `CRITICAL_E2E` | PagerDuty ack and independent watchdog receipts |
| `T7-DR-SCENARIO` | operator / quarterly DR destructive | `DR_ISOLATED`; destructive form, `T7-DR-SCENARIO`, `DR_ISOLATED` | exact scenario-matrix result, timelines, hashes and abort/escalation |

The registry maps every TEST-01..06 and INFRA-01..05 acceptance ID to exactly one command row. `T7-DOC-CONTRACT` mechanically proves requirement-ID domain equals mapping domain, mapping range equals the 24 command IDs above, all IDs are reachable, and no requirement is duplicated. It runs `bash -n` on generated entrypoints; invokes the canonical absolute runner from repository root, `backend/`, `frontend/`, and `/tmp`; and requires identical derived root/argv/evidence. Relative runner, malicious symlink, copied runner in a wrong Git root, root/profile/commit mismatch, caller root env override, and each destructive identity/confirmation mutation must exit `20` or `50` before target access/write.

## Ordered implementation tasks

- [ ] **Freeze the coverage registry —** Input: canonical roadmap sources and exact TEST-02..06 matrices. Operation: map every contract to one owner/lane/command/evidence/release action and reject duplicates/orphans. Output: signed `coverage.v1.json`. Test evidence: source-anchor resolver plus set-equality counts. Failure behavior: affected milestone and release remain blocked.
- [ ] **Freeze and parse the command registry —** Input: the 24 closed command rows, signed checkout/repository identity and each owning requirement. Operation: materialize immutable absolute runner argv, script-derived cwd, expected commit/profile/fixture/guard/artifact/exit semantics, parse every entrypoint, simulate every caller cwd and refuse symlink/root/env/identity drift or unlisted commands before target access. Output: signed `task7-commands.v1.json`. Test evidence: `T7-DOC-CONTRACT`, including `/tmp` positive, malicious symlink/wrong-root, unavailable=`30`, target mismatch=`50`, missing artifact=`40`, and set-equality negatives. Failure behavior: no Task 7 lane receives gate credit.
- [ ] **Build environment and fixture isolation —** Input: lane matrix and sensitivity/provider rules. Operation: create ephemeral database/schema/secret/network namespaces and signed fixture loader with deny-by-default network. Output: reproducible clean test contexts. Test evidence: parallel-run collision, forbidden socket, real-address canary, stale fixture and cleanup-crash cases. Failure behavior: destroy disposable context, quarantine evidence, and fail lane.
- [ ] **Implement evidence capture —** Input: one lane command and runtime metadata. Operation: stream results to a temporary run directory, hash/sign manifest last, and publish immutable only after completeness checks. Output: auditable pass/fail bundle. Test evidence: missing file, changed byte, interrupted upload, wrong commit and replay tests. Failure behavior: bundle is invalid and supplies no gate credit.
- [ ] **Wire CI/release gates —** Input: deterministic, recovery, browser, security, restore and provider evidence. Operation: enforce freshness/applicability and the exact milestone dependency graph. Output: promotion decision, never authority enable. Test evidence: stale/failed/wrong-environment/wrong-fixture/M1-waiver negatives. Failure behavior: retain prior release and controls false.
- [ ] **Operate flake and quarantine policy —** Input: any nondeterministic result. Operation: preserve first failure, classify root cause, fix test/product/environment, and rerun the complete owning suite from clean state. Output: reproducible result or open defect. Test evidence: injected intermittent safety failure cannot be averaged or retried away. Failure behavior: safety gate remains failed.

## Test strategy

- **Registry `test_every_canonical_requirement_has_one_executable_owner_and_release_action`.**
- **Isolation `test_parallel_test_runs_share_no_database_schema_secret_fixture_or_provider_identity`.**
- **Fixture `test_fixture_manifest_hash_signature_source_and_sensitivity_are_closed_and_verified`.**
- **Evidence `test_partial_or_tampered_evidence_manifest_never_counts_as_pass`.**
- **Gate `test_later_green_suite_cannot_waive_m1_m6_m8_or_m9_failure`.**
- **Truth `test_planned_test_and_infrastructure_documents_do_not_claim_current_execution`.**
- **Commands `test_task7_requirements_equal_command_mapping_domain_and_all_24_commands_are_reachable`.**
- **Shell `test_absolute_runner_derives_identical_root_from_every_cwd_and_rejects_relative_symlink_wrong_root_env_commit_or_profile_before_target_access`.**

## Security, privacy, compliance, idempotency, observability, and cost

Use synthetic data by default; restricted provider evidence is encrypted and access-audited. Test identifiers are safe and bounded; secrets/PII never enter JUnit, screenshots, traces, videos, Graphify, or Git. Repeated lane execution uses a run ID but replays the same logical fixture identity. Provider and load suites reserve cash/call/send budgets first and stop at the hard bound. Legal/policy fixtures test deterministic enforcement; they do not establish legal compliance.

## Failure, rollback, and operator recovery

On contamination, unauthorized network call, provider call-count mismatch, secret/PII leak, corrupted evidence, or unsafe cleanup: stop the lane, disable both send controls where applicable, revoke test credentials if exposed, preserve minimized evidence, destroy only the resolved disposable target, and open the mapped incident. Roll back test manifests and release pointers, never product history. Recovery requires a clean-environment rerun of the complete owning gate.

## Acceptance and retained evidence

- [ ] Every requirement in TEST-01..06 and INFRA-01..05 has one owner, lane, fixture, command, evidence and fail action.
- [ ] The closed command manifest contains exactly 24 reachable IDs; syntax, absolute script-derived root, arbitrary cwd, symlink/escape, repository/commit/profile identity, confirmation, artifact and exit behavior are mechanically proved.
- [ ] No live/shared environment or real recipient is reachable from ordinary CI.
- [ ] Evidence distinguishes pass, fail, skip, inapplicable and unavailable without false green.
- [ ] M1/M6/M8/M9 gates remain independent and no test result enables outreach.

Retain coverage/fixture/evidence schema versions, lane configurations, signed run manifests, JUnit/trace/hash outputs, isolation/canary tests, failed-first evidence, incident links, cost records and release decisions under the authoritative DB-06/SEC-06 retention manifest.

## Dependencies and next deliverable

TEST-01 consumes the complete roadmap and defines ownership for [TEST-02 contracts/integration](02-contract-and-integration-tests.md), [TEST-03 recovery](03-workflow-recovery-tests.md), [TEST-04 Gmail](04-gmail-side-effect-tests.md), [TEST-05 browser](05-end-to-end-browser-tests.md), and [TEST-06 load/security/chaos](06-load-security-and-chaos-tests.md). Passing all applicable lanes unlocks INFRA-02 promotion review only; it grants no deployment or send authority.
