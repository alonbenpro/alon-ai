"""Immutable conversation and response-decision persistence."""

from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from alon_ai.records.conversation_models import ReplyEvidenceSpan
from alon_ai.records.models import ArtifactKind

pytestmark = pytest.mark.integration


def test_conversation_artifact_contract_is_available():
    """Removing a conversation artifact kind breaks downstream immutable lineage."""
    assert ArtifactKind.CONVERSATION_TURN_CONTEXT.value == "CONVERSATION_TURN_CONTEXT"


async def test_conversation_turn_context_table_is_migrated(governance_engine):
    """Dropping turn-context persistence makes immutable reply reconstruction impossible."""
    async with governance_engine.connect() as connection:
        assert await connection.scalar(
            text("SELECT to_regclass('record_conversation_turn_contexts')")
        ) == "record_conversation_turn_contexts"


def test_reply_evidence_span_rejects_empty_offsets():
    """Allowing an empty span would detach an interpretation from reply evidence."""
    with pytest.raises(ValidationError):
        ReplyEvidenceSpan(message_id=UUID(int=1), start_offset=4, end_offset=4)
