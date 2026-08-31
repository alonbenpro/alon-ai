# Incident Response, Recovery, and Solo-Operator Runbooks

**Document ID:** OBS-05
**Status:** Planned M8 incident capability; no product incidents/repairs, alert routes, credential revoke tooling, recovery dashboard, backup restore, or exercised runbook exists today
**Milestone:** M6 send incident subset, M7 recovery UI, M8 private operations gate
**Owner:** Solo operator; legal counsel/provider/regulator support joins when the incident facts require it
**Prerequisites:** SEC-01 through SEC-06, OBS-01 through OBS-04, DB-01/03/05/06, WF-05/06, PROVIDER-01/02, BACKEND-02/04/05/06, and FRONTEND-09
**Outputs:** Severity/trigger model, preparation/detection/containment/eradication/recovery protocol, exact runbooks, communications/legal escalation, evidence handling, exercises, and post-incident gates
**Unlocks:** M8 incident/restore evidence and bounded M9 operations
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

One operator can detect, stop harm, preserve trustworthy evidence, determine authoritative state, revoke/rotate, reconcile, restore, communicate/escalate, and recover without direct SQL or blind provider replay. The first safe action is explicit and rehearsed for every Critical threat. Recovery never automatically re-enables either send control or upgrades earned authority.

The lifecycle is informed by [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final), published April 2025 and accessed 2026-08-29. It is adapted for one operator and is not a claim of NIST conformance. Legal notification duties/timelines are facts-and-jurisdiction decisions by counsel/regulators, not inferred from technical severity.

## Current repository state

There is no implemented `incidents` or `repair_actions` table/service, severity classifier, incident command/API/UI, page channel, evidence bundle, forensic access, credential/session emergency revoke, control signal, recovery command, backup/restore automation, contact roster, legal/provider playbook, exercise, or postmortem. Current health/logging can expose foundation failure only. Every runbook below is planned.

## Scope and non-goals

In scope: cyber/privacy/compliance/provider/send/cost/runtime/database/backup/telemetry/operator/supply-chain incidents; severity/roles; detection/triage; immediate kill/revoke; evidence; authoritative reconciliation; typed repair; isolated restore; legal/provider communication decision; exercises; and lessons/re-enable.

Non-goals: a staffed SOC/on-call claim, autonomous LLM incident commander, deleting/altering evidence, direct SQL repair, generic webhook-controlled remediation, blind resend, public disclosure without authorization/counsel, treating logs as truth, or marking resolved because alerts stopped.

## Exact planned implementation surfaces

Use canonical `incidents(severity INFO|LOW|MEDIUM|HIGH|CRITICAL; state OPEN|MITIGATING|RESOLVED)` and `repair_actions`; owners remain `IncidentCommandService` and authenticated `RecoveryCommandService`. Use exact `incident.opened.v1` and `incident.resolved.v1`; do not invent acknowledged/contained domain states. Operational steps/timestamps live in append-only audit/restricted evidence and OBS-01 `incident.operation.completed`.

Create `incidents/contracts.py`, `application/incidents.py`, `application/recovery.py`, local `alon-ai incident`/`alon-ai recovery` commands, safe runbook registry, evidence bundler, notification adapter, `/recovery` projections/registered commands from the frozen API, and tests. No external sender/provider can call repair endpoints.

### Closed incident, alert, runbook, resolution, and repair catalogs

`IncidentCatalogV1` has literal version `incident.catalog.v1` and byte-matches DB-01/05 checks. `IncidentTriggerCode`, `AlertId`, `RunbookId`, `IncidentResolutionCode`, and `RepairActionKind` are extra-forbid closed enums in application, OpenAPI, audit, OBS-01 attributes and PostgreSQL; no free-form fallback/`OTHER` exists. The Critical threat routing table is exact:

| SEC-01 threat | Incident severity | Trigger code | Alert ID | Runbook |
| --- | --- | --- | --- | --- |
| T01 | `CRITICAL` | `AGENT_PROMPT_INJECTION_OR_POISONING` | `ALERT_AGENT_INJECTION` | `IR-06` |
| T02 | `CRITICAL` | `PROVIDER_EXFILTRATION` | `ALERT_PROVIDER_EXFILTRATION` | `IR-06` |
| T03 | `CRITICAL` | `AUTH_OR_SECRET_COMPROMISE` | `ALERT_CREDENTIAL_OR_SESSION` | `IR-03` |
| T04 | `CRITICAL` | `WEB_SESSION_BOUNDARY_ATTACK` | `ALERT_WEB_BOUNDARY` | `IR-05` |
| T05 | `CRITICAL` | `SSRF_OR_DNS_REBINDING` | `ALERT_EGRESS_SSRF` | `IR-05` |
| T06 | `CRITICAL` | `CALLBACK_ABUSE` | `ALERT_CALLBACK_ABUSE` | `IR-05` |
| T07 | `CRITICAL` | `SEND_AUTHORITY_VIOLATION` | `ALERT_SEND_AUTHORITY_VIOLATION` | `IR-01` |
| T08 | `CRITICAL` | `SUPPLY_CHAIN_COMPROMISE` | `ALERT_SUPPLY_CHAIN` | `IR-09` |
| T09 | `CRITICAL` | `WORKFLOW_REPLAY_OR_VERSION_DRIFT` | `ALERT_WORKFLOW_REPLAY` | `IR-07` |
| T10 | `CRITICAL` | `DATASTORE_OR_RESTORE_FAILURE` | `ALERT_BACKUP_RESTORE` | `IR-08` |
| T11 | `CRITICAL` | `OPERATOR_OR_RECOVERY_ERROR` | `ALERT_OPERATOR_REPAIR` | `IR-13` |
| T12 | `CRITICAL` | `AUTHORIZATION_OR_ENUMERATION` | `ALERT_AUTHORIZATION_ENUMERATION` | `IR-05` |
| T13 | `CRITICAL` | `COST_OR_QUOTA_RUNAWAY` | `ALERT_COST_QUOTA` | `IR-10` |
| T14 | `CRITICAL` | `TELEMETRY_PRIVACY_LEAK` | `ALERT_TELEMETRY_PRIVACY` | `IR-04` |
| T15 | `CRITICAL` | `COMPLIANCE_OR_SUPPRESSION_BREACH` | `ALERT_COMPLIANCE_SUPPRESSION` | `IR-12` |
| T16 | `CRITICAL` | `TELEMETRY_OR_ALERT_BLINDNESS` | `ALERT_TELEMETRY_BLINDNESS` | `IR-11` |
| operational | `HIGH` | `GMAIL_AMBIGUITY_STALE` | `ALERT_GMAIL_AMBIGUITY` | `IR-02` |
| T12 restricted-hash branch | `CRITICAL` | `RECIPIENT_HASH_ENUMERATION` | `ALERT_RECIPIENT_HASH_ENUMERATION` | `IR-04` |

Those 18 rows are the complete four-field `IncidentRouteV1` registry and byte-match DB-01. Severity is part of immutable route identity: it is never selected by a caller, patched after insert, or inferred independently from another valid label. `NotificationEscalationV1={incident_route,pager_level,condition_version,for_duration}` is the separate operational projection; for example the immutable `HIGH` Gmail-ambiguity incident may notify at `SEV2` after 60 seconds and escalate paging to `SEV1` after 15 minutes without changing the incident row. Every OBS-02 alert rule names exactly one full route.

Resolution codes are exactly `MITIGATED_NO_LOSS|RECONCILED_SENT|RECONCILED_NOT_SENT|CREDENTIALS_REVOKED_ROTATED|CLEAN_RESTORE_VERIFIED|CODE_CONFIG_ROLLED_BACK|DATA_REMOVED_REMEDIATED|PROVIDER_COUNSEL_CLOSED|FALSE_POSITIVE_VERIFIED|RESIDUAL_RISK_ACCEPTED_WITH_EXPIRY`. Applicability is closed, not merely enum membership:

| Resolution code | Exact applicable trigger set / extra condition |
| --- | --- |
| `MITIGATED_NO_LOSS`, `FALSE_POSITIVE_VERIFIED` | all 18 triggers |
| `RECONCILED_SENT`, `RECONCILED_NOT_SENT` | `SEND_AUTHORITY_VIOLATION`, `GMAIL_AMBIGUITY_STALE` |
| `CREDENTIALS_REVOKED_ROTATED` | `PROVIDER_EXFILTRATION`, `AUTH_OR_SECRET_COMPROMISE`, `WEB_SESSION_BOUNDARY_ATTACK`, `CALLBACK_ABUSE`, `SUPPLY_CHAIN_COMPROMISE` |
| `CLEAN_RESTORE_VERIFIED` | `DATASTORE_OR_RESTORE_FAILURE` |
| `CODE_CONFIG_ROLLED_BACK` | `AGENT_PROMPT_INJECTION_OR_POISONING`, `PROVIDER_EXFILTRATION`, `WEB_SESSION_BOUNDARY_ATTACK`, `SSRF_OR_DNS_REBINDING`, `CALLBACK_ABUSE`, `SUPPLY_CHAIN_COMPROMISE`, `WORKFLOW_REPLAY_OR_VERSION_DRIFT`, `OPERATOR_OR_RECOVERY_ERROR`, `COST_OR_QUOTA_RUNAWAY`, `TELEMETRY_OR_ALERT_BLINDNESS` |
| `DATA_REMOVED_REMEDIATED` | `PROVIDER_EXFILTRATION`, `TELEMETRY_PRIVACY_LEAK`, `COMPLIANCE_OR_SUPPRESSION_BREACH`, `RECIPIENT_HASH_ENUMERATION` |
| `PROVIDER_COUNSEL_CLOSED` | `PROVIDER_EXFILTRATION`, `COST_OR_QUOTA_RUNAWAY`, `COMPLIANCE_OR_SUPPRESSION_BREACH`, `RECIPIENT_HASH_ENUMERATION` |
| `RESIDUAL_RISK_ACCEPTED_WITH_EXPIRY` | severity only `INFO|LOW|MEDIUM`, and trigger only `AGENT_PROMPT_INJECTION_OR_POISONING`, `SSRF_OR_DNS_REBINDING`, `SUPPLY_CHAIN_COMPROMISE`, `WORKFLOW_REPLAY_OR_VERSION_DRIFT`, `OPERATOR_OR_RECOVERY_ERROR`, `AUTHORIZATION_OR_ENUMERATION`, `COST_OR_QUOTA_RUNAWAY`, `TELEMETRY_OR_ALERT_BLINDNESS` |

Everything not listed rejects. Residual-risk acceptance is non-waivable for all HIGH/CRITICAL incidents and for provider exfiltration, credential/session, web-boundary/callback, send authority/Gmail ambiguity, datastore/restore, telemetry privacy, compliance/suppression/Google-policy/legal-review, and recipient-hash-enumeration triggers at every severity. DB-01 enforces both the exact 18 trigger/alert/runbook tuples and this applicability table; application routing performs the same versioned check before command claim.

Repair kinds are exactly `RECONCILE_GMAIL_ATTEMPT|ABORT_OAUTH_SAGA|REVOKE_OPERATOR_SESSIONS|DISABLE_MAILBOX|ROTATE_SECRET_GENERATION|REPAIR_WORKFLOW_PROJECTION|REPAIR_EVENT_OUTBOX_LINK|RESTORE_FROM_VERIFIED_BACKUP|REAPPLY_RECIPIENT_SUPPRESSION|REPLAY_RETENTION_TOMBSTONE|RECONCILE_PROVIDER_COST|IMPORT_OFFLINE_INCIDENT_JOURNAL|ROLLBACK_AGENT_PROMOTION`. Each maps one-to-one to a typed handler, prerequisite set, allowed before/after schema, inverse/recovery behavior and compatible runbooks. Unknown catalog/version/code, code/runbook/alert mismatch, caller-supplied label, or replay with changed code is rejected before DB write/notification/repair. A v2 catalog uses additive DB checks, dual readers and a versioned migration fixture; v1 rows never mutate.

### Severity, paging, ownership, and objectives

Operational pager levels map to canonical DB severity, never replace it:

