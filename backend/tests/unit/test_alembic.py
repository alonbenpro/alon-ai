import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_percent_encoded_password_supports_offline_migration_setup() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "ALON_AI_DATABASE_URL": (
                "postgresql+psycopg://alon_ai:p%40ss@localhost:5432/alon_ai"
            ),
            "ALON_AI_ENVIRONMENT": "test",
        }
    )

    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, (
        "offline Alembic setup rejected a percent-encoded database URL"
    )
