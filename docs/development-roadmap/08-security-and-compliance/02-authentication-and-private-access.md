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

Use the dedicated `security_runtime` namespace with exactly two operational tables: `security_runtime.oidc_flows` and `security_runtime.operator_sessions`. They are not M2 product data and do not change the frozen 46-product-table manifest. PostgreSQL is selected for the initial single-VPS deployment because API-safe transactions, restart survival, CAS, backup, and revocation already exist operationally; no Redis/Vault cluster is introduced. The API auth owner is the only application role with row access. Product workers, DBOS/Temporal roles, frontend, reporting, and agents receive no schema usage or table/function grant.

The following PostgreSQL DDL is normative and compiles after DB-01 creates `public.operators`. A migration runs it as the database owner; role creation is idempotent only to support clean disposable compile fixtures. Production migration identity and role membership are release-manifest inputs, never inferred.

```sql
DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'alon_ai_auth_owner') THEN
        CREATE ROLE alon_ai_auth_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'alon_ai_api_runtime') THEN
        CREATE ROLE alon_ai_api_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'alon_ai_retention_runtime') THEN
        CREATE ROLE alon_ai_retention_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;
    END IF;
END
$roles$;

CREATE SCHEMA security_runtime AUTHORIZATION alon_ai_auth_owner;
REVOKE ALL ON SCHEMA security_runtime FROM PUBLIC;

CREATE TABLE security_runtime.oidc_flows (
    flow_id uuid NOT NULL,
    flow_handle_digest char(64) NOT NULL,
    state_digest char(64) NOT NULL,
    nonce_digest char(64) NOT NULL,
    pkce_verifier_ciphertext bytea NOT NULL,
    flow_payload_ciphertext bytea NOT NULL,
    encryption_key_generation text NOT NULL,
    operator_origin_hash char(64) NOT NULL,
    callback_issuer text NOT NULL,
    client_id_hash char(64) NOT NULL,
    redirect_uri_hash char(64) NOT NULL,
    return_path text NOT NULL,
    idempotency_key_hash char(64) NOT NULL,
    request_schema_version text NOT NULL,
    request_hash char(64) NOT NULL,
    state text NOT NULL DEFAULT 'PENDING',
    claimed_by uuid NULL,
    claim_token_hash char(64) NULL,
    claimed_at timestamptz NULL,
    claim_lease_expires_at timestamptz NULL,
    result_schema_version text NULL,
    result_kind text NULL,
    result_hash char(64) NULL,
    result_http_status smallint NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    expires_at timestamptz NOT NULL,
    terminal_at timestamptz NULL,
    version bigint NOT NULL DEFAULT 1,
    CONSTRAINT pk_security_runtime_oidc_flows PRIMARY KEY (flow_id),
    CONSTRAINT uq_security_runtime_oidc_flow_handle UNIQUE (flow_handle_digest),
    CONSTRAINT uq_security_runtime_oidc_state UNIQUE (state_digest),
    CONSTRAINT uq_security_runtime_oidc_idempotency UNIQUE (operator_origin_hash, idempotency_key_hash),
    CONSTRAINT ck_security_runtime_oidc_hashes CHECK (flow_handle_digest ~ '^[0-9a-f]{64}$' AND state_digest ~ '^[0-9a-f]{64}$' AND nonce_digest ~ '^[0-9a-f]{64}$' AND operator_origin_hash ~ '^[0-9a-f]{64}$' AND client_id_hash ~ '^[0-9a-f]{64}$' AND redirect_uri_hash ~ '^[0-9a-f]{64}$' AND idempotency_key_hash ~ '^[0-9a-f]{64}$' AND request_hash ~ '^[0-9a-f]{64}$' AND (claim_token_hash IS NULL OR claim_token_hash ~ '^[0-9a-f]{64}$') AND (result_hash IS NULL OR result_hash ~ '^[0-9a-f]{64}$')),
    CONSTRAINT ck_security_runtime_oidc_ciphertext CHECK (octet_length(pkce_verifier_ciphertext) >= 32 AND octet_length(flow_payload_ciphertext) >= 32),
    CONSTRAINT ck_security_runtime_oidc_versions CHECK (version > 0 AND encryption_key_generation ~ '^[a-z0-9][a-z0-9._-]{0,63}$' AND request_schema_version ~ '^[a-z0-9][a-z0-9._-]{0,63}$' AND (result_schema_version IS NULL OR result_schema_version ~ '^[a-z0-9][a-z0-9._-]{0,63}$')),
    CONSTRAINT ck_security_runtime_oidc_binding CHECK (callback_issuer = 'https://accounts.google.com' AND return_path ~ '^/[A-Za-z0-9/_-]{0,255}$' AND return_path !~ '//'),
    CONSTRAINT ck_security_runtime_oidc_expiry CHECK (expires_at = created_at + interval '10 minutes'),
    CONSTRAINT ck_security_runtime_oidc_state CHECK (state IN ('PENDING','CLAIMED','CONSUMED','EXPIRED')),
    CONSTRAINT ck_security_runtime_oidc_result CHECK ((result_schema_version IS NULL AND result_kind IS NULL AND result_hash IS NULL AND result_http_status IS NULL) OR (result_schema_version IS NOT NULL AND result_kind IN ('SUCCEEDED','DENIED','INVALID') AND result_hash IS NOT NULL AND result_http_status BETWEEN 200 AND 599)),
    CONSTRAINT ck_security_runtime_oidc_lifecycle CHECK (
        (state = 'PENDING' AND claimed_by IS NULL AND claim_token_hash IS NULL AND claimed_at IS NULL AND claim_lease_expires_at IS NULL AND result_hash IS NULL AND terminal_at IS NULL) OR
        (state = 'CLAIMED' AND claimed_by IS NOT NULL AND claim_token_hash IS NOT NULL AND claimed_at IS NOT NULL AND claim_lease_expires_at > claimed_at AND claim_lease_expires_at <= expires_at AND result_hash IS NULL AND terminal_at IS NULL) OR
        (state = 'CONSUMED' AND claimed_by IS NOT NULL AND claim_token_hash IS NOT NULL AND claimed_at IS NOT NULL AND claim_lease_expires_at > claimed_at AND result_hash IS NOT NULL AND terminal_at IS NOT NULL AND terminal_at >= claimed_at) OR
        (state = 'EXPIRED' AND ((claimed_by IS NULL AND claim_token_hash IS NULL AND claimed_at IS NULL AND claim_lease_expires_at IS NULL) OR (claimed_by IS NOT NULL AND claim_token_hash IS NOT NULL AND claimed_at IS NOT NULL AND claim_lease_expires_at > claimed_at)) AND result_hash IS NULL AND terminal_at IS NOT NULL)
    )
);

CREATE INDEX ix_security_runtime_oidc_expiry ON security_runtime.oidc_flows (expires_at, flow_id) WHERE state IN ('PENDING','CLAIMED');
CREATE INDEX ix_security_runtime_oidc_claim_lease ON security_runtime.oidc_flows (claim_lease_expires_at, flow_id) WHERE state = 'CLAIMED';

CREATE TABLE security_runtime.operator_sessions (
    session_id uuid NOT NULL,
    operator_id uuid NOT NULL,
    authentication_epoch bigint NOT NULL,
    subject_hash char(64) NOT NULL,
    current_handle_digest char(64) NOT NULL,
    previous_handle_digest char(64) NULL,
    previous_handle_expires_at timestamptz NULL,
    lookup_key_generation text NOT NULL,
    issued_at timestamptz NOT NULL,
    reauthenticated_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    idle_expires_at timestamptz NOT NULL,
    absolute_expires_at timestamptz NOT NULL,
    rotate_after timestamptz NOT NULL,
    state text NOT NULL DEFAULT 'ACTIVE',
    end_reason text NULL,
    ended_at timestamptz NULL,
    created_ip_prefix_hash char(64) NOT NULL,
    user_agent_family text NOT NULL,
    version bigint NOT NULL DEFAULT 1,
    CONSTRAINT pk_security_runtime_operator_sessions PRIMARY KEY (session_id),
    CONSTRAINT fk_security_runtime_operator_sessions_operator FOREIGN KEY (operator_id) REFERENCES public.operators (operator_id) ON DELETE RESTRICT,
    CONSTRAINT uq_security_runtime_operator_session_current_handle UNIQUE (current_handle_digest),
    CONSTRAINT uq_security_runtime_operator_session_previous_handle UNIQUE (previous_handle_digest),
    CONSTRAINT ck_security_runtime_operator_session_hashes CHECK (subject_hash ~ '^[0-9a-f]{64}$' AND current_handle_digest ~ '^[0-9a-f]{64}$' AND (previous_handle_digest IS NULL OR previous_handle_digest ~ '^[0-9a-f]{64}$') AND created_ip_prefix_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_security_runtime_operator_session_versions CHECK (version > 0 AND authentication_epoch > 0 AND lookup_key_generation ~ '^[a-z0-9][a-z0-9._-]{0,63}$'),
    CONSTRAINT ck_security_runtime_operator_session_state CHECK (state IN ('ACTIVE','REVOKED','EXPIRED')),
    CONSTRAINT ck_security_runtime_operator_session_agent CHECK (user_agent_family IN ('CHROME','FIREFOX','SAFARI','EDGE','OTHER')),
    CONSTRAINT ck_security_runtime_operator_session_window CHECK (absolute_expires_at = issued_at + interval '8 hours' AND reauthenticated_at BETWEEN issued_at AND last_seen_at AND last_seen_at >= issued_at AND idle_expires_at > last_seen_at AND idle_expires_at <= absolute_expires_at AND rotate_after > issued_at AND rotate_after <= absolute_expires_at),
    CONSTRAINT ck_security_runtime_operator_session_previous CHECK ((previous_handle_digest IS NULL AND previous_handle_expires_at IS NULL) OR (previous_handle_digest IS NOT NULL AND previous_handle_expires_at > last_seen_at AND previous_handle_expires_at <= LEAST(absolute_expires_at, last_seen_at + interval '30 seconds'))),
    CONSTRAINT ck_security_runtime_operator_session_end CHECK ((state = 'ACTIVE' AND end_reason IS NULL AND ended_at IS NULL) OR (state IN ('REVOKED','EXPIRED') AND end_reason ~ '^[A-Z0-9][A-Z0-9_]{0,63}$' AND ended_at IS NOT NULL AND ended_at >= issued_at))
);

CREATE INDEX ix_security_runtime_operator_sessions_active ON security_runtime.operator_sessions (operator_id, issued_at, session_id) WHERE state = 'ACTIVE';
CREATE INDEX ix_security_runtime_operator_sessions_expiry ON security_runtime.operator_sessions (LEAST(idle_expires_at, absolute_expires_at), session_id) WHERE state = 'ACTIVE';

CREATE FUNCTION security_runtime.enforce_oidc_flow_lifecycle() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, security_runtime
AS $function$
BEGIN
    IF NEW.flow_id <> OLD.flow_id OR NEW.flow_handle_digest <> OLD.flow_handle_digest OR NEW.state_digest <> OLD.state_digest OR NEW.nonce_digest <> OLD.nonce_digest OR NEW.request_hash <> OLD.request_hash OR NEW.created_at <> OLD.created_at OR NEW.expires_at <> OLD.expires_at THEN
        RAISE EXCEPTION 'immutable OIDC flow identity changed' USING ERRCODE = '23514';
    END IF;
    IF NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'OIDC flow CAS version must increment by one' USING ERRCODE = '23514';
    END IF;
    IF NOT ((OLD.state = 'PENDING' AND NEW.state IN ('CLAIMED','EXPIRED')) OR (OLD.state = 'CLAIMED' AND NEW.state IN ('CONSUMED','EXPIRED'))) THEN
        RAISE EXCEPTION 'illegal OIDC flow transition' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;

CREATE TRIGGER trg_security_runtime_oidc_flow_lifecycle
BEFORE UPDATE ON security_runtime.oidc_flows
FOR EACH ROW EXECUTE FUNCTION security_runtime.enforce_oidc_flow_lifecycle();

CREATE FUNCTION security_runtime.enforce_operator_session_lifecycle() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, security_runtime
AS $function$
BEGIN
    IF NEW.session_id <> OLD.session_id OR NEW.operator_id <> OLD.operator_id OR NEW.authentication_epoch <> OLD.authentication_epoch OR NEW.subject_hash <> OLD.subject_hash OR NEW.issued_at <> OLD.issued_at OR NEW.absolute_expires_at <> OLD.absolute_expires_at THEN
        RAISE EXCEPTION 'immutable operator session identity changed' USING ERRCODE = '23514';
    END IF;
    IF NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'operator session CAS version must increment by one' USING ERRCODE = '23514';
    END IF;
    IF OLD.state IN ('REVOKED','EXPIRED') AND NEW.state <> OLD.state THEN
        RAISE EXCEPTION 'terminal operator session reopened' USING ERRCODE = '23514';
    END IF;
    IF OLD.state = 'ACTIVE' AND NEW.state NOT IN ('ACTIVE','REVOKED','EXPIRED') THEN
        RAISE EXCEPTION 'illegal operator session transition' USING ERRCODE = '23514';
    END IF;
    IF NEW.current_handle_digest <> OLD.current_handle_digest AND (OLD.state <> 'ACTIVE' OR NEW.state <> 'ACTIVE' OR NEW.previous_handle_digest IS DISTINCT FROM OLD.current_handle_digest OR NEW.previous_handle_expires_at IS NULL OR NEW.previous_handle_expires_at <= statement_timestamp() OR NEW.previous_handle_expires_at > LEAST(NEW.absolute_expires_at, statement_timestamp() + interval '30 seconds')) THEN
        RAISE EXCEPTION 'invalid operator session handle rotation' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;

CREATE FUNCTION security_runtime.enforce_operator_session_scope() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    active_others integer;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.operator_id::text, 20260829));
    IF EXISTS (
        SELECT 1
        FROM security_runtime.operator_sessions AS existing
        WHERE existing.session_id <> NEW.session_id
          AND (existing.current_handle_digest IN (NEW.current_handle_digest, NEW.previous_handle_digest)
               OR existing.previous_handle_digest IN (NEW.current_handle_digest, NEW.previous_handle_digest))
    ) THEN
        RAISE EXCEPTION 'operator session handle digest collision' USING ERRCODE = '23505';
    END IF;
    IF NEW.state = 'ACTIVE' THEN
        SELECT count(*) INTO active_others
        FROM security_runtime.operator_sessions AS existing
        WHERE existing.operator_id = NEW.operator_id
          AND existing.session_id <> NEW.session_id
          AND existing.state = 'ACTIVE';
        IF active_others >= 2 THEN
            RAISE EXCEPTION 'operator active session cap exceeded' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END
$function$;

CREATE TRIGGER trg_10_security_runtime_operator_session_lifecycle
BEFORE UPDATE ON security_runtime.operator_sessions
FOR EACH ROW EXECUTE FUNCTION security_runtime.enforce_operator_session_lifecycle();

CREATE TRIGGER trg_20_security_runtime_operator_session_scope
BEFORE INSERT OR UPDATE ON security_runtime.operator_sessions
FOR EACH ROW EXECUTE FUNCTION security_runtime.enforce_operator_session_scope();

CREATE FUNCTION security_runtime.prune_expired(p_oidc_before timestamptz, p_session_before timestamptz)
RETURNS TABLE (deleted_oidc_flows bigint, deleted_operator_sessions bigint)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
BEGIN
    IF p_oidc_before > statement_timestamp() - interval '24 hours' OR p_session_before > statement_timestamp() - interval '30 days' THEN
        RAISE EXCEPTION 'security runtime retention floor violated' USING ERRCODE = '22023';
    END IF;
    RETURN QUERY
    WITH deleted_flows AS (
        DELETE FROM security_runtime.oidc_flows
        WHERE state IN ('CONSUMED','EXPIRED') AND terminal_at <= p_oidc_before
        RETURNING 1
    ), deleted_sessions AS (
        DELETE FROM security_runtime.operator_sessions
        WHERE state IN ('REVOKED','EXPIRED') AND ended_at <= p_session_before
        RETURNING 1
    )
    SELECT (SELECT count(*)::bigint FROM deleted_flows), (SELECT count(*)::bigint FROM deleted_sessions);
END
$function$;

ALTER TABLE security_runtime.oidc_flows OWNER TO alon_ai_auth_owner;
ALTER TABLE security_runtime.operator_sessions OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.enforce_oidc_flow_lifecycle() OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.enforce_operator_session_lifecycle() OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.enforce_operator_session_scope() OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.prune_expired(timestamptz, timestamptz) OWNER TO alon_ai_auth_owner;

REVOKE ALL ON ALL TABLES IN SCHEMA security_runtime FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA security_runtime FROM PUBLIC;
GRANT USAGE ON SCHEMA security_runtime TO alon_ai_api_runtime, alon_ai_retention_runtime;
GRANT SELECT, INSERT, UPDATE ON security_runtime.oidc_flows, security_runtime.operator_sessions TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.prune_expired(timestamptz, timestamptz) TO alon_ai_retention_runtime;
```

