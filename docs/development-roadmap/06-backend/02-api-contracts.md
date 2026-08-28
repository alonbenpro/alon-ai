# FastAPI and OpenAPI Contracts

**Document ID:** BACKEND-02
**Status:** Planned product API; only `/health/live` and `/health/ready` exist today
**Milestone:** M4 product API, M6 Gmail/control API, M7 reporting/control plane
**Owner:** Solo operator
**Prerequisites:** [BACKEND-01](01-domain-services.md), DB-01/03/05 command records, planned private authentication, and canonical ARCH-03 states/events
**Outputs:** Exact versioned routes, schemas, status/errors, authentication, idempotency, correlation, pagination, and OpenAPI generation rules
**Unlocks:** M4-M7 frontend generated client and operator workflows
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

FastAPI is the only business HTTP backend and OpenAPI source. Routes validate/authenticate/translate, call one application command or query service, and return its authoritative result; they contain no domain rules or provider SDK calls. Next.js renders the generated client and never proxies secrets, writes PostgreSQL, or becomes a second backend.

## Current repository state

The app currently exposes unauthenticated `/health/live` and database-backed `/health/ready`, request correlation/logging, and CORS. There are no product schemas/routes, authentication, idempotency middleware, OAuth callback, reports, controls, agents, workflows, providers, or generated product client. The current health API remains unchanged until explicitly versioned.

## Scope and non-goals

In scope: private single-operator bearer authentication, exact `/api/v1` product surface, OAuth redirect, command/query schemas, concurrency/idempotency/correlation, RFC 9457 problems, pagination, OpenAPI operation IDs, and generated-client drift. Non-goals: public API, webhooks, GraphQL, frontend server actions as business API, provider credentials in HTTP, synchronous long workflow waits, generic CRUD, or returning ORM/provider objects.

## Exact planned implementation surfaces

Create `api/v1/router.py`, `api/v1/schemas/common.py`, `experiments.py`, `campaigns.py`, `approvals.py`, `messages.py`, `controls.py`, `gmail.py`, `recovery.py`, `reports.py`, `api/dependencies/auth.py`, and `api/errors.py`; compose in `api/app.py`. Preserve `/health/live` and `/health/ready`. OpenAPI remains generated to `frontend/openapi.json` then `frontend/src/lib/api/schema.d.ts`.

### Shared HTTP envelope, authentication, idempotency, and correlation

All `/api/v1` routes except Gmail OAuth callback require `Authorization: Bearer {operator_access_token}` with issuer/audience/signature/expiry and active DB-01 operator subject verified. OAuth callback authority is its signed one-time state plus provider code. Mutating JSON requests require `Content-Type: application/json`; browser cookie auth is not used, avoiding CSRF ambiguity.

Every mutation requires `Idempotency-Key` of 16..200 visible ASCII characters. Updates to DB rows with an explicit optimistic version—`experiments.version`, `outreach_messages.version`, `system_controls.version`, and `gmail_history_cursors.version`—also require `If-Match: "{positive_version}"`; missing is 428, a known pre-dispatch mismatch is 412, and a version race inside the transaction is 409. Campaign commands carry immutable `campaign_version` in the path plus exact `expected_state` in `CampaignControlRequestV1`; approval/mailbox commands carry exact `expected_state`/`expected_status`, lock the row, and rely on legal-state plus idempotency because those DB-03 rows have no mutable version column. The application derives an exact command scope from route/actor/resource and hashes the request using DB-01 `command.request.v1` or the route's named text schema. Same scope/key/hash returns the original status, body, `Location`, ETag when present, and correlation; same key/different hash is 409. Commands that commit work then signal a workflow return 202 without claiming completion.

Client may send `X-Request-ID` UUIDv4; invalid values return 400. Otherwise middleware creates it. Every request creates/propagates UUIDv4 `correlation_id`; commands set `causation_id` to the HTTP request ID. Responses include `X-Request-ID` and `X-Correlation-ID`. Logs use safe IDs/route template/status/duration only.

