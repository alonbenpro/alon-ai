"""Immutable conversation and response-decision persistence."""

from datetime import date
from hashlib import sha256
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from test_offer_records import put
from test_organization_records import complete_content, provision_call
from test_product_records import NOW, artifact
from test_qualification_cohorts import (
    KEY,
    OWNER,
    decision_request,
    dossier_request,
    qualified_pool,
)

from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.db.repositories.records_conversation import ConversationRecordsRepository
from alon_ai.db.repositories.records_operators import OperatorRepository
from alon_ai.db.repositories.records_outreach import OutreachRecordsRepository
from alon_ai.db.repositories.records_qualifications import QualificationCohortRepository
from alon_ai.integrations.schemas.provider import Capability, ContentField
from alon_ai.services.schemas.records import (
    ArtifactInput,
    ArtifactKind,
    ProductRecordsDenied,
)
from alon_ai.services.schemas.records_conversation import (
    BookingConfirmationRequest,
    BookingIntentRequest,
    BookingObservationRequest,
    ConversationDocumentInput,
    EvidenceSpanReference,
    FollowUpRequest,
    HandoffRequest,
    ManualOutcomeRequest,
    OperatorMessageRequest,
    RecordConversationDocumentsRequest,
    ReferralRequest,
    ReplyEvidenceSpan,
)
from alon_ai.services.schemas.records_operator import OperatorIdentity
from alon_ai.services.schemas.records_outreach import (
    EvidenceCoverageInput,
    FreezeOutreachContextRequest,
)
from alon_ai.services.schemas.records_qualification import FreezeCohortRequest

pytestmark = pytest.mark.integration


def test_conversation_artifact_contract_is_available():
    """Removing a conversation artifact kind breaks downstream immutable lineage."""
    assert ArtifactKind.CONVERSATION_TURN_CONTEXT.value == "CONVERSATION_TURN_CONTEXT"


def test_handoff_artifact_contract_is_available():
    """Removing handoff artifacts breaks immutable operator ownership lineage."""
    assert ArtifactKind.INVOICE_HANDOFF_BRIEF.value == "INVOICE_HANDOFF_BRIEF"


async def test_conversation_turn_context_table_is_migrated(governance_engine):
    """Dropping turn-context persistence makes immutable reply reconstruction impossible."""
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT to_regclass('record_conversation_turn_contexts')")
            )
            == "record_conversation_turn_contexts"
        )


async def test_handoff_and_lock_tables_are_migrated(governance_engine):
    """Removing handoff locks makes operator ownership unenforceable."""
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT to_regclass('record_conversation_handoffs')")
            )
            == "record_conversation_handoffs"
        )
        assert (
            await connection.scalar(
                text("SELECT to_regclass('record_conversation_lock_events')")
            )
            == "record_conversation_lock_events"
        )


def test_reply_evidence_span_rejects_empty_offsets():
    """Allowing an empty span would detach an interpretation from reply evidence."""
    with pytest.raises(ValidationError):
        ReplyEvidenceSpan(message_id=UUID(int=1), start_offset=4, end_offset=4)


def _hash(value: str) -> str:
    return sha256(value.encode()).hexdigest()


