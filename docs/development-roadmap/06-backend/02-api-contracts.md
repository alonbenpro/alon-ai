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

The app currently exposes unauthenticated `/health/live` and database-backed `/health/ready`, request correlation/logging, and CORS. There are no product schemas/routes, public unsubscribe routes, authentication, idempotency middleware, OAuth callback, reports, controls, agents, workflows, providers, WAF route partition, or generated product client. The current health API remains unchanged until explicitly versioned.

## Scope and non-goals

In scope: private single-operator Google OIDC session delivery owned by FastAPI, the exact `/api/v1` product surface, distinct Gmail OAuth, command/query schemas, concurrency/idempotency/correlation/CSRF, RFC 9457 problems, pagination, OpenAPI operation IDs, generated-client drift, and exactly two recipient-facing public unsubscribe operations as a bounded M9-only exception. Non-goals: any other public API, public signup, inbound webhooks, Next.js authentication backend, JavaScript-visible identity/access/refresh/session tokens, GraphQL, frontend server actions as business API, provider credentials in HTTP, synchronous long workflow waits, generic CRUD, or returning ORM/provider objects. The operator product remains a private deployment.

## Exact planned implementation surfaces

Create `api/v1/router.py`, `api/v1/schemas/common.py`, `auth.py`, `experiments.py`, `campaigns.py`, `approvals.py`, `messages.py`, `suppressions.py`, `artifacts.py`, `controls.py`, `gmail.py`, `recovery.py`, `reports.py`, `api/dependencies/auth.py`, `api/dependencies/csrf.py`, `api/operator_sessions.py`, and `api/errors.py`; compose in `api/app.py`. Preserve `/health/live` and `/health/ready`. OpenAPI remains generated to `frontend/openapi.json` then `frontend/src/lib/api/schema.d.ts`.

### Shared HTTP envelope, authentication, idempotency, and correlation

The four `/api/v1/auth/*` routes establish the browser session; Gmail OAuth remains a separate mailbox-credential saga. The 64-operation `PRIVATE_DEPLOYMENT` partition consists of the original health, auth/callback, Gmail, and operator product/control/report operations; its documented health/auth/OAuth boundary exceptions are not general anonymous product APIs. Every product route in that partition requires the opaque `__Host-alon_ai_session` cookie resolved by FastAPI to one active DB-01 operator whose Google OIDC issuer/subject byte-match configured allowlist values. Exactly two `/api/v1/public/unsubscribe/{token}` operations form the separate `PUBLIC_UNSUBSCRIBE` partition and receive no operator session authority. No other route may enter that partition. The cookie is 256-bit random, rotated on login/reauth and every 15 minutes of active use, `Secure; HttpOnly; SameSite=Strict; Path=/; Domain` absent, with 30-minute idle and 8-hour absolute expiry. `Max-Age` is the remaining absolute lifetime capped at 28,800 seconds and `Expires` is that fixed absolute UTC instant; rotation never extends it. Expiry/revocation/logout respond with `Max-Age=0`/past `Expires`, and logout also clears any flow cookie. The server-side `OperatorSessionStore` owns current/previous-handle overlap for 30 seconds, revocation, idle/absolute expiry, and logout; Task 6 chooses/hardens its persistence without changing this HTTP contract. No identity/access/refresh/session token appears in URL, response JSON, JavaScript, localStorage, sessionStorage, or `NEXT_PUBLIC_*`.

OIDC start creates one server-side flow with state hash, PKCE S256 verifier/challenge, nonce hash, exact issuer/client/redirect IDs, safe validated internal return path, and 10-minute expiry. It sets only `__Host-alon_ai_oidc_flow` as a 256-bit opaque `Secure; HttpOnly; SameSite=Lax; Path=/; Domain` absent and `Max-Age=600` cookie. Google's current [OIDC API reference](https://developers.google.com/identity/openid-connect/reference) says the authorization response `iss` is always exactly `https://accounts.google.com`, while a verified ID token may use issuer `https://accounts.google.com` or legacy `accounts.google.com`; accessed 2026-08-29. Therefore callback `iss` must byte-equal `https://accounts.google.com`, and only verified ID-token `iss` uses the exact allowlist `{accounts.google.com, https://accounts.google.com}`. Neither comparison permits suffix/prefix/case normalization or a configured third value.

