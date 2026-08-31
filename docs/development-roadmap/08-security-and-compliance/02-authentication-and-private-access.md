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
    CONSTRAINT ck_security_runtime_operator_session_previous CHECK ((previous_handle_digest IS NULL AND previous_handle_expires_at IS NULL) OR (previous_handle_digest IS NOT NULL AND previous_handle_expires_at > issued_at AND previous_handle_expires_at <= LEAST(absolute_expires_at, last_seen_at + interval '30 seconds'))),
    CONSTRAINT ck_security_runtime_operator_session_end CHECK ((state = 'ACTIVE' AND end_reason IS NULL AND ended_at IS NULL) OR (state IN ('REVOKED','EXPIRED') AND end_reason ~ '^[A-Z0-9][A-Z0-9_]{0,63}$' AND ended_at IS NOT NULL AND ended_at >= issued_at))
);

CREATE INDEX ix_security_runtime_operator_sessions_active ON security_runtime.operator_sessions (operator_id, issued_at, session_id) WHERE state = 'ACTIVE';
CREATE INDEX ix_security_runtime_operator_sessions_expiry ON security_runtime.operator_sessions (LEAST(idle_expires_at, absolute_expires_at), session_id) WHERE state = 'ACTIVE';

CREATE FUNCTION security_runtime.enforce_oidc_flow_initial() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, security_runtime
AS $function$
BEGIN
    IF NEW.state <> 'PENDING' OR NEW.version <> 1 OR
       (NEW.claimed_by, NEW.claim_token_hash, NEW.claimed_at, NEW.claim_lease_expires_at,
        NEW.result_schema_version, NEW.result_kind, NEW.result_hash,
        NEW.result_http_status, NEW.terminal_at) IS DISTINCT FROM
       (NULL::uuid, NULL::char(64), NULL::timestamptz, NULL::timestamptz,
        NULL::text, NULL::text, NULL::char(64), NULL::smallint, NULL::timestamptz) THEN
        RAISE EXCEPTION 'OIDC flow must be inserted in exact PENDING version 1 state' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;

CREATE TRIGGER trg_security_runtime_oidc_flow_initial
BEFORE INSERT ON security_runtime.oidc_flows
FOR EACH ROW EXECUTE FUNCTION security_runtime.enforce_oidc_flow_initial();

CREATE FUNCTION security_runtime.enforce_oidc_flow_lifecycle() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, security_runtime
AS $function$
BEGIN
    IF (NEW.flow_id, NEW.flow_handle_digest, NEW.state_digest, NEW.nonce_digest,
        NEW.pkce_verifier_ciphertext, NEW.flow_payload_ciphertext,
        NEW.encryption_key_generation, NEW.operator_origin_hash,
        NEW.callback_issuer, NEW.client_id_hash, NEW.redirect_uri_hash,
        NEW.return_path, NEW.idempotency_key_hash, NEW.request_schema_version,
        NEW.request_hash, NEW.created_at, NEW.expires_at) IS DISTINCT FROM
       (OLD.flow_id, OLD.flow_handle_digest, OLD.state_digest, OLD.nonce_digest,
        OLD.pkce_verifier_ciphertext, OLD.flow_payload_ciphertext,
        OLD.encryption_key_generation, OLD.operator_origin_hash,
        OLD.callback_issuer, OLD.client_id_hash, OLD.redirect_uri_hash,
        OLD.return_path, OLD.idempotency_key_hash, OLD.request_schema_version,
        OLD.request_hash, OLD.created_at, OLD.expires_at) THEN
        RAISE EXCEPTION 'immutable complete OIDC request binding changed' USING ERRCODE = '23514';
    END IF;
    IF NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'OIDC flow CAS version must increment by one' USING ERRCODE = '23514';
    END IF;
    IF OLD.state = 'PENDING' AND NEW.state = 'CLAIMED' THEN
        IF to_jsonb(NEW) - ARRAY['state','claimed_by','claim_token_hash','claimed_at','claim_lease_expires_at','version'] <> to_jsonb(OLD) - ARRAY['state','claimed_by','claim_token_hash','claimed_at','claim_lease_expires_at','version'] THEN
            RAISE EXCEPTION 'PENDING to CLAIMED changed a non-claim column' USING ERRCODE = '23514';
        END IF;
    ELSIF OLD.state = 'PENDING' AND NEW.state = 'EXPIRED' THEN
        IF to_jsonb(NEW) - ARRAY['state','terminal_at','version'] <> to_jsonb(OLD) - ARRAY['state','terminal_at','version'] THEN
            RAISE EXCEPTION 'PENDING to EXPIRED changed a non-expiry column' USING ERRCODE = '23514';
        END IF;
    ELSIF OLD.state = 'CLAIMED' AND NEW.state = 'CONSUMED' THEN
        IF to_jsonb(NEW) - ARRAY['state','result_schema_version','result_kind','result_hash','result_http_status','terminal_at','version'] <> to_jsonb(OLD) - ARRAY['state','result_schema_version','result_kind','result_hash','result_http_status','terminal_at','version'] THEN
            RAISE EXCEPTION 'CLAIMED to CONSUMED changed a non-result column' USING ERRCODE = '23514';
        END IF;
    ELSIF OLD.state = 'CLAIMED' AND NEW.state = 'EXPIRED' THEN
        IF to_jsonb(NEW) - ARRAY['state','terminal_at','version'] <> to_jsonb(OLD) - ARRAY['state','terminal_at','version'] THEN
            RAISE EXCEPTION 'CLAIMED to EXPIRED changed a non-expiry column' USING ERRCODE = '23514';
        END IF;
    ELSE
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
DECLARE
    transition_at timestamptz := statement_timestamp();
