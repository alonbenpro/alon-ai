"""Validate a bounded M0 ExperimentBrief without performing external actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    ValidationError,
    model_validator,
)
from pydantic.functional_validators import AfterValidator


def _nonblank(value: str) -> str:
    if not value.strip() or value != value.strip():
        raise ValueError("must be nonblank and have no surrounding whitespace")
    return value


def _require_true(value: object) -> object:
    if type(value) is not bool or value is not True:
        raise ValueError("must be the boolean true")
    return value


def _require_false(value: object) -> object:
    if type(value) is not bool or value is not False:
        raise ValueError("must be the boolean false")
    return value


def _require_int(value: object) -> object:
    if type(value) is not int:
        raise ValueError("must be an integer")
    return value


NonBlankString = Annotated[
    str,
    StringConstraints(strict=True, min_length=1),
    AfterValidator(_nonblank),
]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Timestamp = Annotated[AwareDatetime, Field(strict=False)]
StrictTrue = Annotated[Literal[True], BeforeValidator(_require_true)]
StrictFalse = Annotated[Literal[False], BeforeValidator(_require_false)]
ExactTwo = Annotated[Literal[2], BeforeValidator(_require_int)]
ExactFour = Annotated[Literal[4], BeforeValidator(_require_int)]
ExactThreeHundred = Annotated[Literal[300], BeforeValidator(_require_int)]


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False,
    )


class Hypothesis(StrictFrozenModel):
    operator: NonBlankString
    customer: NonBlankString
    problem: NonBlankString
    deliverable: NonBlankString


class EvidenceReference(StrictFrozenModel):
    reference_id: NonBlankString
    source: NonBlankString


class Baseline(StrictFrozenModel):
    kind: Literal["ZERO_HISTORY", "EVIDENCED"]
    method: NonBlankString
    references: tuple[EvidenceReference, ...]

    @model_validator(mode="after")
    def references_match_kind(self) -> Self:
        if self.kind == "ZERO_HISTORY" and self.references:
            raise ValueError("zero-history baseline cannot contain evidence references")
        if self.kind == "EVIDENCED" and not self.references:
            raise ValueError("evidenced baseline requires at least one reference")
        return self


class BudgetCaps(StrictFrozenModel):
    currency: Literal["ILS"]
    total_agorot: NonNegativeInt
    model_agorot: NonNegativeInt
    discovery_agorot: NonNegativeInt
    operator_time_total_minutes: NonNegativeInt
    operator_time_weekly_minutes: NonNegativeInt

    @model_validator(mode="after")
    def subcaps_fit_total(self) -> Self:
        if self.model_agorot + self.discovery_agorot > self.total_agorot:
            raise ValueError("model and discovery subcaps exceed the total cap")
        if self.operator_time_weekly_minutes > self.operator_time_total_minutes:
            raise ValueError("weekly operator-time cap exceeds the total cap")
        return self


class WorkflowCaps(StrictFrozenModel):
    research_businesses: NonNegativeInt
    qualification_businesses: NonNegativeInt
    contact_recipients: NonNegativeInt
    concurrent_conversations: NonNegativeInt

    @model_validator(mode="after")
    def caps_form_a_bounded_funnel(self) -> Self:
        if self.qualification_businesses > self.research_businesses:
            raise ValueError("qualification cap exceeds research cap")
        if self.contact_recipients > self.qualification_businesses:
            raise ValueError("contact cap exceeds qualification cap")
        if self.concurrent_conversations > self.contact_recipients:
            raise ValueError("concurrency cap exceeds contact cap")
        if self.contact_recipients > 300:
            raise ValueError("contact cap exceeds the pre-revenue ceiling")
        return self


class SourcePolicy(StrictFrozenModel):
    policy_version: NonBlankString
    automated_discovery_source: Literal["BRAVE_PLACE_SEARCH"]
    manual_evidence_sources: tuple[
        Literal["SOCIAL_PROFILE"], Literal["PUBLIC_BUSINESS_PAGE"]
    ]
    manual_review_required: StrictTrue
    provenance_required: StrictTrue
    source_url_or_capture_required: StrictTrue
    reviewer_and_time_required: StrictTrue
    permitted_fields_required: StrictTrue
    retention_policy_required: StrictTrue
    redaction_policy_required: StrictTrue
    cannot_expand_provider_capability: StrictTrue
    unverified_contact_identity_forbidden: StrictTrue


class ModelRoutingPolicy(StrictFrozenModel):
    policy_version: NonBlankString
    tiers: tuple[
        Literal["NO_AI"],
        Literal["NANO"],
        Literal["MINI"],
        Literal["PREMIUM"],
    ]
    deterministic_application_routing: StrictTrue
    agent_may_choose_tier: StrictFalse
    premium_default_denied: StrictTrue
    premium_requires_explicit_operator_approval: StrictTrue
    premium_approval_requirements: tuple[
        Literal["EXACT_TASK_AND_RUN"],
        Literal["MODEL_AND_CONFIG"],
        Literal["MAXIMUM_SPEND_AGOROT"],
        Literal["EXPIRY"],
        Literal["REASON"],
    ]
    batch_non_urgent_research: StrictTrue


class EvidencePolicy(StrictFrozenModel):
    policy_version: NonBlankString
    source_references_required: StrictTrue
    model_call_records_required: StrictTrue
    manual_evidence_records_required: StrictTrue
    infrastructure_evidence_required: StrictTrue


class InfrastructurePolicy(StrictFrozenModel):
    vps_vcpu: ExactTwo
    vps_memory_gb: ExactFour
    encrypted_local_storage: StrictTrue
    backup_destination: Literal["CLOUDFLARE_R2"]
    encrypt_backup_before_upload: StrictTrue
    private_ingress: Literal["CLOUDFLARE_TUNNEL_AND_ACCESS"]
    direct_public_service_exposure: StrictFalse


class LaunchStage(StrictFrozenModel):
    name: Literal["SHADOW", "REVIEW_20", "QUALIFIED_50", "SCALE_100_TO_300"]
    min_real_businesses: NonNegativeInt
    max_real_businesses: NonNegativeInt
    manual_review_required: StrictBool
    real_demand_learning: StrictBool
    explicit_operator_authorization: StrictBool


EXPECTED_LAUNCH_STAGES = (
    {
        "name": "SHADOW",
        "min_real_businesses": 0,
        "max_real_businesses": 0,
        "manual_review_required": False,
        "real_demand_learning": False,
        "explicit_operator_authorization": False,
    },
    {
        "name": "REVIEW_20",
        "min_real_businesses": 0,
        "max_real_businesses": 20,
        "manual_review_required": True,
        "real_demand_learning": True,
        "explicit_operator_authorization": False,
    },
    {
        "name": "QUALIFIED_50",
        "min_real_businesses": 0,
        "max_real_businesses": 50,
        "manual_review_required": False,
        "real_demand_learning": True,
        "explicit_operator_authorization": False,
    },
    {
        "name": "SCALE_100_TO_300",
        "min_real_businesses": 100,
        "max_real_businesses": 300,
        "manual_review_required": False,
        "real_demand_learning": True,
        "explicit_operator_authorization": True,
    },
)


class LaunchPolicy(StrictFrozenModel):
    pre_revenue_recipient_ceiling: ExactThreeHundred
    stages: tuple[LaunchStage, LaunchStage, LaunchStage, LaunchStage]

    @model_validator(mode="after")
    def uses_exact_cost_first_program(self) -> Self:
        actual = tuple(stage.model_dump(mode="json") for stage in self.stages)
        if actual != EXPECTED_LAUNCH_STAGES:
            raise ValueError("launch stages differ from the cost-first program")
        return self


class ConversationBookingLimits(StrictFrozenModel):
    messages_per_conversation: NonNegativeInt
    follow_ups_per_conversation: NonNegativeInt
    bookings_total: NonNegativeInt
    timezone_aware_slot_confirmation_required: StrictTrue

    @model_validator(mode="after")
    def follow_ups_fit_message_cap(self) -> Self:
        if self.follow_ups_per_conversation > self.messages_per_conversation:
            raise ValueError("follow-up cap exceeds message cap")
        return self


class BaselineStrategy(StrictFrozenModel):
    strategy_version: NonBlankString
    description: NonBlankString
    evidence_channel: NonBlankString


class MetricRule(StrictFrozenModel):
    code: NonBlankString
    metric: NonBlankString
    comparator: Literal[
        "LESS_THAN",
        "LESS_THAN_OR_EQUAL",
        "EQUAL",
        "GREATER_THAN_OR_EQUAL",
        "GREATER_THAN",
    ]
    threshold: FiniteNumber
    evidence_required: NonBlankString


class DecisionRule(StrictFrozenModel):
    decision: Literal["CONTINUE", "REVISE", "KILL", "INCONCLUSIVE", "SAFETY_STOP"]
    condition: NonBlankString


class Evaluation(StrictFrozenModel):
    success_rules: Annotated[tuple[MetricRule, ...], Field(min_length=1)]
    economic_rules: Annotated[tuple[MetricRule, ...], Field(min_length=1)]
    kill_rules: Annotated[tuple[MetricRule, ...], Field(min_length=1)]
    decision_rules: Annotated[tuple[DecisionRule, ...], Field(min_length=1)]
    evidence_based_decision_condition: NonBlankString


class OperatorSignature(StrictFrozenModel):
    status: Literal["PENDING", "PROVIDED_UNVERIFIED"]
    signatory: NonBlankString | None
    signed_at: Timestamp | None
    evidence_reference: NonBlankString | None
    verification: Literal["EXTERNAL_REQUIRED"]

    @model_validator(mode="after")
    def fields_match_status(self) -> Self:
        evidence_fields = (self.signatory, self.signed_at, self.evidence_reference)
        if self.status == "PENDING" and any(
            value is not None for value in evidence_fields
        ):
            raise ValueError("pending signature cannot contain signature evidence")
        if self.status == "PROVIDED_UNVERIFIED" and any(
            value is None for value in evidence_fields
        ):
            raise ValueError("provided signature record is incomplete")
        return self


class ExperimentBrief(StrictFrozenModel):
    schema_version: Literal["experiment_brief.v1"]
    revision: PositiveInt
    experiment_code: NonBlankString
    hypothesis: Hypothesis
    idea_origin: Literal["DISCOVERED", "USER_SUPPLIED"]
    jurisdictions: Annotated[tuple[NonBlankString, ...], Field(min_length=1)]
    baseline: Baseline
    budget_caps: BudgetCaps
    workflow_caps: WorkflowCaps
    source_policy: SourcePolicy
    model_routing_policy: ModelRoutingPolicy
    evidence_policy: EvidencePolicy
    infrastructure_policy: InfrastructurePolicy
    launch_policy: LaunchPolicy
    conversation_booking_limits: ConversationBookingLimits
    baseline_strategy: BaselineStrategy
    evaluation: Evaluation
    operator_signature: OperatorSignature

    @model_validator(mode="after")
    def jurisdictions_are_unique(self) -> Self:
        if len(set(self.jurisdictions)) != len(self.jurisdictions):
            raise ValueError("jurisdictions must be unique")
        return self

    @property
    def signature_record_present(self) -> bool:
        """Report presence only; authenticity always requires external verification."""
        return self.operator_signature.status == "PROVIDED_UNVERIFIED"


def canonical_brief_bytes(brief: ExperimentBrief) -> bytes:
    """Return deterministic UTF-8 JSON for review and hashing."""
    payload = brief.model_dump(mode="json")
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_brief_digest(brief: ExperimentBrief) -> str:
    return hashlib.sha256(canonical_brief_bytes(brief)).hexdigest()


class _InvalidJson(Exception):
    pass


def _reject_nonfinite(_: str) -> None:
    raise _InvalidJson


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJson
        result[key] = value
    return result


def _load_json(path: Path) -> object:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_nonfinite,
    )


def _location(parts: tuple[object, ...]) -> str:
    if not parts:
        return "$"
    return ".".join(str(part) for part in parts)


def _redacted_validation_errors(error: ValidationError) -> list[dict[str, str]]:
    return [
        {"location": _location(item["loc"]), "type": item["type"]}
        for item in error.errors(include_input=False, include_url=False)
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", nargs="?", type=Path, help="ExperimentBrief JSON file")
    parser.add_argument(
        "--schema", action="store_true", help="print the JSON Schema and exit"
    )
    arguments = parser.parse_args(argv)
    if arguments.schema and arguments.brief is not None:
        parser.error("brief path cannot be used with --schema")
    if not arguments.schema and arguments.brief is None:
        parser.error("brief path is required unless --schema is used")
    return arguments


def main(argv: list[str] | None = None) -> int:
    arguments = parse_args(argv)
    if arguments.schema:
        print(json.dumps(ExperimentBrief.model_json_schema(), indent=2, sort_keys=True))
        return 0

    try:
        document = _load_json(arguments.brief)
        brief = ExperimentBrief.model_validate(document)
    except (json.JSONDecodeError, UnicodeError, OSError, _InvalidJson):
        error_type = (
            "file_error" if isinstance(sys.exception(), OSError) else "invalid_json"
        )
        print(
            json.dumps(
                {
                    "errors": [{"location": "$", "type": error_type}],
                    "structural_valid": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    except ValidationError as error:
        print(
            json.dumps(
                {
                    "errors": _redacted_validation_errors(error),
                    "structural_valid": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "canonical_sha256": canonical_brief_digest(brief),
                "operator_signature_verification": "external_required",
                "signature_record_present": brief.signature_record_present,
                "structural_valid": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
