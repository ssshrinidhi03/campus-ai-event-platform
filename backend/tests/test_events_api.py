"""Tests for event discovery API (GET /api/v1/events)"""
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app
from app.db.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.event import Event
from app.core.security import get_password_hash
from app.models.enums import UserRole, EventStatus
from datetime import date, time

# Enable testing mode to disable rate limiting
settings.TESTING = True

client = TestClient(app)


def setup_module(module):
    """Create tables and seed test users and events."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Clean up
        db.query(Event).delete(synchronize_session=False)
        db.query(User).delete(synchronize_session=False)

        # Seed users
        users = [
            User(id=1, name="Student User", email="student@campus.edu",
                 password_hash=get_password_hash("student123"), role=UserRole.STUDENT,
                 roll_number="STU001", is_verified=True, is_identity_verified=False),
            User(id=2, name="AI Club", email="aiclub@campus.edu",
                 password_hash=get_password_hash("aiclub123"), role=UserRole.ORGANIZER,
                 is_verified=True, is_identity_verified=False),
            User(id=3, name="Coding Club", email="codingclub@campus.edu",
                 password_hash=get_password_hash("codingclub123"), role=UserRole.ORGANIZER,
                 is_verified=True, is_identity_verified=False),
        ]
        db.add_all(users)
        db.commit()

        # Seed events with various statuses
        events = [
            # APPROVED events (should be visible)
            Event(id=10, title="AI Workshop", description="Learn AI and ML",
                  category="Workshop", organizer_id=2, venue="Hall A",
                  date=date(2026, 10, 20), start_time=time(9, 0), end_time=time(17, 0),
                  status=EventStatus.APPROVED, tags="AI,ML"),
            Event(id=11, title="Cloud Seminar", description="Cloud computing overview",
                  category="Seminar", organizer_id=2, venue="Lab B",
                  date=date(2026, 11, 1), start_time=time(10, 0), end_time=time(12, 0),
                  status=EventStatus.APPROVED, tags="cloud"),
            Event(id=13, title="Transformer Workshop", description="Transformer architectures",
                  category="Workshop", organizer_id=3, venue="Lab 204",
                  date=date(2026, 11, 15), start_time=time(10, 0), end_time=time(16, 0),
                  status=EventStatus.APPROVED, tags="transformer,attention"),
            # Non-approved events (should NOT be visible)
            Event(id=20, title="Draft Event", description="A draft",
                  category="Workshop", organizer_id=2, venue="Room C",
                  date=date(2026, 12, 1), start_time=time(9, 0), end_time=time(11, 0),
                  status=EventStatus.DRAFT, tags="draft"),
            Event(id=21, title="Pending Approval Event", description="Pending",
                  category="Seminar", organizer_id=2, venue="Room D",
                  date=date(2026, 12, 2), start_time=time(9, 0), end_time=time(11, 0),
                  status=EventStatus.PENDING_APPROVAL, tags="pending"),
            Event(id=22, title="Rejected Event", description="Rejected",
                  category="Competition", organizer_id=3, venue="Room E",
                  date=date(2026, 12, 3), start_time=time(9, 0), end_time=time(11, 0),
                  status=EventStatus.REJECTED, tags="rejected"),
        ]
        db.add_all(events)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    pass


class TestEventListAPI:
    """Tests for the public event listing endpoint."""

    def test_returns_only_approved_events(self):
        """GET /api/v1/events returns only APPROVED events, not DRAFT/PENDING/REJECTED."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        approved_ids = {10, 11, 13}
        returned_ids = {e["id"] for e in data}
        assert returned_ids == approved_ids
        # All returned events should have APPROVED status
        for e in data:
            assert e["status"] == "APPROVED"

    def test_excludes_draft_events(self):
        """DRAFT events are not included in the public listing."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert not any(e["id"] == 20 for e in data)

    def test_excludes_pending_approval_events(self):
        """PENDING_APPROVAL events are not included in the public listing."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert not any(e["id"] == 21 for e in data)

    def test_excludes_rejected_events(self):
        """REJECTED events are not included in the public listing."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert not any(e["id"] == 22 for e in data)

    def test_search_filter_by_title(self):
        """Search query filters events by title."""
        response = client.get("/api/v1/events?q=Cloud")
        assert response.status_code == 200
        data = response.json()
        titles = {e["title"] for e in data}
        assert "Cloud Seminar" in titles
        assert "AI Workshop" not in titles
        assert "Transformer Workshop" not in titles

    def test_search_filter_by_description(self):
        """Search query filters events by description."""
        response = client.get("/api/v1/events?q=cloud")
        assert response.status_code == 200
        data = response.json()
        titles = {e["title"] for e in data}
        assert "Cloud Seminar" in titles

    def test_category_filter(self):
        """Category filter returns only events in that category."""
        response = client.get("/api/v1/events?category=Workshop")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # AI Workshop and Transformer Workshop
        for e in data:
            assert e["category"] == "Workshop"

    def test_category_filter_all_returns_all_approved(self):
        """Category 'All' returns all approved events."""
        response = client.get("/api/v1/events?category=All")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_response_includes_required_fields(self):
        """Each event response includes required fields."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        event = data[0]
        required_fields = ["id", "title", "description", "category", "venue",
                           "status", "organizer_id", "organizer_name", "tags"]
        for field in required_fields:
            assert field in event, f"Missing field: {field}"

    def test_no_approved_events_returns_empty_list(self):
        """When no approved events exist, returns empty list."""
        # This is tested implicitly - if we delete all approved events
        db = SessionLocal()
        try:
            db.query(Event).filter(Event.status == EventStatus.APPROVED).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

        response = client.get("/api/v1/events")
        assert response.status_code == 200
        assert response.json() == []
