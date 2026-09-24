"""immutable conversation and response-decision records

Revision ID: 20260920_11
Revises: 20260920_10
"""

from alembic import op

revision = "20260920_11"
down_revision = "20260920_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE record_conversation_campaigns (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, cohort_id UUID NOT NULL,
 offer_acceptance_id UUID NOT NULL, offer_id UUID NOT NULL, profile_id UUID NOT NULL,
 policy_id UUID NOT NULL, content_hash VARCHAR(64) NOT NULL, created_by UUID NOT NULL,
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY (cohort_id,experiment_id) REFERENCES record_qualification_cohorts(id,experiment_id),
 FOREIGN KEY (offer_acceptance_id,experiment_id) REFERENCES record_offer_acceptances(id,experiment_id),
 UNIQUE (id,experiment_id), UNIQUE (cohort_id),
 CHECK (content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversations (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, campaign_id UUID NOT NULL,
 outreach_context_id UUID NOT NULL, cohort_member_ordinal INTEGER NOT NULL,
 organization_id UUID NOT NULL, recipient_id UUID NOT NULL, recipient_source_id UUID NOT NULL,
 supported_contact_source_id UUID NOT NULL, offer_acceptance_id UUID NOT NULL,
 offer_id UUID NOT NULL, profile_id UUID NOT NULL, policy_id UUID NOT NULL,
 thread_identity_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY (campaign_id,experiment_id) REFERENCES record_conversation_campaigns(id,experiment_id),
 FOREIGN KEY (outreach_context_id,experiment_id) REFERENCES record_outreach_contexts(id,experiment_id),
 UNIQUE (id,experiment_id), UNIQUE (campaign_id,cohort_member_ordinal),
 CHECK (cohort_member_ordinal>0 AND thread_identity_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_messages (
 id UUID PRIMARY KEY, conversation_id UUID NOT NULL, experiment_id UUID NOT NULL,
 ordinal INTEGER NOT NULL, direction VARCHAR(16) NOT NULL, provider_call_id UUID,
 provider_evidence_id UUID, provider_message_key VARCHAR(200), sanitized_body TEXT NOT NULL,
 sanitized_hash VARCHAR(64) NOT NULL, raw_hash VARCHAR(64) NOT NULL, received_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY (conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY (provider_call_id) REFERENCES gov_calls(id),
 FOREIGN KEY (provider_evidence_id) REFERENCES gov_evidence(id),
 UNIQUE (conversation_id,ordinal), UNIQUE (provider_call_id,provider_message_key),
 CHECK (ordinal>0 AND direction IN ('INBOUND','OUTBOUND') AND sanitized_hash ~ '^[0-9a-f]{64}$' AND raw_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_turn_contexts (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL,
 inbound_message_id UUID NOT NULL, outreach_context_id UUID NOT NULL,
 offer_acceptance_id UUID NOT NULL, offer_id UUID NOT NULL, profile_id UUID NOT NULL,
 policy_id UUID NOT NULL, dossier_id UUID NOT NULL, matrix_id UUID NOT NULL, decision_id UUID NOT NULL,
 recipient_source_id UUID NOT NULL, context_hash VARCHAR(64) NOT NULL, version INTEGER NOT NULL,
 created_by UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY (conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY (inbound_message_id) REFERENCES record_conversation_messages(id),
 FOREIGN KEY (outreach_context_id,experiment_id) REFERENCES record_outreach_contexts(id,experiment_id),
 UNIQUE (conversation_id,version), UNIQUE (inbound_message_id),
 CHECK (version>0 AND context_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_documents (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL,
 context_id UUID NOT NULL, kind VARCHAR(64) NOT NULL, version INTEGER NOT NULL,
 content JSONB NOT NULL, content_hash VARCHAR(64) NOT NULL, rule_version VARCHAR(100),
 supersedes_id UUID, created_by UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY (conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY (context_id) REFERENCES record_conversation_turn_contexts(id),
 FOREIGN KEY (supersedes_id) REFERENCES record_conversation_documents(id),
 UNIQUE (id,conversation_id), UNIQUE (conversation_id,kind,version),
 CHECK (version>0 AND content_hash ~ '^[0-9a-f]{64}$' AND kind IN (
 'INBOUND_CONTENT_SAFETY_ASSESSMENT','SENDER_IDENTITY_DECISION','REPLY_INTERPRETATION',
 'REPLY_QUESTION','REPLY_OBJECTION','CONVERSATION_DECISION','CONVERSION_READINESS_DECISION',
 'ALLOWED_RESPONSE_OBJECTIVE','COMMERCIAL_DISCLOSURE_DECISION','NEGOTIATION_OPTION_SET',
 'BUDGET_EVIDENCE','TIMELINE_EVIDENCE','RESPONSE_PLAN','RESPONSE_DRAFT','RESPONSE_VALIDATION_RESULT'))
);
CREATE TABLE record_conversation_evidence_spans (
 document_id UUID NOT NULL, message_id UUID NOT NULL, ordinal INTEGER NOT NULL,
 start_offset INTEGER NOT NULL, end_offset INTEGER NOT NULL, excerpt_hash VARCHAR(64) NOT NULL,
 PRIMARY KEY(document_id,ordinal), FOREIGN KEY(document_id) REFERENCES record_conversation_documents(id),
 FOREIGN KEY(message_id) REFERENCES record_conversation_messages(id),
 CHECK (ordinal>0 AND start_offset>=0 AND end_offset>start_offset AND excerpt_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_fact_ledgers (
 id UUID PRIMARY KEY, conversation_id UUID NOT NULL, experiment_id UUID NOT NULL,
 context_id UUID NOT NULL, fact_key VARCHAR(64) NOT NULL, version INTEGER NOT NULL,
 status VARCHAR(32) NOT NULL, value JSONB, source_document_id UUID NOT NULL,
 content_hash VARCHAR(64) NOT NULL, supersedes_id UUID, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY(context_id) REFERENCES record_conversation_turn_contexts(id),
 FOREIGN KEY(source_document_id) REFERENCES record_conversation_documents(id),
 FOREIGN KEY(supersedes_id) REFERENCES record_conversation_fact_ledgers(id),
 UNIQUE(conversation_id,fact_key,version),
 CHECK(version>0 AND status IN ('EXPLICITLY_STATED','REASONABLE_INTERPRETATION','UNKNOWN','CONTRADICTED') AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE FUNCTION record_conversation_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable conversation record'; END $$;
CREATE TRIGGER record_conversation_campaigns_immutable BEFORE UPDATE OR DELETE ON record_conversation_campaigns FOR EACH ROW EXECUTE FUNCTION record_conversation_immutable();
CREATE TRIGGER record_conversations_immutable BEFORE UPDATE OR DELETE ON record_conversations FOR EACH ROW EXECUTE FUNCTION record_conversation_immutable();
CREATE TRIGGER record_conversation_messages_immutable BEFORE UPDATE OR DELETE ON record_conversation_messages FOR EACH ROW EXECUTE FUNCTION record_conversation_immutable();
CREATE TRIGGER record_conversation_turn_contexts_immutable BEFORE UPDATE OR DELETE ON record_conversation_turn_contexts FOR EACH ROW EXECUTE FUNCTION record_conversation_immutable();
CREATE TRIGGER record_conversation_documents_immutable BEFORE UPDATE OR DELETE ON record_conversation_documents FOR EACH ROW EXECUTE FUNCTION record_conversation_immutable();
CREATE TRIGGER record_conversation_evidence_spans_immutable BEFORE UPDATE OR DELETE ON record_conversation_evidence_spans FOR EACH ROW EXECUTE FUNCTION record_conversation_immutable();
CREATE TRIGGER record_conversation_fact_ledgers_immutable BEFORE UPDATE OR DELETE ON record_conversation_fact_ledgers FOR EACH ROW EXECUTE FUNCTION record_conversation_immutable();
""")


def downgrade() -> None:
    op.execute("""
DROP TABLE record_conversation_fact_ledgers;
DROP TABLE record_conversation_evidence_spans;
DROP TABLE record_conversation_documents;
DROP TABLE record_conversation_turn_contexts;
DROP TABLE record_conversation_messages;
DROP TABLE record_conversations;
DROP TABLE record_conversation_campaigns;
""")
    op.execute("DROP FUNCTION record_conversation_immutable()")
