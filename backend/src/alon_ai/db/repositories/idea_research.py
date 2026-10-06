"""Exact persisted research subject selection and read-only research projections."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from alon_ai.db.repositories.accounting import GovernanceRepository
from alon_ai.db.repositories.experiments import ExperimentError, existing_experiment
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables import records
from alon_ai.db.tables.agent_runs import runs
from alon_ai.integrations.schemas.provider import Capability, ContentField, Provider
from alon_ai.provider_usage.schemas.accounting import AccountingDenied
from alon_ai.services.schemas.records import (
    ArtifactInput,
    ArtifactKind,
    SourceReference,
)
from alon_ai.services.schemas.research import (
    RESEARCH_DIMENSIONS,
    CoverageStatus,
    EvidenceStatus,
    MarketResearchCase,
    ResearchCoverage,
    ResearchSourceView,
    SourceFindingPayload,
    SourceFindingView,
    SubjectResearchCase,
)

SUBJECT_KINDS = ("IDEA_CANDIDATE", "IDEA_SEED", "IDEA_BRIEF")


def artifact_reference(row, role: str) -> ArtifactInput:
    return ArtifactInput(
        artifact_id=row["id"],
        kind=ArtifactKind(row["kind"]),
        version=row["version"],
        content_hash=row["content_hash"],
        role=role,
    )


class IdeaResearchRepository:
    def __init__(self, engine, *, clock=None):
        self.engine = engine
        self.clock = clock or (lambda: datetime.now(UTC))

    async def source_view(
        self, experiment_id: UUID, reference: SourceReference
    ) -> ResearchSourceView:
        """Project only licensed Firecrawl URL/title; no network or persistence."""
        fallback = ResearchSourceView(reference=reference)
        if reference.kind != "RETAINED_CONTENT":
            return fallback
        governance = GovernanceRepository(self.engine, clock=self.clock)
        async with self.engine.connect() as connection:
            retained = (
                (
                    await connection.execute(
                        select(gov.retained)
                        .join(gov.calls, gov.calls.c.id == gov.retained.c.call_id)
                        .where(
                            gov.calls.c.experiment_id == experiment_id,
                            gov.retained.c.call_id == reference.call_id,
                            gov.retained.c.grant_id == reference.grant_id,
                            gov.retained.c.grant_version == reference.grant_version,
                            gov.retained.c.expires_at > self.clock(),
                        )
                    )
                )
                .mappings()
                .all()
            )
        exact = next(
            (
                row
                for row in retained
                if row["id"] == reference.retained_id
                and row["field"] == reference.field
                and row["expires_at"] == reference.expires_at
            ),
            None,
        )
        if exact is None or reference.call_id is None:
            return fallback
        try:
            config = await governance.config_for_call(reference.call_id)
            if (
                config.intended_use.provider is not Provider.FIRECRAWL
                or config.intended_use.capability
                not in {
                    Capability.FIRECRAWL_PAGE_CAPTURE,
                    Capability.FIRECRAWL_PDF_CAPTURE,
                    Capability.FIRECRAWL_JS_RETRIEVAL,
                }
                or ContentField.URL not in config.intended_use.required_fields
            ):
                return fallback
            content = await governance.read_content(reference.call_id)
            if reference.field not in content:
                return fallback
            urls = content.get("URL", ())
            # Capture adapters produce exactly one source URL, unlike map/search results.
            url_row = next((row for row in retained if row["field"] == "URL"), None)
            if len(urls) != 1 or url_row is None:
                return fallback
            title = None
            title_row = next((row for row in retained if row["field"] == "TITLE"), None)
            if (
                ContentField.TITLE in config.intended_use.required_fields
                and title_row is not None
            ):
                titles = content.get("TITLE", ())
                if len(titles) == 1 and titles[0].strip():
                    title = titles[0]
            available_until = min(
                exact["expires_at"],
                url_row["expires_at"],
                title_row["expires_at"]
                if title is not None and title_row is not None
                else url_row["expires_at"],
            )
            if available_until <= self.clock():
                return fallback
            return ResearchSourceView(
                reference=reference,
                availability="CURRENT_SOURCE",
                provider="FIRECRAWL",
                url=urls[0],
                title=title,
                available_until=available_until,
            )
        except (AccountingDenied, ValueError):
            return fallback

    async def require_owner(self, experiment_id: UUID, operator_id: UUID) -> None:
        if await existing_experiment(self.engine, operator_id, experiment_id) is None:
            raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")

    @asynccontextmanager
    async def finding_scope(
        self,
        experiment_id: UUID,
        operator_id: UUID,
        run_id: UUID,
        subject: ArtifactInput,
    ):
        """Serialize publication with cancellation; no provider I/O occurs here."""
        await self.require_owner(experiment_id, operator_id)
        async with self.engine.begin() as connection:
            run = (
                (
                    await connection.execute(
                        select(runs)
                        .where(
                            runs.c.run_id == run_id,
                            runs.c.experiment_id == experiment_id,
                            runs.c.operator_id == operator_id,
                        )
                        .with_for_update(read=True)
                    )
                )
                .mappings()
                .one_or_none()
            )
            if run is None:
                raise ExperimentError(404, "AGENT_RUN_NOT_FOUND")
            if run["status"] != "RUNNING" or run["cancel_requested_at"] is not None:
                raise ExperimentError(409, "RESEARCH_RUN_NOT_ACTIVE")
            row = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == subject.artifact_id,
                            records.artifacts.c.experiment_id == experiment_id,
                            records.artifacts.c.kind == subject.kind,
                            records.artifacts.c.version == subject.version,
                            records.artifacts.c.content_hash == subject.content_hash,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise ExperimentError(409, "RESEARCH_SUBJECT_NOT_BOUND")
            exact = (
                str(subject.artifact_id),
                subject.kind.value,
                subject.version,
                subject.content_hash,
            )
            pinned = any(
                (
                    ref.get("artifact_id"),
                    ref.get("kind"),
                    ref.get("version"),
                    ref.get("content_hash"),
                )
                == exact
                for ref in run["input_refs"]
            )
            generated_here = False
            if (
                subject.kind == ArtifactKind.IDEA_CANDIDATE
                and row["operation_id"] is not None
            ):
                generated_here = (
                    await connection.scalar(
                        select(records.idea_discoveries.c.run_id).where(
                            records.idea_discoveries.c.run_id == run_id,
                            records.idea_discoveries.c.experiment_id == experiment_id,
                            records.idea_discoveries.c.operation_id
                            == row["operation_id"],
                        )
                    )
                    is not None
                )
            if not pinned and not generated_here:
                raise ExperimentError(409, "RESEARCH_SUBJECT_NOT_BOUND")
            yield run, row

    async def get_case(
        self, experiment_id: UUID, operator_id: UUID
    ) -> MarketResearchCase:
        await self.require_owner(experiment_id, operator_id)
        async with self.engine.connect() as connection:
            artifacts = (
                (
                    await connection.execute(
                        select(records.artifacts)
                        .where(
                            records.artifacts.c.experiment_id == experiment_id,
                            records.artifacts.c.kind.in_(
                                (*SUBJECT_KINDS, "RESEARCH_EVIDENCE")
                            ),
                        )
                        .order_by(
                            records.artifacts.c.created_at, records.artifacts.c.id
                        )
                    )
                )
                .mappings()
                .all()
            )
            links = (
                (
                    await connection.execute(
                        select(records.artifact_links).where(
                            records.artifact_links.c.experiment_id == experiment_id,
                            records.artifact_links.c.role == "RESEARCH_SUBJECT",
                        )
                    )
                )
                .mappings()
                .all()
            )
            sources = (
                (
                    await connection.execute(
                        select(records.source_refs).where(
                            records.source_refs.c.experiment_id == experiment_id,
                        )
                    )
                )
                .mappings()
                .all()
            )
            selected = set(
                (
                    await connection.execute(
                        select(records.candidate_selections.c.artifact_id).where(
                            records.candidate_selections.c.experiment_id
                            == experiment_id,
                        )
                    )
                ).scalars()
            )
            withdrawn = set(
                (
                    await connection.execute(
                        select(records.artifact_dispositions.c.artifact_id).where(
                            records.artifact_dispositions.c.experiment_id
                            == experiment_id,
                            records.artifact_dispositions.c.disposition.in_(
                                ("SUPERSEDED", "REJECTED")
                            ),
                        )
                    )
                ).scalars()
            )
        by_id = {row["id"]: row for row in artifacts}
        subjects = [row for row in artifacts if row["kind"] in SUBJECT_KINDS]
        findings: dict[UUID, list[SourceFindingView]] = {}
        for link in links:
            row = by_id.get(link["consumer_id"])
            subject = by_id.get(link["producer_id"])
            if (
                row is None
                or subject is None
                or row["kind"] != "RESEARCH_EVIDENCE"
                or row["payload"].get("research_schema") != "SOURCE_FINDING_V1"
            ):
                continue
            source_views = [
                await self.source_view(
                    experiment_id,
                    SourceReference(
                        **{
                            key: value
                            for key, value in source.items()
                            if key in SourceReference.model_fields
                        }
                    ),
                )
                for source in sources
                if source["artifact_id"] == row["id"]
            ]
            view = SourceFindingView(
                artifact=artifact_reference(row, "FINDING"),
                subject=artifact_reference(subject, "RESEARCH_SUBJECT"),
                observation=SourceFindingPayload.model_validate(row["payload"]),
                sources=source_views,
                created_at=row["created_at"],
            )
            findings.setdefault(subject["id"], []).append(view)
        projections = []
        for subject in subjects:
            observed = findings.get(subject["id"], [])
            coverage = []
            for dimension in RESEARCH_DIMENSIONS:
                matched = [
                    item for item in observed if item.observation.dimension == dimension
                ]
                statuses: set[EvidenceStatus] = {
                    item.observation.evidence_status for item in matched
                }
                status: CoverageStatus = (
                    "UNRESEARCHED"
                    if not statuses
                    else next(iter(statuses))
                    if len(statuses) == 1
                    else "MIXED"
                )
                coverage.append(
                    ResearchCoverage(
                        dimension=dimension,
                        status=status,
                        finding_ids=[item.artifact.artifact_id for item in matched],
                    )
                )
            current = subject["id"] not in withdrawn and not any(
                item["logical_id"] == subject["logical_id"]
                and item["version"] > subject["version"]
                for item in subjects
            )
            mode = (
                "SELECTED"
                if subject["id"] in selected
                else "CANDIDATE"
                if subject["kind"] == "IDEA_CANDIDATE"
                else "SUPPLIED"
                if subject["kind"] == "IDEA_SEED"
                else "REFINED"
            )
            projections.append(
                SubjectResearchCase(
                    subject=artifact_reference(subject, "RESEARCH_SUBJECT"),
                    mode=mode,
                    current=current,
                    findings=observed,
                    coverage=coverage,
                    gaps=[
                        item.dimension
                        for item in coverage
                        if item.status not in {"SUPPORTED", "CONTRADICTED"}
                    ],
                )
            )
        count = sum(len(item.findings) for item in projections)
        return MarketResearchCase(
            experiment_id=experiment_id,
            subjects=projections,
            finding_count=count,
            progress="PARTIAL" if count else "NOT_STARTED",
            limitations=[
                "Only current licensed Firecrawl source links are shown; other sources remain reference-only. Provider excerpts are not exposed.",
                "Coverage describes saved observations and does not certify completed market research.",
            ],
        )
