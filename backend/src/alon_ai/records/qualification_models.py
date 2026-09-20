"""Typed immutable inputs and receipts for lead qualification and cohorts."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from alon_ai.providers.contracts import StrictDTO

CriterionStatus = Literal[
    "SATISFIED", "PARTIAL", "NOT_SATISFIED", "UNKNOWN", "CONTRADICTED"
]
QualificationOutcome = Literal[
    "QUALIFIED_CONTACTABLE",
    "PILOT_FIT_CONTACTABLE",
    "REJECTED_NOT_A_FIT",
    "REJECTED_NO_RELEVANT_PROBLEM_SIGNAL",
    "REJECTED_ALREADY_ADEQUATELY_SOLVED",
    "REJECTED_TECHNICAL_MISMATCH",
    "REJECTED_ECONOMIC_MISMATCH",
    "REJECTED_BUYER_MISMATCH",
    "REJECTED_INSUFFICIENT_EVIDENCE",
    "BLOCKED_POLICY_OR_IDENTITY",
    "REVIEW_REQUIRED",
]


class LeadEvidenceInput(StrictDTO):
    id: UUID
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_\-]{0,63}$")
    kind: Literal["OBSERVED_FACT", "HYPOTHESIS", "CONTRADICTION", "UNKNOWN"]
    source_ref: str = Field(min_length=1, max_length=1000)
    excerpt: str = Field(min_length=1, max_length=4000)
    observed_at: AwareDatetime
    valid_until: AwareDatetime
    confidence: Decimal = Field(ge=0, le=1)

    @model_validator(mode="after")
    def chronological(self):
        if self.observed_at >= self.valid_until:
            raise ValueError("lead evidence must have a positive validity window")
        return self


class LeadDossierRequest(StrictDTO):
    candidate_id: UUID
    binding_id: UUID
    admission_id: UUID
    recipient_source_id: UUID
    offer_acceptance_id: UUID
    recorded_by: UUID
    evidence: tuple[LeadEvidenceInput, ...] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_evidence(self):
        if len({item.id for item in self.evidence}) != len(self.evidence) or len(
            {item.code for item in self.evidence}
        ) != len(self.evidence):
            raise ValueError("dossier evidence identifiers must be unique")
        return self


class CriterionResultInput(StrictDTO):
    criterion_code: str = Field(pattern=r"^[A-Z][A-Z0-9_\-]{0,31}$")
    status: CriterionStatus
    evidence_ids: tuple[UUID, ...] = Field(max_length=50)
    rationale: str = Field(min_length=1, max_length=2000)


class QualificationDecisionRequest(StrictDTO):
    dossier_id: UUID
    proposal_fact_id: UUID
    proposed_outcome: QualificationOutcome
    results: tuple[CriterionResultInput, ...] = Field(min_length=1, max_length=100)
    finding_codes: tuple[str, ...] = Field(min_length=1, max_length=50)
    decided_by: UUID
    valid_until: AwareDatetime

    @model_validator(mode="after")
    def unique_results_and_findings(self):
        if len({item.criterion_code for item in self.results}) != len(self.results):
            raise ValueError("criterion results must be unique")
        if len(set(self.finding_codes)) != len(self.finding_codes) or any(
            not item or len(item) > 64 for item in self.finding_codes
        ):
            raise ValueError("finding codes must be unique stable identifiers")
        return self


class FreezeCohortRequest(StrictDTO):
    offer_acceptance_id: UUID
    decision_ids: tuple[UUID, ...] = Field(min_length=50, max_length=50)
    frozen_by: UUID


class LeadDossierReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID
    id: UUID
    version: int
    evidence_ids: tuple[UUID, ...]


class QualificationDecisionReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID
    id: UUID
    matrix_id: UUID
    outcome: QualificationOutcome
    reason_code: str


class CohortReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID
    id: UUID
    member_count: int
