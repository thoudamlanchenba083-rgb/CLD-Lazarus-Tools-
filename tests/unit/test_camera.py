"""Unit tests for Phase 7: Camera events and optional snapshot uploads."""
import io
import pytest
from PIL import Image
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


def _create_test_jpeg():
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_camera_events_permission_denied_logged():
    """Denying camera records a PERMISSION_DENIED event without preview."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # PERMISSION_DENIED event can be logged without active CAMERA consent
    res = client.post(
        "/api/camera/events",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json={"event_type": "PERMISSION_DENIED"},
    )
    assert res.status_code == 201
    assert res.json()["event_type"] == "PERMISSION_DENIED"


def test_camera_events_require_consent():
    """Operational events like PREVIEW_STARTED require active CAMERA consent."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # Without consent -> 403
    res_no_consent = client.post(
        "/api/camera/events",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json={"event_type": "PREVIEW_STARTED"},
    )
    assert res_no_consent.status_code == 403

    # Grant CAMERA consent
    client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "CAMERA", "granted": True},
    )

    # Now allowed
    res_with_consent = client.post(
        "/api/camera/events",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        json={"event_type": "PREVIEW_STARTED"},
    )
    assert res_with_consent.status_code == 201
    assert res_with_consent.json()["event_type"] == "PREVIEW_STARTED"


def test_upload_without_snapshot_consent_is_rejected():
    """Upload without separate SNAPSHOT_UPLOAD consent returns 403."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    jpeg_bytes = _create_test_jpeg()
    files = {"file": ("snapshot.jpg", jpeg_bytes, "image/jpeg")}

    res = client.post(
        "/api/camera/snapshot",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        files=files,
    )
    assert res.status_code == 403
    assert "Separate SNAPSHOT_UPLOAD consent is required" in res.json()["detail"]


def test_upload_spoofed_file_type_is_rejected():
    """Renaming an executable/text to .jpg is rejected by magic byte validation."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # Grant SNAPSHOT_UPLOAD consent
    client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "SNAPSHOT_UPLOAD", "granted": True},
    )

    fake_jpeg = b"MZ\x90\x00\x03\x00\x00\x00this is a test executable binary disguised as jpg"
    files = {"file": ("malicious.jpg", fake_jpeg, "image/jpeg")}

    res = client.post(
        "/api/camera/snapshot",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        files=files,
    )
    assert res.status_code == 400
    assert "Invalid image file" in res.json()["detail"]


def test_valid_snapshot_upload():
    """Valid JPEG with explicit consent is saved."""
    v_res = client.post("/api/visitors")
    v_uuid = v_res.json()["visitor_uuid"]
    s_res = client.post("/api/sessions", json={"visitor_uuid": v_uuid})
    s_uuid = s_res.json()["session_uuid"]
    s_token = s_res.json()["session_token"]

    # Grant SNAPSHOT_UPLOAD consent
    client.post(
        f"/api/consent/{s_uuid}",
        headers={"X-Session-Token": s_token},
        json={"consent_type": "SNAPSHOT_UPLOAD", "granted": True},
    )

    jpeg_bytes = _create_test_jpeg()
    files = {"file": ("volunteer.jpg", jpeg_bytes, "image/jpeg")}

    res = client.post(
        "/api/camera/snapshot",
        headers={"X-Session-ID": s_uuid, "X-Session-Token": s_token},
        files=files,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["saved"] is True
    assert data["filename"].endswith(".jpg")
    assert data["size_bytes"] == len(jpeg_bytes)
