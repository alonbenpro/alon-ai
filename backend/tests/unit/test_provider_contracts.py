"""Capabilities must not become generic API or side-effect authority."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic import ValidationError

from alon_ai.integrations.schemas.provider import (
    CAPABILITIES,
    AgentActor,
    CallAttribution,
    Capability,
    CaptureFormat,
    CostKnowledge,
    FirecrawlCaptureRequest,
    Nature,
    Provider,
    SafeRequestMetadata,
    SystemActor,
    UsageComponent,
    UsageObservation,
)


def test_registry_derives_generation_and_write_nature():
    assert {
        spec.provider
        for spec in CAPABILITIES.values()
        if spec.nature is Nature.GENERATION
    } == {Provider.OPENAI}
    assert CAPABILITIES[Capability.GMAIL_SEND].nature is Nature.WRITE
    assert CAPABILITIES[Capability.GOOGLE_CALENDAR_WRITE].nature is Nature.WRITE
    with pytest.raises(ValueError):
        Capability("FIRECRAWL_AGENT")
    with pytest.raises(TypeError):
        cast(Any, CAPABILITIES)[Capability.GMAIL_SEND] = CAPABILITIES[
            Capability.GMAIL_READ
        ]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "https://user:pass@example.com",
        "http://localhost",
        "http://10.0.0.1",
        "http://[::1]",
        "https://example.com?token=secret",
        "http://2130706433",
        "http://0x7f000001",
        "http://0x7f.0.0.1",
        "http://0177.0.0.1",
        "http://127.1",
        "https://internal.local",
    ],
)
def test_capture_rejects_unsafe_targets(url):
    with pytest.raises(ValidationError):
        FirecrawlCaptureRequest(url=url)


def test_capture_accepts_public_dns_labels_containing_only_hex_letters():
    request = FirecrawlCaptureRequest(url="https://feed.cafe/page")
    assert request.url == "https://feed.cafe/page"


@pytest.mark.parametrize(
    "extra",
    [
        {"prompt": "summarize"},
        {"formats": ("summary",)},
        {"parser": "llm"},
        {"method": "POST"},
        {"body": "x"},
        {"endpoint": "agent"},
    ],
)
def test_capture_has_no_generative_or_arbitrary_transport_escape(extra):
    with pytest.raises(ValidationError):
        FirecrawlCaptureRequest(url="https://example.test/page", **extra)
    request = FirecrawlCaptureRequest(
        url="https://example.test/page", formats=(CaptureFormat.MARKDOWN,)
    )
    assert request.capability is Capability.FIRECRAWL_PAGE_CAPTURE


def test_attribution_requires_explicit_actor_and_forbids_selected_budgets():
    values: dict[str, Any] = {
        "experiment_id": uuid4(),
        "workflow_run_id": uuid4(),
        "operation_run_id": uuid4(),
        "correlation_id": uuid4(),
        "logical_operation_id": uuid4(),
        "config_version": uuid4(),
        "deadline": datetime(2026, 9, 12, tzinfo=UTC),
    }
    attribution = CallAttribution(
        **values, actor=SystemActor(service="provider-executor")
    )
    assert attribution.actor.kind == "system"
    restored = CallAttribution.model_validate_json(attribution.model_dump_json())
    assert restored == attribution
    with pytest.raises(ValidationError):
        CallAttribution.model_validate(
            values
            | {"actor": AgentActor(agent_run_id=uuid4()), "budget_account_ids": ()}
        )
    with pytest.raises(ValidationError):
        CallAttribution.model_validate(values | {"actor": {"kind": "agent"}})
    with pytest.raises(ValidationError):
        SafeRequestMetadata.model_validate(
            {"config_ref": uuid4(), "response_hash": "derived-content"}
        )


def test_usage_rejects_float_money_and_unknown_cost_is_not_zero():
    args: dict[str, Any] = {
        "component": UsageComponent.REQUEST,
        "quantity": Decimal(1),
        "currency": "USD",
        "observation_key": uuid4(),
        "knowledge": CostKnowledge.FINAL,
    }
    with pytest.raises(ValidationError):
        UsageObservation.model_validate(args | {"cost": 0.1})
    with pytest.raises(ValidationError):
        UsageObservation(**args, cost=Decimal("NaN"))
    observation = UsageObservation.model_validate(
        args | {"knowledge": CostKnowledge.UNAVAILABLE, "cost": None}
    )
    assert observation.cost is None


def test_validation_errors_never_retain_raw_inputs_or_unknown_field_names():
    from pydantic import TypeAdapter

    sentinel = "UNIQUE-SOURCE-CONTENT-secret"
    constructors = [
        lambda: cast(Any, FirecrawlCaptureRequest)(
            url=f"https://user:{sentinel}@example.test", **{sentinel: sentinel}
        ),
        lambda: FirecrawlCaptureRequest.model_validate(
            {"url": f"https://user:{sentinel}@example.test"}
        ),
        lambda: FirecrawlCaptureRequest.model_validate_json(
            '{"url":"http://127.0.0.1/' + sentinel + '"}'
        ),
        lambda: TypeAdapter(FirecrawlCaptureRequest).validate_python(
            {"url": f"https://user:{sentinel}@example.test"}
        ),
    ]
    for construct in constructors:
        with pytest.raises(ValidationError) as caught:
            construct()
        assert sentinel not in str(caught.value)
        assert sentinel not in repr(caught.value.errors())
        assert sentinel not in caught.value.json()


def test_brave_malformed_candidate_is_present_not_absent():
    from alon_ai.integrations.schemas.provider import EmailPresence, inspect_brave_email

    args: dict[str, Any] = {
        "business_id": uuid4(),
        "provider_call_id": uuid4(),
        "capability": Capability.BRAVE_LOCAL_DISCOVERY,
        "grant_id": uuid4(),
        "grant_version": 1,
        "evidence_ref": uuid4(),
        "observed_at": datetime(2026, 9, 12, tzinfo=UTC),
    }
    assert (
        inspect_brave_email(candidate="broken email", **args).presence
        is EmailPresence.PRESENT
    )
    assert inspect_brave_email(candidate="", **args).presence is EmailPresence.PRESENT
    assert inspect_brave_email(candidate=None, **args).presence is EmailPresence.ABSENT


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("provider fixture attempted network")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def fake_session(capability, scenario=None):
    from datetime import timedelta

    from alon_ai.integrations.fakes import FakeSession, FixtureScenario
    from alon_ai.integrations.schemas.provider import ContentField, Purpose
    from alon_ai.policies.provider_rights import IntendedUse, ProviderUsageGrant

    now = datetime(2026, 9, 12, tzinfo=UTC)
    purpose = {
        Capability.OPENAI_GENERATE: Purpose.GENERATION,
        Capability.BRAVE_LOCAL_DISCOVERY: Purpose.LEAD_DISCOVERY,
        Capability.BRAVE_COMPANY_DISCOVERY: Purpose.LEAD_DISCOVERY,
        Capability.HUNTER_DOMAIN_SEARCH: Purpose.CONTACT_DISCOVERY,
        Capability.HUNTER_EMAIL_FINDER: Purpose.CONTACT_DISCOVERY,
        Capability.HUNTER_COMPANY_ENRICHMENT: Purpose.CONTACT_DISCOVERY,
        Capability.HUNTER_PERSON_ENRICHMENT: Purpose.CONTACT_DISCOVERY,
        Capability.HUNTER_EMAIL_VERIFICATION: Purpose.EMAIL_VERIFICATION,
        Capability.GMAIL_READ: Purpose.MAILBOX_READ,
        Capability.GOOGLE_CALENDAR_READ: Purpose.CALENDAR_READ,
    }.get(capability, Purpose.RESEARCH)
    shared: dict[str, Any] = {
        "provider": CAPABILITIES[capability].provider,
        "capability": capability,
        "account_handle": "synthetic-account",
        "plan_identifier": "synthetic-plan",
        "order_form_ref": "synthetic-order",
        "terms_version": "synthetic-v1",
        "purpose": purpose,
    }
    grant = ProviderUsageGrant(
        **shared,
        grant_id=uuid4(),
        version=1,
        outbound_use_permitted=True,
        storage_fields=frozenset({ContentField.TEXT}),
        retention_rule_id=uuid4(),
        retention_seconds=3600,
        approved_by=uuid4(),
        approved_at=now - timedelta(days=1),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
        supporting_evidence_ref=uuid4(),
    )
    return FakeSession(
        grants={capability: grant},
        intended_uses={
            capability: IntendedUse(
                **shared, required_fields=frozenset({ContentField.TEXT})
            )
        },
        clock=lambda: now,
        scenario=scenario or FixtureScenario.SUCCESS,
    )


@pytest.mark.parametrize(
    "capability,method",
    [
        (Capability.OPENAI_GENERATE, "generate"),
        (Capability.BRAVE_WEB_COVERAGE, "search"),
        (Capability.BRAVE_LOCAL_DISCOVERY, "search"),
        (Capability.BRAVE_COMPANY_DISCOVERY, "search"),
        (Capability.FIRECRAWL_MAP, "map"),
        (Capability.FIRECRAWL_PAGE_CAPTURE, "capture"),
        (Capability.FIRECRAWL_PDF_CAPTURE, "capture"),
        (Capability.FIRECRAWL_JS_RETRIEVAL, "capture"),
        (Capability.HUNTER_DOMAIN_SEARCH, "domain_search"),
        (Capability.HUNTER_EMAIL_FINDER, "email_finder"),
        (Capability.HUNTER_COMPANY_ENRICHMENT, "company_enrichment"),
        (Capability.HUNTER_PERSON_ENRICHMENT, "person_enrichment"),
        (Capability.HUNTER_EMAIL_VERIFICATION, "verify"),
        (Capability.GMAIL_READ, "read"),
        (Capability.GOOGLE_CALENDAR_READ, "read"),
    ],
)
async def test_every_fake_port_is_typed_synthetic_and_offline(capability, method):
    import pickle

    from pydantic import SecretStr

    from alon_ai.integrations.fakes import (
        FakeBraveProvider,
        FakeCalendarProvider,
        FakeContactDiscoveryProvider,
        FakeEmailVerificationProvider,
        FakeFirecrawlProvider,
        FakeGmailProvider,
        FakeOpenAIProvider,
    )
    from alon_ai.integrations.schemas import provider as c

    session = fake_session(capability)
    now = datetime(2026, 9, 12, tzinfo=UTC)
    business = uuid4()
    observation = c.EmailSourceObservation(
        business_id=business,
        provider_call_id=uuid4(),
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
        grant_id=uuid4(),
        grant_version=1,
        evidence_ref=uuid4(),
        observed_at=now,
        presence=c.EmailPresence.ABSENT,
    )
    adapters = {
        Provider.OPENAI: FakeOpenAIProvider,
        Provider.BRAVE: FakeBraveProvider,
        Provider.FIRECRAWL: FakeFirecrawlProvider,
        Provider.HUNTER: FakeContactDiscoveryProvider,
        Provider.GMAIL: FakeGmailProvider,
        Provider.GOOGLE_CALENDAR: FakeCalendarProvider,
    }
    adapter = adapters[CAPABILITIES[capability].provider](session)
    if capability is Capability.OPENAI_GENERATE:
        request = c.GenerationRequest(
            prompt=SecretStr("customer-owned synthetic prompt"), max_output_tokens=10
        )
    elif capability.name.startswith("BRAVE"):
        request = c.BraveSearchRequest(
            capability=capability, query=SecretStr("synthetic query")
        )
    elif capability is Capability.FIRECRAWL_MAP:
        request = c.FirecrawlMapRequest(url="https://example.test")
    elif capability.name.startswith("FIRECRAWL"):
        request = c.FirecrawlCaptureRequest(
            capability=capability, url="https://example.test"
        )
    elif capability is Capability.HUNTER_EMAIL_VERIFICATION:
        adapter = FakeEmailVerificationProvider(session)
        request = c.EmailVerificationRequest(
            business_id=business,
            email_candidate_id=uuid4(),
            source_evidence_ref=uuid4(),
            business_match_ref=uuid4(),
            address=SecretStr("synthetic@example.test"),
        )
    elif capability.name.startswith("HUNTER"):
        request = c.ContactDiscoveryRequest(
            business_id=business,
            brave_observation=observation,
            domain=SecretStr("example.test"),
        )
    elif capability is Capability.GMAIL_READ:
        request = c.MailboxReadRequest(mailbox_id=uuid4())
    else:
        from datetime import timedelta

        request = c.CalendarReadRequest(
            calendar_id=uuid4(), starts_at=now, ends_at=now + timedelta(hours=1)
        )
    result = await getattr(adapter, method)(request)
    assert result.metadata.status is c.ResultStatus.SUCCEEDED
    assert result.metadata.capability is capability
    assert result.metadata.usage[0].cost == Decimal(0)
    assert session.invocations[0].capability is capability
    assert session.provenance.source_kind == "SYNTHETIC"
    assert "synthetic@example.test" not in repr(result)
    assert "synthetic@example.test" not in result.metadata.model_dump_json()
    with pytest.raises(TypeError):
        pickle.dumps(result)


@pytest.mark.parametrize(
    "method",
    ["domain_search", "email_finder", "company_enrichment", "person_enrichment"],
)
@pytest.mark.parametrize("presence", ["PRESENT", "NOT_AVAILABLE"])
async def test_each_hunter_discovery_port_blocks_without_evidenced_absence(
    method, presence
):
    from pydantic import SecretStr

    from alon_ai.integrations.fakes import FakeContactDiscoveryProvider
    from alon_ai.integrations.schemas import provider as c

    session = fake_session(Capability.HUNTER_DOMAIN_SEARCH)
    business = uuid4()
    observation = c.EmailSourceObservation(
        business_id=business,
        provider_call_id=uuid4(),
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
        grant_id=uuid4(),
        grant_version=1,
        evidence_ref=uuid4(),
        observed_at=datetime(2026, 9, 12, tzinfo=UTC),
        presence=c.EmailPresence(presence),
    )
    request = c.ContactDiscoveryRequest(
        business_id=business,
        brave_observation=observation,
        domain=SecretStr("example.test"),
    )
    with pytest.raises(c.ProviderFailure) as caught:
        await getattr(FakeContactDiscoveryProvider(session), method)(request)
    assert caught.value.code is c.ProviderErrorCode.DENIED
    assert session.invocations == ()


@pytest.mark.parametrize(
    "scenario,status,error",
    [
        ("REFUSED", "REFUSED", "REFUSED"),
        ("ERROR", "FAILED", "UNAVAILABLE"),
        ("MALFORMED", "FAILED", "MALFORMED_RESPONSE"),
        ("TIMEOUT", "UNKNOWN", "TIMEOUT"),
    ],
)
async def test_fake_failure_results_classify_without_raw_upstream_text(
    scenario, status, error
):
    from pydantic import SecretStr

    from alon_ai.integrations.fakes import FakeOpenAIProvider, FixtureScenario
    from alon_ai.integrations.schemas import provider as c

    session = fake_session(Capability.OPENAI_GENERATE, FixtureScenario(scenario))
    result = await FakeOpenAIProvider(session).generate(
        c.GenerationRequest(prompt=SecretStr("secret"), max_output_tokens=10)
    )
    assert result.metadata.status.value == status
    assert result.metadata.error_code is not None
    assert result.metadata.error_code.value == error
    assert result.content is None
    assert "secret" not in result.metadata.model_dump_json()
    if scenario == "TIMEOUT":
        assert result.metadata.usage[0].knowledge is c.CostKnowledge.UNAVAILABLE
        assert result.metadata.usage[0].cost is None


async def test_fake_write_ports_fail_closed_and_gmail_compatibility_is_preserved():
    from alon_ai.integrations.fakes import FakeCalendarProvider, FakeGmailProvider
    from alon_ai.integrations.gmail import EmailDraft, GmailProvider, SendRequest
    from alon_ai.integrations.schemas import provider as c

    session = fake_session(Capability.GMAIL_READ)
    gmail = FakeGmailProvider(session)
    assert isinstance(gmail, GmailProvider)
    with pytest.raises(c.ProviderFailure) as caught:
        await gmail.send(
            SendRequest(
                idempotency_key=uuid4(),
                draft=EmailDraft(
                    to="synthetic@example.com",
                    subject="synthetic",
                    body_text="synthetic",
                ),
            )
        )
    assert caught.value.code is c.ProviderErrorCode.WRITE_AUTHORITY_REQUIRED
    with pytest.raises(c.ProviderFailure):
        await FakeCalendarProvider(session).write(
            c.CalendarWriteRequest(booking_intent_id=uuid4())
        )
    assert session.invocations == ()


def test_malformed_json_contract_entry_point_strips_input():
    sentinel = "UNIQUE-MALFORMED-JSON-secret"
    with pytest.raises(ValidationError) as caught:
        FirecrawlCaptureRequest.model_validate_json("not-json-" + sentinel)
    assert sentinel not in repr(caught.value.errors())
    assert sentinel not in caught.value.json()


async def test_fake_wrong_capability_method_denies_before_invocation():
    from alon_ai.integrations.fakes import FakeFirecrawlProvider
    from alon_ai.integrations.schemas.provider import (
        FirecrawlMapRequest,
        ProviderFailure,
    )

    session = fake_session(Capability.FIRECRAWL_MAP)
    with pytest.raises(ProviderFailure):
        await FakeFirecrawlProvider(session).capture(
            cast(Any, FirecrawlMapRequest(url="https://example.test"))
        )
    assert session.invocations == ()


def test_strict_dto_json_roundtrip_preserves_decimal_uuid_and_aware_datetime():
    from uuid import UUID

    from pydantic import AwareDatetime, field_validator

    from alon_ai.integrations.schemas.provider import StrictDTO

    class ExactValue(StrictDTO):
        record_id: UUID
        amount: Decimal
        observed_at: AwareDatetime

        @field_validator("amount")
        @classmethod
        def positive_amount(cls, amount: Decimal) -> Decimal:
            if amount <= 0:
                raise ValueError("positive amount required")
            return amount

    class Envelope(StrictDTO):
        value: ExactValue
        history: tuple[ExactValue, ...]

    record_id = UUID("00000000-0000-4000-8000-000000000042")
    observed_at = datetime(2026, 9, 12, 18, 0, tzinfo=UTC)
    value = ExactValue(
        record_id=record_id,
        amount=Decimal("0.000000000123"),
        observed_at=observed_at,
    )
    envelope = Envelope(value=value, history=(value,))
    restored_value = ExactValue.model_validate_json(value.model_dump_json())
    restored_envelope = Envelope.model_validate_json(envelope.model_dump_json())
    assert restored_value.record_id == record_id
    assert restored_value.amount == Decimal("0.000000000123")
    assert restored_value.observed_at == observed_at
    assert restored_envelope.value == value
    assert restored_envelope.history == (value,)
    assert restored_envelope.value.observed_at.utcoffset() is not None
    invalid_json = value.model_dump_json().replace('"1.23E-10"', '"-1"')
    with pytest.raises(ValidationError):
        ExactValue.model_validate_json(invalid_json)


@pytest.mark.parametrize("amount", [0.1, True, False])
def test_strict_dto_python_ingress_still_rejects_float_and_bool_money(amount):
    from pydantic import TypeAdapter

    from alon_ai.integrations.schemas.provider import StrictDTO

    class ExactMoney(StrictDTO):
        amount: Decimal

    for parse in (
        lambda: ExactMoney(amount=amount),
        lambda: ExactMoney.model_validate({"amount": amount}),
        lambda: TypeAdapter(ExactMoney).validate_python({"amount": amount}),
    ):
        with pytest.raises(ValidationError):
            parse()


def test_nested_strict_dto_json_errors_hide_fields_input_and_context():
    from alon_ai.integrations.schemas.provider import StrictDTO

    class ExactMoney(StrictDTO):
        amount: Decimal

    class Envelope(StrictDTO):
        value: ExactMoney

    sentinel = "unique-nested-source-secret"
    for raw_json in (
        '{"value":{"amount":"' + sentinel + '"}}',
        '{"value":{"amount":"1.25","' + sentinel + '":"' + sentinel + '"}}',
    ):
        with pytest.raises(ValidationError) as caught:
            Envelope.model_validate_json(raw_json)
        assert sentinel not in str(caught.value)
        assert sentinel not in repr(caught.value.errors())
        assert sentinel not in caught.value.json()