BEGIN
    IF (NEW.session_id, NEW.operator_id, NEW.authentication_epoch, NEW.subject_hash,
        NEW.lookup_key_generation, NEW.issued_at, NEW.reauthenticated_at,
        NEW.absolute_expires_at, NEW.created_ip_prefix_hash, NEW.user_agent_family) IS DISTINCT FROM
       (OLD.session_id, OLD.operator_id, OLD.authentication_epoch, OLD.subject_hash,
        OLD.lookup_key_generation, OLD.issued_at, OLD.reauthenticated_at,
        OLD.absolute_expires_at, OLD.created_ip_prefix_hash, OLD.user_agent_family) THEN
        RAISE EXCEPTION 'immutable complete operator session binding changed' USING ERRCODE = '23514';
    END IF;
    IF NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'operator session CAS version must increment by one' USING ERRCODE = '23514';
    END IF;
    IF OLD.state IN ('REVOKED','EXPIRED') THEN
        RAISE EXCEPTION 'terminal operator session is immutable' USING ERRCODE = '23514';
    ELSIF OLD.state = 'ACTIVE' AND NEW.state = 'ACTIVE' AND NEW.current_handle_digest IS DISTINCT FROM OLD.current_handle_digest THEN
        IF OLD.previous_handle_digest IS NOT NULL AND OLD.previous_handle_expires_at > transition_at THEN
            RAISE EXCEPTION 'operator session cannot rotate while a previous-handle overlap is active' USING ERRCODE = '23514';
        END IF;
        IF NEW.previous_handle_digest IS DISTINCT FROM OLD.current_handle_digest OR
           NEW.previous_handle_expires_at IS DISTINCT FROM LEAST(NEW.absolute_expires_at, transition_at + interval '30 seconds') OR
           NEW.last_seen_at IS DISTINCT FROM transition_at OR
           NEW.idle_expires_at IS DISTINCT FROM LEAST(NEW.absolute_expires_at, transition_at + interval '30 minutes') OR
           NEW.rotate_after IS DISTINCT FROM LEAST(NEW.absolute_expires_at, transition_at + interval '15 minutes') OR
           to_jsonb(NEW) - ARRAY['current_handle_digest','previous_handle_digest','previous_handle_expires_at','last_seen_at','idle_expires_at','rotate_after','version'] <>
           to_jsonb(OLD) - ARRAY['current_handle_digest','previous_handle_digest','previous_handle_expires_at','last_seen_at','idle_expires_at','rotate_after','version'] THEN
            RAISE EXCEPTION 'invalid operator session handle rotation' USING ERRCODE = '23514';
        END IF;
    ELSIF OLD.state = 'ACTIVE' AND NEW.state = 'ACTIVE' THEN
        IF (NEW.previous_handle_digest, NEW.previous_handle_expires_at, NEW.rotate_after) IS DISTINCT FROM
           (OLD.previous_handle_digest, OLD.previous_handle_expires_at, OLD.rotate_after) OR
           NEW.last_seen_at < OLD.last_seen_at OR
           NEW.idle_expires_at IS DISTINCT FROM LEAST(NEW.absolute_expires_at, NEW.last_seen_at + interval '30 minutes') OR
           to_jsonb(NEW) - ARRAY['last_seen_at','idle_expires_at','version'] <>
           to_jsonb(OLD) - ARRAY['last_seen_at','idle_expires_at','version'] THEN
            RAISE EXCEPTION 'ACTIVE session touch changed non-touch authority' USING ERRCODE = '23514';
        END IF;
    ELSIF OLD.state = 'ACTIVE' AND NEW.state IN ('REVOKED','EXPIRED') THEN
        IF to_jsonb(NEW) - ARRAY['state','end_reason','ended_at','version'] <>
           to_jsonb(OLD) - ARRAY['state','end_reason','ended_at','version'] THEN
            RAISE EXCEPTION 'operator session termination changed non-terminal authority' USING ERRCODE = '23514';
        END IF;
    ELSE
        RAISE EXCEPTION 'illegal operator session transition' USING ERRCODE = '23514';
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
    IF TG_OP = 'INSERT' AND (
        NEW.state <> 'ACTIVE' OR NEW.version <> 1 OR
        NEW.previous_handle_digest IS NOT NULL OR NEW.previous_handle_expires_at IS NOT NULL OR
        NEW.end_reason IS NOT NULL OR NEW.ended_at IS NOT NULL OR
        NEW.reauthenticated_at IS DISTINCT FROM NEW.issued_at OR
        NEW.last_seen_at IS DISTINCT FROM NEW.issued_at OR
        NEW.idle_expires_at IS DISTINCT FROM LEAST(NEW.absolute_expires_at, NEW.issued_at + interval '30 minutes') OR
        NEW.rotate_after IS DISTINCT FROM LEAST(NEW.absolute_expires_at, NEW.issued_at + interval '15 minutes')
    ) THEN
        RAISE EXCEPTION 'operator session must be inserted in exact ACTIVE version 1 state' USING ERRCODE = '23514';
    END IF;
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

