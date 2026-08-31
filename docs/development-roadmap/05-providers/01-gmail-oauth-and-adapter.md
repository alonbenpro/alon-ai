# Gmail OAuth and Send Adapter

**Document ID:** PROVIDER-01
**Status:** Planned M6 integration; no OAuth flow, token store, Gmail client, or send exists today
**Milestone:** M6, after M1 and M5
**Owner:** Solo operator
**Prerequisites:** [ROADMAP-ROOT](../README.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [DB-03](../02-database/03-leads-campaigns-and-messages.md), [DB-05](../02-database/05-audit-events-and-idempotency.md), and [WF-05](../03-workflows/05-outreach-and-reply-workflow.md)
**Outputs:** Server-side Gmail OAuth lifecycle, credential boundary, send-only provider port, exact send result/error taxonomy, and mailbox-bound evidence protocol
**Unlocks:** [PROVIDER-02](02-gmail-history-sync.md) and the M6 [SendGateway](../06-backend/04-send-gateway.md)
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

M6 connects one operator-owned Gmail account without giving credentials or send authority to agents, workflows, the frontend, or generic application services. `SendGateway` is the only production caller of the send-only `GmailProvider`; reconciliation and history use the separate read-only port in PROVIDER-02. The adapter translates one already-authorized immutable attempt into one Gmail `users.messages.send` call and returns evidence. It never decides recipient, policy, approval, budget, suppression, retry, or state.

The isolated M1 harness may use a disposable composition of the same wire behavior against owned aliases. That does not install a product mailbox or satisfy M6. Product outreach stays disabled until both M1 and M6 pass, and passing gates grants no campaign, recipient, or spend authority.

## Current repository state

Implemented today: `EmailDraft`, UUID `SendRequest`, `SendResult`, the `GmailProvider` protocol, a minimal `SendGateway`, Gmail-shaped settings, and `ALON_AI_OUTREACH_ENABLED=false`. Missing: OAuth routes, PKCE/state, token encryption, account verification, Gmail SDK/HTTP adapter, MIME construction, stable RFC `Message-ID`, product attempt/result records, history reads, reconciliation, quotas, and any real send. The planned contracts below replace the foundation DTOs at M6; they do not describe current behavior.

## Scope and non-goals

In scope: server-side OAuth authorization-code flow, exact scope grant, encrypted refresh-token storage outside product tables, token refresh/revocation, immutable mailbox binding, RFC 5322 MIME/base64url encoding, one send call, typed evidence/errors, quotas, fixtures, and provider replacement. Non-goals: domain-wide delegation, arbitrary user accounts, SMTP, drafts, Gmail UI automation, contact access, token exposure to Next.js/agents/workflows, adapter retries after ambiguous acceptance, delivery/read claims, or automatic product-outreach enablement.

## Exact planned implementation surfaces

Create `providers/gmail/contracts.py`, `providers/gmail/oauth.py`, `providers/gmail/adapter.py`, `providers/gmail/errors.py`, `providers/gmail/fixtures.py`, and provider composition called only from API/worker composition roots. `application/gmail_mailboxes.py` owns mailbox commands; PROVIDER-02 owns read/sync composition; `application/sending.py` owns `SendGateway`. Do not add a competing mailbox/token table.

### OAuth, token, mailbox, and callback command protocol

`StartGmailAuthorization` is a normal authenticated/idempotent POST command. It allocates UUIDv4 `oauth_flow_id`; a new connection preallocates UUIDv4 `mailbox_id` with `credential_version=1`, while authenticated reconnect freezes the existing mailbox UUID and preallocates exactly prior version plus one. It creates encrypted flow object `gmail/oauth-flows/{oauth_flow_id}` with operator binding, requested-scope hash, redirect ID, PKCE verifier, state-token hash, preallocated mailbox/version, `authorization_expires_at=issued_at+10 minutes`, and `replay_expires_at=issued_at+24 hours`; no product row exists yet. Signed+encrypted browser state contains flow ID, operator binding, scope/redirect hashes, expiries, and nonce. Raw verifier/code/token never leaves the secret boundary.

Exact flow states are `ISSUED`, `CLAIMED`, `EXCHANGE_STARTED`, `CREDENTIAL_STAGED`, `CREDENTIAL_ACTIVE`, `DB_COMMITTED`, `CONSUMED_SUCCESS`, and `CONSUMED_FAILURE`. A versioned credential object has `STAGED`, `ACTIVE`, `GC_CLAIMED`, `REVOKED`, or `DELETED`. Application metadata is exactly safe `oauth_flow_id`, preallocated `mailbox_id`, `provider_account_hash`, `granted_scope_hash`, and encryption `credential_key_version`; secret-store system metadata supplies object version, lifecycle state, CAS generation, and timestamps. The refresh token is envelope-encrypted payload, never metadata. Access tokens remain memory-only.

`CompleteGmailAuthorization` is registered under scope family `gmail.oauth.complete`, concrete scope `gmail.oauth.complete:{oauth_flow_id}`, and derived key `oauth-flow:{oauth_flow_id}` because browser GET cannot supply `Idempotency-Key`. The callback verifies/decrypts state and claims DB-05 `command_idempotency(IN_PROGRESS)` before any exchange using request schema `api.complete_gmail_authorization.request.v1` and a hash of flow ID, state-token hash, authorization-code hash, and redirect ID. Correlation is command metadata, not replay identity. Raw state/code/PKCE never enters PostgreSQL/logs.

`GmailOAuthSagaService` exclusively owns flow and credential objects. A secret-store handler lease keyed `oauth-handler:{oauth_flow_id}` uses compare-and-set generation and 30-second expiry; an exact replay may acquire it only after the prior lease expires. `ISSUED -> CLAIMED` binds request/code hashes. Immediately before the one network exchange, CAS records `EXCHANGE_STARTED`; the authorization code is never exchanged twice. The response must grant exactly `gmail.modify`; `users.getProfile` establishes the provider-account hash.

STAGE writes versioned object `gmail/oauth-credentials/{mailbox_id}/v{credential_version}` with operation key `oauth-stage:{oauth_flow_id}:{mailbox_id}:v{credential_version}`. CAS permits absent -> `STAGED`; repeating the same key returns the existing version after verifying the five safe metadata values, while any mismatch opens an incident and returns restart-required. ACTIVATE uses `oauth-activate:{oauth_flow_id}:{mailbox_id}:v{credential_version}` and CAS `STAGED -> ACTIVE`; same-key replay returns the same ACTIVE version. Before PostgreSQL success this ACTIVE object is still non-addressable by product code because `GmailCredentialResolver` requires an ACTIVE `gmail_mailboxes` row with the exact stored tuple.

Before the database transaction, ACTIVATE acquires key `oauth-db-bind:{oauth_flow_id}:{mailbox_id}:v{credential_version}` and returns signed `ActiveCredentialProofV1={oauth_flow_id,mailbox_id,provider_account_hash,granted_scope_hash,credential_handle_hash,credential_version,credential_key_version,credential_activation_generation,lease_expires_at}`. The secret-store lease is 30 seconds; PostgreSQL lock/statement timeout is 5 seconds and the transaction must start with at least 10 seconds remaining. GC cannot claim an object under this lease. `GmailMailboxCommandService` validates proof signature/expiry and atomically inserts `gmail_mailboxes(status=ACTIVE)` with the byte-equal proof tuple, safe audit, and `command_idempotency(SUCCEEDED)` fixed 303 redirect result. No external call occurs inside the PostgreSQL transaction. Success without exact ACTIVE proof is impossible.

After commit, idempotent CAS records flow `DB_COMMITTED -> CONSUMED_SUCCESS` and credential binding metadata. If that CAS or HTTP response is lost, the database mailbox/result is already authoritative: replay returns the stored 303 and a binder repairs safe secret metadata. If PostgreSQL did not commit, command remains `IN_PROGRESS`, there is no product-addressable mailbox, and exact replay resumes by flow ID from STAGED or ACTIVE without re-exchanging.

The unavoidable exchange-to-stage gap fails closed. A crash before `EXCHANGE_STARTED` lets replay perform the one exchange. After `EXCHANGE_STARTED`, replay performs up to three strong-consistency object reads (initial, then 100 ms and 400 ms); STAGED/ACTIVE resumes, but no object proves the token was never durably captured, so the code is never exchanged again and the flow becomes `CONSUMED_FAILURE` with `oauth_restart_required`. STAGE, ACTIVATE, handler-lease, and bind CAS each allow three total attempts with 100/400 ms backoff within the request deadline; PostgreSQL serialization permits three total attempts while proof remains valid. Exhaustion preserves `IN_PROGRESS` only when STAGED/ACTIVE is resumable; otherwise it stores a `SUCCEEDED` command result with typed `outcome=FAILURE` and the restart redirect, preserving DB-05 result invariants. Provider exchange itself has zero retry.

`OAuthCredentialGarbageCollector` runs hourly. STAGED or unbound ACTIVE becomes eligible only at `orphan_gc_not_before=staged_at+24 hours`. GC first requires no unexpired handler/bind lease, then one PostgreSQL `REPEATABLE READ READ ONLY` snapshot proving no `gmail_mailboxes` row for the exact flow/mailbox/handle/version and no matching `command_idempotency(IN_PROGRESS)` row. CAS to `GC_CLAIMED` is the cleanup winner; callback resume then cannot activate/bind. GC rechecks the same PostgreSQL predicates before revoke/delete. A mailbox or IN_PROGRESS command reference aborts cleanup. An abandoned resumable saga never ages directly into deletion: authenticated `RepairIncident` kind `ABORT_OAUTH_SAGA` must first prove no live lease/mailbox, store the fixed SUCCEEDED failure-outcome restart result, and CAS the flow to `CONSUMED_FAILURE`; only a later GC pass may claim it. Deleted token payload stays deleted; a redacted flow tombstone survives through replay expiry.

`GmailCredentialConsistencyService` checks every credential resolution and scheduled audit. DB ACTIVE plus missing/non-ACTIVE/mismatched secret, or secret metadata conflicting with DB, fails before token access: `GmailMailboxCommandService` disables the mailbox and applicable controls, records safe `gmail.oauth_consistency_failed.v1` audit and incident, and requires authenticated repair or fresh authorization. It never silently rewrites DB or secret state.

| Kill point | Durable state | Exact replay/recovery |
| --- | --- | --- |
| before exchange | command `IN_PROGRESS`; flow `CLAIMED`; no credential | acquire expired/free handler lease; exchange once; continue |
| after exchange / before STAGE | flow `EXCHANGE_STARTED`; no object, unless STAGE response alone was lost | three consistent lookups; resume discovered object, otherwise no second exchange and fixed restart |
| after STAGE / before ACTIVATE | exact STAGED object; no mailbox/result | idempotent ACTIVATE, proof, and DB transaction; exchange count stays one |
| after ACTIVATE / before DB commit | ACTIVE but product-non-addressable object; no DB mailbox/result; command `IN_PROGRESS` | reacquire bind proof and commit exact tuple; exchange count stays one |
| after DB commit / before HTTP | ACTIVE mailbox plus stored SUCCEEDED redirect | return stored 303; binder finishes metadata only |
| cleanup race | one CAS winner between handler/bind lease and `GC_CLAIMED` | reference/lease blocks GC; GC winner blocks resume and requires restart; never delete a bound credential |

OAuth audit types remain audit-only: `gmail.oauth_authorization_started.v1`, `gmail.oauth_connected.v1`, `gmail.oauth_refresh_failed.v1`, `gmail.oauth_revoked.v1`, and `gmail.oauth_consistency_failed.v1`. Safe observability is flow/mailbox IDs, credential-handle hash/version/key version, lifecycle/CAS generation, lease age, command state, retry count, transition/result code, GC proof outcome, and correlation/causation. Forbidden everywhere: raw state/code/verifier/token, ciphertext, mailbox address, provider response/error text, or secret object path. Public callback text is fixed and opaque.

Google's server-side flow supplies offline refresh tokens and requires recovery when a refresh token is revoked or invalid: [server-side authorization](https://developers.google.com/workspace/gmail/api/auth/web-server). `gmail.modify` is selected because the same mailbox must send and read/synchronize; it is restricted and requires applicable Google verification/data-use controls: [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes). No broader `https://mail.google.com/` scope is accepted.

### Send-only port and immutable authority

`GmailProvider.send(request: GmailSendRequestV1) -> GmailSendResultV1` is the only Python method allowed to issue `users.messages.send`. PROVIDER-02's `GmailMailboxReadProvider` cannot send. The request is strict/frozen/extra-forbid and contains exactly:

```text
schema_version="gmail.send.request.v1"; provider_call_id; send_attempt_id;
send_intent_id; experiment_id; campaign_id; campaign_version; campaign_member_id;
lead_id; message_id; mailbox_id; approval_id; policy_decision_id; policy_scope="SEND";
policy_version; scope_hash; policy_facts_hash; policy_allowed=true;
rate_reservation_id; rate_policy_version; rate_window_start; rate_slot_number;
rate_concurrency_lease_token; rate_consumed_at;
idempotency_key; rfc_message_id; mime_sha256; mime_bytes; timeout_ms.
```

`campaign_version` is positive; IDs are UUIDv4; hashes are lowercase 64-hex; `timeout_ms` is `1..30_000` with deterministic default `15_000`. `provider_call_id` and `send_attempt_id` are distinct identities and are never required to equal one another. `mime_bytes` exists only in process memory and is excluded from repr/log/trace serialization. The locked `campaign_member_id` byte-matches `campaign_members(campaign_member_id,campaign_id,campaign_version,lead_id)`. Approval/eligibility basis fields byte-match the intent; `policy_*` fields are exclusively the fresh final SEND decision copied from `send_attempts`, never the eligibility decision; rate fields, immutable concurrency token, and non-null consumption timestamp byte-match that attempt's consumed `send_rate_reservations` row; all remaining identity through `rfc_message_id` matches DB-03 composites. Eligibility and final SEND share `scope_hash` but need not and normally do not share facts hashes. After the call, `GmailResultCaptureService` adds immutable `(provider_result_id,send_attempt_id,provider_call_id,provider='GMAIL')` under the attempt's `(send_attempt_id,mailbox_id,rfc_message_id)`, completing the exact experiment/campaign-version/member/lead/message/mailbox/approval/policy/scope/intent/attempt/call/result chain. The adapter rejects mismatch before credential access.

The fresh `policy_decision_id/policy_version/scope_hash/policy_facts_hash/policy_allowed=true` is the provider boundary's only compliance authority. The adapter revalidates its exact allowed `SEND` composite FK but never receives recipient identity/jurisdiction/consent/legal-review/disclosure/Google-review/observation facts or reason text. Provider fixtures pair the request with the restricted policy fixture: one complete current allow and one zero-call fixture for each dedicated compliance/signal denial. A denial, unknown code, stale decision or recipient hash in request/OpenAPI/log fixture fails before credential lookup.

The gateway builds one RFC 5322 message with exact `From`, `To`, `Subject`, `Date`, MIME version/content type, and stable `Message-ID: {rfc_message_id}`; CR/LF header injection, Bcc, attachments, HTML, tracking pixels, and extra recipients are forbidden in v1. Gmail requires an RFC-formatted MIME message encoded into the message resource's base64url `raw` field: [create and send messages](https://developers.google.com/workspace/gmail/api/guides/sending). The call is `POST /gmail/v1/users/me/messages/send`; a successful response is a Gmail `Message`: [users.messages.send](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send).

The exact discriminated result branches are:

| `result_type` | Required fields | Meaning and application action |
| --- | --- | --- |
| `ACCEPTED` | `schema_version="gmail.send.accepted.v1"`, call/attempt/mailbox/RFC IDs, non-empty Gmail message/thread IDs, provider request ID when supplied, response fingerprint, started/finished UTC | Adapter parsed a successful send response. `GmailResultCaptureService` inserts `provider_results(outcome='ACCEPTED')`; `SendGateway` commits `SENDING -> SENT` and only `send.provider_accepted.v1`. |
| `CONCLUSIVE_REJECTION` | `schema_version="gmail.send.rejected.v1"`, same safe identity, `GmailErrorCode`, retry class, provider request ID, error fingerprint, timestamps | Provider definitively rejected the call. Capture `REJECTED`; deterministic `SendRecoveryService`, never the adapter, decides `FAILED_RETRYABLE` or `FAILED_PERMANENT`. |
| `UNKNOWN` | `schema_version="gmail.send.unknown.v1"`, safe identity, error code/fingerprint, provider request ID when known, timestamps | Acceptance cannot be proven false. Capture `UNKNOWN`; commit `SENDING -> AMBIGUOUS` and `send.outcome_ambiguous.v1`; PROVIDER-02 read-only reconciliation starts, and this result can never authorize retry/replacement or terminal non-send. |

All response/error fingerprints are lowercase SHA-256 over restricted normalized evidence; raw bodies are stored only by protected capture reference when incident policy requires them. A parsed 2xx with IDs is direct acceptance even though it does not prove delivery. A malformed 2xx, connection loss, timeout, or HTTP 5xx is `UNKNOWN`, because the unsafe POST might have been processed. It is never a generic retry.

### Exact Gmail error taxonomy and retry rules

`GmailErrorCode` is exact: `OAUTH_STATE_MISMATCH`, `OAUTH_CODE_INVALID`, `OAUTH_SCOPE_MISSING`, `OAUTH_REPLAY_CONFLICT`, `OAUTH_EXCHANGE_OUTCOME_UNCERTAIN`, `TOKEN_INVALID_GRANT`, `TOKEN_REVOKED`, `MAILBOX_IDENTITY_MISMATCH`, `GMAIL_BAD_REQUEST`, `GMAIL_UNAUTHORIZED`, `GMAIL_FORBIDDEN`, `GMAIL_RATE_LIMITED`, `GMAIL_QUOTA_EXCEEDED`, `GMAIL_NOT_FOUND`, `GMAIL_SERVER_ERROR`, `GMAIL_TRANSPORT_TIMEOUT`, `GMAIL_TRANSPORT_ERROR`, and `GMAIL_RESPONSE_INVALID`. Provider text is never an application error name.

| Observation | Send classification | Automatic adapter retry |
| --- | --- | --- |
| local validation, missing credential, scope/account mismatch | no provider call; permanent/credential recovery | none |
| HTTP 400/401/404 or non-rate 403 with parsed Google error | conclusive rejection; 401/invalid grant disables mailbox | none |
| HTTP 403 `rateLimitExceeded`/`userRateLimitExceeded` or HTTP 429 | conclusive rejection, bounded retry eligibility recorded from headers/window | none inside adapter |
| HTTP 5xx, timeout, connection reset after write may begin, malformed 2xx | `UNKNOWN`/`AMBIGUOUS` | forbidden; Sent reconciliation first |

Google documents 403/429 reasons, per-user mail limits, 5xx errors, and exponential backoff for retryable requests: [Gmail error handling](https://developers.google.com/workspace/gmail/api/guides/handle-errors). For this unsafe POST, that generic advice is subordinate to DB-03 ambiguity safety. `SendRecoveryService` may schedule a new numbered attempt only after an explicit provider rejection or signed local pre-write proof that request bytes never left the process, plus every ARCH-03 guard. Timeout, error class, elapsed time, and zero/multiple/conflicting search or history results are never qualifying evidence. Initial M6 application capacity remains one start per 30 seconds and one concurrent call per mailbox; Gmail/provider quota is a stricter outer ceiling, never authority.

### Fixtures, replacement seam, telemetry, and example

Modes are `LIVE_CAPTURE` and `RECORDED_FIXTURE`. Live mode requires M6 composition, secrets, owned-alias control, and records sanitized request/result fingerprints. Fixture mode accepts only signed immutable `gmail.send.fixture.v1` containing the strict request with `mime_bytes` replaced by `mime_sha256`, exact result, captured time, fixture hash, and no credential/address/body. Fixture mode has no network client. A replacement adapter must pass the same contract, MIME golden vectors, timeout/ambiguity matrix, and call-path proof; provider-specific SDK objects cannot escape.

Safe telemetry: request/correlation/call/intent/attempt/mailbox IDs, provider request ID, state, duration, status/error code, response size, quota headers, and fingerprint. Forbidden: Authorization headers, tokens, raw MIME, subject/body, address, Google error text, or full response. Gmail send has no direct API fee entry, but usage and operational cost remain recorded with zero provider amount when applicable.

```python
GmailSendRequestV1(
    schema_version="gmail.send.request.v1",
    provider_call_id=UUID("8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d"),
    send_attempt_id=UUID("9b85bc7c-cf60-45a9-9925-6c8b82b88e0d"),
    send_intent_id=UUID("6c582e3f-bc90-41f5-82e8-cf70c95c5655"),
    experiment_id=UUID("7dd7a7b3-5d57-4ae8-b1d9-49307050d7b8"),
    campaign_id=UUID("a5dfb772-bb41-4988-8cbd-962dd0803c07"), campaign_version=1,
    campaign_member_id=UUID("03157284-c5c8-4d87-a4d9-cb41777cab5f"),
    lead_id=UUID("041a8a85-23a2-455c-a1f8-67e038b3fc45"),
    message_id=UUID("e924022b-0639-4cb1-9d86-cd49c166d42a"),
    mailbox_id=UUID("f64e645f-9be6-471a-a998-3f28bcbe5d5a"),
    approval_id=UUID("bb50b06e-dafa-4b1f-84de-81f67252bed2"),
    policy_decision_id=UUID("74e403e1-3645-4f5e-b87e-f617255e4ca8"),
    policy_scope="SEND", policy_version="send-policy.v1",
    scope_hash="1111111111111111111111111111111111111111111111111111111111111111",
    policy_facts_hash="2222222222222222222222222222222222222222222222222222222222222222",
    policy_allowed=True,
    rate_reservation_id=UUID("fe88cb7a-876f-4c99-8c7c-10c52403dbb2"),
    rate_policy_version="mailbox-rate.v1",
    rate_window_start=datetime.fromisoformat("2026-08-28T00:00:00+00:00"), rate_slot_number=0,
    rate_concurrency_lease_token="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    rate_consumed_at=datetime.fromisoformat("2026-08-28T00:00:01+00:00"),
    idempotency_key="send-intent-1",
    rfc_message_id="<send-1@test.invalid>",
    mime_sha256="a7a75fb7a7be061112e331a1fc3d0acf7145463a3487aa66190f2586f13a401c",
    mime_bytes=b"From: sender@test.invalid\r\nTo: recipient@test.invalid\r\nSubject: Controlled test\r\nMessage-ID: <send-1@test.invalid>\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=\"utf-8\"\r\n\r\nControlled M6 test.\r\n",
    timeout_ms=15000,
)
```

```json
{
  "result_type": "UNKNOWN",
  "schema_version": "gmail.send.unknown.v1",
  "provider_call_id": "8a0e6e0b-f4b1-4cd7-8cf1-2a75d5edb75d",
  "send_attempt_id": "9b85bc7c-cf60-45a9-9925-6c8b82b88e0d",
  "mailbox_id": "f64e645f-9be6-471a-a998-3f28bcbe5d5a",
  "rfc_message_id": "<send-1@test.invalid>",
  "error_code": "GMAIL_TRANSPORT_TIMEOUT",
  "error_fingerprint": "3333333333333333333333333333333333333333333333333333333333333333",
  "provider_request_id": null,
  "started_at": "2026-08-28T00:00:00Z",
  "finished_at": "2026-08-28T00:00:15Z"
}
```

## Ordered implementation tasks

- [ ] **Implement OAuth secret-store saga and command boundary —** Input: authenticated start command, signed/encrypted flow state, secret-store TTL/PKCE, callback code, preallocated mailbox/version. Operation: claim command before one exchange, idempotently STAGE then ACTIVATE, acquire exact bind proof, commit ACTIVE mailbox+SUCCEEDED result, and retain replay/GC tombstones. Output: stored opaque redirect and mailbox referencing one exact ACTIVE credential generation. Test evidence: executable six-point kill matrix, CAS replay/conflict, TTL/GC race, consistency-disable, and single-exchange proof. Failure behavior: resumable STAGED/ACTIVE state or safe restart; never success without active handle.
- [ ] **Implement strict send contracts and MIME builder —** Input: DB-03 composite intent/attempt and encrypted message fields. Operation: construct strict request, reject tuple/header mismatch, create deterministic RFC message identity and base64url MIME. Output: in-memory `GmailSendRequestV1`. Test evidence: `test_gmail_mime_is_rfc_stable_and_rejects_header_injection_or_second_recipient`. Failure behavior: no credential lookup/provider call.
- [ ] **Implement one-call Gmail adapter —** Input: validated request, fresh mailbox-bound token, deadline. Operation: issue exactly one send POST and map every response/transport edge to the exact result taxonomy. Output: accepted, conclusive rejection, or unknown evidence. Test evidence: `test_gmail_send_status_transport_and_malformed_success_matrix_has_no_hidden_retry`. Failure behavior: return typed evidence; never mutate product state.
- [ ] **Integrate sole SendGateway path —** Input: provider result and original authority tuple. Operation: delegate result capture/state/event/cost transactions to exact sole-writer services. Output: DB-03/ARCH-03 chain. Test evidence: `test_only_sendgateway_reaches_gmailprovider_send` and kill points before/after POST/result commit. Failure behavior: unknown acceptance becomes visible `AMBIGUOUS`; both controls close on invariant breach.
- [ ] **Build fixture and credential-security gates —** Input: sanitized live captures and key-rotation/revocation scenarios. Operation: sign fixtures, prove zero-network replay, scan logs/artifacts, rotate/revoke credentials, and verify unresolved attempts survive. Output: M6 provider evidence. Test evidence: fixture byte/hash test, secret/PII scan, rotation/revocation recovery. Failure behavior: adapter disabled and M6 blocked.

## Test strategy

- **Contract `test_gmail_send_request_preserves_complete_db03_authority_tuple`:** every one-field splice fails before credentials.
- **OAuth `test_callback_claims_command_before_exchange_and_exact_replay_returns_redirect`:** one exchange; no success without exact ACTIVE handle/version.
- **OAuth saga `test_staged_or_active_pre_db_replay_resumes_without_second_exchange`:** DB success requires exact ACTIVE proof.
- **OAuth kill matrix `test_each_oauth_secret_saga_kill_point_has_one_safe_outcome`:** exchange-to-stage gap restarts; post-STAGE resumes; post-DB replays success; cleanup has one CAS winner.
- **OAuth `test_revoked_refresh_token_disables_mailbox_and_send_controls`:** no silent refresh loop.
- **Recovery `test_timeout_after_request_write_is_unknown_not_retry`:** `AMBIGUOUS` is mandatory.
- **Event `test_direct_acceptance_emits_provider_accepted_not_reconciled`:** event meanings never collapse.
- **Quota `test_rate_limit_response_is_conclusive_and_retry_is_recovery_owned`:** adapter call count remains one.
- **Authority `test_provider_request_matches_campaign_member_final_send_and_consumed_rate_reservation`:** eligibility decision cannot substitute.
- **Policy `test_gmail_request_has_fresh_allowed_send_hash_authority_and_no_compliance_or_recipient_payload`:** all dedicated denial fixtures have zero credential/provider calls.
- **Security `test_gmail_telemetry_fixture_and_audit_exclude_tokens_addresses_and_content`:** allowlist scan.

## Security, privacy, compliance, idempotency, observability, and cost

OAuth is least-scope, server-only, CSRF/PKCE-protected, envelope-encrypted, staged/activated by versioned CAS, rotated, revocable, and access-audited. Stable `(mailbox_id,idempotency_key)` and `(mailbox_id,rfc_message_id)` remain the application identities; Gmail offers no product idempotency guarantee. Message/address data is `SENSITIVE_SHORT`; attempt/result/authority hashes are `SAFETY_LONG`; only `RetentionCommandService` purges/redacts and never while ambiguity, incident, or suppression holds exist. Metrics alert on token failure, scope/account mismatch, rate/quota denial, unknown outcomes, ambiguity age, and provider-call-after-disable.

## Failure, rollback, and operator recovery

Any credential leakage, DB/secret handle-version mismatch, mailbox mismatch, impossible result, duplicate candidate, or post-control call disables the mailbox and both send controls, stops dequeue, opens an incident, and preserves restricted evidence. Revoke the credential when compromise is plausible; reconcile all possibly accepted calls before deleting token material. Rollback selects the prior adapter build only after contract fixtures pass. Operators reconnect or resolve through authenticated commands; direct secret/SQL edits are not recovery.

## Acceptance and retained evidence

- [ ] One verified owned mailbox references one exact ACTIVE credential handle/version/key/generation and granted scope without secret exposure; no stored/replayed success exists earlier.
- [ ] `SendGateway -> GmailProvider.send` is the only send call path; agents/workflows/frontend cannot receive the port or credential.
- [ ] Every send observation maps to direct acceptance, conclusive rejection, or operator-visible ambiguity with no blind retry.
- [ ] Direct acceptance and reconciled acceptance retain distinct canonical events.
- [ ] The six OAuth kill points prove one exchange, resumable STAGED/ACTIVE pre-DB states, post-DB success replay, and reference-safe GC with one CAS winner.
- [ ] M1/M6/product authority boundaries remain fail-closed.

Retain OAuth flow/credential lifecycle, safe ACTIVE proof, scope/account/handle/key-version manifest, six-point kill/GC traces, provider contract/schema snapshot, MIME/hash fixtures, error/timeout/quota matrix, call graph, safe telemetry scan, credential rotation/revocation evidence, and official-source access date.

## Dependencies and next deliverable

PROVIDER-01 depends on the immutable DB-03/05 authority chain and exact ARCH-03 event meanings. It unlocks [PROVIDER-02 Gmail history and reconciliation](02-gmail-history-sync.md), then [BACKEND-04 SendGateway](../06-backend/04-send-gateway.md); neither unlocks product outreach without the M1 and M6 gate records plus a separate authenticated bounded authority command.
