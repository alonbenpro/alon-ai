# Data Privacy, Minimization, Rights, and Retention

**Document ID:** SEC-06
**Status:** Planned M8 privacy/retention gate; no product personal data, retention engine, rights workflow, legal hold, encrypted backup, or deletion operation exists today
**Milestone:** M8 private-deployment gate, with minimization required from M3 and Gmail personal-data handling required before M6
**Owner:** Solo operator; qualified legal counsel owns jurisdiction-specific obligations and retention approval
**Prerequisites:** DB-01 through [DB-06 complete 46-table retention manifest](../02-database/06-migrations-seeding-and-retention.md), DB-04 evidence, SEC-01/03/04/05, and OBS-01 through OBS-05
**Outputs:** Data inventory/purpose/minimization, exact retention-policy overlays, rights/deletion/export workflow, holds, transfer/vendor review, telemetry/evaluation/backups retention, and purge/restore evidence
**Unlocks:** M8 privacy gate and the privacy evidence required before any real-recipient collection/send
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Alon can explain what personal/sensitive data exists, why, where, who/provider can access it, its source and jurisdiction, how long each representation remains, what prevents unsafe deletion, and how a validated access/correction/deletion/objection request is executed without erasing suppression or send/recovery evidence. Raw sensitive data is shortest-lived; immutable safety records retain minimized hashes/IDs/reasons only under a current counsel-approved policy.

