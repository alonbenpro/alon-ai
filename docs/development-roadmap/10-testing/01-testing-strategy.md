# Whole-System Testing Strategy and Evidence Ownership

**Document ID:** TEST-01
**Status:** Planned M8 testing program; current unit, readiness-integration, generated-contract, build, secret-scan, and Compose CI checks cover only the foundation
**Milestone:** M1, M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator; the same person may execute and review, but generated evidence and signed manifests must make self-review reproducible
**Prerequisites:** exact task Inputs `TEST-01-T01 <- PRODUCT-01-T03; TEST-01-T02 <- TEST-01-T01; TEST-01-T03 <- TEST-01-T02; TEST-01-T04 <- TEST-01-T03; TEST-01-T05 <- TEST-01-T04,TEST-02-T07,TEST-05-T04,TEST-06-T04,TEST-03-T06,TEST-04-T06,TEST-03-T07,TEST-06-T05; TEST-01-T06 <- TEST-01-T05`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Test taxonomy, environment/isolation rules, fixture provenance, coverage registry, deterministic command lanes, evidence retention, and release-blocking ownership
**Unlocks:** TEST-02 through TEST-06, INFRA-02 promotion gates, and the M8 private-operations evidence bundle
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Every canonical contract has one named test owner, one environment, one authoritative fixture source, one executable command, one retained result, and one fail-closed release action. Passing a later or broader suite cannot waive a failed earlier gate. M1 DBOS acceptance, M6 Gmail safety, M8 restore/security, and M9 legal/public-ingress evidence remain separate necessary gates and never grant send authority by themselves.

## Current repository state

Implemented today: backend pytest unit/integration markers, Ruff, Pyright, Alembic upgrade, frontend Vitest/Testing Library, ESLint/TypeScript/build, generated OpenAPI drift rejection, tracked-secret scan, and a GitHub Actions Compose build/smoke job. The local Compose stack is PostgreSQL/API/idle worker/frontend on loopback with outreach false. There is no declared product schema, DBOS workflow, Temporal adapter, Gmail/OAuth implementation, agent/evaluation runtime, product UI, browser E2E runner, load/chaos harness, backup/PITR system, public unsubscribe ingress, VPS, KMS/secret manager, or exercised DR. Planned test names below are acceptance contracts, not passing claims.

## Scope and non-goals

In scope: strict schemas/digests, all database objects, API private-plus-two-public partition, policies and 14 dedicated final-SEND denials, finite workflows, runtime kill/replay/version behavior, providers/agents/evals, Gmail/OAuth, browser/accessibility, load/rate/budget, security/privacy/supply chain, backup/restore, fixture governance, flake handling, and evidence. Non-goals: mocking PostgreSQL where constraints matter, treating code coverage as assurance, live provider calls in ordinary CI, retrying flaky safety tests until green, production-data fixtures, destructive tests against shared/live targets, or inventing a second contract registry.

## Exact planned implementation surfaces

Create `tests/README.md`, `tests/manifests/coverage.v1.json`, `tests/fixtures/README.md`, `tests/evidence/schema.v1.json`, backend `tests/{contract,integration,recovery,security,load}`, frontend `tests/{contract,e2e,accessibility}`, `scripts/test_manifest.py`, and CI lanes from TEST-02..06. `coverage.v1.json` uses keys `{requirement_id,canonical_source,owner,suite,environment,fixture_manifest,command,evidence_schema,retention_class,release_action}`; `requirement_id` is stable and duplicates/missing sources fail.

