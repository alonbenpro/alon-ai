"""Start a reviewed research-feedback return into Idea refinement."""

from __future__ import annotations

from uuid import UUID, uuid5

from alon_ai.db.repositories import experiments as experiment_repository
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.repositories.idea_research import IdeaResearchRepository
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.services.experiments import (
    ExperimentContext,
    StartReturnRefinementRequest,
    _read_experiment,
)
from alon_ai.services.schemas.records import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    ProductRecordsDenied,
)
from alon_ai.services.schemas.research import (
    AppendSourceFindingRequest,
    MarketResearchCase,
    SourceFindingView,
)


async def start_return_refinement(
    request: ExperimentContext, experiment_id: UUID, body: StartReturnRefinementRequest
) -> dict:
    """Claim an already-committed L08 feedback return; no model call occurs here."""
    detail = await _read_experiment(request, experiment_id)
    if detail is None:
        raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
    owned_verdict = await experiment_repository.owned_verdict(
        request.engine, body.verdict_id, experiment_id
    )
    if owned_verdict is None:
        raise ExperimentError(409, "FORGED_RESEARCH_FEEDBACK")
    try:
        receipt = await ProductRecordsRepository(
            request.engine
        ).start_same_intent_refinement_return(
            body.verdict_id,
            feedback=body.feedback.artifact(),
            command_key=body.command_key,
        )
    except ProductRecordsDenied as error:
        raise ExperimentError(409, error.reason) from None
    if receipt.experiment_id != experiment_id:
        raise ExperimentError(404, "EXPERIMENT_NOT_FOUND")
    return {
        "experiment_id": experiment_id,
        "cycle_id": receipt.id,
        "state": "AWAITING_REFINEMENT"
        if receipt.outcome == "STARTED"
        else "RETURN_REVIEW_REQUIRED",
        "reason_code": receipt.reason_code,
    }


class ResearchService:
    def __init__(self, context: ExperimentContext) -> None:
        self.context = context

    async def get_case(self, experiment_id: UUID) -> MarketResearchCase:
        """Read only committed observations, with exact historical subject identity."""
        return await IdeaResearchRepository(self.context.engine).get_case(
            experiment_id, self.context.operator_id
        )

    async def append_finding(
        self, experiment_id: UUID, body: AppendSourceFindingRequest
    ) -> SourceFindingView:
        """Internal publication boundary for original analysis, never provider excerpts."""
        repository = IdeaResearchRepository(self.context.engine)
        artifact_id = uuid5(body.run_id, f"finding:{body.step_key}")
        command_key = uuid5(body.run_id, f"finding-command:{body.step_key}")
        case = await self.get_case(experiment_id)
        existing = next(
            (
                finding
                for subject in case.subjects
                for finding in subject.findings
                if finding.artifact.artifact_id == artifact_id
            ),
            None,
        )
        if existing is not None:
            expected_subject = body.subject.model_copy(
                update={"role": "RESEARCH_SUBJECT"}
            )
            expected_sources = sorted(
                source.model_dump_json() for source in body.sources
            )
            actual_sources = sorted(
                source.reference.model_dump_json() for source in existing.sources
            )
            if (
                existing.observation != body.payload()
                or existing.subject != expected_subject
                or expected_sources != actual_sources
            ):
                raise ExperimentError(409, "COMMAND_CONFLICT")
            return existing
        async with repository.finding_scope(
            experiment_id, self.context.operator_id, body.run_id, body.subject
        ) as (run, _subject):
            try:
                await ProductRecordsRepository(self.context.engine).append_artifact(
                    ArtifactDraft(
                        id=artifact_id,
                        logical_id=artifact_id,
                        version=1,
                        experiment_id=experiment_id,
                        kind=ArtifactKind.RESEARCH_EVIDENCE,
                        payload=body.payload().model_dump(mode="json"),
                        created_by=self.context.operator_id,
                        created_at=run["created_at"],
                    ),
                    inputs=(
                        ArtifactInput(
                            artifact_id=body.subject.artifact_id,
                            kind=body.subject.kind,
                            version=body.subject.version,
                            content_hash=body.subject.content_hash,
                            role="RESEARCH_SUBJECT",
                        ),
                    ),
                    sources=body.sources,
                    command_key=command_key,
                )
            except ProductRecordsDenied as error:
                raise ExperimentError(409, error.reason) from None
        case = await self.get_case(experiment_id)
        return next(
            finding
            for subject in case.subjects
            for finding in subject.findings
            if finding.artifact.artifact_id == artifact_id
        )

    async def start_return_refinement(
        self, experiment_id: UUID, body: StartReturnRefinementRequest
    ) -> dict:
        return await start_return_refinement(self.context, experiment_id, body)
