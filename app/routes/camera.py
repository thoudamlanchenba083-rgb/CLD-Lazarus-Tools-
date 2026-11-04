"""Camera routes — camera event logging and voluntary test snapshot upload."""
import io
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.camera_event import CameraEvent, CameraEventType
from app.models.consent import ConsentType
from app.schemas.camera import CameraEventCreate, CameraEventResponse, SnapshotUploadResponse
from app.services.consent_service import get_active_consent
from app.services.session_service import get_session_by_uuid, verify_session_token, is_session_active

logger = logging.getLogger("brAInfection.camera")
router = APIRouter(prefix="/api/camera", tags=["camera"])

# Storage directory outside static folder
SNAPSHOTS_DIR = Path("storage/snapshots")
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Limit 2MB for snapshot
MAX_SNAPSHOT_SIZE = 2 * 1024 * 1024


def _validate_session_and_status(
    x_session_id: str | None,
    x_session_token: str | None,
    db: Session,
):
    if not x_session_id or not x_session_token:
        raise HTTPException(status_code=401, detail="Session ID and token are required.")
    session_record = get_session_by_uuid(db, x_session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not verify_session_token(session_record, x_session_token):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    if not is_session_active(session_record):
        raise HTTPException(status_code=410, detail="Session is no longer active.")
    return session_record


@router.post("/events", response_model=CameraEventResponse, status_code=201)
def record_camera_event(
    data: CameraEventCreate,
    x_session_token: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Record a camera event (permission granted/denied, preview started/stopped, capture).

    Requires active session and CAMERA consent (except for PERMISSION_DENIED which logs denial).
    """
    session_record = _validate_session_and_status(x_session_id, x_session_token, db)

    consent = get_active_consent(db, session_record, ConsentType.CAMERA)
    # If the event is not PERMISSION_DENIED, require active CAMERA consent
    if data.event_type != CameraEventType.PERMISSION_DENIED and not consent:
        raise HTTPException(
            status_code=403,
            detail="CAMERA consent is required to record camera operational events."
        )

    now = datetime.now(timezone.utc)
    event_record = CameraEvent(
        session_id=session_record.id,
        event_type=data.event_type,
        consent_id=consent.id if consent else None,
        recorded_at=now,
    )
    db.add(event_record)
    db.commit()
    db.refresh(event_record)

    logger.info(
        "Camera event recorded: session=%s type=%s",
        session_record.session_uuid,
        data.event_type.value,
    )
    return event_record


@router.post("/snapshot", response_model=SnapshotUploadResponse, status_code=201)
async def upload_snapshot(
    file: UploadFile = File(...),
    x_session_token: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Voluntary test snapshot upload.

    Requires SNAPSHOT_UPLOAD consent, verifies real file magic bytes (JPEG/PNG only),
    enforces 2MB maximum size, saves with a random filename outside static.
    """
    session_record = _validate_session_and_status(x_session_id, x_session_token, db)

    # Separate, explicit consent requirement
    consent = get_active_consent(db, session_record, ConsentType.SNAPSHOT_UPLOAD)
    if not consent:
        raise HTTPException(
            status_code=403,
            detail="Separate SNAPSHOT_UPLOAD consent is required to upload volunteer test images."
        )

    # Read content and enforce size limit
    content = await file.read()
    if len(content) > MAX_SNAPSHOT_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {MAX_SNAPSHOT_SIZE // (1024 * 1024)} MB."
        )

    # Validate true file magic bytes using PIL (verifies real image structure, not just extension)
    try:
        img = Image.open(io.BytesIO(content))
        img_format = img.format.upper() if img.format else ""
        if img_format not in ("JPEG", "PNG"):
            raise ValueError(f"Unsupported image format: {img_format}")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file. Only verified JPEG and PNG files are accepted."
        )

    # Generate random filename and store outside static directory
    ext = "jpg" if img_format == "JPEG" else "png"
    random_filename = f"{session_record.session_uuid}_{secrets.token_hex(8)}.{ext}"
    target_path = SNAPSHOTS_DIR / random_filename

    with open(target_path, "wb") as f:
        f.write(content)

    # Record camera event for upload
    now = datetime.now(timezone.utc)
    event_record = CameraEvent(
        session_id=session_record.id,
        event_type=CameraEventType.SNAPSHOT_UPLOADED,
        consent_id=consent.id,
        recorded_at=now,
    )
    db.add(event_record)
    db.commit()

    logger.info(
        "Volunteer snapshot uploaded for session=%s saved as %s (%d bytes)",
        session_record.session_uuid,
        random_filename,
        len(content),
    )

    return SnapshotUploadResponse(
        saved=True,
        filename=random_filename,
        size_bytes=len(content),
        uploaded_at=now,
    )
