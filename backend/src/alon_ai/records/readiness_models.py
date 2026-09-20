"""Strict inputs and receipts for immutable lead-readiness records."""

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from alon_ai.providers.contracts import StrictDTO
from alon_ai.records.models import ArtifactInput


class ProviderResultRequest(StrictDTO):
    candidate_id: UUID | None = None
    batch_id: UUID
    call_id: UUID
    result_evidence_id: UUID
    retained_id: UUID | None = None
    observed_at: AwareDatetime
    valid_until: AwareDatetime
    recorded_by: UUID

    @model_validator(mode="after")
    def chronological(self):
        if self.observed_at >= self.valid_until:
            raise ValueError("provider result must have a positive validity window")
        return self


class ContactabilityDecisionRequest(StrictDTO):
    candidate_id: UUID
    recipient_source_id: UUID | None = None
    provider_result_id: UUID | None = None
    outcome: Literal["SUPPORTED_CONTACT_ADDRESS", "EMAIL_NOT_FOUND"]
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    decided_by: UUID
    valid_until: AwareDatetime


class ResearchPlanRequest(StrictDTO):
    candidate_id: UUID
    recipient_source_id: UUID
    offer_acceptance_id: UUID
    artifact: ArtifactInput
    created_by: UUID


class DiscoveryPlanRequest(StrictDTO):
    batch_id: UUID
    offer_acceptance_id: UUID
    accepted_idea: ArtifactInput
    market_research: ArtifactInput
    mode: Literal["LOCAL_BUSINESS", "ONLINE_COMPANY", "HYBRID"]
    geography_filter_ids: tuple[UUID, ...] = Field(max_length=50)
    created_by: UUID

    @model_validator(mode="after")
    def local_geography_is_explicit(self):
        if self.mode in {"LOCAL_BUSINESS", "HYBRID"} and not self.geography_filter_ids:
            raise ValueError("local and hybrid discovery require explicit geography")
        if len(set(self.geography_filter_ids)) != len(self.geography_filter_ids):
            raise ValueError("discovery geography filters must be unique")
        return self


class ResearchRunRequest(StrictDTO):
    plan_id: UUID
    provider_result_id: UUID | None = None
    independent_source_id: UUID | None = None
    completed_by: UUID

    @model_validator(mode="after")
    def exactly_one_provenance(self):
        if (self.provider_result_id is None) == (self.independent_source_id is None):
            raise ValueError("research run needs exactly one provenance root")
        return self


class ResearchEvidenceLinkRequest(StrictDTO):
    run_id: UUID
    dossier_id: UUID
    dossier_evidence_id: UUID
    linked_by: UUID


class ReadinessReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID


class ContactabilityReceipt(ReadinessReceipt):
    outcome: Literal["SUPPORTED_CONTACT_ADDRESS", "EMAIL_NOT_FOUND"]
    version: int = Field(ge=1)
