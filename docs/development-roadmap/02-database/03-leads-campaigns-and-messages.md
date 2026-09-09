# Leads, Campaigns, Messages, Gmail Observations, and Replies

**Document ID:** DB-03
**Status:** Planned M2 schema; provider use blocked until M6
**Milestone:** M1, M2, M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `DB-03-T01 -> DB-03-T02 -> DB-03-T03 -> DB-03-T04 -> DB-03-T05 -> DB-03-T06`; cross-document task Inputs `DB-03-T01 <- PRODUCT-01-T03,SEC-01-T01; DB-03-T02 <- ARCH-03-T01; DB-03-T03 <- ARCH-03-T01,DB-05-T02; DB-03-T04 <- ARCH-03-T01; DB-03-T05 <- DB-01-T05,BACKEND-05-T03,BACKEND-04-T04; DB-03-T06 <- PROVIDER-02-T01,PROVIDER-02-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): [DB-01](01-core-data-model.md), [DB-02](02-experiment-and-offer-schema.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), and [risk gates](../00-product-strategy/03-risk-register-and-kill-criteria.md)
**Outputs:** Business identity, lead provenance, qualification, campaigns, action authorizations, messages, send intent/attempt ledger, provider observations, replies, suppression, Gmail cursors, full conversations, negotiations and bookings
**Unlocks:** M5 lead workflow and M6 controlled Gmail/reply workflow
**Risk:** Critical
**Complexity:** XL


## Outcome and current repository state

These are planned M2 records; provider use requires later M6 owned-resource and M9 real-recipient gates. No product table or conversation/booking gateway exists today. Normal permitted actions use deterministic ActionAuthorityScopeV1. Agents and workflows cannot call Gmail or calendar writes. SendGateway and BookingGateway are exclusive writers at those provider boundaries.

## Exact record conventions

DB-02 record notation applies: NOT NULL unless ?, uuid IDs, positive integer versions, UTC timestamptz instants, lowercase char(64) digests, text enums, bigint minor-unit money, created_at on each table, named PK/UQ/FK/CHECK plus indexes shown. Artifact input refs used for accepted pipeline consumption are AcceptedRef; only deterministic candidate validation uses ArtifactRef as defined in DB-04. All *_ref values expand into typed columns, the explicitly named link tables or strict composite arrays with per-target deferred checks; no unnamed relation or bare JSON foreign key is permitted. A composite FK always references immutable published identity/version tuples, never a mutable aggregate version as historical truth.

The common CohortRef is (experiment_id,campaign_id,campaign_version,cohort_id,stage_ordinal). MemberRef extends it with campaign_member_id,lead_id,business_id,contact_identity_id,recipient_address_hash. Action attribution adds offer_id/offer_version/offer_content_hash, strategy_version_id/strategy_content_hash, activation_id, producer_strategy_version, checkpoint_generation, control_generation. Those physical columns are repeated on action authority and its intent/attempt ledger and checked by composite FKs. Typed actor/service IDs are authenticated by the command boundary.

## Identity, discovery and frozen membership schema

| Table / exclusive writer | Exact fields beyond common fields | Keys / constraints / index |
| --- | --- | --- |
| businesses / BusinessIdentityService | business_id; canonical_name; canonical_domain?; country_code? char(2); identity_key; identity_status CONFIRMED/CONFLICT/ARCHIVED; version; updated_at | PK; UQ identity_key; lowercase normalized domain; unknown country remains NULL and fails jurisdiction admission; index canonical_domain |
| business_identity_results / BusinessIdentityService | identity_result_id; business_id; person_id?; contact_identity_id?; decision ACCEPTED/DEDUPLICATED/CONFLICT/REJECTED; normalization_version; source_evidence_set_hash; evidence_refs; identity_snapshot_ciphertext bytea; input_hash; result_hash; supersedes_result_id?; accepted_at? | PK identity_result_id; UQ (input_hash,normalization_version); exact immutable (identity_result_id,business_id,result_hash); accepted/deduplicated result requires confirmed supported identity, conflict/rejected cannot qualify; index (business_id,created_at) |
| people / BusinessIdentityService | person_id; business_id; name_ciphertext? bytea; role_ciphertext? bytea; name_status/role_status FACT/ESTIMATE/UNKNOWN; evidence_ref?; confidence numeric(8,7); identity_status; version | PK; business/evidence FKs; known name/role requires source; no fabricated owner; confidence 0..1; index business_id |
| contact_identities / BusinessIdentityService | contact_identity_id; business_id; person_id?; kind EMAIL/PHONE; value_ciphertext bytea; lookup_hash; normalization_version; identity_evidence_ref; status CONFIRMED/CONFLICT/INVALID; source_id; observed_at; verified_at; expires_at; version | PK; UQ (kind,lookup_hash,normalization_version); same-business person/source/evidence FKs; conflict quarantined, no automatic merge; index (business_id,status) |
| lead_sources / EvidenceIngestService | source_id; adapter_id; adapter_version; source_scope_version; terms_review_ref; source_kind; source_url_ciphertext? bytea; source_locator_hash; query_filter_version; retrieved_at; published_at?; expiry_at; capture_hash | PK; UQ (adapter_id,source_locator_hash,retrieved_at); approved source scope; bounded source-specific collection; index (adapter_id,retrieved_at) |
| lead_discovery_candidates / DiscoveryCandidateService | candidate_id; experiment_id; offer_ref; source_id; discovery_artifact_ref LeadDiscoveryCandidate; accepted_business_id?; identity_result_ref?; deduplication_key; preliminary_facts_version/preliminary_facts; unknown_fields; created_at | PK; UQ (experiment_id,source_id,deduplication_key); accepted identity result FK; rejected/conflicting candidates remain evidence, not cohort members |
| leads / LeadCommandService | lead_id; experiment_id; business_id; candidate_id; state; version; suppression_entry_id?; updated_at | PK; UQ (experiment_id,business_id), (lead_id,experiment_id,business_id); canonical ARCH-03 LeadState; state SUPPRESSED requires entry; index (experiment_id,state); stage ownership belongs to cohort membership |
| lead_assessments / QualificationService | assessment_id; lead_id; experiment_id; identity_result_ref; phase PRELIMINARY/FINAL; offer_ref; criteria_version; candidate_ref; dossier_ref? LeadResearchDossier; artifact_ref QualificationDecision; score numeric(8,7); reason_codes; gate_passed boolean; facts_hash; created_at | PK; UQ (lead_id,phase,offer_id,criteria_version,facts_hash); FINAL requires accepted dossier and accepted preliminary decision; PRELIMINARY precedes expensive research; only deterministic gate materializes decision; index (lead_id,phase,created_at) |
| campaigns / CampaignCommandService | campaign_version_id; campaign_id; campaign_version; experiment_id; supersedes_campaign_version_id?; state; offer_ref; policy_version; source_scope_version; conversation_booking_policy_version; created_at; updated_at | PK; UQ (campaign_id,campaign_version,experiment_id); same campaign/experiment immediate predecessor; canonical CampaignState; immutable version configuration; index (experiment_id,state) |
| campaign_cohorts / CampaignAdmissionService, closure by CheckpointEvaluationService | CohortRef; prior_stage_decision_id?; incremental_cap; cumulative_cap; effective_cap; membership_hash; eligibility_snapshot_version; eligibility_query_version; eligibility_snapshot_at; member_count; offer_ref; strategy_version_id/hash; activation_id; qualification_filter_version; causal_variables_version/hash; evidence_definition_version/hash; metric_definition_set_hash; state OPEN/CLOSING/CLOSED; control_generation; checkpoint_generation; opened_at; closed_at? | PK cohort_id; UQ (campaign_id,stage_ordinal); exact four stage tuples; effective_cap <= increment and legal/provider/budget cap; UQ immutable CohortRef; prior CONTINUE same program; CAS generation and frozen configuration trigger; index (campaign_id,state) |
| campaign_members / CampaignAdmissionService | MemberRef; eligibility_ordinal; eligibility_basis_hash; final_qualification_ref; recipient_address_ciphertext bytea; recipient_identity_evidence_ref; jurisdiction_evidence_ref; affirmative_consent_evidence_ref?; counsel_exception_evidence_ref?; legal_review_ref; disclosure_sender_template_ref; google_policy_review_ref; legal_policy_version; status ELIGIBLE/REMOVED; removed_at? | PK campaign_member_id; UQ (experiment_id,recipient_address_hash), (cohort_id,lead_id), (cohort_id,eligibility_ordinal); exact accepted compliance tuples; exactly one consent/exception route; ordinal 1..member_count; index (cohort_id,status); removal never creates a replacement recipient allowance |

QualificationService consumes BusinessIdentityService's accepted/deduplicated identity result. It neither inserts identities nor merges businesses, people or contacts. Multi-source collisions with incompatible evidence remain quarantined. Fact fields retain FACT/ESTIMATE/UNKNOWN, evidence, confidence and source time. Offer filters are re-applied in both phases; deterministic identity, suppression, jurisdiction, legal, capacity and cohort admission remain separate gates.

## Immutable action authorization and send schema

ActionAuthorityScopeV1 is the sole normal authority shape. Its schema_version is action.authority.scope.v1. It binds: authorization_id; action_kind INITIAL_EMAIL/REPLY_EMAIL/BOOKING_CREATE/BOOKING_RESCHEDULE/BOOKING_CANCEL; action_id/version/content_hash/materialization_hash; MemberRef; conversation_id/version/thread_identity_hash; mailbox_id? or calendar_id?; OfferRef; strategy_version_id/hash; activation_id; exact accepted artifact/evidence refs; policy_rule_versions; creation_policy_decision_id/facts_hash; commercial_decision_id/hash (FIRST_CONTACT standard decision for INITIAL_EMAIL; REPLY_DRIVEN decision for a response/negotiation); expires_at; max_effect_count=1; checkpoint_generation/control_generation. Each discriminated arm requires exactly its provider/recipient/thread/slot/attendee/notification fields. The hash covers RFC 8785 envelope bytes, including explicit null fields and all immutable refs.

| Table / writer | Fields / constraints |
| --- | --- |
| action_authorizations / ActionAuthorizationService | PK authorization_id; full immutable scope columns above plus action_basis_hash and scope_schema_version/scope_hash; state PENDING/AUTHORIZED/DENIED/EXPIRED/REVOKED/CONSUMED; authorized_at?; reason_codes; created_at. Unique (authorization_id,scope_hash,action_kind,action_id,action_version,action_content_hash,cohort_id,campaign_member_id,activation_id,control_generation,checkpoint_generation). Scope columns never update. State/receipts are one-way audited transitions. Exactly one intent consumes each authorization using an immutable consumption receipt; no operator preview or per-message decision is needed. |
| action_authorization_consumptions / ActionAuthorizationService | PK authorization_id FK exact authority; action_kind; intent_id; consumed_at; command_key; UQ (action_kind,intent_id); deferred constraint trigger verifies exactly one send intent or booking action of matching kind/scope, never both; append-only |
| outreach_messages / MessageCommandService; send transitions by gateways/recovery | PK message_id; MemberRef; conversation_id; mailbox_id; artifact_ref EmailDraft; conversation_strategy_ref; offer_ref; strategy/activation attribution; message_kind INITIAL/REPLY; in_reply_to_message_id?; thread_identity_hash; round_number; state canonical ARCH-03 MessageState; version; content_version; subject_ciphertext/body_ciphertext bytea; content_hash; materialization_hash; created_at/updated_at. UQ immutable message identity/content tuple, UQ (conversation_id,message_kind,round_number,content_hash); reply requires accepted objective/evaluation and parent; no one-message-per-lead restriction. |
| send_intents / SendGateway via RecordSendIntent | PK send_intent_id; MemberRef; message_id/version/content_hash; mailbox_id; authorization_id/scope_hash; full governing attribution; idempotency_key; rfc_message_id; max_attempts; attempt_count default 0; retry_deadline; retry_policy_version; budget_reservation_id/account_id/currency; open_for_attempt default true; cancelled_at?/cancellation_reason?. UQ message_id, authorization_id, (mailbox_id,idempotency_key), (mailbox_id,rfc_message_id), (send_intent_id,mailbox_id,rfc_message_id). Immutable scope/recipient/mailbox/RFC/retry/budget fields; only bounded attempt count and one-way uncalled cancellation may change. |
| send_attempts / SendGateway; disjoint recovery transitions by SendRecoveryService | PK send_attempt_id; full immutable intent identity and attribution; send_policy_decision_id/version/facts_hash; send_policy_scope SEND and allowed=true; rate_reservation_id/rate_policy_version/rate_window_start/rate_slot_number/rate_concurrency_lease_token/rate_consumed_at; attempt_number; state STARTED/AMBIGUOUS/RECONCILING/SENT/FAILED; started_at/provider_called_at?/completed_at?; error_code?/error_fingerprint?/retry_class?/reconciliation_strategy_version?. UQ (send_intent_id,attempt_number), (send_attempt_id,mailbox_id,rfc_message_id), (send_attempt_id,experiment_id). FK exact consumed rate tuple; immutable attempt identity/facts; partial UQ send_intent_id WHERE unresolved; index (mailbox_id,started_at) WHERE unresolved. |
| suppression_entries / SuppressionCommandService | PK suppression_entry_id; scope GLOBAL/BUSINESS/RECIPIENT; recipient_target_ref_id?; recipient_hash?; business_id?; reason_code; source OPERATOR/GMAIL_UNSUBSCRIBE/GMAIL_HARD_BOUNCE/GMAIL_COMPLAINT/GMAIL_SOFT_BOUNCE_LIMIT/PUBLIC_UNSUBSCRIBE/QUALIFIED_NO_FUTURE_CONTACT/LEGAL_PROHIBITION; trigger_contract_version; trigger_evidence_ref; source_actor_type; source_observation_id?; source_reply_id?; source_command_ref; active default true; version; created_at/deactivated_at?. Partial UQ active global singleton, business_id or recipient_hash; RECIPIENT requires unique random opaque target ref and restricted hash, BUSINESS only business ID, GLOBAL neither; target ref immutable and has no source-member FK. |

Creation uses ActionProposalScopeV1 without creation decision/facts/self-hash, producing action_basis_hash; the ACTION_CREATION policy's scope_hash equals that basis hash. The completed ActionAuthorityScopeV1 includes the exact creation decision/rules/facts_hash and is hashed only afterward; its final scope_hash is not the creation basis hash. This avoids a circular digest. Creation policy facts and fresh gateway facts deliberately differ. The final SEND decision is rebuilt under locks immediately before each attempt. Scope hash equality proves immutable content/context; facts-hash equality is never required and cannot replace fresh evidence. Named fk_send_intents_authority, fk_send_attempts_intent_authority, fk_send_attempts_send_policy_authority and fk_send_attempts_rate_reservation reject every member/recipient/thread/offer/activation/hash/generation/allowed splice. Intent cancellation checks no attempt may have begun; a retention or cancellation operation must never alter a historic parent tuple referenced by attempts.

## Full conversation, negotiation and booking records

| Table / writer | Exact fields / mandatory constraints |
| --- | --- |
| conversations / ConversationService | PK conversation_id; MemberRef; mailbox_id; provider_thread_id?; thread_identity_hash; state COLD_ACTIVE/REPLY_PENDING/INTERESTED/NEGOTIATING/COMMITTED/BOOKING_PENDING/BOOKED/PAUSED/DECLINED/OPTED_OUT/CLOSED; version; cold_sequence_stopped_at?; negative_sentiment_stop_at?; message_count; reply_round_count; frequency_window_start/count; deadline_at; offer_ref; strategy/activation; generation; created_at/updated_at. UQ (mailbox_id,provider_thread_id); counters nonnegative and server-owned; index (cohort_id,state). |
| conversation_messages / GmailReplySyncService for inbound, MessageCommandService on positively accepted outbound result | PK conversation_message_id; conversation_id; ordinal; direction INBOUND/OUTBOUND; provider_observation_id?; outreach_message_id?; provider_message_id?; received_or_sent_at; sender_identity_ref; parent_message_id?; subject_ciphertext/body_ciphertext bytea; sanitized_body_ciphertext bytea; raw_content_hash; sanitized_hash; redaction_policy_version; attachment_metadata_ref?; attribution_ref. UQ (conversation_id,ordinal), (conversation_id,provider_message_id); exactly one inbound observation/outbound source; encrypted complete ordered body, no summary-only authority. |
| replies / GmailReplySyncService | PK reply_id; experiment_id; message_id; mailbox_id; conversation_id; conversation_message_id; provider_observation_id; gmail_message_id/thread_id; received_at; classification_artifact_ref? ReplyEvaluation; UQ provider_observation_id, (mailbox_id,gmail_message_id); exact same-mailbox/thread/message FK; index (conversation_id,received_at) |
| budget_assertions / ConversationService | PK budget_assertion_id; conversation_id; origin FIRST_CONTACT_NO_REPLY/REPLY_EVIDENCE; reply_id?; assertion_kind STATED/INFERRED/UNKNOWN; currency?; lower_minor?/upper_minor?; source_span_ref?; source_span_ciphertext? bytea; confidence numeric(8,7); asserted_at; supersedes_assertion_id?; content_hash. FIRST_CONTACT_NO_REPLY requires reply_id NULL, assertion_kind UNKNOWN, all currency/range/span fields NULL, confidence=0 and injected asserted_at. REPLY_EVIDENCE requires same-conversation reply_id; STATED requires exact quoted lead span and currency/range, INFERRED requires inference source span but cannot satisfy stated-budget predicate, UNKNOWN requires null currency/range/span and confidence=0. Nonnegative ordered known ranges; append-only. |
| negotiation_proposals / ConversationService | PK proposal_id; conversation_id; context_kind FIRST_CONTACT/REPLY_DRIVEN; reply_id?; reply_evaluation_ref?; offer_ref AcceptedRef[OfferPackage]; variant_id?; discount_band_id?; objective enum; requested_terms_version/requested_terms; budget_assertion_id; round_number; source_snapshot_id/hash; attribution_ref; content_hash; UQ (conversation_id,round_number,content_hash); FIRST_CONTACT requires no reply/evaluation, zero inbound count/round/discount, standard offer and FIRST_CONTACT_NO_REPLY UNKNOWN; REPLY_DRIVEN requires same-conversation reply plus AcceptedRef[ReplyEvaluation] and REPLY_EVIDENCE budget; proposal has no commercial authority |
| negotiation_decisions / CommercialPolicyEngine through CommercialDecisionService persistence | PK commercial_decision_id; mode ACTION_EVALUATION; context_kind FIRST_CONTACT/REPLY_DRIVEN; proposal_id; conversation_id; offer_ref AcceptedRef[OfferPackage]; variant_id; budget_assertion_id; rule_version; cost/fee/tax/fx/rounding_versions; input_hash; result_hash; allowed; reason_codes; currency; net_price_minor; tax_minor; gross_price_minor; delivery_cost_minor; fees_minor; contribution_minor; contribution_margin_bps; payment_schedule_version; scope_hash; attribution_ref; UQ (proposal_id,rule_version,input_hash); immutable deterministic engine result; OFFER_CANDIDATE validation cannot enter this table |
| calendar_accounts / CalendarAccountService | PK calendar_id; operator_id; provider GOOGLE_CALENDAR; provider_calendar_identity_hash; credential_handle_hash/version/key_version/activation_generation; permitted_timezone_ids; policy_version; status ACTIVE/DISABLED/REVOKED; authority_mode TEST_CALENDAR_ONLY/PRODUCT_ELIGIBLE; version; UQ provider identity; ACTIVE requires same external proof/lease/consistency protocol as Gmail, with calendar-specific scopes and account binding |
| booking_intents / BookingGateway | PK booking_intent_id; MemberRef; conversation_id; offer_ref; final_qualification_ref; reply_evaluation_ref; commercial_decision_id; buying_intent_evidence_ref; call_agreement_evidence_ref; purchase_acceptance_evidence_ref?; artifact_ref BookingIntent; calendar_id; state canonical ARCH-03 BookingState; version; attribution_ref; booking_policy_version; created_at/updated_at; UQ (conversation_id,artifact_id); no purchase-acceptance requirement for qualified INTERESTED/NEGOTIATING call |
| booking_slot_sets / BookingGateway via AvailabilityService read observations | PK slot_set_id; booking_intent_id; availability_observation_id; calendar_id; policy_version; observed_at; expires_at; content_hash; index booking_intent_id; bounded provider slots and explicit expiry |
| booking_slots / BookingGateway | PK slot_id; slot_set_id; utc_start/end; iana_timezone; local_wall_label; utc_offset_seconds; duration_seconds; tzdb_version; content_hash; UQ (slot_set_id,utc_start); end > start; local/UTC/offset match pinned tzdb; reject nonexistent local time and unresolved repeated time |
| booking_confirmations / BookingGateway | PK confirmation_id; booking_intent_id; slot_id/content_hash; lead_identity_ref; conversation_message_id; explicit_source_span_ref; confirmed_at; expires_at; content_hash; exact confirmed slot/timezone; append-only, ambiguous agreement fails |
| booking_actions / BookingGateway | PK booking_action_id; booking_intent_id; kind CREATE/RESCHEDULE/CANCEL; action_version; prior_booking_state; authorization_id/scope_hash; calendar_id; provider_event_identity; expected_provider_event_version?; confirmation_id?; cancellation_reason_ref?; attendee_set_hash; notification_mode; content_hash; idempotency_key; attribution_ref; UQ authorization_id, (booking_intent_id,kind,action_version), (calendar_id,idempotency_key); CREATE requires null expected_provider_event_version; RESCHEDULE/CANCEL require the current event version; CREATE/RESCHEDULE require confirmation, CANCEL requires explicit request or authorized policy/operator reason |
| booking_attempts / BookingGateway | PK booking_attempt_id; booking_action_id; attempt_number; fresh_policy_decision_id/facts_hash; calendar_lease_token; state STARTED/AMBIGUOUS/RECONCILING/SUCCEEDED/FAILED; started_at; completed_at?; provider_called_at?; prewrite_proof_ref?; UQ (booking_action_id,attempt_number); partial UQ calendar_id WHERE unresolved; calendar_id and exact action attribution copied immutably; no attempt without committed authority/lease |
| booking_provider_results / BookingGateway result recorder | PK booking_result_id; booking_attempt_id; provider_call_id; calendar_id; outcome ACCEPTED/REJECTED/UNKNOWN/RECONCILED/ABSENT_INCONCLUSIVE/CONFLICT; provider_event_identity; provider_event_version?; event_etag?; slot_hash?; attendee_set_hash; notification_hash; payload_ref?; result_hash; observed_at; UQ provider_call_id, (booking_result_id,booking_attempt_id,provider_call_id); exact attempt/calendar/action FK; accepted result must match requested action |
| calendar_observations / CalendarObservationService | PK calendar_observation_id; calendar_id; kind AVAILABILITY/EVENT/CALLBACK; provider_event_identity?; provider_change_identity; observed_at; event_etag?; result_hash; payload_ref?; UQ (calendar_id,provider_change_identity); callbacks deduplicate and only report evidence; index (calendar_id,observed_at) |

Before acceptance every row receives DB-05 action-level strategy attribution. Booking provider receipts preserve business/contact/campaign/conversation/offer/evidence links through BookingIntent. Calendar writes serialize under calendar-side-effects with expected provider event version/ETag, stable event identity, confirmation, attendee and notification hashes. Unknown create/change/cancel outcomes quarantine the exact action kind; negative event observations never permit replacement or blind retry.


### Version and reference materialization

BusinessIdentityResultV1 is the immutable product record in business_identity_results, not a sixteenth inter-agent artifact. identity_result_ref expands to (identity_result_id,business_id,result_hash); QualificationService requires ACCEPTED or DEDUPLICATED. Mutable identity-row versions are evidence snapshots, never historical FK parent keys.

outreach_messages.content_version is immutable; message_version in ActionAuthorityScopeV1/send_intents/send_attempts means that exact content_version. outreach_messages.version is only the mutable optimistic lifecycle version supplied as expected_message_version. State changes cannot invalidate an immutable content FK. A different body/subject/thread materialization creates a new message/content version and new authority. Conversation version in authority is an observed snapshot scalar backed by immutable input/policy evidence, not an FK to the mutable current row version; freshness is checked under lock.

OfferRef always expands to offer_id,experiment_id,offer_version,offer_content_hash and resolves offer_packages' published immutable tuple. Strategy refs resolve global package identity independently of experiment. Initial experiment baseline activation is defined in DB-04 before idea/research; a CohortRef always uses a later exact cohort activation.

## Preserved exact Gmail and rate-ledger DDL

The following existing provider-neutral safety columns retain their exact physical shape. Their foreign-key target tuples are published by the records above. No Gmail read port has a send method; only SendGateway receives GmailWritePort.

```sql
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


