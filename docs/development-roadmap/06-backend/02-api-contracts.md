# FastAPI and OpenAPI Contracts

**Document ID:** BACKEND-02
**Status:** Planned product API; only `/health/live` and `/health/ready` exist today
**Milestone:** M4, M6, M7 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `BACKEND-02-T01 -> BACKEND-02-T02 -> BACKEND-02-T03 -> BACKEND-02-T04 -> BACKEND-02-T05`; cross-document task Inputs `BACKEND-02-T01 <- BACKEND-01-T03; BACKEND-02-T02 <- BACKEND-01-T04; BACKEND-02-T03 <- PROVIDER-01-T04,PROVIDER-02-T01,BACKEND-03-T03,BACKEND-04-T04,BACKEND-05-T06,SEC-03-T02,SEC-04-T03,SEC-05-T04,SEC-02-T04,BACKEND-05-T02; BACKEND-02-T04 <- SEC-02-T04,BACKEND-06-T01; BACKEND-02-T05 <- BACKEND-06-T04`. Descriptive source authorities/resources (not whole-document completion dependencies): [BACKEND-01](01-domain-services.md), DB-01/03/05 command records, planned private authentication, and canonical ARCH-03 states/events
**Outputs:** Exact versioned routes, schemas, status/errors, authentication, idempotency, correlation, pagination, and OpenAPI generation rules
**Unlocks:** M4-M7 frontend generated client and operator workflows
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

FastAPI is the only business HTTP backend and OpenAPI source. Routes validate/authenticate/translate, call one application command or query service, and return its authoritative result; they contain no domain rules or provider SDK calls. Next.js renders the generated client and never proxies secrets, writes PostgreSQL, or becomes a second backend.

The private contract exposes offer economics, discovery and qualification, complete redacted conversations, deterministic send blocks, negotiation, booking, checkpoints, global strategies and exceptions. Stage increments and cumulative ceilings are server-owned; runtime checkpoint decisions are deterministic. OpenAPI operation and route-partition inventories expand with these surfaces and are compared by exact route/operation sets, never a historical fixed count.

## Current repository state

The app currently exposes unauthenticated `/health/live` and database-backed `/health/ready`, request correlation/logging, and CORS. There are no product schemas/routes, public unsubscribe routes, authentication, idempotency middleware, OAuth callback, reports, controls, agents, workflows, providers, WAF route partition, or generated product client. The current health API remains unchanged until explicitly versioned.

## Scope and non-goals

In scope: private single-operator Google OIDC session delivery owned by FastAPI, the exact `/api/v1` product surface, distinct Gmail OAuth, command/query schemas, concurrency/idempotency/correlation/CSRF, RFC 9457 problems, pagination, OpenAPI operation IDs, generated-client drift, and exactly two recipient-facing public unsubscribe operations as a bounded M9-only exception. Non-goals: any other public API, public signup, inbound webhooks, Next.js authentication backend, JavaScript-visible identity/access/refresh/session tokens, GraphQL, frontend server actions as business API, provider credentials in HTTP, synchronous long workflow waits, generic CRUD, or returning ORM/provider objects. The operator product remains a private deployment.

## Exact planned implementation surfaces

Create `api/v1/router.py`, `api/v1/schemas/common.py`, `auth.py`, `experiments.py`, `campaigns.py`, `action_authorizations.py`, `exceptions.py`, `offers.py`, `leads.py`, `conversations.py`, `bookings.py`, `checkpoints.py`, `strategies.py`, `messages.py`, `suppressions.py`, `artifacts.py`, `controls.py`, `gmail.py`, `recovery.py`, `reports.py`, `api/dependencies/auth.py`, `api/dependencies/csrf.py`, `api/operator_sessions.py`, and `api/errors.py`; compose in `api/app.py`. Preserve `/health/live` and `/health/ready`. OpenAPI remains generated to `frontend/openapi.json` then `frontend/src/lib/api/schema.d.ts`.

### Shared HTTP envelope, authentication, idempotency, and correlation

The four `/api/v1/auth/*` routes establish the browser session; Gmail OAuth remains a separate mailbox-credential saga. The `PRIVATE_DEPLOYMENT` partition consists of all listed health, auth/callback, Gmail, and operator product/control/report operations; its documented health/auth/OAuth boundary exceptions are not general anonymous product APIs. Every product route in that partition requires the opaque `__Host-alon_ai_session` cookie resolved by FastAPI to one active DB-01 operator whose Google OIDC issuer/subject byte-match configured allowlist values. Exactly two `/api/v1/public/unsubscribe/{token}` operations form the separate `PUBLIC_UNSUBSCRIBE` partition and receive no operator session authority. No other route may enter that partition. The cookie is 256-bit random, rotated on login/reauth and every 15 minutes of active use, `Secure; HttpOnly; SameSite=Strict; Path=/; Domain` absent, with 30-minute idle and 8-hour absolute expiry. `Max-Age` is the remaining absolute lifetime capped at 28,800 seconds and `Expires` is that fixed absolute UTC instant; rotation never extends it. Expiry/revocation/logout respond with `Max-Age=0`/past `Expires`, and logout also clears any flow cookie. The server-side `OperatorSessionStore` owns current/previous-handle overlap for 30 seconds, revocation, idle/absolute expiry, and logout; Task 6 chooses/hardens its persistence without changing this HTTP contract. No identity/access/refresh/session token appears in URL, response JSON, JavaScript, localStorage, sessionStorage, or `NEXT_PUBLIC_*`.

