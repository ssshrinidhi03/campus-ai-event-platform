from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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

