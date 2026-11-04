"""Telemetry routes — batched telemetry event ingestion."""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.telemetry import TelemetryBatchSubmit, TelemetryBatchResponse
from app.services.session_service import get_session_by_uuid, verify_session_token, is_session_active
from app.services.telemetry_service import record_event

logger = logging.getLogger("brAInfection.telemetry_routes")
router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.post("", response_model=TelemetryBatchResponse, status_code=201)
def submit_telemetry_batch(
    data: TelemetryBatchSubmit,
    x_session_token: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Batched submission of telemetry events.

    Validates session token and active status, verifies all event types against whitelist,
    and records them via telemetry_service.
    """
    if not x_session_id or not x_session_token:
        raise HTTPException(status_code=401, detail="Session ID and token are required.")

    session_record = get_session_by_uuid(db, x_session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not verify_session_token(session_record, x_session_token):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    if not is_session_active(session_record):
        raise HTTPException(status_code=410, detail="Session is no longer active.")

    count = 0
    for item in data.events:
        record_event(
            db=db,
            session_record=session_record,
            event_type=item.event_type,
            metadata=item.metadata,
        )
        count += 1

    return TelemetryBatchResponse(
        received=len(data.events),
        recorded=count,
    )
