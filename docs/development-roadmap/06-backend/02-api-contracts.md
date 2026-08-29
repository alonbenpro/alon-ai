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

In scope: private single-operator Google OIDC session delivery owned by FastAPI, exact `/api/v1` product surface, distinct Gmail OAuth, command/query schemas, concurrency/idempotency/correlation/CSRF, RFC 9457 problems, pagination, OpenAPI operation IDs, and generated-client drift. Non-goals: public API, Next.js authentication backend, JavaScript-visible identity/access/refresh/session tokens, webhooks, GraphQL, frontend server actions as business API, provider credentials in HTTP, synchronous long workflow waits, generic CRUD, or returning ORM/provider objects.

## Exact planned implementation surfaces

Create `api/v1/router.py`, `api/v1/schemas/common.py`, `auth.py`, `experiments.py`, `campaigns.py`, `approvals.py`, `messages.py`, `suppressions.py`, `artifacts.py`, `controls.py`, `gmail.py`, `recovery.py`, `reports.py`, `api/dependencies/auth.py`, `api/dependencies/csrf.py`, `api/operator_sessions.py`, and `api/errors.py`; compose in `api/app.py`. Preserve `/health/live` and `/health/ready`. OpenAPI remains generated to `frontend/openapi.json` then `frontend/src/lib/api/schema.d.ts`.

### Shared HTTP envelope, authentication, idempotency, and correlation

The four `/api/v1/auth/*` routes establish the browser session; Gmail OAuth remains a separate mailbox-credential saga. All other `/api/v1` routes require the opaque `__Host-alon_ai_session` cookie resolved by FastAPI to one active DB-01 operator whose Google OIDC issuer/subject byte-match configured allowlist values. The cookie is 256-bit random, rotated on login/reauth and every 15 minutes of active use, `Secure; HttpOnly; SameSite=Strict; Path=/; Domain` absent, with 30-minute idle and 8-hour absolute expiry. `Max-Age` is the remaining absolute lifetime capped at 28,800 seconds and `Expires` is that fixed absolute UTC instant; rotation never extends it. Expiry/revocation/logout respond with `Max-Age=0`/past `Expires`, and logout also clears any flow cookie. The server-side `OperatorSessionStore` owns current/previous-handle overlap for 30 seconds, revocation, idle/absolute expiry, and logout; Task 6 chooses/hardens its persistence without changing this HTTP contract. No identity/access/refresh/session token appears in URL, response JSON, JavaScript, localStorage, sessionStorage, or `NEXT_PUBLIC_*`.

OIDC start creates one server-side flow with state hash, PKCE S256 verifier/challenge, nonce hash, exact issuer/client/redirect IDs, safe validated internal return path, and 10-minute expiry. It sets only `__Host-alon_ai_oidc_flow` as a 256-bit opaque `Secure; HttpOnly; SameSite=Lax; Path=/; Domain` absent and `Max-Age=600` cookie. Callback requires the flow cookie and exact query union `{code,state}` or `{error,state}`; it always verifies and consumes state/flow once. The code arm also verifies PKCE/nonce/signature/issuer/audience/time and exact configured operator subject before rotating the session; the only accepted error arm is provider `access_denied`. It clears the flow cookie and 303-redirects only to the stored allowlisted relative path or fixed failure location. Successful callback redirects to the stored allowlisted relative `return_path`; the only failure locations are `303 {operator_origin}/?operator_auth=auth_invalid`, `...?operator_auth=auth_denied`, or `...?operator_auth=auth_expired`. Provider text/email/tokens are never rendered or logged. Reauthentication replaces the prior session and revokes it after the overlap. Logout revokes the server record before expiring the cookie. Auth start/callback/session/logout emit safe audit with subject hash, flow/session IDs, result/reason, correlation, and no token or claims payload.

Every unsafe session-authenticated request requires exact configured `Origin`, `Sec-Fetch-Site: same-origin`, and constant custom header `X-CSRF-Intent: operator-command-v1`; logout uses `X-CSRF-Intent: operator-session-v1`. Missing/mismatched Origin/fetch metadata/header is 403 `AUTHORIZATION_DENIED` reason `CSRF_CHECK_FAILED` before command dispatch. CORS permits only the configured operator frontend origin and credentials. Mutating JSON requests require `Content-Type: application/json`. Gmail OAuth callback authority remains the operator/flow binding inside signed+encrypted state and executes only `CompleteGmailAuthorization`; it never uses or exposes the OIDC flow/session.

