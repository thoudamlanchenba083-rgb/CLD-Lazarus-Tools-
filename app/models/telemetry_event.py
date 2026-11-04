"""TelemetryEvent model — consistent event log with validated types and sanitized metadata."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Enum, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TelemetryEventType(str, enum.Enum):
    SESSION_CREATED = "SESSION_CREATED"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CAMERA_PERMISSION_GRANTED = "CAMERA_PERMISSION_GRANTED"
    CAMERA_PERMISSION_DENIED = "CAMERA_PERMISSION_DENIED"
    LOCATION_PERMISSION_GRANTED = "LOCATION_PERMISSION_GRANTED"
    LOCATION_UPDATE_RECEIVED = "LOCATION_UPDATE_RECEIVED"
    DEVICE_METADATA_RECEIVED = "DEVICE_METADATA_RECEIVED"
    SESSION_ENDED = "SESSION_ENDED"


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[TelemetryEventType] = mapped_column(
        Enum(TelemetryEventType), nullable=False, index=True
    )
    event_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    session: Mapped["SessionRecord"] = relationship(
        "SessionRecord", back_populates="telemetry_events"
    )
