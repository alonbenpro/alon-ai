import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alon_ai.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        hide_parameters=True,
    )


class DatabaseHealthChecker:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def __call__(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            structlog.get_logger(__name__).warning(
                "database_readiness_failed",
                service="api",
                error_type=type(error).__name__,
            )
            return False
        return True