Every business mutation except the Gmail OAuth callback requires caller-supplied `Idempotency-Key` of 16..200 visible ASCII characters. OIDC start requires the key but binds it to the anonymous flow cookie/Origin; OIDC callback derives its one-time flow key; session GET/logout are idempotent session operations and do not enter the business command registry. Updates to explicit versions—`experiments.version`, `outreach_messages.version`, `suppression_entries.version`, `system_controls.version`, and `gmail_history_cursors.version`—require `If-Match: "{positive_version}"`; missing is 428, known mismatch 412, transactional race 409. Campaign commands carry immutable positive `campaign_version` in the path plus exact `expected_state`; approval/mailbox/workflow/artifact commands lock exact expected state/status. Artifact commands additionally require exact `artifact_version` and `content_hash`. The Gmail callback derives `command_scope=gmail.oauth.complete:{oauth_flow_id}` and `idempotency_key=oauth-flow:{oauth_flow_id}` and preserves the existing exact resume/replay rules. The application derives a route/actor/resource scope and DB-01 request hash. Same scope/key/hash returns the original status/body/Location/ETag/correlation; changed hash is 409. Commands that commit work then signal a workflow return 202 without claiming completion.

Client may send `X-Request-ID` UUIDv4; invalid values return 400. Otherwise middleware creates it. Every request creates/propagates UUIDv4 `correlation_id`; commands set `causation_id` to the HTTP request ID. Responses include `X-Request-ID` and `X-Correlation-ID`. Logs use safe IDs/route template/status/duration only.

Success shapes are strict/extra-forbid. A response backed by one of the five explicit optimistic-version columns carries HTTP `ETag: "{version}"`; other resource-specific schemas expose their immutable campaign/brief version or expected state without inventing a mutable version. A mutating response carries the resulting aggregate ETag only when that explicit version changed:

- `ResourceResponseV1={schema_version,data,version,correlation_id}`;
- `CommandReceiptV1={schema_version:"api.command_receipt.v1",command_type,command_scope,idempotency_key,status:"COMMITTED"|"ACCEPTED",aggregate_type,aggregate_id,aggregate_version,workflow_run_id,result_hash,correlation_id}`;
- `PageResponseV1={schema_version,items,next_cursor,as_of,projection_version,correlation_id}`.

Exact named resource/query schemas are strict and extra-forbid; braces below are the complete browser allowlist, not examples:

