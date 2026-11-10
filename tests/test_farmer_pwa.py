"""Tests for Farmer PWA assets and static serving."""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_farmer_pwa_static_serving():
    """Verify that FastAPI mounts and serves the Farmer PWA index.html."""
    res = client.get("/farmer/")
    assert res.status_code == 200
    assert "نَبْتَة" in res.text
    assert "manifest.json" in res.text
    assert "dir=\"rtl\"" in res.text


def test_farmer_pwa_manifest():
    """Verify PWA manifest is served."""
    res = client.get("/farmer/manifest.json")
    assert res.status_code == 200
    data = res.json()
    assert data["short_name"] == "نبتة"
    assert data["lang"] == "ar-EG"
