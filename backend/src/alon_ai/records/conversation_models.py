"""Strict immutable inputs shared by conversation persistence commands."""

from datetime import date
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, Field, model_validator

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


class EvidenceSpanReference(StrictDTO):
    document_id: UUID
    ordinal: int = Field(ge=1)


class HandoffRequest(StrictDTO):
    id: UUID
    context_id: UUID
    source_span: EvidenceSpanReference
    kind: Literal["INVOICE", "DEMO", "MEETING_SCHEDULING", "MEETING_BOOKING"]
    content: dict
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: UUID
    booking_observation_id: UUID | None = None
    recorded_by: UUID

    @model_validator(mode="after")
    def booking_observation_is_complete(self):
        booking = self.kind == "MEETING_BOOKING"
        if booking != (self.booking_observation_id is not None):
            raise ValueError("booking requires exact confirmed provider observation")
        return self


class HandoffReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID
    handoff_id: UUID
    action_id: UUID
    source_intent_hash: str


class ReferralRequest(StrictDTO):
    id: UUID
    context_id: UUID
    referred_recipient_id: UUID
    referred_recipient_source_id: UUID
    membership_span: EvidenceSpanReference
    relevance_span: EvidenceSpanReference
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class FollowUpRequest(StrictDTO):
    id: UUID
    context_id: UUID
    source_span: EvidenceSpanReference
    disposition: Literal["EXPLICIT"]
    date_kind: Literal["DATE", "RANGE"]
    start_date: date
    end_date: date | None = None
    timezone: str = Field(min_length=1, max_length=100)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def explicit_date_range_is_valid(self):
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be an IANA timezone") from error
        if self.date_kind == "DATE" and self.end_date is not None:
            raise ValueError("an explicit date has no end date")
        if self.date_kind == "RANGE" and (
            self.end_date is None or self.end_date <= self.start_date
        ):
            raise ValueError("an explicit range must end after it starts")
        return self


class ManualOutcomeRequest(StrictDTO):
    id: UUID
    context_id: UUID
    operator_id: UUID
    active_lock_event_id: UUID
    outcome: Literal["DEMO_PREPARING", "DEMO_SENT", "DEMO_ACCEPTED", "DEMO_DECLINED", "INVOICE_PREPARING", "INVOICE_SENT", "PAYMENT_PENDING", "PAID", "PAYMENT_FAILED", "MEETING_BOOKED", "MEETING_COMPLETED", "MEETING_CANCELLED", "NO_SHOW", "MANUAL_NEGOTIATION", "MANUALLY_CLOSED"]
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class OperatorMessageRequest(StrictDTO):
    id: UUID
    context_id: UUID
    operator_id: UUID
    organization_id: UUID
    recipient_id: UUID
    recipient_source_id: UUID
    thread_identity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    active_lock_event_id: UUID
    body_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class BookingIntentRequest(StrictDTO):
    id: UUID
    context_id: UUID
    scheduling_handoff_id: UUID
    source_span: EvidenceSpanReference
    slot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    attendee_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class BookingConfirmationRequest(StrictDTO):
    id: UUID
    intent_id: UUID
    source_span: EvidenceSpanReference
    confirmation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    slot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    attendee_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class BookingObservationRequest(StrictDTO):
    id: UUID
    intent_id: UUID
    confirmation_id: UUID
    provider_call_id: UUID
    provider_evidence_id: UUID
    provider_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    slot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    attendee_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: AwareDatetime
