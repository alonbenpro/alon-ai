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

### Exact DDL-equivalent lead, campaign, mailbox, and message contract

```sql
CREATE TABLE businesses (
    business_id uuid NOT NULL,
    canonical_name text NOT NULL,
    canonical_domain text NULL,
    country_code char(2) NOT NULL,
    identity_key char(64) NOT NULL,
    identity_status text NOT NULL DEFAULT 'CONFIRMED',
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_businesses PRIMARY KEY (business_id),
    CONSTRAINT uq_businesses_identity_key UNIQUE (identity_key),
    CONSTRAINT ck_businesses_country CHECK (country_code ~ '^[A-Z]{2}$'),
    CONSTRAINT ck_businesses_identity_key CHECK (identity_key ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_businesses_identity_status CHECK (identity_status IN ('CONFIRMED','CONFLICT','ARCHIVED')),
    CONSTRAINT ck_businesses_domain CHECK (canonical_domain IS NULL OR canonical_domain = lower(canonical_domain))
);
CREATE INDEX ix_businesses_domain ON businesses (canonical_domain) WHERE canonical_domain IS NOT NULL;

CREATE TABLE leads (
    lead_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    business_id uuid NOT NULL,
    state text NOT NULL DEFAULT 'DISCOVERED',
    version bigint NOT NULL DEFAULT 1,
    discovery_source_ref text NOT NULL,
    suppression_entry_id uuid NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_leads PRIMARY KEY (lead_id),
    CONSTRAINT fk_leads_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_leads_business FOREIGN KEY (business_id) REFERENCES businesses (business_id) ON DELETE RESTRICT,
    CONSTRAINT uq_leads_experiment_business UNIQUE (experiment_id, business_id),
    CONSTRAINT uq_leads_id_version UNIQUE (lead_id, version),
    CONSTRAINT ck_leads_state CHECK (state IN ('DISCOVERED','RESEARCH_PENDING','RESEARCHED','QUALIFICATION_PENDING','QUALIFIED','DISQUALIFIED','SUPPRESSED','ARCHIVED')),
    CONSTRAINT ck_leads_version CHECK (version > 0),
    CONSTRAINT ck_leads_suppression CHECK ((state = 'SUPPRESSED') = (suppression_entry_id IS NOT NULL))
);
CREATE INDEX ix_leads_experiment_state ON leads (experiment_id, state);
CREATE INDEX ix_leads_business ON leads (business_id);

CREATE TABLE lead_assessments (
    assessment_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    criteria_version text NOT NULL,
    artifact_id uuid NOT NULL,
    score numeric(8,7) NOT NULL,
    reason_codes text[] NOT NULL,
    gate_passed boolean NOT NULL,
    content_hash char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_lead_assessments PRIMARY KEY (assessment_id),
    CONSTRAINT fk_lead_assessments_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE RESTRICT,
    CONSTRAINT uq_lead_assessments_inputs UNIQUE (lead_id, criteria_version, content_hash),
    CONSTRAINT ck_lead_assessments_score CHECK (score BETWEEN 0 AND 1),
    CONSTRAINT ck_lead_assessments_reasons CHECK (cardinality(reason_codes) > 0),
    CONSTRAINT ck_lead_assessments_hash CHECK (content_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_lead_assessments_lead_created ON lead_assessments (lead_id, created_at DESC);

CREATE TABLE gmail_mailboxes (
    mailbox_id uuid NOT NULL,
    owner_operator_id uuid NOT NULL,
    oauth_flow_id uuid NOT NULL,
    provider_account_hash char(64) NOT NULL,
    granted_scope_hash char(64) NOT NULL,
    credential_handle_hash char(64) NOT NULL,
    credential_version integer NOT NULL,
    credential_key_version text NOT NULL,
    credential_activation_generation bigint NOT NULL,
    mailbox_alias text NOT NULL,
    status text NOT NULL DEFAULT 'DISABLED',
    authority_mode text NOT NULL DEFAULT 'TEST_INBOX_ONLY',
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    revoked_at timestamptz NULL,
    CONSTRAINT pk_gmail_mailboxes PRIMARY KEY (mailbox_id),
    CONSTRAINT fk_gmail_mailboxes_operator FOREIGN KEY (owner_operator_id) REFERENCES operators (operator_id) ON DELETE RESTRICT,
    CONSTRAINT uq_gmail_mailboxes_oauth_flow UNIQUE (oauth_flow_id),
    CONSTRAINT uq_gmail_mailboxes_account_hash UNIQUE (provider_account_hash),
    CONSTRAINT uq_gmail_mailboxes_credential UNIQUE (credential_handle_hash, credential_version),
    CONSTRAINT uq_gmail_mailboxes_alias UNIQUE (mailbox_alias),
    CONSTRAINT ck_gmail_mailboxes_hashes CHECK (provider_account_hash ~ '^[0-9a-f]{64}$' AND granted_scope_hash ~ '^[0-9a-f]{64}$' AND credential_handle_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_gmail_mailboxes_credential_version CHECK (credential_version > 0 AND credential_activation_generation > 0 AND credential_key_version ~ '^[a-z0-9][a-z0-9._-]{0,63}$'),
    CONSTRAINT ck_gmail_mailboxes_status CHECK (status IN ('ACTIVE','DISABLED','REVOKED')),
    CONSTRAINT ck_gmail_mailboxes_authority CHECK (authority_mode IN ('TEST_INBOX_ONLY','PRODUCT_ELIGIBLE')),
    CONSTRAINT ck_gmail_mailboxes_revoked CHECK ((status = 'REVOKED') = (revoked_at IS NOT NULL))
);
CREATE INDEX ix_gmail_mailboxes_operator_status ON gmail_mailboxes (owner_operator_id, status);

CREATE TABLE campaigns (
    campaign_version_id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    campaign_version integer NOT NULL,
    experiment_id uuid NOT NULL,
    supersedes_campaign_version_id uuid NULL,
    state text NOT NULL DEFAULT 'DRAFT',
    offer_id uuid NOT NULL,
    policy_version text NOT NULL,
    send_window_start timestamptz NOT NULL,
    send_window_end timestamptz NOT NULL,
    reply_window_end timestamptz NOT NULL,
    daily_cap integer NOT NULL,
    total_cap integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_campaigns PRIMARY KEY (campaign_version_id),
    CONSTRAINT fk_campaigns_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_campaigns_offer FOREIGN KEY (offer_id) REFERENCES offer_hypotheses (offer_id) ON DELETE RESTRICT,
    CONSTRAINT fk_campaigns_supersedes FOREIGN KEY (supersedes_campaign_version_id) REFERENCES campaigns (campaign_version_id) ON DELETE RESTRICT,
    CONSTRAINT uq_campaigns_logical_version UNIQUE (campaign_id, campaign_version),
    CONSTRAINT uq_campaigns_experiment_version UNIQUE (campaign_id, campaign_version, experiment_id),
    CONSTRAINT uq_campaigns_version_scope UNIQUE (campaign_version_id, campaign_id, campaign_version),
    CONSTRAINT ck_campaigns_version CHECK (campaign_version > 0),
    CONSTRAINT ck_campaigns_state CHECK (state IN ('DRAFT','READY','ACTIVE','PAUSED','COMPLETED','CANCELLED','FAILED')),
    CONSTRAINT ck_campaigns_windows CHECK (send_window_start < send_window_end AND send_window_end <= reply_window_end),
    CONSTRAINT ck_campaigns_caps CHECK (daily_cap > 0 AND total_cap > 0 AND daily_cap <= total_cap)
);
CREATE INDEX ix_campaigns_experiment_state ON campaigns (experiment_id, state, updated_at DESC);
CREATE INDEX ix_campaigns_logical_latest ON campaigns (campaign_id, campaign_version DESC);

CREATE TABLE campaign_members (
    campaign_member_id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    campaign_version integer NOT NULL,
    lead_id uuid NOT NULL,
    recipient_address_ciphertext bytea NOT NULL,
    recipient_address_hash char(64) NOT NULL,
    status text NOT NULL DEFAULT 'ELIGIBLE',
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    removed_at timestamptz NULL,
    CONSTRAINT pk_campaign_members PRIMARY KEY (campaign_member_id),
    CONSTRAINT fk_campaign_members_campaign_version FOREIGN KEY (campaign_id, campaign_version) REFERENCES campaigns (campaign_id, campaign_version) ON DELETE RESTRICT,
    CONSTRAINT fk_campaign_members_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE RESTRICT,
    CONSTRAINT uq_campaign_members_lead UNIQUE (campaign_id, campaign_version, lead_id),
    CONSTRAINT uq_campaign_members_authority UNIQUE (campaign_member_id, campaign_id, campaign_version, lead_id),
    CONSTRAINT uq_campaign_members_recipient UNIQUE (campaign_id, campaign_version, recipient_address_hash),
    CONSTRAINT ck_campaign_members_hash CHECK (recipient_address_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_campaign_members_status CHECK (status IN ('ELIGIBLE','REMOVED')),
    CONSTRAINT ck_campaign_members_removed CHECK ((status = 'REMOVED') = (removed_at IS NOT NULL))
);
CREATE INDEX ix_campaign_members_campaign_status ON campaign_members (campaign_id, campaign_version, status);

CREATE TABLE outreach_messages (
    message_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    campaign_version integer NOT NULL,
    campaign_member_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    mailbox_id uuid NOT NULL,
    artifact_id uuid NOT NULL,
    state text NOT NULL DEFAULT 'DRAFT',
    version bigint NOT NULL DEFAULT 1,
    subject_ciphertext bytea NOT NULL,
    body_ciphertext bytea NOT NULL,
    content_hash char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_outreach_messages PRIMARY KEY (message_id),
    CONSTRAINT fk_outreach_messages_campaign_authority FOREIGN KEY (campaign_id, campaign_version, experiment_id) REFERENCES campaigns (campaign_id, campaign_version, experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_outreach_messages_member_authority FOREIGN KEY (campaign_member_id, campaign_id, campaign_version, lead_id) REFERENCES campaign_members (campaign_member_id, campaign_id, campaign_version, lead_id) ON DELETE RESTRICT,
    CONSTRAINT fk_outreach_messages_lead FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE RESTRICT,
    CONSTRAINT fk_outreach_messages_mailbox FOREIGN KEY (mailbox_id) REFERENCES gmail_mailboxes (mailbox_id) ON DELETE RESTRICT,
    CONSTRAINT uq_outreach_messages_mailbox UNIQUE (message_id, mailbox_id),
    CONSTRAINT uq_outreach_messages_authority UNIQUE (message_id, experiment_id, campaign_id, campaign_version, lead_id, mailbox_id),
    CONSTRAINT uq_outreach_messages_send_authority UNIQUE (message_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, mailbox_id),
    CONSTRAINT uq_outreach_messages_content UNIQUE (campaign_id, campaign_version, lead_id, content_hash),
    CONSTRAINT uq_outreach_messages_id_version UNIQUE (message_id, version),
    CONSTRAINT ck_outreach_messages_state CHECK (state IN ('DRAFT','APPROVAL_PENDING','APPROVED','SEND_INTENT_RECORDED','QUEUED','SENDING','AMBIGUOUS','RECONCILING','SENT','FAILED_RETRYABLE','FAILED_PERMANENT','SUPPRESSED','CANCELLED')),
    CONSTRAINT ck_outreach_messages_version CHECK (version > 0),
    CONSTRAINT ck_outreach_messages_hash CHECK (content_hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_outreach_messages_campaign_state ON outreach_messages (campaign_id, campaign_version, state);
CREATE INDEX ix_outreach_messages_mailbox_state ON outreach_messages (mailbox_id, state);

CREATE TABLE approvals (
    approval_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    campaign_version integer NOT NULL,
    campaign_member_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    message_id uuid NOT NULL,
    mailbox_id uuid NOT NULL,
    scope_schema_version integer NOT NULL,
    scope_hash char(64) NOT NULL,
    state text NOT NULL DEFAULT 'PENDING',
    artifact_version_refs jsonb NOT NULL,
    artifact_version_refs_hash char(64) NOT NULL,
    eligibility_policy_decision_id uuid NOT NULL,
    eligibility_policy_scope text NOT NULL DEFAULT 'APPROVAL_ELIGIBILITY',
    eligibility_policy_version text NOT NULL,
    eligibility_facts_hash char(64) NOT NULL,
    eligibility_policy_allowed boolean NOT NULL DEFAULT true,
    max_send_count integer NOT NULL DEFAULT 1,
    expires_at timestamptz NOT NULL,
    operator_id uuid NULL,
    reason_code text NULL,
    requested_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    decided_at timestamptz NULL,
    CONSTRAINT pk_approvals PRIMARY KEY (approval_id),
    CONSTRAINT fk_approvals_experiment FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_approvals_campaign_version FOREIGN KEY (campaign_id, campaign_version) REFERENCES campaigns (campaign_id, campaign_version) ON DELETE RESTRICT,
    CONSTRAINT fk_approvals_message_authority FOREIGN KEY (message_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, mailbox_id) REFERENCES outreach_messages (message_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, mailbox_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT fk_approvals_operator FOREIGN KEY (operator_id) REFERENCES operators (operator_id) ON DELETE RESTRICT,
    CONSTRAINT uq_approvals_send_basis UNIQUE (approval_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, scope_hash),
    CONSTRAINT uq_approvals_eligibility_authority UNIQUE (approval_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, eligibility_policy_decision_id, eligibility_policy_scope, eligibility_policy_version, scope_hash, eligibility_facts_hash, eligibility_policy_allowed),
    CONSTRAINT ck_approvals_state CHECK (state IN ('PENDING','APPROVED','DENIED','EXPIRED','REVOKED','CONSUMED')),
    CONSTRAINT ck_approvals_scope CHECK (scope_schema_version > 0 AND scope_hash ~ '^[0-9a-f]{64}$' AND artifact_version_refs_hash ~ '^[0-9a-f]{64}$' AND eligibility_facts_hash ~ '^[0-9a-f]{64}$' AND jsonb_typeof(artifact_version_refs) = 'object'),
    CONSTRAINT ck_approvals_eligibility CHECK (eligibility_policy_scope = 'APPROVAL_ELIGIBILITY' AND eligibility_policy_allowed),
    CONSTRAINT ck_approvals_cap CHECK (max_send_count = 1),
    CONSTRAINT ck_approvals_expiry CHECK (expires_at > requested_at),
    CONSTRAINT ck_approvals_decision CHECK ((state = 'PENDING' AND operator_id IS NULL AND decided_at IS NULL) OR (state <> 'PENDING' AND reason_code IS NOT NULL AND decided_at IS NOT NULL))
);
CREATE UNIQUE INDEX uq_approvals_active_scope ON approvals (mailbox_id, scope_hash) WHERE state IN ('PENDING','APPROVED');
CREATE INDEX ix_approvals_message_state ON approvals (message_id, state);

CREATE TABLE suppression_entries (
    suppression_entry_id uuid NOT NULL,
    scope text NOT NULL,
    recipient_hash char(64) NULL,
    business_id uuid NULL,
    reason_code text NOT NULL,
    source text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    version bigint NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    deactivated_at timestamptz NULL,
    CONSTRAINT pk_suppression_entries PRIMARY KEY (suppression_entry_id),
    CONSTRAINT fk_suppression_entries_business FOREIGN KEY (business_id) REFERENCES businesses (business_id) ON DELETE RESTRICT,
    CONSTRAINT uq_suppression_entries_id_version UNIQUE (suppression_entry_id, version),
    CONSTRAINT ck_suppression_entries_scope CHECK (scope IN ('GLOBAL','BUSINESS','RECIPIENT')),
    CONSTRAINT ck_suppression_entries_target CHECK ((scope = 'GLOBAL' AND recipient_hash IS NULL AND business_id IS NULL) OR (scope = 'BUSINESS' AND recipient_hash IS NULL AND business_id IS NOT NULL) OR (scope = 'RECIPIENT' AND recipient_hash ~ '^[0-9a-f]{64}$' AND business_id IS NULL)),
    CONSTRAINT ck_suppression_entries_active CHECK ((active AND deactivated_at IS NULL) OR (NOT active AND deactivated_at IS NOT NULL)),
    CONSTRAINT ck_suppression_entries_version CHECK (version > 0)
);
CREATE UNIQUE INDEX uq_suppression_entries_active_recipient ON suppression_entries (recipient_hash) WHERE active AND scope = 'RECIPIENT';
CREATE UNIQUE INDEX uq_suppression_entries_active_business ON suppression_entries (business_id) WHERE active AND scope = 'BUSINESS';
CREATE UNIQUE INDEX uq_suppression_entries_active_global ON suppression_entries ((1)) WHERE active AND scope = 'GLOBAL';

CREATE TABLE send_intents (
    send_intent_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    campaign_version integer NOT NULL,
    campaign_member_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    message_id uuid NOT NULL,
    mailbox_id uuid NOT NULL,
    approval_id uuid NOT NULL,
    eligibility_policy_decision_id uuid NOT NULL,
    eligibility_policy_scope text NOT NULL DEFAULT 'APPROVAL_ELIGIBILITY',
    eligibility_policy_version text NOT NULL,
    eligibility_facts_hash char(64) NOT NULL,
    eligibility_policy_allowed boolean NOT NULL DEFAULT true,
    idempotency_key text NOT NULL,
    scope_hash char(64) NOT NULL,
    rfc_message_id text NOT NULL,
    max_attempts integer NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0,
    retry_deadline timestamptz NOT NULL,
    retry_policy_version text NOT NULL,
    budget_reservation_id uuid NOT NULL,
    open_for_attempt boolean NOT NULL DEFAULT true,
    cancelled_at timestamptz NULL,
    cancellation_reason text NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_send_intents PRIMARY KEY (send_intent_id),
    CONSTRAINT fk_send_intents_message_authority FOREIGN KEY (message_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, mailbox_id) REFERENCES outreach_messages (message_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, mailbox_id) ON DELETE RESTRICT,
    CONSTRAINT fk_send_intents_approval_authority FOREIGN KEY (approval_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, scope_hash) REFERENCES approvals (approval_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, scope_hash) ON DELETE RESTRICT,
    CONSTRAINT fk_send_intents_budget FOREIGN KEY (budget_reservation_id) REFERENCES budget_reservations (reservation_id) ON DELETE RESTRICT,
    CONSTRAINT uq_send_intents_message UNIQUE (message_id),
    CONSTRAINT uq_send_intents_approval UNIQUE (approval_id),
    CONSTRAINT uq_send_intents_mailbox_idempotency UNIQUE (mailbox_id, idempotency_key),
    CONSTRAINT uq_send_intents_mailbox_rfc UNIQUE (mailbox_id, rfc_message_id),
    CONSTRAINT uq_send_intents_mailbox_identity UNIQUE (send_intent_id, mailbox_id),
    CONSTRAINT uq_send_intents_attempt_identity UNIQUE (send_intent_id, mailbox_id, rfc_message_id),
    CONSTRAINT uq_send_intents_attempt_authority UNIQUE NULLS NOT DISTINCT (send_intent_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, approval_id, eligibility_policy_decision_id, eligibility_policy_scope, eligibility_policy_version, scope_hash, eligibility_facts_hash, eligibility_policy_allowed, rfc_message_id, open_for_attempt),
    CONSTRAINT ck_send_intents_hashes CHECK (scope_hash ~ '^[0-9a-f]{64}$' AND eligibility_facts_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_send_intents_eligibility_authority CHECK (eligibility_policy_scope = 'APPROVAL_ELIGIBILITY' AND eligibility_policy_allowed),
    CONSTRAINT ck_send_intents_attempts CHECK (max_attempts > 0 AND attempt_count BETWEEN 0 AND max_attempts),
    CONSTRAINT ck_send_intents_retry_deadline CHECK (retry_deadline > created_at),
    CONSTRAINT ck_send_intents_cancellation CHECK ((open_for_attempt AND cancelled_at IS NULL AND cancellation_reason IS NULL) OR (NOT open_for_attempt AND cancelled_at IS NOT NULL AND cancellation_reason IS NOT NULL))
);
CREATE INDEX ix_send_intents_mailbox_created ON send_intents (mailbox_id, created_at DESC);
CREATE INDEX ix_send_intents_open ON send_intents (mailbox_id, created_at) WHERE cancelled_at IS NULL;

CREATE TABLE send_rate_reservations (
    send_rate_reservation_id uuid NOT NULL,
    send_intent_id uuid NOT NULL,
    mailbox_id uuid NOT NULL,
    rate_policy_version text NOT NULL,
    window_start timestamptz NOT NULL,
    window_end timestamptz NOT NULL,
    slot_number integer NOT NULL,
    concurrency_lease_token char(64) NOT NULL,
    state text NOT NULL DEFAULT 'RESERVED',
    reserved_at timestamptz NOT NULL,
    lease_expires_at timestamptz NOT NULL,
    consumed_at timestamptz NULL,
    released_at timestamptz NULL,
    expired_at timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_send_rate_reservations PRIMARY KEY (send_rate_reservation_id),
    CONSTRAINT fk_send_rate_reservations_intent FOREIGN KEY (send_intent_id, mailbox_id) REFERENCES send_intents (send_intent_id, mailbox_id) ON DELETE RESTRICT,
    CONSTRAINT uq_send_rate_reservations_slot UNIQUE (mailbox_id, rate_policy_version, window_start, slot_number),
    CONSTRAINT uq_send_rate_reservations_attempt_authority UNIQUE (send_rate_reservation_id, send_intent_id, mailbox_id, rate_policy_version, window_start, slot_number, concurrency_lease_token, consumed_at),
    CONSTRAINT ck_send_rate_reservations_state CHECK (state IN ('RESERVED','CONSUMED','RELEASED','EXPIRED')),
    CONSTRAINT ck_send_rate_reservations_window CHECK (window_end > window_start AND slot_number >= 0),
    CONSTRAINT ck_send_rate_reservations_lease CHECK (lease_expires_at > reserved_at AND concurrency_lease_token ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_send_rate_reservations_times CHECK (
        (state = 'RESERVED' AND consumed_at IS NULL AND released_at IS NULL AND expired_at IS NULL) OR
        (state = 'CONSUMED' AND consumed_at IS NOT NULL AND released_at IS NULL AND expired_at IS NULL) OR
        (state = 'RELEASED' AND consumed_at IS NOT NULL AND released_at IS NOT NULL AND expired_at IS NULL) OR
        (state = 'EXPIRED' AND released_at IS NULL AND expired_at IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_send_rate_reservations_active_mailbox ON send_rate_reservations (mailbox_id) WHERE state IN ('RESERVED','CONSUMED');
CREATE INDEX ix_send_rate_reservations_expiry ON send_rate_reservations (lease_expires_at, mailbox_id) WHERE state IN ('RESERVED','CONSUMED');

CREATE TABLE send_attempts (
    send_attempt_id uuid NOT NULL,
    send_intent_id uuid NOT NULL,
    experiment_id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    campaign_version integer NOT NULL,
    campaign_member_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    message_id uuid NOT NULL,
    mailbox_id uuid NOT NULL,
    approval_id uuid NOT NULL,
    eligibility_policy_decision_id uuid NOT NULL,
    eligibility_policy_scope text NOT NULL,
    eligibility_policy_version text NOT NULL,
    eligibility_facts_hash char(64) NOT NULL,
    eligibility_policy_allowed boolean NOT NULL,
    send_policy_decision_id uuid NOT NULL,
    send_policy_scope text NOT NULL DEFAULT 'SEND',
    send_policy_version text NOT NULL,
    scope_hash char(64) NOT NULL,
    send_policy_facts_hash char(64) NOT NULL,
    send_policy_allowed boolean NOT NULL DEFAULT true,
    rate_reservation_id uuid NOT NULL,
    rate_policy_version text NOT NULL,
    rate_window_start timestamptz NOT NULL,
    rate_slot_number integer NOT NULL,
    rate_concurrency_lease_token char(64) NOT NULL,
    rate_consumed_at timestamptz NOT NULL,
    rfc_message_id text NOT NULL,
    intent_open_for_attempt boolean NOT NULL DEFAULT true,
    attempt_number integer NOT NULL,
    state text NOT NULL DEFAULT 'STARTED',
    started_at timestamptz NOT NULL,
    provider_called_at timestamptz NULL,
    completed_at timestamptz NULL,
    error_code text NULL,
    error_fingerprint char(64) NULL,
    retry_class text NULL,
    reconciliation_strategy_version text NULL,
    CONSTRAINT pk_send_attempts PRIMARY KEY (send_attempt_id),
    CONSTRAINT fk_send_attempts_intent_authority FOREIGN KEY (send_intent_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, approval_id, eligibility_policy_decision_id, eligibility_policy_scope, eligibility_policy_version, scope_hash, eligibility_facts_hash, eligibility_policy_allowed, rfc_message_id, intent_open_for_attempt) REFERENCES send_intents (send_intent_id, experiment_id, campaign_id, campaign_version, campaign_member_id, lead_id, message_id, mailbox_id, approval_id, eligibility_policy_decision_id, eligibility_policy_scope, eligibility_policy_version, scope_hash, eligibility_facts_hash, eligibility_policy_allowed, rfc_message_id, open_for_attempt) ON DELETE RESTRICT,
    CONSTRAINT fk_send_attempts_rate_reservation FOREIGN KEY (rate_reservation_id, send_intent_id, mailbox_id, rate_policy_version, rate_window_start, rate_slot_number, rate_concurrency_lease_token, rate_consumed_at) REFERENCES send_rate_reservations (send_rate_reservation_id, send_intent_id, mailbox_id, rate_policy_version, window_start, slot_number, concurrency_lease_token, consumed_at) ON DELETE RESTRICT,
    CONSTRAINT uq_send_attempts_number UNIQUE (send_intent_id, attempt_number),
    CONSTRAINT uq_send_attempts_mailbox_identity UNIQUE (send_attempt_id, mailbox_id),
    CONSTRAINT uq_send_attempts_provider_identity UNIQUE (send_attempt_id, mailbox_id, rfc_message_id),
    CONSTRAINT ck_send_attempts_number CHECK (attempt_number > 0),
    CONSTRAINT ck_send_attempts_state CHECK (state IN ('STARTED','AMBIGUOUS','RECONCILING','SENT','FAILED')),
    CONSTRAINT ck_send_attempts_times CHECK (provider_called_at IS NULL OR provider_called_at >= started_at),
    CONSTRAINT ck_send_attempts_completed CHECK ((state = 'STARTED' AND completed_at IS NULL) OR (state <> 'STARTED' AND completed_at IS NOT NULL)),
    CONSTRAINT ck_send_attempts_error CHECK ((error_fingerprint IS NULL) OR error_fingerprint ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_send_attempts_authority CHECK (eligibility_policy_scope = 'APPROVAL_ELIGIBILITY' AND eligibility_policy_allowed AND send_policy_scope = 'SEND' AND send_policy_allowed AND intent_open_for_attempt AND scope_hash ~ '^[0-9a-f]{64}$' AND eligibility_facts_hash ~ '^[0-9a-f]{64}$' AND send_policy_facts_hash ~ '^[0-9a-f]{64}$' AND rate_concurrency_lease_token ~ '^[0-9a-f]{64}$' AND rate_consumed_at <= started_at)
);
CREATE INDEX ix_send_attempts_unresolved ON send_attempts (mailbox_id, started_at) WHERE state IN ('STARTED','AMBIGUOUS','RECONCILING');

CREATE TABLE provider_results (
    provider_result_id uuid NOT NULL,
    send_attempt_id uuid NOT NULL,
    mailbox_id uuid NOT NULL,
    provider text NOT NULL,
    outcome text NOT NULL,
    gmail_message_id text NULL,
    gmail_thread_id text NULL,
    rfc_message_id text NOT NULL,
    provider_timestamp timestamptz NULL,
    response_fingerprint char(64) NOT NULL,
    captured_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    raw_payload_ref text NULL,
    CONSTRAINT pk_provider_results PRIMARY KEY (provider_result_id),
    CONSTRAINT fk_provider_results_attempt_identity FOREIGN KEY (send_attempt_id, mailbox_id, rfc_message_id) REFERENCES send_attempts (send_attempt_id, mailbox_id, rfc_message_id) ON DELETE RESTRICT,
    CONSTRAINT uq_provider_results_fingerprint UNIQUE (send_attempt_id, response_fingerprint),
    CONSTRAINT uq_provider_results_mailbox_message UNIQUE (mailbox_id, gmail_message_id),
    CONSTRAINT ck_provider_results_provider CHECK (provider = 'GMAIL'),
    CONSTRAINT ck_provider_results_outcome CHECK (outcome IN ('ACCEPTED','REJECTED','UNKNOWN','RECONCILED_SENT','RECONCILED_ABSENT','CONFLICT')),
    CONSTRAINT ck_provider_results_ids CHECK ((outcome IN ('ACCEPTED','RECONCILED_SENT')) = (gmail_message_id IS NOT NULL AND gmail_thread_id IS NOT NULL)),
    CONSTRAINT ck_provider_results_fingerprint CHECK (response_fingerprint ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_provider_results_mailbox_rfc ON provider_results (mailbox_id, rfc_message_id, captured_at DESC);

CREATE TABLE provider_observations (
    provider_observation_id uuid NOT NULL,
    mailbox_id uuid NOT NULL,
    gmail_message_id text NOT NULL,
    gmail_thread_id text NOT NULL,
    history_id text NULL,
    rfc_message_id text NULL,
    direction text NOT NULL,
    observed_at timestamptz NOT NULL,
    payload_ref text NOT NULL,
    fingerprint char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_provider_observations PRIMARY KEY (provider_observation_id),
    CONSTRAINT fk_provider_observations_mailbox FOREIGN KEY (mailbox_id) REFERENCES gmail_mailboxes (mailbox_id) ON DELETE RESTRICT,
    CONSTRAINT uq_provider_observations_message UNIQUE (mailbox_id, gmail_message_id),
    CONSTRAINT uq_provider_observations_fingerprint UNIQUE (mailbox_id, fingerprint),
    CONSTRAINT uq_provider_observations_reply_identity UNIQUE (provider_observation_id, mailbox_id, gmail_message_id, gmail_thread_id),
    CONSTRAINT uq_provider_observations_cursor_identity UNIQUE (provider_observation_id, mailbox_id, gmail_message_id, history_id),
    CONSTRAINT ck_provider_observations_direction CHECK (direction IN ('INBOUND','OUTBOUND')),
    CONSTRAINT ck_provider_observations_fingerprint CHECK (fingerprint ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_provider_observations_thread ON provider_observations (mailbox_id, gmail_thread_id, observed_at);
CREATE INDEX ix_provider_observations_history ON provider_observations (mailbox_id, history_id) WHERE history_id IS NOT NULL;
CREATE INDEX ix_provider_observations_rfc ON provider_observations (mailbox_id, rfc_message_id, observed_at) WHERE rfc_message_id IS NOT NULL;

CREATE TABLE replies (
    reply_id uuid NOT NULL,
    message_id uuid NOT NULL,
    mailbox_id uuid NOT NULL,
    provider_observation_id uuid NOT NULL,
    gmail_message_id text NOT NULL,
    gmail_thread_id text NOT NULL,
    received_at timestamptz NOT NULL,
    classification_artifact_id uuid NULL,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CONSTRAINT pk_replies PRIMARY KEY (reply_id),
    CONSTRAINT fk_replies_message_mailbox FOREIGN KEY (message_id, mailbox_id) REFERENCES outreach_messages (message_id, mailbox_id) ON DELETE RESTRICT,
    CONSTRAINT fk_replies_observation_identity FOREIGN KEY (provider_observation_id, mailbox_id, gmail_message_id, gmail_thread_id) REFERENCES provider_observations (provider_observation_id, mailbox_id, gmail_message_id, gmail_thread_id) ON DELETE RESTRICT,
    CONSTRAINT uq_replies_observation UNIQUE (provider_observation_id),
    CONSTRAINT uq_replies_mailbox_message UNIQUE (mailbox_id, gmail_message_id)
);
CREATE INDEX ix_replies_message_received ON replies (message_id, received_at);

CREATE TABLE gmail_history_cursors (
    mailbox_id uuid NOT NULL,
    history_id text NOT NULL,
    version bigint NOT NULL DEFAULT 1,
    advanced_at timestamptz NOT NULL,
    last_observation_id uuid NULL,
    last_observation_gmail_message_id text NULL,
    last_observation_history_id text NULL,
    CONSTRAINT pk_gmail_history_cursors PRIMARY KEY (mailbox_id),
    CONSTRAINT fk_gmail_history_cursors_mailbox FOREIGN KEY (mailbox_id) REFERENCES gmail_mailboxes (mailbox_id) ON DELETE RESTRICT,
    CONSTRAINT fk_gmail_history_cursors_observation_identity FOREIGN KEY (last_observation_id, mailbox_id, last_observation_gmail_message_id, last_observation_history_id) REFERENCES provider_observations (provider_observation_id, mailbox_id, gmail_message_id, history_id) ON DELETE RESTRICT,
    CONSTRAINT uq_gmail_history_cursors_version UNIQUE (mailbox_id, version),
    CONSTRAINT ck_gmail_history_cursors_version CHECK (version > 0),
    CONSTRAINT ck_gmail_history_cursors_observation_triplet CHECK ((last_observation_id IS NULL AND last_observation_gmail_message_id IS NULL AND last_observation_history_id IS NULL) OR (last_observation_id IS NOT NULL AND last_observation_gmail_message_id IS NOT NULL AND last_observation_history_id IS NOT NULL))
);
CREATE INDEX ix_gmail_history_cursors_advanced ON gmail_history_cursors (advanced_at);
```

