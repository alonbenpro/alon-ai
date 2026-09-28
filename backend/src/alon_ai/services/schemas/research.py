"""Version-bound research observations; these DTOs grant no commercial authority."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from alon_ai.services.schemas.records import (
    ArtifactInput,
    ArtifactKind,
    SourceReference,
)

ResearchDimension = Literal[
    "CUSTOMER_PAIN",
    "BUYER",
    "DEMAND",
    "ALTERNATIVES",
    "COMPETITION",
    "PRICING",
    "REACHABILITY",
    "DELIVERY",
]
RESEARCH_DIMENSIONS: tuple[ResearchDimension, ...] = (
    "CUSTOMER_PAIN",
    "BUYER",
    "DEMAND",
    "ALTERNATIVES",
    "COMPETITION",
    "PRICING",
    "REACHABILITY",
    "DELIVERY",
)
EvidenceStatus = Literal["SUPPORTED", "CONTRADICTED", "INCONCLUSIVE", "UNAVAILABLE"]
ResearchText = Annotated[str, Field(min_length=1, max_length=4000, pattern=r"\S")]
ResearchNotes = Annotated[list[ResearchText], Field(max_length=30)]
StepKey = Annotated[str, Field(min_length=36, max_length=36)]


class ResearchDTO(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, hide_input_in_errors=True
    )


class SourceFindingPayload(ResearchDTO):
    """Original analytical observations only; quotations stay in licensed storage."""

    research_schema: Literal["SOURCE_FINDING_V1"] = "SOURCE_FINDING_V1"
    run_id: str
    step_key: StepKey
    dimension: ResearchDimension
    claim: ResearchText
    finding: ResearchText
    evidence_status: EvidenceStatus
    limitations: ResearchNotes

    @field_validator("run_id", "step_key")
    @classmethod
    def canonical_run_id(cls, value: str) -> str:
        if str(UUID(value)) != value:
            raise ValueError("canonical run id required")
        return value


class MarketResearchReportPayload(ResearchDTO):
    research_schema: Literal["MARKET_RESEARCH_CASE_V1"] = "MARKET_RESEARCH_CASE_V1"
    finding: ResearchText
    limitations: ResearchNotes
    unresolved_questions: ResearchNotes


class AppendSourceFindingRequest(ResearchDTO):
    run_id: UUID
    step_key: UUID
    subject: ArtifactInput
    dimension: ResearchDimension
    claim: ResearchText
    finding: ResearchText
    evidence_status: EvidenceStatus
    limitations: ResearchNotes = Field(default_factory=list)
    sources: tuple[SourceReference, ...] = Field(default=(), max_length=30)

    @field_validator("subject")
    @classmethod
    def research_subject(cls, value: ArtifactInput) -> ArtifactInput:
        if value.kind not in {
            ArtifactKind.IDEA_CANDIDATE,
            ArtifactKind.IDEA_SEED,
            ArtifactKind.IDEA_BRIEF,
        }:
            raise ValueError("exact candidate or idea input required")
        return value

    @model_validator(mode="after")
    def substantive_sources(self):
        if self.evidence_status in {"SUPPORTED", "CONTRADICTED"} and not any(
            source.kind == "RETAINED_CONTENT" for source in self.sources
        ):
            raise ValueError(
                "supported or contradicted analysis requires a retained source"
            )
        return self

    def payload(self) -> SourceFindingPayload:
        return SourceFindingPayload(
            run_id=str(self.run_id),
            step_key=str(self.step_key),
            dimension=self.dimension,
            claim=self.claim,
            finding=self.finding,
            evidence_status=self.evidence_status,
            limitations=self.limitations,
        )


class ResearchSourceView(ResearchDTO):
    reference: SourceReference
    availability: Literal["CURRENT_SOURCE", "REFERENCE_ONLY"] = "REFERENCE_ONLY"
    provider: Literal["FIRECRAWL"] | None = None
    url: str | None = Field(default=None, max_length=2048)
    title: str | None = Field(default=None, max_length=500)
    available_until: datetime | None = None

    @model_validator(mode="after")
    def licensed_source_shape(self):
        if self.availability == "CURRENT_SOURCE":
            from alon_ai.integrations.schemas.provider import public_url

            if (
                self.provider != "FIRECRAWL"
                or self.url is None
                or self.available_until is None
            ):
                raise ValueError("current source identity required")
            public_url(self.url)
            if not self.url.startswith("https://"):
                raise ValueError("public HTTPS source required")
        elif any(
            value is not None
            for value in (self.provider, self.url, self.title, self.available_until)
        ):
            raise ValueError("unavailable source must not disclose content")
        return self


class SourceFindingView(ResearchDTO):
    artifact: ArtifactInput
    subject: ArtifactInput
    observation: SourceFindingPayload
    sources: list[ResearchSourceView]
    created_at: datetime


CoverageStatus = Literal[
    "UNRESEARCHED", "SUPPORTED", "CONTRADICTED", "INCONCLUSIVE", "UNAVAILABLE", "MIXED"
]


class ResearchCoverage(ResearchDTO):
    dimension: ResearchDimension
    status: CoverageStatus
    finding_ids: list[UUID]


class SubjectResearchCase(ResearchDTO):
    subject: ArtifactInput
    mode: Literal["CANDIDATE", "SELECTED", "SUPPLIED", "REFINED"]
    current: bool
    findings: list[SourceFindingView]
    coverage: list[ResearchCoverage]
    gaps: list[ResearchDimension]


class MarketResearchCase(ResearchDTO):
    experiment_id: UUID
    subjects: list[SubjectResearchCase]
    finding_count: int
    progress: Literal["NOT_STARTED", "PARTIAL"]
    # A read projection never claims finished research from row counts alone.
    limitations: list[str]
