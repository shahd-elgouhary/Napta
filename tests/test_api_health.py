"""Unit and integration tests for FastAPI health and basic endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.config import get_settings


@pytest.fixture
def client():
    """Create test client fixture."""
    return TestClient(app)


def test_health_check_endpoint(client):
    """Verify /health returns 200 with healthy status and metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert data["track"] == "Track B (The Body)"


def test_root_endpoint(client):
    """Verify root endpoint returns API links and service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "docs" in data


def test_settings_load():
    """Verify application configuration loads default attributes."""
    settings = get_settings()
    assert settings.APP_NAME == "FieldWise AI - Egypt Edition"
    assert settings.PORT == 8000
    assert "https://power.larc.nasa.gov" in settings.NASA_POWER_BASE_URL