| Lane | Environment and isolation | Network/provider rule | Required evidence | Failure action |
| --- | --- | --- | --- | --- |
| PR deterministic | ephemeral PostgreSQL 18 database per job; network denied after dependency install | signed synthetic/recorded fixtures only | JUnit, schema/manifest diffs, seed, commit and dependency hashes | block PR |
| PR container | disposable Compose project and volume with random project name | health endpoints only; no provider credential | image digests, service health, migration head, outreach-off proof | block PR |
| scheduled recovery/security | dedicated runner; fresh database/schema and disposable secret fixture store | allow only explicit local fault endpoints | kill matrix, row/event/call counts, canary scans | open test incident; block release |
| M1/M6 controlled provider | isolated Google project, owned aliases, separate credentials/schema, hard send cap | Gmail only through canonical gateway; M1 exact two-table harness | signed canonical evidence defined by WF-01/M6 | controls false; Temporal after any M1 disqualifier |
| release/M8 | clean restore host distinct from writers plus immutable candidate image; separate real-AWS acceptance target | no Gmail/provider during restore; the dedicated AWS S3 acceptance profile alone may access its disposable bucket | release/SBOM/provenance, AWS witness acceptance, restore, runbook, browser and capacity bundle | no promotion |
| M9 public boundary | disposable public hostname/ruleset; synthetic opaque tokens | only exact unsubscribe GET/POST exposed | 64/2 route diff, scanner/abuse/WAF/redaction traces | public pair absent; product outreach false |

Fixture manifests bind schema version, source type `SYNTHETIC|RECORDED_REDACTED|OWNED_PROVIDER_CAPTURE`, generator commit, canonical request/result hashes, capture UTC, source/license/policy reference, sensitivity, redaction review, signing key ID and signature. Any byte change creates a new fixture version. CI rejects real addresses, credentials, raw provider bodies, unsigned captures, and fixture use outside its permitted lane.

Evidence directories are run-scoped and immutable after signing: `evidence/{gate}/{UTC}-{commit}-{run_id}/manifest.json`. The manifest records exact commands/exit codes, OS/runtime/dependency/image/schema/config hashes, environment classification, fixture IDs, test counts/skips/retries, artifact hashes, start/end UTC and operator signature. A skip, xfail, retry, missing artifact, clock anomaly, or partial upload is a non-pass unless the owning canonical requirement explicitly declares it inapplicable.

### Closed command manifest

`tests/manifests/task7-commands.v1.json` is the sole planned executable-command registry. Every row has `{command_id,entry_argv,handler:{path,sha256},cwd,owner,lane,profile,fixture_manifest,target_guard,required_inputs,evidence_files,destructive,exit_semantics}`. `entry_argv` is the external call to `scripts/task7/run`; `handler.path` is one different exact file below `scripts/task7/handlers/`; `cwd` is the script-derived repository root. Neither field is executable shell text. The signed manifest plus every handler/fixture/profile is content-addressed in run evidence. Unknown IDs, changed entry argv/handler/hash, unavailable dependency/provider, or missing artifact cannot pass.

Every row's `entry_argv[0]` is the canonical absolute real path formed from the lane's signed checkout identity plus `/scripts/task7/run`; relative invocation is invalid. The remaining entry argv is `--manifest tests/manifests/task7-commands.v1.json --command COMMAND_ID --run-id "$TASK7_RUN_ID" --evidence-root "$TASK7_EVIDENCE_ROOT" --profile PROFILE --target-manifest "$TASK7_TARGET_MANIFEST"`; destructive rows append `--confirm "$TASK7_CONFIRMATION"`. `COMMAND_ID` and `PROFILE` are literal row values. The physical runner derives root only from canonical absolute `${BASH_SOURCE[0]}`, rejects every symlink/noncanonical/escape, calculates the physical directory two levels above itself, runs `git -C "$SCRIPT_DERIVED_ROOT" rev-parse --show-toplevel`, and requires exact equality. It verifies repository identity/commit/clean tree, manifest signature, row, profile, fixture, target-guard metadata and handler SHA-256 before target access. It requires the handler to be absolute after root join, regular, executable, non-symlink, physically inside `scripts/task7/handlers`, mapped to that command, and not `-ef` the runner. It then performs exactly one `exec` of the handler with normalized array arguments; it never executes `entry_argv`, the runner path, a shell string, or a second manifest-selected program. Caller cwd plus `TASK7_REPO_ROOT|REPO_ROOT|GIT_DIR|GIT_WORK_TREE` cannot select a root.

