"""CameraEvent model — permission and capture event log."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CameraEventType(str, enum.Enum):
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PREVIEW_STARTED = "PREVIEW_STARTED"
    PREVIEW_STOPPED = "PREVIEW_STOPPED"
    SNAPSHOT_CAPTURED = "SNAPSHOT_CAPTURED"
    SNAPSHOT_UPLOADED = "SNAPSHOT_UPLOADED"


class CameraEvent(Base):
    __tablename__ = "camera_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[CameraEventType] = mapped_column(
        Enum(CameraEventType), nullable=False, index=True
    )
    consent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("consents.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    session: Mapped["SessionRecord"] = relationship(
        "SessionRecord", back_populates="camera_events"
    )
