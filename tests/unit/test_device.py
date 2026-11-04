"""Unit tests for Phase 5: Device metadata collection and parsing."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, Base
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
from sqlalchemy import event
@event.listens_for(test_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

Base.metadata.create_all(bind=test_engine)
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_device_data_without_consent_is_rejected():
    """Device data submitted before consent is granted must return 403."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    payload = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "language": "en-US",
        "timezone": "America/New_York",
        "screen_width": 1920,
        "screen_height": 1080,
        "online": True,
    }

    # Submit without consent
    res = client.post(
        "/api/device",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=payload,
    )
    assert res.status_code == 403
    assert "DEVICE_METADATA consent is required" in res.json()["detail"]


def test_device_data_with_consent_is_parsed():
    """Device data with consent is parsed for browser, os, and device category."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # Grant DEVICE_METADATA consent
    client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "DEVICE_METADATA", "granted": True},
    )

    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
    payload = {
        "user_agent": ua,
        "language": "en-US",
        "timezone": "America/New_York",
        "screen_width": 390,
        "screen_height": 844,
        "online": True,
    }

    res = client.post(
        "/api/device",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=payload,
    )
    assert res.status_code == 201
    data = res.json()
    assert "Mobile Safari" in data["browser"]
    assert "iOS" in data["os"]
    assert data["device_type"] == "mobile"
    assert data["screen_width"] == 390
    assert data["screen_height"] == 844
    assert data["language"] == "en-US"
    assert data["timezone"] == "America/New_York"
    assert data["online"] is True


def test_oversized_or_malformed_fields_return_422():
    """Fields exceeding length or bounds should return 422 Unprocessable Entity."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # Oversized screen width (> 20000)
    bad_payload = {
        "user_agent": "Test",
        "screen_width": 999999,
    }
    res = client.post(
        "/api/device",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=bad_payload,
    )
    assert res.status_code == 422
