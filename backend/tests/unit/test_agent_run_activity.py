"""Activity persistence must not alter the outcome of a provider operation."""

from contextlib import asynccontextmanager
from uuid import uuid4

from alon_ai.db.repositories import agent_runs


class FailingEngine:
    @asynccontextmanager
    async def begin(self):
        raise ConnectionError("provider-response-secret-text")
        yield


async def test_activity_write_failure_is_safe_and_best_effort(monkeypatch):
    emitted = []

    class Logger:
        def error(self, event, **fields):
            emitted.append((event, fields))

    monkeypatch.setattr(agent_runs.structlog, "get_logger", lambda *_args: Logger())
    run_id = uuid4()

    result = await agent_runs.AgentRunRepository(FailingEngine()).record_activity(
        run_id, "MODEL_REQUEST", "OpenAI request 1 prepared · gpt-6-luna"
    )

    assert result is None
    assert emitted == [
        (
            "agent_run_activity_persistence_failed",
            {
                "run_id": str(run_id),
                "event_type": "MODEL_REQUEST",
                "error_type": "ConnectionError",
            },
        )
    ]
    assert "secret" not in repr(emitted).lower()