- `CampaignVersionResponseV1={schema_version:"api.campaign_version.response.v1",data:{campaign_version_id,campaign_id,campaign_version,experiment_id,supersedes_campaign_version_id,state,offer_id,offer_version,policy_version,send_window_start,send_window_end,reply_window_end,daily_cap,total_cap,eligible_member_count,removed_member_count,members:[{campaign_member_id,lead_id,recipient_address_hash,status,lead_state,identity_state,suppression_entry_id,message:{message_id,mailbox_id,state,version,content_hash,approval_id},created_at,removed_at}],created_at,updated_at},correlation_id}`.
- `ApprovalResponseV1={schema_version:"api.approval.response.v1",data:{approval_id,experiment_id,campaign_id,campaign_version,campaign_member_id,lead_id,message_id,message_version,message_content_hash,mailbox_id,provider_account_hash,intended_operation:"SEND",scope_schema_version,scope_hash,artifact_version_refs,artifact_version_refs_hash,eligibility_policy_decision_id,eligibility_policy_scope,eligibility_policy_version,eligibility_facts_hash,eligibility_policy_allowed,current_authority_valid,state,max_send_count,expires_at,reason_code,requested_at,decided_at,stale_reason_codes},correlation_id}`.
- `OutreachMessageResponseV1={schema_version:"api.outreach_message.response.v1",data:{message_id,experiment_id,campaign_id,campaign_version,campaign_member_id,lead_id,mailbox_id,provider_account_hash,artifact_id,state,version,content_hash,approval:{approval_id,state,scope_hash,max_send_count,expires_at,current_authority_valid,stale_reason_codes},send_intent:{send_intent_id,state,rfc_message_id_hash,policy_decision_id},send_attempt:{send_attempt_id,attempt_number,state,provider_result_id,provider_observation_ids,ambiguity_incident_id,retry_not_before,retry_count,retry_cap},reply:{reply_id,state,classification_artifact_id},timeline:[{timeline_item_id,event_type,state,occurred_at,reason_codes,safe_reference_ids}],created_at,updated_at},version,correlation_id}`.
- `IncidentRepairResponseV1={schema_version:"api.incident_repair.response.v1",data:{incident_id,repair_kind,incident_state,resolution_code,evidence_ref,workflow_run_id,command_status,opened_at,resolved_at,updated_at},correlation_id}`.
- `SuppressionResponseV1={schema_version:"api.suppression.response.v1",data:{suppression_entry_id,scope,business_id,recipient_hash,reason_code,source:"OPERATOR",active,version,created_at,deactivated_at},version,correlation_id}`.
- `ArtifactResponseV1={schema_version:"api.artifact.response.v1",data:{artifact_id,experiment_id,artifact_type,artifact_schema_version,artifact_version,status,agent_run_id,agent_type,agent_version,prompt_version,model_provider,model_name,model_version,toolset_version,input_snapshot_hash,content_hash,allowlisted_content,confidence,abstention_reason,supersedes_artifact_id,latest_validation:{artifact_validation_id,validator_version,schema_valid,provenance_valid,reason_codes,facts_hash,created_at},acceptance:{artifact_acceptance_id,acceptance_mode,gate_version,scope_hash,created_at},evidence_count,evaluation_result_ids,redaction_state,created_at},correlation_id}`.
- `ArtifactEvidenceResponseV1={schema_version:"api.artifact_evidence.response.v1",data:{artifact_id,evidence_item_id,evidence_type,source_uri,source_provider,retrieved_at,published_at,content_hash,mime_type,language,license_basis,redaction_state,claim_pointer,relationship,source_excerpt_hash,created_at},correlation_id}`; `capture_ref` and source content are never serialized.
- `EvaluationResultResponseV1={schema_version:"api.evaluation_result.response.v1",data:{evaluation_result_id,evaluation_case_id,suite_name,suite_version,case_key,agent_run_id,evaluator_version,scores_schema_version,scores,scores_hash,passed,reason_codes,sensitivity_class,input_hash,expected_hash,created_at},correlation_id}`; restricted case snapshots/rubrics are omitted.
- `OperatorAuthorizationResponseV1={schema_version:"api.operator_authorization.response.v1",authorization_url,flow_expires_at,correlation_id}`, `OperatorSessionResponseV1={schema_version:"api.operator_session.response.v1",operator_id,subject_hash,issued_at,idle_expires_at,absolute_expires_at,reauth_required,correlation_id}`, and `OperatorSessionEndedResponseV1={schema_version:"api.operator_session_ended.response.v1",ended:true,ended_at,correlation_id}`. None contains provider claims/tokens/email.

Opaque pagination cursor signs route/filter/order/last-key/projection-version/expiry; tamper/mismatch is `VALIDATION_FAILED`. List order is explicitly stable per route. `limit` defaults 50 and is 1..100.

### Exact route and OpenAPI operation manifest

Existing health:

| Method/path | `operationId` | Success | Errors/auth |
| --- | --- | --- | --- |
| `GET /health/live` | `getLiveness` | 200 existing payload | no auth; never checks DB/provider |
| `GET /health/ready` | `getReadiness` | 200 ready or 503 existing degraded payload | no auth; safe dependency detail only |

Operator OIDC/session (separate from Gmail OAuth):

| Method/path | `operationId` / request -> response | Success/auth |
| --- | --- | --- |
| `POST /api/v1/auth/authorizations` | `startOperatorAuthorization`; `StartOperatorAuthorizationRequestV1={schema_version:"api.operator_authorization.start.v1",return_path}` -> `OperatorAuthorizationResponseV1` | 201 + Google `Location`; no session required; exact Origin/fetch metadata + `Idempotency-Key`; flow cookie set |
| `GET /api/v1/auth/callback` | `completeOperatorAuthorization`; query union of `{code,state}` or `{error,state}` + flow cookie -> fixed redirect | 303; sets rotated session and clears flow only for verified configured subject; fixed safe failure redirects |
| `GET /api/v1/auth/session` | `getOperatorSession` -> `OperatorSessionResponseV1` | 200 and optional rotated `Set-Cookie`; 401 expired/revoked/missing; no token/claims payload |
| `DELETE /api/v1/auth/session` | `endOperatorSession` -> `OperatorSessionEndedResponseV1` | 200 after server revocation and cookie expiry; exact Origin/fetch metadata/`X-CSRF-Intent: operator-session-v1` |

