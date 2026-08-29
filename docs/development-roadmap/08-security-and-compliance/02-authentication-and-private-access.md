# Authentication and Private Operator Access

**Document ID:** SEC-02
**Status:** Planned M7-M8 single-operator access; no product authentication, OIDC flow, server session, private ingress, or revocation system exists today
**Milestone:** M7 operator control plane and M8 private-deployment gate
**Owner:** Solo operator
**Prerequisites:** [BACKEND-01 `OperatorSessionService`](../06-backend/01-domain-services.md), [BACKEND-02 exact auth/session API](../06-backend/02-api-contracts.md), [FRONTEND-01](../07-frontend/01-information-architecture.md), [FRONTEND-09](../07-frontend/09-error-recovery-and-accessibility.md), SEC-01, and SEC-03
**Outputs:** Configured-subject Google OIDC, server-side opaque sessions, CSRF/private-ingress enforcement, rotation/revocation/bootstrap/recovery, and retained authentication evidence
**Unlocks:** Authenticated use of the exact 66-operation API and M8 private operation
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Only Alon's exact configured Google OIDC issuer/subject can obtain a FastAPI-owned browser session. The browser holds only an opaque `__Host-alon_ai_session`; FastAPI resolves all authority server-side before any resource lookup or command claim. Identity OAuth never grants Gmail access and Gmail OAuth never authenticates the operator.

