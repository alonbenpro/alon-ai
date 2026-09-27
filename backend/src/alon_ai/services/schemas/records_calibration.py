"""Immutable aggregate offer-fit calibration and requalification contracts."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from alon_ai.integrations.schemas.provider import StrictDTO
from alon_ai.services.schemas.records import CommandReceipt

CalibrationOutcome = Literal["ACCEPT", "REJECT", "INSUFFICIENT_EVIDENCE"]


class CalibrationProposalRequest(StrictDTO):
    """A repeated, evidence-backed mismatch across otherwise-ready candidates."""

    base_offer_acceptance_id: UUID
    decision_ids: tuple[UUID, ...] = Field(min_length=2, max_length=50)
    mismatch_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    proposed_change_codes: tuple[str, ...] = Field(min_length=1, max_length=32)
    proposed_by: UUID

    @model_validator(mode="after")
    def distinct_inputs(self):
        if len(set(self.decision_ids)) != len(self.decision_ids):
            raise ValueError("calibration decisions must be distinct")
        if len(set(self.proposed_change_codes)) != len(
            self.proposed_change_codes
        ) or any(not item or len(item) > 64 for item in self.proposed_change_codes):
            raise ValueError(
                "calibration change codes must be unique stable identifiers"
            )
        return self


class CalibrationDecisionRequest(StrictDTO):
    proposal_id: UUID
    outcome: CalibrationOutcome
    rule_version: Literal["qualification-calibration-v1"] = (
        "qualification-calibration-v1"
    )
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    decided_by: UUID


class CalibrationFulfillmentRequest(StrictDTO):
    calibration_decision_id: UUID
    offer_acceptance_id: UUID
    fulfilled_by: UUID


class CalibrationProposalReceipt(CommandReceipt):
    id: UUID
    evidence_hash: str


class CalibrationDecisionReceipt(CommandReceipt):
    id: UUID
    outcome: CalibrationOutcome
    reason_code: str


class CalibrationFulfillmentReceipt(CommandReceipt):
    id: UUID
    requalification_count: int
