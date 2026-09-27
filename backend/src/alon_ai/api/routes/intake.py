"""Authenticated optional-idea proposal intake routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from alon_ai.api.dependencies import get_intake_service
from alon_ai.services.intake import IntakeService
from alon_ai.services.schemas.intake import (
    ExperimentSnapshot,
    GenerateIdeaRequest,
    RegenerateIdeaRequest,
    ReviseProposalRequest,
    StartProposalRequest,
)

router = APIRouter()
Service = Annotated[IntakeService, Depends(get_intake_service)]


@router.post("/ideas/generate", response_model=ExperimentSnapshot)
async def generate_idea(body: GenerateIdeaRequest, service: Service) -> dict:
    return await service.generate(body)


@router.post("/ideas/{experiment_id}/generate", response_model=ExperimentSnapshot)
async def regenerate_idea(
    experiment_id: UUID, body: RegenerateIdeaRequest, service: Service
) -> dict:
    return await service.regenerate(experiment_id, body)


@router.post("/ideas/{experiment_id}/revisions", response_model=ExperimentSnapshot)
async def revise_idea(
    experiment_id: UUID, body: ReviseProposalRequest, service: Service
) -> dict:
    return await service.revise(experiment_id, body)


@router.post("/ideas/{experiment_id}/start", response_model=ExperimentSnapshot)
async def start_proposal(
    experiment_id: UUID, body: StartProposalRequest, service: Service
) -> dict:
    return await service.start(experiment_id, body)
