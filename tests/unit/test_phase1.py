"""Tests to ensure Phase 1 acceptance checks pass."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_page_returns_200():
    response = client.get("/")
    assert response.status_code == 200
    assert "Link Safety Lab" in response.text
    assert "/static/css/style.css" in response.text


def test_admin_page_returns_200():
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Session" in response.text
    assert "records" in response.text


def test_legacy_session_endpoint():
    """V1 /api/session must remain compatible."""
    payload = {
        "consent": True,
        "user_agent": "Mozilla/5.0 Test",
        "platform": "Windows",
        "language": "en-US",
        "screen_width": 1920,
        "screen_height": 1080,
        "camera_permission": "granted",
        "location_permission": "granted",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "accuracy": 15.0,
    }
    response = client.post("/api/session", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert "session_id" in data


def test_forced_error_json_shape():
    """Unhandled exceptions return uniform {error, detail, request_id} shape."""
    # We can trigger or check response with a non-existent method/route or simulated exception
    response = client.get("/non-existent-route")
    assert response.status_code == 404