Success shapes are strict/extra-forbid. A response backed by one of the four explicit optimistic-version columns carries HTTP `ETag: "{version}"`; other resource-specific schemas expose their immutable campaign/brief version or expected state without inventing a mutable version. A mutating response carries the resulting aggregate ETag only when that explicit version changed:

- `ResourceResponseV1={schema_version,data,version,correlation_id}`;
- `CommandReceiptV1={schema_version:"api.command_receipt.v1",command_type,command_scope,idempotency_key,status:"COMMITTED"|"ACCEPTED",aggregate_type,aggregate_id,aggregate_version,workflow_run_id,result_hash,correlation_id}`;
- `PageResponseV1={schema_version,items,next_cursor,as_of,projection_version,correlation_id}`.

Opaque pagination cursor signs route/filter/order/last-key/projection-version/expiry; tamper/mismatch is `VALIDATION_FAILED`. List order is explicitly stable per route. `limit` defaults 50 and is 1..100.

### Exact route and OpenAPI operation manifest

Existing health:

| Method/path | `operationId` | Success | Errors/auth |
| --- | --- | --- | --- |
| `GET /health/live` | `getLiveness` | 200 existing payload | no auth; never checks DB/provider |
| `GET /health/ready` | `getReadiness` | 200 ready or 503 existing degraded payload | no auth; safe dependency detail only |

Gmail/mailboxes:

| Method/path | `operationId` / request -> response | Success |
| --- | --- | --- |
| `POST /api/v1/gmail/oauth/authorizations` | `startGmailAuthorization`; `StartGmailAuthorizationRequestV1` -> `GmailAuthorizationResponseV1` | 201, `Location` is Google authorization URL |
| `GET /api/v1/gmail/oauth/callback` | `completeGmailAuthorization`; query `code,state` | 303 to fixed frontend mailbox result route; failures 303 with opaque result code, never token |
| `GET /api/v1/gmail/mailboxes` | `listGmailMailboxes` -> page ordered `(created_at,mailbox_id)` | 200 |
| `DELETE /api/v1/gmail/mailboxes/{mailbox_id}/authorization` | `revokeGmailAuthorization`; `RevokeGmailAuthorizationRequestV1` -> receipt | 202 after disable/reconcile command; 409 unresolved safety denial |
| `POST /api/v1/gmail/mailboxes/{mailbox_id}/commands/sync` | `syncGmailMailbox`; `SyncGmailMailboxRequestV1` -> receipt | 202 |

Experiments/workflows:

| Method/path | `operationId` / schema | Success |
| --- | --- | --- |
| `POST /api/v1/experiments` | `createExperiment`; `CreateExperimentRequestV1` -> experiment resource | 201 + `Location` |
| `GET /api/v1/experiments` | `listExperiments`; state/cursor/limit -> page ordered `(updated_at DESC,experiment_id)` | 200 |
| `GET /api/v1/experiments/{experiment_id}` | `getExperiment`; resource includes brief/run/control summary | 200 |
| `POST /api/v1/experiments/{experiment_id}/commands/approve-scope` | `approveExperimentScope`; `ApproveExperimentScopeRequestV1` -> receipt | 200 |
| `POST /api/v1/experiments/{experiment_id}/commands/start-research` | `startExperimentResearch`; `StartStageRequestV1` -> receipt | 202 |
| `POST /api/v1/experiments/{experiment_id}/commands/start-lead-qualification` | `startLeadQualification`; `StartStageRequestV1` -> receipt | 202 |
| `POST /api/v1/experiments/{experiment_id}/commands/pause` | `pauseExperiment`; `ControlExperimentRequestV1` -> receipt | 202 |
| `POST /api/v1/experiments/{experiment_id}/commands/resume` | `resumeExperiment`; `ControlExperimentRequestV1` -> receipt | 202 |
| `POST /api/v1/experiments/{experiment_id}/commands/cancel` | `cancelExperiment`; `ControlExperimentRequestV1` -> receipt | 202 |
| `POST /api/v1/experiments/{experiment_id}/commands/retry-stage` | `retryExperimentStage`; `RetryExperimentStageRequestV1` -> receipt | 202 with new run ID |
| `POST /api/v1/experiments/{experiment_id}/commands/revise` | `reviseExperiment`; `ReviseExperimentRequestV1` -> resource | 201 new brief/version |
| `POST /api/v1/experiments/{experiment_id}/commands/record-decision` | `recordExperimentDecision`; `RecordExperimentDecisionRequestV1` -> resource | 201 immutable decision |
| `GET /api/v1/workflow-runs/{workflow_run_id}` | `getWorkflowRun`; canonical projection | 200 |