| Pager / DB severity | Criteria/examples | Response objective | Default authority action |
| --- | --- | --- | --- |
| `SEV0` / `CRITICAL` | unauthorized/duplicate/suppressed/wrong-mailbox/post-disable real send; confirmed credential/large PII leak; unrecoverable/corrupted authority; recovery tool abuse; active compromise | acknowledge immediately, containment command <=5m | both controls false; stop external/dequeue work; revoke/rotate as applicable |
| `SEV1` / `HIGH` | ambiguous send >15m, OAuth DB/secret mismatch, DB/runtime invariant, backup/restore failure, cost overrun, telemetry safety blindness >5m, provider/Google complaint | acknowledge <=15m, contain <=30m | affected capability off; product control false; often both controls false |
| `SEV2` / `MEDIUM` | repeated dependency/agent/workflow failure without side-effect uncertainty, retention/rights job failure before deadline, alert-channel degradation with backup path | same operator day | pause affected stage/provider; preserve capacity/evidence |
| `SEV3` / `LOW\|INFO` | isolated expected denial, nonurgent drift/maintenance evidence | weekly review | no authority increase; schedule correction |

The operator is incident commander, technical responder, evidence custodian and communications coordinator, but performs roles sequentially using checklists. At SEV0/SEV1, prioritize containment over diagnosis, then take a timestamped snapshot and contact the applicable external owner: VPS/DB/secret/provider support, Google Workspace, security specialist, insurer, accountant, or Israeli/recipient-jurisdiction counsel. Store contact methods offline. Primary page plus independent out-of-band notification must not depend on Alon AI Gmail credentials.

### Universal response protocol and evidence bundle

1. **Detect and open:** verify alert against a local authoritative query when safe; call `IncidentCommandService` with canonical severity/trigger, correlation and affected experiment. If DB unavailable, start a signed offline incident journal and import a reference after restore—never fabricate prior DB state.
2. **Contain:** execute the runbook's exact control disable/process/queue/network/provider/session/token action. A DB control commit precedes worker signal where DB is available. Preserve ambiguity; do not cancel a possibly called attempt.
3. **Preserve:** record trusted UTC/source/clock state, release/image/config/policy/promotion/key generations, control versions, relevant record/event/snapshot/hash sets, provider IDs, telemetry gaps, commands and operator actions. Encrypt/sign the bundle; exclude unnecessary PII/secret and never place it in Git/Graphify/normal logs.
4. **Scope and authoritative reconciliation:** compare PostgreSQL 46-table facts/events/audit/idempotency/outbox/cost, workflow runtime, secret-store versions/leases, Gmail/provider observations, release/SBOM and backups. Logs/traces are hints only. Mark unknown explicitly.
5. **Eradicate:** revoke/rotate, patch/rollback release/config/promotion/policy, remove malicious dependency/provider/data, repair access/egress/alert path. No in-place history edits.
6. **Recover:** use canonical commands, exact idempotency/versions and registered repair kinds with before/after hashes; or clean isolated restore. Reconcile every possible Gmail call and outstanding cost before workers. Sessions/flows revoked and controls false after restore.
7. **Validate and resolve:** run threat-specific regression plus full affected gate, verify dashboards against DB, monitor a bounded soak, record `incident.resolved.v1` with resolution/evidence. “Resolved” does not enable.
8. **Learn/re-authorize:** within five business days for Critical/High, write blameless factual post-incident review, control/test/runbook change, residual risk/expiry, counsel/provider actions and smaller/equal re-enable proposal. Operator separately executes any allowed enable.

Evidence bundle manifest is RFC 8785 canonical and signed: incident/severity/trigger, created/source UTC and clock evidence, scope/time range, collector/release/config hashes, included artifact IDs/hashes/classes, redactions, chain/custody access, commands/control/key/provider actions, gaps, and signature key generation. Never store active credentials, raw cookies/tokens, full recipient lists/bodies, hidden reasoning, privileged legal advice, or raw environment. Legal counsel decides preservation/privilege/disclosure.

### Exact Critical/High runbooks

