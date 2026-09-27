"""HTTP streaming adapter for operator activity."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi.responses import StreamingResponse

from alon_ai.services.operator import OperatorService

EVENT_POLL_SECONDS = 5


class OperatorStreamAdapter:
    def __init__(
        self, service: OperatorService, token, resolve, disconnected, poll_seconds
    ):
        self.service = service
        self.token = token
        self.resolve = resolve
        self.disconnected = disconnected
        self.poll_seconds = poll_seconds

    async def activity_events(self, experiment_id: UUID | None) -> StreamingResponse:
        return StreamingResponse(
            self.service.events(
                experiment_id,
                token=self.token,
                resolve=self.resolve,
                disconnected=self.disconnected,
                poll_seconds=self.poll_seconds,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )


class OperatorStreamFactory:
    def __init__(self, service: OperatorService) -> None:
        self.service = service

    def for_request(
        self,
        token: str | None,
        resolve: Callable[[str | None], Awaitable[object | None]],
        disconnected: Callable[[], Awaitable[bool]],
    ) -> OperatorStreamAdapter:
        return OperatorStreamAdapter(
            self.service, token, resolve, disconnected, EVENT_POLL_SECONDS
        )
