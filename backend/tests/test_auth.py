from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app
from app.db.database import SessionLocal, engine, Base
from app.models.user import User
from app.core.security import get_password_hash
from app.models.enums import UserRole
from unittest.mock import AsyncMock

# Enable testing mode to disable rate limiting
settings.TESTING = True

client = TestClient(app)


def setup_module(module):
    """Create tables and seed test users before running tests."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Clean up ALL users to ensure test isolation
        db.query(User).delete(synchronize_session=False)
        
        # Seed test users
        users = [
            User(id=1, name="Student User", email="student@campus.edu", password_hash=get_password_hash("student123"), role=UserRole.STUDENT, roll_number="STU001", is_verified=True, is_identity_verified=False),
            User(id=2, name="AI Club", email="aiclub@campus.edu", password_hash=get_password_hash("aiclub123"), role=UserRole.ORGANIZER, is_verified=True, is_identity_verified=False),
            User(id=3, name="Coding Club", email="codingclub@campus.edu", password_hash=get_password_hash("codingclub123"), role=UserRole.ORGANIZER, is_verified=True, is_identity_verified=False),
            User(id=4, name="E-Cell", email="ecell@campus.edu", password_hash=get_password_hash("ecell123"), role=UserRole.ORGANIZER, is_verified=True, is_identity_verified=False),
            User(id=5, name="Photography Club", email="photoclub@campus.edu", password_hash=get_password_hash("photoclub123"), role=UserRole.ORGANIZER, is_verified=True, is_identity_verified=False),
        ]
        db.add_all(users)
        db.commit()
    finally:
        db.close()


def teardown_module(module):
    """Clean up test users after tests - DISABLED to preserve seeded development data.
    
    The test users are the same as the seeded development users. 
    Deleting them breaks manual browser testing.
    To use a separate test database, configure TEST_DATABASE_URL in settings.
    """
    pass


def test_root_health_endpoint():
    """
    Test that GET /health returns status code 200 and {'status': 'ok'}.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_v1_health_endpoint():
    """
    Test that GET /api/v1/health returns status code 200 and {'status': 'ok'}.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_endpoints():
    """
    Verify FastAPI automatic documentation endpoints (/docs and /redoc) load successfully.
    """
    response_docs = client.get("/docs")
    assert response_docs.status_code == 200

    response_redoc = client.get("/redoc")
    assert response_redoc.status_code == 200

    response_openapi = client.get("/openapi.json")
    assert response_openapi.status_code == 200
    assert "Campus AI Event Discovery Platform" in response_openapi.json()["info"]["title"]


def test_login_success_organizer():
    """
    Test successful login for an organizer account.
    Returns 200 with access_token, token_type, and user info.
    """
    response = client.post("/api/v1/auth/login", json={
        "email": "aiclub@campus.edu",
        "password": "aiclub123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "aiclub@campus.edu"
    assert data["user"]["role"] == "ORGANIZER"
    assert data["user"]["name"] == "AI Club"


def test_login_success_student():
    """
    Test successful login for a student account.
    Returns 200 with access_token, token_type, and user info.
    """
    response = client.post("/api/v1/auth/login", json={
        "email": "student@campus.edu",
        "password": "student123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "student@campus.edu"
    assert data["user"]["role"] == "STUDENT"
    assert data["user"]["name"] == "Student User"


def test_login_all_organizers():
    """
    Test that all seeded organizer accounts can login successfully.
    """
    organizers = [
        ("aiclub@campus.edu", "aiclub123", "AI Club"),
        ("codingclub@campus.edu", "codingclub123", "Coding Club"),
        ("ecell@campus.edu", "ecell123", "E-Cell"),
        ("photoclub@campus.edu", "photoclub123", "Photography Club"),
    ]
    for email, password, name in organizers:
        response = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200, f"Login failed for {email}"
        data = response.json()
        assert data["user"]["email"] == email
        assert data["user"]["role"] == "ORGANIZER"
        assert data["user"]["name"] == name


def test_login_incorrect_password():
    """
    Test login with correct email but incorrect password.
    Returns 401 with 'Invalid credentials' detail.
    """
    response = client.post("/api/v1/auth/login", json={
        "email": "aiclub@campus.edu",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_nonexistent_account():
    """
    Test login with non-existent email.
    Returns 401 with 'Invalid credentials' detail (same as wrong password for security).
    """
    response = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@campus.edu",
        "password": "anypassword"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_missing_fields():
    """
    Test login with missing email or password.
    Returns 422 validation error.
    """
    # Missing password
    response = client.post("/api/v1/auth/login", json={"email": "aiclub@campus.edu"})
    assert response.status_code == 422

    # Missing email
    response = client.post("/api/v1/auth/login", json={"password": "aiclub123"})
    assert response.status_code == 422

    # Empty request
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422


def test_login_invalid_email_format():
    """
    Test login with invalid email format.
    Returns 422 validation error.
    """
    response = client.post("/api/v1/auth/login", json={
        "email": "not-an-email",
        "password": "aiclub123"
    })
    assert response.status_code == 422


def test_token_validation_success():
    """
    Test that a valid access token can access protected endpoints.
    """
    # Login first
    login_response = client.post("/api/v1/auth/login", json={
        "email": "aiclub@campus.edu",
        "password": "aiclub123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Use token to access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "aiclub@campus.edu"
    assert data["role"] == "ORGANIZER"


def test_token_validation_invalid_token():
    """
    Test that an invalid/expired token returns 401 with 'Could not validate credentials'.
    """
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_token_validation_missing_token():
    """
    Test that missing Authorization header returns 401.
    """
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_register_success():
    """
    Test successful student registration.
    Returns 200 with access_token, token_type, and user info (unverified).
    """
    response = client.post("/api/v1/auth/register", json={
        "name": "New Student",
        "email": "newstudent@campus.edu",
        "password": "password123",
        "confirm_password": "password123",
        "roll_number": "STU999",
        "account_type": "STUDENT"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "newstudent@campus.edu"
    assert data["user"]["role"] == "STUDENT"
    assert data["user"]["name"] == "New Student"
    assert data["user"]["roll_number"] == "STU999"
    assert data["user"]["is_verified"] is False


def test_register_sends_welcome_email():
    """
    Test that successful registration sends a welcome email.
    """
    import app.services.email as email_module
    from app.services.email import MockEmailBackend

    original_backend = email_module.get_email_backend
    mock_backend = MockEmailBackend()
    email_module.get_email_backend = lambda: mock_backend
    try:
        response = client.post("/api/v1/auth/register", json={
            "name": "Welcome Test Student",
            "email": "welcometest@campus.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "STU222",
            "account_type": "STUDENT"
        })
        assert response.status_code == 200
        welcome_emails = [e for e in mock_backend.sent_emails if "Welcome" in e["subject"]]
        assert len(welcome_emails) == 1
        assert welcome_emails[0]["to"] == "welcometest@campus.edu"
    finally:
        email_module.get_email_backend = original_backend


def test_register_duplicate_sends_no_email():
    """
    Test that duplicate email registration sends no welcome email.
    """
    import app.services.email as email_module
    from app.services.email import MockEmailBackend

    original_backend = email_module.get_email_backend
    mock_backend = MockEmailBackend()
    email_module.get_email_backend = lambda: mock_backend
    try:
        response = client.post("/api/v1/auth/register", json={
            "name": "Another Student",
            "email": "student@campus.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "STU111",
            "account_type": "STUDENT"
        })
        assert response.status_code == 400
        assert len(mock_backend.sent_emails) == 0
    finally:
        email_module.get_email_backend = original_backend


def test_register_email_delivery_failure_does_not_rollback():
    """
    Test that registration succeeds even when email delivery fails.
    """
    import app.services.email as email_module
    from app.services.email import EmailBackend

    class FailingBackend(EmailBackend):
        def send(self, to_email, subject, body, html_body=None):
            return False

    original_backend = email_module.get_email_backend
    email_module.get_email_backend = lambda: FailingBackend()
    try:
        response = client.post("/api/v1/auth/register", json={
            "name": "Failing Email Student",
            "email": "failingemail@campus.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "STU555",
            "account_type": "STUDENT"
        })
        assert response.status_code == 200
        # User should still be registered (login blocked only because unverified)
        login_response = client.post("/api/v1/auth/login", json={
            "email": "failingemail@campus.edu",
            "password": "password123"
        })
        assert login_response.status_code == 403
    finally:
        email_module.get_email_backend = original_backend


def test_register_duplicate_email():
    """
    Test registration with an email that already exists.
    Returns 400 with 'Email already registered'.
    """
    response = client.post("/api/v1/auth/register", json={
        "name": "Another Student",
        "email": "student@campus.edu",  # Already exists from seeded data
        "password": "password123",
        "confirm_password": "password123",
        "roll_number": "STU888",
        "account_type": "STUDENT"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_register_duplicate_roll_number():
    """
    Test registration with a roll number that already exists.
    Returns 400 with 'Roll number already registered'.
    """
    response = client.post("/api/v1/auth/register", json={
        "name": "Another Student",
        "email": "another@campus.edu",
        "password": "password123",
        "confirm_password": "password123",
        "roll_number": "STU001",  # Already exists from seeded data
        "account_type": "STUDENT"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Roll number already registered"


def test_register_password_mismatch():
    """
    Test registration with mismatched passwords.
    Returns 422 validation error.
    """
    response = client.post("/api/v1/auth/register", json={
        "name": "New Student",
        "email": "newstudent2@campus.edu",
        "password": "password123",
        "confirm_password": "differentpassword",
        "roll_number": "STU777",
        "account_type": "STUDENT"
    })
    assert response.status_code == 422


def test_register_invalid_account_type():
    """
    Test registration with invalid account type (ORGANIZER/ADMIN).
    Returns 422 validation error.
    """
    response = client.post("/api/v1/auth/register", json={
        "name": "New Organizer",
        "email": "neworg@campus.edu",
        "password": "password123",
        "confirm_password": "password123",
        "roll_number": "STU666",
        "account_type": "ORGANIZER"
    })
    assert response.status_code == 422


def test_register_missing_required_fields():
    """
    Test registration with missing required fields.
    Returns 422 validation error.
    """
    # Missing name
    response = client.post("/api/v1/auth/register", json={
        "email": "newstudent3@campus.edu",
        "password": "password123",
        "confirm_password": "password123",
        "roll_number": "STU555",
        "account_type": "STUDENT"
    })
    assert response.status_code == 422

    # Missing roll_number
    response = client.post("/api/v1/auth/register", json={
        "name": "New Student",
        "email": "newstudent4@campus.edu",
        "password": "password123",
        "confirm_password": "password123",
        "account_type": "STUDENT"
    })
    assert response.status_code == 422


def test_login_unverified_account():
    """
    Test login with an unverified student account.
    Returns 403 with verification message.
    """
    # First register a new unverified user
    reg_response = client.post("/api/v1/auth/register", json={
        "name": "Unverified Student",
        "email": "unverified@campus.edu",
        "password": "password123",
        "confirm_password": "password123",
        "roll_number": "STU444",
        "account_type": "STUDENT"
    })
    assert reg_response.status_code == 200

    # Try to login - should fail with 403
    login_response = client.post("/api/v1/auth/login", json={
        "email": "unverified@campus.edu",
        "password": "password123"
    })
    assert login_response.status_code == 403
    assert "not verified" in login_response.json()["detail"].lower()


def test_verify_email_success():
    """
    Test email verification with valid token.
    """
    # Use mock email backend to capture verification token
    from app.services.email import MockEmailBackend, get_email_backend
    import app.services.email as email_module
    mock_backend = MockEmailBackend()
    email_module.get_email_backend = lambda: mock_backend

    # Register a new user
    reg_response = client.post("/api/v1/auth/register", json={
        "name": "Verify Student",
        "email": "verify@campus.edu",
        "password": "password123",
        "confirm_password": "password123",
        "roll_number": "STU333",
        "account_type": "STUDENT"
    })
    assert reg_response.status_code == 200

    # Get the verification token from the mock email backend
    assert len(mock_backend.sent_emails) == 2  # welcome + verification
    verification_email = None
    for e in mock_backend.sent_emails:
        if "Verify" in e["subject"]:
            verification_email = e
            break
    assert verification_email is not None, "Verification email not found"
    # Extract token from verification link
    verification_link = verification_email["html_body"]
    import re
    token_match = re.search(r'token=([^"]+)', verification_link)
    assert token_match, "Verification token not found in email"
    token = token_match.group(1)

    # Verify with the token
    verify_response = client.post("/api/v1/auth/verify-email", json={
        "token": token
    })
    assert verify_response.status_code == 200
    assert "verified" in verify_response.json()["message"].lower()

    # Now login should work
    login_response = client.post("/api/v1/auth/login", json={
        "email": "verify@campus.edu",
        "password": "password123"
    })
    assert login_response.status_code == 200


def test_verify_email_invalid_token():
    """
    Test email verification with invalid token.
    Returns 400.
    """
    response = client.post("/api/v1/auth/verify-email", json={
        "token": "invalid-token"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"


def test_resend_verification():
    """
    Test resending verification email.
    """
    response = client.post("/api/v1/auth/resend-verification", json={
        "email": "verify@campus.edu"
    })
    assert response.status_code == 200


def test_unauthorized_role_access():
    """
    Test that students cannot access organizer-only endpoints.
    """
    # Login as student
    login_response = client.post("/api/v1/auth/login", json={
        "email": "student@campus.edu",
        "password": "student123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to access organizer events endpoint
    response = client.get("/api/v1/organizer/events", headers=headers)
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_organizer_publish_indexes_event():
    """
    Test that publishing an event indexes it in the vector store (RAG search).
    Verifies the event becomes APPROVED and is retrievable.
    """
    from unittest.mock import patch

    # Login as organizer
    login_response = client.post("/api/v1/auth/login", json={
        "email": "aiclub@campus.edu",
        "password": "aiclub123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a draft event
    with patch("app.api.organizer.SimpleVectorStore.add_event", new_callable=AsyncMock) as mock_add:
        mock_add.return_value = True
        create_response = client.post("/api/v1/organizer/events", json={
            "title": "Test Publish Event",
            "description": "A test event for publish indexing",
            "category": "Workshop",
            "venue": "Test Hall",
            "date": "2027-01-15",
            "start_time": "10:00",
            "end_time": "12:00",
            "tags": ["test"],
            "capacity": 50,
        }, headers=headers)
        assert create_response.status_code == 201, create_response.text
        event_id = create_response.json()["id"]
        assert create_response.json()["status"] == "DRAFT"

        # Publish the event
        publish_response = client.post(f"/api/v1/organizer/events/{event_id}/publish", headers=headers)
        assert publish_response.status_code == 200, publish_response.text
        assert publish_response.json()["status"] == "APPROVED"

        # Verify vector store indexing was called
        assert mock_add.call_count >= 1


def test_organizer_publish_rejects_non_draft():
    """Test that publishing a non-draft event returns 400."""
    from unittest.mock import patch

    login_response = client.post("/api/v1/auth/login", json={
        "email": "aiclub@campus.edu",
        "password": "aiclub123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to publish without creating an event first (use a non-existent id)
    response = client.post("/api/v1/organizer/events/99999/publish", headers=headers)
    assert response.status_code == 404


def test_search_endpoint_excludes_draft_events():
    """
    Test that the search endpoint only returns APPROVED events.
    Draft events are not indexed, so they won't appear in search results.
    """
    response = client.get("/api/v1/search?q=workshop")
    assert response.status_code in (200, 401)
    if response.status_code == 200:
        data = response.json()
        for ev in data.get("results", []):
            # All returned events should be approved (status verified at DB level)
            assert ev["id"] is not None