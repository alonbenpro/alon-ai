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

## Ordered implementation tasks

- [ ] **Freeze the coverage registry —** Input: canonical roadmap sources and exact TEST-02..06 matrices. Operation: map every contract to one owner/lane/command/evidence/release action and reject duplicates/orphans. Output: signed `coverage.v1.json`. Test evidence: source-anchor resolver plus set-equality counts. Failure behavior: affected milestone and release remain blocked.
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

## Security, privacy, compliance, idempotency, observability, and cost

Use synthetic data by default; restricted provider evidence is encrypted and access-audited. Test identifiers are safe and bounded; secrets/PII never enter JUnit, screenshots, traces, videos, Graphify, or Git. Repeated lane execution uses a run ID but replays the same logical fixture identity. Provider and load suites reserve cash/call/send budgets first and stop at the hard bound. Legal/policy fixtures test deterministic enforcement; they do not establish legal compliance.

## Failure, rollback, and operator recovery

On contamination, unauthorized network call, provider call-count mismatch, secret/PII leak, corrupted evidence, or unsafe cleanup: stop the lane, disable both send controls where applicable, revoke test credentials if exposed, preserve minimized evidence, destroy only the resolved disposable target, and open the mapped incident. Roll back test manifests and release pointers, never product history. Recovery requires a clean-environment rerun of the complete owning gate.

## Acceptance and retained evidence

- [ ] Every requirement consumed by TEST-02..06 has one owner, lane, fixture, command, evidence and fail action.
- [ ] No live/shared environment or real recipient is reachable from ordinary CI.
- [ ] Evidence distinguishes pass, fail, skip, inapplicable and unavailable without false green.
- [ ] M1/M6/M8/M9 gates remain independent and no test result enables outreach.

Retain coverage/fixture/evidence schema versions, lane configurations, signed run manifests, JUnit/trace/hash outputs, isolation/canary tests, failed-first evidence, incident links, cost records and release decisions under the authoritative DB-06/SEC-06 retention manifest.

## Dependencies and next deliverable

TEST-01 consumes the complete roadmap and defines ownership for [TEST-02 contracts/integration](02-contract-and-integration-tests.md), [TEST-03 recovery](03-workflow-recovery-tests.md), [TEST-04 Gmail](04-gmail-side-effect-tests.md), [TEST-05 browser](05-end-to-end-browser-tests.md), and [TEST-06 load/security/chaos](06-load-security-and-chaos-tests.md). Passing all applicable lanes unlocks INFRA-02 promotion review only; it grants no deployment or send authority.