CREATE FUNCTION security_runtime.create_oidc_flow(
    p_flow_id uuid, p_flow_handle_digest char(64), p_state_digest char(64),
    p_nonce_digest char(64), p_pkce_verifier_ciphertext bytea,
    p_flow_payload_ciphertext bytea, p_encryption_key_generation text,
    p_operator_origin_hash char(64), p_callback_issuer text,
    p_client_id_hash char(64), p_redirect_uri_hash char(64), p_return_path text,
    p_idempotency_key_hash char(64), p_request_schema_version text,
    p_request_hash char(64)
) RETURNS security_runtime.oidc_flows
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    existing security_runtime.oidc_flows%ROWTYPE;
    match_count integer;
BEGIN
    INSERT INTO security_runtime.oidc_flows (
        flow_id, flow_handle_digest, state_digest, nonce_digest,
        pkce_verifier_ciphertext, flow_payload_ciphertext,
        encryption_key_generation, operator_origin_hash, callback_issuer,
        client_id_hash, redirect_uri_hash, return_path, idempotency_key_hash,
        request_schema_version, request_hash, expires_at
    ) VALUES (
        p_flow_id, p_flow_handle_digest, p_state_digest, p_nonce_digest,
        p_pkce_verifier_ciphertext, p_flow_payload_ciphertext,
        p_encryption_key_generation, p_operator_origin_hash, p_callback_issuer,
        p_client_id_hash, p_redirect_uri_hash, p_return_path,
        p_idempotency_key_hash, p_request_schema_version, p_request_hash,
        statement_timestamp() + interval '10 minutes'
    ) ON CONFLICT DO NOTHING;

    SELECT count(*) INTO match_count
    FROM security_runtime.oidc_flows
    WHERE flow_id = p_flow_id OR
          (operator_origin_hash, idempotency_key_hash) =
          (p_operator_origin_hash, p_idempotency_key_hash);
    IF match_count <> 1 THEN
        RAISE EXCEPTION 'OIDC flow idempotency identities do not resolve to one row' USING ERRCODE = '23505';
    END IF;
    SELECT * INTO existing
    FROM security_runtime.oidc_flows
    WHERE flow_id = p_flow_id OR
          (operator_origin_hash, idempotency_key_hash) =
          (p_operator_origin_hash, p_idempotency_key_hash)
    FOR UPDATE;
    IF
       (existing.flow_id, existing.flow_handle_digest, existing.state_digest,
        existing.nonce_digest, existing.pkce_verifier_ciphertext,
        existing.flow_payload_ciphertext, existing.encryption_key_generation,
        existing.operator_origin_hash, existing.callback_issuer,
        existing.client_id_hash, existing.redirect_uri_hash, existing.return_path,
        existing.idempotency_key_hash, existing.request_schema_version,
        existing.request_hash) IS DISTINCT FROM
       (p_flow_id, p_flow_handle_digest, p_state_digest, p_nonce_digest,
        p_pkce_verifier_ciphertext, p_flow_payload_ciphertext,
        p_encryption_key_generation, p_operator_origin_hash, p_callback_issuer,
        p_client_id_hash, p_redirect_uri_hash, p_return_path,
        p_idempotency_key_hash, p_request_schema_version, p_request_hash) THEN
        RAISE EXCEPTION 'OIDC flow idempotency or binding conflict' USING ERRCODE = '23505';
    END IF;
    RETURN existing;
END
$function$;

CREATE FUNCTION security_runtime.claim_oidc_flow(
    p_flow_id uuid, p_expected_version bigint, p_claimed_by uuid,
    p_claim_token_hash char(64)
) RETURNS security_runtime.oidc_flows
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    claimed security_runtime.oidc_flows%ROWTYPE;
BEGIN
    UPDATE security_runtime.oidc_flows
    SET state = 'CLAIMED', claimed_by = p_claimed_by,
        claim_token_hash = p_claim_token_hash, claimed_at = statement_timestamp(),
        claim_lease_expires_at = LEAST(expires_at, statement_timestamp() + interval '2 minutes'),
        version = version + 1
    WHERE flow_id = p_flow_id AND version = p_expected_version
      AND state = 'PENDING' AND expires_at > statement_timestamp()
    RETURNING * INTO claimed;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'OIDC claim lost CAS, state, or expiry race' USING ERRCODE = '40001';
    END IF;
    RETURN claimed;
END
$function$;

CREATE FUNCTION security_runtime.consume_oidc_flow(
    p_flow_id uuid, p_expected_version bigint, p_claim_token_hash char(64),
    p_result_schema_version text, p_result_kind text,
    p_result_hash char(64), p_result_http_status smallint
) RETURNS security_runtime.oidc_flows
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    consumed security_runtime.oidc_flows%ROWTYPE;
BEGIN
    UPDATE security_runtime.oidc_flows
    SET state = 'CONSUMED', result_schema_version = p_result_schema_version,
        result_kind = p_result_kind, result_hash = p_result_hash,
        result_http_status = p_result_http_status,
        terminal_at = statement_timestamp(), version = version + 1
    WHERE flow_id = p_flow_id AND version = p_expected_version
      AND state = 'CLAIMED' AND claim_token_hash = p_claim_token_hash
      AND claim_lease_expires_at > statement_timestamp()
    RETURNING * INTO consumed;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'OIDC consume lost CAS, claim, or lease race' USING ERRCODE = '40001';
    END IF;
    RETURN consumed;