OIDC start creates one server-side flow with state hash, PKCE S256 verifier/challenge, nonce hash, exact issuer/client/redirect IDs, safe validated internal return path, and 10-minute expiry. It sets only `__Host-alon_ai_oidc_flow` as a 256-bit opaque `Secure; HttpOnly; SameSite=Lax; Path=/; Domain` absent and `Max-Age=600` cookie. Google's current [OIDC API reference](https://developers.google.com/identity/openid-connect/reference) says the authorization response `iss` is always exactly `https://accounts.google.com`, while a verified ID token may use issuer `https://accounts.google.com` or legacy `accounts.google.com`; accessed 2026-08-29. Therefore callback `iss` must byte-equal `https://accounts.google.com`, and only verified ID-token `iss` uses the exact allowlist `{accounts.google.com, https://accounts.google.com}`. Neither comparison permits suffix/prefix/case normalization or a configured third value.

Callback requires the flow cookie and one strict, duplicate-free, size-bounded query arm for the configured authorization-code response type. Success requires exactly `code,state,iss` and permits only optional `scope`; error requires exactly `error,state,iss` and permits only optional `error_description`. Success forbids every error field, error forbids every success field except echoed `state`/required `iss`, and every other Google response-table field or arbitrary parameter—including `id_token`, `access_token`, `token_type`, `expires_in`, `authuser`, `hd`, `prompt`, and `error_uri`—is rejected rather than copied/logged. The bounded Google redirected-error catalog is exactly `access_denied|invalid_request|unauthorized_client|unsupported_response_type|invalid_scope`; `access_denied` maps to the denied redirect and every other recognized error to invalid as registered, while unknown values reject. State/flow is always verified and consumed once. The code arm verifies the exact HTTPS callback issuer before exchange, then PKCE, nonce, ID-token signature, exact verified-ID-token issuer-set membership, audience, authorized-party where present, issued/expiry time, and exact configured operator subject before rotation. It clears the flow cookie and 303-redirects only to the stored allowlisted relative path or fixed failure location. Successful callback redirects to the stored allowlisted relative `return_path`; the only failure locations are `303 {operator_origin}/?operator_auth=auth_invalid`, `...?operator_auth=auth_denied`, or `...?operator_auth=auth_expired`. Provider text/email/tokens are never rendered or logged. Reauthentication replaces the prior session and revokes it after the overlap. Logout revokes the server record before expiring the cookie. Auth start/callback/session/logout emit safe audit with subject hash, flow/session IDs, result/reason, correlation, and no token or claims payload.

Every unsafe session-authenticated request requires exact configured `Origin`, `Sec-Fetch-Site: same-origin`, and constant custom header `X-CSRF-Intent: operator-command-v1`; logout uses `X-CSRF-Intent: operator-session-v1`. Missing/mismatched Origin/fetch metadata/header is 403 `AUTHORIZATION_DENIED` reason `CSRF_CHECK_FAILED` before command dispatch. CORS permits only the configured operator frontend origin and credentials. Mutating JSON requests require `Content-Type: application/json`. Gmail OAuth callback authority remains the operator/flow binding inside signed+encrypted state and executes only `CompleteGmailAuthorization`; it never uses or exposes the OIDC flow/session.

Every session-authenticated business mutation except the Gmail OAuth callback requires caller-supplied `Idempotency-Key` of 16..200 visible ASCII characters. Public unsubscribe POST instead derives its unforgeable key from the verified token JTI and accepts no caller key. OIDC start requires the key but binds it to the anonymous flow cookie/Origin; OIDC callback derives its one-time flow key; session GET/logout are idempotent session operations and do not enter the business command registry. Updates to explicit versions—`experiments.version`, `outreach_messages.version`, `suppression_entries.version`, `system_controls.version`, and `gmail_history_cursors.version`—require `If-Match: "{positive_version}"`; missing is 428, known mismatch 412, transactional race 409. Campaign commands carry immutable positive `campaign_version` in the path plus exact `expected_state`; action-authorization/mailbox/workflow/artifact commands lock exact expected state/status. Artifact commands additionally require exact `artifact_version` and `content_hash`. The Gmail callback derives `command_scope=gmail.oauth.complete:{oauth_flow_id}` and `idempotency_key=oauth-flow:{oauth_flow_id}` and preserves the existing exact resume/replay rules. The application derives a route/actor/resource scope and DB-01 request hash. Same scope/key/hash returns the original status/body/Location/ETag/correlation; changed hash is 409. Commands that commit work then signal a workflow return 202 without claiming completion.

Client may send `X-Request-ID` UUIDv4; invalid values return 400. Otherwise middleware creates it. Every request creates/propagates UUIDv4 `correlation_id`; commands set `causation_id` to the HTTP request ID. Responses include `X-Request-ID` and `X-Correlation-ID`. Logs use safe IDs/route template/status/duration only.

Success shapes are strict/extra-forbid. A response backed by an explicitly registered optimistic-version column carries HTTP `ETag: "{version}"`; other resource-specific schemas expose their immutable campaign/brief version or expected state without inventing a mutable version. A mutating response carries the resulting aggregate ETag only when that explicit version changed:

- `ResourceResponseV1={schema_version,data,version,correlation_id}`;
- `CommandReceiptV1={schema_version:"api.command_receipt.v1",command_type,command_scope,idempotency_key,status:"COMMITTED"|"ACCEPTED",aggregate_type,aggregate_id,aggregate_version,workflow_run_id,result_hash,correlation_id}`;
- `PageResponseV1={schema_version,items,next_cursor,as_of,projection_version,correlation_id}`.

