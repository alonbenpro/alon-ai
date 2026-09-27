"""Typed immutable outreach-context and draft persistence commands."""

from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from alon_ai.integrations.schemas.provider import StrictDTO
from alon_ai.services.schemas.records import ArtifactDraft, ArtifactInput

RecipientMode = Literal["NAMED_PERSON", "ROLE_INBOX", "GENERAL_BUSINESS_INBOX"]
CoverageDisposition = Literal[
    "USED",
    "NOT_USED",
    "REJECTED_SENSITIVE",
    "REJECTED_INTRUSIVE",
    "REJECTED_IRRELEVANT",
    "REJECTED_UNSUPPORTED",
]


class EvidenceCoverageInput(StrictDTO):
    evidence_id: UUID
    disposition: CoverageDisposition
    reason_code: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")

    @model_validator(mode="after")
    def reason_matches_disposition(self) -> Self:
        if (self.disposition == "USED") == (self.reason_code is not None):
            raise ValueError("unused or rejected evidence requires one reason code")
        return self


class FreezeOutreachContextRequest(StrictDTO):
    cohort_id: UUID
    decision_id: UUID
    artifact: ArtifactDraft
    prompt_configuration: ArtifactInput
    model_config_id: UUID
    recipient_label_evidence_id: UUID | None = None
    coverage: tuple[EvidenceCoverageInput, ...] = Field(min_length=1, max_length=200)
    frozen_by: UUID

    @model_validator(mode="after")
    def exact_context_shape(self) -> Self:
        if len({item.evidence_id for item in self.coverage}) != len(self.coverage):
            raise ValueError("coverage evidence must be unique")
        mode = self.artifact.payload["recipient_mode"]
        if (mode == "GENERAL_BUSINESS_INBOX") != (
            self.recipient_label_evidence_id is None
        ):
            raise ValueError("named and role recipients require label evidence")
        return self


class AngleCandidateInput(StrictDTO):
    id: UUID
    rank: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1, max_length=20)


class SubjectCandidateInput(StrictDTO):
    id: UUID
    rank: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=998)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1, max_length=20)


class SequenceStepInput(StrictDTO):
    ordinal: int = Field(ge=1)
    delay_days: int = Field(ge=0)
    objective: str = Field(min_length=1, max_length=1000)


class ClaimInput(StrictDTO):
    artifact_id: UUID
    ordinal: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)
    kind: Literal["FACTUAL", "COMMERCIAL"]
    evidence_ids: tuple[UUID, ...] = Field(max_length=20)
    offer_field_paths: tuple[str, ...] = Field(max_length=20)

    @model_validator(mode="after")
    def complete_lineage(self) -> Self:
        if self.kind == "FACTUAL" and not self.evidence_ids:
            raise ValueError("factual claim requires evidence")
        if self.kind == "COMMERCIAL" and not self.offer_field_paths:
            raise ValueError("commercial claim requires offer field lineage")
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or len(
            set(self.offer_field_paths)
        ) != len(self.offer_field_paths):
            raise ValueError("claim lineage must be unique")
        return self


class DraftGraphRequest(StrictDTO):
    context_id: UUID
    angles: tuple[AngleCandidateInput, ...] = Field(min_length=1, max_length=20)
    narrative: ArtifactDraft
    strategy: ArtifactDraft
    subjects: tuple[SubjectCandidateInput, ...] = Field(min_length=1, max_length=20)
    sequence: ArtifactDraft
    sequence_steps: tuple[SequenceStepInput, ...] = Field(min_length=1, max_length=1000)
    draft: ArtifactDraft
    primary_angle_id: UUID | None = None
    supporting_angle_id: UUID | None = None
    subject_id: UUID
    cta: str | None = Field(default=None, min_length=1, max_length=1000)
    claims: tuple[ClaimInput, ...] = Field(min_length=1, max_length=500)
    validator: str = Field(pattern=r"^[A-Z][A-Z0-9_.-]{0,99}$")
    validator_version: int = Field(ge=1)
    recorded_by: UUID

    @model_validator(mode="after")
    def unique_ranked_inputs(self) -> Self:
        if len({item.id for item in self.angles}) != len(self.angles) or len(
            {item.rank for item in self.angles}
        ) != len(self.angles):
            raise ValueError("angle identities and ranks must be unique")
        if len({item.id for item in self.subjects}) != len(self.subjects) or len(
            {item.rank for item in self.subjects}
        ) != len(self.subjects):
            raise ValueError("subject identities and ranks must be unique")
        if tuple(item.ordinal for item in self.sequence_steps) != tuple(
            range(1, len(self.sequence_steps) + 1)
        ):
            raise ValueError("sequence steps must be uniquely ordered and contiguous")
        artifact_ids = {
            self.narrative.id,
            self.strategy.id,
            self.sequence.id,
            self.draft.id,
        }
        if any(item.artifact_id not in artifact_ids for item in self.claims):
            raise ValueError("claim references an unrelated artifact")
        return self


class OutreachContextReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID
    id: UUID
    artifact_id: UUID
    content_hash: str


class DraftValidationReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID
    draft_id: UUID
    validation_id: UUID
    disposition: Literal["PASS", "FAIL"]
    reason_codes: tuple[str, ...]
