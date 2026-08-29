# Security Threat Model and Control Closure

**Document ID:** SEC-01
**Status:** Planned M8 security gate; foundation logging, health checks, secret scanning, and outreach-off defaults exist, but none of the product security controls below is implemented
**Milestone:** M8 private-deployment gate, with Critical send/credential controls required before M6
**Owner:** Solo operator
**Prerequisites:** [ARCH-02](../01-architecture/02-module-boundaries.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), DB-01 through DB-06, WF-00 through WF-06, AGENT-01/10, PROVIDER-01/02, BACKEND-01 through BACKEND-06, and FRONTEND-09
**Outputs:** Asset/boundary inventory, actor and abuse-case catalog, Critical control-closure matrix, validation ownership, and residual-risk gate
**Unlocks:** M8 private deployment and the security evidence required by any later bounded M9 experiment
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Before any private deployment, every asset and trust boundary has an explicit threat owner, deterministic prevention or bounded detection, executable test, alert/evidence path, and disable/rollback/recovery action. Critical means one occurrence can disclose a credential or material personal data, cause an unauthorized/duplicate/suppressed send, corrupt authoritative history, defeat recovery, or spend beyond an approved bound. A Critical residual without a proven control keeps `TEST_INBOX_SENDING=false` and `PRODUCT_OUTREACH=false`.

