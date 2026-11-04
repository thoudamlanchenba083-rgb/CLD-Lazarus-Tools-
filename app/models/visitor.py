"""Visitor model — an anonymous, random-UUID-identified visitor."""
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Visitor(Base):
    __tablename__ = "visitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visitor_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    sessions: Mapped[list["SessionRecord"]] = relationship(
        "SessionRecord", back_populates="visitor", cascade="all, delete-orphan"
    )