Callback requires the flow cookie and one strict, duplicate-free, size-bounded query arm for the configured authorization-code response type. Success requires exactly `code,state,iss` and permits only optional `scope`; error requires exactly `error,state,iss` and permits only optional `error_description`. Success forbids every error field, error forbids every success field except echoed `state`/required `iss`, and every other Google response-table field or arbitrary parameter—including `id_token`, `access_token`, `token_type`, `expires_in`, `authuser`, `hd`, `prompt`, and `error_uri`—is rejected rather than copied/logged. The bounded Google redirected-error catalog is exactly `access_denied|invalid_request|unauthorized_client|unsupported_response_type|invalid_scope`; `access_denied` maps to the denied redirect and every other recognized error to invalid as registered, while unknown values reject. State/flow is always verified and consumed once. The code arm verifies the exact HTTPS callback issuer before exchange, then PKCE, nonce, ID-token signature, exact verified-ID-token issuer-set membership, audience, authorized-party where present, issued/expiry time, and exact configured operator subject before rotation. It clears the flow cookie and 303-redirects only to the stored allowlisted relative path or fixed failure location. Successful callback redirects to the stored allowlisted relative `return_path`; the only failure locations are `303 {operator_origin}/?operator_auth=auth_invalid`, `...?operator_auth=auth_denied`, or `...?operator_auth=auth_expired`. Provider text/email/tokens are never rendered or logged. Reauthentication replaces the prior session and revokes it after the overlap. Logout revokes the server record before expiring the cookie. Auth start/callback/session/logout emit safe audit with subject hash, flow/session IDs, result/reason, correlation, and no token or claims payload.

Every unsafe session-authenticated request requires exact configured `Origin`, `Sec-Fetch-Site: same-origin`, and constant custom header `X-CSRF-Intent: operator-command-v1`; logout uses `X-CSRF-Intent: operator-session-v1`. Missing/mismatched Origin/fetch metadata/header is 403 `AUTHORIZATION_DENIED` reason `CSRF_CHECK_FAILED` before command dispatch. CORS permits only the configured operator frontend origin and credentials. Mutating JSON requests require `Content-Type: application/json`. Gmail OAuth callback authority remains the operator/flow binding inside signed+encrypted state and executes only `CompleteGmailAuthorization`; it never uses or exposes the OIDC flow/session.

Every session-authenticated business mutation except the Gmail OAuth callback requires caller-supplied `Idempotency-Key` of 16..200 visible ASCII characters. Public unsubscribe POST instead derives its unforgeable key from the verified token JTI and accepts no caller key. OIDC start requires the key but binds it to the anonymous flow cookie/Origin; OIDC callback derives its one-time flow key; session GET/logout are idempotent session operations and do not enter the business command registry. Updates to explicit versions—`experiments.version`, `outreach_messages.version`, `suppression_entries.version`, `system_controls.version`, and `gmail_history_cursors.version`—require `If-Match: "{positive_version}"`; missing is 428, known mismatch 412, transactional race 409. Campaign commands carry immutable positive `campaign_version` in the path plus exact `expected_state`; approval/mailbox/workflow/artifact commands lock exact expected state/status. Artifact commands additionally require exact `artifact_version` and `content_hash`. The Gmail callback derives `command_scope=gmail.oauth.complete:{oauth_flow_id}` and `idempotency_key=oauth-flow:{oauth_flow_id}` and preserves the existing exact resume/replay rules. The application derives a route/actor/resource scope and DB-01 request hash. Same scope/key/hash returns the original status/body/Location/ETag/correlation; changed hash is 409. Commands that commit work then signal a workflow return 202 without claiming completion.

Client may send `X-Request-ID` UUIDv4; invalid values return 400. Otherwise middleware creates it. Every request creates/propagates UUIDv4 `correlation_id`; commands set `causation_id` to the HTTP request ID. Responses include `X-Request-ID` and `X-Correlation-ID`. Logs use safe IDs/route template/status/duration only.

Success shapes are strict/extra-forbid. A response backed by one of the five explicit optimistic-version columns carries HTTP `ETag: "{version}"`; other resource-specific schemas expose their immutable campaign/brief version or expected state without inventing a mutable version. A mutating response carries the resulting aggregate ETag only when that explicit version changed:

- `ResourceResponseV1={schema_version,data,version,correlation_id}`;
- `CommandReceiptV1={schema_version:"api.command_receipt.v1",command_type,command_scope,idempotency_key,status:"COMMITTED"|"ACCEPTED",aggregate_type,aggregate_id,aggregate_version,workflow_run_id,result_hash,correlation_id}`;
- `PageResponseV1={schema_version,items,next_cursor,as_of,projection_version,correlation_id}`.

Exact named resource/query schemas are strict and extra-forbid; braces below are the complete browser allowlist, not examples:

- `CampaignVersionResponseV1={schema_version:"api.campaign_version.response.v1",data:{campaign_version_id,campaign_id,campaign_version,experiment_id,supersedes_campaign_version_id,state,offer_id,offer_version,offer_content_hash,policy_version,membership_mode:"ALL_CURRENTLY_ELIGIBLE",eligibility_snapshot_version,eligibility_snapshot_at,eligibility_query_version,eligible_set_hash,eligible_member_count,member_cap,send_window_start,send_window_end,reply_window_end,daily_cap,total_cap,removed_member_count,members:[{campaign_member_id,lead_id,eligibility_ordinal,eligibility_basis_hash,status,lead_state,identity_state,suppression_entry_id,compliance_refs:{recipient_identity_evidence_ref,jurisdiction_evidence_ref,affirmative_consent_evidence_ref?,counsel_exception_evidence_ref?,legal_review_ref,legal_policy_version,disclosure_sender_template_ref,google_policy_review_ref},message:{message_id,mailbox_id,state,version,content_hash,approval_id},created_at,removed_at}],created_at,updated_at},correlation_id}`. Every `*_ref` is the exact accepted `{artifact_id,artifact_version,content_hash}` tuple, exactly one consent/exception ref is present, and recipient address hashes/digests/ciphertexts are forbidden.
- `ApprovalResponseV1={schema_version:"api.approval.response.v1",data:{approval_id,experiment_id,campaign_id,campaign_version,campaign_member_id,lead_id,message_id,message_version,message_content_hash,mailbox_id,provider_account_hash,intended_operation:"SEND",scope_schema_version,scope_hash,artifact_version_refs,artifact_version_refs_hash,eligibility_policy_decision_id,eligibility_policy_scope,eligibility_policy_version,eligibility_facts_hash,eligibility_policy_allowed,current_authority_valid,state,max_send_count,expires_at,previewed_at?,preview_materialization_hash?,reason_code,requested_at,decided_at,stale_reason_codes},correlation_id}` is the summary view and never contains recipient address, subject, body, rendered bytes, or a preview receipt.
- `ApprovalSensitivePreviewResponseV1={schema_version:"api.approval_sensitive_preview.response.v1",data:{approval_id,recipient_address,subject,body,rendered_rfc822_base64url,materialization:{schema_version:"approval.preview_materialization.v1",experiment_id,campaign_id,campaign_version,campaign_member_id,lead_id,message_id,message_version,message_content_hash,mailbox_id,provider_account_hash,scope_hash,artifact_version_refs,artifact_version_refs_hash,intended_operation:"SEND",max_send_count:1,approval_expires_at},preview_materialization_hash,previewed_at,preview_expires_at,preview_receipt},correlation_id}` is returned only for `getApproval?view=SENSITIVE_PREVIEW`. The strict RFC 8785 materialization object includes the displayed recipient address, subject, body, and rendered RFC 822 bytes before hashing, even though those sensitive fields are presented as siblings for ergonomic display. `preview_receipt` is an opaque sign-then-encrypt `ApprovalPreviewReceiptV1` binding approval/operator/session epoch/scope/materialization hash/issued/expiry/random nonce; lifetime is at most five minutes.
- `OutreachMessageResponseV1={schema_version:"api.outreach_message.response.v1",data:{message_id,experiment_id,campaign_id,campaign_version,campaign_member_id,lead_id,mailbox_id,provider_account_hash,artifact_id,state,version,content_hash,approval:{approval_id,state,scope_hash,max_send_count,expires_at,current_authority_valid,stale_reason_codes},final_send_compliance:{policy_decision_id,facts_observed_at,recipient_identity_status,recipient_identity_verified_at,recipient_identity_expires_at,jurisdiction_status,jurisdiction_code,jurisdiction_evidence_retrieved_at,jurisdiction_evidence_published_at,jurisdiction_evidence_expires_at,authority_route,consent_status,consent_captured_at,consent_verified_at,consent_expires_at,counsel_exception_decided_at,counsel_exception_effective_at,counsel_exception_expires_at,legal_review_id,legal_review_status,legal_review_effective_at,legal_review_expires_at,legal_policy_version,legal_policy_current,disclosure_sender_template_id,disclosure_sender_template_version,disclosure_sender_template_content_hash,disclosure_validator_version,disclosure_valid,google_policy_review_id,google_policy_review_version,google_policy_status,google_policy_effective_at,google_policy_expires_at,google_policy_compatible,reply_observed,unsubscribe_observed,hard_bounce_observed,complaint_observed,soft_bounce_count,soft_bounce_limit,soft_bounce_last_observed_at,evidence_refs:[{artifact_id,artifact_version,content_hash}],observation_reference_ids,reason_codes},send_intent:{send_intent_id,state,rfc_message_id_hash,policy_decision_id},send_attempt:{send_attempt_id,attempt_number,state,provider_result_id,provider_observation_ids,ambiguity_incident_id,retry_not_before,retry_count,retry_cap},reply:{reply_id,state,classification_artifact_id},timeline:[{timeline_item_id,event_type,state,occurred_at,reason_codes,safe_reference_ids}],created_at,updated_at},version,correlation_id}`. The final-send block is nullable before evaluation; consent fields are non-null only for `AFFIRMATIVE_CONSENT`, exception fields only for `COUNSEL_EXCEPTION`, and it exposes bounded status/enums/exact evidence tuples/record references only—never recipient hash, consent/legal text, source content, or address.
- `IncidentRepairResponseV1={schema_version:"api.incident_repair.response.v1",data:{incident_id,catalog_version:"incident.catalog.v1",trigger_code,runbook_id,alert_id,repair_kind,incident_state,resolution_code,evidence_ref,workflow_run_id,command_status,opened_at,resolved_at,updated_at},correlation_id}`. `RepairIncidentRequestV1` uses the exact DB-05 repair-kind enum plus expected-before/desired-after hashes and evidence ref; unknown catalog values, cross-paired trigger/alert/runbook tuples, inapplicable trigger/resolution or repair/runbook combinations, and forbidden residual-risk acceptance are rejected before command claim and again by named PostgreSQL checks.
- `SuppressionResponseV1={schema_version:"api.suppression.response.v1",data:{suppression_entry_id,scope,business_id,recipient_target_ref_id,reason_code,source:enum[OPERATOR,GMAIL_REPLY,GMAIL_UNSUBSCRIBE,GMAIL_HARD_BOUNCE,GMAIL_COMPLAINT,GMAIL_SOFT_BOUNCE_LIMIT,PUBLIC_UNSUBSCRIBE],source_actor_type,source_observation_id,source_reply_id,active,version,created_at,deactivated_at},version,correlation_id}`. The opaque stored `recipient_target_ref_id` is non-null iff `scope=RECIPIENT`; it is stable after source-member cleanup and is read directly from `suppression_entries`, never reconstructed from lookup material. `recipient_hash`, address ciphertext, content digests, and every derived lookup value are absent from all HTTP schemas.
- `UnsubscribeConfirmationHtmlV1` is the exact self-contained FastAPI HTML byte contract below; it is not JSON, a generated-client model, a Next.js resource, or a product record. `UnsubscribeResultResponseV1={schema_version:"api.unsubscribe_result.response.v1",status:"SUPPRESSED"|"ALREADY_SUPPRESSED"|"INVALID_OR_EXPIRED",processed_at?,correlation_id}` contains no recipient/campaign/message/token/hash identifier.
- `ArtifactResponseV1={schema_version:"api.artifact.response.v1",data:{artifact_id,experiment_id,artifact_type,artifact_schema_version,artifact_version,status,agent_run_id,agent_type,agent_version,prompt_version,model_provider,model_name,model_version,toolset_version,input_snapshot_hash,content_hash,allowlisted_content,confidence,abstention_reason,supersedes_artifact_id,latest_validation:{artifact_validation_id,validator_version,schema_valid,provenance_valid,reason_codes,facts_hash,created_at},acceptance:{artifact_acceptance_id,acceptance_mode,gate_version,scope_hash,created_at},evidence_count,evaluation_result_ids,redaction_state,created_at},correlation_id}`.
- `ArtifactEvidenceResponseV1={schema_version:"api.artifact_evidence.response.v1",data:{artifact_id,evidence_item_id,evidence_type,citation_uri,citation_uri_hash,source_policy_version,source_provider,retrieved_at,published_at,content_hash,mime_type,language,license_basis,redaction_state,claim_pointer,relationship,source_excerpt_hash,created_at},correlation_id}`; raw locator/ciphertext, `capture_ref`, query secrets/PII, and source content are never serialized.
- `EvaluationResultResponseV1={schema_version:"api.evaluation_result.response.v1",data:{evaluation_result_id,evaluation_case_id,suite_name,suite_version,case_key,agent_run_id,evaluator_version,scores_schema_version,scores,scores_hash,passed,reason_codes,sensitivity_class,input_hash,expected_hash,created_at},correlation_id}`; restricted case snapshots/rubrics are omitted.
- `OperatorAuthorizationResponseV1={schema_version:"api.operator_authorization.response.v1",authorization_url,flow_expires_at,correlation_id}`, `OperatorSessionResponseV1={schema_version:"api.operator_session.response.v1",operator_id,subject_hash,issued_at,idle_expires_at,absolute_expires_at,reauth_required,correlation_id}`, and `OperatorSessionEndedResponseV1={schema_version:"api.operator_session_ended.response.v1",ended:true,ended_at,correlation_id}`. None contains provider claims/tokens/email.

