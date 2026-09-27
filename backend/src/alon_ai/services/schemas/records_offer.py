"""Strict contracts for accepted offer design records."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from alon_ai.integrations.schemas.provider import StrictDTO
from alon_ai.services.schemas.records import (
    ArtifactInput,
    ArtifactKind,
    CommandReceipt,
    CycleReceipt,
    ResearchCycleBudgetInput,
)

REQUIRED_RESEARCH_ROLES = (
    "CUSTOMER_EVIDENCE",
    "BUYER_EVIDENCE",
    "PROBLEM_EVIDENCE",
    "ALTERNATIVES",
    "OBJECTIONS",
    "DIFFERENTIATION",
    "REACHABILITY",
    "FEASIBILITY",
    "INTEGRATION",
    "TRUST_COMPLIANCE",
    "CONTRADICTIONS_UNCERTAINTIES",
    "COMPETITOR_PROFILE",
    "SERVICE_PROFILE",
    "PRICE_OBSERVATION",
    "SCOPE_ESTIMATE",
)

PROTECTED_OFFER_FIELDS = (
    "target_customer",
    "buyer",
    "problem",
    "solution_mechanism",
    "credible_outcome",
    "positioning",
    "scope",
    "deliverables",
    "exclusions",
    "prerequisites",
    "timeline",
    "customer_responsibilities",
    "currency",
    "base_price",
    "pilot_terms",
    "third_party_costs",
    "payment_terms",
    "validity",
    "claims",
    "ideal_fit",
    "disqualifiers",
    "negotiation_variables",
)

REQUIRED_QUALIFICATION_CATEGORIES = (
    "REQUIRED_FIT",
    "POSITIVE_SIGNAL",
    "FATAL_DISQUALIFIER",
    "EVIDENCE_QUESTION",
    "TECHNICAL_FIT",
    "ECONOMIC_FIT",
    "BUYER_FIT",
    "CONTACT_FIT",
    "PILOT_FIT",
    "OFFER_SPECIFIC_ASSESSMENT",
)

INITIAL_OUTREACH_POLICY = {
    "pricing": "OMIT",
    "formal_proposal": "FORBIDDEN",
    "detailed_scope": "OMIT",
    "budget_question": "FORBIDDEN",
    "primary_goal": "START_RELEVANT_CONVERSATION",
    "max_sequence_steps": 3,
}

OFFER_FIELD_EVIDENCE_ROLES = {
    "target_customer": ("CUSTOMER_EVIDENCE",),
    "buyer": ("BUYER_EVIDENCE",),
    "problem": ("PROBLEM_EVIDENCE",),
    "solution_mechanism": ("FEASIBILITY", "INTEGRATION"),
    "credible_outcome": ("PROBLEM_EVIDENCE", "DIFFERENTIATION"),
    "positioning": ("COMPETITOR_PROFILE", "DIFFERENTIATION"),
    "scope": ("SCOPE_ESTIMATE", "FEASIBILITY"),
    "deliverables": ("SCOPE_ESTIMATE", "FEASIBILITY"),
    "exclusions": ("FEASIBILITY", "INTEGRATION"),
    "prerequisites": ("INTEGRATION", "TRUST_COMPLIANCE"),
    "timeline": ("SCOPE_ESTIMATE",),
    "customer_responsibilities": ("INTEGRATION",),
    "pilot_terms": ("PRICE_OBSERVATION", "FEASIBILITY"),
    "third_party_costs": ("PRICE_OBSERVATION", "INTEGRATION"),
    "validity": ("PRICE_OBSERVATION",),
    "claims": ("CUSTOMER_EVIDENCE", "PROBLEM_EVIDENCE", "RESEARCH_EVIDENCE"),
    "ideal_fit": ("CUSTOMER_EVIDENCE", "BUYER_EVIDENCE"),
    "disqualifiers": ("OBJECTIONS", "TRUST_COMPLIANCE"),
    "negotiation_variables": ("OBJECTIONS", "PRICE_OBSERVATION"),
}

OPERATOR_FIELD_CONSTRAINTS = {
    "currency": "CURRENCY",
    "base_price": "MINIMUM_PRICE",
    "payment_terms": "MINIMUM_DEPOSIT_RATE",
}


class CommercialEnvelopeRequest(StrictDTO):
    artifact: ArtifactInput
    bundle_id: UUID
    scope_estimate: ArtifactInput


class OfferFieldSource(StrictDTO):
    field_path: str = Field(min_length=1, max_length=64)
    source: ArtifactInput | None = None
    operator_constraint: (
        Literal[
            "CURRENCY",
            "DELIVERY_CAPACITY",
            "HOURLY_COST",
            "MINIMUM_PRICE",
            "MINIMUM_MARGIN_RATE",
            "MAXIMUM_DISCOUNT_RATE",
            "MINIMUM_DEPOSIT_RATE",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> Self:
        if (self.source is None) == (self.operator_constraint is None):
            raise ValueError("field source must be evidence or an operator constraint")
        return self


class QualificationCriterion(StrictDTO):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,31}$")
    category: Literal[
        "REQUIRED_FIT",
        "POSITIVE_SIGNAL",
        "FATAL_DISQUALIFIER",
        "EVIDENCE_QUESTION",
        "TECHNICAL_FIT",
        "ECONOMIC_FIT",
        "BUYER_FIT",
        "CONTACT_FIT",
        "PILOT_FIT",
        "OFFER_SPECIFIC_ASSESSMENT",
    ]
    requirement: str = Field(min_length=1, max_length=1000)
    question: str = Field(min_length=1, max_length=1000)
    rule_kind: Literal["HARD_GATE", "SOFT_SIGNAL", "FATAL_DISQUALIFIER"]
    comparison: Literal["PRESENT", "BOOLEAN_TRUE", "GTE", "LTE", "EQUALS", "ASSESSMENT"]
    threshold: str | None = Field(default=None, max_length=200)
    required_evidence_kind: Literal[
        "RESEARCH_EVIDENCE",
        "PRICE_OBSERVATION",
        "DELIVERY_SCOPE_ESTIMATE",
        "OPERATOR_CONSTRAINT",
    ]
    unknown_behavior: Literal["BLOCK", "NOT_APPLICABLE"]

    @model_validator(mode="after")
    def deterministic_rule(self) -> Self:
        needs_threshold = self.comparison in {"GTE", "LTE", "EQUALS"}
        if needs_threshold != (
            self.threshold is not None and bool(self.threshold.strip())
        ):
            raise ValueError("qualification comparison has invalid threshold")
        if self.rule_kind != "SOFT_SIGNAL" and self.unknown_behavior != "BLOCK":
            raise ValueError("mandatory qualification unknowns must block")
        if (self.category == "FATAL_DISQUALIFIER") != (
            self.rule_kind == "FATAL_DISQUALIFIER"
        ):
            raise ValueError("fatal qualification category and rule must match")
        return self


class OfferAcceptanceRequest(StrictDTO):
    calibration_decision_id: UUID | None = None
    package: ArtifactInput
    proposal_id: UUID
    qualification_profile: ArtifactInput
    criteria: tuple[QualificationCriterion, ...]
    outreach_policy: ArtifactInput
    field_sources: tuple[OfferFieldSource, ...]
    accepted_by: UUID


class OfferGapRequest(StrictDTO):
    artifact: ArtifactInput
    proposal_id: UUID
    missing_fields: tuple[str, ...] = ()
    contradictory_fields: tuple[str, ...] = ()
    required_source_types: tuple[str, ...]
    targeted_questions: tuple[str, ...]

    @model_validator(mode="after")
    def material_gap(self) -> Self:
        if not self.missing_fields and not self.contradictory_fields:
            raise ValueError("offer gap must identify a missing or contradictory field")
        if not self.required_source_types or not self.targeted_questions:
            raise ValueError("offer gap needs sources and targeted questions")
        return self


class InputBundleReceipt(CommandReceipt):
    id: UUID
    artifact_id: UUID
    kind: Literal[ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE] = (
        ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE
    )
    version: int
    content_hash: str


class CommercialEnvelopeReceipt(CommandReceipt):
    id: UUID
    bundle_id: UUID
    status: Literal[
        "READY",
        "IMPOSSIBLE_ECONOMICS",
        "CURRENCY_MISMATCH",
        "DELIVERY_CAPACITY_EXCEEDED",
    ]
    currency: str
    delivery_cost: Decimal | None
    minimum_price: Decimal | None


class OfferProposalReceipt(CommandReceipt):
    id: UUID
    bundle_id: UUID


class OfferAcceptanceReceipt(CommandReceipt):
    id: UUID
    bundle_id: UUID
    offer_artifact_id: UUID
    minimum_price: Decimal


class OfferGapReceipt(CycleReceipt):
    pass


class OfferDesignStartRequest(StrictDTO):
    """Pinned inputs for beginning one durable Offer Design run."""

    verdict_id: UUID
    input_bundle: ArtifactInput
    envelope: ArtifactInput
    scope_estimate: ArtifactInput
    prompt_configuration: ArtifactInput
    model_config_id: UUID
    model_config_workflow_id: UUID
    model_config_version: UUID
    started_by: UUID


class OfferDesignStartReceipt(CommandReceipt):
    id: UUID
    cycle_id: UUID
    bundle_id: UUID
    envelope_id: UUID
    transition_id: UUID


class OfferDesignDecisionRequest(StrictDTO):
    run_id: UUID
    outcome: Literal[
        "ACCEPT",
        "TARGETED_RESEARCH_REQUIRED",
        "IDEA_REFINEMENT_RECOMMENDED",
        "WAITING_FOR_OPERATOR_INPUT",
    ]
    decision_artifact: ArtifactInput
    operator_id: UUID


class OfferDesignDecisionReceipt(CommandReceipt):
    id: UUID
    run_id: UUID
    outcome: str
    transition_id: UUID


class OfferTargetedResearchReturnRequest(StrictDTO):
    """Supplied, bounded continuation after an unaccepted Offer Design run."""

    run_id: UUID
    proposal_id: UUID
    decision_artifact: ArtifactInput
    gap: OfferGapRequest
    plan: ArtifactInput
    budget: ResearchCycleBudgetInput
    operator_id: UUID
    accepted_by: UUID


class OfferTargetedResearchReturnReceipt(CommandReceipt):
    id: UUID
    run_id: UUID
    decision_id: UUID
    child_cycle_id: UUID
    research_attempt_id: UUID
    parent_transition_id: UUID
    child_transition_id: UUID


class OfferIdeaRefinementReturnRequest(StrictDTO):
    """An operator's explicit, supplied next-IdeaBrief confirmation."""

    run_id: UUID
    decision_id: UUID
    commercial_failure_evidence: ArtifactInput
    proposed_idea: ArtifactInput
    accepted_by: UUID


class OfferIdeaRefinementReturnReceipt(CommandReceipt):
    id: UUID
    run_id: UUID
    decision_id: UUID
    child_cycle_id: UUID
    transition_id: UUID