END
$function$;

CREATE FUNCTION security_runtime.expire_oidc_flow(
    p_flow_id uuid, p_expected_version bigint
) RETURNS security_runtime.oidc_flows
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    expired security_runtime.oidc_flows%ROWTYPE;
BEGIN
    UPDATE security_runtime.oidc_flows
    SET state = 'EXPIRED', terminal_at = statement_timestamp(), version = version + 1
    WHERE flow_id = p_flow_id AND version = p_expected_version AND
          ((state = 'PENDING' AND expires_at <= statement_timestamp()) OR
           (state = 'CLAIMED' AND LEAST(expires_at, claim_lease_expires_at) <= statement_timestamp()))
    RETURNING * INTO expired;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'OIDC expiry lost CAS or row is not expired' USING ERRCODE = '40001';
    END IF;
    RETURN expired;
END
$function$;

CREATE FUNCTION security_runtime.create_operator_session(
    p_session_id uuid, p_operator_id uuid, p_authentication_epoch bigint,
    p_subject_hash char(64), p_current_handle_digest char(64),
    p_lookup_key_generation text, p_created_ip_prefix_hash char(64),
    p_user_agent_family text
) RETURNS security_runtime.operator_sessions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    existing security_runtime.operator_sessions%ROWTYPE;
    created security_runtime.operator_sessions%ROWTYPE;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(p_operator_id::text, 20260829));
    SELECT * INTO existing FROM security_runtime.operator_sessions
    WHERE session_id = p_session_id FOR UPDATE;
    IF FOUND THEN
        IF (existing.operator_id, existing.authentication_epoch,
            existing.subject_hash, existing.lookup_key_generation,
            existing.created_ip_prefix_hash,
            existing.user_agent_family) IS DISTINCT FROM
           (p_operator_id, p_authentication_epoch, p_subject_hash,
            p_lookup_key_generation, p_created_ip_prefix_hash,
            p_user_agent_family) OR
           (p_current_handle_digest IS DISTINCT FROM existing.current_handle_digest AND
            p_current_handle_digest IS DISTINCT FROM existing.previous_handle_digest) THEN
            RAISE EXCEPTION 'operator session idempotency or binding conflict' USING ERRCODE = '23505';
        END IF;
        RETURN existing;
    END IF;

    WITH active AS MATERIALIZED (
        SELECT session_id, issued_at
        FROM security_runtime.operator_sessions
        WHERE operator_id = p_operator_id AND state = 'ACTIVE'
        FOR UPDATE
    ), oldest AS (
        SELECT session_id FROM active
        WHERE (SELECT count(*) FROM active) >= 2
        ORDER BY issued_at, session_id
        LIMIT 1
    )
    UPDATE security_runtime.operator_sessions AS session
    SET state = 'REVOKED', end_reason = 'SESSION_CAP_EVICTION',
        ended_at = statement_timestamp(), version = session.version + 1
    FROM oldest
    WHERE session.session_id = oldest.session_id;

    INSERT INTO security_runtime.operator_sessions (
        session_id, operator_id, authentication_epoch, subject_hash,
        current_handle_digest, lookup_key_generation, issued_at,
        reauthenticated_at, last_seen_at, idle_expires_at,
        absolute_expires_at, rotate_after, created_ip_prefix_hash,
        user_agent_family
    ) VALUES (
        p_session_id, p_operator_id, p_authentication_epoch, p_subject_hash,
        p_current_handle_digest, p_lookup_key_generation, statement_timestamp(),
        statement_timestamp(), statement_timestamp(), statement_timestamp() + interval '30 minutes',
        statement_timestamp() + interval '8 hours', statement_timestamp() + interval '15 minutes',
        p_created_ip_prefix_hash, p_user_agent_family
    ) RETURNING * INTO created;
    RETURN created;
END
$function$;

CREATE FUNCTION security_runtime.touch_operator_session(
    p_session_id uuid, p_expected_version bigint, p_presented_handle_digest char(64)
) RETURNS security_runtime.operator_sessions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    touched security_runtime.operator_sessions%ROWTYPE;
BEGIN
    UPDATE security_runtime.operator_sessions
    SET last_seen_at = statement_timestamp(),
        idle_expires_at = LEAST(absolute_expires_at, statement_timestamp() + interval '30 minutes'),
        version = version + 1
    WHERE session_id = p_session_id AND version = p_expected_version
      AND state = 'ACTIVE' AND idle_expires_at > statement_timestamp()
      AND absolute_expires_at > statement_timestamp()
      AND (current_handle_digest = p_presented_handle_digest OR
           (previous_handle_digest = p_presented_handle_digest AND
            previous_handle_expires_at > statement_timestamp()))
    RETURNING * INTO touched;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'operator session touch lost CAS or handle/expiry check' USING ERRCODE = '40001';
    END IF;
    RETURN touched;
END
$function$;