Profile and fixture paths are exactly `tests/profiles/task7/PROFILE.v1.json` and `tests/fixtures/task7/PROFILE.v1.json` under that derived root (a signed `NO_EXTERNAL_FIXTURE` manifest when none is needed). Required environment is immutable: `TASK7_RUN_ID` matches `^[A-Z0-9][A-Z0-9_-]{7,63}$`; `TASK7_EVIDENCE_ROOT` is a new absolute run-owned directory; the signed target manifest names environment, host, database, PostgreSQL system identifier, Compose project or release digest, or literal target kind `STATIC_NO_TARGET`; and confirmation is lowercase SHA-256 of RFC 8785 JSON `{command_id,run_id,target_kind,target_id,target_system_id}`. Credentials are secret references, never environment values. The handler receives exactly `--command COMMAND_ID --run-id RUN_ID --evidence-root PATH --profile PROFILE --target-manifest PATH` and optional `--confirm DIGEST`; it never receives the runner or manifest as an executable target. The guard independently queries every live target and requires exact manifest equality, a disposable/isolated classification for destructive tests, outreach false, and zero active writers; static rows require the signed no-target manifest and perform no cleanup. Exit codes are closed: `0` complete pass; `10` assertion failure; `20` preflight/root/identity/config failure; `30` dependency/provider unavailable (**not a pass**); `40` evidence/integrity failure; `50` unsafe or unconfirmed target refusal; `60` partial/ambiguous external outcome requiring recovery. Signals or any other exit code fail. Only `0` with every row's declared artifact counts.

The physical runner skeleton is frozen below; manifest/signature/target helpers are separately content-addressed. Bash parsing plus a 24-stub spy fixture must execute every row exactly once and prove runner recursion count zero before implementation credit.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
readonly runner_invoked="${BASH_SOURCE[0]}"
[[ "$runner_invoked" == /* && -f "$runner_invoked" && -x "$runner_invoked" && ! -L "$runner_invoked" ]] || exit 20
readonly runner_dir_lexical="${runner_invoked%/*}"
readonly runner_basename="${runner_invoked##*/}"
runner_dir_physical="$(cd -P -- "$runner_dir_lexical" && pwd -P)" || exit 20
readonly runner_dir_physical
readonly runner_real="$runner_dir_physical/$runner_basename"
[[ "$runner_invoked" == "$runner_real" ]] || exit 20
repo_root="$(cd -P -- "$runner_dir_physical/../.." && pwd -P)" || exit 20
readonly repo_root
[[ "$runner_real" == "$repo_root/scripts/task7/run" ]] || exit 20
unset TASK7_REPO_ROOT REPO_ROOT GIT_DIR GIT_WORK_TREE
git_root="$(git -C "$repo_root" rev-parse --show-toplevel)" || exit 20
readonly git_root
[[ "$(cd -P -- "$git_root" && pwd -P)" == "$repo_root" ]] || exit 20

[[ "$#" -eq 12 || "$#" -eq 14 ]] || exit 20
[[ "$1" == --manifest && "$2" == tests/manifests/task7-commands.v1.json ]] || exit 20
[[ "$3" == --command && "$5" == --run-id && "$7" == --evidence-root && "$9" == --profile && "${11}" == --target-manifest ]] || exit 20
if [[ "$#" -eq 14 ]]; then
  [[ "${13}" == --confirm && "${14}" =~ ^[0-9a-f]{64}$ ]] || exit 20
fi
readonly command_id="$4" run_id="$6" evidence_root="$8" profile="${10}" target_manifest="${12}"
handler_record="$(
  "$repo_root/scripts/task7/verify-static-contract" \
    --repository-identity "$repo_root/tests/manifests/repository-identity.v1.json" \
    --command-manifest "$repo_root/$2" --command "$command_id" \
    --profile-name "$profile" --run-id "$run_id" --evidence-root "$evidence_root" \
    --target-manifest "$target_manifest" --entry-runner "$runner_real" --emit handler-record
)" || exit 20
readonly handler_record
IFS=$'\t' read -r handler_relative handler_sha256 handler_extra <<< "$handler_record"
[[ -z "$handler_extra" && "$handler_relative" =~ ^scripts/task7/handlers/[a-z0-9-]+$ && "$handler_sha256" =~ ^[0-9a-f]{64}$ ]] || exit 20
handler_candidate="$repo_root/$handler_relative"
readonly handler_candidate
[[ -f "$handler_candidate" && -x "$handler_candidate" && ! -L "$handler_candidate" ]] || exit 20
handler_dir_physical="$(cd -P -- "${handler_candidate%/*}" && pwd -P)" || exit 20
readonly handler_dir_physical
readonly handler_real="$handler_dir_physical/${handler_candidate##*/}"
[[ "$handler_candidate" == "$handler_real" && "$handler_dir_physical" == "$repo_root/scripts/task7/handlers" && ! "$handler_real" -ef "$runner_real" ]] || exit 20
if [[ -x /usr/bin/sha256sum ]]; then
  handler_digest_line="$(/usr/bin/sha256sum -- "$handler_real")" || exit 20