CREATE TABLE provider_results (
    provider_result_id uuid NOT NULL,
    send_attempt_id uuid NOT NULL,
    provider_call_id uuid NOT NULL,
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
    CONSTRAINT uq_provider_results_cost_authority UNIQUE (provider_result_id, send_attempt_id, provider_call_id, provider),
    CONSTRAINT uq_provider_results_provider_call UNIQUE (provider, provider_call_id),
    CONSTRAINT uq_provider_results_fingerprint UNIQUE (send_attempt_id, response_fingerprint),
    CONSTRAINT uq_provider_results_mailbox_message UNIQUE (mailbox_id, gmail_message_id),
    CONSTRAINT ck_provider_results_provider CHECK (provider = 'GMAIL'),
    CONSTRAINT ck_provider_results_outcome CHECK (outcome IN ('ACCEPTED','REJECTED','UNKNOWN','RECONCILED_SENT','SEARCH_ABSENT_INCONCLUSIVE','CONFLICT')),
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
    signal_kind text NOT NULL DEFAULT 'NONE',
    signal_reason_code text NULL,
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
    CONSTRAINT ck_provider_observations_signal CHECK (signal_kind IN ('NONE','REPLY','UNSUBSCRIBE','HARD_BOUNCE','SOFT_BOUNCE','COMPLAINT') AND ((signal_kind = 'NONE' AND signal_reason_code IS NULL) OR (signal_kind <> 'NONE' AND signal_reason_code IS NOT NULL))),
    CONSTRAINT ck_provider_observations_fingerprint CHECK (fingerprint ~ '^[0-9a-f]{64}$')
);
CREATE INDEX ix_provider_observations_thread ON provider_observations (mailbox_id, gmail_thread_id, observed_at);
CREATE INDEX ix_provider_observations_history ON provider_observations (mailbox_id, history_id) WHERE history_id IS NOT NULL;
CREATE INDEX ix_provider_observations_rfc ON provider_observations (mailbox_id, rfc_message_id, observed_at) WHERE rfc_message_id IS NOT NULL;


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