The official Israeli sources used are the [Privacy Protection Law national record](https://main.knesset.gov.il/Activity/Legislation/Laws/pages/lawprimary.aspx?lawitemid=2000234), [Amendment 13](https://www.gov.il/BlobFolder/reports/13_amendment/he/%D7%AA%D7%99%D7%A7%D7%95%D7%9F%2013%20-%20%D7%A4%D7%A8%D7%A1%D7%95%D7%9D%20%D7%91%D7%A1%D7%A4%D7%A8%20%D7%94%D7%97%D7%95%D7%A7%D7%99%D7%9D.pdf), PPA [Q&A](https://www.gov.il/he/pages/tikun13_qa?chapterIndex=6), [database registration/notice services](https://www.gov.il/he/service/registration_in_the_database), current [PPA legal-information catalog](https://www.gov.il/en/collectors/legalinfo?officeId=4aadba43-3d71-4e7c-a4fe-5bf47b723d4e), [PPA Data Security Regulations guide](https://www.gov.il/he/pages/data_security_guide?chapterIndex=19), and [EEA-to-Israel data regulations](https://www.gov.il/BlobFolder/legalinfo/datatransferredisrael2023/en/Privacy%20Protection%20Regulations%20%28Instructions%20for%20Data%20that%20was%20transferred%20to%20Israel%20from%20the%20European%20Economic%20Area%29.pdf), accessed 2026-08-29. English translations can be unofficial. Counsel must apply the authoritative Hebrew/current law and concrete facts; this file makes no compliance conclusion.

## Current repository state

There are no M2 product tables or real lead/message/evidence/OAuth/session records. Current logs are sanitized, CI scans secrets, and current fixtures/tests are synthetic. There is no data inventory, record of processing/purpose, encryption store, retention schedule, purge/redaction job, legal/incident hold, rights request, provider transfer record, DPA review, backup retention, or restored-data deletion propagation. DB-06 freezes five product retention classes and every one of the 46 tables, but exact live-data durations await this legal/privacy decision.

## Scope and non-goals

In scope: operator, business/lead/recipient, mailbox, message/reply, evidence/artifact/agent/provider, policy/consent/suppression, events/audit/cost, security sessions, logs/traces/metrics, evaluation fixtures/captures, secret objects, backups, source/provenance, cross-border providers, holds, rights validation/export/correction/deletion, and purge evidence.

Non-goals: indefinite raw-data retention because storage is cheap, deleting suppression and causing recontact, deleting immutable safety history without replacement minimum, exporting third-party/secret data to an unverified requester, using production PII in evaluation by default, copying raw evidence into logs/Graphify/prompts, claiming GDPR/Israeli compliance, or choosing a legal basis/retention period without counsel.

## Exact planned implementation surfaces

Create versioned `DataInventoryV1`, `RetentionPolicyV1`, `ProcessingPurposeV1`, `ProviderTransferReviewV1`, `DataRightsRequestV1`, `DataRightsEvidenceV1`, and `HoldRecordV1`; `privacy/inventory.py`, `privacy/redaction.py`, `application/retention.py`, `application/data_rights.py`, admin CLI/API projection only through the existing typed command/query architecture, and tests. `RetentionCommandService` remains the exclusive purge/redaction writer across all 46 product tables. Any future rights API must be added to the canonical API manifest; until then, verified requests are local authenticated operator commands, not an invented route.

### Data inventory, purpose, minimization, and provider boundary

| Data category | Purpose/minimum representation | Normal location and allowed consumer | Forbidden copy |
| --- | --- | --- | --- |
| operator identity/session | exact subject hash/operator/session lifecycle to authorize one operator | `operators`, SEC-02 security-runtime store; `OperatorSessionService` | email/claims/token in product/log/browser storage |
| business/lead/recipient | identity, qualification provenance, contact hash/encrypted address, jurisdiction/consent/suppression | DB-03 + restricted object; lead/policy/SendGateway owners | metric labels, Graphify, generic prompt, public UI |
| message/reply/Gmail observation | exact send/reconcile/reply evidence; encrypted bodies and minimized provider IDs/hashes | DB-03/restricted objects; SendGateway/history/reply owners | logs/traces/errors/eval fixtures/source repo |
| research evidence/artifact/agent | claims, content hashes, bounded capture refs, versions, evaluation | DB-04/restricted object; six capabilities/validators/operator | hidden reasoning, unnecessary page archive, credential/recipient spill |
| consent/legal/policy/suppression | prove or deny recipient authority and prevent recontact | accepted DB-04 evidence + DB-03 suppression + DB-05 decision/audit | model-authored truth, mutable overwrite, public report |
| credential/secret | authenticate provider/session and encrypt data | SEC-03 external versioned secret store/KMS | all 46 product tables, telemetry, prompts, backups unencrypted |
| event/audit/cost/recovery | reproduce state/authority/spend/incident safely | DB-05 minimized immutable records | full body/address/token/provider payload |
| telemetry/evaluation | operate and regress without product authority | OBS allowlisted sink; synthetic/redacted eval store | raw production payload, secret, high-cardinality pseudonymous labels |
| backups | recover exact authoritative/encrypted state | immutable encrypted backup store | same-host plaintext/key co-location, restored active sessions/controls |

Collection must have a registered purpose, minimum fields, source, sensitivity, recipient/country evidence, allowed consumers/providers, retention class/duration, and deletion/hold behavior before schema/provider promotion. Data cannot be repurposed merely because an agent can use it. `evidence.read` requires exact evidence ID/hash/max bytes and defaults `allow_restricted=false`; provider prompts receive only fields required by the specialist contract. No chain-of-thought is requested or stored.

Provider transfer review records entity/service/region, data classes/fields, purpose, retention/training/human-access/subprocessor terms, encryption/access controls, deletion/export capability, incident terms, Google restricted-scope obligations, jurisdiction transfer decision and counsel reference, contract/DPA version, review/expiry, and tested disable/export/delete path. Missing/expired review disables the provider for personal data. A vendor claim is evidence, not a legal conclusion.

### Exact retention policy overlay

DB-06 classes and the 46-table mapping remain canonical. `RetentionPolicyV1` supplies durations; it does not change class/table ownership. The following are conservative technical maximums for synthetic/private pilot data pending counsel; real-recipient collection/sending remains blocked until counsel approves or shortens each value and the provider/finance requirements. “After close” means every workflow/message/provider outcome is terminal/reconciled and no hold exists.

| Class/object | Planned maximum before purge/redaction | Minimum retained after payload removal | Blocking hold |
| --- | --- | --- | --- |
| `SENSITIVE_SHORT` raw recipient/message/reply/provider observation | active operational need, then 30 days after close | non-reversible recipient/content/provider identity hash, UTC, authority/suppression/incident refs | active suppression/consent dispute, unresolved send/reply, complaint, rights/legal/incident |
| raw `evidence_items`/captures | 30 days after acceptance/rejection or experiment close, whichever is later; 7 days for unused failed capture | content hash, source URI only if approved/minimized, retrieval/publication dates, redaction/deletion evidence | decision/gate/citation dispute, incident/legal hold |
| `BUSINESS_ACTIVE` | active experiment plus 12 months after terminal decision | decision/suppression/safety references and deletion evidence | active relationship/experiment, legal/rights/incident |
| `SAFETY_LONG` | 24 months after final terminal/reconciled event as the provisional product maximum | immutable minimized IDs/hashes/state/reason/time/policy/authority chain | unresolved ambiguity/incident, active suppression, counsel/accounting/legal hold |
| `EVALUATION_VERSIONED` promoted/comparison | promoted life plus 12 months; unused/superseded sensitive fixture payload 30 days | manifests/hashes/scores/config/provider ledger/cost evidence | active promotion/regression/incident |
| `RUNTIME_ENGINE` | 30 days after application terminal/reconciled and version migration proof | application workflow/event/snapshot hashes remain in product records | nonterminal run, replay/version incident |
| OIDC flow/session security-runtime | flow payload until 10-minute expiry then purge within 24 hours; terminated session detail 30 days | aggregate auth audit with subject/session safe IDs/reasons | auth incident/legal hold |
| Gmail secret objects | exact PROVIDER-01 10-minute flow/24-hour orphan rules; revoke/destroy token after mailbox revocation and reference/incident closure | safe DB-03 proof tuple/revocation evidence | handler/bind lease, `IN_PROGRESS`, mailbox/send/incident reference |
| ordinary application logs | 30 days; security incident subset copied into restricted evidence under hold | metrics/audit record, not raw log | incident/legal hold |
| authentication/access/control/incident and other applicable technical security records | 24 months in minimized DB audit/security evidence as the provisional floor reflected by PPA guidance on Data Security Regulations regulation 17; counsel classifies the actual database/security level and covered records | safe actor/operation/outcome/time/version/correlation and evidence hash, never token/body/address | incident/legal/regulatory hold |
| distributed traces | 7 days | SLO aggregates and retained incident trace manifest | incident hold |
| bounded metrics | 13 months to compare seasonality, only low-cardinality/non-PII | gate/SLO report hash | incident/audit evidence need |
| encrypted operational backups | 35 daily copies plus 12 monthly copies pending counsel; deletion propagates by expiry, not in-place mutation | backup manifest/deletion tombstone | disaster/legal/incident hold with reviewed expiry |

These are maximums, not minimum legal retention. Accounting invoices may require a different period; `cost_entries.provider_invoice_ref` and finance evidence must receive an explicit counsel/accountant schedule without extending provider prompts, recipient bodies, or tokens. Until real-data policy approval, use synthetic/owned aliases only. A missing duration blocks collection/send and automated purge job activation; it does not justify indefinite raw retention.

### Holds, purge/redaction, and restored data

Hold precedence is legal/regulator, incident/security, unresolved provider/send, active suppression/opt-out, rights dispute, decision/gate, dependency/reference, then normal expiry. Holds have exact target scope, reason enum, authority/reference, created/expiry/review, and immutable audit. They cannot be silently permanent; expired holds require review, not automatic release when risk remains.

`RetentionCommandService` plans a purge graph from the DB-06 FK manifest, snapshots row/count/hash references, redacts restricted payload/object first, inserts deletion evidence/tombstone, then purges only after all downstream references can preserve the minimum. Batches are idempotent and cursor/version bound. Active suppression persists as a recipient hash even after contact/address deletion. Domain/audit/send/repair history is never rewritten to pretend an action did not occur.

Backups are immutable: deletion is recorded in live truth and applied immediately after restore before workers/read access. Expired backups age out under the schedule. Every restore runs the deletion-tombstone replay, forces controls false, revokes sessions/flows, and validates no purged secret/payload becomes operationally accessible.

### Rights and verified operator procedure

Receipt channel is published in the privacy notice but does not become an unauthenticated product endpoint. Alon logs a local `DataRightsRequestV1`, verifies requester identity using the minimum appropriate evidence and a channel independent of the disputed address where proportionate, scopes jurisdiction/request without overcollection, and records deadlines/counsel reference. Unknown or impersonated requests expose nothing.

Search uses exact identity mappings and address hashes in a restricted process. Export is encrypted, time-limited, access-logged, and reviewed to exclude other persons, internal security secrets, privileged material, and provider data not authorized for disclosure. Correction creates a new version/event where records are mutable by design; immutable history is annotated/superseded, not overwritten. Deletion/objection invokes suppression first when marketing is involved, then retention redaction/purge under holds. Completion evidence contains counts/classes/hash/timestamps/reasons, not a new copy of the data. Counsel decides applicability, identity standard, exceptions, deadlines, and regulator notifications.

### Notices, transfers, incidents, and policy change

Before real data, publish a clear operator/business privacy notice covering identity/contact, data/source/purpose, providers/transfers, retention, rights/complaints, security contact and version/effective date, reviewed by counsel. The Google OAuth in-product disclosure is separate and immediately precedes consent as Google's policies require. A policy/source/vendor/region/purpose/schema change creates a new inventory/notice/transfer/retention version and blocks affected collection/provider/send until reviewed.

Potential personal-data breach follows OBS-05. Engineering records detection/scope/containment/evidence; Israeli and recipient-jurisdiction notification thresholds/timing/content are counsel/regulator decisions. Never state “not reportable” from severity alone.

## Ordered implementation tasks

- [ ] **Build complete data/purpose/provider inventory —** Input: 46 tables, security-runtime/secret/telemetry/eval/backup objects and six/Gmail providers. Operation: map fields/class/source/purpose/consumer/region/transfer/retention/deletion. Output: signed `DataInventoryV1`. Test evidence: schema/provider/log/prompt diff has no orphan field. Failure behavior: affected collection/provider/send blocked.
- [ ] **Approve retention and notices —** Input: provisional schedule, recipient jurisdictions, provider/accounting needs. Operation: obtain counsel/accountant decisions, publish/version notices, and freeze `RetentionPolicyV1`. Output: executable durations/holds. Test evidence: every class/table/object has exactly one policy. Failure behavior: no real data/send.
- [ ] **Implement idempotent hold/redact/purge —** Input: DB-06 graph, object store, expiry/holds/tombstones. Operation: redact then purge in bounded batches and replay after restore. Output: minimized records and deletion evidence. Test evidence: FK/hold/crash/retry/restore matrix across all 46 tables. Failure behavior: stop batch; preserve data safely and alert, never partial-reference deletion.
- [ ] **Implement verified rights workflow —** Input: authenticated/scoped request. Operation: search, review, encrypted export, versioned correction, suppression-first deletion/objection, and evidence. Output: completed/denied/escalated request. Test evidence: impersonation, mixed-person, held/immutable, backup propagation. Failure behavior: expose/delete nothing until resolved.
- [ ] **Exercise privacy incident and provider exit —** Input: canary leak or expired provider review. Operation: disable, inventory affected data, revoke access, export/delete provider copy, counsel escalation, and evidence. Output: bounded containment. Test evidence: provider/traces/backups/prompts/evals. Failure behavior: capability/control stays off.

## Test strategy

- **Inventory `test_every_persisted_transmitted_logged_prompted_evaluated_and_backed_up_field_has_purpose_class_owner_and_retention`.**
- **Manifest `test_all_46_product_tables_keep_db06_class_and_retention_writer`.**
- **Purge `test_retention_batch_is_idempotent_fk_safe_hold_aware_and_preserves_suppression_minimum`.**
- **Restore `test_deleted_payload_cannot_reappear_or_enable_after_backup_restore`.**
- **Rights `test_verified_export_correction_deletion_and_objection_exclude_other_person_and_secret_data`.**
- **Leak `test_restricted_canaries_absent_from_logs_traces_metrics_graphify_prompts_and_synthetic_evals`.**
- **Transfer `test_expired_or_changed_provider_review_blocks_personal_data_egress`.**

## Security, privacy, compliance, idempotency, observability, and cost

Privacy is enforced by minimization, encryption, purpose/access allowlists, provider review, versioned retention and audited rights—not a legal-compliance claim. Purge/rights commands are authenticated, expected-versioned and idempotent. Telemetry records class/count/duration/outcome/reason, never target identity. Storage/KMS/egress/provider/legal costs are recorded without retaining personal data merely to explain cost.

## Failure, rollback, and operator recovery

On unknown purpose/retention, hold conflict, partial purge, identity doubt, reappearing restored data, provider exit failure, or leak: stop affected processing/provider/send, preserve minimal evidence, create incident, and seek counsel. Roll back code/policy for future jobs but never restore deleted payload into live use. Resume only after invariant/count/hash and rights/hold review; direct SQL deletion and manual object removal without tombstone are forbidden.

## Acceptance and retained evidence

- [ ] Every table/object/signal/prompt/provider/backup has purpose, class, source, owner, access, region/transfer, retention and deletion behavior.
- [ ] All 46 DB-06 table classes/sole writer remain exact and provisional durations are replaced/approved before real data.
- [ ] Rights, holds, suppression minimum, immutable correction, purge, backup expiry and restored deletion are executable.
- [ ] Official rule, product policy, technical control, evidence, and counsel decision remain separate; no compliance claim is made.

Retain inventory/purpose/transfer/notice/retention versions, official sources/access dates, counsel/accountant references, access/purge/hold/tombstone manifests, rights verification/export/deletion evidence, provider exit proofs, canary scans, backup-expiry/restore reports, and privacy incident exercises.

## Dependencies and next deliverable

SEC-06 consumes DB-06 and supplies privacy constraints to every Task 6 file. Passing it unlocks the M8 privacy/retention gate only. Real outreach still requires [SEC-04](04-outreach-compliance.md), SEC-05, M1/M6 and a separate bounded M9 authority record.
