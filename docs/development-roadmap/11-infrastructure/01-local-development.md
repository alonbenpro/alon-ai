# Reproducible Local Development Environment

**Document ID:** INFRA-01
**Status:** Planned M8 local-environment hardening; a limited lockfile/host/Compose foundation exists today
**Milestone:** M1, M4 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `INFRA-01-T01 <- TEST-01-T02; INFRA-01-T02 <- INFRA-01-T01; INFRA-01-T03 <- INFRA-01-T02; INFRA-01-T04 <- INFRA-01-T03; INFRA-01-T05 <- INFRA-01-T04,TEST-01-T01,TEST-01-T02; INFRA-01-T06 <- INFRA-01-T05,DB-06-T02,BACKEND-02-T02; INFRA-01-T07 <- INFRA-01-T06,DB-01-T05; INFRA-01-T08 <- INFRA-01-T07,TEST-01-T02`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Exact host/Compose workflows, environment isolation, safe reset/seed/migration commands, fixture-only provider modes, local evidence, and current-vs-planned boundary
**Unlocks:** Reliable implementation of M1-M8 tasks and CI parity in INFRA-02
**Risk:** High
**Complexity:** M

## Outcome and timing

A clean laptop can install locked dependencies, run the foundation or future full local stack, migrate/seed an isolated PostgreSQL database, execute deterministic tests, and tear down only its own resources. Local development cannot access production credentials, real recipients, public ingress, or product outreach.

## Current repository state

Implemented: Python 3.13, uv 0.11.26 lock enforcement, Node 24/npm lockfile, Make targets, safe `.env.example`, backend/frontend non-root images, and loopback-only Compose services for PostgreSQL 18, API, idle worker and frontend with outreach false. CI has remotely exercised Compose; Docker was unavailable on the documented local verification host. Missing: product migrations/seed manifest, DBOS runtime, provider fixture modes, Gmail/OAuth, separate test databases, secret fixture store, telemetry, backup service, public/private proxy profiles, and a full-stack local acceptance command.

## Scope and non-goals

In scope: prerequisites, setup, host and Compose modes, named environments, per-run database isolation, deterministic seeds, generated API drift, fake secret/provider stores, local runtime/telemetry, safe reset, cleanup, troubleshooting and evidence. Non-goals: production parity claims, real provider credentials, live Gmail except the separately isolated M1/M6 harness, public hostname/TLS/WAF, production backups, shared developer databases, Kubernetes, Redis/Celery, Kafka, Vault, or a hidden cloud dependency.

## Exact planned implementation surfaces