`GmailMailboxCommandService` may insert `status=ACTIVE` only inside `CompleteGmailAuthorization` after validating signed `ActiveCredentialProofV1`. The row copies exact `(oauth_flow_id,mailbox_id,provider_account_hash,granted_scope_hash,credential_handle_hash,credential_version,credential_key_version,credential_activation_generation)` from the ACTIVE secret object. Product credential resolution hashes the opaque handle and requires every value plus ACTIVE mailbox status to match; no row or mismatch means no token access. The binding tuple is immutable while mailbox status is ACTIVE. Authenticated reconnect may replace the entire tuple atomically only from DISABLED, with the same provider account, exact next credential version, no unresolved attempts, and a new ACTIVE proof; partial field patch is forbidden.

Deferred M2 foreign keys `fk_leads_suppression`, `fk_lead_assessments_artifact`, `fk_outreach_messages_artifact`, `fk_approvals_eligibility_policy_authority`, `fk_send_intents_eligibility_policy_authority`, `fk_send_attempts_send_policy_authority`, and `fk_replies_classification_artifact` are added after DB-04/DB-05 exists. Exact definitions appear in DB-06. `trg_send_intents_immutable_identity` protects every experiment/campaign/member/lead/message/mailbox/approval/eligibility/scope/idempotency/RFC/retry/budget field while allowing only `attempt_count`, `open_for_attempt`, `cancelled_at`, and `cancellation_reason`; `trg_send_intent_cancellation_once` makes the true-to-false cancellation a one-way transition. `fk_send_attempts_intent_authority` copies the non-null `open_for_attempt=true` token: PostgreSQL rejects an attempt for a cancelled intent and blocks flipping the parent token after an attempt exists.

