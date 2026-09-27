"""Explicit offline adapters for tests/development; no network implementation.

These raw fixture ports are not production application services. A governed
executor must supply admission, reservation and validated repository lineage.
Writes intentionally remain unavailable even in fixtures.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from importlib.resources import files
from types import MappingProxyType
from typing import Literal
from uuid import uuid5

from alon_ai.integrations.gmail import SendRequest, SendResult
from alon_ai.integrations.schemas.provider import (
    CAPABILITIES,
    BraveSearchRequest,
    CalendarReadRequest,
    CalendarWriteRequest,
    Capability,
    ContactDiscoveryRequest,
    ContentField,
    CostKnowledge,
    EmailPresence,
    EmailVerificationRequest,
    FirecrawlCaptureRequest,
    FirecrawlMapRequest,
    GenerationRequest,
    MailboxReadRequest,
    Nature,
    Provider,
    ProviderCallResult,
    ProviderErrorCode,
    ProviderFailure,
    ProviderResultMetadata,
    ResultStatus,
    StrictDTO,
    UsageComponent,
    UsageObservation,
)
from alon_ai.policies.provider_rights import (
    GrantEvent,
    IntendedUse,
    ProviderUsageGrant,
    RightsMode,
    RuntimeContent,
    evaluate_rights,
)


class FixtureScenario(StrEnum):
    SUCCESS = "SUCCESS"
    REFUSED = "REFUSED"
    ERROR = "ERROR"
    MALFORMED = "MALFORMED"
    TIMEOUT = "TIMEOUT"


class FixtureProvenance(StrictDTO):
    fixture_id: Literal["synthetic-provider-v1"] = "synthetic-provider-v1"
    source_kind: Literal["SYNTHETIC"] = "SYNTHETIC"
    license: Literal["TEST_ONLY_SYNTHETIC"] = "TEST_ONLY_SYNTHETIC"


class FixtureInvocation(StrictDTO):
    capability: Capability
    ordinal: int


class FakeSession:
    """Injected, capability-scoped fixture state. Never records request content."""

    def __init__(
        self,
        *,
        grants: Mapping[Capability, ProviderUsageGrant],
        intended_uses: Mapping[Capability, IntendedUse],
        clock: Callable[[], datetime],
        events: Callable[[], tuple[GrantEvent, ...]] = lambda: (),
        scenario: FixtureScenario = FixtureScenario.SUCCESS,
    ):
        if not isinstance(scenario, FixtureScenario):
            raise TypeError("fixture scenario required")
        self._grants = MappingProxyType(dict(grants))
        self._uses = MappingProxyType(dict(intended_uses))
        self._clock = clock
        self._events = events
        self._scenario = scenario
        self._invocations: list[FixtureInvocation] = []
        fixture = json.loads(
            files("alon_ai.integrations")
            .joinpath("fixtures/synthetic-v1.json")
            .read_text()
        )
        if (
            fixture["source_kind"] != "SYNTHETIC"
            or fixture["license"] != "TEST_ONLY_SYNTHETIC"
        ):
            raise ProviderFailure(ProviderErrorCode.MALFORMED_RESPONSE)
        self.provenance = FixtureProvenance(
            fixture_id=fixture["fixture_id"],
            source_kind=fixture["source_kind"],
            license=fixture["license"],
        )
        self._content = {
            Capability(cap): MappingProxyType(
                {ContentField(k): tuple(v) for k, v in fields.items()}
            )
            for cap, fields in fixture["content"].items()
        }

    @property
    def invocations(self) -> tuple[FixtureInvocation, ...]:
        return tuple(self._invocations)

    def _run(
        self, capability: Capability, provider: Provider
    ) -> ProviderCallResult[RuntimeContent]:
        spec = CAPABILITIES[capability]
        if spec.provider is not provider:
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        if spec.nature is Nature.WRITE:
            raise ProviderFailure(ProviderErrorCode.WRITE_AUTHORITY_REQUIRED)
        grant, use = self._grants.get(capability), self._uses.get(capability)
        now = self._clock()
        if (
            use is None
            or use.capability is not capability
            or evaluate_rights(grant, self._events(), use, now=now).mode
            is RightsMode.DENIED
        ):
            raise ProviderFailure(ProviderErrorCode.DENIED)
        if grant is None:
            raise ProviderFailure(ProviderErrorCode.DENIED)
        self._invocations.append(
            FixtureInvocation(capability=capability, ordinal=len(self._invocations) + 1)
        )
        status, error = {
            FixtureScenario.SUCCESS: (ResultStatus.SUCCEEDED, None),
            FixtureScenario.REFUSED: (ResultStatus.REFUSED, ProviderErrorCode.REFUSED),
            FixtureScenario.ERROR: (ResultStatus.FAILED, ProviderErrorCode.UNAVAILABLE),
            FixtureScenario.MALFORMED: (
                ResultStatus.FAILED,
                ProviderErrorCode.MALFORMED_RESPONSE,
            ),
            FixtureScenario.TIMEOUT: (ResultStatus.UNKNOWN, ProviderErrorCode.TIMEOUT),
        }[self._scenario]
        unknown = self._scenario is FixtureScenario.TIMEOUT
        component = UsageComponent.REQUEST
        if capability is Capability.HUNTER_EMAIL_VERIFICATION:
            component = UsageComponent.VERIFICATION
        elif capability in {
            Capability.HUNTER_DOMAIN_SEARCH,
            Capability.HUNTER_EMAIL_FINDER,
        }:
            component = UsageComponent.DISCOVERY
        elif capability in {
            Capability.HUNTER_COMPANY_ENRICHMENT,
            Capability.HUNTER_PERSON_ENRICHMENT,
        }:
            component = UsageComponent.ENRICHMENT
        metadata = ProviderResultMetadata(
            capability=capability,
            external_request_id=f"synthetic-{len(self._invocations)}",
            started_at=now,
            finished_at=now,
            status=status,
            error_code=error,
            usage=(
                UsageObservation(
                    component=component,
                    quantity=None if unknown else Decimal(1),
                    currency="USD",
                    cost=None if unknown else Decimal(0),
                    knowledge=CostKnowledge.UNAVAILABLE
                    if unknown
                    else CostKnowledge.FINAL,
                    observation_key=uuid5(
                        grant.grant_id, f"{capability.value}:{len(self._invocations)}"
                    ),
                ),
            ),
        )
        content = (
            RuntimeContent(
                self._content[capability],
                grant=grant,
                intended_use=use,
                observed_at=now,
            )
            if status is ResultStatus.SUCCEEDED
            else None
        )
        return ProviderCallResult(metadata, content)


class FakeOpenAIProvider:
    def __init__(self, session: FakeSession):
        self._session = session

    async def generate(
        self, request: GenerationRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, GenerationRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        return self._session._run(request.capability, Provider.OPENAI)


class FakeBraveProvider:
    def __init__(self, session: FakeSession):
        self._session = session

    async def search(
        self, request: BraveSearchRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, BraveSearchRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        return self._session._run(request.capability, Provider.BRAVE)


class FakeFirecrawlProvider:
    def __init__(self, session: FakeSession):
        self._session = session

    async def map(
        self, request: FirecrawlMapRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, FirecrawlMapRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        return self._session._run(request.capability, Provider.FIRECRAWL)

    async def capture(
        self, request: FirecrawlCaptureRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, FirecrawlCaptureRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        return self._session._run(request.capability, Provider.FIRECRAWL)


class FakeContactDiscoveryProvider:
    def __init__(self, session: FakeSession):
        self._session = session

    def _discover(
        self, request: ContactDiscoveryRequest, capability: Capability
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, ContactDiscoveryRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        if request.brave_observation.presence is not EmailPresence.ABSENT:
            raise ProviderFailure(ProviderErrorCode.DENIED)
        return self._session._run(capability, Provider.HUNTER)

    async def domain_search(
        self, request: ContactDiscoveryRequest
    ) -> ProviderCallResult[RuntimeContent]:
        return self._discover(request, Capability.HUNTER_DOMAIN_SEARCH)

    async def email_finder(
        self, request: ContactDiscoveryRequest
    ) -> ProviderCallResult[RuntimeContent]:
        return self._discover(request, Capability.HUNTER_EMAIL_FINDER)

    async def company_enrichment(
        self, request: ContactDiscoveryRequest
    ) -> ProviderCallResult[RuntimeContent]:
        return self._discover(request, Capability.HUNTER_COMPANY_ENRICHMENT)

    async def person_enrichment(
        self, request: ContactDiscoveryRequest
    ) -> ProviderCallResult[RuntimeContent]:
        return self._discover(request, Capability.HUNTER_PERSON_ENRICHMENT)


class FakeEmailVerificationProvider:
    def __init__(self, session: FakeSession):
        self._session = session

    async def verify(
        self, request: EmailVerificationRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, EmailVerificationRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        return self._session._run(request.capability, Provider.HUNTER)


class FakeGmailProvider:
    """Compatible with existing GmailProvider; send requires future gateway wiring."""

    def __init__(self, session: FakeSession):
        self._session = session

    async def read(
        self, request: MailboxReadRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, MailboxReadRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        return self._session._run(request.capability, Provider.GMAIL)

    async def send(self, request: SendRequest) -> SendResult:
        raise ProviderFailure(ProviderErrorCode.WRITE_AUTHORITY_REQUIRED)


class FakeCalendarProvider:
    def __init__(self, session: FakeSession):
        self._session = session

    async def read(
        self, request: CalendarReadRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, CalendarReadRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        return self._session._run(request.capability, Provider.GOOGLE_CALENDAR)

    async def write(
        self, request: CalendarWriteRequest
    ) -> ProviderCallResult[RuntimeContent]:
        raise ProviderFailure(ProviderErrorCode.WRITE_AUTHORITY_REQUIRED)