## Atomic observed signals and cold-sequence stop

Any inbound reply atomically stores observation/reply/full conversation message, sets cold_sequence_stopped_at, transitions into REPLY_PENDING, increments conversation/control generation, invalidates old send authority, closes provably uncalled cold intents, emits events/audit/outbox, and advances the history cursor. Classification is later and cannot delay the cold stop. A positive reply, question or objection may receive a newly evaluated bounded response. A clear rejection closes persuasion.

Durable suppression uses only PRODUCT-01 DurableSuppressionTriggerV1: explicit unsubscribe/do-not-contact/withdrawal, complaint, hard bounce, applicable legal prohibition, registered soft-bounce threshold, or a rejection with separately evidenced no-permitted-future-contact scope. Neither an ordinary reply nor an offer decline is such evidence. RecipientSignalSuppressionService coordinates the atomic transaction and invokes SuppressionCommandService only when that predicate holds; it never becomes a second suppression writer. Negative sentiment/ambiguous intent pauses and creates an exception without inventing durable suppression.

For a suppression trigger the same transaction creates/returns the active entry and its opaque target ref, suppresses affected nonarchived leads and pre-call messages, closes provably uncalled intents/releases unsent reservations, records canonical events and cursor/result. SENDING/AMBIGUOUS/RECONCILING retains provider truth. Any persistence/sync failure triggers independent product fail-close and ALERT_COMPLIANCE_SUPPRESSION. Public unsubscribe GET never mutates; POST uses token-derived replay and the same suppression transaction.

