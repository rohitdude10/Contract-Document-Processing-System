
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import health


def test_health_endpoint_healthy(monkeypatch):

    monkeypatch.setattr(
        health,
        "check_database_connection",
        AsyncMock(return_value=True),
    )

    monkeypatch.setattr(
        health,
        "check_rabbitmq_connection",
        AsyncMock(return_value=True),
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["services"]["api"] == "healthy"
    assert data["services"]["database"] == "healthy"
    assert data["services"]["rabbitmq"] == "healthy"


def test_health_endpoint_database_failure(monkeypatch):

    async def failed_database_check():
        raise ConnectionError("Database unavailable")

    monkeypatch.setattr(
        health,
        "check_database_connection",
        failed_database_check,
    )

    monkeypatch.setattr(
        health,
        "check_rabbitmq_connection",
        AsyncMock(return_value=True),
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503

    data = response.json()

    assert data["status"] == "degraded"
    assert data["services"]["database"] == "unhealthy"
    assert data["services"]["rabbitmq"] == "healthy"

