"""Application-owned OpenAI execution through the existing governed read path."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from pydantic import SecretStr

from alon_ai.agents.schemas.openai import (
    OpenAIProfile,
    ParsedResponse,
    Route,
    StrictDTO,
    classify_response,
)
from alon_ai.agents.schemas.run import OpenAIRunOutcome
from alon_ai.integrations.openai import ResponsesTransport
from alon_ai.policies.provider_rights import (
    GrantEvent,
    ProviderUsageGrant,
    RuntimeContent,
)
from alon_ai.provider_usage.schemas.accounting import CallReceipt
from alon_ai.services.schemas.records import ArtifactInput, SourceReference


@dataclass(frozen=True)
class AcceptedSource:
    """Current source grant is supplied by the trusted content repository."""

    evidence_ref: UUID
    content: RuntimeContent
    current_grant: ProviderUsageGrant
    events: tuple[GrantEvent, ...] = ()


@dataclass(frozen=True)
class AcceptedArtifact:
    """An exact persisted product record reference, resolved by the runtime."""

    artifact: ArtifactInput
    experiment_id: UUID
    schema_version: int
    selection_id: UUID | None = None
    cycle_id: UUID | None = None
    attempt_id: UUID | None = None
    return_id: UUID | None = None


@dataclass(frozen=True)
class AcceptedOperatorProfile:
    """Exact experiment-bound first-party capability context."""

    profile_id: UUID
    version: int
    content_hash: str
    experiment_id: UUID
    profile_schema_version: int = 2


@dataclass(frozen=True)
class AcceptedRetainedEvidence:
    """An exact persisted source row, not caller-provided evidence text."""

    reference: SourceReference


@dataclass(frozen=True)
class OpenAIExecution:
    route: Route
    outcome: OpenAIRunOutcome
    receipt: CallReceipt | None
    output: StrictDTO | None = field(repr=False)

    def __reduce_ex__(self, protocol: object):
        raise TypeError("advisory runtime output cannot be serialized")


class BoundedOpenAICall:
    """One transport attempt and deterministic advisory-result classification."""

    def __init__(self, profile: OpenAIProfile, transport: ResponsesTransport) -> None:
        self.profile = profile
        self.transport = transport

    async def dispatch(
        self, input_json: str, secret: SecretStr, client_request_id: UUID
    ) -> Mapping[str, Any]:
        return await self.transport.create(
            profile=self.profile,
            input_json=input_json,
            secret=secret,
            client_request_id=client_request_id,
            timeout_seconds=self.profile.timeout_seconds,
        )

    def classify(self, response: Mapping[str, Any], input_json: str) -> ParsedResponse:
        parsed = classify_response(response, self.profile)
        if (
            parsed.outcome == "SUCCEEDED"
            and parsed.output is not None
            and self.profile.output_validator is not None
        ):
            try:
                self.profile.output_validator(parsed.output, input_json)
            except (PermissionError, ValueError):
                parsed = ParsedResponse(
                    "SCHEMA_MISMATCH",
                    None,
                    None,
                    parsed.usage,
                    parsed.external_request_id,
                )
        return parsed
