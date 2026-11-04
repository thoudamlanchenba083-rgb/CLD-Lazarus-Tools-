"""Session model — an anonymous, expiring session linked to a visitor."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    EXPIRED = "EXPIRED"


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    # Token for session ownership verification (random, unguessable)
    session_token: Mapped[str] = mapped_column(String(64), nullable=False)
    visitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    visitor: Mapped["Visitor"] = relationship("Visitor", back_populates="sessions")
    consents: Mapped[list["Consent"]] = relationship(
        "Consent", back_populates="session", cascade="all, delete-orphan"
    )
    device_details: Mapped[list["DeviceDetails"]] = relationship(
        "DeviceDetails", back_populates="session", cascade="all, delete-orphan"
    )
    location_updates: Mapped[list["LocationUpdate"]] = relationship(
        "LocationUpdate", back_populates="session", cascade="all, delete-orphan"
    )
    camera_events: Mapped[list["CameraEvent"]] = relationship(
        "CameraEvent", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sessions_status", "status"),
    )
