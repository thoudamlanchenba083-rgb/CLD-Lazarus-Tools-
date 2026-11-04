"""Session routes — start, read, heartbeat, end sessions."""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionInfo,
    SessionEndResponse,
    HeartbeatResponse,
)
from app.services.session_service import (
    get_visitor_by_uuid,
    create_session,
    get_session_by_uuid,
    verify_session_token,
    touch_session,
    end_session,
    is_session_active,
)

logger = logging.getLogger("brAInfection.sessions")
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _get_session_and_verify(
    session_id: str,
    x_session_token: str | None,
    db: Session,
) -> "SessionRecord":
    """Helper: look up a session and verify the caller's token."""
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Session token required.")
    session_record = get_session_by_uuid(db, session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not verify_session_token(session_record, x_session_token):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    return session_record


@router.post("", response_model=SessionResponse, status_code=201)
def start_session(data: SessionCreate, db: Session = Depends(get_db)):
    """Start a new session linked to the given visitor UUID."""
    visitor = get_visitor_by_uuid(db, data.visitor_uuid)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found.")
    session_record = create_session(db, visitor)
    logger.info("Session started: %s", session_record.session_uuid)
    return session_record


@router.get("/{session_id}", response_model=SessionInfo)
def read_session(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Read the caller's own session. Ownership verified by session token."""
    session_record = _get_session_and_verify(session_id, x_session_token, db)
    return session_record


@router.post("/{session_id}/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Update last_activity to keep the session alive."""
    session_record = _get_session_and_verify(session_id, x_session_token, db)
    if not is_session_active(session_record):
        raise HTTPException(status_code=410, detail="Session is no longer active.")
    session_record = touch_session(db, session_record)
    return HeartbeatResponse(
        session_uuid=session_record.session_uuid,
        status=session_record.status.value,
        last_activity=session_record.last_activity,
    )


@router.post("/{session_id}/end", response_model=SessionEndResponse)
def end_session_endpoint(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """End the caller's session."""
    session_record = _get_session_and_verify(session_id, x_session_token, db)
    if not is_session_active(session_record):
        raise HTTPException(status_code=410, detail="Session is already ended or expired.")
    session_record = end_session(db, session_record)
    logger.info("Session ended: %s", session_record.session_uuid)
    return SessionEndResponse(
        session_uuid=session_record.session_uuid,
        status=session_record.status.value,
        ended_at=session_record.ended_at,
    )
