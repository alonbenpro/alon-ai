"""Start a reviewed research-feedback return into Idea refinement."""

from __future__ import annotations

from uuid import UUID

from alon_ai.db.repositories import experiments as experiment_repository
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.services.experiments import (
    ExperimentContext,
    StartReturnRefinementRequest,
    _read_experiment,
)
from alon_ai.services.schemas.records import ProductRecordsDenied


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

    async def start_return_refinement(
        self, experiment_id: UUID, body: StartReturnRefinementRequest
    ) -> dict:
        return await start_return_refinement(self.context, experiment_id, body)