RecipientLookupKeyService alone normalizes addresses and produces the existing deterministic lowercase SHA-256 lookup digest. It is pseudonymous and offline enumerable, restricted by column grants, rate/audit controls and encrypted volumes/WAL/backups. API/events/logs/reports/exports never expose the digest or derive a public fingerprint. Suppression's persisted random recipient_target_ref_id has no source-member FK and survives permitted source purge unchanged.

## Gmail credential, attempt and recovery invariants

ACTIVE gmail_mailboxes copies the exact signed ActiveCredentialProofV1 tuple (oauth_flow_id,mailbox_id,provider_account_hash,granted_scope_hash,credential_handle_hash,credential_version,credential_key_version,credential_activation_generation). Secret resolution requires every field and ACTIVE status. Reconnect from DISABLED replaces the whole tuple, exact next version/same account/new proof/no unresolved attempt; no partial patch or plaintext credential column.

An immutable intent precedes any provider call. A fresh final SEND decision, one unique consumed mailbox/window slot and concurrency lease, conservative STARTED attempt and event/audit/idempotency/outbox commit before SendGateway calls the write port once. A crash in the gap is ambiguous unless signed local proof proves no bytes left the process. UNKNOWN/malformed/transport/5xx/timeouts remain AMBIGUOUS/RECONCILING with the lease retained. A lease expiring by wall time is not no-send evidence.