[NIST SP 800-63B-4 session management](https://pages.nist.gov/800-63-4/sp800-63b.html), [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html), [Google OAuth 2.0 policies](https://developers.google.com/identity/protocols/oauth2/policies), [RFC 7636 PKCE](https://www.rfc-editor.org/rfc/rfc7636), [OAuth 2.0 Security Best Current Practice, RFC 9700](https://www.rfc-editor.org/rfc/rfc9700), and the [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) and [CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) guidance were accessed 2026-08-29. They support engineering choices; Alon AI does not claim NIST/OWASP conformance.

## Current repository state

Only unauthenticated health endpoints and CORS exist. There are no product routes, Google OIDC configuration, subject allowlist, flow/session store, session cookie, CSRF dependency, private network layer, logout, concurrent-session view, revocation, reauthentication, security audit, or recovery command. All behavior below is planned. The four auth operations and cookie durations are frozen by BACKEND-02 and are not renamed here.

## Scope and non-goals

In scope: `startOperatorAuthorization`, `completeOperatorAuthorization`, `getOperatorSession`, `endOperatorSession`; exact subject allowlist; state/nonce/PKCE; opaque cookies; server-side persistence; fixation/replay/CSRF/enumeration controls; idle/absolute expiry; rotation overlap; concurrent sessions; logout, key rotation, emergency revoke; safe bootstrap/recovery; and private ingress.

Non-goals: passwords, public signup, magic links, roles/teams, email-domain authorization, accepting any Google account, JavaScript tokens, bearer access tokens for the product API, Next.js auth backend, Gmail OAuth reuse, security questions, permanent break-glass sessions, or bypassing OIDC when Google is unavailable.

## Exact planned implementation surfaces

Create `api/operator_sessions.py`, `api/dependencies/auth.py`, `api/dependencies/csrf.py`, `security/session_store.py`, `security/oidc.py`, `security/private_ingress.py`, `application/operator_sessions.py`, and `tests/security/test_operator_sessions.py`. `OperatorSessionService` remains the sole auth/session owner and maps only the four frozen auth operations. Product routes resolve the operator from this dependency before invoking canonical application services.

### Exact configuration and subject authority

Required secret/non-public configuration: one HTTPS `operator_origin`; exact callback issuer `https://accounts.google.com`; fixed verified-ID-token issuer set exactly `{accounts.google.com, https://accounts.google.com}`; client ID and secret references; exact callback URI; a non-empty subject allowlist with one active subject for the initial solo deployment; fixed internal return-path prefixes; cookie/flow key-ring generations; and trusted reverse-proxy CIDRs. The authorization tuple is `(verified ID-token issuer-set member, exact subject)`; issuer-set membership is byte-exact before the authority check. Email, hosted domain, display name, tenant/domain membership, or an `email_verified` claim never substitutes. Google's [OIDC API reference](https://developers.google.com/identity/openid-connect/reference) states that authorization-response `iss` is always `https://accounts.google.com` and separately documents the legacy ID-token issuer representation; [RFC 9207](https://www.rfc-editor.org/rfc/rfc9207) defines the authorization-response `iss` parameter (both accessed 2026-08-29).

Startup refuses product routes when configuration is missing, wildcarded, HTTP outside explicit local development, mismatched to deployment origin, contains a query/fragment, trusts an unbounded proxy range, or has no active subject. `/health/live` remains process liveness; readiness reports only a safe `authentication_configuration` dependency state. It never returns subjects/client IDs/secrets.

### Exact OIDC flow protocol

1. `POST /api/v1/auth/authorizations` validates exact Origin, `Sec-Fetch-Site: same-origin`, JSON content type, anonymous-flow idempotency key, and a relative return path under the fixed allowlist.
2. Generate 256-bit flow handle, 256-bit `state`, 256-bit `nonce`, and PKCE verifier using the platform CSPRNG. Persist only flow-handle/state/nonce lookup digests; encrypt the verifier and required flow payload under SEC-03. Store exact issuer/client/redirect/return path, creation/expiry, idempotency request hash/result, and state `PENDING`.
3. Return only the allowlisted Google authorization URL and set `__Host-alon_ai_oidc_flow`: opaque, `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`, no `Domain`, `Max-Age=600`. Use authorization code flow plus PKCE S256 and minimal `openid` subject-identification scopes; do not request Gmail scopes.
4. `GET /api/v1/auth/callback` accepts the configured authorization-code response only: a duplicate-free strict success arm requiring `code,state,iss` with optional `scope`, or an error arm requiring `error,state,iss` with optional `error_description`, plus the flow cookie. It rejects body, code/error splice, missing `iss`, every other documented response-table field for a different response type, arbitrary extras (`authuser`, `hd`, `prompt`, `error_uri` included), duplicates, unknown error value, oversized/malformed values, wrong method/host/callback URI, or missing flow. The Google documented redirected-error values are exactly `access_denied|invalid_request|unauthorized_client|unsupported_response_type|invalid_scope`; the optional description is size-validated then discarded.
5. Validate callback `iss` byte-for-byte as exactly `https://accounts.google.com`, then atomically claim and consume the flow once before code exchange. Constant-time verify state digest. On the code arm verify TLS response, PKCE, provider signature/JWK/algorithm, ID-token `iss` against the separate exact set `{accounts.google.com, https://accounts.google.com}`, client audience/authorized party, nonce, issued/expiry/not-before bounds with tested clock skew, and exact configured subject. Provider email/text/claims/tokens are never logged or rendered.
6. Rotate to a completely new session handle; clear the flow cookie; return only the stored relative success path or fixed `auth_invalid`, `auth_denied`, `auth_expired` redirect defined by BACKEND-02. Callback replay returns a safe fixed failure and creates no session.

### Server-side session store and frozen cookie contract

Use a dedicated `security_runtime` persistence namespace with `operator_oidc_flows` and `operator_sessions`. These are operational security records, not M2 product data and do not change the frozen 46-product-table manifest. PostgreSQL is selected for the initial single-VPS deployment because API/worker-safe transactions, restart survival, CAS, backup, and revocation already exist operationally; no Redis/Vault cluster is introduced. The rows contain digests and encrypted flow material only, never Google or Gmail tokens.

`operator_sessions` fields are: UUID `session_id`; `operator_id`; `subject_hash`; HMAC-SHA-256 `current_handle_digest`; nullable previous digest/expiry; `key_generation`; `issued_at`; `last_seen_at`; `idle_expires_at`; fixed `absolute_expires_at`; `rotate_after`; state `ACTIVE|REVOKED|EXPIRED`; revocation reason/time; created IP-prefix hash and user-agent-family enum for anomaly evidence; and optimistic version. `operator_oidc_flows` carries the exact encrypted/digested fields from the flow protocol, `PENDING|CLAIMED|CONSUMED|EXPIRED`, claim lease, and idempotent result hash.

The `__Host-alon_ai_session` cookie is exactly 256-bit random, `Secure; HttpOnly; SameSite=Strict; Path=/`, `Domain` absent. Idle expiry is 30 minutes; absolute expiry is fixed eight hours. `Max-Age` is remaining absolute lifetime capped at 28,800 seconds and `Expires` is the fixed absolute UTC instant. Active use rotates every 15 minutes; the previous handle remains valid for at most 30 seconds and cannot rotate again. Rotation never extends absolute expiry. Idle extension is server-side and cannot pass absolute expiry; writes are coalesced to at most once per minute.

Handle lookup is `HMAC-SHA-256(session_lookup_key_generation, raw_handle)`; neither raw handle nor digest appears in logs/telemetry/errors. Compare digests in constant time. A found row still requires `ACTIVE`, configured subject remains allowlisted, operator active, idle/absolute time valid, and key generation accepted. Unknown/revoked/expired/old-overlap handles return the same opaque 401 body class and clear the cookie.

### CSRF, XSS, private ingress, and enumeration

Every unsafe session-authenticated product request requires exact configured `Origin`, `Sec-Fetch-Site: same-origin`, mutating JSON content type, and `X-CSRF-Intent: operator-command-v1`; logout requires `operator-session-v1`. Reject before idempotency/command dispatch. Cookie SameSite is defense-in-depth, never the only CSRF control. CORS allows exactly `operator_origin` with credentials and no wildcard. Reverse proxy accepts only HTTPS, overwrites forwarded headers, sets HSTS after deployment proof, limits request/query/header/body sizes, and exposes product routes only through the operator's authenticated private network or allowlisted ingress; health returns safe data.

Frontend content security policy starts `default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'` and adds only build/runtime nonces and required Google navigation origins. No raw HTML from evidence/model/provider is rendered. All identifiers are authorization-checked after session resolution. Anonymous or wrong-subject requests receive uniform safe errors and bounded rate limits by network-prefix bucket; no response distinguishes subject/resource existence.

### Concurrent sessions, logout, rotation, and emergency revoke

Allow at most two ACTIVE sessions for the configured operator to support laptop plus recovery device. Creating a third revokes the oldest before returning success and records safe audit. Reauthentication replaces the initiating session; the previous handle has only the frozen 30-second rotation overlap. `DELETE /api/v1/auth/session` revokes server state before expiring both cookies and is idempotent.

Normal key rotation adds a new active generation, issues only new handles, rewraps flow ciphertext where needed, and retains the previous lookup/decryption key only through the maximum eight-hour session plus ten-minute flow window; then all rows on that generation are revoked/expired before key destruction. Emergency revoke increments an `authentication_epoch`, atomically revokes all sessions/flows, clears cookies on next request, disables product mutations, and requires normal Google OIDC again. Confirmed OIDC client/key compromise also rotates the Google client secret and SEC-03 key generation.

### Safe bootstrap and recovery

Bootstrap is a local deployment ceremony, not an HTTP endpoint: generate/store key references; configure exact origin/redirect/subject from a separately verified Google account; run configuration and callback tests; start with both send controls false; authenticate normally; verify subject hash/audit; then enable only read/control-plane work allowed by the milestone. A bootstrap manifest records hashes, not subjects or secrets.

Lost browser/session uses normal OIDC. Lost device invokes the local authenticated `revoke-operator-sessions --all --reason <enum>` command from the VPS console/private recovery channel, then rotates keys if theft is suspected. Lost OIDC access has no bypass: keep product mutations and both send controls off, preserve data, restore Google account access or change the configured subject through an offline, two-artifact configuration release and re-bootstrap. Database recovery restores sessions as revoked/expired and flows as expired. A database/clock/key mismatch fails closed; no local admin cookie is minted.

## Ordered implementation tasks

- [ ] **Implement strict OIDC flow state —** Input: exact config, return path, Origin, anonymous key. Operation: persist digests/encrypted PKCE with 10-minute one-time CAS and verify the complete callback protocol. Output: configured-subject authentication only. Test evidence: exact success `{code,state,iss,scope?}` and error `{error,state,iss,error_description?}` arms; callback `iss=https://accounts.google.com` accepts while callback legacy/bogus/missing/duplicate issuer rejects; verified ID-token issuer accepts each of the separate two exact values and rejects every other value; state/nonce/PKCE/audience/subject/error/replay matrix. Failure behavior: fixed failure redirect, cleared flow cookie, no session.
- [ ] **Implement server-side sessions —** Input: verified subject. Operation: issue/digest/store/rotate opaque handle with frozen cookie, idle/absolute, overlap, optimistic concurrency, and two-session cap. Output: active operator context. Test evidence: fixation, parallel rotation, prior-handle overlap, expiry, restart, logout, third-session eviction. Failure behavior: revoke/clear and require OIDC.
- [ ] **Enforce private request boundary —** Input: session plus HTTP metadata. Operation: resolve subject before lookup, enforce Origin/fetch/CSRF/content type/CORS/proxy/size/CSP controls. Output: authenticated generated API call. Test evidence: cross-origin/XSS/enumeration/header-spoof suite. Failure behavior: safe 401/403 before command claim.
- [ ] **Implement lifecycle and emergency controls —** Input: logout, reauth, key rotation, device loss, compromise. Operation: revoke rows/generations/epoch, clear cookies, and preserve safe audit. Output: bounded invalidation. Test evidence: stolen current/previous cookie and emergency-revoke propagation. Failure behavior: product mutations/control enables unavailable.
- [ ] **Prove bootstrap and restore —** Input: clean VPS/database/key references. Operation: bootstrap exact subject, restore with sessions revoked, authenticate normally, and run authority tests. Output: signed recovery evidence. Test evidence: no bypass cookie or restored session. Failure behavior: system remains private/read-only/off.

## Test strategy

- **Protocol `test_oidc_callback_requires_exact_google_parameter_arm_state_nonce_pkce_issuer_set_audience_time_and_subject`:** official success/error fixtures require `iss`; both exact issuer spellings pass; extra/duplicate/cross-arm/unknown values fail before exchange/session.
- **Cookie `test_session_and_flow_cookie_attributes_match_backend02_byte_for_byte`.**
- **Session `test_rotation_idle_absolute_overlap_logout_concurrency_and_epoch_revocation`.**
- **CSRF `test_every_unsafe_operation_rejects_bad_origin_fetch_metadata_intent_or_content_type_before_dispatch`.**
- **Separation `test_operator_oidc_never_requests_or_accepts_gmail_scope_and_gmail_oauth_never_creates_session`.**
- **Enumeration `test_anonymous_wrong_subject_and_unknown_resource_are_not_distinguishable`.**
- **Recovery `test_restored_database_revokes_sessions_and_bootstrap_has_no_auth_bypass`.**

## Security, privacy, compliance, idempotency, observability, and cost

Audit only session/flow UUID, subject hash, action/outcome/reason enum, key generation, coarse anomaly class, request/correlation, and UTC; never handles/digests, claims, email, IP, user-agent string, code, state, nonce, PKCE, or tokens. Auth metrics have bounded action/outcome labels and no subject/session ID. OIDC start idempotency is flow-cookie/Origin bound; callback consumes once; logout/revoke replay safely. Session storage is `SAFETY_LONG` only as a minimized terminated record under SEC-06. Google identity calls are cost-free unless provider terms change; rate limiting prevents abuse.

## Failure, rollback, and operator recovery

Wrong subject, signature/JWK failure, replay, clock anomaly, session-store/key mismatch, CSRF bypass suspicion, impossible concurrent rotation, or enumeration regression revokes the affected generation; severe cases revoke the epoch and disable product mutations. Roll back API/frontend together to the last signed compatible release. Preserve safe auth audit and restricted incident evidence. Recovery always returns through verified Google OIDC; no SQL row edit, cookie injection, Gmail token, or email claim restores authority.

## Acceptance and retained evidence

- [ ] Four frozen auth operations, exact cookies/durations, subject allowlist, and frontend behavior match BACKEND-02/FRONTEND-09.
- [ ] Identity OAuth and Gmail OAuth share no cookie, state, token, callback authority, scope, or service owner.
- [ ] Session fixation/replay, CSRF/XSS/enumeration, concurrent sessions, logout/rotation/emergency revoke, bootstrap, and restore are tested.
- [ ] Product authority is server-side and no browser/provider token is stored or exposed.

Retain config hashes, OIDC discovery/JWK pinning evidence, protocol/security test results, cookie captures with values redacted, session lifecycle/audit counts, revoke/rotation drills, private-ingress/CSP scans, and clean bootstrap/restore reports.

## Dependencies and next deliverable

SEC-02 depends on BACKEND-02's exact HTTP contract and [SEC-03](03-secrets-and-oauth-token-security.md) keying. It unlocks authenticated M7 operation and the identity part of M8; it grants no Gmail credential, approval, final `SEND`, compliance, or control-enable authority.