async def _phase2_graph(engine):
    """Build one governed turn from the existing fixed-50 context workflow."""
    experiment_id, acceptance, criteria, plan, _, _, leads = await qualified_pool(
        engine, size=50
    )
    qualifications = QualificationCohortRepository(
        engine, lookup_key=KEY, clock=lambda: NOW
    )
    dossiers, decisions = [], []
    for index, lead in enumerate(leads):
        dossier = await qualifications.record_dossier(
            dossier_request(acceptance, lead, index), command_key=UUID(int=1000 + index)
        )
        dossiers.append(dossier)
        decisions.append(
            await qualifications.decide(
                await decision_request(
                    lead, dossier, criteria, policy_ref=plan.qualification_rule_id
                ),
                command_key=UUID(int=2000 + index),
            )
        )
    cohort = await qualifications.freeze_cohort(
        FreezeCohortRequest(
            offer_acceptance_id=acceptance["id"],
            decision_ids=tuple(item.id for item in decisions),
            frozen_by=OWNER,
        ),
        command_key=UUID(int=3000),
    )
    model_call = await provision_call(
        engine, experiment_id, Capability.OPENAI_GENERATE, {ContentField.COMPANY}
    )
    prompt = await put(
        ProductRecordsRepository(engine, clock=lambda: NOW),
        experiment_id,
        ArtifactKind.OUTREACH_PROMPT_CONFIGURATION,
        {"template": "Use the frozen governed context."},
    )
    frozen = await OutreachRecordsRepository(
        engine, lookup_key=KEY, clock=lambda: NOW
    ).freeze_context(
        FreezeOutreachContextRequest(
            cohort_id=cohort.id,
            decision_id=decisions[0].id,
            artifact=artifact(
                experiment_id,
                ArtifactKind.OUTREACH_CONTEXT_BUNDLE,
                {
                    "status": "FROZEN",
                    "recipient_mode": "GENERAL_BUSINESS_INBOX",
                    "recipient_label": None,
                    "greeting": "Hello team",
                },
            ),
            prompt_configuration=ArtifactInput.from_receipt(
                prompt, role="PROMPT_CONFIGURATION"
            ),
            model_config_id=model_call[2].id,
            coverage=(
                EvidenceCoverageInput(
                    evidence_id=dossiers[0].evidence_ids[0], disposition="USED"
                ),
            ),
            frozen_by=OWNER,
        ),
        command_key=UUID(int=4000),
    )
    async with engine.begin() as connection:
        frozen_row = (
            (
                await connection.execute(
                    text("SELECT * FROM record_outreach_contexts WHERE id=:id"),
                    {"id": frozen.id},
                )
            )
            .mappings()
            .one()
        )
        campaign_id, conversation_id, message_id, turn_id = (
            UUID(int=value) for value in range(5001, 5005)
        )
        await connection.execute(
            text("""INSERT INTO record_conversation_campaigns (id,experiment_id,cohort_id,offer_acceptance_id,offer_id,profile_id,policy_id,content_hash,created_by,created_at)
            VALUES (:id,:experiment_id,:cohort_id,:offer_acceptance_id,:offer_id,:profile_id,:policy_id,:content_hash,:created_by,:created_at)"""),
            {
                "id": campaign_id,
                "experiment_id": experiment_id,
                "cohort_id": cohort.id,
                "offer_acceptance_id": frozen_row["offer_acceptance_id"],
                "offer_id": frozen_row["offer_id"],
                "profile_id": frozen_row["profile_id"],
                "policy_id": frozen_row["policy_id"],
                "content_hash": _hash("campaign"),
                "created_by": OWNER,
                "created_at": NOW,
            },
        )
        await connection.execute(
            text("""INSERT INTO record_conversations (id,experiment_id,campaign_id,outreach_context_id,cohort_member_ordinal,organization_id,recipient_id,recipient_source_id,supported_contact_source_id,offer_acceptance_id,offer_id,profile_id,policy_id,thread_identity_hash,created_at)
            VALUES (:id,:experiment_id,:campaign_id,:outreach_context_id,1,:organization_id,:recipient_id,:recipient_source_id,:supported_contact_source_id,:offer_acceptance_id,:offer_id,:profile_id,:policy_id,:thread_identity_hash,:created_at)"""),
            {
                "id": conversation_id,
                "experiment_id": experiment_id,
                "campaign_id": campaign_id,
                "outreach_context_id": frozen.id,
                "organization_id": frozen_row["organization_id"],
                "recipient_id": frozen_row["recipient_id"],
                "recipient_source_id": frozen_row["recipient_source_id"],
                "supported_contact_source_id": frozen_row["contact_source_id"],
                "offer_acceptance_id": frozen_row["offer_acceptance_id"],
                "offer_id": frozen_row["offer_id"],
                "profile_id": frozen_row["profile_id"],
                "policy_id": frozen_row["policy_id"],
                "thread_identity_hash": _hash("thread"),
                "created_at": NOW,
            },
        )
        body = "Jamie is our operations lead. Please follow up from 2026-10-01 through 2026-10-03."
        await connection.execute(
            text("""INSERT INTO record_conversation_messages (id,conversation_id,experiment_id,ordinal,direction,sanitized_body,sanitized_hash,raw_hash,received_at)
            VALUES (:id,:conversation_id,:experiment_id,1,'INBOUND',:body,:sanitized_hash,:raw_hash,:received_at)"""),
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "experiment_id": experiment_id,
                "body": body,
                "sanitized_hash": _hash(body),
                "raw_hash": _hash("raw reply"),
                "received_at": NOW,
            },
        )
        await connection.execute(
            text("""INSERT INTO record_conversation_turn_contexts (id,experiment_id,conversation_id,inbound_message_id,outreach_context_id,offer_acceptance_id,offer_id,profile_id,policy_id,dossier_id,matrix_id,decision_id,recipient_source_id,context_hash,version,created_by,created_at)
            VALUES (:id,:experiment_id,:conversation_id,:inbound_message_id,:outreach_context_id,:offer_acceptance_id,:offer_id,:profile_id,:policy_id,:dossier_id,:matrix_id,:decision_id,:recipient_source_id,:context_hash,1,:created_by,:created_at)"""),
            {
                "id": turn_id,
                "experiment_id": experiment_id,
                "conversation_id": conversation_id,
                "inbound_message_id": message_id,
                "outreach_context_id": frozen.id,
                "offer_acceptance_id": frozen_row["offer_acceptance_id"],
                "offer_id": frozen_row["offer_id"],
                "profile_id": frozen_row["profile_id"],
                "policy_id": frozen_row["policy_id"],
                "dossier_id": frozen_row["dossier_id"],
                "matrix_id": frozen_row["matrix_id"],
                "decision_id": frozen_row["decision_id"],
                "recipient_source_id": frozen_row["recipient_source_id"],
                "context_hash": _hash("turn"),
                "created_by": OWNER,
                "created_at": NOW,
            },
        )
    repo = ConversationRecordsRepository(engine, clock=lambda: NOW)
    document_id = UUID(int=5005)
    start = body.index("Jamie")
    lead_end = body.index(". Please")
    date_start = body.index("2026-10-01")
    await repo.record_documents(
        RecordConversationDocumentsRequest(
            context_id=turn_id,
            documents=(
                ConversationDocumentInput(
                    id=document_id,
                    kind="REPLY_INTERPRETATION",
                    version=1,
                    content={
                        "classification": "EXPLICIT",
                        "follow_up": {
                            "disposition": "EXPLICIT",
                            "span_ordinal": 3,
                            "date_kind": "RANGE",
                            "start_date": "2026-10-01",
                            "end_date": "2026-10-03",
                            "timezone": "Asia/Jerusalem",
                        },
                    },
                    content_hash=_hash("interpretation"),
                    spans=(
                        ReplyEvidenceSpan(
                            message_id=message_id,
                            start_offset=start,
                            end_offset=start + 5,
                        ),
                        ReplyEvidenceSpan(
                            message_id=message_id, start_offset=6, end_offset=lead_end
                        ),
                        ReplyEvidenceSpan(
                            message_id=message_id,
                            start_offset=date_start,
                            end_offset=len(body) - 1,
                        ),
                    ),
                ),
            ),
            facts=(),
            recorded_by=OWNER,
        ),
        command_key=UUID(int=5006),
    )
    operator_id = UUID(int=5007)
    await OperatorRepository(engine, clock=lambda: NOW).register_operator(
        OperatorIdentity(
            id=operator_id,
            auth_subject="operator-phase2",
            display_name="Phase 2 Operator",
        ),
        command_key=UUID(int=5008),
    )
    provider_call = await provision_call(
        engine, experiment_id, Capability.FIRECRAWL_PAGE_CAPTURE, {ContentField.COMPANY}
    )
    _, _, provider_evidence, _, _ = await complete_content(
        engine, provider_call, {ContentField.COMPANY: ("booking confirmation",)}
    )
    return {
        "repo": repo,
        "experiment_id": experiment_id,
        "context_id": turn_id,
        "conversation_id": conversation_id,
        "document_id": document_id,
        "membership": EvidenceSpanReference(document_id=document_id, ordinal=1),
        "relevance": EvidenceSpanReference(document_id=document_id, ordinal=2),
        "date_span": EvidenceSpanReference(document_id=document_id, ordinal=3),
        "recipient_id": frozen_row["recipient_id"],
        "recipient_source_id": frozen_row["recipient_source_id"],
        "organization_id": frozen_row["organization_id"],
        "thread_identity_hash": _hash("thread"),
        "operator_id": operator_id,
        "provider_call_id": provider_call[4],
        "provider_evidence_id": provider_evidence,
    }