CREATE FUNCTION security_runtime.rotate_operator_session(
    p_session_id uuid, p_expected_version bigint,
    p_expected_current_handle_digest char(64), p_new_current_handle_digest char(64)
) RETURNS security_runtime.operator_sessions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    rotated security_runtime.operator_sessions%ROWTYPE;
BEGIN
    UPDATE security_runtime.operator_sessions
    SET current_handle_digest = p_new_current_handle_digest,
        previous_handle_digest = current_handle_digest,
        previous_handle_expires_at = LEAST(absolute_expires_at, statement_timestamp() + interval '30 seconds'),
        last_seen_at = statement_timestamp(),
        idle_expires_at = LEAST(absolute_expires_at, statement_timestamp() + interval '30 minutes'),
        rotate_after = LEAST(absolute_expires_at, statement_timestamp() + interval '15 minutes'),
        version = version + 1
    WHERE session_id = p_session_id AND version = p_expected_version
      AND state = 'ACTIVE' AND current_handle_digest = p_expected_current_handle_digest
      AND p_new_current_handle_digest <> p_expected_current_handle_digest
      AND rotate_after <= statement_timestamp()
      AND idle_expires_at > statement_timestamp()
      AND absolute_expires_at > statement_timestamp() + interval '30 seconds'
      AND (previous_handle_digest IS NULL OR previous_handle_expires_at <= statement_timestamp())
    RETURNING * INTO rotated;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'operator session rotation lost CAS or current-handle/window check' USING ERRCODE = '40001';
    END IF;
    RETURN rotated;
END
$function$;

CREATE FUNCTION security_runtime.end_operator_session(
    p_session_id uuid, p_expected_version bigint, p_terminal_state text,
    p_end_reason text
) RETURNS security_runtime.operator_sessions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, security_runtime
AS $function$
DECLARE
    ended security_runtime.operator_sessions%ROWTYPE;
BEGIN
    IF p_terminal_state NOT IN ('REVOKED','EXPIRED') THEN
        RAISE EXCEPTION 'operator session terminal state is invalid' USING ERRCODE = '22023';
    END IF;
    UPDATE security_runtime.operator_sessions
    SET state = p_terminal_state, end_reason = p_end_reason,
        ended_at = statement_timestamp(), version = version + 1
    WHERE session_id = p_session_id AND version = p_expected_version AND state = 'ACTIVE'
    RETURNING * INTO ended;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'operator session termination lost CAS or state race' USING ERRCODE = '40001';
    END IF;
    RETURN ended;
END
$function$;

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
ALTER FUNCTION security_runtime.enforce_oidc_flow_initial() OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.enforce_oidc_flow_lifecycle() OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.enforce_operator_session_lifecycle() OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.enforce_operator_session_scope() OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.create_oidc_flow(uuid, char(64), char(64), char(64), bytea, bytea, text, char(64), text, char(64), char(64), text, char(64), text, char(64)) OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.claim_oidc_flow(uuid, bigint, uuid, char(64)) OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.consume_oidc_flow(uuid, bigint, char(64), text, text, char(64), smallint) OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.expire_oidc_flow(uuid, bigint) OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.create_operator_session(uuid, uuid, bigint, char(64), char(64), text, char(64), text) OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.touch_operator_session(uuid, bigint, char(64)) OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.rotate_operator_session(uuid, bigint, char(64), char(64)) OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.end_operator_session(uuid, bigint, text, text) OWNER TO alon_ai_auth_owner;
ALTER FUNCTION security_runtime.prune_expired(timestamptz, timestamptz) OWNER TO alon_ai_auth_owner;