| Table | Exclusive write owner | Retention class / retention owner |
| --- | --- | --- |
| `businesses` | `BusinessIdentityService` | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `leads` | `LeadCommandService` | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `lead_assessments` | `LeadQualificationService` | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `gmail_mailboxes` | `GmailMailboxCommandService` | `SAFETY_LONG` / `RetentionCommandService` |
| `campaigns` | `CampaignCommandService` | `BUSINESS_ACTIVE` / `RetentionCommandService` |
| `campaign_members` | `CampaignAdmissionService` | `SENSITIVE_SHORT` / `RetentionCommandService` |
| `outreach_messages` | `MessageCommandService` | `SENSITIVE_SHORT` / `RetentionCommandService` |
| `approvals` | `ApprovalCommandService` | `SAFETY_LONG` / `RetentionCommandService` |
| `suppression_entries` | `SuppressionCommandService` | `SAFETY_LONG` / `RetentionCommandService` |
| `send_intents` | application `SendGateway` | `SAFETY_LONG` / `RetentionCommandService` |
| `send_rate_reservations` | `SendRateReservationService` under SendGateway/Recovery transactions | `SAFETY_LONG` / `RetentionCommandService` |
| `send_attempts` | application `SendGateway` and `SendRecoveryService` under disjoint transitions | `SAFETY_LONG` / `RetentionCommandService` |
| `provider_results` | `GmailResultCaptureService` | `SAFETY_LONG` / `RetentionCommandService` |
| `provider_observations` | `GmailObservationService` | `SENSITIVE_SHORT` / `RetentionCommandService` |
| `replies` | `GmailReplySyncService` | `SENSITIVE_SHORT` / `RetentionCommandService` |
| `gmail_history_cursors` | `GmailHistorySyncService` | `SAFETY_LONG` / `RetentionCommandService` |

