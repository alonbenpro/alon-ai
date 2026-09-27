"""Public health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from alon_ai.api.dependencies import get_health_service
from alon_ai.api.schemas.health import (
    LivenessResponse,
    ReadinessResponse,
    ReadinessUnavailableResponse,
)
from alon_ai.services.health import HealthService

router = APIRouter()
HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]


@router.get("/live", response_model=LivenessResponse)
async def live(service: HealthServiceDependency) -> LivenessResponse:
    return service.live()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessUnavailableResponse}},
)
async def ready(service: HealthServiceDependency) -> ReadinessResponse:
    return await service.ready()
