from fastapi.testclient import TestClient

from alon_ai.api.app import create_app
from alon_ai.config import Settings


class FakeHealth:
    def __init__(self, healthy: bool) -> None:
        self.healthy = healthy

    async def __call__(self) -> bool:
        return self.healthy


def test_readiness_returns_ready_payload_when_database_is_healthy() -> None:
    app = create_app(Settings(environment="test", _env_file=None))
    with TestClient(app) as client:
        app.state.database_health = FakeHealth(healthy=True)
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}


def test_readiness_returns_service_unavailable_payload_when_database_is_down() -> None:
    app = create_app(Settings(environment="test", _env_file=None))
    with TestClient(app) as client:
        app.state.database_health = FakeHealth(healthy=False)
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "down"}
