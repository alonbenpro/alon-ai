"""Strict immutable inputs shared by conversation persistence commands."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from alon_ai.providers.contracts import StrictDTO


class ReplyEvidenceSpan(StrictDTO):
    message_id: UUID
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)

    @model_validator(mode="after")
    def has_content(self):
        if self.end_offset <= self.start_offset:
            raise ValueError("evidence span must contain text")
        return self


class ConversationDocumentInput(StrictDTO):
    id: UUID
    kind: Literal[
        "INBOUND_CONTENT_SAFETY_ASSESSMENT",
        "SENDER_IDENTITY_DECISION",
        "REPLY_INTERPRETATION",
        "REPLY_QUESTION",
        "REPLY_OBJECTION",
        "CONVERSATION_DECISION",
        "CONVERSION_READINESS_DECISION",
        "ALLOWED_RESPONSE_OBJECTIVE",
        "COMMERCIAL_DISCLOSURE_DECISION",
        "NEGOTIATION_OPTION_SET",
        "BUDGET_EVIDENCE",
        "TIMELINE_EVIDENCE",
        "RESPONSE_PLAN",
        "RESPONSE_DRAFT",
        "RESPONSE_VALIDATION_RESULT",
    ]
    version: int = Field(ge=1)
    content: dict
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_version: str | None = Field(default=None, min_length=1, max_length=100)
    spans: tuple[ReplyEvidenceSpan, ...] = Field(max_length=100)


class ConversationRecordReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID
    conversation_id: UUID
    document_ids: tuple[UUID, ...]


class ConversationFactInput(StrictDTO):
    id: UUID
    fact_key: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    version: int = Field(ge=1)
    status: Literal["EXPLICITLY_STATED", "REASONABLE_INTERPRETATION", "UNKNOWN", "CONTRADICTED"]
    value: dict | None = None
    source_document_id: UUID
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    supersedes_id: UUID | None = None


class RecordConversationDocumentsRequest(StrictDTO):
    context_id: UUID
    documents: tuple[ConversationDocumentInput, ...] = Field(min_length=1, max_length=30)
    facts: tuple[ConversationFactInput, ...] = Field(max_length=30)
    recorded_by: UUID

    @model_validator(mode="after")
    def document_keys_are_unique(self):
        keys = {(item.kind, item.version) for item in self.documents}
        if len(keys) != len(self.documents) or len({item.id for item in self.documents}) != len(self.documents):
            raise ValueError("conversation documents must have unique identities and versions")
        if len({(item.fact_key, item.version) for item in self.facts}) != len(self.facts):
            raise ValueError("fact keys and versions must be unique")
        return self
