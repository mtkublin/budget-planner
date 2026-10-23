from fastapi.testclient import TestClient

import budget_planner
from budget_planner.config import Settings
from budget_planner.web.app import app, create_app


def test_package_importable() -> None:
    assert budget_planner.__name__ == "budget_planner"


def test_healthz_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_echoes_settings() -> None:
    cfg = Settings(_env_file=None)
    client = TestClient(create_app(settings=cfg))
    response = client.get("/")
    assert response.status_code == 200
    assert "base_currency=PLN" in response.text
    assert "tz=Europe/Warsaw" in response.text
