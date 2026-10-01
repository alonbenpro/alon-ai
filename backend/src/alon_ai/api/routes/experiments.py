"""HTTP contracts and one-call experiment handlers."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from alon_ai.api.dependencies import (
    get_experiment_service,
    get_idea_service,
    get_research_service,
)
from alon_ai.api.schemas.experiments import (
    AcceptRequest,
    CreateExperimentRequest,
    ExperimentRuntimeStatus,
    RefineRequest,
    SelectCandidateRequest,
    StartReturnRefinementRequest,
)
from alon_ai.services.experiments import ExperimentService
from alon_ai.services.ideas import IdeaService
from alon_ai.services.research import ResearchService
from alon_ai.services.schemas.agent_runs import (
    SavedIdeaProfileResult,
    SetupIdeaProfileRequest,
    SetupIdeaProfileResult,
)
from alon_ai.services.schemas.intake import ExperimentSnapshot
from alon_ai.services.schemas.research import MarketResearchCase

router = APIRouter()
ExperimentServiceDependency = Annotated[
    ExperimentService, Depends(get_experiment_service)
]
IdeaServiceDependency = Annotated[IdeaService, Depends(get_idea_service)]
ResearchServiceDependency = Annotated[ResearchService, Depends(get_research_service)]


@router.post("/idea-profile", response_model=SetupIdeaProfileResult)
async def setup_idea_profile(
    body: SetupIdeaProfileRequest, service: ExperimentServiceDependency
) -> SetupIdeaProfileResult:
    return await service.setup_profile(body)


@router.get("/idea-profile", response_model=SavedIdeaProfileResult)
async def get_idea_profile(
    service: ExperimentServiceDependency,
) -> SavedIdeaProfileResult:
    return await service.get_profile()


@router.post("/experiments", response_model=ExperimentSnapshot, status_code=201)
async def create_experiment(
    body: CreateExperimentRequest, service: ExperimentServiceDependency
) -> dict:
    return await service.create(body)


@router.get("/experiments/runtime", response_model=ExperimentRuntimeStatus)
async def experiment_runtime_status(
    service: ExperimentServiceDependency,
) -> ExperimentRuntimeStatus:
    return await service.runtime_status()


@router.get("/experiments/{experiment_id}", response_model=ExperimentSnapshot)
async def get_experiment(
    experiment_id: UUID, service: ExperimentServiceDependency
) -> dict:
    return await service.get(experiment_id)


@router.get(
    "/experiments/{experiment_id}/research-case", response_model=MarketResearchCase
)
async def get_research_case(
    experiment_id: UUID, service: ResearchServiceDependency
) -> MarketResearchCase:
    return await service.get_case(experiment_id)


@router.post(
    "/experiments/{experiment_id}/returns/refine",
    description="Claim an already-committed L08 feedback return; no model call occurs here.",
)
async def start_return_refinement(
    experiment_id: UUID,
    body: StartReturnRefinementRequest,
    service: ResearchServiceDependency,
) -> dict:
    return await service.start_return_refinement(experiment_id, body)


@router.post("/experiments/{experiment_id}/discover")
async def discover_experiment(
    experiment_id: UUID, body: RefineRequest, service: IdeaServiceDependency
) -> dict:
    return await service.discover(experiment_id, body)


@router.post("/experiments/{experiment_id}/select")
async def select_experiment_candidate(
    experiment_id: UUID, body: SelectCandidateRequest, service: IdeaServiceDependency
) -> dict:
    return await service.select(experiment_id, body)


@router.post("/experiments/{experiment_id}/refine")
async def refine_experiment(
    experiment_id: UUID, body: RefineRequest, service: IdeaServiceDependency
) -> dict:
    return await service.refine(experiment_id, body)


@router.post("/experiments/{experiment_id}/accept")
async def accept_experiment_idea(
    experiment_id: UUID, body: AcceptRequest, service: IdeaServiceDependency
) -> dict:
    return await service.accept(experiment_id, body)