Gmail/mailboxes:

| Method/path | `operationId` / request -> response | Success |
| --- | --- | --- |
| `POST /api/v1/gmail/oauth/authorizations` | `startGmailAuthorization`; `StartGmailAuthorizationRequestV1` -> `GmailAuthorizationResponseV1` | 201, `Location` is Google authorization URL |
| `GET /api/v1/gmail/oauth/callback` | `completeGmailAuthorization`; query `code,state` -> registered `CompleteGmailAuthorization` | 303 only after exact ACTIVE handle/version and mailbox+SUCCEEDED commit; post-DB replay returns stored redirect; conflict/invalid/undurable-exchange map to opaque `oauth_conflict`/`oauth_invalid`/`oauth_restart_required`; resumable STAGED/ACTIVE exhaustion is 503 + `Retry-After` with no result commit |
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
| `POST /api/v1/experiments/{experiment_id}/commands/start-outreach-and-reply` | `startOutreachAndReply`; `StartOutreachAndReplyRequestV1={schema_version,expected_campaign_id,expected_campaign_version,expected_campaign_state:"ACTIVE",m1_gate_id,m6_gate_id}` -> `CommandReceiptV1` | 202 after `READY_FOR_OUTREACH -> OUTREACH_ACTIVE` and finite run commit; exact M1/M6/active-campaign/control/evidence guards |
| `POST /api/v1/experiments/{experiment_id}/commands/start-evaluation` | `startExperimentEvaluation`; `StartExperimentEvaluationRequestV1={schema_version,expected_state:enum[READY_FOR_OUTREACH,EVALUATING],metric_snapshot_id,evidence_bundle_artifact_id,rule_version}` -> `CommandReceiptV1` | 202 after finite evaluation run commit; no-send or closed-outreach evidence gate |
| `POST /api/v1/experiments/{experiment_id}/commands/pause` | `pauseExperiment`; `ControlExperimentRequestV1` -> receipt | 202 |
| `POST /api/v1/experiments/{experiment_id}/commands/resume` | `resumeExperiment`; `ControlExperimentRequestV1` -> receipt | 202 |
| `POST /api/v1/experiments/{experiment_id}/commands/cancel` | `cancelExperiment`; `ControlExperimentRequestV1` -> receipt | 202 |
| `POST /api/v1/experiments/{experiment_id}/commands/retry-stage` | `retryExperimentStage`; `RetryExperimentStageRequestV1` -> receipt | 202 with new run ID |
| `POST /api/v1/experiments/{experiment_id}/commands/revise` | `reviseExperiment`; `ReviseExperimentRequestV1` -> resource | 201 new brief/version |
| `POST /api/v1/experiments/{experiment_id}/commands/record-decision` | `recordExperimentDecision`; `RecordExperimentDecisionRequestV1` -> resource | 201 immutable decision |
| `GET /api/v1/workflow-runs/{workflow_run_id}` | `getWorkflowRun`; canonical projection | 200 |
| `POST /api/v1/workflow-runs/{workflow_run_id}/commands/cancel` | `cancelWorkflowRun`; `CancelWorkflowRunRequestV1={schema_version,expected_state:enum[PENDING,RUNNING,PAUSE_REQUESTED,PAUSED],reason_code}` -> `CommandReceiptV1` | 202 after `CANCEL_REQUESTED` commit; operator session, CSRF, idempotency, locked expected state; resulting finite run remains queryable |

Campaigns, approvals, messages, controls, recovery:

