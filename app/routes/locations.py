"""Location routes — bounded, consent-gated location submissions."""
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.consent import ConsentType
from app.models.location import LocationUpdate
from app.schemas.telemetry import LocationSubmit, LocationResponse
from app.services.session_service import get_session_by_uuid, verify_session_token, is_session_active
from app.services.consent_service import get_active_consent

logger = logging.getLogger("brAInfection.locations")
router = APIRouter(prefix="/api/location", tags=["locations"])

# Server-side rate limit & caps:
# Max 4 updates per minute per session, max 50 total updates per session
MAX_UPDATES_PER_MINUTE = 4
MAX_UPDATES_PER_SESSION = 50

# In-memory tracking of recent update timestamps per session_id (int)
_session_update_timestamps = defaultdict(list)


def check_location_rate_limit(session_id: int, db: Session):
    now = datetime.now(timezone.utc)
    one_minute_ago = now - timedelta(seconds=60)

    # Clean old timestamps
    recent = [ts for ts in _session_update_timestamps[session_id] if ts > one_minute_ago]
    _session_update_timestamps[session_id] = recent

    if len(recent) >= MAX_UPDATES_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: maximum {MAX_UPDATES_PER_MINUTE} location updates per minute allowed."
        )

    # Check total updates cap in database
    total_count = db.query(LocationUpdate).filter(LocationUpdate.session_id == session_id).count()
    if total_count >= MAX_UPDATES_PER_SESSION:
        raise HTTPException(
            status_code=429,
            detail=f"Session cap exceeded: maximum {MAX_UPDATES_PER_SESSION} location updates per session allowed."
        )


@router.post("", response_model=LocationResponse, status_code=201)
def submit_location(
    data: LocationSubmit,
    x_session_token: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Submit approved location. Requires active session, LOCATION consent, and enforces rate limits."""
    if not x_session_id or not x_session_token:
        raise HTTPException(status_code=401, detail="Session ID and token are required.")

    session_record = get_session_by_uuid(db, x_session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not verify_session_token(session_record, x_session_token):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    if not is_session_active(session_record):
        raise HTTPException(status_code=410, detail="Session is no longer active.")

    # Require active LOCATION consent
    consent = get_active_consent(db, session_record, ConsentType.LOCATION)
    if not consent:
        raise HTTPException(
            status_code=403,
            detail="Active LOCATION consent is required to submit location updates."
        )

    # Check rate limits & session cap
    check_location_rate_limit(session_record.id, db)

    now = datetime.now(timezone.utc)
    loc_record = LocationUpdate(
        session_id=session_record.id,
        latitude=data.latitude,
        longitude=data.longitude,
        accuracy=data.accuracy,
        recorded_at=now,
    )
    db.add(loc_record)
    db.commit()
    db.refresh(loc_record)

    # Record timestamp for rate-limiting
    _session_update_timestamps[session_record.id].append(now)

    logger.info(
        "Location recorded for session=%s (lat=%.4f, lon=%.4f, acc=%.1f)",
        session_record.session_uuid,
        data.latitude,
        data.longitude,
        data.accuracy or 0.0,
    )
    return loc_record
