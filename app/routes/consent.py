"""Consent routes — record, list and revoke consent."""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.consent import ConsentCreate, ConsentResponse, ConsentRevokeResponse, ConsentListResponse
from app.services.session_service import get_session_by_uuid, verify_session_token, is_session_active
from app.services.consent_service import (
    record_consent,
    revoke_consent,
    get_consent_by_id,
    get_session_consents,
)

logger = logging.getLogger("brAInfection.consent")
router = APIRouter(prefix="/api/consent", tags=["consent"])


def _require_active_session(session_id: str, x_session_token: str | None, db: Session):
    """Verify session ownership and that it is still active."""
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Session token required.")
    session_record = get_session_by_uuid(db, session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not verify_session_token(session_record, x_session_token):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    if not is_session_active(session_record):
        raise HTTPException(status_code=410, detail="Session is no longer active.")
    return session_record


@router.post("/{session_id}", response_model=ConsentResponse, status_code=201)
def create_consent(
    session_id: str,
    data: ConsentCreate,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Record a consent decision for the given session and type."""
    session_record = _require_active_session(session_id, x_session_token, db)
    consent = record_consent(db, session_record, data.consent_type, data.granted)
    logger.info(
        "Consent recorded: session=%s type=%s granted=%s",
        session_id,
        data.consent_type.value,
        data.granted,
    )
    return consent


@router.get("/{session_id}", response_model=ConsentListResponse)
def list_consents(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """List all consent records for the caller's session."""
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Session token required.")
    session_record = get_session_by_uuid(db, session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not verify_session_token(session_record, x_session_token):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    consents = get_session_consents(db, session_record)
    return ConsentListResponse(consents=consents)


@router.delete("/{consent_id}", response_model=ConsentRevokeResponse)
def revoke_consent_endpoint(
    consent_id: int,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Revoke a specific consent. The related endpoints will immediately reject new data."""
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Session token required.")
    consent = get_consent_by_id(db, consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found.")
    # Verify session ownership
    session_record = consent.session
    if not verify_session_token(session_record, x_session_token):
        raise HTTPException(status_code=403, detail="Invalid session token.")
    if consent.revoked_at is not None:
        raise HTTPException(status_code=409, detail="Consent is already revoked.")
    consent = revoke_consent(db, consent)
    logger.info(
        "Consent revoked: id=%d type=%s session=%s",
        consent.id,
        consent.consent_type.value,
        session_record.session_uuid,
    )
    return ConsentRevokeResponse(
        id=consent.id,
        consent_type=consent.consent_type,
        revoked_at=consent.revoked_at,
    )
