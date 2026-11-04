"""Consent service — record, check and revoke consent."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.consent import Consent, ConsentType
from app.models.session import SessionRecord, SessionStatus


def record_consent(
    db: Session,
    session_record: SessionRecord,
    consent_type: ConsentType,
    granted: bool = True,
) -> Consent:
    """Record a consent decision for the given session and type.

    If a previous active consent of the same type exists, it is revoked first.
    """
    settings = get_settings()

    # Revoke any existing active consent of the same type
    existing = get_active_consent(db, session_record, consent_type)
    if existing:
        existing.revoked_at = datetime.now(timezone.utc)

    consent = Consent(
        session_id=session_record.id,
        consent_type=consent_type,
        consent_version=settings.consent_version,
        granted=granted,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


def revoke_consent(db: Session, consent: Consent) -> Consent:
    """Revoke a consent record."""
    consent.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(consent)
    return consent


def get_consent_by_id(db: Session, consent_id: int) -> Consent | None:
    """Look up a consent record by ID."""
    return db.query(Consent).filter(Consent.id == consent_id).first()


def get_active_consent(
    db: Session,
    session_record: SessionRecord,
    consent_type: ConsentType,
) -> Consent | None:
    """Get the currently active consent of a given type for a session.
    Returns None if no active consent exists.
    """
    return (
        db.query(Consent)
        .filter(
            Consent.session_id == session_record.id,
            Consent.consent_type == consent_type,
            Consent.granted == True,
            Consent.revoked_at == None,
        )
        .order_by(Consent.recorded_at.desc())
        .first()
    )


def require_consent(
    db: Session,
    session_record: SessionRecord,
    consent_type: ConsentType,
) -> Consent:
    """Check that the session has active consent of the given type.
    Raises ValueError if not.
    """
    consent = get_active_consent(db, session_record, consent_type)
    if consent is None:
        raise ValueError(
            f"Active {consent_type.value} consent is required for this operation."
        )
    return consent


def get_session_consents(db: Session, session_record: SessionRecord) -> list[Consent]:
    """Get all consent records for a session."""
    return (
        db.query(Consent)
        .filter(Consent.session_id == session_record.id)
        .order_by(Consent.recorded_at.desc())
        .all()
    )
