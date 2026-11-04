"""Unit tests for consent management."""
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


def test_consent_lifecycle():
    # 1. Create visitor and session
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # 2. Record consent
    c_res = client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "CAMERA", "granted": True},
    )
    assert c_res.status_code == 201
    c_data = c_res.json()
    assert c_data["consent_type"] == "CAMERA"
    assert c_data["granted"] is True
    assert c_data["consent_version"] == 1
    assert c_data["revoked_at"] is None
    consent_id = c_data["id"]

    # 3. List consents
    list_res = client.get(f"/api/consent/{s_uuid}", headers={"X-Session-Token": s_token})
    assert list_res.status_code == 200
    consents = list_res.json()["consents"]
    assert len(consents) == 1
    assert consents[0]["id"] == consent_id

    # 4. Revoke consent
    rev_res = client.delete(f"/api/consent/{consent_id}", headers={"X-Session-Token": s_token})
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["id"] == consent_id
    assert rev_data["revoked_at"] is not None

    # 5. Revoking again returns conflict 409
    rev_again = client.delete(f"/api/consent/{consent_id}", headers={"X-Session-Token": s_token})
    assert rev_again.status_code == 409


def test_consent_rejection_without_token():
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]

    c_res = client.post(
        f"/api/consent/{s_uuid}",
        json={"consent_type": "CAMERA", "granted": True},
    )
    assert c_res.status_code == 401