Extend `Makefile`; add `infra/compose.test.yaml`, `infra/compose.observability.yaml`, `scripts/dev/{preflight,create_database,reset_database,smoke}.sh`, `backend/src/alon_ai/persistence/seeding.py`, fake `VersionedSecretStore`, and signed fixture manifests. Preserve `infra/compose.yaml` as the default local topology. Profiles are `foundation` (today's services), `product` (future runtime modules), and `observability` (local collector only); public ingress is never a local default.

| Environment | Database/secret/provider isolation | Send controls | Permitted network |
| --- | --- | --- | --- |
| host development | explicitly named local DB `alon_ai_dev`; ignored local config; fake secret store | both false | dependency installation and loopback app only |
| Compose development | fixed project `alon-ai-dev`; volume `alon-ai-dev_postgres_data`; fake secrets | both false | container network; published loopback ports only |
| deterministic test | database `alon_ai_test_{run_id}` or per-worker schema; ephemeral fake secrets | both false | denied after setup |
| M1/M6 harness | separate command/config/schema/project and owned-alias credential generation | exact harness control only; product false | explicit Gmail allowlist under TEST-04 |

Canonical setup/check sequence remains:

```sh
make setup
make generate
make lint
make typecheck
make test
make build
```

Container sequence is exact and non-destructive:

```sh
docker compose --project-name alon-ai-dev --env-file .env.example -f infra/compose.yaml config
docker compose --project-name alon-ai-dev --env-file .env.example -f infra/compose.yaml build api worker frontend
docker compose --project-name alon-ai-dev --env-file .env.example -f infra/compose.yaml run --rm api alembic upgrade head
docker compose --project-name alon-ai-dev --env-file .env.example -f infra/compose.yaml up --detach --wait
```

Reset is deliberately separate. `scripts/dev/reset_database.sh --project alon-ai-dev --database alon_ai --confirm alon-ai-dev:alon_ai` first resolves Compose labels, container ID, database name, PostgreSQL system identifier, mounted volume name/path and both controls; it refuses wildcard/empty/mismatched/live labels. It takes a disposable schema manifest, stops API/worker, removes only `alon-ai-dev_postgres_data`, recreates/migrates/seeds, then proves controls false. No `docker system prune`, broad volume glob, or unresolved variable is permitted.

All setup/migration/generation/smoke requirements map exactly to `T7-LOCAL-SMOKE`; reset/cleanup requirements map exactly to destructive `T7-LOCAL-RESET` in the [TEST-01 closed command manifest](../10-testing/01-testing-strategy.md#closed-command-manifest). The invocations use profiles `LOCAL_COMPOSE` and `LOCAL_DISPOSABLE` respectively; reset must include the signed target manifest and confirmation digest. Docker unavailable exits `30`, a label/database/system-ID/volume/control mismatch exits `50` before stop/removal, and incomplete cleanup exits `40`; none counts as pass. Set equality proves the two domains are disjoint and complete.

## Local autonomous-sales fixture topology

All new product capabilities remain planned. Extend the existing loopback Compose topology with the same application workers/services and isolated fixtures; no additional product backend is introduced. Seed both idea origins, accepted offer economics, source/candidate/dossier/PRELIMINARY/FINAL records, conversations/negotiations, calendar intents/slots/actions, four cohorts/checkpoints and multiple global-strategy activations using deterministic synthetic identities.

The recovery/release evidence must bind the accepted OfferPackage/economics/claim hashes; approved agent configurations and GlobalStrategyPackage/StrategyActivation/rollback lineage; campaign/cohort ordinals, membership/query/hash, caps and frozen qualification/causal/evidence/metric versions; CheckpointEvidenceBundle/cutoff/decision/learning triggers; full conversation/reply/negotiation state and counters; BookingIntent/slot/confirmation/action/attempt/result/observation/notification state; current suppression/tombstones/legal-policy; immutable action authorizations/consumptions; costs/reservations; and all current control/checkpoint generations.

Ordinary local/CI profiles deny all Gmail/calendar/provider network and keep PRODUCT_OUTREACH, TEST_INBOX_SENDING, CALENDAR_WRITES and TEST_CALENDAR_WRITES false. Model/read fixtures and separate Gmail/calendar read/write spies are injected only into their named owners; the browser never receives a provider SDK or credential. Dedicated M6 profiles require signed owned-resource gates and distinct credential/calendar/mailbox namespaces; copying a fixture profile cannot enable a real target.

Local startup verifies schema/runtime/API/strategy/retention manifest hashes, current baseline attribution and source scopes before any run. Run the full deterministic sales simulation and bounded crash/replay fixtures against fresh real PostgreSQL. Restart/reset requires exact disposable target identity and cannot reuse real contact/message/calendar evidence. Reset cancels local work and preserves signed fixture reports, not live data; destructive safeguards and TEST-01 runner exit semantics remain unchanged.

## Ordered implementation tasks

<!-- roadmap-task id=INFRA-01-T01 milestone=M1 depends_on=TEST-01-T02 mode=serial locks=dependency-lockfiles -->
- [ ] **Freeze prerequisites and preflight —** Input: lockfiles, runtime floors, repository root, environment enum and TEST-01 signed task7-commands.v1.json checkout/root/profile contract. Operation: verify exact uv/Python/Node/npm/Docker/PostgreSQL versions, ignored config and no real secrets; verify the actual checkout/root/profile against the signed command registry before install/start. Output: machine-readable preflight. Test evidence: wrong version/root/tracked-env/provider-secret negatives. Failure behavior: stop before install/start.
<!-- roadmap-task id=INFRA-01-T02 milestone=M1 depends_on=INFRA-01-T01 mode=serial locks=compose-topology -->
- [ ] **Implement isolated host/Compose modes —** Input: exact service/profile/project/database names. Operation: create per-mode network/database/volume/fake-secret boundaries and loopback ports. Output: reproducible stack. Test evidence: parallel project, port collision, cross-database and forbidden-network tests. Failure behavior: stop only affected project; preserve diagnostics.
<!-- roadmap-task id=INFRA-01-T03 milestone=M1 depends_on=INFRA-01-T02 mode=serial locks=compose-topology -->
- [ ] **Implement safe reset and cleanup —** Input: explicit project/database confirmation and resolved resource labels. Operation: stop foundation writers, remove only the confirmed disposable foundation volume/database, recreate its foundation schema and verify all provider/product execution paths are unavailable; no product migration/control-row claim. Output: clean isolated M1 foundation environment, with product reset verification deferred to its explicit later task. Test evidence: empty/wildcard/wrong-system-ID/production-like target refusal. Failure behavior: perform no deletion.
<!-- roadmap-task id=INFRA-01-T04 milestone=M1 depends_on=INFRA-01-T03 mode=serial locks=compose-topology -->
- [ ] **Document and retain local smoke evidence —** Input: running stack. Operation: check foundation liveness, non-root/loopback/isolation/fixture mode and unavailable provider/product paths; report absent product migrations/client/runtime as unavailable, never passed. Output: honest M1 foundation-only local run manifest. Test evidence: unavailable Docker/provider reported as unavailable, not passed. Failure behavior: leave stack stopped or degraded and show exact failed check.
<!-- roadmap-task id=INFRA-01-T05 milestone=M1 depends_on=INFRA-01-T04,TEST-01-T01,TEST-01-T02 mode=serial locks=test-command-registry -->
- [ ] **Close local command ownership —** Input: implemented M1 foundation setup/smoke/reset requirements and TEST-01 signed coverage/command registries. Operation: bind exact cwd/profile/target guard/artifacts/exit semantics to the two commands and inject target mismatches. Output: signed M1 foundation command mapping; later product reset/smoke mapping remains an explicit later gate. Test evidence: unavailable Docker=`30` and pre-delete wrong identity=`50`. Failure behavior: local lane receives no gate credit.
<!-- roadmap-task id=INFRA-01-T06 milestone=M4 depends_on=INFRA-01-T05,DB-06-T02,BACKEND-02-T02 mode=serial locks=migration-head,openapi-contract,frontend-client -->
- [ ] **Implement product migration, seed, and generation workflow —** Input: DB-06 deterministic seed output and BACKEND-02 M4/M5 no-send OpenAPI/client contract. Operation: upgrade, seed twice, generate the client, and compare committed outputs on the isolated stack established by the preceding M1 tasks. Output: deterministic M4 product local truth. Test evidence: catalog/seed hash and generated no-diff. Failure behavior: no product app starts on stale schema/client.
<!-- roadmap-task id=INFRA-01-T07 milestone=M4 depends_on=INFRA-01-T06,DB-01-T05 mode=serial locks=compose-topology,migration-head -->
- [ ] **Complete product local reset and cleanup —** Input: deterministic M4 migration/seed/generated-client truth, explicit confirmed local project/database/resource labels and outreach-off product control schema. Operation: stop writers, remove only verified local volume/database, recreate, migrate and prove controls false. Output: clean migrated/seeded product local environment with controls false. Test evidence: empty/wildcard/wrong-system-ID/production-like target refusal. Failure behavior: perform no deletion.
<!-- roadmap-task id=INFRA-01-T08 milestone=M4 depends_on=INFRA-01-T07,TEST-01-T02 mode=serial locks=compose-topology,test-command-registry -->
- [ ] **Complete product smoke evidence and local command ownership —** Input: clean reset product environment, generated no-send client/schema truth, TEST-01 signed command/coverage registries and exact product setup/smoke/reset requirements. Operation: check live/ready/frontend, non-root users, worker readiness, schema head, fixture mode and controls. Bind and verify the complete product setup/smoke/reset command/profile/target/artifact/exit map against the existing TEST-01 registry. Output: complete M4 product local smoke/run manifest and signed product setup/smoke/reset command-ownership evidence. Test evidence: unavailable Docker/provider reported as unavailable, not passed. Complete original target/version/hash/exit mapping negatives remain required. Failure behavior: leave stack stopped or degraded and show exact failed check.

## Test strategy

- **Preflight `test_local_preflight_rejects_wrong_root_versions_tracked_secret_and_real_provider_mode`.**
- **Isolation `test_two_compose_projects_share_no_network_volume_database_or_secret_state`.**
- **Seed `test_local_seed_runs_twice_with_same_hash_and_outreach_false`.**
- **Reset `test_reset_resolves_exact_labels_system_id_and_refuses_ambiguous_target`.**
- **Parity `test_local_and_ci_commands_use_same_locked_migration_generation_lint_typecheck_test_build_contract`.**
- **Smoke `test_local_stack_health_nonroot_worker_schema_and_controls_are_evidence_bearing`.**

## Security, privacy, compliance, idempotency, observability, and cost

`.env.example` remains fake and safe; ignored `.env` is not a production secret store. Fixtures contain synthetic identities and signed hashes. Local agent/provider modes deny network and Gmail ports. Reset/seed/smoke commands are idempotent by exact project/database/run ID. Local telemetry uses redacted console or disposable collector and is never uploaded by default. No local result establishes legal compliance or production capacity; all external spend remains zero outside explicit harnesses.

## Failure, rollback, and operator recovery

On dependency drift, migration/seed/generation mismatch, container root user, unknown volume, provider network attempt, leaked canary or control enable: stop affected processes, preserve safe logs/config hashes, rotate any exposed test credential, and recreate only after exact-target preflight. Roll back lock/config changes through Git, not by mutating caches or stamping migrations. If Docker is unavailable, run supported host checks and record Compose as untested.

## Acceptance and retained evidence

- [ ] A clean host can reproduce locked setup/checks and an isolated loopback Compose stack.
- [ ] M1/M6 harness authority cannot leak into ordinary local development.
- [ ] Reset/cleanup cannot resolve or delete a broad, shared or production target.
- [ ] Current foundation checks and future planned services are described without conflating them.

Retain preflight output, dependency/lock hashes, Compose config/image digests, migration/seed/client diffs, smoke results, exact resource labels/system ID for resets and truthful unavailable-tool notes.

## Dependencies and next deliverable

INFRA-01 supplies reproducible commands and isolation to [INFRA-02 CI/release](02-ci-cd-and-release-process.md) and all TEST suites. It creates no cloud/VPS resource and grants no deployment, provider or send authority.