Application writes use `UPDATE ... WHERE primary_key=? AND version=?` and require exactly one row; stale CAS affects zero rows. Claim uses only `PENDING -> CLAIMED`; a second claimant, lease-expired claimant, or callback replay cannot exchange and closes the flow as `EXPIRED`. Session creation takes the per-operator advisory lock, revokes the oldest ACTIVE session through an ordinary versioned update when two exist, then inserts; the trigger independently rejects a third. Rotation is one CAS winner, makes the old current handle the sole previous digest for at most 30 seconds, and cannot rotate from the previous handle. Cross-column digest collision, terminal reopening, bulk update without version increment, and DELETE through the API role fail.

`security_runtime.prune_expired` is the retention role's only capability and copies SEC-06 `retention.policy.v1` row `AUTH_RUNTIME_DETAIL`: terminal flow detail is removed within 24 hours and every terminated session-detail row no later than 30 days after termination, with no legal/incident extension. A hold must extract separately minimized authentication audit under `SAFETY_LONG`; that audit contains only allowed IDs/hashes/enums and is not an operational session row. Encrypted pgBackRest backups cover this schema under canonical row `OPERATIONAL_BACKUP_CHAINS`; no table is excluded and no personal-data recovery point exceeds 35 days. On restore, before API readiness or role login, the release-owned repair runs the following exact transaction and verifies both update counts plus key-generation availability:

```sql
BEGIN;
UPDATE security_runtime.oidc_flows
SET state = 'EXPIRED', terminal_at = statement_timestamp(), version = version + 1
WHERE state IN ('PENDING','CLAIMED');
UPDATE security_runtime.operator_sessions
SET state = 'REVOKED', end_reason = 'DATABASE_RESTORED', ended_at = statement_timestamp(), version = version + 1
WHERE state = 'ACTIVE';
COMMIT;
```

The release introspects `pg_class`/`pg_namespace` and requires the security-runtime ordinary-table set to equal exactly `{oidc_flows,operator_sessions}` and the product-table set to remain exactly the DB-06 46 names; neither set may absorb the other.

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

- [ ] **Migrate and introspect the exact operational schema —** Input: DB-01 operators and the normative DDL. Operation: compile on a fresh supported PostgreSQL cluster, introspect tables/columns/constraints/indexes/triggers/owners/ACLs, then execute the restore and retention transactions. Output: exactly `security_runtime.{oidc_flows,operator_sessions}` beside—not inside—the 46-table product set. Test evidence: catalog equality, role-denial, dump/restore, expiry/prune boundaries, and worker/product-role no-access fixtures. Failure behavior: authentication readiness false and release blocked.
- [ ] **Implement strict OIDC flow state —** Input: exact config, return path, Origin, anonymous key. Operation: persist digests/encrypted PKCE with 10-minute one-time claim/consume CAS and verify the complete callback protocol. Output: configured-subject authentication only. Test evidence: exact success `{code,state,iss,scope?}` and error `{error,state,iss,error_description?}` arms; callback `iss=https://accounts.google.com` accepts while callback legacy/bogus/missing/duplicate issuer rejects; verified ID-token issuer accepts each of the separate two exact values and rejects every other value; state/nonce/PKCE/audience/subject/error/replay plus two-claimer/expired-lease/stale-version matrix. Failure behavior: fixed failure redirect, cleared flow cookie, no session.
- [ ] **Implement server-side sessions —** Input: verified subject. Operation: issue/digest/store/rotate opaque handle with frozen cookie, idle/absolute, overlap, optimistic concurrency, and two-session cap. Output: active operator context. Test evidence: fixation, parallel rotation, prior-handle overlap, expiry, restart, logout, third-session eviction. Failure behavior: revoke/clear and require OIDC.
- [ ] **Enforce private request boundary —** Input: session plus HTTP metadata. Operation: resolve subject before lookup, enforce Origin/fetch/CSRF/content type/CORS/proxy/size/CSP controls. Output: authenticated generated API call. Test evidence: cross-origin/XSS/enumeration/header-spoof suite. Failure behavior: safe 401/403 before command claim.
- [ ] **Implement lifecycle and emergency controls —** Input: logout, reauth, key rotation, device loss, compromise. Operation: revoke rows/generations/epoch, clear cookies, and preserve safe audit. Output: bounded invalidation. Test evidence: stolen current/previous cookie and emergency-revoke propagation. Failure behavior: product mutations/control enables unavailable.
- [ ] **Prove bootstrap and restore —** Input: clean VPS/database/key references. Operation: bootstrap exact subject, restore with sessions revoked, authenticate normally, and run authority tests. Output: signed recovery evidence. Test evidence: no bypass cookie or restored session. Failure behavior: system remains private/read-only/off.

