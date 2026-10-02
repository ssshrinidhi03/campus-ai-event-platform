from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.document import Document


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class EventSource(Base):
    """
    EventSource model representing AI-extracted evidence/provenance metadata.
    Stores the exact field name, extracted value, source document reference, page number,
    and excerpt of source text that justified the AI extraction.
    """
    __tablename__ = "event_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    extracted_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        server_default=func.now(),
    )

    # Relationships
    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="sources",
    )
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="sources",
    )

    def __repr__(self) -> str:
        return (
            f"<EventSource(id={self.id}, field='{self.field_name}', "
            f"event_id={self.event_id}, document_id={self.document_id})>"
        )
