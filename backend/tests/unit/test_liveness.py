from fastapi.testclient import TestClient

from alon_ai.api.app import create_app
from alon_ai.config import Settings


def test_liveness_does_not_require_database() -> None:
    app = create_app(Settings(environment="test", _env_file=None))
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