The model uses [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/), the [OWASP 2025 GenAI risk catalog](https://genai.owasp.org/llm-top-10/), OWASP [SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html), [NIST SP 800-57 Part 1 Rev. 5](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final), [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final), [RFC 8785 JSON Canonicalization](https://www.rfc-editor.org/rfc/rfc8785), and [CISA SBOM resources](https://www.cisa.gov/topics/cyber-threats-and-advisories/sbom/sbomresourceslibrary) as engineering references, accessed 2026-08-29. They are not certifications or claims of conformance.

## Current repository state

Implemented today: structured request logs with sanitized route paths and request IDs, liveness/readiness checks, CI credential scanning, typed configuration, `OUTREACH_ENABLED=false`, and a minimal guarded send protocol. Missing: operator authentication, server sessions, product/Gmail OAuth, product tables/workflows/agents/providers, encryption/key management, hardened fetch egress, telemetry pipeline, incident automation, backups/restores, release provenance, security tests, and real send authority. Nothing currently sends email. All controls below are planned unless explicitly identified as current foundation behavior.

## Scope and non-goals

In scope: confidentiality, integrity, availability, privacy, send authority, durable replay, identity and Gmail OAuth, browser threats, untrusted evidence/model output, provider/supply-chain compromise, cost abuse, telemetry, backup/restore, operator mistakes, and recovery tooling.

Non-goals: public signup, teams/RBAC, multi-tenancy, public webhooks, autonomous remediation, agents making policy/compliance decisions, a claim of legal compliance, generic zero-trust branding, or accepting risk because the deployment has one user. A solo operator reduces identity complexity, not blast radius.

## Exact planned implementation surfaces

Create `security/threats.py`, `security/redaction.py`, `security/egress.py`, `security/invariants.py`, `security/release.py`, `tests/security/`, and versioned manifests under `security/manifests/`. Integrate only through existing owners: `OperatorSessionService`, `GmailOAuthSagaService`, `PolicyEvaluationService`, application `SendGateway`, `ControlCommandService`, `IncidentCommandService`, `RecoveryCommandService`, `RetentionCommandService`, provider ports, and the DB-05 audit/cost/event records. No threat control becomes a second writer or a new Gmail path.

### Assets, classification, and minimum invariant

| Asset | Class | Minimum invariant |
| --- | --- | --- |
| Google OIDC client secret, Gmail OAuth refresh/access tokens, state/PKCE/nonce material, encryption/signing/lookup keys | `SECRET` | never enters product tables, logs, errors, fixtures, Graphify, telemetry, prompts, browser storage, or backups without envelope encryption |
| Session/flow handles and cookies | `SECRET_TRANSIENT` | opaque, hashed for lookup, server-side state, bounded lifetime, rotation/revocation, never JavaScript-visible |
| Recipient address, name, reply/body, evidence capture, prompt input/output, provider payload | `RESTRICTED_PERSONAL` | least-use decryption in bounded memory; encrypted storage; no telemetry copy; policy-versioned retention |
| Suppression, consent/lawful-basis/jurisdiction evidence, legal review, approval basis, final `SEND` decision | `SAFETY_AUTHORITY` | immutable/versioned, exact identity/scope/hash, fresh at final SEND, never agent-authored authority |
| `send_intents`, `send_rate_reservations`, `send_attempts`, provider results/observations, RFC identity | `SIDE_EFFECT_EVIDENCE` | one mailbox-bound authority chain; ambiguity never retries; provider call only through `SendGateway` |
| 46 M2 product tables, domain/audit events, command results, workflow snapshots and RFC 8785 digests | `AUTHORITATIVE` | sole writer, atomic transition bundle, hash verification before consume/replay, restore invariant checks |
| Source/lockfiles/images/CI artifacts/SBOM/release manifest | `SUPPLY_CHAIN` | reviewed immutable inputs, pinned hashes, signed provenance, no unreviewed production promotion |
| Logs/traces/metrics/dashboards/alerts/evaluation captures | `OPERATIONAL_RESTRICTED` | allowlisted schema, bounded labels, no secret/PII, integrity and access evidence |
| Database/object/secret-store backups and offline recovery key | `RECOVERY_CRITICAL` | encrypted, separated keys, tested clean restore, restore cannot enable sends |

### Actors and trust boundaries

Actors are: the authenticated operator; an error-prone or compromised operator/browser; unauthenticated Internet attacker; malicious site/recipient/content author; compromised model/search/page/business/Gmail/OIDC provider; malicious dependency/build runner; runaway or prompt-injected agent; DBOS/Temporal replaying worker; compromised API/worker/telemetry process; and a recovery operator using stolen or stale evidence.

| Boundary | Allowed crossing | Denied by default |
| --- | --- | --- |
| browser -> FastAPI | opaque `__Host-` cookie for operator surfaces; exact public unsubscribe capability; Origin/fetch metadata/CSRF intent; generated 66-operation contract | tokens, arbitrary redirect, raw provider error, client authority, unknown operation |
| FastAPI -> Google OIDC | fixed issuer/client/redirect, state, nonce, PKCE S256, minimal identity scopes | Gmail scope, wildcard redirect, email-as-authorization, dynamic issuer |
| application -> versioned secret store/KMS | typed object ID/version/CAS/lease and ciphertext | plaintext token in PostgreSQL, config dump, broad list/read, agent/workflow access |
| application -> PostgreSQL | named sole-writer transactions over the frozen 46 product tables | provider/route/agent direct writes, raw secrets, direct SQL repair |
| workflow -> application | frozen command/input/result snapshots and RFC 8785 hashes | runtime history as business truth, re-executed external effect, unknown version |
| agent -> six provider capabilities | `model.complete_structured`, `evidence.read`, `search.query`, `page.extract`, `business.search`, `business.details` only | Gmail, `SendGateway`, credentials, state mutation, arbitrary network/tool |
| page/search/enrichment -> Internet | allowlisted scheme/domain, public-IP egress proxy, bounded bytes/time/type, redirect/DNS revalidation | loopback/private/link-local/metadata/file schemes, credential forwarding, DNS-rebinding result |
| `SendGateway` -> Gmail | one attempt-bound request after the exact 14-step BACKEND-04 order | blind retry, altered mailbox/RFC/basis, agent/workflow direct call |
| Google callback -> FastAPI | exact registered OIDC or Gmail callback parser and one-time flow | webhook-style generic payload, unsigned/unbound state, open redirect |
| app -> telemetry/alert sink | allowlisted privacy-safe schema over authenticated TLS | request/body/headers/token/address, unbounded labels, inbound control webhook |
| backup store -> isolated restore | encrypted immutable backup plus separate key and manifest | restore into live writers, restored enabled controls, unverified schema/hash chain |

No public webhook exists in the 66-operation manifest. The two public unsubscribe confirmation operations are a route-bound opaque capability: GET cannot mutate and only explicit POST reaches the observed-suppression transaction. Adding any webhook or other public operation is a new architecture/security review, not an implementation convenience.

### Threat and abuse-case control closure

| ID / threat | Severity | Deterministic prevention or bounded detection | Owner | Required test | Alert/evidence | Disable, rollback, recovery |
| --- | --- | --- | --- | --- | --- | --- |
| T01 prompt injection or poisoned evidence changes authority | Critical | fetched text is untrusted data; six-capability allowlist; strict output schemas; artifact validation/acceptance; agents never command, send, approve, suppress, or decide compliance | `AgentRunRecordingService` + `ArtifactValidationService` | direct/indirect injection, poisoned citation, tool-call, exfiltration fixtures across all 552 cases | hard-safety evaluation result and authority graph | reject artifact/config; rollback promotion; pause stage; both send controls remain false |
| T02 provider/model exfiltrates secrets or excess PII | Critical | prompt/data allowlists, minimization, no credentials in context, per-capability egress and provider contracts, DLP/redaction test, restricted vendor-use review | provider adapter owner + operator | canary-secret and PII-field negative tests for every capability | OBS-01 `security.authorization.denied`; provider ledger/capture manifest | disable provider/config; revoke exposed credential; purge prohibited copy; incident/counsel review |
| T03 OIDC/Gmail OAuth token, code, state, nonce, PKCE, or session theft/replay | Critical | SEC-02/03 exact opaque cookies, PKCE/state/nonce, subject allowlist, encrypted objects, one-time CAS, rotation, expiry, revocation; identity OAuth separated from Gmail OAuth | `OperatorSessionService` / `GmailOAuthSagaService` | fixation, callback replay, stolen previous handle, concurrent flow, six Gmail kill points, GC race | safe auth/OAuth audit, replay counters, session-generation evidence | revoke all sessions/tokens, rotate affected key generation, disable mailbox and both send controls, normal OIDC/bootstrap recovery only |
| T04 CSRF, XSS, session fixation, open redirect, enumeration | Critical | exact Origin + `Sec-Fetch-Site` + CSRF intent; CSP/no inline script; contextual escaping; fixed relative return allowlist; opaque uniform errors/timing; handle rotation | `OperatorSessionService` + FastAPI/frontend | cross-origin mutation/logout, stored/reflected XSS, malformed return, identifier sweep/timing | auth/security counter without target ID plus browser security-test evidence; no new report endpoint | revoke session generation; disable product mutations; rollback frontend/API; reauthenticate |
| T05 SSRF, DNS rebinding, redirect/protocol smuggling | Critical | dedicated egress resolver/proxy; HTTPS only; canonical host allowlist; resolve and reject non-public/loopback/private/link-local/multicast; pin/revalidate every redirect and connect IP; no auth header forwarding; size/type/time caps | page/search provider adapters | IPv4/IPv6 literals, mixed encodings, CNAME/TTL rebind, redirect to metadata/private, `file:`/`gopher:` | blocked-egress metric by bounded reason; safe source hash | disable capability/provider, quarantine captures/artifacts, rotate any exposed credential, incident |
| T06 webhook/callback abuse | Critical | only two exact Google callbacks; query union, method, issuer/redirect/state/flow binding, one-time claim, body rejection, rate limit; no public webhook | FastAPI callback handlers | extra field/body/method, error/code splice, state swap, oversized query, replay | callback-denial audit with flow hash/reason only | disable affected OAuth start; revoke/GC safe objects; rotate state/signing generation |
| T07 Gmail duplicate, ambiguous, cross-mailbox, or suppressed send | Critical | frozen 14-step order, composite FKs, one active mailbox rate lease, stable RFC ID, one provider call, result capture, ambiguity quarantine, authorized mailbox-only reconciliation; last-mile locked suppression | application `SendGateway` + `SendRecoveryService` | full kill matrix, concurrent winner, cross-mailbox/multiple match, suppression race, runtime replay | attempt/result/observation chain; ambiguity-age and duplicate/suppression-breach page | disable both controls, stop dequeue, reconcile; never retry ambiguity; typed repair only |
| T08 dependency/build/container/supply-chain compromise | Critical | lockfile hashes, least CI token permissions, secret scan, SBOM, vulnerability/license review, signed build provenance/image digest, protected promotion manifest, no mutable production tags | release owner (operator) | tampered lock/artifact/signature, malicious package fixture, rollback drill | retained SBOM/provenance/scans and release digest | block/rollback release by digest; rotate CI/runtime secrets; rebuild from clean base |
| T09 DBOS replay, Temporal replay, or version drift repeats effects/corrupts truth | Critical | M1 eight-item gate; workflow snapshot RFC 8785 verification; external calls outside replayed workflow body behind idempotent application command; stored result replay; Temporal mandatory after any DBOS disqualifier | workflow runtime adapter + application owner | crash at every command/step/provider boundary, version/patch/replay matrix | signed M1 bundle and workflow/command/result hashes | stop product workflow work; migrate to Temporal after a disqualifier; controls false; drain/version-route |
| T10 PostgreSQL, secret-store, backup loss/corruption or unsafe restore | Critical | encrypted backups, immutable manifest/hashes, separate key copy, daily restore verification, isolated restore, 46-table/invariant/event/send-chain checks, controls forced false | operator + `RetentionCommandService` | corrupt/missing key, point-in-time loss, full clean-server restore, unresolved attempt preservation | backup age/verification/restore report | stop writers/workers; restore isolated; rotate secrets; reconcile providers; enable nothing automatically |
| T11 operator error, insider mistake, or recovery tool overreach | Critical | one operator still uses reauth, previews, `If-Match`, idempotency, typed registered repair, before/after hashes, no SQL/free-form patch, two-stage high-harm confirmation, immutable audit | operator + `RecoveryCommandService` | stale tab/double click/wrong scope, malicious repair payload, lost laptop, emergency revoke | command/audit/repair chain and anomaly alert | emergency revoke; disable controls first; rollback config/code; isolated restore if truth uncertain |
| T12 resource, recipient-hash, or authorization enumeration | Critical | configured OIDC subject allowlist before resource lookup; generated route registry; uniform 404/403; UUIDs are not authority; query filters scoped after auth; deterministic SHA-256 recipient/address lookups are pseudonymous offline-enumerable residual risk, restricted to the internal lookup service under column privilege with no API/event/log/report/export field and encrypted volume/WAL/snapshot/backup storage | FastAPI auth dependency + query owners + `RecipientLookupKeyService` | anonymous/cross-subject, ID sweep, timing/body-size comparison, forged cookie, common-address offline dictionary and restricted-column query-rate fixtures | `ALERT_AUTHORIZATION_ENUMERATION` or `ALERT_RECIPIENT_HASH_ENUMERATION`; bounded denial/query-rate evidence with no resource/hash label; incident trigger `AUTHORIZATION_OR_ENUMERATION` or `RECIPIENT_HASH_ENUMERATION` | revoke sessions, take product API private/offline, revoke lookup access, preserve query audit, classify exposure with privacy/counsel, fix boundary, apply hold/retention/notification decision, and restore only verified access |
| T13 cost/token/call amplification or provider quota abuse | Critical | reservation before call, hard per-run/workflow/experiment/provider/currency caps, bounded tools/results/tokens/deadlines, cancellation, `cost_entries` reconciliation, no auto budget increase | `BudgetService` + `ProviderCostReconciliationService` | concurrency/replay, runaway loop, provider overcharge/missing receipt, FX outage | budget/cost reservation gap and max-cost alerts | stop provider calls/stage; disable controls if Gmail/reputation affected; reconcile invoice; rollback agent config |
| T14 log/trace/metric/eval/Graphify data leakage | Critical | OBS-01 exact allowlist/redaction; no bodies/headers/query/tokens/address/hash labels; synthetic fixtures; Graphify exclusions; secret/PII canaries; restricted sink | telemetry owner + evaluation owner | canary matrix across logs/errors/traces/metrics/fixtures/Graphify/prompts | zero-match scans and sink access audit | stop exporters/evals; revoke leaked material; delete/quarantine copy under retention/counsel; incident |
| T15 suppression/compliance/policy drift or stale cache authorizes send | Critical | uncached locked PostgreSQL suppression read at step 2/7; versioned policy/legal evidence; unknown fact denies; control enable grants no downstream authority | `SuppressionQueryService` + `PolicyEvaluationService` | create/deactivate race, stale cache, changed jurisdiction/consent/disclosure, approval replay | final `SEND` policy decision and denial/control metrics | disable `PRODUCT_OUTREACH`; create suppression; cancel unsent; counsel/policy review before re-enable |
| T16 monitoring blind spot or alert-path failure hides a Critical condition | Critical | telemetry self-health, local authoritative DB queries, two independent notification paths, synthetic canaries, no telemetry as product truth | operator/observability owner | drop exporter, full disk, clock skew, alert endpoint outage, DB-vs-dashboard mismatch | telemetry gap alert plus local incident record | controls false when safety visibility unavailable; use local read-only recovery; repair exporter after truth check |

Every T01-T16 condition is routed by OBS-02/OBS-05 through a closed `incident.catalog.v1` tuple of trigger code, runbook ID, alert ID, resolution code, and DB-05 repair kind. Missing, unknown, or cross-version values reject routing/replay and keep the safety condition open; free text and telemetry labels never select a repair. Residual High/Medium risks require an owner and expiry; no Critical risk may be accepted verbally. An operator risk acceptance is a signed, versioned artifact with scope, expiry, evidence, and compensating control, but cannot waive credential, privacy, suppression, duplicate-send, restore, Google-policy, or legal-review gates.

### Security source and claim discipline

- **Sourced standard/vendor rule:** cite the exact official page, version/update date when available, and access date.
- **Conservative Alon AI policy:** may be stricter than a source; label it as product policy and version it.
- **Technical enforcement:** name the service/table/command/test that denies or detects.
- **Evidence:** retain a reproducible manifest, trace, row/hash set, scan, or drill result; dashboard color is not evidence.
- **Legal-counsel decision:** recipient jurisdiction, legal basis/consent exception, disclosure text, direct-mail/database duties, transfer/retention, and breach notification remain counsel decisions. The system records them; agents never decide them.

## Ordered implementation tasks

- [ ] **Freeze the asset/boundary registry —** Input: all 46 product tables, security-runtime/session objects, provider/agent/Gmail/runtime/backup/telemetry surfaces. Operation: assign class, owner, allowed crossings, retention, and invariant; diff against import/call/data-flow graphs. Output: signed registry. Test evidence: every table, secret, side effect, and trust boundary maps exactly once. Failure behavior: M8 and affected M6 gate remain blocked.
- [ ] **Implement deterministic security boundaries —** Input: T01-T16. Operation: add auth, redaction, egress, envelope encryption, supply-chain, replay, budget, send, and restore controls through canonical owners. Output: deny-by-default paths. Test evidence: named tests in the closure table. Failure behavior: applicable capability/control stays disabled.
- [ ] **Build the Critical abuse corpus —** Input: attacker/provider/operator/replay/recovery cases. Operation: run security/integration/chaos tests with secret/PII canaries and exact call/write assertions. Output: signed results keyed to threat ID. Test evidence: each Critical row has a fresh pass. Failure behavior: open Critical incident and reject release.
- [ ] **Exercise disable and recovery —** Input: one simulated occurrence per Critical threat. Operation: disable, revoke/rotate, drain, reconcile, rollback, or restore using only typed commands/runbooks. Output: bounded recovery evidence. Test evidence: no blind send, SQL patch, stale authority, or automatic re-enable. Failure behavior: keep controls false and restore into isolation.
- [ ] **Review residual risk before every authority increase —** Input: current threat register, release/provider/policy/eval/restore evidence. Operation: recompute residuals and expiry; obtain counsel decisions where legal scope applies. Output: signed gate record. Test evidence: stale/missing evidence denial. Failure behavior: authority does not advance.

## Test strategy

- **Security `test_each_critical_threat_has_owner_prevention_or_detection_alert_test_and_recovery`:** machine-check the closure table/manifest.
- **Authority `test_only_sendgateway_can_call_gmail_and_only_canonical_owners_write_46_tables`:** static graph plus runtime spies.
- **Injection `test_untrusted_content_cannot_select_tool_authority_policy_or_send`:** all eight agents and six capabilities.
- **Browser `test_oidc_session_csrf_xss_fixation_replay_and_enumeration_matrix`:** SEC-02.
- **Egress `test_ssrf_dns_rebinding_redirect_and_protocol_matrix`:** no private connection.
- **Recovery `test_critical_incident_disable_revoke_reconcile_restore_requires_no_sql`:** clean-server drill.
- **Leak `test_canaries_absent_from_logs_traces_metrics_errors_fixtures_graphify_and_prompts`:** repository plus sink scan.
- **Supply chain `test_release_rejects_unpinned_unsigned_or_sbom_drift`:** artifact tamper cases.

## Security, privacy, compliance, idempotency, observability, and cost

Security controls carry `request_id`, correlation/causation, canonical record IDs, safe reason enums, and versions; never secret/PII. Repeated denial/recovery uses exact command idempotency. Security evidence follows SEC-06 holds/retention. Paid security tests and provider calls reserve cost first. Applicable legal rules are inputs to SEC-04/06 and do not become engineering claims of compliance.

## Failure, rollback, and operator recovery

On an unmodeled Critical symptom, immediately commit both send controls false, stop new provider/agent/dequeue work, revoke exposed session/OAuth/key generations, preserve restricted evidence, and open `incidents(CRITICAL)`. Determine authoritative state from PostgreSQL, secret-store versions, provider evidence, and signed release/backup manifests—not logs alone. Roll back by immutable release/config/promotion pointer; reconcile every possibly called Gmail attempt; restore only into isolation. Recovery uses registered `RepairIncident` kinds and exact before/after hashes; direct SQL, blind replay, or automatic enable is forbidden.

## Acceptance and retained evidence

- [ ] T01-T16 cover every named actor, asset, boundary, and required abuse case without an owner gap.
- [ ] Every Critical row has deterministic prevention or bounded detection, named owner/test/alert/evidence, and disable/rollback/recovery.
- [ ] Frozen 46-table, state/event, sole-writer, runtime gate, six-capability, OAuth, API/UI, approval/final-SEND, RFC 8785, and recovery contracts remain unchanged.
- [ ] No security document claims implementation, legal compliance, or production readiness without evidence.

Retain the signed registry/control matrix, threat tests, authority/egress graphs, canary scans, SBOM/provenance, auth/Gmail crash matrices, incident drills, backup/restore report, residual-risk decisions, counsel references, and control-state evidence.

## Dependencies and next deliverable

SEC-01 consumes the complete Task 1-5 architecture and is implemented through [SEC-02 private access](02-authentication-and-private-access.md), [SEC-03 secrets](03-secrets-and-oauth-token-security.md), [SEC-04 outreach compliance](04-outreach-compliance.md), [SEC-05 safety controls](05-suppression-budgets-and-kill-switch.md), [SEC-06 privacy](06-data-privacy-and-retention.md), and OBS-01 through OBS-05. Passing it unlocks only the M8 private-deployment security gate; real outreach still needs retained legal/policy authority and a separate bounded M9 enable decision.