Campaigns, approvals, messages, controls, recovery:

| Method/path | `operationId` / schema | Success |
| --- | --- | --- |
| `POST /api/v1/experiments/{experiment_id}/campaigns` | `createCampaignVersion`; `CreateCampaignVersionRequestV1` | 201 + `Location` |
| `GET /api/v1/campaigns/{campaign_id}/versions/{campaign_version}` | `getCampaignVersion` | 200 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/activate` | `activateCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/pause` | `pauseCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/resume` | `resumeCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/cancel` | `cancelCampaign`; `CampaignControlRequestV1` | 202 |
| `GET /api/v1/approvals` | `listApprovals`; state/cursor/limit, ordered `(requested_at,approval_id)` | 200 |
| `GET /api/v1/approvals/{approval_id}` | `getApproval` | 200 |
| `POST /api/v1/approvals/{approval_id}/commands/approve` | `approveApproval`; `DecideApprovalRequestV1` | 200 |
| `POST /api/v1/approvals/{approval_id}/commands/deny` | `denyApproval`; `DecideApprovalRequestV1` | 200 |
| `POST /api/v1/approvals/{approval_id}/commands/revoke` | `revokeApproval`; `RevokeApprovalRequestV1` | 200 |
| `GET /api/v1/messages/{message_id}` | `getOutreachMessage`; redacted message/send/reply timeline | 200 |
| `POST /api/v1/messages/{message_id}/commands/request-approval` | `requestMessageApproval`; `RequestApprovalRequestV1` | 201 approval |
| `POST /api/v1/messages/{message_id}/commands/record-send-intent` | `recordMessageSendIntent`; `RecordSendIntentRequestV1` | 202 after atomic intent/queue commit |
| `POST /api/v1/messages/{message_id}/commands/abort-retry` | `abortMessageRetry`; `AbortSendRetryRequestV1` | 200 terminal result |
| `GET /api/v1/controls` | `listSystemControls` | 200 |
| `POST /api/v1/controls/{control_name}/commands/enable` | `enableSystemControl`; `ChangeControlRequestV1` | 200; product enable gate may deny |
| `POST /api/v1/controls/{control_name}/commands/disable` | `disableSystemControl`; `ChangeControlRequestV1` | 200 |
| `GET /api/v1/recovery/send-attempts` | `listUnresolvedSendAttempts`; cursor/limit, ordered `(started_at,send_attempt_id)` | 200 |
| `POST /api/v1/send-attempts/{send_attempt_id}/commands/reconcile` | `reconcileSendAttempt`; `ReconcileSendAttemptRequestV1` | 202 |
| `POST /api/v1/incidents/{incident_id}/commands/repair` | `repairIncident`; `RepairIncidentRequestV1` | 202/200 matching typed repair kind |

Reports are read-only and defined in BACKEND-06:

| Method/path | `operationId` | Success |
| --- | --- | --- |
| `GET /api/v1/reports/experiments/{experiment_id}/overview` | `getExperimentOverviewReport` | 200 |
| `GET /api/v1/reports/experiments/{experiment_id}/funnel` | `getExperimentFunnelReport` | 200 |
| `GET /api/v1/reports/experiments/{experiment_id}/costs` | `getExperimentCostReport` | 200 |
| `GET /api/v1/reports/experiments/{experiment_id}/timeline` | `getExperimentTimelineReport` | 200/page |
| `GET /api/v1/reports/providers` | `getProviderOperationsReport` | 200/page |
| `GET /api/v1/reports/approvals` | `getApprovalQueueReport` | 200/page |

Path IDs parse UUIDv4; campaign versions positive. Literal canonical state/control names are OpenAPI enums, not display labels. Routes not listed are not part of v1. OpenAPI rejects duplicate operation IDs and undocumented response statuses.

### Exact errors and status semantics

All errors use [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) media type `application/problem+json` and strict `ProblemDetailsV1={type,title,status,detail,instance,error_code,request_id,correlation_id,reason_codes,current_version}`. `type` is the literal stable URI `urn:alon-ai:problem:{lowercase_error_code}`; `status` byte-matches the HTTP status; safe detail is at most 300 characters; reason codes are sorted unique; current version is nullable. FastAPI response models filter output to declared fields, and unique operation IDs drive generated clients: [response models](https://fastapi.tiangolo.com/tutorial/response-model/) and [client generation](https://fastapi.tiangolo.com/advanced/generate-clients/). Exact mapping:

| HTTP | `error_code` |
| --- | --- |
| 400 | `VALIDATION_FAILED`, `OAUTH_CALLBACK_INVALID` |
| 401 | `AUTHENTICATION_REQUIRED` |
| 403 | `AUTHORIZATION_DENIED`, `POLICY_DENIED` |
| 404 | `NOT_FOUND` |
| 409 | `IDEMPOTENCY_HASH_CONFLICT`, `VERSION_CONFLICT`, `STATE_TRANSITION_DENIED`, `AMBIGUOUS_SEND_REQUIRES_RECONCILIATION` |
| 412 | `PRECONDITION_FAILED` |
| 422 | FastAPI validation is normalized to `VALIDATION_FAILED` without echoing secrets/content |
| 428 | `IDEMPOTENCY_KEY_REQUIRED`, `PRECONDITION_REQUIRED` |
| 429 | `RATE_LIMITED`, `BUDGET_EXHAUSTED`; include bounded `Retry-After` when known |
| 503 | `DEPENDENCY_UNAVAILABLE` |
| 500 | `INTERNAL_ERROR`; opaque incident reference only |

State/policy denials do not become 500. An `If-Match` value already known not to equal the current ETag returns 412 `PRECONDITION_FAILED`; an optimistic version race discovered inside the command transaction returns 409 `VERSION_CONFLICT`. [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) defines `If-Match` as a lost-update guard. An ambiguous send reconciliation command is 202; attempting resend/requeue is 409. OAuth callback never renders provider text. Query reports may return `stale=true` inside 200 only when their documented source cutoff is complete; unknown/corrupt projection is 503, not misleading partial success.

### Request/response example

```http
POST /api/v1/experiments/7dd7a7b3-5d57-4ae8-b1d9-49307050d7b8/commands/pause
Authorization: Bearer operator-token
Idempotency-Key: pause-20260828-0001
If-Match: "7"
X-Request-ID: 862f761d-a83b-4e8a-a98b-d5edbbe79074
Content-Type: application/json

