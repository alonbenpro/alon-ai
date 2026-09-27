"""Sanitized, read-only projections of authoritative experiment activity."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from alon_ai.api.dependencies import get_operator_service, get_operator_stream_service
from alon_ai.api.operator_stream import OperatorStreamAdapter
from alon_ai.api.schemas.operator import ActivityResponse, SystemStatus
from alon_ai.services.operator import OperatorService

router = APIRouter()
OperatorServiceDependency = Annotated[OperatorService, Depends(get_operator_service)]
OperatorStreamDependency = Annotated[
    OperatorStreamAdapter, Depends(get_operator_stream_service)
]


@router.get("/status", response_model=SystemStatus)
async def status(service: OperatorServiceDependency) -> SystemStatus:
    return await service.status()


@router.get("/activity", response_model=ActivityResponse)
async def activity(
    service: OperatorServiceDependency, experiment_id: UUID | None = None
) -> ActivityResponse:
    return await service.activity(experiment_id)


@router.get("/activity/events")
async def activity_events(
    service: OperatorStreamDependency, experiment_id: UUID | None = None
) -> StreamingResponse:
    return await service.activity_events(experiment_id)
