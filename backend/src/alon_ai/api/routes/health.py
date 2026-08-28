from typing import Literal

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["api"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["up"]


class ReadinessUnavailableResponse(BaseModel):
    status: Literal["not_ready"]
    database: Literal["down"]


@router.get("/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    return LivenessResponse(status="ok", service="api")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessUnavailableResponse}},
)
async def ready(request: Request) -> Response:
    if not await request.app.state.database_health():
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "down"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "database": "up"},
    )