### Send transition reconciliation

`outreach_messages.state` is the ARCH-03 message aggregate. `send_attempts.state` is ledger evidence, not a second message state machine. Direct captured acceptance commits provider result, `SENDING -> SENT`, and `send.provider_accepted.v1`. Unknown outcome commits `SENDING -> AMBIGUOUS` and `send.outcome_ambiguous.v1`; `AMBIGUOUS -> RECONCILING` commits `send.reconciliation_started.v1`. Recovery loads the intent's immutable experiment/campaign/member/lead/message/mailbox/approval/eligibility-basis/RFC tuple, proves the attempt adds one fresh allowed SEND decision plus the exact consumed rate reservation, and searches only that Gmail account. Exactly one mailbox-bound matching Sent observation permits `RECONCILING -> SENT` and `send.reconciled_as_sent.v1`. A conclusive absence after the configured window may produce `FAILED_RETRYABLE`; cross-mailbox or multiple matches, malformed identity, or operator stop produces `FAILED_PERMANENT`. `AMBIGUOUS` never requeues.

## Ordered implementation tasks

- [ ] **Migrate identity and lead records —** Input: canonicalization rules and ARCH-03 `LeadState`. Operation: create businesses/leads/assessments with uniqueness, conflict quarantine, and provenance. Output: deduplicated M5-ready schema. Test evidence: `test_concurrent_same_business_discovery_creates_one_lead`. Failure behavior: quarantine conflict; never auto-merge.
- [ ] **Migrate campaigns, approvals, and suppression —** Input: campaign/approval states and policy facts. Operation: create exact-scope/version records and fail-closed suppression indexes. Output: deterministic admission substrate. Test evidence: `test_suppression_overrides_qualification_and_approval`. Failure behavior: deny admission and audit reason.
- [ ] **Migrate message and send ledger —** Input: ARCH-03 message transitions. Operation: create immutable message content, intent identity, attempts, results, observations, replies, and cursor. Output: complete ambiguity chain. Test evidence: exhaustive PostgreSQL constraint and transition tests. Failure behavior: keep unresolved state operator-visible; disable send on impossible state.
- [ ] **Implement sole send transaction boundaries —** Input: approved message and current controls. Operation: commit intent/policy/budget/queue evidence, release transaction, call Gmail only through `SendGateway`, then record result or ambiguity. Output: auditable side effect. Test evidence: kill point before/after each boundary. Failure behavior: no blind retry; reconcile first.
- [ ] **Implement atomic history sync —** Input: mailbox cursor and provider page. Operation: deduplicate observations/replies, append events, then advance cursor in the same transaction. Output: lossless replayable sync. Test evidence: crash on every row/cursor boundary. Failure behavior: rollback page and fetch it again.

