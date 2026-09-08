# Load, Security, Privacy, and Chaos Tests

**Document ID:** TEST-06
**Status:** Planned M8 adversarial/capacity gate and M9 public-ingress subset; current CI only scans tracked files for high-signal credentials and smoke-tests foundation containers
**Milestone:** M8, M9 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator; counsel/provider support participates only where facts require it
**Prerequisites:** exact local order `TEST-06-T01 -> TEST-06-T02 -> TEST-06-T03 -> TEST-06-T04 -> TEST-06-T05 -> TEST-06-T06`; cross-document task Inputs `TEST-06-T01 <- TEST-01-T01; TEST-06-T02 <- INFRA-02-T02; TEST-06-T03 <- SEC-01-T02; TEST-06-T04 <- INFRA-04-T02,INFRA-02-T04; TEST-06-T05 <- TEST-01-T01; TEST-06-T06 <- LAUNCH-03-T02,BACKEND-02-T05,SEC-04-T04,OBS-01-T07`. Descriptive source authorities/resources (not whole-document completion dependencies): SEC-01 T01-T16, SEC-02..06, BACKEND-02..05, OBS-01..05, TEST-01..05, and candidate infrastructure manifests
**Outputs:** Measured capacity envelope, rate/budget correctness, T01-T16 closure evidence, secret/PII/hash-enumeration scans, public abuse/WAF matrix, fault/chaos results, and safe rollback thresholds
**Unlocks:** M8 capacity/security acceptance and the infrastructure portion of M9 public unsubscribe eligibility
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

The smallest private topology has a measured safe operating envelope and fails closed under overload, dependency loss, malicious input, telemetry blindness, secret/PII canaries, and operator error. Tests prove deterministic limits; they do not chase vanity throughput. Public testing exposes exactly two M9-gated unsubscribe operations and proves scanners/abuse cannot mutate via GET, enumerate a recipient, or reach the private API.

The staged-admission chaos suite races at `99/100`, `199/200`, `299/300`, `399/400`, and cumulative `999/1,000`; injects DB/runtime loss around barrier commits; replays stale `CONTINUE`; and attempts duplicate identity, allocation drift, lower-counsel-cap bypass, and immediate-1,000 admission. Every case must preserve the smaller applicable ceiling, produce zero excess provider calls, and stop new admission when authoritative truth is unavailable.

## Current repository state

There is no load generator, WAF/proxy manifest, rate limiter implementation, security corpus, dependency-fault proxy, disk/clock/network chaos harness, SBOM/provenance gate, telemetry sink, recipient-hash enumeration test, public ingress, backup/restore fault suite, or measured capacity/SLO result. Current secret scan, non-root containers, loopback Compose ports and outreach-off defaults are useful foundation controls only.

## Scope and non-goals

In scope: API/DB/worker/browser throughput and latency, pool/queue/storage headroom, mailbox rate/concurrency, provider/cost/budget caps, exact 66/64+2 ingress, WAF method/URI/body/token/origin/fetch/CSRF rules, T01-T16, SSRF/DNS rebinding, callback/session attacks, supply chain, canaries, SHA-256 recipient lookup offline-enumeration residual risk, PostgreSQL/WAL/disk/clock/telemetry/secret/provider faults, backup corruption and restore. Non-goals: production denial-of-service, real-recipient load, destructive chaos on shared/live targets, autonomous remediation, penetration-test/compliance certification claims, or adding Redis/Kafka/Kubernetes to inflate scores.

## Exact planned implementation surfaces

Create `tests/load/` using k6 or Locust selected once in the locked dependency manifest (one tool, not both), `tests/security/corpus/`, `tests/chaos/`, proxy fault fixtures, `tests/manifests/capacity.v1.json`, and `infra/security/public-route-policy.v1.json`. Default target is a disposable clone with synthetic data and both controls false. Before destructive cases the harness resolves and records host/project/database/system identifier, refuses names lacking the run ID, snapshots evidence, and verifies no production credential/domain.

Initial safe-capacity acceptance for the planned 4-vCPU/8-GiB single-VPS topology is deliberately modest: 10 concurrent authenticated browser/API users (one real operator plus test headroom), 20 read requests/s for 15 minutes, 2 mutation requests/s for 15 minutes, 4 concurrent non-Gmail worker tasks, PostgreSQL connection ceiling 40 with application pools capped below it, and one Gmail start per mailbox per 30 seconds with concurrency one. At p95, private reads must stay <=500 ms, mutations excluding async work <=1 s, control-disable commit <=5 s, and no safety SLO/error/cap violation. The test stops at 70% memory, 80% disk, pool wait p95 >250 ms, database CPU >80% for 5 minutes, error >1% for 5 minutes, any integrity error, or any external call beyond manifest. These are planned launch bounds to validate, not current capacity claims; failed bounds require reducing authority or resizing, not hiding the result.

