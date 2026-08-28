from alon_ai.config import Settings
from alon_ai.worker.main import build_worker_startup_event


def test_worker_startup_event_reports_worker_and_disabled_outreach() -> None:
    settings = Settings(environment="test", outreach_enabled=False, _env_file=None)

    event = build_worker_startup_event(settings)

    assert event == {
        "event": "worker_ready",
        "service": "worker",
        "outreach_enabled": False,
    }
