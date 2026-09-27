"""Regression cases for source licensing and runtime-only result containment."""

import json
import pickle
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from alon_ai.integrations.schemas.provider import (
    Capability,
    ContentField,
    Provider,
    Purpose,
)
from alon_ai.policies.provider_rights import (
    GrantEvent,
    GrantEventKind,
    IntendedUse,
    ProviderUsageGrant,
    RightsMode,
    RuntimeContent,
    evaluate_rights,
)

NOW = datetime(2026, 9, 12, tzinfo=UTC)


def use(**changes):
    values: dict[str, Any] = {
        "provider": Provider.BRAVE,
        "account_handle": "synthetic-account",
        "capability": Capability.BRAVE_LOCAL_DISCOVERY,
        "plan_identifier": "synthetic-plan",
        "order_form_ref": "synthetic-order",
        "terms_version": "synthetic-terms-v1",
        "purpose": Purpose.LEAD_DISCOVERY,
        "required_fields": frozenset({ContentField.EMAIL}),
    }
    return IntendedUse(**(values | changes))


def grant(**changes):
    values: dict[str, Any] = {
        "grant_id": uuid4(),
        "version": 1,
        "provider": Provider.BRAVE,
        "account_handle": "synthetic-account",
        "capability": Capability.BRAVE_LOCAL_DISCOVERY,
        "plan_identifier": "synthetic-plan",
        "order_form_ref": "synthetic-order",
        "terms_version": "synthetic-terms-v1",
        "purpose": Purpose.LEAD_DISCOVERY,
        "outbound_use_permitted": True,
        "storage_fields": frozenset({ContentField.EMAIL}),
        "retention_rule_id": uuid4(),
        "retention_seconds": 3600,
        "approved_by": uuid4(),
        "approved_at": NOW - timedelta(days=1),
        "effective_at": NOW - timedelta(hours=1),
        "expires_at": NOW + timedelta(days=1),
        "supporting_evidence_ref": uuid4(),
    }
    return ProviderUsageGrant(**(values | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"account_handle": "foreign"},
        {"plan_identifier": "free"},
        {"order_form_ref": "foreign"},
        {"terms_version": "old"},
        {"capability": Capability.BRAVE_WEB_COVERAGE},
        {"purpose": Purpose.OFFICIAL_SOURCE_IDENTIFICATION},
        {"outbound_use_permitted": False},
        {"expires_at": NOW},
        {"effective_at": NOW + timedelta(seconds=1)},
        {
            "storage_fields": frozenset(),
            "retention_seconds": None,
            "retention_rule_id": None,
        },
    ],
)
def test_discovery_never_downgrades_or_accepts_mismatched_rights(changes):
    assert (
        evaluate_rights(grant(**changes), (), use(), now=NOW).mode is RightsMode.DENIED
    )


def test_missing_grant_denies_and_full_grant_has_exact_retention():
    assert evaluate_rights(None, (), use(), now=NOW).mode is RightsMode.DENIED
    decision = evaluate_rights(grant(), (), use(), now=NOW)
    assert decision.mode is RightsMode.RETAIN_SCOPED_CONTENT
    assert decision.allowed_fields == frozenset({ContentField.EMAIL})
    assert decision.retain_until == NOW + timedelta(hours=1)


@pytest.mark.parametrize(
    "kind",
    [GrantEventKind.REVOKED, GrantEventKind.REVIEW_REQUIRED, GrantEventKind.EXPIRED],
)
def test_effective_events_deny_even_after_activation(kind):
    g = grant()
    event = GrantEvent(
        event_id=uuid4(),
        grant_id=g.grant_id,
        grant_version=1,
        kind=kind,
        effective_at=NOW,
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    assert evaluate_rights(g, (event,), use(), now=NOW).mode is RightsMode.DENIED


def test_transient_exception_requires_exact_licensed_purpose_and_no_fields():
    g = grant(
        purpose=Purpose.OFFICIAL_SOURCE_IDENTIFICATION,
        storage_fields=frozenset(),
        retention_seconds=None,
        retention_rule_id=None,
    )
    intended = use(
        purpose=Purpose.OFFICIAL_SOURCE_IDENTIFICATION, required_fields=frozenset()
    )
    assert (
        evaluate_rights(g, (), intended, now=NOW).mode
        is RightsMode.TRANSIENT_OFFICIAL_SOURCE_IDENTIFICATION
    )
    assert evaluate_rights(g, (), use(), now=NOW).mode is RightsMode.DENIED
    assert (
        evaluate_rights(
            g, (), use(purpose=Purpose.OFFICIAL_SOURCE_IDENTIFICATION), now=NOW
        ).mode
        is RightsMode.DENIED
    )


def test_runtime_content_refuses_serialization_and_expired_retention():
    g = grant()
    content = RuntimeContent(
        {
            ContentField.EMAIL: ("UNIQUE-RESULT@example.test",),
            ContentField.TEXT: ("secret snippet",),
        },
        grant=g,
        intended_use=use(),
        observed_at=NOW,
    )
    assert "UNIQUE-RESULT" not in repr(content)
    with pytest.raises(TypeError):
        pickle.dumps(content)
    with pytest.raises(TypeError):
        json.dumps(content)
    retained = content.retain(current_grant=g, events=(), now=NOW)
    assert retained.fields == {ContentField.EMAIL: ("UNIQUE-RESULT@example.test",)}
    with pytest.raises(PermissionError):
        content.retain(current_grant=g, events=(), now=NOW + timedelta(hours=1))
    with pytest.raises(PermissionError):
        content.retain(current_grant=grant(), events=(), now=NOW)


def test_revocation_after_completion_blocks_retention_and_transient_cannot_retain():
    g = grant()
    content = RuntimeContent(
        {ContentField.EMAIL: ("x@example.test",)},
        grant=g,
        intended_use=use(),
        observed_at=NOW,
    )
    event = GrantEvent(
        event_id=uuid4(),
        grant_id=g.grant_id,
        grant_version=1,
        kind=GrantEventKind.REVOKED,
        effective_at=NOW + timedelta(seconds=1),
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    with pytest.raises(PermissionError):
        content.retain(current_grant=g, events=(event,), now=NOW + timedelta(seconds=2))
    transient_grant = grant(
        purpose=Purpose.OFFICIAL_SOURCE_IDENTIFICATION,
        storage_fields=frozenset(),
        retention_seconds=None,
        retention_rule_id=None,
    )
    intended = use(
        purpose=Purpose.OFFICIAL_SOURCE_IDENTIFICATION, required_fields=frozenset()
    )
    transient = RuntimeContent(
        {ContentField.URL: ("https://example.test",)},
        grant=transient_grant,
        intended_use=intended,
        observed_at=NOW,
    )
    seen = []
    transient.consume_official_sources(
        lambda urls: seen.extend(urls),
        current_grant=transient_grant,
        events=(),
        now=NOW,
    )
    assert seen == ["https://example.test"]
    with pytest.raises(PermissionError):
        transient.retain(current_grant=transient_grant, events=(), now=NOW)


def test_grant_rejects_ambiguous_or_naive_approval():
    with pytest.raises(ValidationError):
        grant(approved_at=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError):
        grant(storage_fields=frozenset({ContentField.EMAIL}), retention_seconds=None)