## Test strategy

- **Protocol `test_oidc_callback_and_id_token_issuers_are_validated_separately`:** official success/error fixtures require callback `iss` byte-equal to `https://accounts.google.com`; legacy callback `accounts.google.com` and every other/missing/duplicate issuer fail before exchange; only the later verified ID-token fixture accepts both exact issuer spellings; extra/duplicate/cross-arm/unknown values fail before exchange/session.
- **Cookie `test_session_and_flow_cookie_attributes_match_backend02_byte_for_byte`.**
- **Session `test_rotation_idle_absolute_overlap_logout_concurrency_and_epoch_revocation`.**
- **DDL `test_security_runtime_compiles_and_contains_exactly_two_owned_tables_with_closed_acls`.**
- **Concurrency `test_oidc_claim_and_session_rotation_each_have_one_cas_winner_and_stale_version_zero_rows`.**
- **Invariant `test_cross_current_previous_handle_collision_overlap_over_30_seconds_and_third_active_session_fail`.**
- **Roles `test_api_cannot_delete_or_prune_and_worker_product_public_roles_have_no_security_runtime_access`.**
- **Retention/restore `test_prune_floors_and_restore_expire_flows_revoke_sessions_before_readiness`.**
- **CSRF `test_every_unsafe_operation_rejects_bad_origin_fetch_metadata_intent_or_content_type_before_dispatch`.**
- **Separation `test_operator_oidc_never_requests_or_accepts_gmail_scope_and_gmail_oauth_never_creates_session`.**
- **Enumeration `test_anonymous_wrong_subject_and_unknown_resource_are_not_distinguishable`.**
- **Recovery `test_restored_database_revokes_sessions_and_bootstrap_has_no_auth_bypass`.**