Direct Gmail acceptance records send.provider_accepted.v1. Exactly one authorized mailbox/RFC/recipient/thread matching Sent observation resolves prior ambiguity as send.reconciled_as_sent.v1. Zero matches at any age is SEARCH_ABSENT_INCONCLUSIVE, never retry evidence; multiple/cross-mailbox/conflicting/malformed matches remain quarantined with an incident. At 300 seconds unresolved ambiguity escalates. Only explicit provider rejection or signed local pre-write proof may enter bounded retry, preserving original intent/RFC identity and requiring fresh authority/facts/rate slot. Provider result call UUID is distinct from send_attempt_id and exactly binds the cost ledger.

## Ordered implementation tasks

<!-- roadmap-task id=DB-03-T01 milestone=M1 depends_on=PRODUCT-01-T03,SEC-01-T01 mode=parallel locks=architecture-contracts,provider-contracts -->
- [ ] **Publish pure Gmail-facing composite contracts —** Input: the PRODUCT-01 vocabulary crosswalk, SEC-01 Critical send/credential interface, and the document-local DB-03 table/state contract. Operation: define versioned strict business, lead, assessment, campaign/cohort, ActionAuthorityScopeV1, message, send-intent, send-attempt, mailbox-authority, encrypted-message, safe-target, identity-tuple, and ambiguity-state contracts without executing a migration. Output: versioned DB-03 composite wire/authority contracts consumed by the M1 Gmail adapters and later M2/M6 persistence. Test evidence: schema/discriminator/hash/golden-vector coverage and forbidden SQLAlchemy/runtime imports. Failure behavior: block provider adapters and migration implementation.
<!-- roadmap-task id=DB-03-T02 milestone=M2 depends_on=DB-03-T01,ARCH-03-T01 mode=serial locks=database-schema,migration-head -->
- [ ] **Migrate identity and lead records —** Input: canonicalization rules and ARCH-03 `LeadState`. Operation: create businesses/people/contact identities/sources/leads/phased assessments with uniqueness, conflict quarantine, and provenance. Output: deduplicated M5-ready schema. Test evidence: `test_concurrent_same_business_discovery_creates_one_lead`. Failure behavior: quarantine conflict; never auto-merge.
<!-- roadmap-task id=DB-03-T03 milestone=M2 depends_on=DB-03-T02,ARCH-03-T01,DB-05-T02 mode=serial locks=database-schema,migration-head,compliance-policy -->
- [ ] **Migrate staged campaigns, action authorizations, and suppression —** Input: the final DB-03 wire/authority contracts, PRODUCT-02 stage tuples, ARCH-03 lead/campaign/action authorization states, DB-05 policy-table and foreign-key constraints, and document-local canonicalization and static policy rules. Operation: create exact stage-scope/version records, serializable incremental/cumulative admission, experiment-wide recipient uniqueness, the durable opaque recipient target ref, and fail-closed suppression indexes and update the complete DB-06 table/foreign-key/retention inventory atomically. Output: deterministic staged admission substrate over the separately migrated identity/lead schema. Test evidence: `test_suppression_overrides_qualification_and_action authorization`, `test_concurrent_stage_final_slot_never_over_admits`, `test_recipient_cannot_reappear_in_another_stage`, and target-ref constraint introspection. Failure behavior: deny admission and audit reason.
<!-- roadmap-task id=DB-03-T04 milestone=M2 depends_on=DB-03-T03,ARCH-03-T01 mode=serial locks=database-schema,migration-head -->
- [ ] **Migrate message and send ledger —** Input: ARCH-03 message transitions. Operation: create immutable message content, intent identity, attempts, results, observations, full conversations, replies, budget assertions, negotiation decisions, booking intents/slots/confirmations/actions/attempts/results, calendar observations and cursors. Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints. Test evidence: exhaustive PostgreSQL constraint and transition tests. Failure behavior: keep unresolved state operator-visible; disable send on impossible state.
<!-- roadmap-task id=DB-03-T05 milestone=M6 depends_on=DB-03-T04,DB-01-T05,BACKEND-05-T03,BACKEND-04-T04 mode=serial locks=database-schema,gmail-side-effects,backend-domain,security-runtime -->
- [ ] **Implement sole send transaction boundaries —** Input: authorized message/current controls, completed BACKEND-04 SendGateway transaction interface and BACKEND-05 immutable action authorization basis; implemented sole gateway execution/result transaction interface. Operation: validate DB constraints and integrate through the sole BACKEND-04 intent/pre-call/result transaction owners; execute the before/after boundary kill matrix without implementing a second transaction writer or Gmail caller. Output: auditable side effect. Test evidence: kill point before/after each boundary. Failure behavior: ambiguity is permanently quarantined and only positive Sent evidence resolves it; retryable state requires explicit provider rejection or signed local pre-write proof.
<!-- roadmap-task id=DB-03-T06 milestone=M6 depends_on=DB-03-T05,PROVIDER-02-T01,PROVIDER-02-T03 mode=serial locks=database-schema,gmail-side-effects,backend-domain -->
- [ ] **Implement atomic history sync —** Input: mailbox cursor/provider page and the PROVIDER-02 atomic observation/reply/event/cursor transaction implementation. Operation: verify DB constraint and replay integration through the sole PROVIDER-02 atomic history owner, including row/cursor crash rollback; do not implement another observation/reply/event/cursor writer. Output: lossless replayable sync. Test evidence: crash on every row/cursor boundary. Failure behavior: rollback page and fetch it again.


## Verification, recovery and acceptance

Retain exact schema/constraint/trigger introspection; every one-field identity, offer, cohort, policy, authorization, activation, recipient/thread, slot, provider-result and consumed-rate splice must fail. Test identity races, phased qualification, full-thread ordering/redaction, STATED/INFERRED/UNKNOWN budget, all cost-first stages and cumulative unique-recipient limits. Exercise cold-stop versus durable suppression/rejection/negative-sentiment cases and source-purge-stable opaque suppression refs.

Crash before/after intent, attempt, provider result, signal/cursor, booking action/confirmation/notification and callback commits. Replay must produce one authoritative effect or explicit unresolved quarantine. Test every DST/expiry/ETag/confirmation/notification conflict, cancellation/reschedule independently, and call agreement without purchase acceptance. No database recovery, pause, rollback or deletion may manufacture proof an external effect did not happen.

DB-06 enumerates every table above for migration, retention and backup. The schema unlocks [lead qualification](../03-workflows/04-lead-qualification-workflow.md), [conversations](../03-workflows/05-outreach-and-reply-workflow.md), and [booking](../03-workflows/07-booking-workflow.md) only at their retained gates.