| Runbook / trigger | First containment | Authoritative diagnosis/evidence | Eradication and recovery gate |
| --- | --- | --- | --- |
| IR-01 unauthorized/duplicate/suppressed/wrong-mailbox/post-disable send | commit both controls false; stop dequeues; do not revoke Gmail until possibly called outcomes are captured unless active theft requires it | exact approval basis/intent/final `SEND`/rate/attempt/result/observation/control versions, RFC/mailbox chain and provider Sent search only in authorized account | reconcile all attempts, suppress affected targets, revoke/reauthorize if compromised, BACKEND-04 full kill/race suite, counsel/provider/recipient remediation decision; new smaller/equal gate |
| IR-02 ambiguous Gmail outcome | product and relevant test control false; retain consumed rate lease; start mailbox-only reconciliation; never retry or create a replacement intent | immutable intent/attempt/fresh decision/lease, direct result, authorized Sent observations/cursor/runtime crash point | exactly one match -> canonical sent; zero/multiple/cross/malformed evidence retains permanent quarantine; 300 seconds is investigation escalation only; no unresolved ambiguity before re-enable |
| IR-03 OIDC/session/Gmail/provider secret compromise | revoke session epoch/affected OAuth/provider grants, disable mailbox/providers/both send controls, rotate exposed generations | session/flow/object access audit, subject/key generations, DB mailbox proof, provider account activity, safe canary | normal OIDC/reauthorization, exact DB/secret consistency, stolen-handle/token negative tests, SEC-02/03 rotation/restore proof |
| IR-04 privacy/telemetry/prompt/evaluation data leak | stop exporter/provider/eval/access path, revoke credential if present, preserve minimum restricted copy, product off if recipient data/authority affected | data inventory/purpose/provider/region/access, canary locations, sink/backups, affected subjects/records/times | delete/quarantine/rotate, vendor exit, SEC-06 rights/retention and leak scans; counsel decides notification/remediation and re-enable |
| IR-05 SSRF/DNS rebinding/XSS/CSRF/callback exploit | isolate product ingress/egress, revoke sessions/flows, disable affected provider and both controls when authority uncertain | proxy/DNS/connect evidence, request/callback safe IDs, session/command/audit/provider calls and release | fix allowlist/resolve/redirect/CSP/Origin/parser, rotate, full security matrix and clean deployment |
| IR-06 prompt injection/data poisoning/provider exfiltration | disable candidate/active config and provider; pause affected workflows; controls false if outreach artifacts/decisions affected | input/evidence/artifact/provider ledger/config/promotion hashes and authority graph; no raw malicious content in normal log | quarantine sources/artifacts, rollback promotion/provider, rerun all affected 552 cases/security gates, revalidate accepted artifacts before resume |
| IR-07 DB/runtime corruption or replay/version mismatch | stop API writes/workers/dequeues, controls false, snapshot volumes/logical evidence | 46-table constraints/events/commands/outbox/snapshots/digests vs DBOS/Temporal history and provider evidence | typed repair if provable; otherwise isolated restore; M1/workflow crash/version suite; Temporal migration after DBOS disqualifier |
| IR-08 backup/key loss or failed restore | stop destructive maintenance/writers; preserve surviving backups/keys; controls false | backup/key/manifest/signature/age/catalog, restore logs and last known DB/provider state | restore clean isolated, reconcile provider/cost, revoke sessions, rotate/re-authorize lost keys, full invariant/restore proof |
| IR-09 supply-chain/release compromise | stop rollout/workers/external egress, controls false, revoke CI/deploy/runtime credentials | SBOM/lock/provenance/image digest/build runner/IAM/release diff and runtime indicators | rebuild from clean signed source/base, remove dependency, rotate, security/eval/workflow/restore tests, deploy immutable digest |
| IR-10 cost/quota runaway | stop affected provider/stage; product off if Gmail/reputation; keep reservations/evidence | provider call/result/usage/price/FX/cost/invoice and replay/concurrency chain | reconcile honestly, rollback config, fix limits, exact cost/eval suite; never raise cap to resolve |
| IR-11 telemetry/alert blindness | if send-safety gap >5m, both controls false; use local read-only authoritative queries; repair independent page path | collector/export/drop/disk/clock/cert/access plus DB-to-sink count comparison | clean telemetry config, canary/page and count reconciliation, bounded soak; no historical “all clear” inference |
| IR-12 complaint/unsubscribe/legal/Google-policy change | product control false; stop recipient/campaign; create/retain suppression; preserve communication | recipient policy/consent/source/disclosure/suppression/send/reply/provider evidence and current official sources | counsel/provider review, remediation, new policy/template/approval/cohort; never rely on prior M1/M6/control |
| IR-13 operator/recovery tooling error | disable controls, halt repair, revoke operator sessions if compromise suspected | command/idempotency/before-after/repair/audit/session/release evidence | revert via registered inverse/new repair or isolated restore; reauth and recovery-tool security test; no SQL patch |

