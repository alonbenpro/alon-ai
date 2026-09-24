"""Versioned provider ports. These describe evidence access, never effect authority.

DTOs carry safe references and operational facts. Request content is excluded from
serialization; response content lives in a separate nonserializable runtime object.
Concrete network adapters must enforce DNS and redirect egress policy as well.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol, Self, TypeVar
from urllib.parse import parse_qsl, unquote, urlsplit
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import SchemaValidator, core_schema

if TYPE_CHECKING:
    from alon_ai.providers.rights import RuntimeContent


def _native_json_schema(schema: Any) -> Any:
    """Remove only our Python error wrappers for the sanitized JSON entry point.

    Core wrap validators materialize JSON input as Python values and break strict
    Decimal/datetime JSON hydration. Removing them here preserves Pydantic's own
    JSON validation, including nested models and discriminated unions. The caller
    catches and sanitizes all JSON parser/validation errors instead.
    """
    if isinstance(schema, dict):
        if schema.get("type") == "function-wrap" and schema.get("metadata", {}).get(
            "provider_python_error_wrapper"
        ):
            return _native_json_schema(schema["schema"])
        return {key: _native_json_schema(value) for key, value in schema.items()}
    if isinstance(schema, list):
        return [_native_json_schema(value) for value in schema]
    if isinstance(schema, tuple):
        return tuple(_native_json_schema(value) for value in schema)
    return schema


class StrictDTO(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, hide_input_in_errors=True
    )
    schema_version: Literal[1] = 1

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        try:
            # Only the error wrappers installed below are removed. User field/
            # model validators and strict native JSON conversion remain intact.
            validator = SchemaValidator(
                _native_json_schema(cls.__pydantic_core_schema__)
            )
            return validator.validate_json(
                json_data,
                strict=strict,
                extra=extra,
                context=context,
                by_alias=by_alias,
                by_name=by_name,
            )
        except ValidationError:
            raise ValidationError.from_exception_data(
                "Provider contract",
                [
                    {
                        "type": "value_error",
                        "loc": (),
                        "input": None,
                        "ctx": {"error": ValueError("invalid provider contract")},
                    }
                ],
                hide_input=True,
            ) from None

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def sanitize(value: object, validate: core_schema.ValidatorFunctionWrapHandler):
            try:
                return validate(value)
            except ValidationError:
                raise ValidationError.from_exception_data(
                    "Provider contract",
                    [
                        {
                            "type": "value_error",
                            "loc": (),
                            "input": None,
                            "ctx": {"error": ValueError("invalid provider contract")},
                        }
                    ],
                    hide_input=True,
                ) from None

        return core_schema.no_info_wrap_validator_function(
            sanitize,
            handler(source),
            metadata={"provider_python_error_wrapper": True},
        )


class Provider(StrEnum):
    OPENAI = "OPENAI"
    BRAVE = "BRAVE"
    FIRECRAWL = "FIRECRAWL"
    HUNTER = "HUNTER"
    GMAIL = "GMAIL"
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"


class Capability(StrEnum):
    OPENAI_GENERATE = "OPENAI_GENERATE"
    BRAVE_WEB_COVERAGE = "BRAVE_WEB_COVERAGE"
    BRAVE_LOCAL_DISCOVERY = "BRAVE_LOCAL_DISCOVERY"
    BRAVE_COMPANY_DISCOVERY = "BRAVE_COMPANY_DISCOVERY"
    FIRECRAWL_MAP = "FIRECRAWL_MAP"
    FIRECRAWL_PAGE_CAPTURE = "FIRECRAWL_PAGE_CAPTURE"
    FIRECRAWL_PDF_CAPTURE = "FIRECRAWL_PDF_CAPTURE"
    FIRECRAWL_JS_RETRIEVAL = "FIRECRAWL_JS_RETRIEVAL"
    HUNTER_DOMAIN_SEARCH = "HUNTER_DOMAIN_SEARCH"
    HUNTER_EMAIL_FINDER = "HUNTER_EMAIL_FINDER"
    HUNTER_COMPANY_ENRICHMENT = "HUNTER_COMPANY_ENRICHMENT"
    HUNTER_PERSON_ENRICHMENT = "HUNTER_PERSON_ENRICHMENT"
    HUNTER_EMAIL_VERIFICATION = "HUNTER_EMAIL_VERIFICATION"
    GMAIL_READ = "GMAIL_READ"
    GMAIL_SEND = "GMAIL_SEND"
    GOOGLE_CALENDAR_READ = "GOOGLE_CALENDAR_READ"
    GOOGLE_CALENDAR_WRITE = "GOOGLE_CALENDAR_WRITE"


class Nature(StrEnum):
    GENERATION = "GENERATION"
    READ = "READ"
    WRITE = "WRITE"


class CapabilitySpec(StrictDTO):
    provider: Provider
    nature: Nature


CAPABILITIES: Mapping[Capability, CapabilitySpec] = MappingProxyType(
    {
        capability: CapabilitySpec(
            provider=Provider.GOOGLE_CALENDAR
            if capability.name.startswith("GOOGLE_CALENDAR")
            else Provider(capability.name.split("_")[0]),
            nature=Nature.GENERATION
            if capability is Capability.OPENAI_GENERATE
            else Nature.WRITE
            if capability in {Capability.GMAIL_SEND, Capability.GOOGLE_CALENDAR_WRITE}
            else Nature.READ,
        )
        for capability in Capability
    }
)


class Purpose(StrEnum):
    GENERATION = "GENERATION"
    RESEARCH = "RESEARCH"
    LEAD_DISCOVERY = "LEAD_DISCOVERY"
    OFFICIAL_SOURCE_IDENTIFICATION = "OFFICIAL_SOURCE_IDENTIFICATION"
    CONTACT_DISCOVERY = "CONTACT_DISCOVERY"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    MAILBOX_READ = "MAILBOX_READ"
    CALENDAR_READ = "CALENDAR_READ"
    GATEWAY_EFFECT = "GATEWAY_EFFECT"


class ContentField(StrEnum):
    URL = "URL"
    TITLE = "TITLE"
    TEXT = "TEXT"
    EMAIL = "EMAIL"
    COMPANY = "COMPANY"
    RANKING = "RANKING"
    MESSAGE = "MESSAGE"
    EVENT = "EVENT"


class AgentActor(StrictDTO):
    kind: Literal["agent"] = "agent"
    agent_run_id: UUID


class SystemActor(StrictDTO):
    kind: Literal["system"] = "system"
    service: Literal[
        "provider-executor",
        "contact-resolution",
        "campaign-supply",
        "send-gateway",
        "calendar-gateway",
    ]


class OperationRunKind(StrEnum):
    RESEARCH = "RESEARCH"
    DISCOVERY = "DISCOVERY"
    ENRICHMENT = "ENRICHMENT"
    VERIFICATION = "VERIFICATION"
    SYSTEM = "SYSTEM"


class CallAttribution(StrictDTO):
    """Repository scope resolver must validate all referenced run relationships."""

    experiment_id: UUID
    workflow_run_id: UUID
    operation_run_id: UUID
    operation_run_kind: OperationRunKind = OperationRunKind.SYSTEM
    actor: Annotated[AgentActor | SystemActor, Field(discriminator="kind")]
    correlation_id: UUID
    logical_operation_id: UUID
    config_version: UUID
    deadline: AwareDatetime


class SafeRequestMetadata(StrictDTO):
    """Only customer-owned configuration references; never result-derived values."""

    config_ref: UUID
    requested_count: int = Field(default=1, ge=1, le=100)


class CostKnowledge(StrEnum):
    ESTIMATE = "ESTIMATE"
    FINAL = "FINAL"
    UNAVAILABLE = "UNAVAILABLE"


class UsageComponent(StrEnum):
    REQUEST = "REQUEST"
    INPUT_TOKEN = "INPUT_TOKEN"
    OUTPUT_TOKEN = "OUTPUT_TOKEN"
    CACHED_TOKEN = "CACHED_TOKEN"
    SEARCH_RESULT = "SEARCH_RESULT"
    CAPTURE_PAGE = "CAPTURE_PAGE"
    DISCOVERY = "DISCOVERY"
    ENRICHMENT = "ENRICHMENT"
    VERIFICATION = "VERIFICATION"


class UsageObservation(StrictDTO):
    component: UsageComponent
    quantity: Decimal | None = Field(ge=0, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    cost: Decimal | None = Field(ge=0, allow_inf_nan=False)
    knowledge: CostKnowledge
    observation_key: UUID

    @model_validator(mode="after")
    def known_cost(self) -> UsageObservation:
        if (self.knowledge is CostKnowledge.UNAVAILABLE) != (self.cost is None):
            raise ValueError("cost knowledge mismatch")
        return self


class ProviderErrorCode(StrEnum):
    DENIED = "DENIED"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    INCOMPLETE_RESULT = "INCOMPLETE_RESULT"
    CANCELLED_RESULT = "CANCELLED_RESULT"
    REFUSED = "REFUSED"
    WRITE_AUTHORITY_REQUIRED = "WRITE_AUTHORITY_REQUIRED"


class ProviderFailure(Exception):
    """Only classified codes, never upstream bodies or arbitrary exception text."""

    def __init__(self, code: ProviderErrorCode):
        if not isinstance(code, ProviderErrorCode):
            raise TypeError("provider error code required")
        self.code = code
        super().__init__(code.value)


class ResultStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    REFUSED = "REFUSED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ProviderResultMetadata(StrictDTO):
    capability: Capability
    external_request_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_-]{1,100}$"
    )
    started_at: AwareDatetime
    finished_at: AwareDatetime
    status: ResultStatus
    error_code: ProviderErrorCode | None = None
    usage: tuple[UsageObservation, ...] = ()

    @model_validator(mode="after")
    def valid_result(self) -> ProviderResultMetadata:
        if self.finished_at < self.started_at:
            raise ValueError("invalid result timing")
        if (self.status is ResultStatus.SUCCEEDED) != (self.error_code is None):
            raise ValueError("result status mismatch")
        return self


T = TypeVar("T")


class ProviderCallResult[T]:
    """Runtime-only result. Persist metadata explicitly, never the whole result."""

    __slots__ = ("content", "metadata")

    def __init__(self, metadata: ProviderResultMetadata, content: T | None):
        self.metadata = metadata
        self.content = content

    def __repr__(self) -> str:
        return f"ProviderCallResult(metadata={self.metadata!r}, content=<runtime-only>)"

    def __reduce_ex__(self, protocol: object):
        raise TypeError("runtime provider result cannot be serialized")


def public_url(value: str) -> str:
    """Syntactic egress guard only; future transports MUST validate DNS/redirects."""
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (
            len(value) > 2048
            or any(c.isspace() or ord(c) < 32 for c in value)
            or "\\" in value
        ):
            raise ValueError
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.username
            or parsed.password
            or not host
            or parsed.fragment
        ):
            raise ValueError
        if parsed.port not in {None, 80, 443}:
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if "." not in host or host.endswith(
                (".localhost", ".local", ".internal", ".lan")
            ):
                raise ValueError from None
            if not re.fullmatch(r"[a-z0-9.-]+", host) or re.fullmatch(
                r"(?:[0-9]+|0x[0-9a-f]+)(?:\.(?:[0-9]+|0x[0-9a-f]+))*", host
            ):
                raise ValueError from None
        else:
            if not address.is_global:
                raise ValueError
        for key, _ in parse_qsl(parsed.query):
            normalized = unquote(key).lower().replace("-", "_")
            if any(
                part in normalized
                for part in (
                    "token",
                    "key",
                    "secret",
                    "password",
                    "auth",
                    "credential",
                    "signature",
                )
            ):
                raise ValueError
    except (ValueError, UnicodeError):
        raise ValueError("public credential-free URL required") from None
    return value


class GenerationRequest(StrictDTO):
    capability: Literal[Capability.OPENAI_GENERATE] = Capability.OPENAI_GENERATE
    prompt: SecretStr = Field(exclude=True, repr=False)
    max_output_tokens: int = Field(ge=1, le=32768)


class BraveSearchRequest(StrictDTO):
    capability: Literal[
        Capability.BRAVE_WEB_COVERAGE,
        Capability.BRAVE_LOCAL_DISCOVERY,
        Capability.BRAVE_COMPANY_DISCOVERY,
    ]
    query: SecretStr = Field(exclude=True, repr=False)
    limit: int = Field(default=10, ge=1, le=100)


class CaptureFormat(StrEnum):
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    TEXT = "TEXT"


class FirecrawlMapRequest(StrictDTO):
    capability: Literal[Capability.FIRECRAWL_MAP] = Capability.FIRECRAWL_MAP
    url: str = Field(exclude=True, repr=False)
    limit: int = Field(default=10, ge=1, le=100)
    _url_guard = field_validator("url")(public_url)


class FirecrawlCaptureRequest(StrictDTO):
    capability: Literal[
        Capability.FIRECRAWL_PAGE_CAPTURE,
        Capability.FIRECRAWL_PDF_CAPTURE,
        Capability.FIRECRAWL_JS_RETRIEVAL,
    ] = Capability.FIRECRAWL_PAGE_CAPTURE
    url: str = Field(exclude=True, repr=False)
    formats: tuple[CaptureFormat, ...] = (CaptureFormat.MARKDOWN,)
    wait_ms: int = Field(default=0, ge=0, le=10000)
    _url_guard = field_validator("url")(public_url)

    @model_validator(mode="after")
    def deterministic_options(self) -> FirecrawlCaptureRequest:
        if not self.formats or len(set(self.formats)) != len(self.formats):
            raise ValueError("unique deterministic capture format required")
        if self.wait_ms and self.capability is not Capability.FIRECRAWL_JS_RETRIEVAL:
            raise ValueError("wait requires JS retrieval capability")
        return self


class EmailPresence(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class EmailSourceObservation(StrictDTO):
    business_id: UUID
    provider_call_id: UUID
    capability: Literal[
        Capability.BRAVE_LOCAL_DISCOVERY, Capability.BRAVE_COMPANY_DISCOVERY
    ]
    grant_id: UUID
    grant_version: int = Field(ge=1)
    evidence_ref: UUID | None
    observed_at: AwareDatetime
    presence: EmailPresence

    @model_validator(mode="after")
    def evidence_for_inspected_response(self) -> EmailSourceObservation:
        if (
            self.presence is not EmailPresence.NOT_AVAILABLE
            and self.evidence_ref is None
        ):
            raise ValueError("inspected source evidence required")
        return self


class ContactDiscoveryRequest(StrictDTO):
    business_id: UUID
    brave_observation: EmailSourceObservation
    domain: SecretStr = Field(exclude=True, repr=False)
    person_name: SecretStr | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="after")
    def evidence_scope(self) -> ContactDiscoveryRequest:
        if self.business_id != self.brave_observation.business_id:
            raise ValueError("business observation scope mismatch")
        return self


class VerificationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    ACCEPT_ALL = "ACCEPT_ALL"
    UNKNOWN = "UNKNOWN"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"


class VerificationPolicy(StrictDTO):
    policy_id: UUID
    version: int = Field(ge=1)
    max_age_seconds: int = Field(gt=0)
    accepted_statuses: frozenset[VerificationStatus] = frozenset(
        {VerificationStatus.VALID}
    )
    require_business_match: Literal[True] = True

    @model_validator(mode="after")
    def safe_statuses(self) -> VerificationPolicy:
        if self.accepted_statuses != frozenset({VerificationStatus.VALID}):
            raise ValueError("V1 requires valid verification")
        return self


class EmailVerificationRequest(StrictDTO):
    capability: Literal[Capability.HUNTER_EMAIL_VERIFICATION] = (
        Capability.HUNTER_EMAIL_VERIFICATION
    )
    business_id: UUID
    email_candidate_id: UUID
    source_evidence_ref: UUID
    business_match_ref: UUID
    address: SecretStr = Field(exclude=True, repr=False)


class EmailVerificationObservation(StrictDTO):
    business_id: UUID
    email_candidate_id: UUID
    source_evidence_ref: UUID
    business_match_ref: UUID
    provider_call_id: UUID
    status: VerificationStatus
    verified_at: AwareDatetime
    expires_at: AwareDatetime
    policy_id: UUID
    policy_version: int = Field(ge=1)


class MailboxReadRequest(StrictDTO):
    capability: Literal[Capability.GMAIL_READ] = Capability.GMAIL_READ
    mailbox_id: UUID
    limit: int = Field(default=10, ge=1, le=100)


class CalendarReadRequest(StrictDTO):
    capability: Literal[Capability.GOOGLE_CALENDAR_READ] = (
        Capability.GOOGLE_CALENDAR_READ
    )
    calendar_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def valid_window(self) -> CalendarReadRequest:
        if self.ends_at <= self.starts_at:
            raise ValueError("invalid calendar window")
        return self


class CalendarWriteRequest(StrictDTO):
    capability: Literal[Capability.GOOGLE_CALENDAR_WRITE] = (
        Capability.GOOGLE_CALENDAR_WRITE
    )
    booking_intent_id: UUID


class OpenAIProvider(Protocol):
    async def generate(
        self, request: GenerationRequest
    ) -> ProviderCallResult[RuntimeContent]: ...


class BraveProvider(Protocol):
    async def search(
        self, request: BraveSearchRequest
    ) -> ProviderCallResult[RuntimeContent]: ...


class FirecrawlProvider(Protocol):
    async def map(
        self, request: FirecrawlMapRequest
    ) -> ProviderCallResult[RuntimeContent]: ...
    async def capture(
        self, request: FirecrawlCaptureRequest
    ) -> ProviderCallResult[RuntimeContent]: ...


class ContactDiscoveryProvider(Protocol):
    async def domain_search(
        self, request: ContactDiscoveryRequest
    ) -> ProviderCallResult[RuntimeContent]: ...
    async def email_finder(
        self, request: ContactDiscoveryRequest
    ) -> ProviderCallResult[RuntimeContent]: ...
    async def company_enrichment(
        self, request: ContactDiscoveryRequest
    ) -> ProviderCallResult[RuntimeContent]: ...
    async def person_enrichment(
        self, request: ContactDiscoveryRequest
    ) -> ProviderCallResult[RuntimeContent]: ...


class EmailVerificationProvider(Protocol):
    async def verify(
        self, request: EmailVerificationRequest
    ) -> ProviderCallResult[RuntimeContent]: ...


class GmailReadProvider(Protocol):
    async def read(
        self, request: MailboxReadRequest
    ) -> ProviderCallResult[RuntimeContent]: ...


class CalendarProvider(Protocol):
    async def read(
        self, request: CalendarReadRequest
    ) -> ProviderCallResult[RuntimeContent]: ...
    async def write(
        self, request: CalendarWriteRequest
    ) -> ProviderCallResult[RuntimeContent]: ...


def inspect_brave_email(
    *,
    candidate: str | None,
    business_id: UUID,
    provider_call_id: UUID,
    capability: Literal[
        Capability.BRAVE_LOCAL_DISCOVERY, Capability.BRAVE_COMPANY_DISCOVERY
    ],
    grant_id: UUID,
    grant_version: int,
    evidence_ref: UUID,
    observed_at: datetime,
) -> EmailSourceObservation:
    """Trusted parser of an inspected source-authorized response; syntax is irrelevant."""
    return EmailSourceObservation(
        business_id=business_id,
        provider_call_id=provider_call_id,
        capability=capability,
        grant_id=grant_id,
        grant_version=grant_version,
        evidence_ref=evidence_ref,
        observed_at=observed_at,
        presence=EmailPresence.ABSENT if candidate is None else EmailPresence.PRESENT,
    )
