# Secrets, OAuth Tokens, and Cryptographic Key Security

**Document ID:** SEC-03
**Status:** Planned M6-M8 credential boundary; typed secret settings and CI secret scanning exist, but no runtime secret store, token encryption, key hierarchy, rotation, revocation, or restore proof exists
**Milestone:** M6 Gmail credential gate and M8 private-deployment/recovery gate
**Owner:** Solo operator
**Prerequisites:** [PROVIDER-01 Gmail OAuth saga](../05-providers/01-gmail-oauth-and-adapter.md), [DB-03 mailbox proof](../02-database/03-leads-campaigns-and-messages.md), [DB-06 retention](../02-database/06-migrations-seeding-and-retention.md), SEC-01, and SEC-02
**Outputs:** Versioned secret-object store, envelope-encryption/key hierarchy, least-access protocol, rotation/revocation/zeroization, backup/restore, and leak-prevention evidence
**Unlocks:** Safe M6 Gmail pilot credentials, operator sessions, encrypted personal data, and M8 restore
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Secrets and OAuth tokens exist only in a versioned encrypted object boundary with exact CAS/lease/audit semantics. Product PostgreSQL stores only the frozen safe Gmail ACTIVE proof tuple—flow/account/scope/credential-handle hash/version/key/generation—and never token or ciphertext. A database dump, log sink, fixture set, Graphify graph, agent prompt, or browser compromise alone cannot yield a provider credential.

