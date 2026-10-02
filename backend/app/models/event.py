from datetime import datetime, date, time, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Date, Time, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import EventStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.registration import EventRegistration
    from app.models.document import Document
    from app.models.source import EventSource


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Event(Base):
    """
    Event model representing campus workshops, seminars, competitions, and gatherings.
    """
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    organizer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    eligibility: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    registration_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        SQLEnum(EventStatus, native_enum=False),
        nullable=False,
        default=EventStatus.DRAFT,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        onupdate=get_utc_now,
        server_default=func.now(),
    )

    # Relationships
    organizer: Mapped["User"] = relationship(
        "User",
        back_populates="organized_events",
    )
    registrations: Mapped[List["EventRegistration"]] = relationship(
        "EventRegistration",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    sources: Mapped[List["EventSource"]] = relationship(
        "EventSource",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title='{self.title}', status='{self.status}')>"
