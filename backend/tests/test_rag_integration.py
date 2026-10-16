"""Integration tests for RAG endpoints"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_search_endpoint_exists():
    r = client.get('/api/v1/search?q=test')
    assert r.status_code in (200, 401)  # may require auth or not
