# Leads, Campaigns, Messages, Gmail Observations, and Replies

**Document ID:** DB-03
**Status:** Planned M2 schema; provider use blocked until M6
**Milestone:** M2 schema, M5 qualification, M6 operator-owned inbox sending
**Owner:** Solo operator
**Prerequisites:** [DB-01](01-core-data-model.md), [DB-02](02-experiment-and-offer-schema.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), and [risk gates](../00-product-strategy/03-risk-register-and-kill-criteria.md)
**Outputs:** Business identity, lead provenance, qualification, campaigns, approvals, messages, send intent/attempt ledger, provider observations, replies, suppression, and Gmail cursors
**Unlocks:** M5 lead workflow and M6 controlled Gmail/reply workflow
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

M2 defines the product records that make qualification and sending auditable. M5 may populate leads without sending. M6 may use operator-owned inboxes only after provider/policy/security prerequisites exist. Product outreach remains disabled until both M1 and M6 evidence gates pass; `READY_FOR_OUTREACH`, `QUALIFIED`, `APPROVED`, or a queued workflow never independently authorizes Gmail.

## Current repository state

Only typed Gmail-flavored DTOs and a minimal guarded `SendGateway` protocol exist. There is no Gmail adapter/OAuth/history sync, lead, business, campaign, approval, message, suppression, policy implementation, intent, attempt, provider observation, reply, cursor, or product send. Current configuration defaults outreach off.

## Scope and non-goals

In scope: deterministic identity/deduplication, provenance, canonical lead/campaign/message/approval states, immutable send identity, one-attempt ledger, ambiguous outcome evidence, suppression, replies, and cursor atomicity. Non-goals: harvested contact dumps, automatic identity merges, bulk blasts, direct agent/workflow Gmail access, blind retry, mutable sent content, provider IDs as primary keys, or real prospects before M9 authority.

## Exact planned implementation surfaces

Create `domain/leads.py`, `domain/messaging.py`, `domain/approvals.py`, `application/sending.py`, `application/gmail_sync.py`, `persistence/models/messaging.py`, repositories, and the M2 migration.

### Identity, qualification, campaign, and approval records

| Table | Required columns/keys | Required constraints/indexes | Owner/event |
| --- | --- | --- | --- |
| `businesses` | `business_id uuid PK`, `canonical_name`, `canonical_domain text null`, `country_code char(2)`, `identity_key text`, `identity_status text`, timestamps | unique `identity_key`; domain normalized when present; status `CONFIRMED/CONFLICT/ARCHIVED`; index domain | identity service; conflicts emit `lead.identity_conflict_detected.v1` on affected lead |
| `leads` | `lead_id uuid PK`, `experiment_id FK`, `business_id FK`, `state text`, `version bigint`, `discovery_source_ref text`, `suppression_entry_id uuid null`, timestamps | `state in ('DISCOVERED','RESEARCH_PENDING','RESEARCHED','QUALIFICATION_PENDING','QUALIFIED','DISQUALIFIED','SUPPRESSED','ARCHIVED')`; unique `(experiment_id,business_id)`; unique `(lead_id,version)`; indexes `(experiment_id,state)` and `business_id` | `LeadCommandService`; lead catalog events |
| `lead_assessments` | `assessment_id uuid PK`, `lead_id FK`, `criteria_version text`, `artifact_id uuid`, `score numeric`, `reason_codes text[]`, `gate_passed bool`, `content_hash`, `created_at` | unique `(lead_id,criteria_version,content_hash)`; `score between 0 and 1`; immutable | deterministic gate emits qualified/disqualified event |
| `campaigns` | `campaign_id uuid PK`, `experiment_id FK`, `campaign_version int`, `supersedes_campaign_id FK self null`, `state text`, `offer_id FK`, `policy_version text`, send/reply window, `daily_cap int`, `total_cap int`, timestamps | `state in ('DRAFT','READY','ACTIVE','PAUSED','COMPLETED','CANCELLED','FAILED')`; unique `(experiment_id,campaign_version)`; window/cap checks; only `ACTIVE` admits; terminal recovery creates a new ID/version linked to predecessor; immutable configuration per version | campaign command service |
| `campaign_members` | `campaign_id FK`, `campaign_version`, `lead_id FK`, `recipient_address_ciphertext bytea`, `recipient_address_hash text`, `status text`, timestamps, composite PK | unique `(campaign_id,campaign_version,lead_id)` and recipient hash; lead must be `QUALIFIED` at admission; `status in ('ELIGIBLE','REMOVED')` | deterministic admission service |
| `approvals` | `approval_id uuid PK`, `experiment_id FK`, `campaign_id FK null`, `lead_id FK null`, `message_id uuid null`, `scope_hash text`, `state text`, `artifact_version_refs jsonb`, `policy_version`, caps, `expires_at`, `operator_id FK null`, timestamps | `state in ('PENDING','APPROVED','DENIED','EXPIRED','REVOKED','CONSUMED')`; unique `scope_hash` among active approvals; exact-scope immutable; consumed at most once | approval service; approval catalog events |
| `suppression_entries` | `suppression_entry_id uuid PK`, `scope text`, `recipient_hash text null`, `business_id FK null`, `reason_code`, `source`, `active bool`, timestamps | exactly one of recipient/business/global scope; partial unique active target; index active hash/business | suppression service; `lead.suppressed.v1`/`send.suppressed.v1` |

