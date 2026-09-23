"""Sanitized, read-only projections of authoritative experiment activity."""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text

from alon_ai.api.auth import COOKIE_NAME, AuthService

router = APIRouter()
EVENT_POLL_SECONDS = 5
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


_STATES: dict[str, tuple[ActivityState, str]] = {
    "RESERVED": ("queued", "Operation queued"),
    "DISPATCHED": ("running", "Operation running"),
    "RECONCILING": ("blocked", "Operation requires reconciliation"),
    "FINAL": ("completed", "Operation finished"),
    "RELEASED": ("blocked", "Operation stopped"),
}


async def _activity(request: Request, experiment_id: UUID | None) -> ActivityResponse:
    async with request.app.state.engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text("""SELECT c.id, o.kind, c.state,
                    coalesce(c.finished_at,c.created_at) AS occurred_at
                    FROM gov_calls c JOIN gov_operations o ON o.id=c.operation_id
                    WHERE (CAST(:experiment_id AS UUID) IS NULL OR c.experiment_id=:experiment_id)
                    ORDER BY c.created_at DESC,c.id DESC LIMIT 50"""),
                    {"experiment_id": experiment_id},
                )
            )
            .mappings()
            .all()
        )
    items = [
        ActivityItem(
            id=row["id"],
            kind=row["kind"],
            state=_STATES[row["state"]][0],
            label=_STATES[row["state"]][1],
            occurred_at=row["occurred_at"],
        )
        for row in rows
    ]
    if not items:
        return ActivityResponse(items=[], cursor=None)
    canonical = json.dumps(
        [(str(item.id), item.state, item.occurred_at.isoformat()) for item in items],
        separators=(",", ":"),
    )
    return ActivityResponse(
        items=items, cursor=hashlib.sha256(canonical.encode()).hexdigest()
    )


@router.get("/status", response_model=SystemStatus)
async def status(request: Request) -> SystemStatus:
    async with request.app.state.engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    text("SELECT state,count(*) AS total FROM gov_calls GROUP BY state")
                )
            )
            .mappings()
            .all()
        )
    counts: dict[ActivityState, int] = {
        "queued": 0,
        "running": 0,
        "completed": 0,
        "blocked": 0,
    }
    for row in rows:
        counts[_STATES[row["state"]][0]] += row["total"]
    return SystemStatus(
        health={"status": "ok"}, readiness={"status": "ready"}, counts=counts
    )


@router.get("/activity", response_model=ActivityResponse)
async def activity(
    request: Request, experiment_id: UUID | None = None
) -> ActivityResponse:
    return await _activity(request, experiment_id)


@router.get("/activity/events")
async def activity_events(
    request: Request, experiment_id: UUID | None = None
) -> StreamingResponse:
    auth: AuthService = request.app.state.auth
    token = request.cookies.get(COOKIE_NAME)

    async def events():
        previous: str | None = None
        first = True
        while not await request.is_disconnected():
            if await auth.resolve(token) is None:
                break
            current = await _activity(request, experiment_id)
            if first or current.cursor != previous:
                yield f"event: activity\ndata: {current.model_dump_json()}\n\n"
                previous = current.cursor
                first = False
            else:
                yield ": heartbeat\n\n"
            await asyncio.sleep(EVENT_POLL_SECONDS)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
