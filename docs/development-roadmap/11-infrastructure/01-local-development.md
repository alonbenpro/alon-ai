# Reproducible Local Development Environment

**Document ID:** INFRA-01
**Status:** Planned M8 local-environment hardening; a limited lockfile/host/Compose foundation exists today
**Milestone:** M0-M8 developer reproducibility; M8 operations prerequisite
**Owner:** Solo operator
**Prerequisites:** Current `Makefile`, `.env.example`, Dockerfiles, `infra/compose.yaml`, [local runbook](../../runbooks/local-development.md), TEST-01/02, and the selected Pydantic AI/DBOS/PostgreSQL architecture
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

## Ordered implementation tasks

- [ ] **Freeze prerequisites and preflight —** Input: lockfiles, runtime floors, repository root and environment enum. Operation: verify exact uv/Python/Node/npm/Docker/PostgreSQL versions, ignored config and no real secrets. Output: machine-readable preflight. Test evidence: wrong version/root/tracked-env/provider-secret negatives. Failure behavior: stop before install/start.
- [ ] **Implement isolated host/Compose modes —** Input: exact service/profile/project/database names. Operation: create per-mode network/database/volume/fake-secret boundaries and loopback ports. Output: reproducible stack. Test evidence: parallel project, port collision, cross-database and forbidden-network tests. Failure behavior: stop only affected project; preserve diagnostics.
- [ ] **Implement migration/seed/generation workflow —** Input: DB-06 seed manifest and BACKEND-02 OpenAPI. Operation: upgrade, seed twice, generate client and compare committed outputs. Output: deterministic local truth. Test evidence: catalog/seed hash and generated no-diff. Failure behavior: no app start on stale schema/client.
- [ ] **Implement safe reset and cleanup —** Input: explicit project/database confirmation and resolved resource labels. Operation: stop writers, remove only verified local volume/database, recreate, migrate and prove controls false. Output: clean local environment. Test evidence: empty/wildcard/wrong-system-ID/production-like target refusal. Failure behavior: perform no deletion.
- [ ] **Document and retain local smoke evidence —** Input: running stack. Operation: check live/ready/frontend, non-root users, worker readiness, schema head, fixture mode and controls. Output: local run manifest. Test evidence: unavailable Docker/provider reported as unavailable, not passed. Failure behavior: leave stack stopped or degraded and show exact failed check.
- [ ] **Close local command ownership —** Input: every setup/smoke/reset requirement and TEST-01 registry. Operation: bind exact cwd/profile/target guard/artifacts/exit semantics to the two commands and inject target mismatches. Output: signed mapping. Test evidence: unavailable Docker=`30` and pre-delete wrong identity=`50`. Failure behavior: local lane receives no gate credit.

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
