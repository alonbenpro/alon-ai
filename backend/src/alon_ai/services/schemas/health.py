"""Transport-neutral health results."""

from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["api"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["up"]


class ReadinessUnavailableResponse(BaseModel):
    status: Literal["not_ready"]
    database: Literal["down"]
