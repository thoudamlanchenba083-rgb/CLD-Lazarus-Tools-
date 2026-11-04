"""Consent model — per-type, versioned, revocable consent records."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Boolean, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConsentType(str, enum.Enum):
    DEVICE_METADATA = "DEVICE_METADATA"
    CAMERA = "CAMERA"
    LOCATION = "LOCATION"
    SNAPSHOT_UPLOAD = "SNAPSHOT_UPLOAD"


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_type: Mapped[ConsentType] = mapped_column(
        Enum(ConsentType), nullable=False
    )
    consent_version: Mapped[int] = mapped_column(Integer, nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    session: Mapped["SessionRecord"] = relationship(
        "SessionRecord", back_populates="consents"
    )

    __table_args__ = (
        Index("ix_consents_session_type", "session_id", "consent_type"),
    )

    @property
    def is_active(self) -> bool:
        """Returns True if this consent is currently active (granted and not revoked)."""
        return self.granted and self.revoked_at is None
