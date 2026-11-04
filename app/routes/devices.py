"""Device routes — submit browser-exposed device metadata."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from user_agents import parse

from app.database import get_db
from app.models.consent import ConsentType
from app.models.device import DeviceDetails
from app.schemas.telemetry import DeviceSubmit, DeviceResponse
from app.services.session_service import get_session_by_uuid, verify_session_token, is_session_active
from app.services.consent_service import get_active_consent

logger = logging.getLogger("brAInfection.devices")
router = APIRouter(prefix="/api/device", tags=["devices"])


@router.post("", response_model=DeviceResponse, status_code=201)
def submit_device(
    data: DeviceSubmit,
    request: Request,
    x_session_token: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Submit parsed, validated device metadata. Requires active session and DEVICE_METADATA consent."""
    if not x_session_id or not x_session_token:
        raise HTTPException(status_code=401, detail="Session ID and token are required.")

    session_record = get_session_by_uuid(db, x_session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not verify_session_token(session_record, x_session_token):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    if not is_session_active(session_record):
        raise HTTPException(status_code=410, detail="Session is no longer active.")

    # Require active DEVICE_METADATA consent
    consent = get_active_consent(db, session_record, ConsentType.DEVICE_METADATA)
    if not consent:
        raise HTTPException(
            status_code=403,
            detail="DEVICE_METADATA consent is required before submitting device data."
        )

    # Use client-submitted user-agent or fall back to request header User-Agent
    raw_ua = (data.user_agent or request.headers.get("user-agent") or "")[:600]
    parsed_ua = parse(raw_ua)

    # Determine device category
    if parsed_ua.is_mobile:
        device_category = "mobile"
    elif parsed_ua.is_tablet:
        device_category = "tablet"
    elif parsed_ua.is_pc:
        device_category = "desktop"
    elif parsed_ua.is_bot:
        device_category = "bot"
    else:
        device_category = "other"

    browser_family = f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}".strip()[:120] or None
    os_family = f"{parsed_ua.os.family} {parsed_ua.os.version_string}".strip()[:120] or None

    # Length-limit all fields from client
    device_record = DeviceDetails(
        session_id=session_record.id,
        browser=browser_family,
        os=os_family,
        device_type=device_category,
        screen_width=data.screen_width,
        screen_height=data.screen_height,
        language=(data.language or "")[:80] or None,
        timezone=(data.timezone or "")[:80] or None,
        online=data.online,
        user_agent=raw_ua,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(device_record)
    db.commit()
    db.refresh(device_record)

    logger.info(
        "Device info recorded for session=%s category=%s browser=%s os=%s",
        session_record.session_uuid,
        device_category,
        browser_family,
        os_family,
    )
    return device_record
