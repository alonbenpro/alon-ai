"""Transactional immutable conversation response records."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.records.conversation_models import (
    BookingConfirmationRequest,
    BookingIntentRequest,
    BookingObservationRequest,
    ConversationRecordReceipt,
    FollowUpRequest,
    HandoffReceipt,
    HandoffRequest,
    ManualOutcomeRequest,
    OperatorMessageRequest,
    RecordConversationDocumentsRequest,
    ReferralRequest,
)
from alon_ai.records.models import CommandReceipt, ProductRecordsDenied
from alon_ai.records.repository import _complete, _existing, _request_hash, safe_records


class ConversationRecordsRepository:
    def __init__(self, engine: AsyncEngine, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.engine, self.clock = engine, clock

    async def _context(self, connection, context_id: UUID):
        return (
            (
                await connection.execute(
                    text("""SELECT t.id AS context_id,t.experiment_id,t.conversation_id,t.offer_acceptance_id,t.offer_id,
                    t.profile_id,t.policy_id,c.organization_id,c.recipient_id,c.recipient_source_id,
                    c.thread_identity_hash FROM record_conversation_turn_contexts t
                    JOIN record_conversations c ON c.id=t.conversation_id
                    WHERE t.id=:id"""),
                    {"id": context_id},
                )
            )
            .mappings()
            .one_or_none()
        )

    async def _span_exists(self, connection, context, span) -> bool:
        return bool(
            await connection.scalar(
                text("""SELECT 1 FROM record_conversation_documents d
                JOIN record_conversation_evidence_spans s ON s.document_id=d.id
                WHERE d.id=:document_id AND s.ordinal=:ordinal
                AND d.conversation_id=:conversation_id AND d.context_id=:context_id"""),
                {
                    "document_id": span.document_id,
                    "ordinal": span.ordinal,
                    "conversation_id": context["conversation_id"],
                    "context_id": context.get("context_id"),
                },
            )
        )

    async def _active_lock(self, connection, conversation_id: UUID):
        row = (
            (
                await connection.execute(
                    text("""SELECT id,lock_kind,event_kind,related_handoff_id FROM record_conversation_lock_events
                    WHERE conversation_id=:conversation_id ORDER BY event_ordinal DESC LIMIT 1"""),
                    {"conversation_id": conversation_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        return row if row is not None and row["event_kind"] == "ACTIVATE" else None

    @safe_records
    async def record_documents(self, request: RecordConversationDocumentsRequest, *, command_key: UUID) -> ConversationRecordReceipt:
        async with self.engine.begin() as connection:
            context = (await connection.execute(text("SELECT experiment_id, conversation_id FROM record_conversation_turn_contexts WHERE id=:id"), {"id": request.context_id})).mappings().one_or_none()
            if context is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            await lock_experiment(connection, context["experiment_id"])
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_CONVERSATION_DOCUMENTS", request_hash)
            if prior:
                return ConversationRecordReceipt(command_id=prior["id"], result_id=prior["result_id"], conversation_id=context["conversation_id"], document_ids=tuple(item.id for item in request.documents))
            for item in request.documents:
                for ordinal, span in enumerate(item.spans, 1):
                    message = (await connection.execute(text("SELECT sanitized_body, sanitized_hash FROM record_conversation_messages WHERE id=:id AND conversation_id=:conversation_id"), {"id": span.message_id, "conversation_id": context["conversation_id"]})).mappings().one_or_none()
                    if message is None or message["sanitized_hash"] != sha256(message["sanitized_body"].encode()).hexdigest() or span.end_offset > len(message["sanitized_body"]):
                        raise ProductRecordsDenied("EVIDENCE_SPAN_MISMATCH")
                    excerpt = message["sanitized_body"][span.start_offset:span.end_offset]
                    if not excerpt:
                        raise ProductRecordsDenied("EVIDENCE_SPAN_MISMATCH")
                await connection.execute(text("""INSERT INTO record_conversation_documents (id,experiment_id,conversation_id,context_id,kind,version,content,content_hash,rule_version,created_by,created_at)
                    VALUES (:id,:experiment_id,:conversation_id,:context_id,:kind,:version,CAST(:content AS jsonb),:content_hash,:rule_version,:created_by,:created_at)"""), {"id": item.id, "experiment_id": context["experiment_id"], "conversation_id": context["conversation_id"], "context_id": request.context_id, "kind": item.kind, "version": item.version, "content": json.dumps(item.content, sort_keys=True), "content_hash": item.content_hash, "rule_version": item.rule_version, "created_by": request.recorded_by, "created_at": self.clock()})
                for ordinal, span in enumerate(item.spans, 1):
                    body = (await connection.execute(text("SELECT sanitized_body FROM record_conversation_messages WHERE id=:id"), {"id": span.message_id})).scalar_one()
                    excerpt_hash = sha256(body[span.start_offset:span.end_offset].encode()).hexdigest()
                    await connection.execute(text("INSERT INTO record_conversation_evidence_spans (document_id,message_id,ordinal,start_offset,end_offset,excerpt_hash) VALUES (:document_id,:message_id,:ordinal,:start_offset,:end_offset,:excerpt_hash)"), {"document_id": item.id, "message_id": span.message_id, "ordinal": ordinal, "start_offset": span.start_offset, "end_offset": span.end_offset, "excerpt_hash": excerpt_hash})
            for fact in request.facts:
                source = (await connection.execute(text("SELECT id FROM record_conversation_documents WHERE id=:id AND context_id=:context_id"), {"id": fact.source_document_id, "context_id": request.context_id})).scalar_one_or_none()
                if source is None:
                    raise ProductRecordsDenied("FACT_LINEAGE_MISMATCH")
                if fact.supersedes_id is not None:
                    prior_fact = (await connection.execute(text("SELECT fact_key, version FROM record_conversation_fact_ledgers WHERE id=:id AND conversation_id=:conversation_id"), {"id": fact.supersedes_id, "conversation_id": context["conversation_id"]})).mappings().one_or_none()
                    if prior_fact is None or prior_fact["fact_key"] != fact.fact_key or prior_fact["version"] + 1 != fact.version:
                        raise ProductRecordsDenied("FACT_SUPERSESSION_MISMATCH")
                await connection.execute(text("""INSERT INTO record_conversation_fact_ledgers (id,conversation_id,experiment_id,context_id,fact_key,version,status,value,source_document_id,content_hash,supersedes_id,created_at)
                    VALUES (:id,:conversation_id,:experiment_id,:context_id,:fact_key,:version,:status,CAST(:value AS jsonb),:source_document_id,:content_hash,:supersedes_id,:created_at)"""), {"id": fact.id, "conversation_id": context["conversation_id"], "experiment_id": context["experiment_id"], "context_id": request.context_id, "fact_key": fact.fact_key, "version": fact.version, "status": fact.status, "value": json.dumps(fact.value, sort_keys=True), "source_document_id": fact.source_document_id, "content_hash": fact.content_hash, "supersedes_id": fact.supersedes_id, "created_at": self.clock()})
            command_id = await _complete(connection, command_key=command_key, experiment_id=context["experiment_id"], kind="RECORD_CONVERSATION_DOCUMENTS", request_hash=request_hash, result_type="CONVERSATION_DOCUMENTS", result_id=request.context_id, now=self.clock())
            return ConversationRecordReceipt(command_id=command_id, result_id=request.context_id, conversation_id=context["conversation_id"], document_ids=tuple(item.id for item in request.documents))

    async def _receipt(self, connection, command_key, kind, request_hash, result_type, result_id, experiment_id):
        command_id = await _complete(connection, command_key=command_key, experiment_id=experiment_id, kind=kind, request_hash=request_hash, result_type=result_type, result_id=result_id, now=self.clock())
        return CommandReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def record_handoff(self, request: HandoffRequest, *, command_key: UUID) -> HandoffReceipt:
        async with self.engine.begin() as connection:
            context = await self._context(connection, request.context_id)
            if context is None or not await self._span_exists(connection, context, request.source_span):
                raise ProductRecordsDenied("HANDOFF_EVIDENCE_MISMATCH")
            await lock_experiment(connection, context["experiment_id"])
            intent = sha256(json.dumps({"conversation": str(context["conversation_id"]), "context": str(request.context_id), "span": request.source_span.model_dump(mode="json"), "kind": request.kind, "offer_acceptance": str(context["offer_acceptance_id"]), "offer": str(context["offer_id"]), "profile": str(context["profile_id"]), "policy": str(context["policy_id"]), "recipient": str(context["recipient_id"])}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_CONVERSATION_HANDOFF", request_hash)
            if prior:
                return HandoffReceipt(command_id=prior["id"], result_id=prior["result_id"], handoff_id=prior["result_id"], action_id=request.action_id, source_intent_hash=intent)
            active = await self._active_lock(connection, context["conversation_id"])
            scheduling_lock_id: UUID | None = None
            if active and active["lock_kind"] == "MANUAL_TAKEOVER":
                raise ProductRecordsDenied("MANUAL_TAKEOVER_ACTIVE")
            if request.kind == "MEETING_BOOKING":
                observed = await connection.scalar(text("""SELECT 1 FROM record_conversation_booking_observations o
                    JOIN record_conversation_booking_intents i ON i.id=o.intent_id
                    WHERE o.id=:id AND i.conversation_id=:conversation_id AND i.context_id=:context_id
                    AND i.offer_acceptance_id=:offer_acceptance_id AND i.offer_id=:offer_id
                    AND i.profile_id=:profile_id AND i.policy_id=:policy_id AND i.recipient_id=:recipient_id"""), {"id": request.booking_observation_id, **context})
                if not observed or active is None or active["lock_kind"] != "SCHEDULING_ONLY":
                    raise ProductRecordsDenied("BOOKING_OBSERVATION_MISMATCH")
                scheduling_lock_id = active["id"]
            elif active is not None:
                raise ProductRecordsDenied("AUTOMATION_LOCK_ACTIVE")
            await connection.execute(text("""INSERT INTO record_conversation_handoffs (id,experiment_id,conversation_id,context_id,kind,source_document_id,source_span_ordinal,source_intent_hash,offer_acceptance_id,offer_id,profile_id,policy_id,recipient_id,booking_observation_id,content,content_hash,created_at)
                VALUES (:id,:experiment_id,:conversation_id,:context_id,:kind,:source_document_id,:source_span_ordinal,:source_intent_hash,:offer_acceptance_id,:offer_id,:profile_id,:policy_id,:recipient_id,:booking_observation_id,CAST(:content AS jsonb),:content_hash,:created_at)"""), {**context, **request.model_dump(exclude={"source_span", "content", "recorded_by"}), "source_document_id": request.source_span.document_id, "source_span_ordinal": request.source_span.ordinal, "source_intent_hash": intent, "content": json.dumps(request.content, sort_keys=True), "created_at": self.clock()})
            await connection.execute(text("INSERT INTO record_conversation_operator_actions (id,handoff_id,experiment_id,conversation_id,action,priority,content_hash,created_at) VALUES (:id,:handoff_id,:experiment_id,:conversation_id,:action,:priority,:content_hash,:created_at)"), {"id": request.action_id, "handoff_id": request.id, "experiment_id": context["experiment_id"], "conversation_id": context["conversation_id"], "action": request.kind, "priority": "URGENT" if request.kind == "INVOICE" else "HIGH", "content_hash": request.content_hash, "created_at": self.clock()})
            if request.kind == "MEETING_BOOKING":
                assert scheduling_lock_id is not None
                await connection.execute(text("INSERT INTO record_conversation_lock_events (id,experiment_id,conversation_id,lock_kind,event_kind,related_handoff_id,prior_lock_id,content_hash,created_at) VALUES (:id,:experiment_id,:conversation_id,'SCHEDULING_ONLY','RELEASE',:handoff_id,:prior_lock_id,:content_hash,:created_at)"), {"id": uuid4(), "experiment_id": context["experiment_id"], "conversation_id": context["conversation_id"], "handoff_id": request.id, "prior_lock_id": scheduling_lock_id, "content_hash": request.content_hash, "created_at": self.clock()})
            lock_kind = "SCHEDULING_ONLY" if request.kind == "MEETING_SCHEDULING" else "MANUAL_TAKEOVER"
            await connection.execute(text("INSERT INTO record_conversation_lock_events (id,experiment_id,conversation_id,lock_kind,event_kind,related_handoff_id,content_hash,created_at) VALUES (:id,:experiment_id,:conversation_id,:lock_kind,'ACTIVATE',:handoff_id,:content_hash,:created_at)"), {"id": uuid4(), "experiment_id": context["experiment_id"], "conversation_id": context["conversation_id"], "lock_kind": lock_kind, "handoff_id": request.id, "content_hash": request.content_hash, "created_at": self.clock()})
            receipt = await self._receipt(connection, command_key, "RECORD_CONVERSATION_HANDOFF", request_hash, "CONVERSATION_HANDOFF", request.id, context["experiment_id"])
            return HandoffReceipt(command_id=receipt.command_id, result_id=request.id, handoff_id=request.id, action_id=request.action_id, source_intent_hash=intent)

    async def assert_automation_allowed(self, context_id: UUID, action: str) -> None:
        async with self.engine.connect() as connection:
            context = await self._context(connection, context_id)
            if context is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            active = await self._active_lock(connection, context["conversation_id"])
            if active and active["lock_kind"] == "MANUAL_TAKEOVER":
                raise ProductRecordsDenied("MANUAL_TAKEOVER_ACTIVE")
            if active and active["lock_kind"] == "SCHEDULING_ONLY" and action not in {"TIMEZONE_CLARIFICATION", "OFFER_CURRENT_SLOTS", "CONFIRM_EXACT_SLOT"}:
                raise ProductRecordsDenied("SCHEDULING_ONLY_RESTRICTED")

    @safe_records
    async def record_referral(self, request: ReferralRequest, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            context = await self._context(connection, request.context_id)
            if context is None or not await self._span_exists(connection, context, request.membership_span) or not await self._span_exists(connection, context, request.relevance_span):
                raise ProductRecordsDenied("REFERRAL_EVIDENCE_MISMATCH")
            await lock_experiment(connection, context["experiment_id"])
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_RECIPIENT_REFERRAL", request_hash)
            if prior:
                return CommandReceipt(command_id=prior["id"], result_id=prior["result_id"])
            await connection.execute(text("""INSERT INTO record_conversation_referrals (id,experiment_id,conversation_id,context_id,source_document_id,source_span_ordinal,organization_id,referred_recipient_id,referred_recipient_source_id,content_hash,created_at)
                VALUES (:id,:experiment_id,:conversation_id,:context_id,:source_document_id,:source_span_ordinal,:organization_id,:referred_recipient_id,:referred_recipient_source_id,:content_hash,:created_at)"""), {**context, **request.model_dump(exclude={"membership_span", "relevance_span"}), "source_document_id": request.relevance_span.document_id, "source_span_ordinal": request.relevance_span.ordinal, "created_at": self.clock()})
            for role, span in (("ORGANIZATION_MEMBERSHIP", request.membership_span), ("RELEVANCE", request.relevance_span)):
                await connection.execute(text("INSERT INTO record_conversation_referral_evidence (referral_id,document_id,span_ordinal,role) VALUES (:referral_id,:document_id,:span_ordinal,:role)"), {"referral_id": request.id, "document_id": span.document_id, "span_ordinal": span.ordinal, "role": role})
            return await self._receipt(connection, command_key, "RECORD_RECIPIENT_REFERRAL", request_hash, "RECIPIENT_REFERRAL", request.id, context["experiment_id"])

    @safe_records
    async def record_follow_up(self, request: FollowUpRequest, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            context = await self._context(connection, request.context_id)
            if context is None or not await self._span_exists(connection, context, request.source_span):
                raise ProductRecordsDenied("FOLLOW_UP_EVIDENCE_MISMATCH")
            await lock_experiment(connection, context["experiment_id"])
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_LEAD_FOLLOW_UP", request_hash)
            if prior:
                return CommandReceipt(command_id=prior["id"], result_id=prior["result_id"])
            await connection.execute(text("""INSERT INTO record_conversation_follow_ups (id,experiment_id,conversation_id,context_id,source_document_id,source_span_ordinal,disposition,date_kind,start_date,end_date,timezone,content_hash,created_at)
                VALUES (:id,:experiment_id,:conversation_id,:context_id,:source_document_id,:source_span_ordinal,:disposition,:date_kind,:start_date,:end_date,:timezone,:content_hash,:created_at)"""), {**context, **request.model_dump(exclude={"source_span"}), "source_document_id": request.source_span.document_id, "source_span_ordinal": request.source_span.ordinal, "created_at": self.clock()})
            return await self._receipt(connection, command_key, "RECORD_LEAD_FOLLOW_UP", request_hash, "LEAD_FOLLOW_UP", request.id, context["experiment_id"])

    async def _manual_authority(self, connection, context, lock_id, operator_id):
        active = await self._active_lock(connection, context["conversation_id"])
        operator = await connection.scalar(text("SELECT 1 FROM record_operators WHERE id=:id AND status='ACTIVE'"), {"id": operator_id})
        if active is None or active["lock_kind"] != "MANUAL_TAKEOVER" or active["id"] != lock_id or not operator:
            raise ProductRecordsDenied("MANUAL_TAKEOVER_REQUIRED")

    @safe_records
    async def record_manual_outcome(self, request: ManualOutcomeRequest, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            context = await self._context(connection, request.context_id)
            if context is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            await lock_experiment(connection, context["experiment_id"])
            await self._manual_authority(connection, context, request.active_lock_event_id, request.operator_id)
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_MANUAL_OUTCOME", request_hash)
            if prior:
                return CommandReceipt(command_id=prior["id"], result_id=prior["result_id"])
            await connection.execute(text("INSERT INTO record_conversation_manual_outcomes (id,experiment_id,conversation_id,context_id,operator_id,active_lock_event_id,outcome,content_hash,created_at) VALUES (:id,:experiment_id,:conversation_id,:context_id,:operator_id,:active_lock_event_id,:outcome,:content_hash,:created_at)"), {**context, **request.model_dump(), "created_at": self.clock()})
            return await self._receipt(connection, command_key, "RECORD_MANUAL_OUTCOME", request_hash, "MANUAL_OUTCOME", request.id, context["experiment_id"])

    @safe_records
    async def record_operator_message(self, request: OperatorMessageRequest, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            context = await self._context(connection, request.context_id)
            if context is None or any(context[key] != getattr(request, key) for key in ("organization_id", "recipient_id", "recipient_source_id", "thread_identity_hash")):
                raise ProductRecordsDenied("OPERATOR_MESSAGE_LINEAGE_MISMATCH")
            await lock_experiment(connection, context["experiment_id"])
            await self._manual_authority(connection, context, request.active_lock_event_id, request.operator_id)
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_OPERATOR_MESSAGE", request_hash)
            if prior:
                return CommandReceipt(command_id=prior["id"], result_id=prior["result_id"])
            await connection.execute(text("""INSERT INTO record_conversation_operator_messages (id,experiment_id,conversation_id,context_id,operator_id,organization_id,recipient_id,recipient_source_id,thread_identity_hash,active_lock_event_id,body_hash,content_hash,created_at)
                VALUES (:id,:experiment_id,:conversation_id,:context_id,:operator_id,:organization_id,:recipient_id,:recipient_source_id,:thread_identity_hash,:active_lock_event_id,:body_hash,:content_hash,:created_at)"""), {**context, **request.model_dump(), "created_at": self.clock()})
            return await self._receipt(connection, command_key, "RECORD_OPERATOR_MESSAGE", request_hash, "OPERATOR_MESSAGE", request.id, context["experiment_id"])

    @safe_records
    async def record_booking_intent(self, request: BookingIntentRequest, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            context = await self._context(connection, request.context_id)
            if context is None or not await self._span_exists(connection, context, request.source_span):
                raise ProductRecordsDenied("BOOKING_INTENT_LINEAGE_MISMATCH")
            await lock_experiment(connection, context["experiment_id"])
            active = await self._active_lock(connection, context["conversation_id"])
            scheduling = await connection.scalar(text("SELECT 1 FROM record_conversation_handoffs WHERE id=:id AND conversation_id=:conversation_id AND kind='MEETING_SCHEDULING'"), {"id": request.scheduling_handoff_id, "conversation_id": context["conversation_id"]})
            if active is None or active["lock_kind"] != "SCHEDULING_ONLY" or active["related_handoff_id"] != request.scheduling_handoff_id or not scheduling:
                raise ProductRecordsDenied("SCHEDULING_LOCK_REQUIRED")
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_BOOKING_INTENT", request_hash)
            if prior:
                return CommandReceipt(command_id=prior["id"], result_id=prior["result_id"])
            await connection.execute(text("""INSERT INTO record_conversation_booking_intents (id,experiment_id,conversation_id,context_id,scheduling_handoff_id,source_document_id,source_span_ordinal,offer_acceptance_id,offer_id,profile_id,policy_id,recipient_id,slot_hash,attendee_hash,intent_hash,content_hash,created_at)
                VALUES (:id,:experiment_id,:conversation_id,:context_id,:scheduling_handoff_id,:source_document_id,:source_span_ordinal,:offer_acceptance_id,:offer_id,:profile_id,:policy_id,:recipient_id,:slot_hash,:attendee_hash,:intent_hash,:content_hash,:created_at)"""), {**context, **request.model_dump(exclude={"source_span"}), "source_document_id": request.source_span.document_id, "source_span_ordinal": request.source_span.ordinal, "created_at": self.clock()})
            return await self._receipt(connection, command_key, "RECORD_BOOKING_INTENT", request_hash, "BOOKING_INTENT", request.id, context["experiment_id"])

    @safe_records
    async def record_booking_confirmation(self, request: BookingConfirmationRequest, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            context = (
                (
                    await connection.execute(text("""SELECT i.experiment_id,i.conversation_id,i.context_id FROM record_conversation_booking_intents i WHERE i.id=:id"""), {"id": request.intent_id})
                )
                .mappings()
                .one_or_none()
            )
            if context is None or not await self._span_exists(connection, context, request.source_span):
                raise ProductRecordsDenied("BOOKING_CONFIRMATION_LINEAGE_MISMATCH")
            await lock_experiment(connection, context["experiment_id"])
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_BOOKING_CONFIRMATION", request_hash)
            if prior:
                return CommandReceipt(command_id=prior["id"], result_id=prior["result_id"])
            await connection.execute(text("""INSERT INTO record_conversation_booking_confirmations (id,intent_id,source_document_id,source_span_ordinal,confirmation_hash,slot_hash,attendee_hash,content_hash,created_at)
                VALUES (:id,:intent_id,:source_document_id,:source_span_ordinal,:confirmation_hash,:slot_hash,:attendee_hash,:content_hash,:created_at)"""), {**request.model_dump(exclude={"source_span"}), "source_document_id": request.source_span.document_id, "source_span_ordinal": request.source_span.ordinal, "created_at": self.clock()})
            return await self._receipt(connection, command_key, "RECORD_BOOKING_CONFIRMATION", request_hash, "BOOKING_CONFIRMATION", request.id, context["experiment_id"])

    @safe_records
    async def record_booking_observation(self, request: BookingObservationRequest, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            context = (
                (
                    await connection.execute(text("SELECT experiment_id FROM record_conversation_booking_intents WHERE id=:id"), {"id": request.intent_id})
                )
                .mappings()
                .one_or_none()
            )
            if context is None:
                raise ProductRecordsDenied("BOOKING_OBSERVATION_MISMATCH")
            await lock_experiment(connection, context["experiment_id"])
            request_hash = _request_hash(request=request)
            prior = await _existing(connection, command_key, "RECORD_BOOKING_OBSERVATION", request_hash)
            if prior:
                return CommandReceipt(command_id=prior["id"], result_id=prior["result_id"])
            await connection.execute(text("""INSERT INTO record_conversation_booking_observations (id,intent_id,confirmation_id,provider_call_id,provider_evidence_id,provider_event_hash,slot_hash,attendee_hash,content_hash,observed_at)
                VALUES (:id,:intent_id,:confirmation_id,:provider_call_id,:provider_evidence_id,:provider_event_hash,:slot_hash,:attendee_hash,:content_hash,:observed_at)"""), request.model_dump())
            return await self._receipt(connection, command_key, "RECORD_BOOKING_OBSERVATION", request_hash, "BOOKING_OBSERVATION", request.id, context["experiment_id"])
