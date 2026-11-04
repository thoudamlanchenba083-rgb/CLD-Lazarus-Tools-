"""Unit tests for Phase 6: Location sharing, bounding, rate limiting, and revocation."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, Base
from app.routes.locations import _session_update_timestamps
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


def test_location_without_consent_is_rejected():
    """Denying or omitting consent means no location is stored (403)."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    payload = {"latitude": 37.7749, "longitude": -122.4194, "accuracy": 10.0}
    res = client.post(
        "/api/location",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=payload,
    )
    assert res.status_code == 403
    assert "Active LOCATION consent is required" in res.json()["detail"]


def test_location_with_consent_and_validation():
    """Approved location is recorded and bounded by coordinates range."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # Grant LOCATION consent
    client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "LOCATION", "granted": True},
    )

    # Valid payload
    payload = {"latitude": 40.7128, "longitude": -74.0060, "accuracy": 5.5}
    res = client.post(
        "/api/location",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=payload,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["latitude"] == 40.7128
    assert data["longitude"] == -74.0060
    assert data["accuracy"] == 5.5

    # Out of range latitude (> 90) -> 422
    bad_payload = {"latitude": 105.0, "longitude": 0.0}
    bad_res = client.post(
        "/api/location",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=bad_payload,
    )
    assert bad_res.status_code == 422


def test_location_rejected_after_revocation_or_end():
    """Updates after revocation or session end are rejected."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    c_res = client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "LOCATION", "granted": True},
    )
    consent_id = c_res.json()["id"]

    # Revoke consent
    client.delete(f"/api/consent/{consent_id}", headers={"X-Session-Token": s_token})

    # Submitting location after revoke
    payload = {"latitude": 10.0, "longitude": 20.0}
    res_after_revoke = client.post(
        "/api/location",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=payload,
    )
    assert res_after_revoke.status_code == 403

    # Re-grant consent, then end session
    client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "LOCATION", "granted": True},
    )
    client.post(f"/api/sessions/{s_uuid}/end", headers={"X-Session-Token": s_token})

    # Submitting location after session end -> 410 Gone
    res_after_end = client.post(
        "/api/location",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=payload,
    )
    assert res_after_end.status_code == 410


def test_location_rate_limit_burst():
    """Burst of updates exceeding rate limit hits 429."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "LOCATION", "granted": True},
    )

    # 4 allowed per minute
    payload = {"latitude": 12.0, "longitude": 34.0}
    for i in range(4):
        res = client.post(
            "/api/location",
            headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
            json=payload,
        )
        assert res.status_code == 201

    # 5th request should hit 429
    res_burst = client.post(
        "/api/location",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=payload,
    )
    assert res_burst.status_code == 429
    assert "Rate limit exceeded" in res_burst.json()["detail"]
