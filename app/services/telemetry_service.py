"""Telemetry service — single unified entry point for logging all lifecycle and consent events."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.session import SessionRecord
from app.models.telemetry_event import TelemetryEvent, TelemetryEventType
from app.websocket.manager import manager

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
    """Record a validated telemetry event for a session and broadcast minimal summary to admins."""
    clean_meta = sanitize_metadata(metadata)
    now = datetime.now(timezone.utc)
    event = TelemetryEvent(
        session_id=session_record.id,
        event_type=event_type,
        event_metadata=clean_meta,
        recorded_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(
        "Telemetry recorded: session=%s event=%s",
        session_record.session_uuid,
        event_type.value,
    )

    # Broadcast minimal summary event to connected admins (no sensitive info)
    summary_message = {
        "event_uuid": event.event_uuid,
        "session_uuid": session_record.session_uuid,
        "event_type": event_type.value,
        "status": session_record.status.value,
        "recorded_at": now.isoformat(),
        "summary": clean_meta,
    }

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast(summary_message))
    except RuntimeError:
        # If no active event loop in thread, schedule or skip broadcast cleanly
        pass

    return event