async def test_phase2_normalized_commands_preserve_lineage_and_locks(governance_engine):
    graph = await _phase2_graph(governance_engine)
    repo = graph["repo"]
    referral = ReferralRequest(
        id=UUID(int=6001),
        context_id=graph["context_id"],
        referred_recipient_id=graph["recipient_id"],
        referred_recipient_source_id=graph["recipient_source_id"],
        membership_span=graph["membership"],
        relevance_span=graph["relevance"],
        content_hash=_hash("referral"),
    )
    referral_key = UUID(int=6002)
    receipt = await repo.record_referral(referral, command_key=referral_key)
    assert await repo.record_referral(referral, command_key=referral_key) == receipt
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.record_referral(
            referral.model_copy(update={"content_hash": _hash("changed")}),
            command_key=referral_key,
        )
    with pytest.raises(ProductRecordsDenied):
        await repo.record_referral(
            referral.model_copy(
                update={
                    "id": UUID(int=6099),
                    "referred_recipient_source_id": UUID(int=1),
                }
            ),
            command_key=UUID(int=6099),
        )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_conversation_referral_evidence WHERE referral_id=:id"
                ),
                {"id": referral.id},
            )
            == 2
        )
    follow_up = FollowUpRequest(
        id=UUID(int=6003),
        context_id=graph["context_id"],
        source_span=graph["date_span"],
        disposition="EXPLICIT",
        date_kind="RANGE",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 3),
        timezone="Asia/Jerusalem",
        content_hash=_hash("follow-up"),
    )
    await repo.record_follow_up(follow_up, command_key=UUID(int=6004))
    with pytest.raises(ProductRecordsDenied):
        await repo.record_follow_up(
            follow_up.model_copy(
                update={
                    "id": UUID(int=6098),
                    "source_span": EvidenceSpanReference(
                        document_id=UUID(int=1), ordinal=1
                    ),
                }
            ),
            command_key=UUID(int=6098),
        )
    with pytest.raises(ValidationError):
        FollowUpRequest(
            id=UUID(int=6005),
            context_id=graph["context_id"],
            source_span=graph["date_span"],
            disposition="EXPLICIT",
            date_kind="DATE",
            start_date=date(2026, 10, 1),
            timezone="not/a-timezone",
            content_hash=_hash("vague"),
        )
    with pytest.raises(ValidationError):
        FollowUpRequest.model_validate(
            {
                "id": UUID(int=6005),
                "context_id": graph["context_id"],
                "source_span": graph["date_span"],
                "disposition": "VAGUE",
                "date_kind": "DATE",
                "start_date": date(2026, 10, 1),
                "timezone": "Asia/Jerusalem",
                "content_hash": _hash("vague"),
            }
        )
    with pytest.raises(ProductRecordsDenied, match="FOLLOW_UP_EVIDENCE_MISMATCH"):
        await repo.record_follow_up(
            follow_up.model_copy(
                update={"id": UUID(int=6095), "start_date": date(2026, 10, 2)}
            ),
            command_key=UUID(int=6095),
        )
    vague_document_id = UUID(int=6100)
    async with governance_engine.begin() as connection:
        await connection.execute(
            text("""INSERT INTO record_conversation_documents
            (id,experiment_id,conversation_id,context_id,kind,version,content,content_hash,rule_version,created_by,created_at)
            SELECT :id,experiment_id,conversation_id,context_id,kind,2,
              '{"classification":"VAGUE"}'::jsonb,:hash,rule_version,created_by,created_at
            FROM record_conversation_documents WHERE id=:source"""),
            {
                "id": vague_document_id,
                "source": graph["document_id"],
                "hash": _hash("vague interpretation"),
            },
        )
        await connection.execute(
            text("""INSERT INTO record_conversation_evidence_spans
            (document_id,message_id,ordinal,start_offset,end_offset,excerpt_hash)
            SELECT :id,message_id,ordinal,start_offset,end_offset,excerpt_hash
            FROM record_conversation_evidence_spans WHERE document_id=:source"""),
            {"id": vague_document_id, "source": graph["document_id"]},
        )
    vague_follow_up = follow_up.model_copy(
        update={
            "id": UUID(int=6101),
            "source_span": EvidenceSpanReference(
                document_id=vague_document_id, ordinal=3
            ),
        }
    )
    with pytest.raises(ProductRecordsDenied, match="FOLLOW_UP_EVIDENCE_MISMATCH"):
        await repo.record_follow_up(vague_follow_up, command_key=UUID(int=6101))
    async with governance_engine.connect() as connection:
        with pytest.raises(
            SQLAlchemyError, match="follow-up explicit interpretation mismatch"
        ):
            await connection.execute(
                text("""INSERT INTO record_conversation_follow_ups
                (id,experiment_id,conversation_id,context_id,source_document_id,source_span_ordinal,
                 disposition,date_kind,start_date,end_date,timezone,content_hash,created_at)
                VALUES (:id,:experiment_id,:conversation_id,:context_id,:source_document_id,3,
                 'EXPLICIT','RANGE',:start_date,:end_date,:timezone,:content_hash,:created_at)"""),
                {
                    "id": vague_follow_up.id,
                    "experiment_id": graph["experiment_id"],
                    "conversation_id": graph["conversation_id"],
                    "context_id": graph["context_id"],
                    "source_document_id": vague_document_id,
                    "start_date": date(2026, 10, 1),
                    "end_date": date(2026, 10, 3),
                    "timezone": "Asia/Jerusalem",
                    "content_hash": _hash("forged follow-up"),
                    "created_at": NOW,
                },
            )
        await connection.rollback()
    scheduling = HandoffRequest(
        id=UUID(int=6006),
        context_id=graph["context_id"],
        source_span=graph["date_span"],
        kind="MEETING_SCHEDULING",
        content={"request": "schedule"},
        content_hash=_hash("scheduling"),
        action_id=UUID(int=6007),
        recorded_by=OWNER,
    )
    scheduling_receipt = await repo.record_handoff(
        scheduling, command_key=UUID(int=6008)
    )
    assert (
        await repo.record_handoff(scheduling, command_key=UUID(int=6008))
        == scheduling_receipt
    )
    with pytest.raises(ProductRecordsDenied):
        await repo.record_handoff(scheduling, command_key=UUID(int=6097))
    async with governance_engine.connect() as connection:
        with pytest.raises(SQLAlchemyError):
            await connection.execute(
                text("""INSERT INTO record_conversation_lock_events (id,experiment_id,conversation_id,lock_kind,event_kind,content_hash,created_at)
                VALUES (:id,:experiment_id,:conversation_id,'MANUAL_TAKEOVER','ACTIVATE',:content_hash,:created_at)"""),
                {
                    "id": UUID(int=6999),
                    "experiment_id": graph["experiment_id"],
                    "conversation_id": graph["conversation_id"],
                    "content_hash": _hash("invalid lock"),
                    "created_at": NOW,
                },
            )
        await connection.rollback()
    await repo.assert_automation_allowed(graph["context_id"], "CONFIRM_EXACT_SLOT")
    with pytest.raises(ProductRecordsDenied, match="SCHEDULING_ONLY_RESTRICTED"):
        await repo.assert_automation_allowed(graph["context_id"], "NEGOTIATE_PRICE")
    intent = BookingIntentRequest(
        id=UUID(int=6009),
        context_id=graph["context_id"],
        scheduling_handoff_id=scheduling.id,
        source_span=graph["date_span"],
        slot_hash=_hash("slot"),
        attendee_hash=_hash("attendee"),
        intent_hash=_hash("intent"),
        content_hash=_hash("booking intent"),
    )
    async with governance_engine.connect() as connection:
        lineage = (
            (
                await connection.execute(
                    text("""SELECT t.offer_acceptance_id,t.offer_id,t.profile_id,t.policy_id,c.recipient_id
            FROM record_conversation_turn_contexts t JOIN record_conversations c ON c.id=t.conversation_id
            WHERE t.id=:id"""),
                    {"id": graph["context_id"]},
                )
            )
            .mappings()
            .one()
        )
    for changed in ("offer_acceptance_id", "profile_id"):
        forged = dict(lineage)
        forged[changed] = UUID(int=6199)
        async with governance_engine.connect() as connection:
            with pytest.raises(
                SQLAlchemyError, match="booking intent commercial lineage mismatch"
            ):
                await connection.execute(
                    text("""INSERT INTO record_conversation_booking_intents
                    (id,experiment_id,conversation_id,context_id,scheduling_handoff_id,source_document_id,
                     source_span_ordinal,offer_acceptance_id,offer_id,profile_id,policy_id,recipient_id,
                     slot_hash,attendee_hash,intent_hash,content_hash,created_at)
                    VALUES (:id,:experiment_id,:conversation_id,:context_id,:scheduling_handoff_id,
                     :source_document_id,3,:offer_acceptance_id,:offer_id,:profile_id,:policy_id,
                     :recipient_id,:slot_hash,:attendee_hash,:intent_hash,:content_hash,:created_at)"""),
                    {
                        **forged,
                        "id": UUID(int=6102),
                        "experiment_id": graph["experiment_id"],
                        "conversation_id": graph["conversation_id"],
                        "context_id": graph["context_id"],
                        "scheduling_handoff_id": scheduling.id,
                        "source_document_id": graph["document_id"],
                        "slot_hash": _hash("slot"),
                        "attendee_hash": _hash("attendee"),
                        "intent_hash": _hash("intent"),
                        "content_hash": _hash("forged booking"),
                        "created_at": NOW,
                    },
                )
            await connection.rollback()
    # A legacy intent inserted under an older guard cannot launder its commercial
    # lineage through an otherwise valid booking observation and final handoff.
    async with governance_engine.connect() as connection:
        await connection.execute(
            text(
                "ALTER TABLE record_conversation_booking_intents DISABLE TRIGGER record_conversation_booking_intent_lineage"
            )
        )
        forged = {
            **dict(lineage),
            "offer_acceptance_id": UUID(int=6199),
            "id": UUID(int=6200),
            "experiment_id": graph["experiment_id"],
            "conversation_id": graph["conversation_id"],
            "context_id": graph["context_id"],
            "scheduling_handoff_id": scheduling.id,
            "source_document_id": graph["document_id"],
            "slot_hash": _hash("slot"),
            "attendee_hash": _hash("attendee"),
            "intent_hash": _hash("legacy intent"),
            "content_hash": _hash("legacy content"),
            "created_at": NOW,
        }
        await connection.execute(
            text("""INSERT INTO record_conversation_booking_intents
            (id,experiment_id,conversation_id,context_id,scheduling_handoff_id,source_document_id,
             source_span_ordinal,offer_acceptance_id,offer_id,profile_id,policy_id,recipient_id,
             slot_hash,attendee_hash,intent_hash,content_hash,created_at)
            VALUES (:id,:experiment_id,:conversation_id,:context_id,:scheduling_handoff_id,
             :source_document_id,3,:offer_acceptance_id,:offer_id,:profile_id,:policy_id,
             :recipient_id,:slot_hash,:attendee_hash,:intent_hash,:content_hash,:created_at)"""),
            forged,
        )
        await connection.execute(
            text(
                "ALTER TABLE record_conversation_booking_intents ENABLE TRIGGER record_conversation_booking_intent_lineage"
            )
        )
        await connection.execute(
            text("""INSERT INTO record_conversation_booking_confirmations
            (id,intent_id,source_document_id,source_span_ordinal,confirmation_hash,slot_hash,
             attendee_hash,content_hash,created_at)
            VALUES (:id,:intent_id,:source_document_id,3,:confirmation_hash,:slot_hash,
             :attendee_hash,:content_hash,:created_at)"""),
            {
                "id": UUID(int=6201),
                "intent_id": forged["id"],
                "source_document_id": graph["document_id"],
                "confirmation_hash": _hash("legacy confirmation"),
                "slot_hash": _hash("slot"),
                "attendee_hash": _hash("attendee"),
                "content_hash": _hash("legacy confirmation content"),
                "created_at": NOW,
            },
        )
        await connection.execute(
            text("""INSERT INTO record_conversation_booking_observations
            (id,intent_id,confirmation_id,provider_call_id,provider_evidence_id,provider_event_hash,
             slot_hash,attendee_hash,content_hash,observed_at)
            VALUES (:id,:intent_id,:confirmation_id,:provider_call_id,:provider_evidence_id,
             :provider_event_hash,:slot_hash,:attendee_hash,:content_hash,:observed_at)"""),
            {
                "id": UUID(int=6202),
                "intent_id": forged["id"],
                "confirmation_id": UUID(int=6201),
                "provider_call_id": graph["provider_call_id"],
                "provider_evidence_id": graph["provider_evidence_id"],
                "provider_event_hash": _hash("legacy provider event"),
                "slot_hash": _hash("slot"),
                "attendee_hash": _hash("attendee"),
                "content_hash": _hash("legacy observation"),
                "observed_at": NOW,
            },
        )
        with pytest.raises(SQLAlchemyError, match="booking handoff mismatch"):
            await connection.execute(
                text("""INSERT INTO record_conversation_handoffs
                (id,experiment_id,conversation_id,context_id,kind,source_document_id,
                 source_span_ordinal,source_intent_hash,offer_acceptance_id,offer_id,profile_id,
                 policy_id,recipient_id,booking_observation_id,content,content_hash,created_at)
                VALUES (:id,:experiment_id,:conversation_id,:context_id,'MEETING_BOOKING',
                 :source_document_id,3,:source_intent_hash,:offer_acceptance_id,:offer_id,:profile_id,
                 :policy_id,:recipient_id,:booking_observation_id,'{}'::jsonb,:content_hash,:created_at)"""),
                {
                    **dict(lineage),
                    "id": UUID(int=6203),
                    "experiment_id": graph["experiment_id"],
                    "conversation_id": graph["conversation_id"],
                    "context_id": graph["context_id"],
                    "source_document_id": graph["document_id"],
                    "source_intent_hash": _hash("legacy handoff"),
                    "booking_observation_id": UUID(int=6202),
                    "content_hash": _hash("legacy handoff content"),
                    "created_at": NOW,
                },
            )
        await connection.rollback()
    await repo.record_booking_intent(intent, command_key=UUID(int=6010))
    confirmation = BookingConfirmationRequest(
        id=UUID(int=6011),
        intent_id=intent.id,
        source_span=graph["date_span"],
        confirmation_hash=_hash("confirmation"),
        slot_hash=_hash("slot"),
        attendee_hash=_hash("attendee"),
        content_hash=_hash("booking confirmation"),
    )
    await repo.record_booking_confirmation(confirmation, command_key=UUID(int=6012))
    bad_observation = BookingObservationRequest(
        id=UUID(int=6013),
        intent_id=intent.id,
        confirmation_id=confirmation.id,
        provider_call_id=graph["provider_call_id"],
        provider_evidence_id=graph["provider_evidence_id"],
        provider_event_hash=_hash("provider event"),
        slot_hash=_hash("wrong slot"),
        attendee_hash=_hash("attendee"),
        content_hash=_hash("bad observation"),
        observed_at=NOW,
    )
    with pytest.raises(ProductRecordsDenied):
        await repo.record_booking_observation(
            bad_observation, command_key=UUID(int=6014)
        )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT lock_kind FROM record_conversation_lock_events WHERE conversation_id=:id ORDER BY event_ordinal DESC LIMIT 1"
                ),
                {"id": graph["conversation_id"]},
            )
            == "SCHEDULING_ONLY"
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_conversation_handoffs WHERE conversation_id=:id"
                ),
                {"id": graph["conversation_id"]},
            )
            == 1
        )
    observation = bad_observation.model_copy(
        update={
            "id": UUID(int=6015),
            "slot_hash": _hash("slot"),
            "content_hash": _hash("observation"),
        }
    )
    observation_receipt = await repo.record_booking_observation(
        observation, command_key=UUID(int=6016)
    )
    assert (
        await repo.record_booking_observation(observation, command_key=UUID(int=6016))
        == observation_receipt
    )
    booking = HandoffRequest(
        id=UUID(int=6017),
        context_id=graph["context_id"],
        source_span=graph["date_span"],
        kind="MEETING_BOOKING",
        content={"request": "booked"},
        content_hash=_hash("booking handoff"),
        action_id=UUID(int=6018),
        booking_observation_id=observation.id,
        recorded_by=OWNER,
    )
    await repo.record_handoff(booking, command_key=UUID(int=6019))
    async with governance_engine.connect() as connection:
        lock_id = await connection.scalar(
            text(
                "SELECT id FROM record_conversation_lock_events WHERE conversation_id=:id ORDER BY event_ordinal DESC LIMIT 1"
            ),
            {"id": graph["conversation_id"]},
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_conversation_handoffs WHERE conversation_id=:id"
                ),
                {"id": graph["conversation_id"]},
            )
            == 2
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_conversation_operator_actions WHERE conversation_id=:id"
                ),
                {"id": graph["conversation_id"]},
            )
            == 2
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_conversation_lock_events WHERE conversation_id=:id AND event_kind='RELEASE'"
                ),
                {"id": graph["conversation_id"]},
            )
            == 1
        )
    for action in (
        "DRAFT",
        "SEND",
        "NUDGE",
        "COMMERCIAL_DISCLOSURE",
        "CALENDAR_ACTION",
    ):
        with pytest.raises(ProductRecordsDenied, match="MANUAL_TAKEOVER_ACTIVE"):
            await repo.assert_automation_allowed(graph["context_id"], action)
    message = OperatorMessageRequest(
        id=UUID(int=6020),
        context_id=graph["context_id"],
        operator_id=graph["operator_id"],
        organization_id=graph["organization_id"],
        recipient_id=graph["recipient_id"],
        recipient_source_id=graph["recipient_source_id"],
        thread_identity_hash=graph["thread_identity_hash"],
        active_lock_event_id=lock_id,
        body_hash=_hash("operator message"),
        content_hash=_hash("operator audit"),
    )
    operator_receipt = await repo.record_operator_message(
        message, command_key=UUID(int=6021)
    )
    assert (
        await repo.record_operator_message(message, command_key=UUID(int=6021))
        == operator_receipt
    )
    with pytest.raises(ProductRecordsDenied, match="MANUAL_TAKEOVER_REQUIRED"):
        await repo.record_operator_message(
            message.model_copy(
                update={"id": UUID(int=6096), "active_lock_event_id": UUID(int=1)}
            ),
            command_key=UUID(int=6096),
        )
    outcome = ManualOutcomeRequest(
        id=UUID(int=6022),
        context_id=graph["context_id"],
        operator_id=graph["operator_id"],
        active_lock_event_id=lock_id,
        outcome="MEETING_BOOKED",
        content_hash=_hash("manual outcome"),
    )
    outcome_receipt = await repo.record_manual_outcome(
        outcome, command_key=UUID(int=6023)
    )
    assert (
        await repo.record_manual_outcome(outcome, command_key=UUID(int=6023))
        == outcome_receipt
    )
    async with governance_engine.connect() as connection:
        with pytest.raises(SQLAlchemyError):
            await connection.execute(
                text(
                    "UPDATE record_conversation_operator_messages SET body_hash=:hash WHERE id=:id"
                ),
                {"id": message.id, "hash": _hash("mutated")},
            )
        await connection.rollback()
    async with governance_engine.connect() as connection:
        with pytest.raises(SQLAlchemyError):
            await connection.execute(
                text(
                    "UPDATE record_conversation_manual_outcomes SET outcome='PAID' WHERE id=:id"
                ),
                {"id": outcome.id},
            )
        await connection.rollback()
