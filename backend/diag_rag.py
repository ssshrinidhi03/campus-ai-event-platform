"""Diagnose RAG retrieval relevance - log scores for various queries."""
import asyncio, sys, json
sys.path.insert(0, '.')
from app.services.vector_store import SimpleVectorStore
from app.db.database import SessionLocal
from app.models.event import Event
from app.models.enums import EventStatus

async def diagnose():
    db = SessionLocal()
    vs = SimpleVectorStore()
    
    print("=== VECTOR STORE STATS ===")
    print(f"Total embeddings: {len(vs.embeddings)}")
    for eid, emb in vs.embeddings.items():
        print(f"  Event {eid}: {emb.title[:50]}... | emb_dim={len(emb.embedding)} | first5={emb.embedding[:5]}")
    
    print("\n=== DB EVENTS ===")
    events = db.query(Event).filter(Event.status == EventStatus.APPROVED).all()
    for e in events:
        print(f"  Event {e.id}: {e.title} | category={e.category} | venue={e.venue}")
    
    print("\n=== SIMILARITY SCORES FOR VARIOUS QUERIES ===")
    queries = [
        "cloud computing",
        "AWS Azure seminar",
        "transformer architectures",
        "AI workshop",
        "machine learning",
        "coding competition",
        "quantum physics",
        "basketball tournament",
    ]
    
    for q in queries:
        print(f"\n--- Query: '{q}' ---")
        results = await vs.search(q, limit=10)
        if not results:
            print("  No results (above threshold)")
            continue
        for emb, score in results:
            print(f"  Event {emb.event_id}: {emb.title[:50]}... | score={score:.4f}")
    
    print("\n=== SCORE DISTRIBUTION (all pairs) ===")
    # Generate query embedding for "cloud computing" and compare with all events
    qe = await vs._gen("cloud computing")
    print(f"Query 'cloud computing' embedding first 5: {qe[:5] if qe else 'EMPTY'}")
    for eid, emb in vs.embeddings.items():
        s = vs._cosine(qe, emb.embedding)
        print(f"  vs Event {eid} ({emb.title[:40]}): score={s:.4f}")
    
    db.close()

asyncio.run(diagnose())
