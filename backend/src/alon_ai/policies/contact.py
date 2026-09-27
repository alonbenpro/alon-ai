from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from alon_ai.integrations.schemas.provider import (
    ContentField,
    EmailPresence,
    ProviderResultMetadata,
    StrictDTO,
    VerificationStatus,
)
from alon_ai.policies.provider_rights import (
    GrantEvent,
    ProviderUsageGrant,
    RuntimeContent,
)


class ContactDecision(StrEnum):
    AVOIDED_HUNTER = "AVOIDED_HUNTER"
    FALLBACK_ALLOWED = "FALLBACK_ALLOWED"
    PAUSED = "PAUSED"


class ContactDecisionReceipt(StrictDTO):
    candidate_id: UUID
    presence: EmailPresence
    decision: ContactDecision
    counterfactual_savings: Literal["UNAVAILABLE"] = "UNAVAILABLE"


class ContactPolicyDenied(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__("contact policy denied: " + reason)


def _metadata(value: object) -> ProviderResultMetadata:
    return ProviderResultMetadata.model_validate_json(json.dumps(value, default=str))


def _fields(
    content: RuntimeContent,
    grant: ProviderUsageGrant,
    events: tuple[GrantEvent, ...],
    now: datetime,
):
    return content.retain(current_grant=grant, events=events, now=now).fields


def observe_email_presence(
    content: RuntimeContent,
    grant: ProviderUsageGrant,
    events: tuple[GrantEvent, ...],
    *,
    now: datetime,
) -> EmailPresence:
    """Inspect only currently licensed EMAIL content; never return the address."""
    values = _fields(content, grant, events, now).get(ContentField.EMAIL, ())
    return EmailPresence.PRESENT if values else EmailPresence.ABSENT


def observe_verification_status(
    content: RuntimeContent,
    grant: ProviderUsageGrant,
    events: tuple[GrantEvent, ...],
    *,
    now: datetime,
) -> VerificationStatus:
    """Parse an exact licensed verifier status; malformed content stays UNKNOWN."""
    values = _fields(content, grant, events, now).get(ContentField.TEXT, ())
    if len(values) != 1:
        return VerificationStatus.UNKNOWN
    try:
        return VerificationStatus(values[0])
    except ValueError:
        return VerificationStatus.UNKNOWN
