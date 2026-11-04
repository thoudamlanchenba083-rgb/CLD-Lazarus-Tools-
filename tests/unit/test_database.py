"""Unit tests for database models, cascade delete, and constraints."""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.visitor import Visitor
from app.models.session import SessionRecord, SessionStatus
from app.models.consent import Consent, ConsentType
from app.models.device import DeviceDetails
from app.models.location import LocationUpdate
from app.models.camera_event import CameraEvent, CameraEventType


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Enable SQLite foreign key support
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_cascade_delete(test_db):
    """Deleting a session must cascade and delete child rows (consents, device, location, camera)."""
    now = datetime.now(timezone.utc)
    visitor = Visitor(visitor_uuid="vis-123", created_at=now)
    test_db.add(visitor)
    test_db.commit()

    session = SessionRecord(
        session_uuid="sess-123",
        session_token="tok-123",
        visitor_id=visitor.id,
        status=SessionStatus.ACTIVE,
        started_at=now,
        expires_at=now,
        last_activity=now,
    )
    test_db.add(session)
    test_db.commit()

    consent = Consent(
        session_id=session.id,
        consent_type=ConsentType.CAMERA,
        consent_version=1,
        granted=True,
        recorded_at=now,
    )
    device = DeviceDetails(session_id=session.id, user_agent="TestAgent")
    location = LocationUpdate(session_id=session.id, latitude=12.34, longitude=56.78, accuracy=10.0)
    camera = CameraEvent(session_id=session.id, event_type=CameraEventType.PERMISSION_GRANTED)

    test_db.add_all([consent, device, location, camera])
    test_db.commit()

    assert test_db.query(Consent).filter_by(session_id=session.id).count() == 1
    assert test_db.query(DeviceDetails).filter_by(session_id=session.id).count() == 1
    assert test_db.query(LocationUpdate).filter_by(session_id=session.id).count() == 1
    assert test_db.query(CameraEvent).filter_by(session_id=session.id).count() == 1

    # Delete session
    test_db.delete(session)
    test_db.commit()

    # Verify all related records are deleted
    assert test_db.query(Consent).filter_by(session_id=session.id).count() == 0
    assert test_db.query(DeviceDetails).filter_by(session_id=session.id).count() == 0
    assert test_db.query(LocationUpdate).filter_by(session_id=session.id).count() == 0
    assert test_db.query(CameraEvent).filter_by(session_id=session.id).count() == 0
