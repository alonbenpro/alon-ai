"""Bind follow-up evidence and booking commercial lineage to the exact turn.

Revision ID: 20260923_19
Revises: 20260922_18
"""

from alembic import op

revision = "20260923_19"
down_revision = "20260922_18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
DO $$ BEGIN
 IF EXISTS (
  SELECT 1 FROM record_conversation_follow_ups f
  JOIN record_conversation_documents d ON d.id=f.source_document_id
  WHERE d.kind<>'REPLY_INTERPRETATION'
     OR d.experiment_id IS DISTINCT FROM f.experiment_id
     OR d.conversation_id IS DISTINCT FROM f.conversation_id
     OR d.context_id IS DISTINCT FROM f.context_id
     OR d.content->'follow_up'->>'disposition' IS DISTINCT FROM 'EXPLICIT'
     OR d.content->'follow_up'->>'span_ordinal' IS DISTINCT FROM f.source_span_ordinal::text
     OR d.content->'follow_up'->>'date_kind' IS DISTINCT FROM f.date_kind
     OR d.content->'follow_up'->>'start_date' IS DISTINCT FROM f.start_date::text
     OR d.content->'follow_up'->>'end_date' IS DISTINCT FROM f.end_date::text
     OR d.content->'follow_up'->>'timezone' IS DISTINCT FROM f.timezone
     OR NOT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name=f.timezone)
 ) THEN RAISE EXCEPTION 'existing follow-up lacks explicit interpretation evidence'; END IF;
 IF EXISTS (
  SELECT 1 FROM record_conversation_booking_intents i
  JOIN record_conversation_turn_contexts t ON t.id=i.context_id
  JOIN record_conversations c ON c.id=i.conversation_id
  WHERE (i.experiment_id,i.offer_acceptance_id,i.offer_id,i.profile_id,i.policy_id,i.recipient_id)
    IS DISTINCT FROM (t.experiment_id,t.offer_acceptance_id,t.offer_id,t.profile_id,t.policy_id,c.recipient_id)
     OR c.experiment_id IS DISTINCT FROM i.experiment_id
 ) THEN RAISE EXCEPTION 'existing booking intent has mismatched commercial lineage'; END IF;
 IF EXISTS (
  SELECT 1 FROM record_conversation_handoffs h
  JOIN record_conversation_booking_observations o ON o.id=h.booking_observation_id
  JOIN record_conversation_booking_intents i ON i.id=o.intent_id
  WHERE h.kind='MEETING_BOOKING' AND
    (i.experiment_id,i.conversation_id,i.context_id,i.offer_acceptance_id,
     i.offer_id,i.profile_id,i.policy_id,i.recipient_id)
    IS DISTINCT FROM
    (h.experiment_id,h.conversation_id,h.context_id,h.offer_acceptance_id,
     h.offer_id,h.profile_id,h.policy_id,h.recipient_id)
 ) THEN RAISE EXCEPTION 'existing booking handoff has mismatched commercial lineage'; END IF;
END $$;

