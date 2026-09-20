"""Transactional immutable conversation response records."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.records.conversation_models import (
    ConversationRecordReceipt,
    RecordConversationDocumentsRequest,
)
from alon_ai.records.models import ProductRecordsDenied
from alon_ai.records.repository import _complete, _existing, _request_hash, safe_records


class ConversationRecordsRepository:
    def __init__(self, engine: AsyncEngine, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.engine, self.clock = engine, clock

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
                    VALUES (:id,:experiment_id,:conversation_id,:context_id,:kind,:version,:content::jsonb,:content_hash,:rule_version,:created_by,:created_at)"""), {"id": item.id, "experiment_id": context["experiment_id"], "conversation_id": context["conversation_id"], "context_id": request.context_id, "kind": item.kind, "version": item.version, "content": json.dumps(item.content, sort_keys=True), "content_hash": item.content_hash, "rule_version": item.rule_version, "created_by": request.recorded_by, "created_at": self.clock()})
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
                    VALUES (:id,:conversation_id,:experiment_id,:context_id,:fact_key,:version,:status,:value::jsonb,:source_document_id,:content_hash,:supersedes_id,:created_at)"""), {"id": fact.id, "conversation_id": context["conversation_id"], "experiment_id": context["experiment_id"], "context_id": request.context_id, "fact_key": fact.fact_key, "version": fact.version, "status": fact.status, "value": json.dumps(fact.value, sort_keys=True), "source_document_id": fact.source_document_id, "content_hash": fact.content_hash, "supersedes_id": fact.supersedes_id, "created_at": self.clock()})
            command_id = await _complete(connection, command_key=command_key, experiment_id=context["experiment_id"], kind="RECORD_CONVERSATION_DOCUMENTS", request_hash=request_hash, result_type="CONVERSATION_DOCUMENTS", result_id=request.context_id, now=self.clock())
            return ConversationRecordReceipt(command_id=command_id, result_id=request.context_id, conversation_id=context["conversation_id"], document_ids=tuple(item.id for item in request.documents))