Exact named resource/query schemas are strict and extra-forbid; braces below are the complete browser allowlist, not examples:

- `CampaignVersionResponseV1={schema_version:"api.campaign_version.response.v1",data:{campaign_version_id,campaign_id,campaign_version,experiment_id,supersedes_campaign_version_id,state,offer_id,offer_version,offer_content_hash,policy_version,membership_mode:"ALL_CURRENTLY_ELIGIBLE",eligibility_snapshot_version,eligibility_snapshot_at,eligibility_query_version,eligible_set_hash,eligible_member_count,member_cap,send_window_start,send_window_end,reply_window_end,daily_cap,total_cap,removed_member_count,members:[{campaign_member_id,lead_id,eligibility_ordinal,eligibility_basis_hash,status,lead_state,identity_state,suppression_entry_id,compliance_refs:{recipient_identity_evidence_ref,jurisdiction_evidence_ref,affirmative_consent_evidence_ref?,counsel_exception_evidence_ref?,legal_review_ref,legal_policy_version,disclosure_sender_template_ref,google_policy_review_ref},message:{message_id,mailbox_id,state,version,content_hash,authorization_id},created_at,removed_at}],created_at,updated_at},correlation_id}`. Every `*_ref` is the exact accepted `{artifact_id,artifact_version,content_hash}` tuple, exactly one consent/exception ref is present, and recipient address hashes/digests/ciphertexts are forbidden.
- `OutreachMessageResponseV1={schema_version:"api.outreach_message.response.v1",data:{message_id,experiment_id,campaign_id,campaign_version,campaign_member_id,lead_id,mailbox_id,provider_account_hash,artifact_id,state,version,content_hash,action_authority:{authorization_id,state,action_kind,scope_hash,offer_id,offer_version,strategy_version_id,activation_id,cohort_id,control_generation,checkpoint_generation,max_effect_count,expires_at,current_authority_valid,stale_reason_codes},final_send_compliance:{policy_decision_id,facts_observed_at,recipient_identity_status,recipient_identity_verified_at,recipient_identity_expires_at,jurisdiction_status,jurisdiction_code,jurisdiction_evidence_retrieved_at,jurisdiction_evidence_published_at,jurisdiction_evidence_expires_at,authority_route,consent_status,consent_captured_at,consent_verified_at,consent_expires_at,counsel_exception_decided_at,counsel_exception_effective_at,counsel_exception_expires_at,legal_review_id,legal_review_status,legal_review_effective_at,legal_review_expires_at,legal_policy_version,legal_policy_current,disclosure_sender_template_id,disclosure_sender_template_version,disclosure_sender_template_content_hash,disclosure_validator_version,disclosure_valid,google_policy_review_id,google_policy_review_version,google_policy_status,google_policy_effective_at,google_policy_expires_at,google_policy_compatible,reply_observed,unsubscribe_observed,hard_bounce_observed,complaint_observed,soft_bounce_count,soft_bounce_limit,soft_bounce_last_observed_at,evidence_refs:[{artifact_id,artifact_version,content_hash}],observation_reference_ids,reason_codes},send_intent:{send_intent_id,state,rfc_message_id_hash,policy_decision_id},send_attempt:{send_attempt_id,attempt_number,state,provider_result_id,provider_observation_ids,ambiguity_incident_id,retry_not_before,retry_count,retry_cap},reply:{reply_id,state,classification_artifact_id},timeline:[{timeline_item_id,event_type,state,occurred_at,reason_codes,safe_reference_ids}],created_at,updated_at},version,correlation_id}`. The final-send block is nullable before evaluation; consent fields are non-null only for `AFFIRMATIVE_CONSENT`, exception fields only for `COUNSEL_EXCEPTION`, and it exposes bounded status/enums/exact evidence tuples/record references only—never recipient hash, consent/legal text, source content, or address.
- `IncidentRepairResponseV1={schema_version:"api.incident_repair.response.v1",data:{incident_id,catalog_version:"incident.catalog.v1",trigger_code,runbook_id,alert_id,repair_kind,incident_state,resolution_code,evidence_ref,workflow_run_id,command_status,opened_at,resolved_at,updated_at},correlation_id}`. `RepairIncidentRequestV1` uses the exact DB-05 repair-kind enum plus expected-before/desired-after hashes and evidence ref; unknown catalog values, cross-paired trigger/alert/runbook tuples, inapplicable trigger/resolution or repair/runbook combinations, and forbidden residual-risk acceptance are rejected before command claim and again by named PostgreSQL checks.
- `SuppressionResponseV1={schema_version:"api.suppression.response.v1",data:{suppression_entry_id,scope,business_id,recipient_target_ref_id,reason_code,source:enum[OPERATOR,GMAIL_UNSUBSCRIBE,GMAIL_HARD_BOUNCE,GMAIL_COMPLAINT,GMAIL_SOFT_BOUNCE_LIMIT,PUBLIC_UNSUBSCRIBE,QUALIFIED_NO_FUTURE_CONTACT,LEGAL_PROHIBITION],source_actor_type,source_observation_id,source_reply_id,active,version,created_at,deactivated_at},version,correlation_id}`. The opaque stored `recipient_target_ref_id` is non-null iff `scope=RECIPIENT`; it is stable after source-member cleanup and is read directly from `suppression_entries`, never reconstructed from lookup material. `recipient_hash`, address ciphertext, content digests, and every derived lookup value are absent from all HTTP schemas.
- `UnsubscribeConfirmationHtmlV1` is the exact self-contained FastAPI HTML byte contract below; it is not JSON, a generated-client model, a Next.js resource, or a product record. `UnsubscribeResultResponseV1={schema_version:"api.unsubscribe_result.response.v1",status:"SUPPRESSED"|"ALREADY_SUPPRESSED"|"INVALID_OR_EXPIRED",processed_at?,correlation_id}` contains no recipient/campaign/message/token/hash identifier.
- `ArtifactResponseV1={schema_version:"api.artifact.response.v1",data:{artifact_id,experiment_id,artifact_type,artifact_schema_version,artifact_version,status,agent_run_id,agent_type,agent_version,prompt_version,model_provider,model_name,model_version,toolset_version,input_snapshot_hash,content_hash,allowlisted_content,confidence,abstention_reason,supersedes_artifact_id,latest_validation:{artifact_validation_id,validator_version,schema_valid,provenance_valid,reason_codes,facts_hash,created_at},acceptance:{artifact_acceptance_id,acceptance_mode,gate_version,scope_hash,created_at},evidence_count,evaluation_result_ids,redaction_state,created_at},correlation_id}`.
- `ArtifactEvidenceResponseV1={schema_version:"api.artifact_evidence.response.v1",data:{artifact_id,evidence_item_id,evidence_type,citation_uri,citation_uri_hash,source_policy_version,source_provider,retrieved_at,published_at,content_hash,mime_type,language,license_basis,redaction_state,claim_pointer,relationship,source_excerpt_hash,created_at},correlation_id}`; raw locator/ciphertext, `capture_ref`, query secrets/PII, and source content are never serialized.
- `EvaluationResultResponseV1={schema_version:"api.evaluation_result.response.v1",data:{evaluation_result_id,evaluation_case_id,suite_name,suite_version,case_key,agent_run_id,evaluator_version,scores_schema_version,scores,scores_hash,passed,reason_codes,sensitivity_class,input_hash,expected_hash,created_at},correlation_id}`; restricted case snapshots/rubrics are omitted.
- `OperatorAuthorizationResponseV1={schema_version:"api.operator_authorization.response.v1",authorization_url,flow_expires_at,correlation_id}`, `OperatorSessionResponseV1={schema_version:"api.operator_session.response.v1",operator_id,subject_hash,issued_at,idle_expires_at,absolute_expires_at,reauth_required,correlation_id}`, and `OperatorSessionEndedResponseV1={schema_version:"api.operator_session_ended.response.v1",ended:true,ended_at,correlation_id}`. None contains provider claims/tokens/email.