Opaque pagination cursor signs route/filter/order/last-key/projection-version/expiry; tamper/mismatch is `VALIDATION_FAILED`. List order is explicitly stable per route. `limit` defaults 50 and is 1..100.

### Exact route and OpenAPI operation manifest

The closed manifest is exactly 66 unique method/path/`operationId` triples: exactly 64 belong to `PRIVATE_DEPLOYMENT` and exactly the following two belong to `PUBLIC_UNSUBSCRIBE`. The partition is release-enforced metadata as well as documentation; duplicate, unclassified, or differently classified operations fail generation. `PRIVATE_DEPLOYMENT` means the private operator deployment surface, including its specifically documented health and OAuth callback ingress, not that every operation uses the session cookie.

Existing health:

| Method/path | `operationId` | Success | Errors/auth |
| --- | --- | --- | --- |
| `GET /health/live` | `getLiveness` | 200 existing payload | no auth; never checks DB/provider |
| `GET /health/ready` | `getReadiness` | 200 ready or 503 existing degraded payload | no auth; safe dependency detail only |

Public scanner-safe unsubscribe capability (not an operator session and never a webhook): GET cannot mutate; only the explicit POST reaches a command transaction. Both routes are absent/unavailable and their ingress is unpublished until the M9 real-recipient release evidence proves retained legal review/versioned policy, current M1/M6 evidence, live suppression repair tests, and signed public-route/WAF configuration. Before that gate, deployment validation requires `PUBLIC_UNSUBSCRIBE` disabled and no public route match; application startup rejects a contradictory enabled route. Once enabled, token verification and the application path fail closed on missing key generation, suppression dependency, control state, or route-policy version. Any suppression transaction/sync failure disables `PRODUCT_OUTREACH`, opens `ALERT_COMPLIANCE_SUPPRESSION`, and makes POST unavailable until typed repair proves no-next-SEND.