{"schema_version":"api.control_experiment.request.v1","reason_code":"OPERATOR_REQUEST"}
```

Response is 202 `CommandReceiptV1` only after the pause-request transaction commits; it does not claim runtime acknowledgement or `PAUSED` until WF-06 records it.

## Ordered implementation tasks

- [ ] **Implement shared auth/error/idempotency/correlation dependencies —** Input: operator token, headers, command envelope, application errors. Operation: validate, derive exact scope/hash, map safe problem/status, and propagate IDs. Output: consistent route boundary. Test evidence: auth/header/replay/error snapshot matrix. Failure behavior: no handler/provider/runtime call.
- [ ] **Implement M4/M5 product routes —** Input: BACKEND-01 services and schemas. Operation: add experiment/workflow commands and reads in manifest order. Output: generated no-send client. Test evidence: OpenAPI and real-service integration tests. Failure behavior: route omitted/blocked until service exists.
- [ ] **Implement M6 Gmail/control/recovery routes —** Input: provider/policy/SendGateway/command services and private auth. Operation: add OAuth/mailbox/campaign/approval/message/control/recovery surface. Output: operator-safe commands. Test evidence: call-path/authority/ambiguity/status E2E. Failure behavior: send controls remain false.
- [ ] **Implement M7 report routes —** Input: BACKEND-06 projections. Operation: expose versioned read models/pagination without business logic. Output: stable dashboard API. Test evidence: projection/OpenAPI/browser contract tests. Failure behavior: visible stale/degraded response; no inferred truth.
- [ ] **Generate and gate OpenAPI client —** Input: composed FastAPI app. Operation: emit deterministic schema, validate operation/route/status uniqueness, regenerate TypeScript, and diff. Output: one API source of truth. Test evidence: `test_openapi_generated_client_has_no_drift`. Failure behavior: CI/release blocked.

## Test strategy

- **Contract `test_api_manifest_has_exact_paths_methods_operation_ids_and_statuses`:** no undocumented route.
- **Idempotency `test_command_replay_returns_original_status_body_location_and_correlation`:** hash conflict is 409.
- **Concurrency `test_if_match_required_and_stale_version_never_calls_service`:** 428/412/409 exact; state-only rows use locked expected-state checks.
- **Security `test_openapi_and_problem_details_expose_no_secret_ciphertext_or_provider_payload`:** schema/log scan.
- **Boundary `test_fastapi_routes_call_one_application_service_and_no_provider_or_orm`:** dependency spies/import graph.
- **E2E `test_nextjs_uses_generated_client_and_never_implements_business_route`:** no second backend.

## Security, privacy, compliance, idempotency, observability, and cost

Private operator authentication does not weaken explicit authorization/audit. CORS is the one configured frontend origin; OAuth redirect URIs are exact. Sensitive fields are absent or redacted in OpenAPI/responses/problems/logs. Command keys and expected versions protect double clicks/races. Metrics cover route/status/error/latency/replay/conflict without payloads. Query and command cost is observable; paid/provider work remains separately reserved before call.

## Failure, rollback, and operator recovery

Unknown application error, duplicate operation ID, schema/client drift, auth failure mode, or accidental provider/ORM reach blocks release. Roll back API code while preserving command rows/results; replay remains exact. During degraded dependencies, keep mutations/send controls closed and expose safe 503/incident status. Never repair by changing a stored HTTP result or bypassing application commands.

## Acceptance and retained evidence

- [ ] Every v1 path/method/operation/status/schema/error/auth rule is exact and generated once from FastAPI.
- [ ] Mutations are authenticated, idempotent, version-aware, correlated, and safe on replay.
- [ ] Async receipts distinguish committed request from workflow/provider completion.
- [ ] Next.js has no business/provider/database authority and consumes the drift-free generated client.
- [ ] Current health-only implementation truth is not overstated.

Retain OpenAPI/schema/client artifacts, route manifest checker, auth/idempotency/version/status tests, safe error/log scans, application-boundary graph, OAuth/control/ambiguity E2E traces, and generated-client drift output.

## Dependencies and next deliverable

BACKEND-02 depends on BACKEND-01 and consumes BACKEND-03 through BACKEND-06 as their milestones arrive. It unlocks the M4-M7 generated frontend client; no route can unlock provider authority beyond its underlying application gate.
