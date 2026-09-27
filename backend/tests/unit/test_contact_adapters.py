from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import SecretStr

from alon_ai.integrations.fakes import (
    FakeBraveProvider,
    FakeContactDiscoveryProvider,
    FakeEmailVerificationProvider,
)
from alon_ai.integrations.schemas.provider import (
    BraveSearchRequest,
    Capability,
    ContactDiscoveryRequest,
    ContentField,
    EmailPresence,
    EmailSourceObservation,
    EmailVerificationRequest,
    Provider,
    Purpose,
    VerificationStatus,
)
from alon_ai.policies.provider_rights import (
    GrantEvent,
    GrantEventKind,
    IntendedUse,
    ProviderUsageGrant,
    RuntimeContent,
)
from alon_ai.provider_usage.schemas.accounting import CapabilityConfig, PriceBound

NOW = datetime(2026, 9, 12, 12, tzinfo=UTC)


def config(capability: Capability) -> CapabilityConfig:
    purpose = (
        Purpose.LEAD_DISCOVERY
        if capability
        in {
            Capability.BRAVE_LOCAL_DISCOVERY,
            Capability.BRAVE_COMPANY_DISCOVERY,
        }
        else Purpose.EMAIL_VERIFICATION
        if capability is Capability.HUNTER_EMAIL_VERIFICATION
        else Purpose.CONTACT_DISCOVERY
    )
    return CapabilityConfig(
        id=uuid4(),
        version=uuid4(),
        workflow_id=uuid4(),
        intended_use=IntendedUse(
            provider=(
                Provider.BRAVE
                if capability.name.startswith("BRAVE")
                else Provider.HUNTER
            ),
            account_handle="synthetic-contact",
            capability=capability,
            plan_identifier="synthetic-plan",
            order_form_ref="synthetic-order",
            terms_version="synthetic-v1",
            purpose=purpose,
            required_fields=frozenset(
                {
                    ContentField.EMAIL
                    if capability is not Capability.HUNTER_EMAIL_VERIFICATION
                    else ContentField.TEXT
                }
            ),
        ),
        prices=(PriceBound(price_id=uuid4(), max_quantity=Decimal(1)),),
        fx_id=uuid4(),
        requested_count=1,
        adapter_version=uuid4(),
    )


def observation(business_id, presence=EmailPresence.ABSENT):
    return EmailSourceObservation(
        business_id=business_id,
        provider_call_id=uuid4(),
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
        grant_id=uuid4(),
        grant_version=1,
        evidence_ref=uuid4(),
        observed_at=NOW,
        presence=presence,
    )


def licensed(capability: Capability, field: ContentField):
    configured = config(capability)
    use = configured.intended_use
    grant = ProviderUsageGrant(
        grant_id=uuid4(),
        version=1,
        **use.model_dump(exclude={"schema_version", "required_fields"}),
        outbound_use_permitted=True,
        storage_fields=frozenset({field}),
        retention_rule_id=uuid4(),
        retention_seconds=3600,
        approved_by=uuid4(),
        approved_at=NOW - timedelta(days=2),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        supporting_evidence_ref=uuid4(),
    )
    return use, grant


@pytest.mark.parametrize(
    ("capability", "provider_type", "request_type", "method"),
    [
        (
            Capability.BRAVE_LOCAL_DISCOVERY,
            FakeBraveProvider,
            BraveSearchRequest,
            "search",
        ),
        (
            Capability.HUNTER_DOMAIN_SEARCH,
            FakeContactDiscoveryProvider,
            ContactDiscoveryRequest,
            "domain_search",
        ),
        (
            Capability.HUNTER_EMAIL_FINDER,
            FakeContactDiscoveryProvider,
            ContactDiscoveryRequest,
            "email_finder",
        ),
        (
            Capability.HUNTER_COMPANY_ENRICHMENT,
            FakeContactDiscoveryProvider,
            ContactDiscoveryRequest,
            "company_enrichment",
        ),
        (
            Capability.HUNTER_PERSON_ENRICHMENT,
            FakeContactDiscoveryProvider,
            ContactDiscoveryRequest,
            "person_enrichment",
        ),
        (
            Capability.HUNTER_EMAIL_VERIFICATION,
            FakeEmailVerificationProvider,
            EmailVerificationRequest,
            "verify",
        ),
    ],
)
def test_contact_adapter_builds_only_the_pinned_typed_call(
    capability, provider_type, request_type, method
):
    from alon_ai.integrations.contact import ConfiguredContactAdapter

    business_id = uuid4()
    source = observation(business_id)
    if request_type is BraveSearchRequest:
        request = BraveSearchRequest(
            capability=capability, query=SecretStr("synthetic query"), limit=1
        )
    elif request_type is ContactDiscoveryRequest:
        request = ContactDiscoveryRequest(
            business_id=business_id,
            brave_observation=source,
            domain=SecretStr("example.test"),
        )
    else:
        request = EmailVerificationRequest(
            business_id=business_id,
            email_candidate_id=uuid4(),
            source_evidence_ref=uuid4(),
            business_match_ref=uuid4(),
            address=SecretStr("synthetic@example.test"),
        )
    provider = object.__new__(provider_type)
    adapter = ConfiguredContactAdapter(provider, request, capability=capability)
    assert adapter.capability is capability
    assert adapter.method == method