Opaque pagination cursor signs route/filter/order/last-key/projection-version/expiry; tamper/mismatch is `VALIDATION_FAILED`. List order is explicitly stable per route. `limit` defaults 50 and is 1..100.

### Exact route and OpenAPI operation manifest

The closed manifest is the exact set of method/path/operationId rows in this document. All private rows belong to PRIVATE_DEPLOYMENT and exactly the following two belong to PUBLIC_UNSUBSCRIBE. The partition is release-enforced metadata as well as documentation; duplicate, unclassified, or differently classified operations fail generation. `PRIVATE_DEPLOYMENT` means the private operator deployment surface, including its specifically documented health and OAuth callback ingress, not that every operation uses the session cookie.

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
| `GET /api/v1/workflow-runs/{workflow_run_id}` | `getWorkflowRun`; canonical projection | 200 |
| `POST /api/v1/workflow-runs/{workflow_run_id}/commands/cancel` | `cancelWorkflowRun`; `CancelWorkflowRunRequestV1={schema_version,expected_state:enum[PENDING,RUNNING,PAUSE_REQUESTED,PAUSED],reason_code}` -> `CommandReceiptV1` | 202 after `CANCEL_REQUESTED` commit; operator session, CSRF, idempotency, locked expected state; resulting finite run remains queryable |

Campaigns, action authority, messages, controls, recovery:

| Method/path | `operationId` / schema | Success |
| --- | --- | --- |
| `POST /api/v1/experiments/{experiment_id}/campaigns` | `createCampaignVersion`; `CreateCampaignVersionRequestV1={schema_version:"api.create_campaign_version.request.v1",expected_experiment_version,offer_id,offer_version,offer_content_hash,policy_version,membership_mode:"ALL_CURRENTLY_ELIGIBLE",eligibility_snapshot_version,eligibility_query_version:"campaign.eligibility.v1",expected_eligible_set_hash,expected_eligible_member_count,member_cap,send_window_start,send_window_end,reply_window_end,daily_cap,total_cap}` -> `CampaignVersionResponseV1` | 201 + `Location`; all-or-nothing snapshot membership |
| `GET /api/v1/campaigns/{campaign_id}/versions/{campaign_version}` | `getCampaignVersion` -> `CampaignVersionResponseV1` | 200 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/ready` | `readyCampaign`; `ReadyCampaignRequestV1={schema_version,expected_state:"DRAFT",offer_id,offer_version,policy_version}` -> `CampaignVersionResponseV1` | 200 `DRAFT -> READY`; immutable path version + locked state; exact offer/policy, eligible-member, draft/action-authority guards; `campaign.ready.v1` |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/activate` | `activateCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/pause` | `pauseCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/resume` | `resumeCampaign`; `CampaignControlRequestV1` | 202 |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/cancel` | `cancelCampaign`; `CampaignControlRequestV1` | 202 |
| `GET /api/v1/messages/{message_id}` | `getOutreachMessage`; redacted message/send/reply timeline | 200 |
| `POST /api/v1/messages/{message_id}/commands/record-send-intent` | `recordMessageSendIntent`; `RecordSendIntentRequestV1` | 202 after atomic intent/queue commit |
| `POST /api/v1/messages/{message_id}/commands/abort-retry` | `abortMessageRetry`; `AbortSendRetryRequestV1` -> `OutreachMessageResponseV1` | 200 terminal message |
| `GET /api/v1/controls` | `listSystemControls` | 200 |
| `POST /api/v1/controls/{control_name}/commands/enable` | `enableSystemControl`; `ChangeControlRequestV1` | 200; product enable gate may deny |
| `POST /api/v1/controls/{control_name}/commands/disable` | `disableSystemControl`; `ChangeControlRequestV1` | 200 |
| `GET /api/v1/recovery/overview` | `getRecoveryOverview`; cursor/limit -> `PageResponseV1[RecoveryOverviewItemV1]` ordered `(attention_since,record_kind,record_id)` | 200 authenticated snapshot spanning workflow runs, IN_PROGRESS commands, unresolved Gmail/calendar attempts, cursor incidents, checkpoint/strategy activation blockers, and repair actions; 400 cursor, 409 expired snapshot restart, 503 corrupt source |
| `GET /api/v1/recovery/send-attempts` | `listUnresolvedSendAttempts`; cursor/limit, ordered `(started_at,send_attempt_id)` | 200 |
| `POST /api/v1/send-attempts/{send_attempt_id}/commands/reconcile` | `reconcileSendAttempt`; `ReconcileSendAttemptRequestV1` | 202 |
| `POST /api/v1/incidents/{incident_id}/commands/repair` | `repairIncident`; `RepairIncidentRequestV1` -> `IncidentRepairResponseV1` | 202/200 matching typed repair kind |

Both control POST routes are operator-only and `ChangeControlRequestV1` has no actor field; FastAPI derives `actor_type=OPERATOR` and the session operator ID. Registered internal system actors call `ControlCommandService.disable` directly with the DB-01 closed actor ID/reason/evidence union and cannot invoke either HTTP route. `listSystemControls` returns `actor_type` plus exactly one safe `changed_by_operator_id` or `changed_by_system_actor_id`; it never synthesizes an operator for fail-closed automation. Enable rejects the system union at both contract and database layers.

Campaign eligibility is server-owned. getExperiment/getExperimentOverviewReport expose the current cohort's snapshot version/query/hash/count/effective cap and governing offer/strategy/activation. Read-only lead discovery/dossier/qualification lists are allowed for inspection. CreateCampaignVersion/FreezeCohortMembership accepts no chosen member IDs; deterministic approved-source/filter/order rules select the eligible bounded set and freeze every member with same-scope accepted FINAL qualification and compliance evidence. Exact stage tuples are (1,100,100), (2,200,300), (3,300,600), (4,400,1000); effective cap is the smaller signed legal/provider/reputation/budget/configured cap. Scope/hash/count drift, duplicate recipient, stale evidence, wrong prior CONTINUE or concurrent final-slot loss returns a typed conflict with zero partial admission. No mid-cohort member/configuration rewrite is allowed.

Purpose-scoped sensitive inspection is available only through getExceptionSensitivePreview with an active operator session and step-up within five minutes. Missing/expired step-up returns 401 AUTHENTICATION_REQUIRED reason STEP_UP_REAUTH_REQUIRED before decrypting. Responses use Cache-Control: no-store, max-age=0, Pragma: no-cache and Referrer-Policy: no-referrer; no telemetry/cache/browser persistence/prefetch/service worker/analytics copy. SensitivePreviewService returns exact scope/materialization and opaque session/operator/exception-bound receipt, at most five minutes. The read grants no action authority. Routine authorization and deterministic artifact acceptance require no preview.

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

Path IDs parse UUIDv4 except the bounded opaque public unsubscribe token; campaign versions are positive. Literal canonical state/control names are OpenAPI enums, not display labels. Routes not listed are not part of v1. The manifest is the union of every concrete method/path/operationId row in this document, including the autonomous-sales table below. OpenAPI generation verifies exact set equality, uniqueness, schemas/statuses, owner and PRIVATE_DEPLOYMENT versus the two PUBLIC_UNSUBSCRIBE operations. No other public route is permitted. Gateway writes and runtime deterministic internal commands are not arbitrary HTTP endpoints.

### Exact operation preconditions and failures

This table fixes authentication/status behavior for these named operations; listed statuses are exhaustive in addition to their declared success, and every code uses the global `ProblemDetailsV1` mapping below.

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


### Autonomous sales API operations

Each concrete row adds one unique operationId. All are PRIVATE_DEPLOYMENT, require the opaque operator session, expose strict extra-forbid schemas and use BACKEND-06 query owners. GET lists use signed filter/cutoff/projection-bound pagination; detail GETs return 200 or 401/403/404/503. Lists additionally permit 400 invalid cursor and 409 REPORT_SNAPSHOT_EXPIRED. Sensitive detail uses no-store/redaction and explicit purpose. POST requires command CSRF/Origin, Idempotency-Key, strict JSON and expected state/version (If-Match for mutable version) and returns 200/202 after commit, or the canonical 400/401/403/404/409/412/428/429/503 errors. No provider call runs in the route.

| Method/path | operationId / exact request or response | Owner / success |
| --- | --- | --- |
| GET /api/v1/experiments/{experiment_id}/offers | listOfferPackages -> PageResponseV1[OfferPackageResponseV1] | OfferQueryService / 200 |
| GET /api/v1/offers/{offer_id} | getOfferPackage -> OfferPackageResponseV1 | OfferQueryService / 200 |
| GET /api/v1/offers/{offer_id}/economics | getOfferEconomics -> OfferEconomicsResponseV1 | OfferQueryService / 200 |
| POST /api/v1/experiments/{experiment_id}/commands/materialize-idea | materializeSuppliedIdea; {schema_version,idea_text,user_provenance,expected_idea_origin:USER_SUPPLIED} | IdeaBriefMaterializer / 201 canonical IdeaBrief, before research |
| POST /api/v1/experiments/{experiment_id}/commands/configure-envelope | configureOfferEnvelope; {schema_version,expected_brief_version,economics_constraints,source_allowlist_version,conversation_booking_policy_version,reason_code} | ExperimentBriefCommandService / 200 new pre-run brief; active-cohort mutation denied |
| GET /api/v1/experiments/{experiment_id}/lead-sources | listLeadSources -> PageResponseV1[LeadSourceResponseV1] | LeadQueryService / 200 |
| GET /api/v1/experiments/{experiment_id}/lead-candidates | listLeadCandidates -> PageResponseV1[LeadCandidateResponseV1] | LeadQueryService / 200 |
| GET /api/v1/leads/{lead_id}/dossier | getLeadDossier -> LeadDossierResponseV1 | LeadQueryService / 200 |
| GET /api/v1/leads/{lead_id}/qualification | getLeadQualification -> QualificationResponseV1 | LeadQueryService / 200 with both explicit phases |
| GET /api/v1/campaigns/{campaign_id}/cohorts | listCampaignCohorts -> PageResponseV1[CohortResponseV1] | CampaignQueryService / 200 |
| GET /api/v1/action-authorizations/{authorization_id} | getActionAuthorization -> ActionAuthorizationResponseV1 | ActionAuthorizationQueryService / 200; read cannot authorize |
| GET /api/v1/campaigns/{campaign_id}/send-blocks | listSendBlocks -> PageResponseV1[SendBlockResponseV1] | ActionAuthorizationQueryService / 200 |
| GET /api/v1/campaigns/{campaign_id}/conversations | listConversations -> PageResponseV1[ConversationSummaryV1] | ConversationQueryService / 200 |
| GET /api/v1/conversations/{conversation_id} | getConversation -> ConversationResponseV1 | ConversationQueryService / 200 redacted complete ordered thread |
| GET /api/v1/conversations/{conversation_id}/negotiations | listNegotiationDecisions -> PageResponseV1[NegotiationResponseV1] | ConversationQueryService / 200 |
| POST /api/v1/conversations/{conversation_id}/commands/pause | pauseConversation; {schema_version,expected_state,reason_code} | ConversationService / 200, increment generation |
| GET /api/v1/bookings | listBookings -> PageResponseV1[BookingResponseV1] | BookingQueryService / 200 |
| GET /api/v1/bookings/{booking_intent_id} | getBooking -> BookingResponseV1 | BookingQueryService / 200 |
| GET /api/v1/calendars | listCalendarAccounts -> PageResponseV1[CalendarAccountResponseV1] | CalendarAccountService / 200 safe configured account states |
| GET /api/v1/calendars/{calendar_id}/availability | getCalendarAvailability; bounded UTC window/IANA timezone/duration -> AvailabilityResponseV1 | AvailabilityService / 200; not reservation/confirmation |
| POST /api/v1/bookings/{booking_intent_id}/commands/reschedule | requestBookingReschedule; {schema_version,expected_state,confirmation_id,slot_id,slot_hash,reason_code} | BookingGateway / 202 only after existing explicit lead confirmation and fresh guards |
| POST /api/v1/bookings/{booking_intent_id}/commands/cancel | requestBookingCancellation; {schema_version,expected_state,reason_code,evidence_ref} | BookingGateway / 202 separate authorized cancellation |
| POST /api/v1/booking-actions/{booking_action_id}/commands/reconcile | reconcileBookingAction; {schema_version,expected_state,reason_code} | BookingGateway / 202 read reconciliation, no retry |
| GET /api/v1/campaigns/{campaign_id}/checkpoints | listCheckpoints -> PageResponseV1[CheckpointResponseV1] | CheckpointQueryService / 200 |
| GET /api/v1/checkpoints/{checkpoint_id} | getCheckpoint -> CheckpointResponseV1 | CheckpointQueryService / 200 |
| GET /api/v1/checkpoints/{checkpoint_id}/evidence | getCheckpointEvidence -> CheckpointEvidenceResponseV1 | CheckpointQueryService / 200 minimized evidence only |
| GET /api/v1/strategies | listGlobalStrategies -> PageResponseV1[StrategyResponseV1] | StrategyQueryService / 200 |
| GET /api/v1/strategies/{strategy_version_id} | getGlobalStrategy -> StrategyResponseV1 | StrategyQueryService / 200 |
| GET /api/v1/strategies/{strategy_version_id}/evidence | getStrategyEvidence -> StrategyEvidenceResponseV1 | StrategyQueryService / 200 protected evaluation summary |
| GET /api/v1/campaigns/{campaign_id}/strategy-activations | listStrategyActivations -> PageResponseV1[StrategyActivationResponseV1] | StrategyQueryService / 200 |
| POST /api/v1/campaigns/{campaign_id}/commands/request-strategy-rollback | requestStrategyRollback; {schema_version,expected_activation_id,target_strategy_version_id,expected_checkpoint_generation,reason_code,evidence_ref} | StrategyActivationService / 202 pause/close/boundary gate, never immediate pointer update |
| GET /api/v1/exceptions | listExceptions -> PageResponseV1[ExceptionResponseV1] | ExceptionQueryService / 200 |
| GET /api/v1/exceptions/{exception_id} | getException -> ExceptionResponseV1 | ExceptionQueryService / 200 |
| GET /api/v1/exceptions/{exception_id}/sensitive-preview | getExceptionSensitivePreview; purpose -> SensitivePreviewResponseV1 | SensitivePreviewService / 200 step-up/no-store; no send authority |
| POST /api/v1/exceptions/{exception_id}/commands/resolve | resolveException; {schema_version,expected_state,reason_code,correction_command_ref,evidence_ref} | ExceptionCommandService / 200 after deterministic correction; cannot waive bounds |
| GET /api/v1/reports/exceptions | getExceptionQueueReport -> PageResponseV1[ExceptionResponseV1] | ExceptionQueryService / 200 |

Strict new DTO allowlists (common schema_version/correlation_id plus PageResponseV1 paging; no additional DB fields automatically serialize):

- OfferPackageResponseV1: offer_id/version/hash, idea_origin/idea_ref, research_ref, accepted_status, customer/problem/solution/positioning, permitted scope/deliverables/exclusions, claim-to-minimized-evidence refs, qualification_filter_version, booking_policy_version, valid_from/expires_at, strategy_version_id/activation_id.
- OfferEconomicsResponseV1: offer_id/version/hash, currency, base/minimum_net_price_minor, delivery_cost_minor, fee/tax/FX/rounding versions, margin_floor_bps, allowed variants/pilots/discount_bands/payment schedules, server_calculated_examples, cost_evidence_status. Client may format, never recompute authoritative outcomes.
- LeadSourceResponseV1/LeadCandidateResponseV1/LeadDossierResponseV1/QualificationResponseV1: source_id/adapter/scope/query/filter/version/time/review status; candidate/lead/business/person opaque refs; dedupe disposition; sanitized business facts with FACT/ESTIMATE/UNKNOWN/confidence/minimized evidence; offer/filter version; separate phase/result/reasons/artifact refs; no invented identity or raw contact/hash.
- CohortResponseV1: campaign/cohort/stage IDs, exact increment/cumulative/effective caps, member_count/hash, eligibility snapshot/query, offer/strategy/activation, qualification/causal/evidence/metric versions, prior/current checkpoint, state/generations and remaining capacity.
- ActionAuthorizationResponseV1/SendBlockResponseV1: authorization/action/message/conversation/cohort IDs, action kind/content/scope hash, offer/strategy/activation, expiry/state/generations, commercial/fresh policy decision IDs, allowed/status/reason_codes/as_of; no raw facts or manual-approval action.
- ConversationSummaryV1/ConversationResponseV1: conversation/member/lead/business refs, canonical state, offer/strategy/activation, cold/terminal/negative-sentiment stop status, counters/window/deadline, current objective/commercial/booking refs, complete ordered messages {message_id,direction,occurred_at,redacted_subject,redacted_body,redaction_state,parent_id,reply_evaluation_ref,attribution_ref}; pagination pins conversation version/cutoff without dropping intervening messages.
- NegotiationResponseV1: proposal/decision IDs, objective, offer/variant/band, assertion_kind STATED/INFERRED/UNKNOWN, redacted budget availability, allowed/reason_codes, authoritative net/tax/gross/fees/cost/contribution/margin, rule/FX/rounding versions, purchase_acceptance_status, evidence refs/strategy/activation. Sensitive budget source spans require exception inspection.
- BookingResponseV1/AvailabilityResponseV1/CalendarAccountResponseV1: safe calendar/booking/action/provider-event opaque IDs, state, business/contact/conversation/campaign/cohort/offer/strategy/activation refs, buying_intent/call_agreement/optional_purchase status, labelled UTC/IANA/offset/tzdb/duration slots and expiry/confirmation status, attendee_count/notification mode, action kind/version/ETag hash/outcome/ambiguity reasons. No raw attendee list, private calendar description or tokens.
- CheckpointResponseV1/CheckpointEvidenceResponseV1: campaign/cohort/stage/checkpoint IDs, frozen cutoff/member/denominator/definitions, bundle/hash, exact five-way decision/reasons, costs/missing/unresolved/evidence_mode, minimized primary/secondary/guardrail refs and next-stage eligibility; no raw thread/body/PII.
- StrategyResponseV1/StrategyEvidenceResponseV1/StrategyActivationResponseV1: global version/hash/parent/status, applicable agent result set (PROMOTE/KEEP/ROLLBACK/INSUFFICIENT_EVIDENCE), minimized comparison/holdout/transfer/guardrail outcomes, expected metrics/confidence/rollback rule, campaign/cohort/checkpoint/prior activation/generations/effective time, history; no candidate-readable holdout payload or unrestricted prompt editing.
- ExceptionResponseV1: exception/scope/incident/action IDs, state/severity/reason, safe evidence refs, required correction/owner/expiry/generation, resolved command. SensitivePreviewResponseV1 adds only purpose-authorized decrypted fields, exact scope/materialization hash, preview expiry/opaque receipt under step-up/no-store controls; no tokens or provider client.

RecoveryOverviewItemV1 adds BOOKING_ACTION, CHECKPOINT and STRATEGY_ACTIVATION to the existing WORKFLOW_RUN/COMMAND/SEND_ATTEMPT/CURSOR_INCIDENT/REPAIR_ACTION union. Each arm carries the exact safe record ID/state/attention time/reasons/offer/cohort/strategy/activation refs and permitted typed next command; it never infers resolution. ArtifactResponseV1 additionally exposes scope_kind, nullable experiment_id, producer_kind/producer_id/producer_strategy_version, input_snapshot_kind/ID/hash, output_hash, governing_mode, governing strategy/activation, configuration manifest ref and immutable acceptance receipt. Null attribution is legal only for the explicitly non-product bootstrap/evaluation modes in DB-04.

All private new operations join the exact OpenAPI route-owner/schema/status/security/CSRF/role registry and generated fingerprint. There is no public booking, provider callback, strategy editor, raw-lead export or direct Gmail/calendar write route. The two M9 unsubscribe operations retain their separate scanner-safe token/Origin/rate/expiry contract unchanged.

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

<!-- roadmap-task id=BACKEND-02-T01 milestone=M4 depends_on=BACKEND-01-T03 mode=serial locks=openapi-contract -->
- [ ] **Implement the M4 private route foundation —** Input: the BACKEND-01 committed command-result/error boundary plus the document-local frozen M4 actor/route fixture and HTTP metadata contract. Operation: implement scope/hash/idempotency/safe-error/correlation mechanics without real OIDC. Output: versioned private route-boundary and HTTP-metadata contract usable with fixture actors before OIDC integration. Test evidence: fixture-actor, header, replay, error, and correlation snapshot matrix. Failure behavior: no handler, provider, or runtime call.
<!-- roadmap-task id=BACKEND-02-T02 milestone=M4 depends_on=BACKEND-02-T01,BACKEND-01-T04 mode=serial locks=openapi-contract -->
- [ ] **Implement M4/M5 no-send routes and client —** Input: BACKEND-01 no-send services and the M4 private route foundation. Operation: implement experiment/workflow, campaign-readiness, artifact/evidence/evaluation, and suppression operations in manifest order. Output: M4/M5 no-send OpenAPI and generated client. Test evidence: OpenAPI generation and real-service integration tests. Failure behavior: omit or block a route until its service exists.
<!-- roadmap-task id=BACKEND-02-T03 milestone=M6 depends_on=BACKEND-02-T02,PROVIDER-01-T04,PROVIDER-02-T01,BACKEND-03-T03,BACKEND-04-T04,BACKEND-05-T06,SEC-03-T02,SEC-04-T03,SEC-05-T04,SEC-02-T04,BACKEND-05-T02 mode=serial locks=openapi-contract,security-runtime -->
- [ ] **Implement the isolated M6 owned-inbox API —** Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service. Operation: bind the implemented SEC-02 OIDC/session/request owner and expose authenticated owned-inbox Gmail OAuth/callback, mailbox, campaign readiness/list/detail, action authority, deterministic send blocks and exception inspection, message/timeline, control and Gmail-specific reconcile/retry routes through canonical services; complete sales/report/recovery projections remain in the distinct M7 contract/route tasks. Output: authenticated M6 owned-inbox command/query/preview API and generated contract; later M7 full private/report manifest remains separate. Test evidence: OAuth, command, authority, ambiguity, recovery, and status E2E cases under the isolated M6 profile. Failure behavior: send controls remain false and a fresh OAuth flow is required when state is invalid.
<!-- roadmap-task id=BACKEND-02-T04 milestone=M7 depends_on=BACKEND-02-T03,SEC-02-T04,BACKEND-06-T01 mode=serial locks=openapi-contract,security-runtime -->
- [ ] **Freeze the authenticated M7 report/recovery contract —** Input: the M6 owned-inbox API, SEC-02 authenticated session/request boundary, and BACKEND-06 stable projection/query schemas. Operation: freeze one versioned private/report/recovery OpenAPI contract that binds each private operation to the existing SEC-02 boundary before BACKEND-06 route implementation. Output: versioned authenticated M7 private/report/recovery OpenAPI contract. Test evidence: schema, scope, session, Origin/CSRF, pagination, cursor, error, redaction, and zero-route-implementation tests. Failure behavior: BACKEND-06 implementation and private UI generation remain blocked.
<!-- roadmap-task id=BACKEND-02-T05 milestone=M7 depends_on=BACKEND-02-T04,BACKEND-06-T04 mode=serial locks=openapi-contract,frontend-client -->
- [ ] **Generate and gate the disabled-public API manifest and client —** Input: the authenticated M7 contract, BACKEND-06 implemented report/recovery routes, composed FastAPI app, and document-local frozen public-ingress requirements. Operation: emit deterministic OpenAPI, exact listed-private-plus-two-public-disabled manifest, and generated TypeScript client; prove the public pair is unavailable and unpublished before M9. Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client. Test evidence: generated drift, route/status uniqueness, authentication binding, private-only deployment, and disabled-public synthetic edge tests. Failure behavior: CI/release remains blocked with no public ingress or real-recipient outreach.

## Test strategy

- **Contract `test_api_manifest_has_exact_registered_paths_methods_operation_ids_schemas_and_statuses`:** exact set equality and every listed PRIVATE_DEPLOYMENT row plus exactly two PUBLIC_UNSUBSCRIBE rows; no undocumented/unclassified route.
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