### Message, attempt, provider, and reply records

| Table | Required columns/keys | Required constraints/indexes | Owner/event |
| --- | --- | --- | --- |
| `gmail_mailboxes` | `mailbox_id uuid PK`, `owner_operator_id FK operators`, `provider_account_hash text`, `mailbox_alias text`, `status text`, `authority_mode text`, timestamps | unique `provider_account_hash`; unique `mailbox_alias`; status `ACTIVE/DISABLED/REVOKED`; authority `TEST_INBOX_ONLY/PRODUCT_ELIGIBLE`; no OAuth token or address in logs | authenticated Gmail composition/control service; provider credentials remain outside product rows |
| `outreach_messages` | `message_id uuid PK`, `campaign_id FK`, `campaign_version`, `lead_id FK`, `artifact_id uuid`, `state text`, `version bigint`, `subject_ciphertext bytea`, `body_ciphertext bytea`, `content_hash`, `approval_id FK null`, timestamps | `state in ('DRAFT','APPROVAL_PENDING','APPROVED','SEND_INTENT_RECORDED','QUEUED','SENDING','AMBIGUOUS','RECONCILING','SENT','FAILED_RETRYABLE','FAILED_PERMANENT','SUPPRESSED','CANCELLED')`; unique `(campaign_id,campaign_version,lead_id,content_hash)`; unique `(message_id,version)`; no mutation after `SEND_INTENT_RECORDED`; indexes state/campaign | message command service |
| `send_intents` | `send_intent_id uuid PK`, `message_id FK unique`, `idempotency_key text`, `scope_hash`, `rfc_message_id text`, `max_attempts int`, `attempt_count int`, `retry_deadline`, `retry_policy_version`, `budget_reservation_id FK`, `created_at` | unique `idempotency_key`; unique `rfc_message_id`; positive bounded attempts; `attempt_count<=max_attempts`; immutable identity/retry fields | `SendGateway` application service; `send.intent_recorded.v1` |
| `send_attempts` | `send_attempt_id uuid PK`, `send_intent_id FK`, `attempt_number int`, `state text`, `policy_decision_id uuid`, `started_at`, `provider_called_at`, `completed_at`, `error_code null`, `retry_class null`, `reconciliation_strategy_version null` | unique `(send_intent_id,attempt_number)`; state `STARTED/AMBIGUOUS/RECONCILING/SENT/FAILED`; timestamp/state checks; index unresolved state | `SendGateway`/`SendRecoveryService`; send attempt/reconciliation/failure events |
| `provider_results` | `provider_result_id uuid PK`, `send_attempt_id FK`, `provider text`, `outcome text`, Gmail message/thread IDs null, `provider_timestamp null`, `response_fingerprint`, `captured_at`, `raw_payload_ref text null` | unique `(send_attempt_id,response_fingerprint)`; `outcome in ('ACCEPTED','REJECTED','UNKNOWN','RECONCILED_SENT','RECONCILED_ABSENT','CONFLICT')`; IDs required for accepted/reconciled sent; immutable | Gmail adapter result capture |
| `provider_observations` | `provider_observation_id uuid PK`, `mailbox_id FK gmail_mailboxes`, `gmail_message_id`, `gmail_thread_id`, `history_id text null`, `rfc_message_id text null`, `direction text`, `observed_at`, `payload_ref`, `fingerprint` | unique `(mailbox_id,gmail_message_id)`; unique `(mailbox_id,fingerprint)`; `direction in ('INBOUND','OUTBOUND')`; indexes thread/history | Gmail sync/reconciliation evidence |
| `replies` | `reply_id uuid PK`, `message_id FK`, `provider_observation_id FK unique`, `gmail_message_id`, `gmail_thread_id`, `received_at`, `classification_artifact_id uuid null`, `created_at` | unique Gmail identity through observation; index `(message_id,received_at)`; immutable | Gmail sync emits `reply.received.v1`; application later attaches classification |
| `gmail_history_cursors` | `mailbox_id uuid PK/FK gmail_mailboxes`, `history_id text`, `version bigint`, `advanced_at`, `last_observation_id FK provider_observations null` | optimistic `(mailbox_id,version)`; cursor advance transaction includes all observations/events | Gmail sync; `gmail.history_cursor_advanced.v1` |

Foreign keys to `artifacts`, `policy_decisions`, and event/audit records are added in DB-04/DB-05 in the same M2 revision chain. Cycles use deferrable constraints only when a single transaction genuinely creates both records.

### Send transition reconciliation

