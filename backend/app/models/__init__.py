"""
Database Models Package.

Exports all SQLAlchemy 2.0 entity models and enums:
- UserRole: Enumeration of roles (STUDENT, ORGANIZER, ADMIN)
- EventStatus: Lifecycle states (DRAFT, PENDING_APPROVAL, APPROVED, REJECTED, CANCELLED)
- User: Platform user entity
- Event: Campus event entity
- EventRegistration: Unique user registration per event
- Document: Uploaded event notices/flyers
- EventSource: Provenance tracking for AI-extracted fields
"""

from app.db.database import Base
from app.models.enums import UserRole, EventStatus
from app.models.user import User
from app.models.event import Event
from app.models.registration import EventRegistration
from app.models.document import Document
from app.models.source import EventSource

__all__ = [
    "Base",
    "UserRole",
    "EventStatus",
    "User",
    "Event",
    "EventRegistration",
    "Document",
    "EventSource",
]