Every runbook names `Owner: Solo operator`, links the exact alert and commands, declares safe prerequisites/stop conditions, and has a quarterly test. If the listed first action is unavailable, use the next lower layer: DB control command -> stop worker/dequeue process -> provider OAuth revoke/network egress block. Record which layer succeeded; process kill never rewrites product truth.

### Communications, legal/regulatory, and privacy decisions

Only the operator sends external incident communications, using pre-reviewed templates and counsel/provider guidance. Technical severity does not decide notification. For a possible personal-data breach, direct-marketing complaint, recipient-jurisdiction issue, regulator request, or Google policy/credential incident, contact qualified counsel promptly with the minimum encrypted evidence and record the scoped advice reference. Counsel decides applicable Israeli/foreign authority or data-subject notice, deadlines/content, privilege, preservation, and whether law enforcement/insurer is involved.

Status messages are factual: what is known/unknown, affected service/data/time, containment, safe action, next update. Never speculate, admit legal liability, expose another recipient, include tokens/credentials, or claim compliance/no impact without evidence. Provider support ticket IDs and sanitized exports are retained; provider assertions are corroborated.

### Exercises, readiness, and re-enable

Before M6, exercise IR-01/02/03/12 using owned aliases and every Gmail/OAuth kill point. Before M8, exercise all IR-01..13, including lost laptop, DB unavailable control fallback, corrupt backup/key, compromised dependency, sink outage, cost runaway, privacy canary and unavailable counsel/provider channel. Quarterly rotate through all Critical runbooks; clean restore at least every 90 days; contact/channel test quarterly.

An exercise passes only with fresh timestamps, deterministic first action, no uncontrolled provider call/data leak, complete authoritative reconciliation, signed evidence, tested alert/backup channel, typed recovery/no SQL, controls false after restore, and recorded improvement owner/date. Tabletop discussion alone is insufficient for executable paths.

Re-enable checklist: incident canonical `RESOLVED`; evidence signed; root cause and scope credible; credentials/releases/config/policies/promotions repaired; no unresolved Gmail/cost/rights/holds; affected tests/gates pass; telemetry/alerts/backups current; counsel/provider decisions complete; exact control expected version/reason/evidence; cohort/cap no larger without new earned authority. Enable remains a separate BACKEND-05 command and creates no work.

## Ordered implementation tasks

- [ ] **Implement incident/evidence contracts —** Input: canonical states/events/severity/triggers and secure evidence schema. Operation: open/mitigate/audit/bundle/sign/resolve through sole owners. Output: authoritative incident record. Test evidence: idempotency/concurrency/tamper/redaction/DB-unavailable journal import. Failure behavior: remain OPEN/off.
- [ ] **Implement containment and recovery commands —** Input: IR-01..13 exact first actions and record evidence. Operation: disable/stop/revoke/rotate/reconcile/rollback/restore via canonical services. Output: bounded harm and typed recovery. Test evidence: inject every unavailable-layer/crash/replay variant. Failure behavior: fall to lower containment layer; never improvise SQL/send.
- [ ] **Wire alerts/contacts/communications —** Input: OBS-02 alerts, offline contacts and counsel/provider templates. Operation: page safe IDs, acknowledge/escalate, record external decisions/references. Output: actionable one-operator coordination. Test evidence: primary/out-of-band/provider/counsel channel outage. Failure behavior: local incident/control fallback.
- [ ] **Exercise all runbooks —** Input: clean test environment/owned aliases/synthetic canaries/backups. Operation: run executable scenarios with signed timeline/evidence and independent invariant checks. Output: M6/M8 readiness bundle. Test evidence: IR-01..13 matrix and 90-day restore. Failure behavior: milestone blocked.
- [ ] **Implement post-incident and re-enable gate —** Input: resolved incident, root cause, fixes/tests/evidence/current policies. Operation: record review/actions/residual risk and separately evaluate exact enable. Output: lessons and bounded eligibility. Test evidence: missing/stale/larger-cohort/automatic-enable denials. Failure behavior: controls false.