| Method/path | `operationId` / request -> response | Success/auth |
| --- | --- | --- |
| `GET /api/v1/public/unsubscribe/{token}` | `getUnsubscribeConfirmation` -> `UnsubscribeConfirmationHtmlV1` | 200 `text/html; charset=utf-8`; identical generic bytes; no command claim, suppression, audit mutation, token consumption, control change, or other write |
| `POST /api/v1/public/unsubscribe/{token}` | `confirmUnsubscribe`; `ConfirmUnsubscribeRequestV1={schema_version:"api.unsubscribe_confirm.request.v1",confirmation:"UNSUBSCRIBE"}` -> `UnsubscribeResultResponseV1` | 200 after `RecipientSignalSuppressionService`; exact public Origin, same-origin fetch metadata, JSON content type and `X-CSRF-Intent: unsubscribe-confirm-v1`; server-derived token-JTI command key; no caller `Idempotency-Key` |

`UnsubscribeTokenV1` is an opaque sign-then-encrypt token with random 256-bit `jti`, exact message/campaign-member/mailbox and policy/template IDs, issued/expiry instants, audience `alon-ai-unsubscribe`, route binding and key generation. It copies `retention.policy.v1`: `expires_at` is no more than 90 days after `issued_at` and no later than the signed recipient-obligation end; its minting generation is retired from new issuance before rotation but remains verify/decrypt-capable for at least 97 days after its last issuance. Missing key coverage disables the public pair and product outreach. The token contains no address/hash and its ciphertext is never logged, traced, rendered, stored in browser storage or sent as referrer. FastAPI returns the exact UTF-8 bytes below for every GET that reaches the route, independent of token validity; byte length is `1057` and lowercase SHA-256 is `a84df42ef2572b71f222a14a848114ba1dfece9168acbadc7f1884bcb2a9b975` (one LF after the doctype and one final LF). It includes no template interpolation, token, third-party asset, form, operator shell, generated Next client, analytics, or storage access. The only script action is the focused button's same-path POST; it never parses the response body or writes the token to DOM/storage.

```html
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Email preferences</title></head><body><main><h1>Stop these emails?</h1><p>This page has not changed your preferences.</p><button id="confirm" type="button">Unsubscribe</button><p id="status" role="status" aria-live="polite"></p></main><script>(()=>{"use strict";const b=document.getElementById("confirm"),s=document.getElementById("status");b.addEventListener("click",async()=>{b.disabled=true;s.textContent="Processing...";try{const r=await fetch(location.pathname,{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Intent":"unsubscribe-confirm-v1"},credentials:"omit",referrerPolicy:"no-referrer",body:"{\"schema_version\":\"api.unsubscribe_confirm.request.v1\",\"confirmation\":\"UNSUBSCRIBE\"}"});s.textContent=r.ok?"Your request has been recorded.":"We could not process this request.";}catch{s.textContent="We could not process this request.";}finally{b.disabled=false;}});})();</script></body></html>
```