def test_contact_adapter_rejects_config_or_quantity_substitution():
    from alon_ai.integrations.contact import ConfiguredContactAdapter

    request = BraveSearchRequest(
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
        query=SecretStr("synthetic query"),
        limit=1,
    )
    adapter = ConfiguredContactAdapter(
        object.__new__(FakeBraveProvider),
        request,
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
    )
    wrong = config(Capability.BRAVE_COMPANY_DISCOVERY)
    with pytest.raises(ValueError, match="configured contact adapter mismatch"):
        adapter.validate_config(wrong)
    with pytest.raises(ValueError, match="configured contact adapter mismatch"):
        adapter.validate_config(
            config(Capability.BRAVE_LOCAL_DISCOVERY).model_copy(
                update={"requested_count": 2}
            )
        )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (("VALID",), VerificationStatus.VALID),
        (("INVALID",), VerificationStatus.INVALID),
        (("ACCEPT_ALL",), VerificationStatus.ACCEPT_ALL),
        (("UNKNOWN",), VerificationStatus.UNKNOWN),
        (("TEMPORARY_FAILURE",), VerificationStatus.TEMPORARY_FAILURE),
        (("not-a-status",), VerificationStatus.UNKNOWN),
        (("VALID", "INVALID"), VerificationStatus.UNKNOWN),
        ((), VerificationStatus.UNKNOWN),
    ],
)
def test_verification_status_requires_exact_licensed_content(raw, expected):
    from alon_ai.policies.contact import observe_verification_status

    use, grant = licensed(Capability.HUNTER_EMAIL_VERIFICATION, ContentField.TEXT)
    content = RuntimeContent(
        {ContentField.TEXT: raw}, grant=grant, intended_use=use, observed_at=NOW
    )
    assert observe_verification_status(content, grant, (), now=NOW) is expected


@pytest.mark.parametrize("candidate", ["malformed-candidate", "", "   "])
def test_any_observed_brave_candidate_counts_present_even_if_malformed(candidate):
    from alon_ai.policies.contact import observe_email_presence

    use, grant = licensed(Capability.BRAVE_LOCAL_DISCOVERY, ContentField.EMAIL)
    content = RuntimeContent(
        {ContentField.EMAIL: (candidate,)},
        grant=grant,
        intended_use=use,
        observed_at=NOW,
    )
    assert observe_email_presence(content, grant, (), now=NOW) is EmailPresence.PRESENT


def test_runtime_parser_rechecks_exact_grant_and_revocation():
    from alon_ai.policies.contact import observe_verification_status

    use, grant = licensed(Capability.HUNTER_EMAIL_VERIFICATION, ContentField.TEXT)
    content = RuntimeContent(
        {ContentField.TEXT: ("VALID",)},
        grant=grant,
        intended_use=use,
        observed_at=NOW,
    )
    wrong = grant.model_copy(update={"grant_id": uuid4()})
    with pytest.raises(PermissionError, match="source grant changed"):
        observe_verification_status(content, wrong, (), now=NOW)
    revoked = GrantEvent(
        event_id=uuid4(),
        grant_id=grant.grant_id,
        grant_version=grant.version,
        kind=GrantEventKind.REVOKED,
        effective_at=NOW,
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    with pytest.raises(PermissionError, match="source rights denied"):
        observe_verification_status(content, grant, (revoked,), now=NOW)
