"""Strict L03 product-record commands and receipts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from alon_ai.providers.contracts import StrictDTO
from alon_ai.records.operator_models import OperatorProfileVersion


class ArtifactKind(StrEnum):
    EXPERIMENT_BRIEF = "EXPERIMENT_BRIEF"
    IDEA_SEED = "IDEA_SEED"
    IDEA_CANDIDATE = "IDEA_CANDIDATE"
    IDEA_BRIEF = "IDEA_BRIEF"
    RESEARCH_PLAN = "RESEARCH_PLAN"
    RESEARCH_EVIDENCE = "RESEARCH_EVIDENCE"
    COMPETITOR_PROFILE = "COMPETITOR_PROFILE"
    SERVICE_PROFILE = "SERVICE_PROFILE"
    PRICE_OBSERVATION = "PRICE_OBSERVATION"
    MARKET_RESEARCH_REPORT = "MARKET_RESEARCH_REPORT"
    MARKET_RESEARCH_RECOMMENDATION = "MARKET_RESEARCH_RECOMMENDATION"
    RESEARCH_FEEDBACK_BRIEF = "RESEARCH_FEEDBACK_BRIEF"
    OFFER_RESEARCH_GAP_BRIEF = "OFFER_RESEARCH_GAP_BRIEF"
    DELIVERY_SCOPE_ESTIMATE = "DELIVERY_SCOPE_ESTIMATE"
    OFFER_DESIGN_INPUT_BUNDLE = "OFFER_DESIGN_INPUT_BUNDLE"
    COMMERCIAL_DESIGN_ENVELOPE = "COMMERCIAL_DESIGN_ENVELOPE"
    OFFER_DESIGN_PROPOSAL = "OFFER_DESIGN_PROPOSAL"
    OFFER_PACKAGE = "OFFER_PACKAGE"
    OFFER_QUALIFICATION_PROFILE = "OFFER_QUALIFICATION_PROFILE"
    INITIAL_OUTREACH_POLICY = "INITIAL_OUTREACH_POLICY"
    VALIDATION_RESULT = "VALIDATION_RESULT"
    ACCEPTANCE_RECEIPT = "ACCEPTANCE_RECEIPT"


_PAYLOAD_FIELDS: dict[ArtifactKind, dict[str, type]] = {
    ArtifactKind.EXPERIMENT_BRIEF: {"objective": str},
    ArtifactKind.IDEA_SEED: {"origin": str, "statement": str},
    ArtifactKind.IDEA_CANDIDATE: {"title": str, "hypothesis": str},
    ArtifactKind.IDEA_BRIEF: {
        "title": str,
        "customer": str,
        "problem": str,
        "core_intent": str,
        "material_pivot": bool,
    },
    ArtifactKind.RESEARCH_PLAN: {"questions": list, "method": str},
    ArtifactKind.RESEARCH_EVIDENCE: {"claim": str, "finding": str},
    ArtifactKind.COMPETITOR_PROFILE: {"name": str, "positioning": str},
    ArtifactKind.SERVICE_PROFILE: {"name": str, "scope": str},
    ArtifactKind.PRICE_OBSERVATION: {
        "status": str,
        "currency": object,
        "amount": object,
        "unit": str,
        "source_note": str,
    },
    ArtifactKind.MARKET_RESEARCH_REPORT: {"finding": str, "limitations": list},
    ArtifactKind.MARKET_RESEARCH_RECOMMENDATION: {
        "recommendation": str,
        "rationale": str,
    },
    ArtifactKind.OFFER_RESEARCH_GAP_BRIEF: {
        "required_evidence": list,
        "justification": str,
    },
    ArtifactKind.DELIVERY_SCOPE_ESTIMATE: {"hours": str, "basis": str},
    ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE: {"status": str},
    ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE: {"status": str, "reason": str},
    ArtifactKind.OFFER_DESIGN_PROPOSAL: {
        "target_customer": str,
        "buyer": str,
        "problem": str,
        "solution_mechanism": str,
        "credible_outcome": str,
        "positioning": str,
        "scope": str,
        "deliverables": list,
        "exclusions": list,
        "prerequisites": list,
        "timeline": str,
        "customer_responsibilities": list,
        "currency": str,
        "base_price": str,
        "pilot_terms": str,
        "third_party_costs": str,
        "payment_terms": str,
        "validity": str,
        "claims": list,
        "ideal_fit": list,
        "disqualifiers": list,
        "negotiation_variables": list,
    },
    ArtifactKind.OFFER_PACKAGE: {
        "target_customer": str,
        "buyer": str,
        "problem": str,
        "solution_mechanism": str,
        "credible_outcome": str,
        "positioning": str,
        "scope": str,
        "deliverables": list,
        "exclusions": list,
        "prerequisites": list,
        "timeline": str,
        "customer_responsibilities": list,
        "currency": str,
        "base_price": str,
        "pilot_terms": str,
        "third_party_costs": str,
        "payment_terms": str,
        "validity": str,
        "claims": list,
        "ideal_fit": list,
        "disqualifiers": list,
        "negotiation_variables": list,
    },
    ArtifactKind.OFFER_QUALIFICATION_PROFILE: {"summary": str},
    ArtifactKind.INITIAL_OUTREACH_POLICY: {
        "pricing": str,
        "formal_proposal": str,
        "detailed_scope": str,
        "budget_question": str,
        "primary_goal": str,
    },
    ArtifactKind.RESEARCH_FEEDBACK_BRIEF: {"preserve": list, "change": list},
    ArtifactKind.VALIDATION_RESULT: {
        "validator": str,
        "disposition": str,
        "reason": str,
    },
    ArtifactKind.ACCEPTANCE_RECEIPT: {"disposition": str, "reason": str},
}


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 4000


def validate_payload(kind: ArtifactKind, payload: dict[str, Any]) -> dict[str, Any]:
    expected = _PAYLOAD_FIELDS[kind]
    if set(payload) != set(expected):
        raise ValueError("artifact payload fields do not match kind")
    for key, expected_type in expected.items():
        value = payload[key]
        if expected_type is int:
            if type(value) is not int or value < 0:
                raise ValueError("invalid artifact payload value")
        elif expected_type is bool:
            if type(value) is not bool:
                raise ValueError("invalid artifact payload value")
        elif expected_type is str:
            if not _nonempty(value):
                raise ValueError("invalid artifact payload value")
        elif expected_type is object:
            continue
        elif (
            not isinstance(value, list)
            or not value
            or not all(_nonempty(item) for item in value)
        ):
            raise ValueError("invalid artifact payload value")
    if kind is ArtifactKind.IDEA_SEED and payload["origin"] not in {
        "USER_SUPPLIED",
    }:
        raise ValueError("invalid idea origin")
    if kind is ArtifactKind.MARKET_RESEARCH_RECOMMENDATION and payload[
        "recommendation"
    ] not in {
        "PROCEED_TO_OFFER",
        "REFINE_SAME_IDEA",
        "MATERIAL_PIVOT_RECOMMENDED",
        "KILL_IDEA",
        "INCONCLUSIVE",
    }:
        raise ValueError("invalid research recommendation")
    if kind is ArtifactKind.VALIDATION_RESULT and payload["disposition"] not in {
        "PASS",
        "FAIL",
    }:
        raise ValueError("invalid validation disposition")
    if kind is ArtifactKind.ACCEPTANCE_RECEIPT and payload["disposition"] not in {
        "ACCEPTED",
        "REJECTED",
        "SUPERSEDED",
    }:
        raise ValueError("invalid acceptance disposition")
    if kind is ArtifactKind.PRICE_OBSERVATION:
        quoted = payload["status"] == "QUOTED"
        unavailable = payload["status"] == "REQUIRED_UNAVAILABLE"
        valid_quote = (
            isinstance(payload["currency"], str)
            and len(payload["currency"]) == 3
            and payload["currency"].isupper()
            and isinstance(payload["amount"], str)
            and bool(payload["amount"])
        )
        if valid_quote:
            try:
                amount = Decimal(payload["amount"])
                exponent = amount.as_tuple().exponent
                valid_quote = (
                    amount > 0
                    and amount < Decimal(1000000000000)
                    and isinstance(exponent, int)
                    and exponent >= -6
                )
            except InvalidOperation:
                valid_quote = False
        if not (quoted or unavailable) or quoted != valid_quote:
            raise ValueError("invalid quote evidence")
        if unavailable and (
            payload["currency"] is not None or payload["amount"] is not None
        ):
            raise ValueError("unavailable quote cannot invent a price")
    if kind is ArtifactKind.DELIVERY_SCOPE_ESTIMATE:
        try:
            hours = Decimal(payload["hours"])
        except InvalidOperation as error:
            raise ValueError("invalid delivery scope estimate") from error
        exponent = hours.as_tuple().exponent
        if (
            hours <= 0
            or hours > Decimal(100000)
            or not isinstance(exponent, int)
            or exponent < -2
        ):
            raise ValueError("invalid delivery scope estimate")
    if kind is ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE and payload["status"] != "FROZEN":
        raise ValueError("invalid offer input bundle")
    if kind is ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE and payload["status"] not in {
        "READY",
        "IMPOSSIBLE_ECONOMICS",
        "CURRENCY_MISMATCH",
        "DELIVERY_CAPACITY_EXCEEDED",
    }:
        raise ValueError("invalid commercial envelope")
    if kind in {ArtifactKind.OFFER_DESIGN_PROPOSAL, ArtifactKind.OFFER_PACKAGE}:
        try:
            price = Decimal(payload["base_price"])
        except InvalidOperation as error:
            raise ValueError("invalid offer price") from error
        currency = payload["currency"]
        exponent = price.as_tuple().exponent
        if (
            not isinstance(currency, str)
            or len(currency) != 3
            or not currency.isupper()
            or price <= 0
            or not isinstance(exponent, int)
            or exponent < -2
        ):
            raise ValueError("invalid offer economics")
    if kind is ArtifactKind.INITIAL_OUTREACH_POLICY and payload != {
        "pricing": "OMIT",
        "formal_proposal": "FORBIDDEN",
        "detailed_scope": "OMIT",
        "budget_question": "FORBIDDEN",
        "primary_goal": "START_RELEVANT_CONVERSATION",
    }:
        raise ValueError("invalid initial outreach policy")
    return payload


# Compatibility name; authorization belongs to the explicit operator registry.
OperatorCapabilityProfile = OperatorProfileVersion


class ProductExperiment(StrictDTO):
    id: UUID
    operator_profile_id: UUID
    operator_profile_version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    created_at: AwareDatetime


class ProductWorkflow(StrictDTO):
    id: UUID
    experiment_id: UUID
    role: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,99}$")
    created_at: AwareDatetime


class ProductAgent(StrictDTO):
    id: UUID
    workflow_id: UUID
    role: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,99}$")
    created_at: AwareDatetime


class ArtifactDraft(StrictDTO):
    id: UUID
    logical_id: UUID
    version: int = Field(ge=1)
    experiment_id: UUID
    workflow_id: UUID | None = None
    agent_id: UUID | None = None
    operation_id: UUID | None = None
    kind: ArtifactKind
    payload: dict[str, Any]
    created_by: UUID
    created_at: AwareDatetime

    @model_validator(mode="after")
    def valid_artifact(self) -> Self:
        validate_payload(self.kind, self.payload)
        if self.agent_id is not None and self.workflow_id is None:
            raise ValueError("agent artifact requires workflow")
        if self.operation_id is not None and self.workflow_id is None:
            raise ValueError("operation artifact requires workflow")
        return self


class ArtifactInput(StrictDTO):
    artifact_id: UUID
    kind: ArtifactKind
    version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")

    @classmethod
    def from_receipt(cls, receipt: ArtifactReceipt, *, role: str) -> ArtifactInput:
        return cls(
            artifact_id=receipt.artifact_id,
            kind=receipt.kind,
            version=receipt.version,
            content_hash=receipt.content_hash,
            role=role,
        )


class SourceReference(StrictDTO):
    kind: Literal["RETAINED_CONTENT", "GOVERNANCE_EVIDENCE"]
    evidence_id: UUID | None = None
    retained_id: UUID | None = None
    call_id: UUID | None = None
    grant_id: UUID | None = None
    grant_version: int | None = Field(default=None, ge=1)
    field: str | None = None
    expires_at: AwareDatetime | None = None

    @classmethod
    def governance_evidence(cls, evidence_id: UUID) -> SourceReference:
        return cls(kind="GOVERNANCE_EVIDENCE", evidence_id=evidence_id)

    @classmethod
    def retained_content(
        cls,
        *,
        retained_id: UUID,
        call_id: UUID,
        grant_id: UUID,
        grant_version: int,
        field: str,
        expires_at: datetime,
    ) -> SourceReference:
        return cls(
            kind="RETAINED_CONTENT",
            retained_id=retained_id,
            call_id=call_id,
            grant_id=grant_id,
            grant_version=grant_version,
            field=field,
            expires_at=expires_at,
        )

    @model_validator(mode="after")
    def exact_shape(self) -> Self:
        retained = (
            self.retained_id,
            self.call_id,
            self.grant_id,
            self.grant_version,
            self.field,
            self.expires_at,
        )
        if self.kind == "GOVERNANCE_EVIDENCE":
            if self.evidence_id is None or any(item is not None for item in retained):
                raise ValueError("invalid governance evidence reference")
        elif self.evidence_id is not None or any(item is None for item in retained):
            raise ValueError("invalid retained content reference")
        return self


class CommandReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID


class ArtifactReceipt(CommandReceipt):
    artifact_id: UUID
    kind: ArtifactKind
    version: int
    content_hash: str


class CycleReceipt(CommandReceipt):
    id: UUID
    experiment_id: UUID
    ordinal: int


class IdeaAcceptanceReceipt(CommandReceipt):
    id: UUID
    cycle_id: UUID
    artifact_id: UUID


class ResearchAttemptReceipt(CommandReceipt):
    id: UUID
    cycle_id: UUID
    ordinal: int


class VerdictReceipt(CommandReceipt):
    id: UUID
    cycle_id: UUID
    verdict: Literal[
        "PROCEED_TO_OFFER",
        "REFINE_SAME_IDEA",
        "MATERIAL_PIVOT_RECOMMENDED",
        "KILL_IDEA",
        "INCONCLUSIVE",
    ]


class PivotDecisionReceipt(CommandReceipt):
    id: UUID
    cycle_id: UUID


class ArtifactDispositionReceipt(CommandReceipt):
    id: UUID
    artifact_id: UUID
    disposition: Literal["VALIDATED", "ACCEPTED", "REJECTED", "SUPERSEDED"]


class ProductRecordsDenied(Exception):
    """A stable fail-closed error that never includes payload or SQL details."""

    def __init__(self, reason: str = "INVALID_STATE") -> None:
        self.reason = reason
        super().__init__(reason)
