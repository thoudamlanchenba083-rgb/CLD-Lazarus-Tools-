"""Legacy V1 session route — keeps /api/session working during migration.

This will be removed once the frontend is fully migrated to V2 APIs.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.consent import ConsentType
from app.services.session_service import create_visitor, create_session
from app.services.consent_service import record_consent

logger = logging.getLogger("brAInfection.legacy")
router = APIRouter(tags=["legacy"])


class LegacySessionIn(BaseModel):
    """V1-compatible session input."""
    consent: bool
    user_agent: str = Field(default="", max_length=600)
    platform: str = Field(default="", max_length=120)
    language: str = Field(default="", max_length=80)
    screen_width: int | None = Field(default=None, ge=0, le=20000)
    screen_height: int | None = Field(default=None, ge=0, le=20000)
    camera_permission: str = Field(default="not_requested", max_length=40)
    location_permission: str = Field(default="not_requested", max_length=40)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100000)


@router.post("/api/session")
def legacy_create_session(data: LegacySessionIn, db: Session = Depends(get_db)):
    """V1-compatible: create a session with all data in one POST.

    Internally creates a visitor, session, consents, device and location records.
    """
    if not data.consent:
        raise HTTPException(status_code=400, detail="Consent is required.")

    # Create visitor and session
    visitor = create_visitor(db)
    session_record = create_session(db, visitor)

    # Record device metadata consent and store device info
    from app.models.device import DeviceDetails
    record_consent(db, session_record, ConsentType.DEVICE_METADATA, True)
    device = DeviceDetails(
        session_id=session_record.id,
        user_agent=data.user_agent,
        browser=None,  # Will be parsed in Phase 5
        os=data.platform,
        language=data.language,
        screen_width=data.screen_width,
        screen_height=data.screen_height,
    )
    db.add(device)

    # Camera consent
    if data.camera_permission in ("granted", "denied"):
        record_consent(
            db, session_record, ConsentType.CAMERA,
            granted=(data.camera_permission == "granted"),
        )

    # Location consent and data
    if data.location_permission == "granted" and data.latitude is not None:
        from app.models.location import LocationUpdate
        record_consent(db, session_record, ConsentType.LOCATION, True)
        loc = LocationUpdate(
            session_id=session_record.id,
            latitude=data.latitude,
            longitude=data.longitude,
            accuracy=data.accuracy,
        )
        db.add(loc)

    db.commit()
    logger.info("Legacy session created: %s", session_record.session_uuid)
    return {"saved": True, "session_id": session_record.session_uuid}