`outreach_messages.state` is the ARCH-03 message aggregate. `send_attempts.state` is ledger evidence, not a second message state machine. `SENDING -> AMBIGUOUS` commits `send.outcome_ambiguous.v1`; `AMBIGUOUS -> RECONCILING` commits `send.reconciliation_started.v1`; exactly one matching Sent observation permits `RECONCILING -> SENT` and `send.reconciled_as_sent.v1`. A conclusive absence after the configured window may produce `FAILED_RETRYABLE`; multiple matches, malformed identity, or operator stop produces `FAILED_PERMANENT`. `AMBIGUOUS` never requeues.

## Ordered implementation tasks

- [ ] **Migrate identity and lead records —** Input: canonicalization rules and ARCH-03 `LeadState`. Operation: create businesses/leads/assessments with uniqueness, conflict quarantine, and provenance. Output: deduplicated M5-ready schema. Test evidence: `test_concurrent_same_business_discovery_creates_one_lead`. Failure behavior: quarantine conflict; never auto-merge.
- [ ] **Migrate campaigns, approvals, and suppression —** Input: campaign/approval states and policy facts. Operation: create exact-scope/version records and fail-closed suppression indexes. Output: deterministic admission substrate. Test evidence: `test_suppression_overrides_qualification_and_approval`. Failure behavior: deny admission and audit reason.
- [ ] **Migrate message and send ledger —** Input: ARCH-03 message transitions. Operation: create immutable message content, intent identity, attempts, results, observations, replies, and cursor. Output: complete ambiguity chain. Test evidence: exhaustive PostgreSQL constraint and transition tests. Failure behavior: keep unresolved state operator-visible; disable send on impossible state.
- [ ] **Implement sole send transaction boundaries —** Input: approved message and current controls. Operation: commit intent/policy/budget/queue evidence, release transaction, call Gmail only through `SendGateway`, then record result or ambiguity. Output: auditable side effect. Test evidence: kill point before/after each boundary. Failure behavior: no blind retry; reconcile first.
- [ ] **Implement atomic history sync —** Input: mailbox cursor and provider page. Operation: deduplicate observations/replies, append events, then advance cursor in the same transaction. Output: lossless replayable sync. Test evidence: crash on every row/cursor boundary. Failure behavior: rollback page and fetch it again.

## Test strategy

- **Unit `test_message_transition_matrix_matches_arch03`:** all legal/illegal edges and events.
- **Constraint `test_one_intent_per_message_and_key`:** concurrent commands cannot duplicate intent.
- **Recovery `test_timeout_after_gmail_acceptance_reconciles_without_resend`:** stable RFC ID finds Sent evidence.
- **Recovery `test_multiple_sent_matches_require_operator_resolution`:** never guess which send won.
- **Integration `test_history_observations_events_cursor_commit_atomically`:** cursor cannot skip a reply.
- **Security `test_logs_and_events_exclude_decrypted_recipient_and_body`:** safe telemetry only.
- **Contract `test_only_send_gateway_invokes_gmail_send`:** import/call graph has one production caller.

## Security, privacy, compliance, idempotency, observability, and cost

Recipient addresses and message content are encrypted; normalized hashes support scoped dedupe/suppression without appearing in logs. Legal/compliance facts and approval versions are deterministic inputs; model prose cannot authorize send. The stable idempotency key and RFC Message-ID survive retries/restarts. Every provider call records policy, budget, correlation, attempt, result/ambiguity, and cost reference. Retention minimizes personal/message data while preserving safety evidence hashes and suppression requirements.

## Failure, rollback, and operator recovery

Global disable stops admission and dequeue before the next provider call. Campaign pause stops new calls but does not erase ambiguous evidence. Operator recovery compares message/intent/attempt, provider results, Sent observations, workflow history, and events; it resolves through an audited command, never direct SQL. Provider credential compromise disables provider and preserves restricted incident evidence. Schema rollback cannot remove unresolved attempts or active suppression.

## Acceptance and retained evidence

- [ ] Every lead/campaign/message/approval state uses ARCH-03 names exactly.
- [ ] Every workflow read/write maps to a table and named constraint here.
- [ ] One stable intent key, RFC Message-ID, bounded attempt ledger, result capture, and Sent reconciliation cover Gmail ambiguity.
- [ ] Agents and workflows cannot invoke Gmail or mutate these aggregates directly.
- [ ] Product outreach remains disabled until both M1 and M6 pass.

Retain constraint introspection, identity races, transition matrix, send kill-point traces, Sent reconciliation fixtures, cursor crash traces, suppression tests, encrypted-field/log scans, and provider call-path proof.

## Dependencies and next deliverable

DB-03 depends on DB-01/02, ARCH-03, DB-04 artifact references, and DB-05 policy/event/idempotency records. It unlocks [WF-04 lead qualification](../03-workflows/04-lead-qualification-workflow.md) and, only after all M6 gates, [WF-05 outreach/reply](../03-workflows/05-outreach-and-reply-workflow.md).