REVOKE ALL ON ALL TABLES IN SCHEMA security_runtime FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA security_runtime FROM PUBLIC;
GRANT USAGE ON SCHEMA security_runtime TO alon_ai_api_runtime, alon_ai_retention_runtime;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON security_runtime.oidc_flows, security_runtime.operator_sessions FROM alon_ai_api_runtime;
GRANT SELECT ON security_runtime.oidc_flows, security_runtime.operator_sessions TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.create_oidc_flow(uuid, char(64), char(64), char(64), bytea, bytea, text, char(64), text, char(64), char(64), text, char(64), text, char(64)) TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.claim_oidc_flow(uuid, bigint, uuid, char(64)) TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.consume_oidc_flow(uuid, bigint, char(64), text, text, char(64), smallint) TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.expire_oidc_flow(uuid, bigint) TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.create_operator_session(uuid, uuid, bigint, char(64), char(64), text, char(64), text) TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.touch_operator_session(uuid, bigint, char(64)) TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.rotate_operator_session(uuid, bigint, char(64), char(64)) TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.end_operator_session(uuid, bigint, text, text) TO alon_ai_api_runtime;
GRANT EXECUTE ON FUNCTION security_runtime.prune_expired(timestamptz, timestamptz) TO alon_ai_retention_runtime;
```

The migration is one transaction, and every security-definer function is owned by the `NOLOGIN` auth owner, fixes `search_path` to `pg_catalog,security_runtime`, schema-qualifies table access, receives only typed scalar arguments, and has PUBLIC execute revoked before the API role can log in. `alon_ai_api_runtime` has table SELECT plus exactly the eight lifecycle functions above; raw INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER privileges are absent and direct-write negatives return `42501`. The retention role can execute only `prune_expired`; product/worker/public roles have neither schema usage nor function/table privileges.

`create_oidc_flow` is idempotent only when the flow ID or `(operator_origin_hash,idempotency_key_hash)` resolves to the byte-identical complete request binding; conflict is `23505`. It alone inserts exact `PENDING`, version 1, ten-minute rows. `claim_oidc_flow` gives one current-version winner a canonical two-minute lease bounded by flow expiry; consume/expire accept only their exact state, version, claim/lease conditions. A stale/concurrent/expired function call returns `40001` and performs no write. The insert/lifecycle triggers independently freeze state/nonce/PKCE ciphertext and payload, origin, issuer/client/callback hashes, return path, request idempotency/schema/hash and creation/expiry, then admit only the columns named for the exact transition. Even an owner-side migration statement cannot change request authority during `PENDING -> CLAIMED`.

`create_operator_session` takes the per-operator advisory lock, returns an exact replay only while its original binding still matches, revokes the deterministic oldest ACTIVE row when two already exist, and inserts the canonical ACTIVE/version-1 timing tuple. Touch, rotate and end are separate current-version functions; lost races return `40001`. Rotation can use only the current handle after `rotate_after`, changes that handle, copies the old current digest to previous, and atomically sets the one 30-second overlap, 30-minute idle limit and next 15-minute rotation. It cannot run while an earlier overlap is active. When current does not change, the trigger freezes the previous digest/expiry and rotation deadline; therefore a prior handle cannot be fabricated, replaced, extended or slid by a touch or termination. The row check retains that set-once historical tuple after expiry without requiring it to remain later than a subsequently advanced `last_seen_at`; the authentication predicate alone makes an expired previous handle unusable, while current-handle touch and the next genuine rotation remain legal. Terminal rows and the complete subject/epoch/key/device/time binding are immutable. Cross-row digest collision, active-session cap, terminal reopening, broad update and direct API DML all fail independently of application code.

### Permanent rollback-only security-runtime fixture

The exact fixture below runs only after the DB-01 plus primary SEC-02 SQL extraction compiles in a fresh database. It proves two ordinary auth tables, zero API direct-write grants, exactly eight API lifecycle-function grants, `42501` raw DML denial, one `40001` claim winner, idempotent OIDC create, function-mediated create/touch/genuine rotation, current-handle touch after an expired overlap, and the three reviewer counterexamples against owner authority so the lifecycle trigger—not an earlier ACL—must return the exact `23514` message. The disposable superuser may use replica mode only to seed an exact historical post-rotation row without a wall-clock sleep; its asserted touch runs through the API function under normal trigger enforcement. It ends with `ROLLBACK`; retaining a row or accepting a different failure target fails the fixture.

```sql
\set ON_ERROR_STOP on
\pset pager off

BEGIN;

DO $$
DECLARE
    table_count integer;
    write_grants integer;
    api_function_grants integer;
BEGIN
    SELECT count(*) INTO table_count
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='security_runtime' AND c.relkind='r';
    SELECT count(*) INTO write_grants
    FROM information_schema.role_table_grants
    WHERE grantee='alon_ai_api_runtime' AND table_schema='security_runtime'
      AND privilege_type IN ('INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER');
    SELECT count(*) INTO api_function_grants
    FROM information_schema.role_routine_grants
    WHERE grantee='alon_ai_api_runtime' AND specific_schema='security_runtime'
      AND privilege_type='EXECUTE';
    IF table_count <> 2 OR write_grants <> 0 OR api_function_grants <> 8 THEN
        RAISE EXCEPTION 'security catalog mismatch tables=% writes=% functions=%', table_count, write_grants, api_function_grants;
    END IF;
    RAISE NOTICE 'SECURITY_CATALOG_GREEN tables=% api_direct_writes=% api_execute_functions=%', table_count, write_grants, api_function_grants;
END $$;

INSERT INTO public.operators (operator_id,subject,display_name)
VALUES
 ('20000000-0000-4000-8000-000000000001','exceptional-security-green','Exceptional Security GREEN'),
 ('20000000-0000-4000-8000-000000000002','exceptional-overlap-green','Exceptional Overlap GREEN');

SET LOCAL ROLE alon_ai_api_runtime;

DO $$
DECLARE actual_state text;
BEGIN
    BEGIN
        INSERT INTO security_runtime.oidc_flows (
          flow_id,flow_handle_digest,state_digest,nonce_digest,pkce_verifier_ciphertext,
          flow_payload_ciphertext,encryption_key_generation,operator_origin_hash,
          callback_issuer,client_id_hash,redirect_uri_hash,return_path,
          idempotency_key_hash,request_schema_version,request_hash,expires_at
        ) VALUES (
          '20000000-0000-4000-8000-000000000099',repeat('0',64),repeat('1',64),repeat('2',64),
          convert_to(repeat('p',32),'UTF8'),convert_to(repeat('f',32),'UTF8'),'key.v1',repeat('3',64),
          'https://accounts.google.com',repeat('4',64),repeat('5',64),'/acl',repeat('6',64),
          'oidc.request.v1',repeat('7',64),statement_timestamp()+interval '10 minutes'
        );
        RAISE EXCEPTION 'API direct INSERT escaped';
    EXCEPTION WHEN insufficient_privilege THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE;
        IF actual_state <> '42501' THEN RAISE; END IF;
        RAISE NOTICE 'SECURITY_ACL_GREEN operation=direct_insert sqlstate=%', actual_state;
    END;
