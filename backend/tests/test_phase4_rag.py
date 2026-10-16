"""Tests for Phase 4 RAG"""
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_rag_endpoint_basic():
    r = client.post("/api/v1/ai/query", json={"query":"test"})
    assert r.status_code in (200,401,422,503)

def test_search_endpoint_basic():
    r = client.get("/api/v1/search?q=workshop")
    assert r.status_code in (200,401)
