"""Unit tests for visitor and session management."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, Base
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

# Set up test DB engine with StaticPool so in-memory SQLite maintains tables across connections
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


def test_visitor_and_session_creation():
    # 1. Create visitor
    v_res = client.post("/api/visitors")
    assert v_res.status_code == 201
    visitor_data = v_res.json()
    assert "visitor_uuid" in visitor_data
    v_uuid = visitor_data["visitor_uuid"]

    # 2. Start session
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    assert s_res.status_code == 201
    session_data = s_res.json()
    assert "session_uuid" in session_data
    assert "session_token" in session_data
    assert session_data["status"] == "ACTIVE"
    s_uuid = session_data["session_uuid"]
    s_token = session_data["session_token"]

    # 3. Read own session
    get_res = client.get(f"/api/sessions/{s_uuid}", headers={"X-Session-Token": s_token})
    assert get_res.status_code == 200
    info = get_res.json()
    assert info["session_uuid"] == s_uuid
    assert info["status"] == "ACTIVE"


def test_session_isolation():
    """Browser A cannot read Browser B's session."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # Request without token
    res_no_token = client.get(f"/api/sessions/{s_uuid}")
    assert res_no_token.status_code == 401

    # Request with wrong token
    res_wrong_token = client.get(f"/api/sessions/{s_uuid}", headers={"X-Session-Token": "invalid-token"})
    assert res_wrong_token.status_code == 403


def test_session_end_and_heartbeat():
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # Heartbeat
    hb_res = client.post(f"/api/sessions/{s_uuid}/heartbeat", headers={"X-Session-Token": s_token})
    assert hb_res.status_code == 200
    assert hb_res.json()["status"] == "ACTIVE"

    # End session
    end_res = client.post(f"/api/sessions/{s_uuid}/end", headers={"X-Session-Token": s_token})
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "ENDED"

    # Subsequent heartbeat should return 410 (no longer active)
    hb_after_end = client.post(f"/api/sessions/{s_uuid}/heartbeat", headers={"X-Session-Token": s_token})
    assert hb_after_end.status_code == 410
