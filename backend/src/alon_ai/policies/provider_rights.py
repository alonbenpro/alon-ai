"""Pure grant evaluation and explicit, scoped content access.

Inputs are trusted current repository grants/events and intended use. A credential,
caller-created grant, or old decision is never an authorization source. Python
callbacks are trusted code: this is a containment boundary, not a hostile-code sandbox.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from alon_ai.integrations.schemas.provider import (
    CAPABILITIES,
    Capability,
    ContentField,
    Nature,
    Provider,
    Purpose,
    StrictDTO,
)


class ProviderUsageGrant(StrictDTO):
    grant_id: UUID
    version: int = Field(ge=1)
    provider: Provider
    account_handle: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    capability: Capability
    plan_identifier: str = Field(
        min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$"
    )
    order_form_ref: str = Field(
        min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$"
    )
    terms_version: str = Field(
        min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$"
    )
    purpose: Purpose
    outbound_use_permitted: bool
    storage_fields: frozenset[ContentField]
    retention_rule_id: UUID | None
    retention_seconds: int | None = Field(gt=0, le=315360000)
    approved_by: UUID
    approved_at: AwareDatetime
    effective_at: AwareDatetime
    expires_at: AwareDatetime
    supporting_evidence_ref: UUID
    supersedes_id: UUID | None = None

    @model_validator(mode="after")
    def unambiguous_grant(self) -> ProviderUsageGrant:
        if CAPABILITIES[self.capability].provider is not self.provider:
            raise ValueError("grant provider capability mismatch")
        if self.approved_at > self.effective_at or self.effective_at >= self.expires_at:
            raise ValueError("invalid grant timeline")
        if bool(self.storage_fields) != (
            self.retention_seconds is not None and self.retention_rule_id is not None
        ):
            raise ValueError("explicit retention policy required")
        if not self.storage_fields and (
            self.retention_seconds is not None or self.retention_rule_id is not None
        ):
            raise ValueError("transient grant cannot contain retention policy")
        return self


class GrantEventKind(StrEnum):
    ACTIVATED = "ACTIVATED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class GrantEvent(StrictDTO):
    event_id: UUID
    grant_id: UUID
    grant_version: int = Field(ge=1)
    kind: GrantEventKind
    effective_at: AwareDatetime
    actor_id: UUID
    evidence_ref: UUID


class IntendedUse(StrictDTO):
    """Resolved from trusted account/config/request policy by the executor."""

    provider: Provider
    account_handle: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    capability: Capability
    plan_identifier: str = Field(min_length=1, max_length=100)
    order_form_ref: str = Field(min_length=1, max_length=100)
    terms_version: str = Field(min_length=1, max_length=100)
    purpose: Purpose
    required_fields: frozenset[ContentField]


class RightsMode(StrEnum):
    DENIED = "DENIED"
    TRANSIENT_OFFICIAL_SOURCE_IDENTIFICATION = (
        "TRANSIENT_OFFICIAL_SOURCE_IDENTIFICATION"
    )
    RETAIN_SCOPED_CONTENT = "RETAIN_SCOPED_CONTENT"


class RightsReason(StrEnum):
    ALLOWED = "ALLOWED"
    MISSING_GRANT = "MISSING_GRANT"
    MISMATCH = "MISMATCH"
    NOT_CURRENT = "NOT_CURRENT"
    EVENT_DENIED = "EVENT_DENIED"
    PURPOSE_DENIED = "PURPOSE_DENIED"
    OUTREACH_DENIED = "OUTREACH_DENIED"
    STORAGE_DENIED = "STORAGE_DENIED"
    WRITE_AUTHORITY_REQUIRED = "WRITE_AUTHORITY_REQUIRED"


class RightsDecision(StrictDTO):
    mode: RightsMode
    reason: RightsReason
    grant_id: UUID | None = None
    grant_version: int | None = None
    allowed_fields: frozenset[ContentField] = frozenset()
    retain_until: AwareDatetime | None = None
    retention_rule_id: UUID | None = None


_DISCOVERY = frozenset(
    {Capability.BRAVE_LOCAL_DISCOVERY, Capability.BRAVE_COMPANY_DISCOVERY}
)
_HUNTER_DISCOVERY = frozenset(
    {
        Capability.HUNTER_DOMAIN_SEARCH,
        Capability.HUNTER_EMAIL_FINDER,
        Capability.HUNTER_COMPANY_ENRICHMENT,
        Capability.HUNTER_PERSON_ENRICHMENT,
    }
)
_PURPOSES = {
    Capability.OPENAI_GENERATE: {Purpose.GENERATION},
    Capability.BRAVE_WEB_COVERAGE: {
        Purpose.RESEARCH,
        Purpose.OFFICIAL_SOURCE_IDENTIFICATION,
    },
    Capability.GMAIL_READ: {Purpose.MAILBOX_READ},
    Capability.GOOGLE_CALENDAR_READ: {Purpose.CALENDAR_READ},
    Capability.HUNTER_EMAIL_VERIFICATION: {Purpose.EMAIL_VERIFICATION},
}


def evaluate_rights(
    grant: ProviderUsageGrant | None,
    events: tuple[GrantEvent, ...],
    intended_use: IntendedUse,
    *,
    now: datetime,
) -> RightsDecision:
    """Pure fail-closed decision; expiry is exclusive; blocking events are monotone."""

    def deny(reason: RightsReason) -> RightsDecision:
        return RightsDecision(
            mode=RightsMode.DENIED,
            reason=reason,
            grant_id=grant.grant_id if grant else None,
            grant_version=grant.version if grant else None,
        )

    if now.tzinfo is None or now.utcoffset() is None:
        return deny(RightsReason.NOT_CURRENT)
    spec = CAPABILITIES[intended_use.capability]
    if spec.nature is Nature.WRITE:
        return deny(RightsReason.WRITE_AUTHORITY_REQUIRED)
    if grant is None:
        return deny(RightsReason.MISSING_GRANT)
    if spec.provider is not intended_use.provider:
        return deny(RightsReason.MISMATCH)
    for field in (
        "provider",
        "account_handle",
        "capability",
        "plan_identifier",
        "order_form_ref",
        "terms_version",
        "purpose",
    ):
        if getattr(grant, field) != getattr(intended_use, field):
            return deny(RightsReason.MISMATCH)
    if not grant.approved_at <= grant.effective_at <= now < grant.expires_at:
        return deny(RightsReason.NOT_CURRENT)
    if any(
        event.grant_id == grant.grant_id
        and event.grant_version == grant.version
        and event.effective_at <= now
        and event.kind is not GrantEventKind.ACTIVATED
        for event in events
    ):
        return deny(RightsReason.EVENT_DENIED)
    capability = intended_use.capability
    allowed_purposes = _PURPOSES.get(capability, {Purpose.RESEARCH})
    if capability in _DISCOVERY:
        allowed_purposes = {
            Purpose.LEAD_DISCOVERY,
            Purpose.OFFICIAL_SOURCE_IDENTIFICATION,
        }
    elif capability in _HUNTER_DISCOVERY:
        allowed_purposes = {Purpose.CONTACT_DISCOVERY}
    if intended_use.purpose not in allowed_purposes:
        return deny(RightsReason.PURPOSE_DENIED)
    if (
        intended_use.purpose in {Purpose.LEAD_DISCOVERY, Purpose.CONTACT_DISCOVERY}
        and not grant.outbound_use_permitted
    ):
        return deny(RightsReason.OUTREACH_DENIED)
    if (
        intended_use.purpose is Purpose.OFFICIAL_SOURCE_IDENTIFICATION
        and not intended_use.required_fields
    ):
        return RightsDecision(
            mode=RightsMode.TRANSIENT_OFFICIAL_SOURCE_IDENTIFICATION,
            reason=RightsReason.ALLOWED,
            grant_id=grant.grant_id,
            grant_version=grant.version,
        )
    if (
        not intended_use.required_fields
        or not intended_use.required_fields <= grant.storage_fields
        or grant.retention_seconds is None
    ):
        return deny(RightsReason.STORAGE_DENIED)
    return RightsDecision(
        mode=RightsMode.RETAIN_SCOPED_CONTENT,
        reason=RightsReason.ALLOWED,
        grant_id=grant.grant_id,
        grant_version=grant.version,
        allowed_fields=intended_use.required_fields,
        retention_rule_id=grant.retention_rule_id,
        retain_until=min(
            grant.expires_at, now + timedelta(seconds=grant.retention_seconds)
        ),
    )


class ScopedRetainedContent:
    """Explicitly licensed content for an authorized content repository, never audit."""

    __slots__ = (
        "expires_at",
        "fields",
        "grant_id",
        "grant_version",
        "retention_rule_id",
    )

    def __init__(
        self,
        fields: Mapping[ContentField, tuple[str, ...]],
        decision: RightsDecision,
        expires_at: datetime,
    ):
        self.fields = MappingProxyType(dict(fields))
        self.grant_id = decision.grant_id
        self.grant_version = decision.grant_version
        self.expires_at = expires_at
        self.retention_rule_id = decision.retention_rule_id

    def __repr__(self) -> str:
        return "ScopedRetainedContent(<licensed content>)"

    def __reduce_ex__(self, protocol: object):
        raise TypeError("use the authorized content repository explicitly")


class RuntimeContent:
    """No dump/hash/cache representation. Re-evaluate current source rights on use."""

    __slots__ = ("__fields", "__grant_id", "__grant_version", "__observed_at", "__use")

    def __init__(
        self,
        fields: Mapping[ContentField, tuple[str, ...]],
        *,
        grant: ProviderUsageGrant,
        intended_use: IntendedUse,
        observed_at: datetime,
    ):
        if (
            evaluate_rights(grant, (), intended_use, now=observed_at).mode
            is RightsMode.DENIED
        ):
            raise PermissionError("source rights denied")
        if any(
            not isinstance(k, ContentField)
            or not isinstance(v, tuple)
            or any(not isinstance(x, str) for x in v)
            for k, v in fields.items()
        ):
            raise TypeError("typed content fields required")
        self.__fields = MappingProxyType(dict(fields))
        self.__grant_id = grant.grant_id
        self.__grant_version = grant.version
        self.__use = intended_use
        self.__observed_at = observed_at

    def __repr__(self) -> str:
        return "RuntimeContent(<runtime-only>)"

    def __reduce_ex__(self, protocol: object):
        raise TypeError("runtime provider content cannot be serialized")

    def _decision(
        self,
        current_grant: ProviderUsageGrant | None,
        events: tuple[GrantEvent, ...],
        now: datetime,
    ) -> RightsDecision:
        if (
            current_grant is None
            or current_grant.grant_id != self.__grant_id
            or current_grant.version != self.__grant_version
        ):
            raise PermissionError("source grant changed")
        decision = evaluate_rights(current_grant, events, self.__use, now=now)
        if decision.mode is RightsMode.DENIED or now < self.__observed_at:
            raise PermissionError("source rights denied")
        return decision

    def consume_official_sources(
        self,
        consumer: Callable[[tuple[str, ...]], None],
        *,
        current_grant: ProviderUsageGrant | None,
        events: tuple[GrantEvent, ...],
        now: datetime,
    ) -> None:
        decision = self._decision(current_grant, events, now)
        if decision.mode is not RightsMode.TRANSIENT_OFFICIAL_SOURCE_IDENTIFICATION:
            raise PermissionError("explicit transient purpose required")
        consumer(self.__fields.get(ContentField.URL, ()))

    def retain(
        self,
        *,
        current_grant: ProviderUsageGrant | None,
        events: tuple[GrantEvent, ...],
        now: datetime,
    ) -> ScopedRetainedContent:
        decision = self._decision(current_grant, events, now)
        if (
            decision.mode is not RightsMode.RETAIN_SCOPED_CONTENT
            or current_grant is None
            or current_grant.retention_seconds is None
        ):
            raise PermissionError("content retention denied")
        expires = min(
            current_grant.expires_at,
            self.__observed_at + timedelta(seconds=current_grant.retention_seconds),
        )
        if now >= expires:
            raise PermissionError("content retention expired")
        return ScopedRetainedContent(
            {k: v for k, v in self.__fields.items() if k in decision.allowed_fields},
            decision,
            expires,
        )
