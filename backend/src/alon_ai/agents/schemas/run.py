"""Immutable OpenAI run intent and outcome contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Version = Annotated[str, Field(min_length=1, max_length=64)]
ModelIdentifier = Annotated[str, Field(min_length=1, max_length=100)]


class OpenAIRunOutcome(StrEnum):
    NO_AI = "NO_AI"
    READY = "READY"
    RECOVERING = "RECOVERING"
    RESULT_UNAVAILABLE = "RESULT_UNAVAILABLE"
    SUCCEEDED = "SUCCEEDED"
    REFUSED = "REFUSED"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    INCOMPLETE = "INCOMPLETE"
    TIMEOUT = "TIMEOUT"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"
    CANCELLED = "CANCELLED"


class OpenAIRunIntent(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, hide_input_in_errors=True
    )

    idempotency_key: UUID
    config_id: UUID
    config_version: UUID
    experiment_id: UUID
    workflow_id: UUID
    operation_id: UUID
    agent_run_id: UUID | None
    prompt_version: Version
    prompt_hash: Hash
    schema_version: Version
    output_schema_hash: Hash
    model_identifier: ModelIdentifier
    reasoning_effort: Annotated[
        str, Field(pattern=r"^(none|minimal|low|medium|high|xhigh)$")
    ]
    accepted_input_refs: tuple[UUID, ...]
    input_hash: Hash
    client_request_id: UUID
    created_at: AwareDatetime


class OpenAIRunRecord(OpenAIRunIntent):
    call_id: UUID | None
    outcome: OpenAIRunOutcome
    output_hash: Hash | None
    finished_at: AwareDatetime | None


class OpenAIRunConflict(Exception):
    def __init__(self):
        super().__init__("OpenAI run identity or result conflicts with durable record")


class OpenAIRunNotFound(Exception):
    def __init__(self):
        super().__init__("OpenAI run intent not found")


class OpenAIRunStoreError(Exception):
    def __init__(self):
        super().__init__("OpenAI run evidence store unavailable")