## Test strategy

- **Coverage `test_every_sec01_critical_threat_maps_to_alert_incident_runbook_owner_test_evidence_and_recovery`.**
- **Catalog `test_incident_trigger_resolution_repair_runbook_and_alert_v1_are_closed_db_checked_and_routed`:** exact 18 positive routes, cross-pair trigger/alert/runbook negatives, every positive resolution applicability arm, inapplicable trigger/resolution negatives, non-waivable and HIGH/CRITICAL residual-risk negatives, resolution/repair lists, unknown/replay rejection and v1-to-v2 migration fixture.
- **Cardinality `test_incident_telemetry_uses_only_catalog_version_severity_trigger_runbook_alert_resolution_and_repair_kind`:** no record ID, recipient hash or free text becomes a metric label.
- **State `test_incident_uses_only_open_mitigating_resolved_and_exact_arch03_events`.**
- **Containment `test_each_runbook_first_action_stops_new_harm_when_db_worker_provider_or_alert_layer_fails`.**
- **Gmail `test_incident_never_cancels_or_retries_possibly_called_attempt_before_reconciliation`.**
- **Evidence `test_bundle_is_canonical_signed_minimized_access_audited_and_tamper_evident`.**
- **Restore `test_clean_restore_revokes_sessions_forces_controls_false_replays_deletions_and_calls_no_provider`.**
- **Legal `test_technical_severity_cannot_auto_decide_notification_or_compliance`.**
- **Reenable `test_resolved_alert_or_passing_m1_m6_never_automatically_enables_or_expands_authority`.**

## Security, privacy, compliance, idempotency, observability, and cost

Incident access is strongest private operator authentication/reauth plus exact CSRF/version/idempotency. Evidence is encrypted/minimized/signed and held under SEC-06/counsel; normal telemetry contains safe IDs/enums only. Incident commands/costs correlate end-to-end. Emergency containment is not delayed for cost, but provider/support/legal/restore spend is recorded and does not auto-increase budgets.

## Failure, rollback, and operator recovery

This document defines failure handling. When state/evidence cannot be proven, choose containment and unknown—not optimistic resolution. Roll back immutable release/config/promotion/policy pointers; revoke/rotate exposed authority; reconcile providers; restore isolated if needed. `RecoveryCommandService` executes only registered repairs with exact before/after hashes. Direct SQL, deleted history, blind replay/send, unsourced legal conclusion, or automatic enable invalidates the incident exercise and keeps the gate closed.

## Acceptance and retained evidence

- [ ] IR-01..13 cover every Critical threat/failure with first action, authority sources, owner, tests, evidence, external escalation and recovery.
- [ ] Canonical incident states/events/writers and typed repair/no-SQL rules remain exact.
- [ ] One operator can receive an independent alert, contain through layered fallbacks, reconcile, restore, communicate and recover.
- [ ] Legal notification/compliance decisions are counsel-owned and distinct from technical severity.
- [ ] Exercises and re-enable evidence are fresh, executable, signed, and never expand authority automatically.

Retain runbook registry/versions, offline contact-test records, safe alert payloads, incident/event/audit/repair rows, signed evidence/timelines/access logs, provider/counsel reference records, containment/revoke/rotation/reconcile traces, IR-01..13 exercises, post-incident actions, restore reports, residual-risk decisions, and re-enable denials/command evidence.

## Dependencies and next deliverable

OBS-05 closes Task 6 operational response and feeds later testing/infrastructure/launch documents. Passing its exercises unlocks only the M8 incident gate. A real M9 experiment still requires every security/privacy/compliance/eval/restore gate and a separate bounded authority command.