END $$;

SELECT (security_runtime.create_oidc_flow(
  '20000000-0000-4000-8000-000000000101',repeat('1',64),repeat('2',64),repeat('3',64),
  convert_to(repeat('p',32),'UTF8'),convert_to(repeat('f',32),'UTF8'),'key.v1',repeat('4',64),
  'https://accounts.google.com',repeat('5',64),repeat('6',64),'/before',repeat('7',64),
  'oidc.request.v1',repeat('8',64)
)).flow_id;
-- Exact replay returns the same row; no second row.
SELECT (security_runtime.create_oidc_flow(
  '20000000-0000-4000-8000-000000000101',repeat('1',64),repeat('2',64),repeat('3',64),
  convert_to(repeat('p',32),'UTF8'),convert_to(repeat('f',32),'UTF8'),'key.v1',repeat('4',64),
  'https://accounts.google.com',repeat('5',64),repeat('6',64),'/before',repeat('7',64),
  'oidc.request.v1',repeat('8',64)
)).flow_id;
SELECT (security_runtime.claim_oidc_flow(
  '20000000-0000-4000-8000-000000000101',1,
  '20000000-0000-4000-8000-000000000111',repeat('9',64)
)).version;

DO $$
DECLARE actual_state text;
BEGIN
    BEGIN
        PERFORM security_runtime.claim_oidc_flow(
          '20000000-0000-4000-8000-000000000101',1,
          '20000000-0000-4000-8000-000000000112',repeat('a',64));
        RAISE EXCEPTION 'second OIDC claimant escaped';
    EXCEPTION WHEN serialization_failure THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE;
        IF actual_state <> '40001' THEN RAISE; END IF;
        RAISE NOTICE 'SECURITY_CAS_GREEN operation=second_claim sqlstate=%',actual_state;
    END;
END $$;

DO $$
DECLARE actual_state text;
BEGIN
    BEGIN
        UPDATE security_runtime.oidc_flows SET version=version+1
        WHERE flow_id='20000000-0000-4000-8000-000000000101';
        RAISE EXCEPTION 'API direct UPDATE escaped';
    EXCEPTION WHEN insufficient_privilege THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE;
        IF actual_state <> '42501' THEN RAISE; END IF;
        RAISE NOTICE 'SECURITY_ACL_GREEN operation=direct_update sqlstate=%',actual_state;
    END;
END $$;

SELECT (security_runtime.create_operator_session(
  '20000000-0000-4000-8000-000000000201','20000000-0000-4000-8000-000000000001',
  1,repeat('b',64),repeat('c',64),'lookup.v1',repeat('d',64),'CHROME'
)).version;
SELECT (security_runtime.touch_operator_session(
  '20000000-0000-4000-8000-000000000201',1,repeat('c',64)
)).version;

RESET ROLE;
SET LOCAL ROLE alon_ai_auth_owner;

-- Older canonical row permits a genuine rotation to be exercised without a wait.
INSERT INTO security_runtime.operator_sessions (
 session_id,operator_id,authentication_epoch,subject_hash,current_handle_digest,
 lookup_key_generation,issued_at,reauthenticated_at,last_seen_at,idle_expires_at,
 absolute_expires_at,rotate_after,created_ip_prefix_hash,user_agent_family
) VALUES (
 '20000000-0000-4000-8000-000000000202','20000000-0000-4000-8000-000000000001',1,
 repeat('1',64),repeat('2',64),'lookup.v1',statement_timestamp()-interval '20 minutes',
 statement_timestamp()-interval '20 minutes',statement_timestamp()-interval '20 minutes',
 statement_timestamp()+interval '10 minutes',statement_timestamp()+interval '7 hours 40 minutes',
 statement_timestamp()-interval '5 minutes',repeat('3',64),'FIREFOX'
);

-- Exact reviewer fabrication against an unrotated row.
DO $$
DECLARE actual_state text; actual_message text;
BEGIN
    BEGIN
        UPDATE security_runtime.operator_sessions
        SET previous_handle_digest=repeat('4',64),
            previous_handle_expires_at=statement_timestamp()+interval '30 seconds',
            last_seen_at=statement_timestamp(),
            idle_expires_at=statement_timestamp()+interval '30 minutes',
            version=version+1
        WHERE session_id='20000000-0000-4000-8000-000000000202';
        RAISE EXCEPTION 'previous-handle fabrication escaped';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE,actual_message=MESSAGE_TEXT;
        IF actual_state <> '23514' OR actual_message <> 'ACTIVE session touch changed non-touch authority' THEN RAISE; END IF;
        RAISE NOTICE 'SECURITY_TRIGGER_GREEN mutation=fabricated_previous_handle sqlstate=% message=%',actual_state,actual_message;
    END;
END $$;

