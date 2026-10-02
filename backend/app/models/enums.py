import enum


class UserRole(str, enum.Enum):
    """
    User roles within the Campus AI Event Discovery Platform.
    - STUDENT: Default campus user discovering and registering for events.
    - ORGANIZER: Campus club/committee organizer who uploads event notices and drafts.
    - ADMIN: Campus authority moderating and approving published events.
    """
    STUDENT = "STUDENT"
    ORGANIZER = "ORGANIZER"
    ADMIN = "ADMIN"


class EventStatus(str, enum.Enum):
    """
    Lifecycle status of an event in the platform.
    - DRAFT: Initial event creation or AI draft undergoing organizer review.
    - PENDING_APPROVAL: Submitted by organizer, awaiting admin approval.
    - APPROVED: Verified by admin and visible on public discovery feed.
    - REJECTED: Denied by campus admin with feedback.
    - CANCELLED: Previously approved event marked cancelled by organizer/admin.
    """
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