CREATE OR REPLACE FUNCTION record_conversation_follow_up_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (
  SELECT 1 FROM record_conversation_turn_contexts t
  JOIN record_conversations c ON c.id=t.conversation_id
  JOIN record_conversation_documents d ON d.id=NEW.source_document_id
  JOIN record_conversation_evidence_spans s ON s.document_id=d.id AND s.ordinal=NEW.source_span_ordinal
  WHERE t.id=NEW.context_id AND t.experiment_id=NEW.experiment_id
    AND c.id=NEW.conversation_id AND c.experiment_id=NEW.experiment_id
    AND d.experiment_id=NEW.experiment_id AND d.conversation_id=NEW.conversation_id
    AND d.context_id=NEW.context_id AND d.kind='REPLY_INTERPRETATION'
    AND d.content->'follow_up'->>'disposition'='EXPLICIT'
    AND d.content->'follow_up'->>'span_ordinal'=NEW.source_span_ordinal::text
    AND d.content->'follow_up'->>'date_kind'=NEW.date_kind
    AND d.content->'follow_up'->>'start_date'=NEW.start_date::text
    AND d.content->'follow_up'->>'end_date' IS NOT DISTINCT FROM NEW.end_date::text
    AND d.content->'follow_up'->>'timezone'=NEW.timezone
 ) OR NOT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name=NEW.timezone)
 THEN RAISE EXCEPTION 'follow-up explicit interpretation mismatch'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION record_conversation_booking_intent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (
  SELECT 1 FROM record_conversation_handoffs h
  JOIN record_conversation_turn_contexts t ON t.id=NEW.context_id
  JOIN record_conversations c ON c.id=NEW.conversation_id
  JOIN record_conversation_documents d ON d.id=NEW.source_document_id
  JOIN record_conversation_evidence_spans s ON s.document_id=d.id AND s.ordinal=NEW.source_span_ordinal
  WHERE h.id=NEW.scheduling_handoff_id AND h.kind='MEETING_SCHEDULING'
    AND h.experiment_id=NEW.experiment_id AND h.conversation_id=NEW.conversation_id
    AND t.experiment_id=NEW.experiment_id AND t.conversation_id=NEW.conversation_id
    AND c.experiment_id=NEW.experiment_id
    AND d.experiment_id=NEW.experiment_id AND d.conversation_id=NEW.conversation_id
    AND d.context_id=NEW.context_id
    AND (NEW.offer_acceptance_id,NEW.offer_id,NEW.profile_id,NEW.policy_id,NEW.recipient_id)
      = (t.offer_acceptance_id,t.offer_id,t.profile_id,t.policy_id,c.recipient_id)
 ) THEN RAISE EXCEPTION 'booking intent commercial lineage mismatch'; END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION record_conversation_handoff_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record_conversations; t record_conversation_turn_contexts; i record_conversation_booking_intents; o record_conversation_booking_observations;
BEGIN
 SELECT * INTO c FROM record_conversations WHERE id=NEW.conversation_id;
 SELECT * INTO t FROM record_conversation_turn_contexts WHERE id=NEW.context_id;
 IF c.id IS NULL OR t.id IS NULL OR c.experiment_id<>NEW.experiment_id
    OR t.experiment_id<>NEW.experiment_id OR t.conversation_id<>NEW.conversation_id
    OR NOT EXISTS(SELECT 1 FROM record_conversation_documents d JOIN record_conversation_evidence_spans s ON s.document_id=d.id
      WHERE d.id=NEW.source_document_id AND s.ordinal=NEW.source_span_ordinal AND d.experiment_id=NEW.experiment_id AND d.conversation_id=NEW.conversation_id AND d.context_id=NEW.context_id)
    OR (NEW.offer_acceptance_id,NEW.offer_id,NEW.profile_id,NEW.policy_id,NEW.recipient_id)
      IS DISTINCT FROM (t.offer_acceptance_id,t.offer_id,t.profile_id,t.policy_id,c.recipient_id)
 THEN RAISE EXCEPTION 'handoff lineage mismatch'; END IF;
 IF NEW.kind='MEETING_BOOKING' THEN
  SELECT * INTO o FROM record_conversation_booking_observations WHERE id=NEW.booking_observation_id;
  IF o.id IS NOT NULL THEN SELECT * INTO i FROM record_conversation_booking_intents WHERE id=o.intent_id; END IF;
  IF o.id IS NULL OR i.id IS NULL
     OR (i.experiment_id,i.conversation_id,i.context_id,i.offer_acceptance_id,i.offer_id,i.profile_id,i.policy_id,i.recipient_id)
       IS DISTINCT FROM (NEW.experiment_id,NEW.conversation_id,NEW.context_id,NEW.offer_acceptance_id,NEW.offer_id,NEW.profile_id,NEW.policy_id,NEW.recipient_id)
     OR NOT EXISTS(SELECT 1 FROM record_conversation_booking_confirmations b
       WHERE b.id=o.confirmation_id AND b.intent_id=i.id
         AND (b.source_document_id,b.source_span_ordinal)=(NEW.source_document_id,NEW.source_span_ordinal))
  THEN RAISE EXCEPTION 'booking handoff mismatch'; END IF;
 END IF;
 RETURN NEW;
