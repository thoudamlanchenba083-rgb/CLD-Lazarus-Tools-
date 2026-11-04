"""Unit tests for Phase 8: Telemetry and batched event pipeline."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, Base
from app.models.telemetry_event import TelemetryEvent, TelemetryEventType
from app.services.telemetry_service import sanitize_metadata
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


def test_sanitize_metadata():
    """Whitelists only safe keys and filters coordinates, tokens, or raw full UA."""
    meta = {
        "consent_type": "CAMERA",
        "granted": True,
        "raw_user_agent": "Mozilla/5.0 ... dangerous long UA ...",
        "latitude": 37.77,
        "token": "secret-token-123",
        "device_type": "mobile",
    }
    sanitized = sanitize_metadata(meta)
    assert "consent_type" in sanitized
    assert "granted" in sanitized
    assert "device_type" in sanitized
    assert "raw_user_agent" not in sanitized
    assert "latitude" not in sanitized
    assert "token" not in sanitized


def test_batched_telemetry_submission():
    """Batched submission of events for an active session."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    batch_payload = {
        "events": [
            {
                "event_type": "SESSION_CREATED",
                "metadata": {"action": "started"},
            },
            {
                "event_type": "CONSENT_GRANTED",
                "metadata": {"consent_type": "CAMERA", "granted": True},
            },
            {
                "event_type": "CAMERA_PERMISSION_GRANTED",
                "metadata": {"device_type": "desktop"},
            },
        ]
    }

    res = client.post(
        "/api/telemetry",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=batch_payload,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["received"] == 3
    assert data["recorded"] == 3


def test_unknown_event_type_rejected():
    """Unknown or unwhitelisted event type returns 422."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    bad_payload = {
        "events": [
            {
                "event_type": "MALICIOUS_CUSTOM_EVENT",
                "metadata": {},
            }
        ]
    }
    res = client.post(
        "/api/telemetry",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json=bad_payload,
    )
    assert res.status_code == 422


def test_telemetry_rejected_without_valid_session():
    """Telemetry without active session returns 401 or 403."""
    res_no_auth = client.post(
        "/api/telemetry",
        json={"events": [{"event_type": "SESSION_CREATED"}]},
    )
    assert res_no_auth.status_code == 401
