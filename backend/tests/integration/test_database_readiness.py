import os

import pytest

from alon_ai.config import Settings
from alon_ai.db.engine import DatabaseHealthChecker, create_engine


@pytest.mark.integration
async def test_real_postgres_is_ready() -> None:
    settings = Settings(
        environment="test",
        database_url=os.environ["ALON_AI_DATABASE_URL"],
        _env_file=None,
    )
    engine = create_engine(settings)
    try:
        assert await DatabaseHealthChecker(engine)() is True
    finally:
        await engine.dispose()