The GET response headers are exact: `Content-Type: text/html; charset=utf-8`, `Cache-Control: no-store, max-age=0`, `Pragma: no-cache`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=(), payment=(), usb=()`, and `Content-Security-Policy: default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; connect-src 'self'; script-src 'sha256-TyNtMCDTite6EHq+vVEPtiPyhpTVy8RbSlB8d6MSTPs='`. Scanner GET is read-only. POST verifies every token binding and derives `public-unsubscribe:{HMAC(jti)}` for exact replay; invalid/expired/unknown and already-suppressed results are recipient-opaque. Only POST may call the atomic observed-suppression service. Public middleware applies a smaller independent request/URI/body limit, method/content-type allowlist, WAF token-shape rule, bounded per-source and global rate buckets, exact public Origin, `Sec-Fetch-Site: same-origin`, confirmation CSRF header, and uniform error body/timing bucket; it never shares the operator rate bucket. No IP, token, JTI, recipient, ciphertext, digest, query string, user-agent, or referrer becomes a log/trace/metric label.

Operator OIDC/session (separate from Gmail OAuth):

| Method/path | `operationId` / request -> response | Success/auth |
| --- | --- | --- |
| `POST /api/v1/auth/authorizations` | `startOperatorAuthorization`; `StartOperatorAuthorizationRequestV1={schema_version:"api.operator_authorization.start.v1",return_path}` -> `OperatorAuthorizationResponseV1` | 201 + Google `Location`; no session required; exact Origin/fetch metadata + `Idempotency-Key`; flow cookie set |
| `GET /api/v1/auth/callback` | `completeOperatorAuthorization`; strict success `{code,state,iss,scope?}` or error `{error,state,iss,error_description?}` + flow cookie -> fixed redirect | 303; callback `iss` must equal `https://accounts.google.com`; verified ID-token `iss` separately permits exactly `{accounts.google.com,https://accounts.google.com}` plus configured subject; fixed safe failure redirects |
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
| `POST /api/v1/experiments/{experiment_id}/campaigns` | `createCampaignVersion`; `CreateCampaignVersionRequestV1={schema_version:"api.create_campaign_version.request.v1",expected_experiment_version,offer_id,offer_version,offer_content_hash,policy_version,membership_mode:"ALL_CURRENTLY_ELIGIBLE",eligibility_snapshot_version,eligibility_query_version:"campaign.eligibility.v1",expected_eligible_set_hash,expected_eligible_member_count,member_cap,send_window_start,send_window_end,reply_window_end,daily_cap,total_cap}` -> `CampaignVersionResponseV1` | 201 + `Location`; all-or-nothing snapshot membership |
| `GET /api/v1/campaigns/{campaign_id}/versions/{campaign_version}` | `getCampaignVersion` -> `CampaignVersionResponseV1` | 200 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/ready` | `readyCampaign`; `ReadyCampaignRequestV1={schema_version,expected_state:"DRAFT",offer_id,offer_version,policy_version}` -> `CampaignVersionResponseV1` | 200 `DRAFT -> READY`; immutable path version + locked state; exact offer/policy, eligible-member, draft/approval guards; `campaign.ready.v1` |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/activate` | `activateCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/pause` | `pauseCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/resume` | `resumeCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/cancel` | `cancelCampaign`; `CampaignControlRequestV1` | 202 |
| `GET /api/v1/approvals` | `listApprovals`; state/cursor/limit, ordered `(requested_at,approval_id)` | 200 |
| `GET /api/v1/approvals/{approval_id}` | `getApproval`; exact query `view=SUMMARY|SENSITIVE_PREVIEW` defaults `SUMMARY` | 200 summary, or step-up-protected sensitive preview under the same operation ID |
| `POST /api/v1/approvals/{approval_id}/commands/approve` | `approveApproval`; `DecideApprovalRequestV1={schema_version:"api.decide_approval.request.v1",expected_state:"PENDING",reason_code,preview_receipt}` | 200 only after a fresh matching manual preview receipt |
| `POST /api/v1/approvals/{approval_id}/commands/deny` | `denyApproval`; same request shape but `preview_receipt` is forbidden/absent | 200 |
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

Both control POST routes are operator-only and `ChangeControlRequestV1` has no actor field; FastAPI derives `actor_type=OPERATOR` and the session operator ID. Registered internal system actors call `ControlCommandService.disable` directly with the DB-01 closed actor ID/reason/evidence union and cannot invoke either HTTP route. `listSystemControls` returns `actor_type` plus exactly one safe `changed_by_operator_id` or `changed_by_system_actor_id`; it never synthesizes an operator for fail-closed automation. Enable rejects the system union at both contract and database layers.

`getExperiment` and `getExperimentOverviewReport` expose only a safe `CampaignEligibilitySummaryV1={membership_mode:"ALL_CURRENTLY_ELIGIBLE",eligibility_snapshot_version,eligibility_snapshot_at,eligibility_query_version:"campaign.eligibility.v1",eligible_set_hash,eligible_member_count,member_cap_ceiling}` aggregate—never a pre-campaign lead list or selectable IDs. `createCampaignVersion` locks the experiment/version and every candidate row, executes `campaign.eligibility.v1` over all leads in that experiment that are `QUALIFIED`, unsuppressed, identity-verified, and backed by the exact current accepted qualification/recipient/jurisdiction/consent-or-counsel/legal/template/Google-policy tuples, orders by canonical lowercase UUID bytes, and hashes RFC 8785 `{experiment_id,experiment_version,query_version,members:[{lead_id,lead_version,qualification_artifact_ref,recipient_identity_ref,jurisdiction_ref,authority_ref,legal_review_ref,legal_policy_version,disclosure_sender_template_ref,google_policy_review_ref,eligibility_basis_hash}]}`. The transaction recomputes and byte-matches requested snapshot version/query/hash/count, requires `1 <= count <= member_cap <= signed experiment sample cap <= 100`, refuses overflow rather than truncating, inserts the campaign plus all and only those members with consecutive ordinals, and verifies row count/set hash before commit. Any drift, duplicate, zero set, missing/stale evidence, cross-experiment offer/member, user-supplied member ID, subset/omission, or post-read race returns 409 `STATE_TRANSITION_DENIED` reason `CAMPAIGN_ELIGIBILITY_SNAPSHOT_MISMATCH` with no campaign/member row. A later changed population requires a new immutable campaign version; it never edits membership in place.