## Security, privacy, compliance, idempotency, observability, and cost

Audit only session/flow UUID, subject hash, action/outcome/reason enum, key generation, coarse anomaly class, request/correlation, and UTC; never handles/digests, claims, email, IP, user-agent string, code, state, nonce, PKCE, or tokens. Auth metrics have bounded action/outcome labels and no subject/session ID. OIDC start idempotency is flow-cookie/Origin bound; callback consumes once; logout/revoke replay safely. Operational session rows are not `SAFETY_LONG`: their detail is purged no later than 30 days after termination, while only a separately materialized minimized authentication audit may use that class under SEC-06. Google identity calls are cost-free unless provider terms change; rate limiting prevents abuse.

## Failure, rollback, and operator recovery

Wrong subject, signature/JWK failure, replay, clock anomaly, session-store/key mismatch, CSRF bypass suspicion, impossible concurrent rotation, or enumeration regression revokes the affected generation; severe cases revoke the epoch and disable product mutations. Roll back API/frontend together to the last signed compatible release. Preserve safe auth audit and restricted incident evidence. Recovery always returns through verified Google OIDC; no SQL row edit, cookie injection, Gmail token, or email claim restores authority.

## Acceptance and retained evidence

- [ ] Four frozen auth operations, exact cookies/durations, subject allowlist, and frontend behavior match BACKEND-02/FRONTEND-09.
- [ ] Identity OAuth and Gmail OAuth share no cookie, state, token, callback authority, scope, or service owner.
- [ ] Session fixation/replay, CSRF/XSS/enumeration, concurrent sessions, logout/rotation/emergency revoke, bootstrap, and restore are tested.
- [ ] Product authority is server-side and no browser/provider token is stored or exposed.
- [ ] Fresh PostgreSQL compile/catalog/ACL/concurrency/retention/restore evidence proves exactly two operational tables and preserves the separate 46-product-table count.

Retain config hashes, OIDC discovery/JWK pinning evidence, protocol/security test results, cookie captures with values redacted, session lifecycle/audit counts, revoke/rotation drills, private-ingress/CSP scans, and clean bootstrap/restore reports.

## Dependencies and next deliverable

SEC-02 depends on BACKEND-02's exact HTTP contract and [SEC-03](03-secrets-and-oauth-token-security.md) keying. It unlocks authenticated M7 operation and the identity part of M8; it grants no Gmail credential, approval, final `SEND`, compliance, or control-enable authority.
