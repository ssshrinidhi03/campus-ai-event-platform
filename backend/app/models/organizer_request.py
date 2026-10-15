from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import OrganizerRequestStatus

if TYPE_CHECKING:
    from app.models.user import User


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrganizerRequest(Base):
    __tablename__ = "organizer_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[OrganizerRequestStatus] = mapped_column(
        SQLEnum(OrganizerRequestStatus, native_enum=False),
        nullable=False,
        default=OrganizerRequestStatus.PENDING,
        index=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    admin_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
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

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    admin: Mapped[Optional["User"]] = relationship("User", foreign_keys=[admin_id])

    def __repr__(self) -> str:
        return f"<OrganizerRequest(id={self.id}, user_id={self.user_id}, status='{self.status}')>"
