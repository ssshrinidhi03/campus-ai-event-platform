from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import UserRole
from app.core.password import get_password_hash, verify_password

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.registration import EventRegistration
    from app.models.saved_event import SavedEvent


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    User model representing platform users (Students, Organizers, Administrators).
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False),
        nullable=False,
        default=UserRole.STUDENT,
    )
    roll_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True, nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_identity_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    verification_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reset_token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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
    organized_events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="organizer",
        cascade="all, delete-orphan",
    )
    registrations: Mapped[List["EventRegistration"]] = relationship(
        "EventRegistration",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    saved_events: Mapped[List["SavedEvent"]] = relationship(
        "SavedEvent",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def events(self) -> List["Event"]:
        """Convenience alias for events organized by this user."""
        return self.organized_events

    def set_verification_token(self, token: str, expires_hours: int = 24) -> None:
        """Set verification token (stored as hash) with expiration."""
        from datetime import timedelta
        self.verification_token_hash = get_password_hash(token)
        self.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

    def verify_verification_token(self, token: str) -> bool:
        """Verify a verification token against stored hash."""
        if not self.verification_token_hash or not self.verification_token_expires:
            return False
        expires = self.verification_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return False
        return verify_password(token, self.verification_token_hash)

    def clear_verification_token(self) -> None:
        """Clear verification token after successful verification."""
        self.verification_token_hash = None
        self.verification_token_expires = None

    def set_reset_token(self, token: str, expires_hours: int = 1) -> None:
        """Set password reset token (stored as hash) with expiration."""
        from datetime import timedelta
        self.reset_token_hash = get_password_hash(token)
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

    def verify_reset_token(self, token: str) -> bool:
        """Verify a password reset token against stored hash."""
        if not self.reset_token_hash or not self.reset_token_expires:
            return False
        expires = self.reset_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return False
        return verify_password(token, self.reset_token_hash)

    def clear_reset_token(self) -> None:
        """Clear password reset token after successful reset."""
        self.reset_token_hash = None
        self.reset_token_expires = None

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}', role='{self.role}', roll_number='{self.roll_number}', verified={self.is_verified}, identity_verified={self.is_identity_verified})>"
