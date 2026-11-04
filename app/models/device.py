"""DeviceDetails model — parsed, validated device metadata per session."""
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceDetails(Base):
    __tablename__ = "device_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    browser: Mapped[str | None] = mapped_column(String(120), nullable=True)
    os: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    screen_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    screen_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    online: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(600), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    session: Mapped["SessionRecord"] = relationship(
        "SessionRecord", back_populates="device_details"
    )
