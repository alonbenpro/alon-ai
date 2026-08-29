# Contract and PostgreSQL Integration Tests

**Document ID:** TEST-02
**Status:** Planned M2-M8 contract/integration suite; current repository proves only foundation migrations, health/readiness, generated health types, and minimal send-gateway unit contracts
**Milestone:** M2 persistence, M3 provider/agent contracts, M6 policy/Gmail integration, M8 API release gate
**Owner:** Solo operator
**Prerequisites:** [DB-01 through DB-06](../02-database/01-core-data-model.md), [AGENT-01](../04-agents/01-agent-runtime-and-contracts.md), provider contracts, [BACKEND-02 exact API manifest](../06-backend/02-api-contracts.md#exact-route-and-openapi-operation-manifest), BACKEND-03/04/05/06, SEC-01/05, and TEST-01
**Outputs:** Strict schema/digest vectors, real-PostgreSQL DDL and transaction proof, provider/API/policy contract matrices, and cross-owner set-equality evidence
**Unlocks:** TEST-03/04 recovery execution, generated frontend client eligibility, and M8 release candidate construction
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Byte-level contracts, named PostgreSQL invariants, sole-writer transactions, and HTTP/provider partitions fail before orchestration or browser work can consume them. Tests use canonical upstream manifests as authority and compare independent fixtures by exact set equality; they do not maintain a weaker alias contract.

## Current repository state

Alembic currently has only the foundation schema, OpenAPI exposes health operations, and the generated TypeScript client covers that surface. PostgreSQL 18 integration runs in CI. The 46 product tables, deferred FKs/triggers/retention commands, 66-operation API, 64+2 release partition, provider result families, full policy engine, incident catalog, agent schemas/evals, and product transactions remain planned.

## Scope and non-goals

In scope: Pydantic strict/extra-forbid/frozen models, RFC 8785, all 46 product tables and named DDL, migrations/seeds/retention, domain states/events, atomic bundles, outbox delivery, six provider capabilities, Gmail read/send unions, agent terminal unions, 66 operations, named response/problem schemas, 14 dedicated final-SEND denials, incident tuple/resolution/repair applicability, sole writers, and generated clients. Non-goals: SQLite substitutes, snapshot approval without semantic review, ORM-only constraint tests, route-count-only assertions, provider SDK objects, or network-backed provider calls.

## Exact planned implementation surfaces

Create `backend/tests/contract/`, `backend/tests/integration/`, `tests/manifests/{tables,api,states_events,policies,incidents,providers}.v1.json`, strict schema snapshots, and `scripts/verify_contract_sets.py`. Use a PostgreSQL role matrix: migration owner, API writer, worker writer, read projection, retention owner, and recipient-lookup owner; unauthorized SQL must fail by role before application checks.

The canonical 46-table set is exactly: `operators`, `experiments`, `workflow_runs`, `system_controls`, `budget_accounts`, `budget_reservations`, `incidents`; `experiment_briefs`, `ideas`, `offer_hypotheses`, `metric_definitions`, `metric_observations`, `metric_snapshots`, `experiment_decisions`; `businesses`, `leads`, `lead_assessments`, `gmail_mailboxes`, `campaigns`, `campaign_members`, `outreach_messages`, `approvals`, `suppression_entries`, `send_intents`, `send_rate_reservations`, `send_attempts`, `provider_results`, `provider_observations`, `replies`, `gmail_history_cursors`; `agent_runs`, `artifacts`, `evidence_items`, `artifact_evidence_links`, `artifact_validations`, `artifact_acceptances`, `evaluation_cases`, `evaluation_results`; `domain_events`, `audit_events`, `command_idempotency`, `outbox_messages`, `outbox_deliveries`, `policy_decisions`, `cost_entries`, `repair_actions`. The test derives DDL names from PostgreSQL catalogs and requires exact equality with this signed manifest.

| Contract family | Required positives | Required negatives | Evidence |
| --- | --- | --- | --- |
| strict models | every schema/version/discriminator branch round-trips | extra/missing/cross-branch fields, wrong literal/type, invalid time/UUID/hash/decimal | JSON Schema hashes and rejection corpus |
| RFC 8785 | DB-01 three normative bytes/SHA-256 reproduced by two implementations | duplicate keys, non-I-JSON numbers, invalid Unicode, whitespace/key-order/escape/schema-type, SQL NULL vs JSON null | byte and digest vectors |
| DDL/migrations | empty/prior/backup schema reaches exactly 46 tables; every named FK/check/unique/index/trigger/owner; seed twice no diff | one-column composite splices, immutable mutation, unsafe downgrade/backfill, secret/real-recipient seed | catalog dump, revision graph, counts/hashes |
| transactions/outbox | aggregate+event+audit+idempotency+outbox atomic; delivery receipt dedupe | failure after every write, duplicate command, poison delivery, direct external effect | row-set hashes and call count zero |
| providers/agents | six capability `SUCCESS|FAILURE`, Gmail `ACCEPTED|CONCLUSIVE_REJECTION|UNKNOWN`, agent `SUCCESS|ABSTAIN|FAILED` | cross-capability result, payload on failure, missing payload digest, provider-native error, usage/ledger mismatch, forbidden authority | schema/ledger fixture hashes |
| agent evaluations | exact eight suites/552 cases/three fresh captures per case (1,656), signed capture sets, two offline scorers and exact AGENT-10 golden/threshold/regression/cost gates | missing/replayed capture, live non-model network, scorer disagreement, hard failure, privacy/authority edge, threshold one unit below | dataset/capture/signature/scorer/promotion hashes |
| API | exact 66 method/path/operationId triples, exact 64 `PRIVATE_DEPLOYMENT` + 2 `PUBLIC_UNSUBSCRIBE`, strict responses/errors/ETags/cursors | duplicate/unclassified route, webhook/general public route, auth/CSRF/idempotency/version bypass, recipient hash in any schema | OpenAPI diff and route registry hash |
| policy | approval eligibility plus final SEND fixed rule order and exact reason registry; all 14 dedicated compliance/signal denials reach zero credential/call | stale/cross-recipient evidence, generic reason substitution, reused queued facts, equalized facts hashes, unknown fact/version | decision/facts/scope hashes and call spies |
| incident | all 18 positive trigger/alert/runbook tuples and exact resolution/repair applicability | every cross-pair, unknown catalog/code, inapplicable resolution/repair, forbidden residual-risk acceptance | DB/application/OpenAPI set equality |

The 14 dedicated denial fixtures are exactly `RECIPIENT_IDENTITY_UNVERIFIED`, `RECIPIENT_JURISDICTION_UNKNOWN`, `RECIPIENT_CONSENT_MISSING`, `RECIPIENT_CONSENT_EXPIRED`, `COUNSEL_EXCEPTION_MISSING`, `LEGAL_REVIEW_MISSING`, `LEGAL_REVIEW_STALE`, `DISCLOSURE_TEMPLATE_INVALID`, `GOOGLE_POLICY_DENIED`, `RECIPIENT_REPLIED`, `RECIPIENT_OPTED_OUT`, `RECIPIENT_HARD_BOUNCED`, `RECIPIENT_COMPLAINT`, and `RECIPIENT_SOFT_BOUNCE_LIMIT`.

Reference command sequence from repository root after implementation:

```sh
cd backend && uv run alembic upgrade head
cd backend && uv run pytest tests/contract tests/integration -q --strict-markers
uv run python scripts/verify_contract_sets.py --database "$ALON_AI_TEST_DATABASE_URL" --openapi frontend/openapi.json --manifests tests/manifests
npm --prefix frontend run api:generate
git diff --exit-code -- frontend/openapi.json frontend/src/lib/api/schema.d.ts
```

`ALON_AI_TEST_DATABASE_URL` must resolve to a newly created database whose server/database IDs are printed and matched against the run manifest before any drop/downgrade/restore operation.

## Ordered implementation tasks

- [ ] **Freeze schema and digest manifests —** Input: DB-01, AGENT-01 and provider exact models. Operation: build independent strict-schema and RFC 8785 vectors and compare schema/version/discriminator sets. Output: signed contract manifests. Test evidence: positive/negative corpus and two-implementation digests. Failure behavior: no consumer generation or migration.
- [ ] **Prove the complete PostgreSQL contract —** Input: DB-01..06 DDL, owners and retention manifest. Operation: migrate clean/prior/restored databases, introspect exact 46 tables/FKs/checks/indexes/triggers/privileges, inject transaction failures and exercise holds/purge. Output: catalog/invariant evidence. Test evidence: set equality plus every composite one-field splice and all-table retention ownership. Failure behavior: rollback current revision; keep workers/API writers stopped.
- [ ] **Prove provider, agent, evaluation and cost contracts —** Input: six capability fixtures, Gmail unions, terminal agent results, exact eight-suite/552-case evaluation manifests and cost ledgers. Operation: validate every allowed branch/error/timeout/budget/cancel and cross-family denial, then prove 1,656 fresh capture completeness/signatures and two offline scorers against all AGENT-10 goldens/gates. Output: byte-compatible adapter and reproducible evaluation acceptance. Test evidence: request/result/ledger/payload/capture/scorer hashes, network isolation and usage/cost reconciliation matrix. Failure behavior: adapter/config cannot be promoted.
- [ ] **Prove API and generated-client partition —** Input: BACKEND-02 exact manifest. Operation: compare OpenAPI, runtime router metadata, Caddy/WAF route manifest fixture and generated client operation sets. Output: exact 66/64+2 evidence. Test evidence: public pair unavailable pre-M9, GET write spy zero, POST-only suppression, and no webhook/general public route. Failure behavior: startup/release rejected.
- [ ] **Prove policy and incident closure —** Input: fixed rules/reasons and `incident.catalog.v1`. Operation: evaluate all positive/applicable and exhaustive negative cross-pairs on real PostgreSQL. Output: matching domain/DB/API registries. Test evidence: 14 no-call denial fixtures, 18 route tuples and resolution/repair applicability. Failure behavior: sending/public ingress/recovery commands disabled.

## Test strategy

- **DDL `test_catalog_exactly_matches_46_table_constraint_index_trigger_and_owner_manifest`.**
- **Digest `test_two_rfc8785_encoders_match_three_normative_vectors_and_reject_invalid_ijson`.**
- **Atomicity `test_command_event_audit_idempotency_outbox_and_delivery_are_failure_atomic`.**
- **Provider `test_capability_gmail_and_agent_discriminated_unions_reject_cross_branch_fields`.**
- **Evaluation `test_eight_suites_552_cases_1656_fresh_captures_and_two_offline_scorers_match_agent10`.**
- **API `test_openapi_router_client_and_edge_manifests_equal_exact_66_and_64_plus_2_partition`.**
- **Policy `test_fourteen_dedicated_final_send_denials_have_zero_credential_and_provider_calls`.**
- **Incident `test_incident_catalog_tuple_resolution_and_repair_applicability_match_database`.**
- **Privileges `test_only_canonical_service_roles_can_write_each_product_or_security_runtime_record`.**

## Security, privacy, compliance, idempotency, observability, and cost

Database fixtures use synthetic identities and restricted roles; recipient SHA-256 is treated as pseudonymous and offline-enumerable, never exported/logged/API-visible. Contract telemetry contains safe schema/operation/reason/version only. Provider cases have zero network and zero cost. Public/legal fixtures prove enforcement shape, not legal approval. Commands and fixture captures are replay-safe by canonical hash and signed manifest.

## Failure, rollback, and operator recovery

On schema drift, irreversible migration, route widening, catalog mismatch, provider-union ambiguity, policy no-call breach, or privilege failure: stop release, disable affected adapter and both send controls, preserve catalog/OpenAPI/row/call evidence, restore the last clean test database only after resolving its identity, and fix the canonical owner rather than weakening the manifest. Never stamp Alembic head, edit rows, or update a golden snapshot merely to turn the suite green.

## Acceptance and retained evidence

- [ ] Exact strict schemas/RFC 8785 vectors and provider/agent/Gmail unions are independently reproducible.
- [ ] PostgreSQL proves all 46 tables, declared DDL/privileges/transactions/retention behavior.
- [ ] API/router/client/edge sets equal 66 operations with the exact private/public partition.
- [ ] Policy 14-denial and incident catalog/applicability matrices are closed and no-call/DB-enforced.

Retain signed manifests, schema/catalog/OpenAPI/client diffs, revision and seed hashes, JUnit/failure-injection results, provider/agent/cost fixture hashes, route/call/privilege traces and exact command output.

## Dependencies and next deliverable

TEST-02 supplies immutable boundary evidence to [TEST-03](03-workflow-recovery-tests.md), [TEST-04](04-gmail-side-effect-tests.md), [TEST-05](05-end-to-end-browser-tests.md), and INFRA-02. A passing contract suite permits those suites to execute; it does not authorize a provider call, public route, deployment, or send.