| Method/path | `operationId` / schema | Success |
| --- | --- | --- |
| `POST /api/v1/experiments/{experiment_id}/campaigns` | `createCampaignVersion`; `CreateCampaignVersionRequestV1` -> `CampaignVersionResponseV1` | 201 + `Location` |
| `GET /api/v1/campaigns/{campaign_id}/versions/{campaign_version}` | `getCampaignVersion` -> `CampaignVersionResponseV1` | 200 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/ready` | `readyCampaign`; `ReadyCampaignRequestV1={schema_version,expected_state:"DRAFT",offer_id,offer_version,policy_version}` -> `CampaignVersionResponseV1` | 200 `DRAFT -> READY`; immutable path version + locked state; exact offer/policy, eligible-member, draft/approval guards; `campaign.ready.v1` |
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
| `POST /api/v1/messages/{message_id}/commands/request-approval` | `requestMessageApproval`; `RequestApprovalRequestV1` -> `ApprovalResponseV1` | 201 approval |
| `POST /api/v1/messages/{message_id}/commands/record-send-intent` | `recordMessageSendIntent`; `RecordSendIntentRequestV1` | 202 after atomic intent/queue commit |
| `POST /api/v1/messages/{message_id}/commands/abort-retry` | `abortMessageRetry`; `AbortSendRetryRequestV1` -> `OutreachMessageResponseV1` | 200 terminal message |
| `GET /api/v1/controls` | `listSystemControls` | 200 |
| `POST /api/v1/controls/{control_name}/commands/enable` | `enableSystemControl`; `ChangeControlRequestV1` | 200; product enable gate may deny |
| `POST /api/v1/controls/{control_name}/commands/disable` | `disableSystemControl`; `ChangeControlRequestV1` | 200 |
| `GET /api/v1/recovery/overview` | `getRecoveryOverview`; cursor/limit -> `PageResponseV1[RecoveryOverviewItemV1]` ordered `(attention_since,record_kind,record_id)` | 200 authenticated snapshot spanning workflow runs, IN_PROGRESS commands, unresolved attempts, cursor incidents, and repair actions; 400 cursor, 409 expired snapshot restart, 503 corrupt source |
| `GET /api/v1/recovery/send-attempts` | `listUnresolvedSendAttempts`; cursor/limit, ordered `(started_at,send_attempt_id)` | 200 |
| `POST /api/v1/send-attempts/{send_attempt_id}/commands/reconcile` | `reconcileSendAttempt`; `ReconcileSendAttemptRequestV1` | 202 |
| `POST /api/v1/incidents/{incident_id}/commands/repair` | `repairIncident`; `RepairIncidentRequestV1` -> `IncidentRepairResponseV1` | 202/200 matching typed repair kind |

Artifacts, evidence, and evaluation:

| Method/path | `operationId` / schema | Success |
| --- | --- | --- |
| `GET /api/v1/artifacts/{artifact_id}` | `getArtifact` -> `ArtifactResponseV1` | 200 schema/provenance/latest validation/acceptance/agent config/version/hash/redaction metadata |
| `GET /api/v1/artifacts/{artifact_id}/evidence` | `listArtifactEvidence`; cursor/limit -> `PageResponseV1[ArtifactEvidenceResponseV1]`, ordered `(created_at,evidence_item_id,claim_pointer,relationship)` | 200 allowlisted citation/link/redaction fields; no restricted capture/content |
| `GET /api/v1/evaluation-results/{evaluation_result_id}` | `getEvaluationResult` -> `EvaluationResultResponseV1` | 200 allowlisted case/suite/evaluator/config/scores/pass/reasons/version/hash/sensitivity fields |
| `POST /api/v1/artifacts/{artifact_id}/commands/accept` | `acceptArtifact`; `AcceptArtifactRequestV1={schema_version,artifact_version,content_hash,expected_status:"VALIDATED",reason_code}` -> `ArtifactResponseV1` | 200; locked exact version/hash/status, deterministic validation must pass; `artifact.accepted.v1` + audit |
| `POST /api/v1/artifacts/{artifact_id}/commands/reject` | `rejectArtifact`; `RejectArtifactRequestV1={schema_version,artifact_version,content_hash,expected_status:enum[PRODUCED,VALIDATED],reason_code}` -> `ArtifactResponseV1` | 200; locked exact version/hash/status; `artifact.rejected.v1` + audit |

Suppressions (safe hashes/IDs only):

| Method/path | `operationId` / schema | Success |
| --- | --- | --- |
| `GET /api/v1/suppressions` | `listSuppressions`; scope/active/cursor/limit -> `PageResponseV1[SuppressionResponseV1]`, ordered `(created_at,suppression_entry_id)` | 200; fresh uncached authoritative page |
| `POST /api/v1/suppressions` | `createSuppression`; `CreateSuppressionRequestV1={schema_version,scope:enum[GLOBAL,BUSINESS,RECIPIENT],business_id,recipient_hash,reason_code}` -> `SuppressionResponseV1` | 201 + `Location`; target union exact; source forced `OPERATOR`; event/audit commit |
| `POST /api/v1/suppressions/{suppression_entry_id}/commands/deactivate` | `deactivateSuppression`; `DeactivateSuppressionRequestV1={schema_version,expected_active:true,reason_code}` -> `SuppressionResponseV1` | 200 with `If-Match`; only while both send controls false, no matching nonterminal intent/message or ambiguity, and no blocker; emits deactivation event/audit |

Reports are read-only and defined in BACKEND-06:

| Method/path | `operationId` | Success |
| --- | --- | --- |
| `GET /api/v1/reports/experiments/{experiment_id}/overview` | `getExperimentOverviewReport` | 200 |
| `GET /api/v1/reports/experiments/{experiment_id}/funnel` | `getExperimentFunnelReport` | 200 |
| `GET /api/v1/reports/experiments/{experiment_id}/costs` | `getExperimentCostReport` | 200 |
| `GET /api/v1/reports/experiments/{experiment_id}/timeline` | `getExperimentTimelineReport` | 200/page |
| `GET /api/v1/reports/providers` | `getProviderOperationsReport` | 200/page |
| `GET /api/v1/reports/approvals` | `getApprovalQueueReport` | 200/page |

Path IDs parse UUIDv4; campaign versions positive. Literal canonical state/control names are OpenAPI enums, not display labels. Routes not listed are not part of v1. The manifest is exactly 64 routes/64 unique operation IDs including `getRecoveryOverview`, all four operator-session operations, all four newly exposed workflow/campaign commands, all three suppression operations, and all five artifact/evidence/evaluation operations. OpenAPI rejects duplicates and undocumented response statuses. The generated Next.js recovery dashboard may call only `getRecoveryOverview`/the listed typed commands; it cannot reconstruct recovery truth from logs.

### Exact corrected-surface preconditions and failures

This table is the operation-level contract for the 16 added operations; listed statuses are exhaustive in addition to their declared success, and every code uses the global `ProblemDetailsV1` mapping below.

| Operations | Authentication / replay / concurrency | Exact non-success HTTP statuses |
| --- | --- | --- |
| `startOperatorAuthorization` | no session; exact Origin/fetch metadata; anonymous-flow `Idempotency-Key`; strict JSON | 400, 403, 409, 428, 503 |
| `completeOperatorAuthorization` | one unexpired opaque flow cookie plus state; single-use query union; no caller key | always safe 303 after internal 400/403/503 classification; no Problem Details/provider text reaches browser |
| `getOperatorSession` | opaque session cookie; rotation may set a replacement cookie | 401, 503 |
| `endOperatorSession` | active opaque session; Origin/fetch metadata and session CSRF intent; server revocation precedes cookie expiry | 401, 403, 503 |
| `readyCampaign` | operator session, command CSRF/key, immutable path version, locked `expected_state=DRAFT`; no `If-Match` | 400, 401, 403, 404, 409, 428, 503 |
| `startOutreachAndReply`, `startExperimentEvaluation` | operator session, command CSRF/key, latest experiment `If-Match`, locked expected state and exact evidence refs | 400, 401, 403, 404, 409, 412, 428, 429, 503 |
| `cancelWorkflowRun` | operator session, command CSRF/key, locked nonterminal expected run state; no run version invented | 400, 401, 403, 404, 409, 428, 503 |
| `listSuppressions` | operator session; uncached server read; signed filter-bound cursor | 400, 401, 403, 503 |
| `createSuppression` | operator session, command CSRF/key, strict target union and reason; no `If-Match` | 400, 401, 403, 409, 428, 503 |
| `deactivateSuppression` | operator session, command CSRF/key, row `If-Match`, `expected_active=true`, reason and fail-closed guards | 400, 401, 403, 404, 409, 412, 428, 503 |
| `getArtifact`, `getEvaluationResult` | operator session; allowlisted read only | 401, 403, 404, 503 |
| `listArtifactEvidence` | operator session; allowlisted read with signed cursor | 400, 401, 403, 404, 409, 503 |
| `acceptArtifact`, `rejectArtifact` | operator session, command CSRF/key, locked exact artifact version/hash/status and mandatory canonical reason; no mutable ETag invented | 400, 401, 403, 404, 409, 428, 503 |

### Exact errors and status semantics

All errors use [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) media type `application/problem+json` and strict `ProblemDetailsV1={type,title,status,detail,instance,error_code,request_id,correlation_id,reason_codes,current_version}`. `type` is the literal stable URI `urn:alon-ai:problem:{lowercase_error_code}`; `status` byte-matches the HTTP status; safe detail is at most 300 characters; reason codes are sorted unique; current version is nullable. FastAPI response models filter output to declared fields, and unique operation IDs drive generated clients: [response models](https://fastapi.tiangolo.com/tutorial/response-model/) and [client generation](https://fastapi.tiangolo.com/advanced/generate-clients/). Exact mapping:

| HTTP | `error_code` |
| --- | --- |
| 400 | `VALIDATION_FAILED`, `OAUTH_CALLBACK_INVALID`, `OIDC_CALLBACK_INVALID` |
| 401 | `AUTHENTICATION_REQUIRED` |
| 403 | `AUTHORIZATION_DENIED`, `POLICY_DENIED`; CSRF/Origin/fetch-metadata failure is `AUTHORIZATION_DENIED` reason `CSRF_CHECK_FAILED` |
| 404 | `NOT_FOUND` |
| 409 | `IDEMPOTENCY_HASH_CONFLICT`, `VERSION_CONFLICT`, `STATE_TRANSITION_DENIED`, `AMBIGUOUS_SEND_REQUIRES_RECONCILIATION` |
| 412 | `PRECONDITION_FAILED` |
| 422 | FastAPI validation is normalized to `VALIDATION_FAILED` without echoing secrets/content |
| 428 | `IDEMPOTENCY_KEY_REQUIRED`, `PRECONDITION_REQUIRED` |
| 429 | `RATE_LIMITED`, `BUDGET_EXHAUSTED`; include bounded `Retry-After` when known |
| 503 | `DEPENDENCY_UNAVAILABLE` |
| 500 | `INTERNAL_ERROR`; opaque incident reference only |

OIDC callback invalid/expired/denied conditions map internally to `OIDC_CALLBACK_INVALID` or `AUTHORIZATION_DENIED` and then only the fixed safe redirect; missing/expired/revoked session is 401 `AUTHENTICATION_REQUIRED` with reason `SESSION_MISSING`, `SESSION_IDLE_EXPIRED`, `SESSION_ABSOLUTE_EXPIRED`, `SESSION_REVOKED`, or `REAUTH_REQUIRED`. OIDC/Gmail state/code/provider text never enters Problem Details. Suppression deactivation guard failure is 409 `STATE_TRANSITION_DENIED` reasons `SUPPRESSION_TARGET_IN_FLIGHT`, `SUPPRESSION_AMBIGUITY_OPEN`, `SUPPRESSION_CONTROLS_NOT_DISABLED`, or `SUPPRESSION_NOT_ACTIVE`; stale ETag is 412. Artifact exact version/hash/status/supersession failures are 409 `VERSION_CONFLICT`/`STATE_TRANSITION_DENIED` reasons `ARTIFACT_VERSION_MISMATCH`, `ARTIFACT_HASH_MISMATCH`, `ARTIFACT_NOT_VALIDATED`, `ARTIFACT_SUPERSEDED`, or `ARTIFACT_ALREADY_TERMINAL`. Campaign readiness and stage/run guard failures are 409 `STATE_TRANSITION_DENIED` or 403 `POLICY_DENIED` with sorted canonical reasons; no runtime/service call occurs.

State/policy denials do not become 500. An `If-Match` value already known not to equal the current ETag returns 412 `PRECONDITION_FAILED`; an optimistic version race discovered inside the command transaction returns 409 `VERSION_CONFLICT`. [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) defines `If-Match` as a lost-update guard. An ambiguous send reconciliation command is 202; attempting resend/requeue is 409. OAuth callback never renders provider text. Invalid state/code/scope/account maps internally to 400 `OAUTH_CALLBACK_INVALID` then fixed 303 `oauth_invalid`; same-flow/different-hash maps to 409 `IDEMPOTENCY_HASH_CONFLICT` then `oauth_conflict`. `EXCHANGE_STARTED` with no durably discoverable credential maps to 503 `DEPENDENCY_UNAVAILABLE` then fixed `oauth_restart_required` and never re-exchanges. STAGED/ACTIVE transient exhaustion remains `IN_PROGRESS` and returns safe 503 with `Retry-After`; an exact retry resumes. DB/secret mismatch disables the mailbox and returns opaque dependency failure/incident reference. Only exact ACTIVE proof plus committed mailbox+SUCCEEDED may return/replay `oauth_connected`. Query reports may return `stale=true` inside 200 only when their documented source cutoff is complete; unknown/corrupt projection is 503, not misleading partial success. A missing/expired exported report snapshot maps to 409 `STATE_TRANSITION_DENIED` with reason `REPORT_SNAPSHOT_EXPIRED`; clients restart from page one, never continue against a new snapshot.

### Request/response example

```http
POST /api/v1/experiments/7dd7a7b3-5d57-4ae8-b1d9-49307050d7b8/commands/pause
Cookie: __Host-alon_ai_session=opaque
Origin: https://operator.example
Sec-Fetch-Site: same-origin
X-CSRF-Intent: operator-command-v1
Idempotency-Key: pause-20260828-0001
If-Match: "7"
X-Request-ID: 862f761d-a83b-4e8a-a98b-d5edbbe79074
Content-Type: application/json

