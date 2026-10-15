from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.user import User


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class SavedEvent(Base):
    """
    SavedEvent model representing a user's saved/bookmarked event.
    Enforces a database-level uniqueness constraint preventing duplicate saves.
    """
    __tablename__ = "saved_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        server_default=func.now(),
    )

    # Database-level uniqueness constraint to prevent duplicate saves
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_saved_event_event_user"),
    )

    # Relationships
    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="saved_by_users",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="saved_events",
    )

    def __repr__(self) -> str:
        return f"<SavedEvent(id={self.id}, event_id={self.event_id}, user_id={self.user_id})>"