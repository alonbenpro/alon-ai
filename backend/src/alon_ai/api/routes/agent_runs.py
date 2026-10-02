"""Private operator Idea run admission and read/control endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from alon_ai.api.dependencies import get_agent_run_service
from alon_ai.services.agent_run_service import AgentRunService
from alon_ai.services.schemas.agent_runs import (
    AgentRunRequest,
    CancelRunRequest,
    CancelRunResult,
    RejectRunRequest,
    RunEvents,
    RunRef,
    RunResult,
    RunView,
)

router = APIRouter()
Service = Annotated[AgentRunService, Depends(get_agent_run_service)]


@router.post(
    "/experiments/{experiment_id}/agent-runs", response_model=RunRef, status_code=202
)
async def admit_run(
    experiment_id: UUID, body: AgentRunRequest, service: Service
) -> RunRef:
    return await service.admit(experiment_id, body)


@router.get("/agent-runs/{run_id}", response_model=RunView)
async def get_run(run_id: UUID, service: Service) -> RunView:
    return await service.get(run_id)


@router.get("/agent-runs/{run_id}/result", response_model=RunResult)
async def get_run_result(run_id: UUID, service: Service) -> RunResult:
    return await service.result(run_id)


@router.get("/agent-runs/{run_id}/events", response_model=RunEvents)
async def get_run_events(run_id: UUID, service: Service) -> RunEvents:
    return await service.events(run_id)


@router.post("/agent-runs/{run_id}/cancel", response_model=CancelRunResult)
async def cancel_run(
    run_id: UUID, body: CancelRunRequest, service: Service
) -> CancelRunResult:
    return await service.cancel(run_id, body)


@router.post("/agent-runs/{run_id}/reject", response_model=RunView)
async def reject_run(run_id: UUID, body: RejectRunRequest, service: Service) -> RunView:
    return await service.reject(run_id, body)