`SENSITIVE_PREVIEW` is the sole controlled exception to summary redaction. It requires an active operator session whose step-up reauthentication completed no more than five minutes earlier; otherwise it returns 401 `AUTHENTICATION_REQUIRED` reason `STEP_UP_REAUTH_REQUIRED` without decrypting content. The response uses `Cache-Control: no-store, max-age=0`, `Pragma: no-cache`, `Referrer-Policy: no-referrer`, and never enters OpenTelemetry/logs/error bodies/report caches, browser persistence, clipboard helpers, prefetch, service workers, screenshots, or analytics. The service decrypts and renders once, hashes exact RFC 8785 materialization bytes, and returns a receipt expiring no later than the approval and five-minute preview window. `approveApproval` verifies signature/key/session/operator/approval/scope/materialization/expiry, locks and re-renders the exact message/recipient/mailbox/artifact tuple, requires byte-identical hash, then atomically stores only preview hash/receipt hash/timestamps and the manual operator decision. Every automated/system/workflow actor, absent preview, stale receipt, changed recipient/content/version/artifact, replay against another approval/session/operator, and any re-render mismatch is denied before state change. No automatic `DRAFT -> APPROVED` transition exists.

Artifacts, evidence, and evaluation:

| Method/path | `operationId` / schema | Success |
| --- | --- | --- |
| `GET /api/v1/artifacts/{artifact_id}` | `getArtifact` -> `ArtifactResponseV1` | 200 schema/provenance/latest validation/acceptance/agent config/version/hash/redaction metadata |
| `GET /api/v1/artifacts/{artifact_id}/evidence` | `listArtifactEvidence`; cursor/limit -> `PageResponseV1[ArtifactEvidenceResponseV1]`, ordered `(created_at,evidence_item_id,claim_pointer,relationship)` | 200 allowlisted citation/link/redaction fields; no restricted capture/content |
| `GET /api/v1/evaluation-results/{evaluation_result_id}` | `getEvaluationResult` -> `EvaluationResultResponseV1` | 200 allowlisted case/suite/evaluator/config/scores/pass/reasons/version/hash/sensitivity fields |
| `POST /api/v1/artifacts/{artifact_id}/commands/accept` | `acceptArtifact`; `AcceptArtifactRequestV1={schema_version,artifact_version,content_hash,expected_status:"VALIDATED",reason_code}` -> `ArtifactResponseV1` | 200; locked exact version/hash/status, deterministic validation must pass; `artifact.accepted.v1` + audit |
| `POST /api/v1/artifacts/{artifact_id}/commands/reject` | `rejectArtifact`; `RejectArtifactRequestV1={schema_version,artifact_version,content_hash,expected_status:enum[PRODUCED,VALIDATED],reason_code}` -> `ArtifactResponseV1` | 200; locked exact version/hash/status; `artifact.rejected.v1` + audit |

Suppressions (safe record references only; no recipient hash):

| Method/path | `operationId` / schema | Success |
| --- | --- | --- |
| `GET /api/v1/suppressions` | `listSuppressions`; scope/active/cursor/limit -> `PageResponseV1[SuppressionResponseV1]`, ordered `(created_at,suppression_entry_id)` | 200; fresh uncached authoritative page |
| `POST /api/v1/suppressions` | `createSuppression`; strict discriminated `CreateSuppressionRequestV1`: `GLOBAL={schema_version,scope:"GLOBAL",reason_code}`, `BUSINESS={schema_version,scope:"BUSINESS",business_id,reason_code}`, or `RECIPIENT={schema_version,scope:"RECIPIENT",recipient_source_ref_id,reason_code}` -> `SuppressionResponseV1` | 201 + `Location`; `recipient_source_ref_id` is an existing opaque `campaign_member_id` used only for authenticated creation, never the durable target ref or a hash; service resolves lookup material internally, stores/returns one opaque `recipient_target_ref_id`; source forced `OPERATOR`; event/audit commit |
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

Path IDs parse UUIDv4 except the bounded opaque public unsubscribe token; campaign versions are positive. Literal canonical state/control names are OpenAPI enums, not display labels. Routes not listed are not part of v1. The manifest is exactly 66 routes/66 unique operation IDs: the prior 64 plus read-only `getUnsubscribeConfirmation` and mutating `confirmUnsubscribe`. It includes `getRecoveryOverview`, all four operator-session operations, all four exposed workflow/campaign commands, all three operator suppression operations, and all five artifact/evidence/evaluation operations. OpenAPI rejects duplicates and undocumented response statuses. The generated Next.js recovery dashboard may call only `getRecoveryOverview`/the listed typed commands; it cannot reconstruct recovery truth from logs.

