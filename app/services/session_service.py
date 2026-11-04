"""Session service — create, touch, expire and end sessions."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.visitor import Visitor
from app.models.session import SessionRecord, SessionStatus


def create_visitor(db: Session) -> Visitor:
    """Create an anonymous visitor with a random UUID."""
    visitor = Visitor(visitor_uuid=str(uuid.uuid4()))
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    return visitor


def get_visitor_by_uuid(db: Session, visitor_uuid: str) -> Visitor | None:
    """Look up a visitor by their UUID."""
    return db.query(Visitor).filter(Visitor.visitor_uuid == visitor_uuid).first()


def create_session(db: Session, visitor: Visitor) -> SessionRecord:
    """Start a new session for the given visitor."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    session_record = SessionRecord(
        session_uuid=str(uuid.uuid4()),
        session_token=secrets.token_urlsafe(48),
        visitor_id=visitor.id,
        status=SessionStatus.ACTIVE,
        started_at=now,
        expires_at=now + timedelta(minutes=settings.session_lifetime_minutes),
        last_activity=now,
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record


def get_session_by_uuid(db: Session, session_uuid: str) -> SessionRecord | None:
    """Look up a session by its UUID."""
    return (
        db.query(SessionRecord)
        .filter(SessionRecord.session_uuid == session_uuid)
        .first()
    )


def verify_session_token(session_record: SessionRecord, token: str) -> bool:
    """Check that the provided token matches the session."""
    return secrets.compare_digest(session_record.session_token, token)


def touch_session(db: Session, session_record: SessionRecord) -> SessionRecord:
    """Update last_activity for the session (heartbeat)."""
    now = datetime.now(timezone.utc)
    if session_record.status != SessionStatus.ACTIVE:
        return session_record
    session_record.last_activity = now
    db.commit()
    db.refresh(session_record)
    return session_record


def end_session(db: Session, session_record: SessionRecord) -> SessionRecord:
    """Mark a session as ENDED."""
    now = datetime.now(timezone.utc)
    session_record.status = SessionStatus.ENDED
    session_record.ended_at = now
    session_record.last_activity = now
    db.commit()
    db.refresh(session_record)
    return session_record


def expire_stale_sessions(db: Session) -> int:
    """Mark ACTIVE sessions as EXPIRED if they have been inactive past their expiry.
    Returns the number of sessions expired.
    """
    now = datetime.now(timezone.utc)
    stale = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.status == SessionStatus.ACTIVE,
            SessionRecord.expires_at <= now,
        )
        .all()
    )
    for s in stale:
        s.status = SessionStatus.EXPIRED
        s.ended_at = now
    db.commit()
    return len(stale)


def is_session_active(session_record: SessionRecord) -> bool:
    """Check if a session is active and not expired."""
    if session_record.status != SessionStatus.ACTIVE:
        return False
    now = datetime.now(timezone.utc)
    expires_at = session_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        return False
    return True