END $$;
""")


def downgrade() -> None:
    op.execute(r"""
CREATE OR REPLACE FUNCTION record_conversation_follow_up_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM record_conversation_turn_contexts t JOIN record_conversation_documents d ON d.id=NEW.source_document_id JOIN record_conversation_evidence_spans s ON s.document_id=d.id AND s.ordinal=NEW.source_span_ordinal WHERE t.id=NEW.context_id AND t.conversation_id=NEW.conversation_id AND d.conversation_id=NEW.conversation_id AND d.context_id=NEW.context_id) THEN RAISE EXCEPTION 'follow-up source mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_conversation_booking_intent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM record_conversation_handoffs h JOIN record_conversation_turn_contexts t ON t.id=NEW.context_id JOIN record_conversation_documents d ON d.id=NEW.source_document_id JOIN record_conversation_evidence_spans s ON s.document_id=d.id AND s.ordinal=NEW.source_span_ordinal WHERE h.id=NEW.scheduling_handoff_id AND h.kind='MEETING_SCHEDULING' AND h.conversation_id=NEW.conversation_id AND t.conversation_id=NEW.conversation_id AND d.conversation_id=NEW.conversation_id AND d.context_id=NEW.context_id) THEN RAISE EXCEPTION 'booking intent mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION record_conversation_handoff_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record_conversations; t record_conversation_turn_contexts; i record_conversation_booking_intents; o record_conversation_booking_observations;
BEGIN
 SELECT * INTO c FROM record_conversations WHERE id=NEW.conversation_id;
 SELECT * INTO t FROM record_conversation_turn_contexts WHERE id=NEW.context_id;
 IF c.id IS NULL OR t.id IS NULL OR t.conversation_id<>NEW.conversation_id
    OR NOT EXISTS(SELECT 1 FROM record_conversation_documents d JOIN record_conversation_evidence_spans s ON s.document_id=d.id
      WHERE d.id=NEW.source_document_id AND s.ordinal=NEW.source_span_ordinal AND d.conversation_id=NEW.conversation_id AND d.context_id=NEW.context_id)
    OR (NEW.offer_acceptance_id,NEW.offer_id,NEW.profile_id,NEW.policy_id,NEW.recipient_id) <> (t.offer_acceptance_id,t.offer_id,t.profile_id,t.policy_id,c.recipient_id) THEN RAISE EXCEPTION 'handoff lineage mismatch'; END IF;
 IF NEW.kind='MEETING_BOOKING' THEN
  SELECT * INTO o FROM record_conversation_booking_observations WHERE id=NEW.booking_observation_id;
  SELECT * INTO i FROM record_conversation_booking_intents WHERE id=o.intent_id;
  IF o.id IS NULL OR i.conversation_id<>NEW.conversation_id OR i.context_id<>NEW.context_id OR i.offer_id<>NEW.offer_id OR i.policy_id<>NEW.policy_id OR i.recipient_id<>NEW.recipient_id
     OR NOT EXISTS(SELECT 1 FROM record_conversation_booking_confirmations b WHERE b.id=o.confirmation_id AND b.intent_id=i.id AND (b.source_document_id,b.source_span_ordinal)=(NEW.source_document_id,NEW.source_span_ordinal)) THEN RAISE EXCEPTION 'booking handoff mismatch'; END IF;
 END IF;
 RETURN NEW;
END $$;
""")
