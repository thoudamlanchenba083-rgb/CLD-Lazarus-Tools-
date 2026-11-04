"""Smoke test: GET /health returns ok."""
from fastapi.testclient import TestClient


def test_health():
    """GET /health should return {"status": "ok"}."""
    # Import here so the app is created fresh for each test run
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