## Test strategy

- **Unit `test_message_transition_matrix_matches_arch03`:** all legal/illegal edges and events.
- **Constraint `test_one_intent_per_message_approval_and_mailbox_key`:** concurrent commands cannot duplicate an intent or consume one approval twice; mailbox, campaign/member version, approval, message, eligibility basis/scope hash, RFC ID, and idempotency identity cannot mutate.
- **Constraint `test_cross_scope_message_member_approval_eligibility_send_policy_intent_rate_attempt_rows_fail`:** every one-column splice across experiment, campaign version, `campaign_member_id`, lead, mailbox, approval, eligibility decision, final SEND decision, scope/facts hash, rate reservation/lease token/consumption timestamp, or allowed flag violates a named composite FK; a RESERVED rate row cannot back an attempt.
- **OAuth binding `test_active_mailbox_requires_exact_active_credential_proof_tuple`:** flow/account/scope/handle/version/key/generation splice or non-ACTIVE proof creates no mailbox/SUCCEEDED result.
- **Concurrency `test_one_active_mailbox_rate_lease_and_unique_window_slot`:** simultaneous gateway transactions produce one consumed lease/attempt winner and one typed rate denial; a RESERVED or token/timestamp-spliced reservation cannot satisfy the attempt FK.
- **Suppression `test_last_mile_suppression_cancels_intent_without_attempt_or_provider_call`:** nullable-cancellation FK and row/event counts prove the no-call path.
- **Recovery `test_timeout_after_gmail_acceptance_reconciles_without_resend`:** stable RFC ID finds Sent evidence.
- **Recovery `test_reconciliation_uses_only_the_authorized_mailbox`:** approval/intent/attempt/result account IDs agree; cross-account evidence is rejected and the searched account is retained.
- **Recovery `test_multiple_sent_matches_require_operator_resolution`:** never guess which send won.
- **Integration `test_history_observations_events_cursor_commit_atomically`:** cursor cannot skip a reply.
- **Constraint `test_reply_and_cursor_require_same_mailbox_gmail_message_thread_history_observation`:** provider evidence cannot be spliced by bare observation ID.
- **Security `test_logs_and_events_exclude_decrypted_recipient_and_body`:** safe telemetry only.
- **Contract `test_only_send_gateway_invokes_gmail_send`:** import/call graph has one production caller.