### Exact corrected-surface preconditions and failures

This table is the operation-level contract for the 18 reviewed additions to the original 48-operation manifest; listed statuses are exhaustive in addition to their declared success, and every code uses the global `ProblemDetailsV1` mapping below.

| Operations | Authentication / replay / concurrency | Exact non-success HTTP statuses |
| --- | --- | --- |
| `getUnsubscribeConfirmation` | no session; opaque token validation; read-only/no command claim; per-source ephemeral rate bucket | 400, 404, 429, 503 with one generic public body |
| `confirmUnsubscribe` | no session; exact public Origin/fetch metadata/JSON/CSRF confirmation; token-derived command key; serializable observed-suppression transaction | 400, 403, 404, 409, 429, 503 with one generic public body; exact replay remains 200 |
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

- [ ] **Implement shared auth/error/idempotency/correlation dependencies —** Input: OIDC flow/session cookies, Origin/CSRF headers, command envelope, application errors. Operation: validate, derive exact scope/hash, map safe problem/status, and propagate IDs. Output: consistent route boundary. Test evidence: auth/header/replay/error snapshot matrix and separate callback-versus-ID-token issuer fixtures. Failure behavior: no handler/provider/runtime call.
- [ ] **Implement M4/M5 product routes —** Input: BACKEND-01 services and schemas. Operation: add experiment/workflow, campaign readiness, artifact/evidence/evaluation, and suppression operations in manifest order. Output: generated no-send client. Test evidence: OpenAPI and real-service integration tests. Failure behavior: route omitted/blocked until service exists.
- [ ] **Implement M6 Gmail/control/recovery routes —** Input: provider/policy/SendGateway/command/query services and private auth/signed OAuth state. Operation: add FastAPI-owned OIDC session, command-idempotent Gmail OAuth callback, mailbox/campaign/approval/message/control and both recovery surfaces. Output: operator-safe commands and typed overview. Test evidence: six-point OAuth saga replay/crash/GC matrix, ACTIVE-proof response gate, recovery coverage, call-path/authority/ambiguity/status E2E. Failure behavior: send controls remain false/fresh OAuth flow required.
- [ ] **Implement M7 report routes —** Input: BACKEND-06 projections. Operation: expose versioned read models/pagination without business logic. Output: stable dashboard API. Test evidence: projection/OpenAPI/browser contract tests. Failure behavior: visible stale/degraded response; no inferred truth.
- [ ] **Generate and gate OpenAPI client and future public ingress —** Input: composed FastAPI app, this route partition, and M9 release evidence. Operation: emit deterministic schema, validate operation/route/status uniqueness and the exact 64 `PRIVATE_DEPLOYMENT` plus two `PUBLIC_UNSUBSCRIBE` partition, regenerate TypeScript/diff, and require Task 7 infrastructure/tests to expose only the two public paths to recipient Internet traffic while health/operator/auth/Gmail/product routes stay on private ingress; exercise WAF method/token/size rules, independent public rate limits, scanner GET, Origin/fetch/CSRF POST, token abuse, redaction, dependency failure, `PRODUCT_OUTREACH` fail-close, and pre-M9 public-route absence. Output: one API source of truth plus signed route-map/test evidence consumed by M9. Test evidence: `test_openapi_generated_client_has_no_drift` plus proxy partition/security/load/log-scan/kill/recovery suites. Failure behavior: CI/release blocked, no public unsubscribe ingress, and no real-recipient outreach.

## Test strategy

- **Contract `test_api_manifest_has_exact_66_paths_methods_operation_ids_schemas_and_statuses`:** exact set equality and exactly 64 `PRIVATE_DEPLOYMENT` plus two `PUBLIC_UNSUBSCRIBE`; no undocumented/unclassified route.
- **Unsubscribe `test_get_never_mutates_and_post_atomically_suppresses_without_exposing_recipient_or_token`:** scanner GET, duplicate/concurrent POST, crash at every transaction write, invalid/expired token and no-next-SEND fixtures.
- **OIDC `test_google_oidc_callback_exact_parameter_arms_and_issuer_set_match_official_fixtures`:** exact success `{code,state,iss,scope?}` and error `{error,state,iss,error_description?}`; duplicate/extra/cross-arm rejection; callback accepts only `https://accounts.google.com` and rejects legacy `accounts.google.com`; verified ID-token issuer separately accepts each exact Google value; audience/time/nonce/subject checks.
- **Suppression HTTP `test_suppression_http_schema_uses_only_opaque_source_and_target_refs`:** create accepts `recipient_source_ref_id` only, response/list/replay emit stored `recipient_target_ref_id`, and OpenAPI rejects/contains zero recipient hash/address ciphertext/digest target fields.
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
