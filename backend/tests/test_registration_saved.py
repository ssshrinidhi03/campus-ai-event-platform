"""Tests for event registration and saved events features"""
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app
from app.db.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.event import Event
from app.models.registration import EventRegistration
from app.models.saved_event import SavedEvent
from app.core.security import get_password_hash
from app.models.enums import UserRole, EventStatus
from datetime import date, time

# Enable testing mode
settings.TESTING = True

client = TestClient(app)


def setup_module(module):
    """Create tables and seed test data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(EventRegistration).delete(synchronize_session=False)
        db.query(SavedEvent).delete(synchronize_session=False)
        db.query(Event).delete(synchronize_session=False)
        db.query(User).delete(synchronize_session=False)

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
            User(id=4, name="Other Student", email="other@campus.edu",
                 password_hash=get_password_hash("other123"), role=UserRole.STUDENT,
                 roll_number="STU002", is_verified=True, is_identity_verified=False),
        ]
        db.add_all(users)
        db.commit()

        events = [
            Event(id=10, title="AI Workshop", description="Learn AI", category="Workshop",
                  organizer_id=2, venue="Hall A", date=date(2026, 10, 20),
                  start_time=time(9, 0), end_time=time(17, 0),
                  status=EventStatus.APPROVED, tags="AI,ML"),
            Event(id=11, title="Cloud Seminar", description="Cloud computing", category="Seminar",
                  organizer_id=2, venue="Lab B", date=date(2026, 11, 1),
                  start_time=time(10, 0), end_time=time(12, 0),
                  status=EventStatus.APPROVED, tags="cloud"),
            Event(id=12, title="Draft Event", description="Not published", category="Workshop",
                  organizer_id=2, venue="Room C", date=date(2026, 12, 1),
                  start_time=time(9, 0), end_time=time(11, 0),
                  status=EventStatus.DRAFT, tags="draft"),
        ]
        db.add_all(events)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    pass


class TestUserRegistration:
    """Test student registration flow."""

    def test_register_for_approved_event(self):
        """Student can register for an approved event."""
        # Login as student
        r = client.post("/api/v1/auth/login", json={
            "email": "student@campus.edu", "password": "student123"
        })
        assert r.status_code == 200
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Register for event 10
        r = client.post(
            "/api/v1/events/10/register",
            headers=headers,
            json={"name": "Student User", "email": "student@campus.edu", "college": "CS"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "Registration successful"
        assert "registration_id" in data

    def test_duplicate_registration_rejected(self):
        """Student cannot register twice for same event."""
        r = client.post("/api/v1/auth/login", json={
            "email": "student@campus.edu", "password": "student123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(
            "/api/v1/events/10/register",
            headers=headers,
            json={"name": "Student User", "email": "student@campus.edu", "college": "CS"}
        )
        assert r.status_code == 400
        assert "already" in r.json()["detail"].lower()

    def test_list_user_registrations(self):
        """Student can list their own registrations."""
        r = client.post("/api/v1/auth/login", json={
            "email": "student@campus.edu", "password": "student123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/registrations", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["event_id"] == 10
        assert data[0]["event_title"] == "AI Workshop"
        assert data[0]["status"] == "REGISTERED"

    def test_registration_list_excludes_other_students(self):
        """One student cannot see another student's registrations."""
        r = client.post("/api/v1/auth/login", json={
            "email": "other@campus.edu", "password": "other123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/registrations", headers=headers)
        assert r.status_code == 200
        data = r.json()
        # Other student has no registrations
        assert len(data) == 0


class TestRegistrationAuthorization:
    """Test registration access control."""

    def test_unauthenticated_cannot_register(self):
        """Unauthenticated users cannot register."""
        r = client.post(
            "/api/v1/events/10/register",
            json={"name": "X", "email": "x@y.com", "college": "CS"}
        )
        assert r.status_code == 401

    def test_register_nonexistent_event(self):
        """Registering for nonexistent event returns 404."""
        r = client.post("/api/v1/auth/login", json={
            "email": "student@campus.edu", "password": "student123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(
            "/api/v1/events/9999/register",
            headers=headers,
            json={"name": "Student User", "email": "student@campus.edu", "college": "CS"}
        )
        assert r.status_code == 404


class TestSavedEvents:
    """Test saved events flow."""

    def test_save_event(self):
        """Student can save an approved event."""
        r = client.post("/api/v1/auth/login", json={
            "email": "student@campus.edu", "password": "student123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(f"/api/v1/events/10/save", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["event_id"] == 10
        assert data["user_id"] == 1

    def test_duplicate_save_rejected(self):
        """Student cannot save same event twice."""
        r = client.post("/api/v1/auth/login", json={
            "email": "student@campus.edu", "password": "student123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(f"/api/v1/events/10/save", headers=headers)
        assert r.status_code == 400

    def test_list_saved_events(self):
        """Student can list their saved events."""
        r = client.post("/api/v1/auth/login", json={
            "email": "student@campus.edu", "password": "student123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/saved-events", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["event_id"] == 10
        assert data[0]["event_title"] == "AI Workshop"

    def test_saved_events_exclude_other_students(self):
        """One student cannot see another student's saved events."""
        r = client.post("/api/v1/auth/login", json={
            "email": "other@campus.edu", "password": "other123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/saved-events", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 0

    def test_unsave_event(self):
        """Student can remove a saved event."""
        r = client.post("/api/v1/auth/login", json={
            "email": "student@campus.edu", "password": "student123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.delete(f"/api/v1/events/10/save", headers=headers)
        assert r.status_code == 200

        # Verify it's removed
        r = client.get("/api/v1/saved-events", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 0


class TestOrganizerRegistrations:
    """Test organizer viewing registrations for their events."""

    def test_organizer_event_detail_includes_registrations(self):
        """Organizer can view registrations for their own event."""
        r = client.post("/api/v1/auth/login", json={
            "email": "aiclub@campus.edu", "password": "aiclub123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/organizer/events/10", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "registrations" in data
        # Student registered for event 10
        assert len(data["registrations"]) == 1
        assert data["registrations"][0]["user_name"] == "Student User"

    def test_organizer_cannot_view_other_organizers_event(self):
        """Organizer cannot view another organizer's event registrations."""
        # Event 11 belongs to AI Club (user 2), login as Coding Club
        r = client.post("/api/v1/auth/login", json={
            "email": "codingclub@campus.edu", "password": "codingclub123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/organizer/events/10", headers=headers)
        assert r.status_code == 404

    def test_organizer_events_list_registration_count(self):
        """Organizer events list includes registration count."""
        r = client.post("/api/v1/auth/login", json={
            "email": "aiclub@campus.edu", "password": "aiclub123"
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get("/api/v1/organizer/events", headers=headers)
        assert r.status_code == 200
        data = r.json()
        event_10 = next(e for e in data if e["id"] == 10)
        assert event_10["registration_count"] == 1