{"schema_version":"api.control_experiment.request.v1","reason_code":"OPERATOR_REQUEST"}
```

Response is 202 `CommandReceiptV1` only after the pause-request transaction commits; it does not claim runtime acknowledgement or `PAUSED` until WF-06 records it.

## Ordered implementation tasks

- [ ] **Implement shared auth/error/idempotency/correlation dependencies —** Input: OIDC flow/session cookies, Origin/CSRF headers, command envelope, application errors. Operation: validate, derive exact scope/hash, map safe problem/status, and propagate IDs. Output: consistent route boundary. Test evidence: auth/header/replay/error snapshot matrix. Failure behavior: no handler/provider/runtime call.
- [ ] **Implement M4/M5 product routes —** Input: BACKEND-01 services and schemas. Operation: add experiment/workflow, campaign readiness, artifact/evidence/evaluation, and suppression operations in manifest order. Output: generated no-send client. Test evidence: OpenAPI and real-service integration tests. Failure behavior: route omitted/blocked until service exists.
- [ ] **Implement M6 Gmail/control/recovery routes —** Input: provider/policy/SendGateway/command/query services and private auth/signed OAuth state. Operation: add FastAPI-owned OIDC session, command-idempotent Gmail OAuth callback, mailbox/campaign/approval/message/control and both recovery surfaces. Output: operator-safe commands and typed overview. Test evidence: six-point OAuth saga replay/crash/GC matrix, ACTIVE-proof response gate, recovery coverage, call-path/authority/ambiguity/status E2E. Failure behavior: send controls remain false/fresh OAuth flow required.
- [ ] **Implement M7 report routes —** Input: BACKEND-06 projections. Operation: expose versioned read models/pagination without business logic. Output: stable dashboard API. Test evidence: projection/OpenAPI/browser contract tests. Failure behavior: visible stale/degraded response; no inferred truth.
- [ ] **Generate and gate OpenAPI client —** Input: composed FastAPI app. Operation: emit deterministic schema, validate operation/route/status uniqueness, regenerate TypeScript, and diff. Output: one API source of truth. Test evidence: `test_openapi_generated_client_has_no_drift`. Failure behavior: CI/release blocked.

## Test strategy

- **Contract `test_api_manifest_has_exact_64_paths_methods_operation_ids_schemas_and_statuses`:** no undocumented route.
- **Idempotency `test_command_replay_returns_original_status_body_location_and_correlation`:** hash conflict is 409.
- **OAuth `test_callback_never_returns_or_replays_success_without_exact_active_credential_tuple`:** STAGED/ACTIVE resumes; post-DB replays; undurable exchange restarts once.
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
