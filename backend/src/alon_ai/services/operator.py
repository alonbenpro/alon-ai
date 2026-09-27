"""Read-only operator activity and status use cases."""

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID

from alon_ai.services.schemas.operator import (
    ActivityItem,
    ActivityResponse,
    ActivityState,
    SystemStatus,
)

_STATES: dict[str, tuple[ActivityState, str]] = {
    "RESERVED": ("queued", "Operation queued"),
    "DISPATCHED": ("running", "Operation running"),
    "RECONCILING": ("blocked", "Operation requires reconciliation"),
    "FINAL": ("completed", "Operation finished"),
    "RELEASED": ("blocked", "Operation stopped"),
}


class OperatorService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def status(self) -> SystemStatus:
        rows = await self.repository.status_counts()
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

    async def activity(self, experiment_id: UUID | None) -> ActivityResponse:
        rows = await self.repository.activity_rows(experiment_id)
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
            [
                (str(item.id), item.state, item.occurred_at.isoformat())
                for item in items
            ],
            separators=(",", ":"),
        )
        return ActivityResponse(
            items=items, cursor=hashlib.sha256(canonical.encode()).hexdigest()
        )

    async def events(
        self,
        experiment_id: UUID | None,
        *,
        token: str | None,
        resolve: Callable[[str | None], Awaitable[object | None]],
        disconnected: Callable[[], Awaitable[bool]],
        poll_seconds: float,
    ) -> AsyncIterator[str]:
        previous: str | None = None
        first = True
        while not await disconnected():
            if await resolve(token) is None:
                break
            current = await self.activity(experiment_id)
            if first or current.cursor != previous:
                yield f"event: activity\ndata: {current.model_dump_json()}\n\n"
                previous = current.cursor
                first = False
            else:
                yield ": heartbeat\n\n"
            await asyncio.sleep(poll_seconds)
