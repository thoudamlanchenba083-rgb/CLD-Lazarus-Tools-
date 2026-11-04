"""Admin routes — V1-compatible token-based admin API.

Will be replaced with proper login/cookie auth in Phase 10.
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.session import SessionRecord

logger = logging.getLogger("brAInfection.admin")
router = APIRouter(prefix="/api", tags=["admin"])


def _verify_admin(x_admin_token: str | None = Header(default=None)):
    """V1-compatible admin token check."""
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token.")


@router.get("/sessions")
def list_sessions(
    x_admin_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """List recent sessions (admin only). V1-compatible endpoint."""
    _verify_admin(x_admin_token)
    rows = (
        db.query(SessionRecord)
        .order_by(SessionRecord.started_at.desc())
        .limit(250)
        .all()
    )
    result = []
    for s in rows:
        entry = {
            "id": s.session_uuid,
            "created_at": s.started_at.isoformat() if s.started_at else None,
            "status": s.status.value if s.status else None,
            "camera_permission": "not_requested",
            "location_permission": "not_requested",
            "latitude": None,
            "longitude": None,
            "accuracy": None,
            "platform": None,
            "user_agent": None,
        }
        # Populate from related tables if available
        if s.device_details:
            d = s.device_details[0]
            entry["platform"] = d.os or d.browser or ""
            entry["user_agent"] = d.user_agent or ""
        if s.location_updates:
            loc = s.location_updates[-1]
            entry["latitude"] = loc.latitude
            entry["longitude"] = loc.longitude
            entry["accuracy"] = loc.accuracy
            entry["location_permission"] = "granted"
        if s.camera_events:
            for evt in s.camera_events:
                if evt.event_type.value == "PERMISSION_GRANTED":
                    entry["camera_permission"] = "granted"
                    break
                elif evt.event_type.value == "PERMISSION_DENIED":
                    entry["camera_permission"] = "denied"
        result.append(entry)
    return result
