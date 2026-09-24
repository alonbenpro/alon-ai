"""immutable handoff, lock, and operator outcome records

Revision ID: 20260920_12
Revises: 20260920_11
"""

from alembic import op

revision = "20260920_12"
down_revision = "20260920_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE record_conversation_referrals (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL,
 context_id UUID NOT NULL, source_document_id UUID NOT NULL, source_span_ordinal INTEGER NOT NULL,
 organization_id UUID NOT NULL, referred_recipient_id UUID NOT NULL,
 referred_recipient_source_id UUID NOT NULL, content_hash VARCHAR(64) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY(context_id) REFERENCES record_conversation_turn_contexts(id),
 FOREIGN KEY(source_document_id,source_span_ordinal) REFERENCES record_conversation_evidence_spans(document_id,ordinal),
 FOREIGN KEY(referred_recipient_source_id,experiment_id,organization_id,referred_recipient_id)
   REFERENCES record_org_recipient_sources(id,experiment_id,organization_id,recipient_id),
 CHECK(content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_follow_ups (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL,
 context_id UUID NOT NULL, source_document_id UUID NOT NULL, source_span_ordinal INTEGER NOT NULL,
 disposition VARCHAR(16) NOT NULL, date_kind VARCHAR(8) NOT NULL, start_date DATE NOT NULL,
 end_date DATE, timezone VARCHAR(100) NOT NULL, content_hash VARCHAR(64) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY(context_id) REFERENCES record_conversation_turn_contexts(id),
 FOREIGN KEY(source_document_id,source_span_ordinal) REFERENCES record_conversation_evidence_spans(document_id,ordinal),
 UNIQUE(conversation_id,source_document_id,source_span_ordinal),
 CHECK(disposition='EXPLICIT' AND date_kind IN ('DATE','RANGE')
   AND ((date_kind='DATE' AND end_date IS NULL) OR (date_kind='RANGE' AND end_date > start_date))
   AND length(btrim(timezone)) BETWEEN 1 AND 100 AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_handoffs (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL,
 context_id UUID NOT NULL, kind VARCHAR(32) NOT NULL, source_document_id UUID NOT NULL,
 source_span_ordinal INTEGER NOT NULL, source_intent_hash VARCHAR(64) NOT NULL,
 offer_acceptance_id UUID NOT NULL, offer_id UUID NOT NULL, profile_id UUID NOT NULL,
 policy_id UUID NOT NULL, recipient_id UUID NOT NULL, booking_observation_id UUID,
 content JSONB NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY(context_id) REFERENCES record_conversation_turn_contexts(id),
 FOREIGN KEY(source_document_id,source_span_ordinal) REFERENCES record_conversation_evidence_spans(document_id,ordinal),
 UNIQUE(conversation_id,kind,source_intent_hash),
 CHECK(kind IN ('INVOICE','DEMO','MEETING_SCHEDULING','MEETING_BOOKING')
   AND source_intent_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$'
   AND ((kind='MEETING_BOOKING') = (booking_observation_id IS NOT NULL)))
);
CREATE TABLE record_conversation_operator_actions (
 id UUID PRIMARY KEY, handoff_id UUID NOT NULL UNIQUE, experiment_id UUID NOT NULL,
 conversation_id UUID NOT NULL, action VARCHAR(64) NOT NULL, priority VARCHAR(16) NOT NULL,
 content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(handoff_id) REFERENCES record_conversation_handoffs(id),
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 CHECK(priority IN ('URGENT','HIGH') AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_lock_events (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL,
 lock_kind VARCHAR(32) NOT NULL, event_kind VARCHAR(16) NOT NULL, related_handoff_id UUID,
 prior_lock_id UUID, event_ordinal BIGSERIAL NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY(related_handoff_id) REFERENCES record_conversation_handoffs(id),
 FOREIGN KEY(prior_lock_id) REFERENCES record_conversation_lock_events(id),
 UNIQUE(conversation_id,event_ordinal),
 CHECK(lock_kind IN ('SCHEDULING_ONLY','MANUAL_TAKEOVER') AND event_kind IN ('ACTIVATE','RELEASE')
   AND content_hash ~ '^[0-9a-f]{64}$'
   AND ((event_kind='ACTIVATE' AND prior_lock_id IS NULL) OR (event_kind='RELEASE' AND prior_lock_id IS NOT NULL)))
);
CREATE TABLE record_conversation_manual_outcomes (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL,
 context_id UUID NOT NULL, operator_id UUID NOT NULL, active_lock_event_id UUID NOT NULL,
 outcome VARCHAR(32) NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY(context_id) REFERENCES record_conversation_turn_contexts(id),
 FOREIGN KEY(operator_id) REFERENCES record_operators(id),
 FOREIGN KEY(active_lock_event_id) REFERENCES record_conversation_lock_events(id),
 CHECK(outcome IN ('DEMO_PREPARING','DEMO_SENT','DEMO_ACCEPTED','DEMO_DECLINED','INVOICE_PREPARING','INVOICE_SENT','PAYMENT_PENDING','PAID','PAYMENT_FAILED','MEETING_BOOKED','MEETING_COMPLETED','MEETING_CANCELLED','NO_SHOW','MANUAL_NEGOTIATION','MANUALLY_CLOSED') AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_operator_messages (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL,
 context_id UUID NOT NULL, operator_id UUID NOT NULL, organization_id UUID NOT NULL,
 recipient_id UUID NOT NULL, recipient_source_id UUID NOT NULL, thread_identity_hash VARCHAR(64) NOT NULL,
 active_lock_event_id UUID NOT NULL, body_hash VARCHAR(64) NOT NULL, content_hash VARCHAR(64) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY(context_id) REFERENCES record_conversation_turn_contexts(id),
 FOREIGN KEY(operator_id) REFERENCES record_operators(id),
 FOREIGN KEY(active_lock_event_id) REFERENCES record_conversation_lock_events(id),
 FOREIGN KEY(recipient_source_id,experiment_id,organization_id,recipient_id)
   REFERENCES record_org_recipient_sources(id,experiment_id,organization_id,recipient_id),
 CHECK(thread_identity_hash ~ '^[0-9a-f]{64}$' AND body_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_referral_evidence (
 referral_id UUID NOT NULL REFERENCES record_conversation_referrals(id), document_id UUID NOT NULL,
 span_ordinal INTEGER NOT NULL, role VARCHAR(32) NOT NULL, PRIMARY KEY(referral_id,role),
 FOREIGN KEY(document_id,span_ordinal) REFERENCES record_conversation_evidence_spans(document_id,ordinal),
 CHECK(role IN ('ORGANIZATION_MEMBERSHIP','RELEVANCE'))
);
CREATE TABLE record_conversation_booking_intents (
 id UUID PRIMARY KEY, experiment_id UUID NOT NULL, conversation_id UUID NOT NULL, context_id UUID NOT NULL,
 scheduling_handoff_id UUID NOT NULL UNIQUE, source_document_id UUID NOT NULL, source_span_ordinal INTEGER NOT NULL,
 offer_acceptance_id UUID NOT NULL, offer_id UUID NOT NULL, profile_id UUID NOT NULL, policy_id UUID NOT NULL,
 recipient_id UUID NOT NULL, slot_hash VARCHAR(64) NOT NULL, attendee_hash VARCHAR(64) NOT NULL,
 intent_hash VARCHAR(64) NOT NULL, content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(conversation_id,experiment_id) REFERENCES record_conversations(id,experiment_id),
 FOREIGN KEY(context_id) REFERENCES record_conversation_turn_contexts(id),
 FOREIGN KEY(scheduling_handoff_id) REFERENCES record_conversation_handoffs(id),
 FOREIGN KEY(source_document_id,source_span_ordinal) REFERENCES record_conversation_evidence_spans(document_id,ordinal),
 CHECK(slot_hash ~ '^[0-9a-f]{64}$' AND attendee_hash ~ '^[0-9a-f]{64}$'
   AND intent_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_booking_confirmations (
 id UUID PRIMARY KEY, intent_id UUID NOT NULL UNIQUE, source_document_id UUID NOT NULL,
 source_span_ordinal INTEGER NOT NULL, confirmation_hash VARCHAR(64) NOT NULL,
 slot_hash VARCHAR(64) NOT NULL, attendee_hash VARCHAR(64) NOT NULL, content_hash VARCHAR(64) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL, FOREIGN KEY(intent_id) REFERENCES record_conversation_booking_intents(id),
 FOREIGN KEY(source_document_id,source_span_ordinal) REFERENCES record_conversation_evidence_spans(document_id,ordinal),
 CHECK(confirmation_hash ~ '^[0-9a-f]{64}$' AND slot_hash ~ '^[0-9a-f]{64}$'
   AND attendee_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE record_conversation_booking_observations (
 id UUID PRIMARY KEY, intent_id UUID NOT NULL, confirmation_id UUID NOT NULL UNIQUE,
 provider_call_id UUID NOT NULL, provider_evidence_id UUID NOT NULL, provider_event_hash VARCHAR(64) NOT NULL,
 slot_hash VARCHAR(64) NOT NULL, attendee_hash VARCHAR(64) NOT NULL, content_hash VARCHAR(64) NOT NULL,
 observed_at TIMESTAMPTZ NOT NULL, FOREIGN KEY(intent_id) REFERENCES record_conversation_booking_intents(id),
 FOREIGN KEY(confirmation_id) REFERENCES record_conversation_booking_confirmations(id),
 FOREIGN KEY(provider_call_id) REFERENCES gov_calls(id), FOREIGN KEY(provider_evidence_id) REFERENCES gov_evidence(id),
 UNIQUE(provider_call_id,provider_evidence_id), CHECK(provider_event_hash ~ '^[0-9a-f]{64}$'
   AND slot_hash ~ '^[0-9a-f]{64}$' AND attendee_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$')
);
ALTER TABLE record_conversation_handoffs ADD FOREIGN KEY(booking_observation_id) REFERENCES record_conversation_booking_observations(id);

CREATE FUNCTION record_handoff_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable handoff record'; END $$;
CREATE FUNCTION record_conversation_lock_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE current record_conversation_lock_events;
BEGIN
 PERFORM 1 FROM record_conversations WHERE id=NEW.conversation_id AND experiment_id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO current FROM record_conversation_lock_events WHERE conversation_id=NEW.conversation_id ORDER BY event_ordinal DESC LIMIT 1;
 IF NEW.event_kind='ACTIVATE' THEN
  IF current.id IS NOT NULL AND current.event_kind='ACTIVATE' THEN RAISE EXCEPTION 'active automation lock exists'; END IF;
 ELSIF current.id IS NULL OR current.event_kind<>'ACTIVATE' OR NEW.prior_lock_id<>current.id OR NEW.lock_kind<>current.lock_kind THEN
  RAISE EXCEPTION 'invalid lock release';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_conversation_handoff_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE FUNCTION record_conversation_operator_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record_conversations; l record_conversation_lock_events;
BEGIN
 SELECT * INTO c FROM record_conversations WHERE id=NEW.conversation_id;
 SELECT * INTO l FROM record_conversation_lock_events WHERE conversation_id=NEW.conversation_id ORDER BY event_ordinal DESC LIMIT 1;
 IF NOT EXISTS(SELECT 1 FROM record_conversation_turn_contexts WHERE id=NEW.context_id AND conversation_id=NEW.conversation_id)
    OR l.id IS NULL OR l.event_kind<>'ACTIVATE' OR l.lock_kind<>'MANUAL_TAKEOVER' OR l.id<>NEW.active_lock_event_id
    OR NOT EXISTS(SELECT 1 FROM record_operators WHERE id=NEW.operator_id AND status='ACTIVE') THEN RAISE EXCEPTION 'manual operator authority required'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_conversation_operator_message_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c record_conversations; l record_conversation_lock_events;
BEGIN
 SELECT * INTO c FROM record_conversations WHERE id=NEW.conversation_id;
 SELECT * INTO l FROM record_conversation_lock_events WHERE conversation_id=NEW.conversation_id ORDER BY event_ordinal DESC LIMIT 1;
 IF NOT EXISTS(SELECT 1 FROM record_conversation_turn_contexts WHERE id=NEW.context_id AND conversation_id=NEW.conversation_id)
    OR l.id IS NULL OR l.event_kind<>'ACTIVATE' OR l.lock_kind<>'MANUAL_TAKEOVER' OR l.id<>NEW.active_lock_event_id
    OR NOT EXISTS(SELECT 1 FROM record_operators WHERE id=NEW.operator_id AND status='ACTIVE')
    OR (c.organization_id,c.recipient_id,c.recipient_source_id,c.thread_identity_hash) <> (NEW.organization_id,NEW.recipient_id,NEW.recipient_source_id,NEW.thread_identity_hash) THEN RAISE EXCEPTION 'operator message lineage mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_conversation_booking_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE i record_conversation_booking_intents; c record_conversation_booking_confirmations;
BEGIN
 IF TG_TABLE_NAME='record_conversation_booking_confirmations' THEN
  SELECT * INTO i FROM record_conversation_booking_intents WHERE id=NEW.intent_id;
  IF i.slot_hash<>NEW.slot_hash OR i.attendee_hash<>NEW.attendee_hash
     OR NOT EXISTS(SELECT 1 FROM record_conversation_documents d JOIN record_conversation_evidence_spans s ON s.document_id=d.id WHERE d.id=NEW.source_document_id AND s.ordinal=NEW.source_span_ordinal AND d.conversation_id=i.conversation_id AND d.context_id=i.context_id) THEN RAISE EXCEPTION 'booking confirmation mismatch'; END IF;
 ELSE
  SELECT * INTO i FROM record_conversation_booking_intents WHERE id=NEW.intent_id;
  SELECT * INTO c FROM record_conversation_booking_confirmations WHERE id=NEW.confirmation_id;
  IF c.id IS NULL OR c.intent_id<>i.id OR i.slot_hash<>NEW.slot_hash OR i.attendee_hash<>NEW.attendee_hash OR c.slot_hash<>NEW.slot_hash OR c.attendee_hash<>NEW.attendee_hash
     OR NOT EXISTS(SELECT 1 FROM gov_evidence WHERE id=NEW.provider_evidence_id AND call_id=NEW.provider_call_id AND kind='PROVIDER_RESULT') THEN RAISE EXCEPTION 'booking observation mismatch'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_conversation_referral_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r record_conversation_referrals;
BEGIN
 IF TG_TABLE_NAME='record_conversation_referrals' THEN
  IF NOT EXISTS(SELECT 1 FROM record_conversation_turn_contexts t JOIN record_conversation_documents d ON d.id=NEW.source_document_id JOIN record_conversation_evidence_spans s ON s.document_id=d.id AND s.ordinal=NEW.source_span_ordinal WHERE t.id=NEW.context_id AND t.conversation_id=NEW.conversation_id AND d.conversation_id=NEW.conversation_id AND d.context_id=NEW.context_id) THEN RAISE EXCEPTION 'referral source mismatch'; END IF;
  RETURN NEW;
 END IF;
 SELECT * INTO r FROM record_conversation_referrals WHERE id=NEW.referral_id;
 IF NOT EXISTS(SELECT 1 FROM record_conversation_documents d JOIN record_conversation_evidence_spans s ON s.document_id=d.id
   WHERE d.id=NEW.document_id AND s.ordinal=NEW.span_ordinal AND d.conversation_id=r.conversation_id)
   OR (NEW.role='RELEVANCE' AND (NEW.document_id,NEW.span_ordinal)<>(r.source_document_id,r.source_span_ordinal)) THEN RAISE EXCEPTION 'referral evidence mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_conversation_referral_complete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (SELECT count(*) FROM record_conversation_referral_evidence WHERE referral_id=NEW.id)<>2
    OR NOT EXISTS(SELECT 1 FROM record_conversation_referral_evidence WHERE referral_id=NEW.id AND role='ORGANIZATION_MEMBERSHIP')
    OR NOT EXISTS(SELECT 1 FROM record_conversation_referral_evidence WHERE referral_id=NEW.id AND role='RELEVANCE') THEN RAISE EXCEPTION 'referral requires membership and relevance evidence'; END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION record_conversation_follow_up_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM record_conversation_turn_contexts t JOIN record_conversation_documents d ON d.id=NEW.source_document_id JOIN record_conversation_evidence_spans s ON s.document_id=d.id AND s.ordinal=NEW.source_span_ordinal WHERE t.id=NEW.context_id AND t.conversation_id=NEW.conversation_id AND d.conversation_id=NEW.conversation_id AND d.context_id=NEW.context_id) THEN RAISE EXCEPTION 'follow-up source mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_conversation_booking_intent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM record_conversation_handoffs h JOIN record_conversation_turn_contexts t ON t.id=NEW.context_id JOIN record_conversation_documents d ON d.id=NEW.source_document_id JOIN record_conversation_evidence_spans s ON s.document_id=d.id AND s.ordinal=NEW.source_span_ordinal WHERE h.id=NEW.scheduling_handoff_id AND h.kind='MEETING_SCHEDULING' AND h.conversation_id=NEW.conversation_id AND t.conversation_id=NEW.conversation_id AND d.conversation_id=NEW.conversation_id AND d.context_id=NEW.context_id) THEN RAISE EXCEPTION 'booking intent mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_conversation_lock_topology BEFORE INSERT ON record_conversation_lock_events FOR EACH ROW EXECUTE FUNCTION record_conversation_lock_guard();
CREATE TRIGGER record_conversation_handoff_lineage BEFORE INSERT ON record_conversation_handoffs FOR EACH ROW EXECUTE FUNCTION record_conversation_handoff_guard();
CREATE TRIGGER record_conversation_operator_message_lineage BEFORE INSERT ON record_conversation_operator_messages FOR EACH ROW EXECUTE FUNCTION record_conversation_operator_message_guard();
CREATE TRIGGER record_conversation_outcome_lineage BEFORE INSERT ON record_conversation_manual_outcomes FOR EACH ROW EXECUTE FUNCTION record_conversation_operator_guard();
CREATE TRIGGER record_conversation_confirmation_lineage BEFORE INSERT ON record_conversation_booking_confirmations FOR EACH ROW EXECUTE FUNCTION record_conversation_booking_guard();
CREATE TRIGGER record_conversation_observation_lineage BEFORE INSERT ON record_conversation_booking_observations FOR EACH ROW EXECUTE FUNCTION record_conversation_booking_guard();
CREATE TRIGGER record_conversation_referral_evidence_lineage BEFORE INSERT ON record_conversation_referral_evidence FOR EACH ROW EXECUTE FUNCTION record_conversation_referral_guard();
CREATE TRIGGER record_conversation_referral_lineage BEFORE INSERT ON record_conversation_referrals FOR EACH ROW EXECUTE FUNCTION record_conversation_referral_guard();
CREATE CONSTRAINT TRIGGER record_conversation_referral_complete AFTER INSERT ON record_conversation_referrals DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION record_conversation_referral_complete();
CREATE TRIGGER record_conversation_follow_up_lineage BEFORE INSERT ON record_conversation_follow_ups FOR EACH ROW EXECUTE FUNCTION record_conversation_follow_up_guard();
CREATE TRIGGER record_conversation_booking_intent_lineage BEFORE INSERT ON record_conversation_booking_intents FOR EACH ROW EXECUTE FUNCTION record_conversation_booking_intent_guard();
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['referrals','follow_ups','handoffs','operator_actions','lock_events','manual_outcomes','operator_messages','referral_evidence','booking_intents','booking_confirmations','booking_observations'] LOOP EXECUTE format('CREATE TRIGGER record_handoff_%s_immutable BEFORE UPDATE OR DELETE ON record_conversation_%s FOR EACH ROW EXECUTE FUNCTION record_handoff_immutable()',t,t); END LOOP; END $$;
""")


def downgrade() -> None:
    op.execute("""
DROP TABLE record_conversation_referral_evidence;
DROP TABLE record_conversation_operator_messages;
DROP TABLE record_conversation_manual_outcomes;
DROP TABLE record_conversation_lock_events;
DROP TABLE record_conversation_operator_actions;
ALTER TABLE record_conversation_handoffs DROP CONSTRAINT record_conversation_handoffs_booking_observation_id_fkey;
DROP TABLE record_conversation_booking_observations;
DROP TABLE record_conversation_booking_confirmations;
DROP TABLE record_conversation_booking_intents;
DROP TABLE record_conversation_handoffs;
DROP TABLE record_conversation_follow_ups;
DROP TABLE record_conversation_referrals;
""")
    op.execute("DROP FUNCTION record_conversation_referral_guard()")
    op.execute("DROP FUNCTION record_conversation_referral_complete()")
    op.execute("DROP FUNCTION record_conversation_follow_up_guard()")
    op.execute("DROP FUNCTION record_conversation_booking_intent_guard()")
    op.execute("DROP FUNCTION record_conversation_booking_guard()")
    op.execute("DROP FUNCTION record_conversation_operator_guard()")
    op.execute("DROP FUNCTION record_conversation_operator_message_guard()")
    op.execute("DROP FUNCTION record_conversation_handoff_guard()")
    op.execute("DROP FUNCTION record_conversation_lock_guard()")
    op.execute("DROP FUNCTION record_handoff_immutable()")