RESET ROLE;
SET LOCAL ROLE alon_ai_api_runtime;
SELECT (security_runtime.rotate_operator_session(
  '20000000-0000-4000-8000-000000000202',1,repeat('2',64),repeat('5',64)
)).version;
SELECT (security_runtime.touch_operator_session(
  '20000000-0000-4000-8000-000000000202',2,repeat('5',64)
)).version;
RESET ROLE;
SET LOCAL ROLE alon_ai_auth_owner;

-- Exact reviewer OIDC mutation, attempted with table-owner authority so the
-- trigger rather than the ACL proves the complete binding.
DO $$
DECLARE actual_state text; actual_message text;
BEGIN
    BEGIN
        UPDATE security_runtime.oidc_flows
        SET state='CONSUMED',
            pkce_verifier_ciphertext=convert_to(repeat('q',32),'UTF8'),
            operator_origin_hash=repeat('a',64),return_path='/after',
            result_schema_version='oidc.result.v1',result_kind='SUCCEEDED',
            result_hash=repeat('f',64),result_http_status=303,
            terminal_at=statement_timestamp(),version=version+1
        WHERE flow_id='20000000-0000-4000-8000-000000000101';
        RAISE EXCEPTION 'OIDC binding mutation escaped';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE,actual_message=MESSAGE_TEXT;
        IF actual_state <> '23514' OR actual_message <> 'immutable complete OIDC request binding changed' THEN RAISE; END IF;
        RAISE NOTICE 'SECURITY_TRIGGER_GREEN mutation=oidc_complete_binding sqlstate=% message=%',actual_state,actual_message;
    END;
END $$;

DO $$
DECLARE actual_state text; actual_message text;
BEGIN
    BEGIN
        UPDATE security_runtime.operator_sessions
        SET previous_handle_digest=repeat('f',64),
            previous_handle_expires_at=statement_timestamp()+interval '30 seconds',
            last_seen_at=statement_timestamp(),
            idle_expires_at=statement_timestamp()+interval '30 minutes',
            version=version+1
        WHERE session_id='20000000-0000-4000-8000-000000000202';
        RAISE EXCEPTION 'previous-handle replacement escaped';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE,actual_message=MESSAGE_TEXT;
        IF actual_state <> '23514' OR actual_message <> 'ACTIVE session touch changed non-touch authority' THEN RAISE; END IF;
        RAISE NOTICE 'SECURITY_TRIGGER_GREEN mutation=replaced_previous_handle sqlstate=% message=%',actual_state,actual_message;
    END;
END $$;

DO $$
DECLARE actual_state text; actual_message text;
BEGIN
    BEGIN
        UPDATE security_runtime.operator_sessions
        SET previous_handle_expires_at=statement_timestamp()+interval '30 seconds',
            last_seen_at=statement_timestamp(),
            idle_expires_at=statement_timestamp()+interval '30 minutes',
            version=version+1
        WHERE session_id='20000000-0000-4000-8000-000000000202';
        RAISE EXCEPTION 'previous-handle slide escaped';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE,actual_message=MESSAGE_TEXT;
        IF actual_state <> '23514' OR actual_message <> 'ACTIVE session touch changed non-touch authority' THEN RAISE; END IF;
        RAISE NOTICE 'SECURITY_TRIGGER_GREEN mutation=sliding_previous_handle sqlstate=% message=%',actual_state,actual_message;
    END;
END $$;

RESET ROLE;

-- Exact historical result of a genuine rotation two minutes ago. Replica mode
-- avoids a wall-clock wait only for this seed; the target touch is origin/API.
SET LOCAL session_replication_role = replica;
INSERT INTO security_runtime.operator_sessions (
 session_id,operator_id,authentication_epoch,subject_hash,current_handle_digest,
 previous_handle_digest,previous_handle_expires_at,lookup_key_generation,
 issued_at,reauthenticated_at,last_seen_at,idle_expires_at,absolute_expires_at,
 rotate_after,created_ip_prefix_hash,user_agent_family,version
) VALUES (
 '20000000-0000-4000-8000-000000000203','20000000-0000-4000-8000-000000000002',1,
 repeat('6',64),repeat('7',64),repeat('8',64),statement_timestamp()-interval '90 seconds',
 'lookup.v1',statement_timestamp()-interval '20 minutes',statement_timestamp()-interval '20 minutes',
 statement_timestamp()-interval '2 minutes',statement_timestamp()+interval '28 minutes',
 statement_timestamp()+interval '7 hours 40 minutes',statement_timestamp()+interval '13 minutes',
 repeat('9',64),'SAFARI',2
);
SET LOCAL session_replication_role = origin;
SET LOCAL ROLE alon_ai_api_runtime;
SELECT (security_runtime.touch_operator_session(
  '20000000-0000-4000-8000-000000000203',2,repeat('7',64)
)).version;
RESET ROLE;

DO $$
DECLARE flow_count integer; session_count integer;
BEGIN
    SELECT count(*) INTO flow_count FROM security_runtime.oidc_flows;
    SELECT count(*) INTO session_count FROM security_runtime.operator_sessions;
    IF flow_count<>1 OR session_count<>3 THEN RAISE EXCEPTION 'unexpected row counts'; END IF;
    RAISE NOTICE 'SECURITY_FUNCTION_GREEN flows=% sessions=% oidc_version=2 touched_version=2 rotated_version=3 post_overlap_touch_version=3',flow_count,session_count;
END $$;
ROLLBACK;
```

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
