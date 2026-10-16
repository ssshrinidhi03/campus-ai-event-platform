"""Search API endpoints for semantic search"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.services.vector_store import SimpleVectorStore
from app.models.event import Event
from app.schemas.ai import RagQueryRequest, RagQueryResponse, RagEventResult
from app.services.ai import get_ai_provider, AiProviderError
router = APIRouter(prefix="/search", tags=["Search"])

# Global vector store instance
_vector_store = None

def get_vector_store() -> SimpleVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = SimpleVectorStore()
    return _vector_store

@router.get("/")
async def semantic_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    vs = get_vector_store()
    results = await vs.search(q, limit=limit, filters={"category": category} if category else None)
    events = []
    for emb, score in results:
        ev = db.query(Event).filter(Event.id == emb.event_id).first()
        if ev:
            events.append({
                "id": ev.id,
                "title": ev.title,
                "description": ev.description,
                "category": ev.category,
                "venue": ev.venue,
                "date": ev.date.isoformat() if ev.date else None,
                "tags": emb.tags,
                "relevance_score": float(score),
            })
    return {"query": q, "results": events, "total": len(events)}

@router.post("/reindex")
async def reindex(db: Session = Depends(get_db)):
    vs = get_vector_store()
    stats = await vs.reindex_all(db)
    return {"message": "Reindex completed", "stats": stats}

@router.get("/stats")
async def search_stats():
    vs = get_vector_store()
    return vs.get_stats()