| Family | Required scenarios | Exact invariant |
| --- | --- | --- |
| rate/budget/load | boundary bursts, concurrent workers, duplicate commands, pool exhaustion, cost overage | one winner/lease; caps never exceeded or auto-raised; overload 429/503 is bounded and no partial write |
| public ingress | exact GET/POST, wrong method/path/content type/body/token, scanner/prefetch, cross-origin, replay, spray, source/global bucket, upstream loss | only two route matches; GET zero writes; POST one suppression; no identifier/log label; dependency failure product-off |
| T01-T16 | each SEC-01 owner/test/alert/runbook/recovery row | prevention or bounded detection fires; exact incident tuple; first action executable; no Critical gap |
| secrets/PII | canaries across Git/image/env/process/log/error/trace/metric/eval/fixture/Graphify/backup/browser | zero unauthorized matches; scanner reports locations without printing values |
| recipient hash | common-address offline dictionary, SQL privilege/query-rate/API/log/report/export sweeps | SHA-256 remains explicitly pseudonymous/enumerable; only lookup service reads restricted column; alert/incident on abuse |
| chaos | DB restart/read-only/latency, worker/API kill, full disk, WAL/archive loss, clock skew, DNS/egress/provider/secret/KMS/telemetry/alert outage, corrupt backup/key | authoritative state preserved/unknown explicit; controls false where visibility/authority uncertain; no blind call/automatic enable |
| supply chain | changed lock, mutable tag, unsigned image/SBOM/provenance, stale base/vulnerability/license exception | candidate rejected or documented risk expires; rollback by digest |