elif [[ -x /usr/bin/shasum ]]; then
  handler_digest_line="$(/usr/bin/shasum -a 256 -- "$handler_real")" || exit 20
else
  exit 30
fi
readonly handler_digest_line
readonly handler_digest="${handler_digest_line%% *}"
[[ "$handler_digest" == "$handler_sha256" ]] || exit 40
handler_args=(--command "$command_id" --run-id "$run_id" --evidence-root "$evidence_root" --profile "$profile" --target-manifest "$target_manifest")
if [[ "$#" -eq 14 ]]; then
  handler_args+=(--confirm "${14}")
fi
exec "$handler_real" "${handler_args[@]}"
```

| Command ID | Exact handler path | Owner / lane | Profile and exact invocation substitution | Required artifact |
| --- | --- | --- | --- | --- |
| `T7-DOC-CONTRACT` | `scripts/task7/handlers/doc-contract` | operator / PR deterministic | `DOCS_LOCKED`; substitute `COMMAND_ID=T7-DOC-CONTRACT`, `PROFILE=DOCS_LOCKED` | source-anchor/link/terminology/count/command equality, sole-AWS-S3-authority/head/provider-survival/M8-acceptance equality, plus Bash/cwd/symlink/root/commit/profile-negative JSON |
| `T7-CONTRACT-INTEGRATION` | `scripts/task7/handlers/contract-integration` | operator / PR deterministic | `PG_EPHEMERAL`; `T7-CONTRACT-INTEGRATION`, `PG_EPHEMERAL` | catalog/OpenAPI/policy/incident JUnit plus hashes |
| `T7-WORKFLOW-RECOVERY` | `scripts/task7/handlers/workflow-recovery` | operator / scheduled recovery | `DBOS_EPHEMERAL`; `T7-WORKFLOW-RECOVERY`, `DBOS_EPHEMERAL` | finite-state/kill-point/version/Temporal evidence |
| `T7-GMAIL-OFFLINE` | `scripts/task7/handlers/gmail-offline` | operator / PR deterministic | `GMAIL_RECORDED`; `T7-GMAIL-OFFLINE`, `GMAIL_RECORDED` | union/ambiguity/reconciliation/OAuth-saga JUnit |
| `T7-GMAIL-LIVE` | `scripts/task7/handlers/gmail-live` | operator / M6 controlled provider | `GMAIL_OWNED_ALIAS`; `T7-GMAIL-LIVE`, `GMAIL_OWNED_ALIAS` | signed capped provider transcript and call/send counts |
| `T7-BROWSER-PRIVATE` | `scripts/task7/handlers/browser-private` | operator / release M8 | `BROWSER_PRIVATE`; `T7-BROWSER-PRIVATE`, `BROWSER_PRIVATE` | Playwright, axe, viewport, trace and screenshot bundle |
| `T7-BROWSER-PUBLIC` | `scripts/task7/handlers/browser-public` | operator / M9 public boundary | `BROWSER_PUBLIC_M9`; `T7-BROWSER-PUBLIC`, `BROWSER_PUBLIC_M9` | scanner/GET-write-zero/POST/WAF/redaction evidence |
| `T7-LOAD` | `scripts/task7/handlers/load` | operator / release M8 | `LOAD_ISOLATED`; `T7-LOAD`, `LOAD_ISOLATED` | workload, latency/error, database/rate/budget and stop proof |
| `T7-SECURITY-CHAOS` | `scripts/task7/handlers/security-chaos` | operator / scheduled recovery/security | `SECURITY_CHAOS_ISOLATED`; `T7-SECURITY-CHAOS`, `SECURITY_CHAOS_ISOLATED` | secret/PII/hash-enumeration/chaos/SBOM results |
| `T7-LOCAL-SMOKE` | `scripts/task7/handlers/local-smoke` | operator / local | `LOCAL_COMPOSE`; `T7-LOCAL-SMOKE`, `LOCAL_COMPOSE` | image/config hashes, health and outreach-off proof |
| `T7-LOCAL-RESET` | `scripts/task7/handlers/local-reset` | operator / local destructive | `LOCAL_DISPOSABLE`; destructive form with `COMMAND_ID=T7-LOCAL-RESET`, `PROFILE=LOCAL_DISPOSABLE` | target identity, backup-not-required attestation, reset and post-health |
| `T7-RELEASE-CANDIDATE` | `scripts/task7/handlers/release-candidate` | operator / release M8 | `RELEASE_IMMUTABLE`; `T7-RELEASE-CANDIDATE`, `RELEASE_IMMUTABLE` | signed image/SBOM/provenance/gate manifest |
| `T7-RELEASE-PROMOTE` | `scripts/task7/handlers/release-promote` | operator / manual release destructive | `PRIVATE_PRODUCTION`; destructive form, `T7-RELEASE-PROMOTE`, `PRIVATE_PRODUCTION` | preflight, candidate digest, migration/health and pointer evidence |
| `T7-RELEASE-ROLLBACK` | `scripts/task7/handlers/release-rollback` | operator / manual release destructive | `PRIVATE_PRODUCTION`; destructive form, `T7-RELEASE-ROLLBACK`, `PRIVATE_PRODUCTION` | incident, compatible schema, prior digest and health evidence |
| `T7-VPS-VERIFY` | `scripts/task7/handlers/vps-verify` | operator / release M8 | `PRIVATE_PRODUCTION_READONLY`; `T7-VPS-VERIFY`, `PRIVATE_PRODUCTION_READONLY` | topology/firewall/TLS/secret/identity/capacity evidence |
| `T7-PUBLIC-EDGE-VERIFY` | `scripts/task7/handlers/public-edge-verify` | operator / M9 public boundary | `PUBLIC_M9_READONLY`; `T7-PUBLIC-EDGE-VERIFY`, `PUBLIC_M9_READONLY` | exact two-route edge/DNS/TLS/WAF/abuse evidence |
| `T7-BACKUP-BOTH` | `scripts/task7/handlers/backup-both` | operator / scheduled backup | `BACKUP_REPOSITORIES`; `T7-BACKUP-BOTH`, `BACKUP_REPOSITORIES` | per-repository pgBackRest check/backup/info/WAL coverage plus immutable GCS and accepted AWS S3 Object-Lock receipts |
| `T7-AWS-WITNESS-ACCEPT` | `scripts/task7/handlers/aws-witness-accept` | operator / M8 controlled-provider destructive acceptance | `AWS_S3_WITNESS_ACCEPT_EU_CENTRAL_1`; destructive form, `T7-AWS-WITNESS-ACCEPT`, `AWS_S3_WITNESS_ACCEPT_EU_CENTRAL_1` | real disposable `eu-central-1` general-purpose bucket identity; versioning/Object Lock/bucket-policy/IAM hashes; concurrent genesis/update CAS with `200|409|412|timeout` reconciliation; exact version/ETag/checksum/read-back; retention/delete/bypass denial; pgBackRest repo-2 backup/WAL/restore; independent package/account-lockout drill; signed evidence hashes |
| `T7-TOMBSTONE-PURGE` | `scripts/task7/handlers/tombstone-purge` | retention owner / manual destructive | `RETENTION_PRODUCTION`; destructive form, `T7-TOMBSTONE-PURGE`, `RETENTION_PRODUCTION` | PREPARED receipts, irreversible DB authorization/fences, GCS marker mirror/receipt, AWS S3 certificate/read receipt/sole head conditional-write receipt, applied transaction/watermark/ack |
| `T7-RESTORE-PRIMARY` | `scripts/task7/handlers/restore-primary` | operator / quarterly destructive drill | `RESTORE_ISOLATED_REPO1`; destructive form, `T7-RESTORE-PRIMARY`, `RESTORE_ISOLATED_REPO1` | repo-1 PITR, independent AWS S3 authority-head/certificate replay, validations and destroy receipt |
| `T7-RESTORE-DR` | `scripts/task7/handlers/restore-dr` | operator / quarterly destructive drill | `RESTORE_ISOLATED_REPO2`; destructive form, `T7-RESTORE-DR`, `RESTORE_ISOLATED_REPO2` | off-Google bootstrap/decrypt/PITR plus sole AWS S3 authority-head/certificate replay and destroy receipt |
| `T7-MONITOR-VERIFY` | `scripts/task7/handlers/monitor-verify` | operator / scheduled monitoring | `MONITOR_SYNTHETIC`; `T7-MONITOR-VERIFY`, `MONITOR_SYNTHETIC` | collector/sink/policy/dashboard/receipt matrix |
| `T7-CRITICAL-PAGE-VERIFY` | `scripts/task7/handlers/critical-page-verify` | operator / daily paging synthetic | `CRITICAL_E2E`; `T7-CRITICAL-PAGE-VERIFY`, `CRITICAL_E2E` | PagerDuty ack and independent watchdog receipts |
| `T7-DR-SCENARIO` | `scripts/task7/handlers/dr-scenario` | operator / quarterly DR destructive | `DR_ISOLATED`; destructive form, `T7-DR-SCENARIO`, `DR_ISOLATED` | exact scenario-matrix result, timelines, hashes and abort/escalation |

The registry maps every TEST-01..06 and INFRA-01..05 acceptance ID to exactly one command row. `T7-DOC-CONTRACT` mechanically proves requirement-ID domain equals mapping domain, mapping range equals the 24 command IDs above, handler-path set equals the 24 distinct paths above, all IDs are reachable, and no requirement is duplicated. It runs `bash -n` on the runner and all handlers; substitutes 24 executable spy handlers with signed hashes; invokes the canonical absolute runner once per row from repository root, `backend/`, `frontend/`, and `/tmp`; and requires one matching handler exec, identical derived root/normalized handler argv/evidence, runner-exec count `0`, and total handler calls `24` per starting directory. A row whose handler is `scripts/task7/run`, equal-inode/copy recursion, a second exec, relative handler, handler symlink/escape/hash mismatch, malicious runner symlink, copied runner in a wrong Git root, root/profile/commit mismatch, caller root env override, and each destructive identity/confirmation mutation must exit `20`, `40`, or `50` before target access/write.

## Sales coverage ownership and launch evidence

The coverage registry must include every canonical sales artifact and durable boundary. The command set remains the exact existing 24 rows; expanded cases join their owning commands with versioned scenario IDs and exact set-equality checks. Do not introduce a shadow runner or certify a future implementation from roadmap text.

| Required sales coverage | Owning command / document |
| --- | --- |
| all fifteen artifacts, order/lineage, unsupported facts/evidence, approved multi-source dedupe, PRELIMINARY/FINAL, deterministic commercial vectors, conversation states, booking and strategy schema/owner/privacy contracts | T7-CONTRACT-INTEGRATION / TEST-02 |
| close/freeze/decision/learning trigger, all-agent results, cross-campaign activation, no mid-cohort mutation, weak evidence, rollback and crash/replay at every durable boundary | T7-WORKFLOW-RECOVERY / TEST-03 |
| EmailWritingAgent/SendGateway separation, inbound cold-stop and durable-suppression distinction, bounded reply/terminal race, Gmail provider uncertainty/caps/history | T7-GMAIL-OFFLINE and separately owned-alias T7-GMAIL-LIVE / TEST-04 |
| complete funnel, calendar, exception and strategy UI, browser bypass denial, full cost-first staged campaign simulation | T7-BROWSER-PRIVATE / TEST-05 |
| calendar/write capability isolation, commercial and strategy injection, multi-campaign races, privacy leakage, kill/restore chaos and public abuse | T7-SECURITY-CHAOS, T7-LOAD and existing public-edge commands / TEST-06 |
| release/rollback/backup/restore preserves offer/strategy/cohort/checkpoint/conversation/booking/suppression and never reopens effects | existing release/restore/DR command rows / INFRA-02/04/05 |

Recorded calendar action fixtures are part of T7-CONTRACT-INTEGRATION and T7-WORKFLOW-RECOVERY; real dedicated-calendar acceptance is WF-07-T04's separately signed M6 provider gate. The Gmail live runner never gains CalendarWritePort. No new live command is inferred from an offline fixture.

Acceptance evidence follows exactly: synthetic agent pipeline → recorded provider fixtures → owned test-inbox conversations → simulated objections and negotiation → test calendar bookings → checkpoint and global-learning simulation → tightly controlled real campaign → earned autonomous sending and negotiation. Phases 1–6 never count as real demand. Existing M1, M6, M8 and M9 gates retain independent authority. The full simulation proves SHADOW/REVIEW_20/QUALIFIED_50/SCALE_100_TO_300 increments, cumulative 0/20/50/explicitly-authorized-100-to-300, five exact checkpoint decisions and four exact learning results with sole SendGateway/BookingGateway writers.

## Ordered implementation tasks

<!-- roadmap-task id=TEST-01-T01 milestone=M1 depends_on=PRODUCT-01-T03 mode=serial locks=test-command-registry -->
- [ ] **Freeze the coverage registry —** Input: the PRODUCT-01 vocabulary crosswalk, canonical roadmap source documents, and exact document-local TEST-02..06 matrices. Operation: map every contract to one owner/lane/command/evidence/release action and reject duplicates/orphans. Output: signed `coverage.v1.json`. Test evidence: source-anchor resolver plus set-equality counts. Failure behavior: affected milestone and release remain blocked.
<!-- roadmap-task id=TEST-01-T02 milestone=M1 depends_on=TEST-01-T01 mode=serial locks=test-command-registry -->
- [ ] **Freeze and parse the command registry —** Input: the 24 closed command rows, distinct handler map, signed checkout/repository identity and each owning requirement. Operation: materialize immutable absolute entry argv and handler digest, parse every Bash file, execute the 24-spy nonrecursive dispatch fixture from every cwd, and refuse self/equal-inode/second-exec/symlink/root/env/identity drift or unlisted commands before target access. Output: signed `task7-commands.v1.json`. Test evidence: `T7-DOC-CONTRACT`, including exact 24 calls/zero runner recursion, `/tmp` positive, malicious handler/runner symlink/wrong-root/hash, unavailable=`30`, target mismatch=`50`, missing artifact=`40`, the reachable `T7-AWS-WITNESS-ACCEPT` row, and set-equality negatives. Failure behavior: no Task 7 lane receives gate credit.
<!-- roadmap-task id=TEST-01-T03 milestone=M1 depends_on=TEST-01-T02 mode=serial locks=test-command-registry -->
- [ ] **Build environment and fixture isolation —** Input: lane matrix and sensitivity/provider rules. Operation: create ephemeral database/schema/secret/network namespaces and signed fixture loader with deny-by-default network. Output: reproducible clean test contexts. Test evidence: parallel-run collision, forbidden socket, real-address canary, stale fixture and cleanup-crash cases. Failure behavior: destroy disposable context, quarantine evidence, and fail lane.
<!-- roadmap-task id=TEST-01-T04 milestone=M1 depends_on=TEST-01-T03 mode=serial locks=test-command-registry -->
- [ ] **Implement evidence capture —** Input: one lane command and runtime metadata. Operation: stream results to a temporary run directory, hash/sign manifest last, and publish immutable only after completeness checks. Output: versioned evidence-capture/convention contract and auditable pass/fail bundle. Test evidence: missing file, changed byte, interrupted upload, wrong commit and replay tests. Failure behavior: bundle is invalid and supplies no gate credit.
<!-- roadmap-task id=TEST-01-T05 milestone=M8 depends_on=TEST-01-T04,TEST-02-T07,TEST-05-T04,TEST-06-T04,TEST-03-T06,TEST-04-T06,TEST-03-T07,TEST-06-T05 mode=serial locks=test-command-registry -->
- [ ] **Wire CI/release gates —** Input: deterministic, recovery, browser, security, restore and provider evidence, including TEST-03 signed command mapping and TEST-06 signed command-coverage report. Operation: enforce freshness/applicability and the exact milestone dependency graph. Output: promotion decision, never authority enable. Test evidence: stale/failed/wrong-environment/wrong-fixture/M1-waiver negatives. Failure behavior: retain prior release and controls false.
<!-- roadmap-task id=TEST-01-T06 milestone=M8 depends_on=TEST-01-T05 mode=serial locks=test-command-registry -->
- [ ] **Operate flake and quarantine policy —** Input: any nondeterministic result. Operation: preserve first failure, classify root cause, fix test/product/environment, and rerun the complete owning suite from clean state. Output: reproducible result or open defect. Test evidence: injected intermittent safety failure cannot be averaged or retried away. Failure behavior: safety gate remains failed.

## Test strategy

- **Registry `test_every_canonical_requirement_has_one_executable_owner_and_release_action`.**
- **Isolation `test_parallel_test_runs_share_no_database_schema_secret_fixture_or_provider_identity`.**
- **Fixture `test_fixture_manifest_hash_signature_source_and_sensitivity_are_closed_and_verified`.**
- **Evidence `test_partial_or_tampered_evidence_manifest_never_counts_as_pass`.**
- **Gate `test_later_green_suite_cannot_waive_m1_m6_m8_or_m9_failure`.**
- **Truth `test_planned_test_and_infrastructure_documents_do_not_claim_current_execution`.**
- **Commands `test_task7_requirements_equal_command_mapping_domain_and_all_24_commands_are_reachable`.**
- **AWS acceptance `test_m8_requires_real_eu_central_1_s3_witness_cas_lock_pgbackrest_and_lockout_evidence_not_an_emulator`.**
- **Shell `test_absolute_runner_derives_identical_root_from_every_cwd_and_rejects_relative_symlink_wrong_root_env_commit_or_profile_before_target_access`.**
- **Dispatch `test_24_entry_rows_exec_24_distinct_handlers_once_with_zero_runner_recursion_and_exact_normalized_argv`.**

## Security, privacy, compliance, idempotency, observability, and cost

Use synthetic data by default; restricted provider evidence is encrypted and access-audited. Test identifiers are safe and bounded; secrets/PII never enter JUnit, screenshots, traces, videos, Graphify, or Git. Repeated lane execution uses a run ID but replays the same logical fixture identity. Provider and load suites reserve cash/call/send budgets first and stop at the hard bound. Legal/policy fixtures test deterministic enforcement; they do not establish legal compliance.

## Failure, rollback, and operator recovery

On contamination, unauthorized network call, provider call-count mismatch, secret/PII leak, corrupted evidence, or unsafe cleanup: stop the lane, disable both send controls where applicable, revoke test credentials if exposed, preserve minimized evidence, destroy only the resolved disposable target, and open the mapped incident. Roll back test manifests and release pointers, never product history. Recovery requires a clean-environment rerun of the complete owning gate.

## Acceptance and retained evidence

- [ ] Every requirement in TEST-01..06 and INFRA-01..05 has one owner, lane, fixture, command, evidence and fail action.
- [ ] The closed command manifest contains exactly 24 reachable IDs; syntax, absolute script-derived root, arbitrary cwd, symlink/escape, repository/commit/profile identity, confirmation, artifact and exit behavior are mechanically proved.
- [ ] `T7-AWS-WITNESS-ACCEPT` is a required M8 row: missing AWS authorization/credits/provider access is unavailable exit `30`, no emulator can pass, and any failed semantic blocks M8 pending a signed architecture amendment to an otherwise unselected provider with documented and live-tested CAS/Object Lock.
- [ ] No live/shared environment or real recipient is reachable from ordinary CI.
- [ ] Evidence distinguishes pass, fail, skip, inapplicable and unavailable without false green.
- [ ] M1/M6/M8/M9 gates remain independent and no test result enables outreach.

Retain coverage/fixture/evidence schema versions, lane configurations, signed run manifests, JUnit/trace/hash outputs, isolation/canary tests, failed-first evidence, incident links, cost records and release decisions under the authoritative DB-06/SEC-06 retention manifest.

## Dependencies and next deliverable

TEST-01 consumes the complete roadmap and defines ownership for [TEST-02 contracts/integration](02-contract-and-integration-tests.md), [TEST-03 recovery](03-workflow-recovery-tests.md), [TEST-04 Gmail](04-gmail-side-effect-tests.md), [TEST-05 browser](05-end-to-end-browser-tests.md), and [TEST-06 load/security/chaos](06-load-security-and-chaos-tests.md). Passing all applicable lanes unlocks INFRA-02 promotion review only; it grants no deployment or send authority.
