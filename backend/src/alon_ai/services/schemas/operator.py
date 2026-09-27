"""Operator activity projections shared by the HTTP surface."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ActivityState = Literal["queued", "running", "completed", "blocked"]


class ActivityItem(BaseModel):
    id: UUID
    kind: str
    state: ActivityState
    label: str
    occurred_at: datetime


class ActivityResponse(BaseModel):
    items: list[ActivityItem]
    cursor: str | None


class SystemStatus(BaseModel):
    health: dict[str, Literal["ok"]]
    readiness: dict[str, Literal["ready", "not_ready"]]
    counts: dict[ActivityState, int]
