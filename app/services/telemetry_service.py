"""Telemetry service — single unified entry point for logging all lifecycle and consent events."""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.session import SessionRecord
from app.models.telemetry_event import TelemetryEvent, TelemetryEventType

logger = logging.getLogger("brAInfection.telemetry")

# Whitelist allowed metadata keys (strictly no secrets, coordinates, tokens, or raw full UA)
ALLOWED_METADATA_KEYS = {
    "consent_type",
    "consent_version",
    "granted",
    "revoked",
    "device_type",
    "browser",
    "os",
    "language",
    "timezone",
    "action",
    "timestamp",
}


def sanitize_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Sanitize metadata to keep only whitelisted, non-sensitive keys."""
    if not meta or not isinstance(meta, dict):
        return {}
    sanitized = {}
    for k, v in meta.items():
        if k in ALLOWED_METADATA_KEYS:
            # Ensure scalar or small string values
            if isinstance(v, (str, int, float, bool)) or v is None:
                sanitized[k] = v
    return sanitized


def record_event(
    db: Session,
    session_record: SessionRecord,
    event_type: TelemetryEventType,
    metadata: dict[str, Any] | None = None,
) -> TelemetryEvent:
    """Record a validated telemetry event for a session."""
    clean_meta = sanitize_metadata(metadata)
    event = TelemetryEvent(
        session_id=session_record.id,
        event_type=event_type,
        event_metadata=clean_meta,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(
        "Telemetry recorded: session=%s event=%s",
        session_record.session_uuid,
        event_type.value,
    )
    return event
