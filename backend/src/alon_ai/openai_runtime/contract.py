"""Trusted, immutable Responses profiles and advisory result parsing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Literal
from uuid import UUID

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from pydantic import ValidationError

from alon_ai.providers.contracts import StrictDTO


class AdvisoryAnswer(StrictDTO):
    """Small initial output contract; role-specific schemas belong to later L06 work."""

    answer: str


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _strict_schema(node: object) -> bool:
    if not isinstance(node, dict):
        return False
    kind = node.get("type")
    if kind == "object":
        properties = node.get("properties")
        return (
            isinstance(properties, dict)
            and node.get("additionalProperties") is False
            and set(node.get("required", [])) == set(properties)
            and all(_strict_schema(value) for value in properties.values())
        )
    if kind == "array":
        return _strict_schema(node.get("items"))
    return kind in {"string", "integer", "number", "boolean", "null"}


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class OpenAIProfile:
    """Provisioned application policy; no agent-controlled model or tools field."""

    config_id: UUID
    config_version: UUID
    adapter_version: UUID
    prompt_version: str
    instructions: str = field(repr=False)
    schema_version: str
    json_schema: Mapping[str, Any] = field(repr=False)
    output_model: type[StrictDTO]
    model_identifier: str
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"]
    max_output_tokens: int
    timeout_seconds: int = 60
    output_validator: Callable[[StrictDTO, str], None] | None = field(
        default=None, repr=False, compare=False
    )
    _schema_json: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            not self.prompt_version
            or not self.schema_version
            or not self.instructions
            or not self.model_identifier
            or not 1 <= self.max_output_tokens <= 32768
            or not 1 <= self.timeout_seconds <= 3600
            or not _strict_schema(dict(self.json_schema))
            or not issubclass(self.output_model, StrictDTO)
            or self.output_validator is not None
            and not callable(self.output_validator)
        ):
            raise ValueError("invalid immutable OpenAI profile")
        # An owned copy prevents a caller mutating a provisioned schema after review.
        schema_json = canonical_json(self.json_schema)
        object.__setattr__(self, "_schema_json", schema_json)
        object.__setattr__(self, "json_schema", _freeze(json.loads(schema_json)))

    @property
    def schema_json(self) -> str:
        return self._schema_json


class Route(StrEnum):
    NO_AI = "NO_AI"
    CHEAP = "CHEAP"
    STRONGER = "STRONGER"
    PREMIUM = "PREMIUM"


@dataclass(frozen=True)
class PremiumAuthorization:
    authorization_id: UUID
    scope: UUID
    expires_at: datetime
    approved_by: UUID
    approved_at: datetime


@dataclass(frozen=True)
class RoutingFacts:
    needs_ai: bool
    validated_escalation: bool = False
    premium_requested: bool = False
    premium_authorization: PremiumAuthorization | None = None


@dataclass(frozen=True)
class RouteSelection:
    route: Route
    config_id: UUID | None


@dataclass(frozen=True)
class RoutingPolicy:
    cheap: UUID
    stronger: UUID
    premium: UUID
    approved_premium: tuple[PremiumAuthorization, ...] = ()

    def select(
        self, facts: RoutingFacts, *, scope: UUID, now: datetime
    ) -> RouteSelection:
        selection = self.resolve(facts, scope=scope)
        authorization = facts.premium_authorization
        if selection.route is Route.PREMIUM and (
            authorization is None
            or now.tzinfo is None
            or authorization.expires_at.tzinfo is None
            or authorization.approved_at.tzinfo is None
            or authorization.approved_at > now
            or now >= authorization.expires_at
        ):
            raise PermissionError("premium route requires current scoped authorization")
        return selection

    def resolve(self, facts: RoutingFacts, *, scope: UUID) -> RouteSelection:
        """Resolve immutable identity; current authority is required only for dispatch."""
        if not facts.needs_ai:
            return RouteSelection(Route.NO_AI, None)
        if facts.premium_requested:
            authorization = facts.premium_authorization
            if (
                authorization is None
                or authorization not in self.approved_premium
                or authorization.scope != scope
            ):
                raise PermissionError(
                    "premium route requires current scoped authorization"
                )
            return RouteSelection(Route.PREMIUM, self.premium)
        if facts.validated_escalation:
            return RouteSelection(Route.STRONGER, self.stronger)
        return RouteSelection(Route.CHEAP, self.cheap)


ResponseOutcome = Literal[
    "SUCCEEDED",
    "REFUSED",
    "SCHEMA_MISMATCH",
    "INCOMPLETE",
    "FAILED",
    "CANCELLED",
    "UNCERTAIN",
]


@dataclass(frozen=True)
class ParsedResponse:
    outcome: ResponseOutcome
    output: StrictDTO | None = field(repr=False)
    output_hash: str | None
    usage: Mapping[str, int] | None
    external_request_id: str | None


def _usage(response: Mapping[str, Any]) -> Mapping[str, int] | None:
    raw = response.get("usage")
    if not isinstance(raw, dict):
        return None
    if any(
        type(raw.get(k)) is not int or raw[k] < 0
        for k in ("input_tokens", "output_tokens", "total_tokens")
    ):
        return None
    if raw["total_tokens"] != raw["input_tokens"] + raw["output_tokens"]:
        return None
    result = {
        key: raw[key] for key in ("input_tokens", "output_tokens", "total_tokens")
    }
    details = raw.get("input_tokens_details")
    if isinstance(details, dict) and "cached_tokens" in details:
        cached = details["cached_tokens"]
        if type(cached) is not int or cached < 0 or cached > raw["input_tokens"]:
            return None
        result["cached_tokens"] = cached
    return MappingProxyType(result)


def classify_response(
    response: Mapping[str, Any], profile: OpenAIProfile
) -> ParsedResponse:
    """Never return arbitrary model text or tool calls as executable authority."""

    usage = _usage(response)
    external_id = response.get("id")
    if (
        not isinstance(external_id, str)
        or len(external_id) > 100
        or not external_id.replace("_", "").replace("-", "").isalnum()
    ):
        external_id = None

    def result(
        outcome: ResponseOutcome, output: StrictDTO | None = None
    ) -> ParsedResponse:
        return ParsedResponse(
            outcome,
            output,
            sha256(canonical_json(output.model_dump(mode="json"))) if output else None,
            usage,
            external_id,
        )

    status = response.get("status")
    if status == "incomplete":
        return result("INCOMPLETE")
    if status == "failed":
        return result("FAILED")
    if status == "cancelled":
        return result("CANCELLED")
    if status != "completed":
        return result("UNCERTAIN")
    items = response.get("output")
    if not isinstance(items, list) or not items:
        return result("SCHEMA_MISMATCH")
    texts: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("type") == "reasoning":
            continue
        if not isinstance(item, dict) or item.get("type") != "message":
            return result("SCHEMA_MISMATCH")
        parts = item.get("content")
        if not isinstance(parts, list):
            return result("SCHEMA_MISMATCH")
        for part in parts:
            if not isinstance(part, dict):
                return result("SCHEMA_MISMATCH")
            if part.get("type") == "refusal":
                return result("REFUSED")
            if part.get("type") != "output_text" or not isinstance(
                part.get("text"), str
            ):
                return result("SCHEMA_MISMATCH")
            texts.append(part["text"])
    if len(texts) != 1:
        return result("SCHEMA_MISMATCH")
    try:
        output = profile.output_model.model_validate_json(texts[0], strict=True)
        Draft202012Validator(json.loads(profile.schema_json)).validate(
            output.model_dump(mode="json", exclude={"schema_version"})
        )
    except (ValidationError, JSONSchemaValidationError):
        return result("SCHEMA_MISMATCH")
    return result("SUCCEEDED", output)