## Security, privacy, compliance, idempotency, observability, and cost

Recipient addresses and message content are encrypted; normalized hashes support scoped dedupe/suppression without appearing in logs. Legal/compliance facts and approval versions are deterministic inputs; model prose cannot authorize send. The stable idempotency key and RFC Message-ID survive retries/restarts. Every provider call records policy, budget, correlation, attempt, result/ambiguity, and cost reference. Retention minimizes personal/message data while preserving safety evidence hashes and suppression requirements.

## Failure, rollback, and operator recovery

Global disable stops admission and dequeue before the next provider call. Campaign pause stops new calls but does not erase ambiguous evidence. Operator recovery compares message/intent/attempt, provider results, Sent observations, workflow history, and events; it resolves through an audited command, never direct SQL. Provider credential compromise disables provider and preserves restricted incident evidence. Schema rollback cannot remove unresolved attempts or active suppression.

## Acceptance and retained evidence

- [ ] Every lead/campaign/message/approval state uses ARCH-03 names exactly.
- [ ] Every workflow read/write maps to a table and named constraint here.
- [ ] One immutable mailbox-bound authority tuple, stable intent key/RFC Message-ID, bounded attempt ledger, result capture, direct provider-accepted event, and ambiguity-only Sent reconciliation cover every Gmail outcome.
- [ ] Agents and workflows cannot invoke Gmail or mutate these aggregates directly.
- [ ] Product outreach remains disabled until both M1 and M6 pass.

Retain constraint introspection, identity races, transition matrix, send kill-point traces, Sent reconciliation fixtures, cursor crash traces, suppression tests, encrypted-field/log scans, and provider call-path proof.

## Dependencies and next deliverable

DB-03 depends on DB-01/02, ARCH-03, DB-04 artifact references, and DB-05 policy/event/idempotency records. It unlocks [WF-04 lead qualification](../03-workflows/04-lead-qualification-workflow.md) and, only after all M6 gates, [WF-05 outreach/reply](../03-workflows/05-outreach-and-reply-workflow.md).
