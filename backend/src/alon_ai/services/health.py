"""Liveness and dependency readiness use cases."""

from collections.abc import Awaitable, Callable

from alon_ai.services.schemas.health import LivenessResponse, ReadinessResponse


class ReadinessUnavailable(Exception):
    """Required database dependency is unavailable."""


class HealthService:
    def __init__(self, database_health: Callable[[], Awaitable[bool]]) -> None:
        self.database_health = database_health

    def live(self) -> LivenessResponse:
        return LivenessResponse(status="ok", service="api")

    async def ready(self) -> ReadinessResponse:
        if not await self.database_health():
            raise ReadinessUnavailable
        return ReadinessResponse(status="ready", database="up")