[NIST SP 800-57 Part 1 Rev. 5](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final), [Google OAuth 2.0 policies](https://developers.google.com/identity/protocols/oauth2/policies), the [Google Gmail scope catalog](https://developers.google.com/workspace/gmail/api/auth/scopes), and OWASP [Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html), [Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html), and [Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html) guidance were accessed 2026-08-29. Algorithm/library selection must follow the current approved runtime cryptography policy at implementation; this roadmap is not cryptographic certification.

## Current repository state

`Settings` uses `SecretStr` for Gmail configuration, `.env.example` contains placeholders, CI scans tracked names/content without printing matches, logs suppress configuration values, and outreach defaults off. The current settings still contemplate static Gmail refresh-token configuration and are not the target OAuth store. No OAuth flow, token exchange, encrypted object, KMS/KEK/DEK, runtime workload identity, key inventory, rotation, revocation, access audit, memory hygiene, backup key, or restore drill exists.

## Scope and non-goals

In scope: OIDC client secret, Gmail OAuth code/access/refresh token and account proof, session/flow encryption/lookup keys, provider API keys, database credentials, signing keys, object/backup encryption keys, CI/deploy credentials, personal-data DEKs, and test canaries.

Non-goals: secrets in source or `.env` in production, one shared master key, raw tokens in the 46 product tables, secret-store listing by agents/workflows, exportable long-lived CI credentials, logging redacted prefixes/last-four values, home-grown crypto primitives, embedding secrets in system prompts, or claiming memory zeroization is perfect in managed Python.

## Exact planned implementation surfaces

Create `security/keys.py`, `security/envelope.py`, `security/secret_store.py`, `security/secret_types.py`, `security/zeroization.py`, `application/credential_consistency.py`, `commands/secrets.py`, and security tests. The production `VersionedSecretStore` adapter must provide `create`, strong `get(id,version)`, `compare_and_swap`, `claim_lease`, `release_lease`, `revoke`, and reference-checked `destroy`. PROVIDER-01's exact `STAGED`, `ACTIVE`, `GC_CLAIMED`, handler/bind leases, six kill points, 24-hour orphan rules, and `ActiveCredentialProofV1` remain normative.

The initial production adapter is the deployment provider's managed KMS plus versioned secret manager selected in M8 infrastructure review; local development uses an ephemeral encrypted fixture store containing fake tokens only. No Gmail pilot starts until the chosen adapter passes the CAS/lease/restart/backup tests. This avoids operating a Vault cluster alone and avoids weakening the external versioned-object contract to plaintext files.

### Secret classes and exact access allowlist

| Secret class | Allowed accessor/use | Explicit denial |
| --- | --- | --- |
| Google OIDC client secret | `OperatorSessionService` token endpoint call | frontend, Gmail adapter, agents/workflows, logs, product DB |
| Gmail authorization code/PKCE/state encryption | exact flow-claimed `GmailOAuthSagaService` | post-exchange reuse, query/log/error/fixture, operator UI |
| Gmail refresh/access token | Gmail OAuth saga and `GmailProvider` for the exact mailbox/account/scope/generation | `SendGateway` plaintext persistence, agent/provider-other capability, general worker config |
| session/flow lookup and envelope keys | SEC-02 store implementation only | application payloads, telemetry, browser |
| provider model/search/page/business keys | matching adapter process/capability only | agents as values, other provider adapter, prompt/tool result |
| DB credential | API/worker/migration workload identity with separate minimum privileges | frontend, provider, test fixtures, Graphify |
| audit/evidence/manifest signing key | exact signer with signing-only interface | decryption, Gmail, model prompt |
| backup key/recovery wrapping key | backup job or offline restore ceremony | live API/worker, same host copy as encrypted backup |
| CI/deploy credential | short-lived OIDC workload identity and exact environment | pull-request code from forks, runtime, developer laptop file |

Every access request includes workload/service identity, secret class/object ID, exact version/generation, purpose enum, correlation/causation, and lease where required. Policy rejects wildcard object/version, cross-mailbox token use, unrecognized purpose, interactive list/export, or stale revoked generation. Safe audit stores object UUID/hash and generation, never secret name containing customer data, plaintext, ciphertext, provider response, or token fingerprint.

### Key hierarchy and encrypted-object envelope

Key hierarchy is: offline recovery wrapping key -> managed KMS root/KEK generation -> purpose-specific KEKs (`oauth`, `session-flow`, `personal-data`, `backup-manifest`, `signing` where asymmetric) -> random per-object DEK -> ciphertext. Separate lookup-HMAC keys digest bearer handles; signing keys never encrypt. Production KEKs are non-exportable where the provider supports it. No key is reused across environment or purpose.

Each encrypted object records non-secret `object_id`, type enum, version, state, key generation, algorithm identifier, nonce, ciphertext, authentication tag, AAD hash, created/activated/revoked/destroyed UTC, lease metadata, and reference status. AAD is canonical RFC 8785 UTF-8 over `{schema_version,environment,object_id,object_type,version,key_generation,provider_account_hash?,scope_hash?}`. Encryption uses a current authenticated-encryption construction supplied by the approved library/KMS; implementation records the exact algorithm/version and includes tamper/golden tests. Reusing a nonce/key pair is a Critical failure.

Gmail token objects bind exact `oauth_flow_id`, `mailbox_id`, provider account hash, scope hash, handle hash, object version, key generation, credential generation, expiry, and revocation state. `ActiveCredentialProofV1` is short-lived and signed over that exact tuple. Only a byte-matching DB-03 mailbox tuple permits token retrieval. A DB/secret mismatch denies, disables mailbox and both controls, and opens an incident.

### Rotation, revocation, deletion, and memory handling

- Access tokens refresh under a per-credential CAS lease; the old version remains decryptable only through the bounded in-flight overlap and is then revoked. Scope reduction revokes prior tokens at the earliest safe opportunity, consistent with Google's OAuth policy.
- Refresh-token/client/provider-key compromise: disable dependent capability and both send controls when Gmail is involved; revoke at provider; rotate KEK only if key exposure is suspected; reauthorize instead of copying a token.
- KEK rotation: create new generation, new writes use it, inventory and rewrap DEKs without decrypting payload outside KMS where possible, verify counts/tags, retire old generation only after sessions/flows/in-flight calls/backups are closed or rewrapped; unsubscribe verification/decryption generations additionally satisfy the non-shortenable 97-day post-last-issuance overlap.
- Signing/lookup key rotation uses versioned verification rings and bounded acceptance; emergency rotation revokes sessions/flows/manifests whose proof cannot be re-established. For public unsubscribe, exact `retention.policy.v1` rows apply: token expiry is at most 90 days after issue, and each signing-verification/decryption generation remains verify/decrypt-only for at least 97 days after its last issuance while retired for new minting. Missing coverage makes the public pair unavailable and product outreach false; compromise follows the emergency route-mode/recipient-remediation path rather than silently shortening validation for already issued tokens.
- Gmail flow expires after 10 minutes; replay/orphan evidence and GC use PROVIDER-01's exact 24-hour/CAS/DB-reference rules. A stuck resumable `IN_PROGRESS` saga is never deleted by age.
- Revocation marks first, denies new reads immediately, reconciles in-flight effects, then destroys ciphertext only when retention/incident/legal/reference holds permit. Product rows retain safe immutable proof hashes.
- Python code uses mutable byte buffers only where library APIs allow, avoids copies/string formatting, scopes decryption to the provider call, clears references/buffers in `finally`, disables core dumps, and never claims guaranteed physical zeroization. Isolation/short lifetime is the primary defense.

### Backup, restore, and emergency access

Encrypted secret-object backups contain ciphertext/metadata only and use a backup-specific key generation. KMS configuration and recovery material are exported only as provider-supported wrapped/escrow artifacts; two encrypted offline copies are held separately from the VPS/backups and inventoried quarterly. A single lost copy must not destroy recoverability; a single stolen copy must not decrypt without the second factor/provider control.

Quarterly clean restore proves: manifest/signature/hash; exact object versions/states/leases; DB mailbox proof linkage; no ACTIVE token for revoked mailbox; old key availability only as required; all restored sessions/flows revoked/expired; both controls false; and a token can be reauthorized when a key/object is intentionally unavailable. Restore never calls Gmail or providers. If keys are irrecoverable, preserve safe DB evidence, revoke provider grants, and reauthorize; never patch ciphertext or proof tuples.

### Absolute exclusion and redaction rules

Forbidden everywhere outside the secret call boundary: `Authorization`, `Cookie`, `Set-Cookie` values; OAuth code/state/nonce/PKCE; access/refresh/ID tokens; client secrets; API/DB/KMS keys; decrypted address/body/evidence or other PII; raw secret/ciphertext object; provider token/error response; environment/config dumps; or hashes of low-entropy secrets. Logging/telemetry/errors use only allowlisted enums, record UUIDs, versions/generations, safe provider/capability, and correlation. Tests use unmistakably fake canaries and assert absence in logs, traces, metrics, snapshots, exception chains, pytest output, build layers, Git, `.firecrawl`, Graphify, LLM prompts, and retained fixtures.

## Ordered implementation tasks

- [ ] **Implement the key/object contracts —** Input: secret classes, key hierarchy, canonical AAD, CAS/lease states. Operation: build strict models/ports and managed adapter with authenticated encryption and least workload identity. Output: versioned encrypted objects. Test evidence: tamper, nonce uniqueness, cross-purpose/environment/version denial. Failure behavior: secret read/write unavailable; capability off.
- [ ] **Implement Gmail credential lifecycle —** Input: PROVIDER-01 flow and ACTIVE tuple. Operation: exchange once, STAGE/ACTIVATE, bind proof, DB commit, refresh/rotate/revoke/GC under exact leases. Output: mailbox-scoped retrievable credential. Test evidence: six kill points, three strong reads, handler/bind/GC CAS races, mismatch. Failure behavior: no mailbox success/token access; both controls false on mismatch.
- [ ] **Apply exact access/redaction controls —** Input: workload, purpose, version and data-flow inventory. Operation: enforce allowlist/audit and run canary scans across every sink. Output: zero uncontrolled secret path. Test evidence: compromised agent/workflow/frontend/telemetry attempts. Failure behavior: deny, revoke, incident.
- [ ] **Implement rotation and emergency revoke —** Input: scheduled/compromise generation change. Operation: rewrap/verify/retire or revoke/provider-disable with bounded overlap. Output: current inventory and retired key proof. Test evidence: mid-call/mid-flow/mid-backup rotation and stolen generation. Failure behavior: dependent capability remains disabled.
- [ ] **Prove clean backup/restore —** Input: encrypted object/DB backups and separate recovery artifacts. Operation: restore isolated, verify linkage/invariants, revoke sessions/flows, and reauthorize one fake mailbox. Output: signed drill. Test evidence: missing/corrupt key/object/manifest variants. Failure behavior: do not start workers or enable controls.

## Test strategy

- **Crypto `test_envelope_aad_tamper_nonce_reuse_wrong_generation_and_cross_environment_fail_closed`.**
- **Access `test_agents_workflows_frontend_and_unrelated_adapters_cannot_read_or_list_secrets`.**
- **OAuth `test_active_credential_proof_and_db_tuple_are_required_for_exact_mailbox_token`.**
- **Lifecycle `test_refresh_rotation_revoke_gc_and_emergency_compromise_have_one_cas_winner`.**
- **Leak `test_secret_canaries_absent_from_every_output_sink_and_build_layer`.**
- **Restore `test_clean_restore_with_lost_and_corrupt_components_never_enables_or_calls_provider`.**

## Security, privacy, compliance, idempotency, observability, and cost

Google requires minimum necessary scopes and revocation when obsolete; exact approved Gmail use/policy is separately reviewed in SEC-04. Secret operations are idempotent by object/version/CAS and observable only through safe class/action/outcome/generation enums. Access audit and minimal metadata follow SEC-06. KMS/secret-manager operation and storage prices enter DB-05 `cost_entries` where attributable; alerts cover abnormal read/refresh/KMS volume without object/session/mailbox labels.

## Failure, rollback, and operator recovery

On leak/tamper/mismatch/unknown generation: deny access, disable the dependent capability and both send controls for Gmail, stop new provider work, revoke sessions/provider grants, rotate affected generations, preserve restricted evidence, and open a Critical incident. Roll back code/config but never revive a revoked object. Reconcile possibly called Gmail attempts before credential destruction. Restore only into isolation; use fresh authorization when proof is uncertain.

## Acceptance and retained evidence

- [ ] No token/secret/ciphertext exists in the 46 product tables, browser, log/error/telemetry, fixture, Graphify, prompt, Git, or image layer.
- [ ] Key hierarchy, object AAD/version/state, CAS/lease, access, rotation, revocation, GC, deletion, backup, and restore are executable.
- [ ] Exact PROVIDER-01/DB-03 Gmail saga and SEC-02 session contracts remain unchanged.
- [ ] Every credential read is exact-purpose, mailbox/version/generation bound, audited safely, and revocable.

Retain key/secret inventory without values, KMS/IAM policies, algorithm/library versions, canary scans, access-denial traces, OAuth kill/CAS matrices, rotation/revocation reports, provider revocation evidence, and clean backup/restore manifests.

## Dependencies and next deliverable

SEC-03 supplies the cryptographic boundary for [SEC-02](02-authentication-and-private-access.md), SEC-06, PROVIDER-01, and backups. Passing its M6 subset permits only operator-owned test-inbox credentials; real recipients still require [SEC-04](04-outreach-compliance.md), SEC-05, M1/M6, and separate bounded authority.