Capacity/rate/budget rows map exactly to `T7-LOAD`; T01-T16, secret/PII/recipient-hash/supply-chain and bounded fault rows map exactly to `T7-SECURITY-CHAOS`; public abuse/WAF rows map exactly to `T7-PUBLIC-EDGE-VERIFY`; restore-specific corrupt-chain/key rows delegate to `T7-RESTORE-PRIMARY|T7-RESTORE-DR` without duplicate ownership. Each uses the exact [TEST-01 runner form](01-testing-strategy.md#closed-command-manifest) and its named profile. `T7-LOAD` and `T7-SECURITY-CHAOS` target a signed isolated target; any destructive injection additionally requires the target manifest and confirmation digest. Threshold stop, unsafe target or absent injector exits `10`, `50` or `30` respectively, never pass. Set equality rejects an unmapped or multiply owned requirement.

## Ordered implementation tasks

<!-- roadmap-task id=TEST-06-T01 milestone=M8 depends_on=TEST-01-T01 mode=serial locks=test-command-registry -->
- [ ] **Freeze capacity and destructive-target guards —** Input: the TEST-01 signed coverage manifest plus document-local planned VPS resources, SLOs, pools/queues/caps, and an operator-selected disposable target. Operation: encode thresholds/stop conditions and resolve target identity before any load/fault. Output: signed capacity scenario. Test evidence: production-like name, unresolved variable, wrong DB/system ID and threshold-stop self-tests. Failure behavior: refuse execution.
<!-- roadmap-task id=TEST-06-T02 milestone=M8 depends_on=TEST-06-T01,INFRA-02-T02 mode=serial locks=test-command-registry -->
- [ ] **Measure private capacity/rate/budget —** Input: representative synthetic dataset and candidate image. Operation: run ramp/steady/burst/soak while comparing API results to PostgreSQL and cost/rate ledgers. Output: safe envelope or smaller/resized recommendation. Test evidence: latency/errors/resources/rows/leases/cost exactness. Failure behavior: release/authority capped at last proven bound.
<!-- roadmap-task id=TEST-06-T03 milestone=M8 depends_on=TEST-06-T02,SEC-01-T02 mode=serial locks=test-command-registry -->
- [ ] **Execute T01-T16 and canary corpus —** Input: SEC-01 closure matrix, secret/PII/hash canaries and candidate artifacts. Operation: attack every boundary and verify exact alert/incident/runbook/disable evidence. Output: signed security matrix. Test evidence: no orphan threat and zero uncontrolled data/authority path. Failure behavior: Critical incident and release blocked.
<!-- roadmap-task id=TEST-06-T04 milestone=M8 depends_on=TEST-06-T03,INFRA-04-T02,INFRA-02-T04 mode=serial locks=test-command-registry -->
- [ ] **Execute bounded chaos and rollback —** Input: disposable environment, fault schedule, backup and last release. Operation: inject one fault at a time, capture detection/containment/recovery, and restore/rollback without live-target mutation. Output: recovery-time/data-loss measurements. Test evidence: each fault meets its RPO/RTO/invariant or records failure. Failure behavior: M8 blocked; preserve environment for diagnosis.
<!-- roadmap-task id=TEST-06-T05 milestone=M8 depends_on=TEST-06-T04,TEST-01-T01 mode=serial locks=test-command-registry -->
- [ ] **Close adversarial command ownership —** Input: every capacity/security/privacy/public/fault requirement and TEST-01 registry. Operation: prove exact mapping to `T7-LOAD`, `T7-SECURITY-CHAOS`, `T7-PUBLIC-EDGE-VERIFY` or the restore owner; validate profile, guard, stop and artifact semantics. Output: signed command-coverage report. Test evidence: orphan/duplicate/unsafe/unavailable negatives. Failure behavior: M8/M9 remains blocked.
<!-- roadmap-task id=TEST-06-T06 milestone=M9 depends_on=TEST-06-T05,LAUNCH-03-T02,BACKEND-02-T05,SEC-04-T04,OBS-01-T07 mode=serial locks=test-command-registry,live-environment -->
- [ ] **Prove active public route, WAF, and recipient-stop controls —** Input: the SEC-04 activation-ready stop path, LAUNCH-03 recipient-opaque activated public capability, BACKEND-02 exact disabled-public 64+2 manifest, and TEST-06-owned synthetic unsubscribe tokens; active-public safe correlation/redaction evidence. Operation: exercise token, method, path, body, scanner GET, Origin/fetch/CSRF POST, rate, timeout, redaction, dependency failure, suppression, Gmail-history, and operator evidence against the active bounded M9 ingress. Output: scanner-safe active public-ingress and recipient-suppression evidence. Test evidence: route equality, database writes, provider calls, events/telemetry, suppression, and dependency `PRODUCT_OUTREACH` fail-close counts. Failure behavior: disable the public hostname/ruleset and keep product outreach false.

## Test strategy

- **Capacity `test_planned_private_envelope_meets_latency_resource_integrity_and_stop_thresholds`.**
- **Rate `test_restart_burst_and_concurrency_never_exceed_mailbox_rate_budget_or_cost_caps`.**
- **Threat `test_t01_through_t16_map_to_exact_alert_incident_runbook_evidence_and_recovery`.**
- **Public `test_only_two_m9_routes_survive_scanner_waf_token_csrf_rate_and_dependency_matrix`.**
- **Leak `test_canaries_absent_from_all_artifacts_sinks_images_browser_graphify_and_backups`.**
- **Hash `test_recipient_sha256_dictionary_and_query_sweep_remains_restricted_alerted_residual_risk`.**
- **Chaos `test_db_disk_wal_clock_kms_provider_telemetry_and_backup_faults_fail_closed`.**
- **Supply `test_unpinned_unsigned_mutable_or_sbom_drifted_release_is_rejected`.**

## Security, privacy, compliance, idempotency, observability, and cost

All attacks use synthetic targets and bounded rates. Public per-source evidence stores only coarse outcome/bucket, never IP/token/JTI/recipient/hash. Recipient SHA-256 is never called anonymous; encryption/least privilege and rate detection are compensating controls, not a claim against offline enumeration. Paid tools/provider calls require explicit reservation and manifest cap. Legal/counsel determinations remain external inputs; security tests prove enforcement and evidence only.

## Failure, rollback, and operator recovery

Any integrity breach, post-disable call, cap overrun, public route widening, GET mutation, canary leak, hash exposure, unalerted Critical condition, uncontrolled destructive target, or RPO/RTO miss stops the test and candidate. Set both controls false; disable public ingress for every public-boundary or suppression-observability fault; revoke exposed material, preserve minimized evidence, restore disposable state, and execute the exact IR runbook. Roll back by immutable digest/config/WAF version; never increase capacity/caps or delete evidence to obtain a pass.

## Acceptance and retained evidence

- [ ] The private launch envelope is measured with exact resources, thresholds, data set and stop conditions.
- [ ] T01-T16, secrets/PII/hash enumeration, supply-chain and chaos matrices have no Critical coverage gap.
- [ ] Public ingress exposes only two M9-gated operations and remains scanner-safe, rate-bounded and redacted.
- [ ] Every fault records observed RPO/RTO and fail-closed authority; unavailable infrastructure is reported as untested, never passed.

Retain load scripts/manifests/raw summaries, resource/database/rate/cost comparisons, T01-T16 and canary results, route/WAF configs and requests with sensitive values removed, incident/alert/runbook traces, fault timelines, restore/rollback results and capacity decision.

## Dependencies and next deliverable

TEST-06 feeds [INFRA-02 release](../11-infrastructure/02-ci-cd-and-release-process.md), [INFRA-03 VPS/ingress](../11-infrastructure/03-private-vps-deployment.md), and [INFRA-05 DR](../11-infrastructure/05-monitoring-and-disaster-recovery.md). Passing M8 tests permits private deployment review; the public subset is only one M9 prerequisite and cannot publish ingress or authorize outreach alone.
