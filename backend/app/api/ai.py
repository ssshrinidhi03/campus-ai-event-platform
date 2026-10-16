"""
AI API Routes
Endpoints for AI-powered event extraction and RAG queries.
"""

import base64
import time
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.db.database import get_db
from app.core.security import get_current_user, require_organizer
from app.schemas.ai import (
    EventExtractionRequest,
    EventExtractionResponse,
    RagQueryRequest,
    RagQueryResponse,
    AiHealthResponse,
)
from app.services.ai import (
    get_ai_provider, AiProviderError, AiProviderUnavailableError, AiProviderValidationError,
    create_agent,
)
from app.services.vector_store import SimpleVectorStore
from app.models.user import User
from app.models.event import Event
from app.models.enums import EventStatus

router = APIRouter(prefix="/ai", tags=["AI"])

# Allowed image MIME types and max size (5MB)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image_file(file: UploadFile) -> bytes:
    """Validate uploaded image file and return its content as bytes."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    content = file.file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum size: {MAX_IMAGE_SIZE // (1024*1024)}MB"
        )
    
    # Reset file pointer for potential re-reading
    file.file.seek(0)
    return content


@router.post("/extract-event", response_model=EventExtractionResponse)
async def extract_event(
    request: EventExtractionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Extract structured event data from text announcement or poster image.
    
    - **text**: Raw text announcement (optional if image provided)
    - **image_base64**: Base64 encoded poster image (optional if text provided)
    - **image_mime_type**: MIME type of the image
    
    Returns extracted event fields with confidence score and warnings for missing data.
    """
    if not request.text and not request.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'image_base64' must be provided"
        )

    provider = get_ai_provider()
    
    try:
        result = await provider.extract_event(request)
        return result
    except AiProviderUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except AiProviderValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except AiProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Event extraction failed: {str(e)}"
        )


@router.post("/extract-event-upload", response_model=EventExtractionResponse)
async def extract_event_upload(
    text: str = Form(None),
    image: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
):
    """
    Extract structured event data from text announcement and/or poster image upload.
    
    - **text**: Raw text announcement (optional if image provided)
    - **image**: Poster image file (optional if text provided)
    
    Returns extracted event fields with confidence score and warnings for missing data.
    """
    if not text and not image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'image' must be provided"
        )

    image_base64 = None
    image_mime_type = None
    
    if image:
        content = validate_image_file(image)
        image_base64 = base64.b64encode(content).decode("utf-8")
        image_mime_type = image.content_type

    request = EventExtractionRequest(
        text=text,
        image_base64=image_base64,
        image_mime_type=image_mime_type,
    )

    provider = get_ai_provider()
    
    try:
        result = await provider.extract_event(request)
        return result
    except AiProviderUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except AiProviderValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except AiProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Event extraction failed: {str(e)}"
        )


@router.post("/query", response_model=RagQueryResponse)
async def query_events(
    request: RagQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Natural language query about campus events using RAG.
    
    - **query**: Natural language question (e.g., "What hackathons are happening this month?")
    - **limit**: Maximum number of results (default 10)
    - **categories**: Filter by event categories
    - **date_from**: Filter events from this date
    - **date_to**: Filter events until this date
    """
    provider = get_ai_provider()
    vs = SimpleVectorStore()

    # Step 1: Semantic retrieval from vector store (only APPROVED events are indexed)
    try:
        search_results = await vs.search(
            request.query,
            limit=request.limit,
            filters={"category": request.categories[0]} if request.categories else None,
        )
    except Exception as e:
        logger.warning(f"Vector store search failed: {e}")
        search_results = []

    # Step 2: Re-verify approval status and fetch full event data from DB
    events_context = []
    seen_ids = set()
    for emb, score in search_results:
        if emb.event_id in seen_ids:
            continue
        ev = (
            db.query(Event)
            .filter(Event.id == emb.event_id, Event.status == EventStatus.APPROVED)
            .first()
        )
        if not ev:
            continue
        seen_ids.add(emb.event_id)
        events_context.append({
            "id": ev.id,
            "title": ev.title,
            "description": ev.description,
            "category": ev.category,
            "venue": ev.venue,
            "date": ev.date.isoformat() if ev.date else None,
            "start_time": ev.start_time.strftime("%H:%M") if ev.start_time else None,
            "end_time": ev.end_time.strftime("%H:%M") if ev.end_time else None,
            "organizer_name": ev.organizer.name if ev.organizer else None,
            "tags": ev.tags.split(",") if ev.tags else [],
            "relevance_score": float(score),
        })

    # Apply date filters server-side
    if request.date_from:
        from datetime import datetime
        date_from = request.date_from.date() if hasattr(request.date_from, 'date') else request.date_from
        events_context = [e for e in events_context if e.get("date") and e["date"] >= str(date_from)]
    if request.date_to:
        from datetime import datetime
        date_to = request.date_to.date() if hasattr(request.date_to, 'date') else request.date_to
        events_context = [e for e in events_context if e.get("date") and e["date"] <= str(date_to)]

    # Limit results
    events_context = events_context[:request.limit]

    try:
        result = await provider.query_events(request, events_context)
        return result
    except AiProviderUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except AiProviderValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e)
        )
    except AiProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {str(e)}"
        )


@router.post("/reindex", response_model=dict)
async def reindex_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_organizer),
):
    """
    Manually reindex all approved events into the vector store for RAG search.
    Requires organizer privileges.
    """
    vs = SimpleVectorStore()
    try:
        stats = await vs.reindex_all(db)
        return {"message": "Reindexing complete", "stats": stats}
    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {str(e)}"
        )


@router.get("/health", response_model=AiHealthResponse)
async def ai_health():
    """Check AI service health and configuration."""
    provider = get_ai_provider()
    return await provider.health_check()


@router.post("/agent-query", response_model=RagQueryResponse)
async def agent_query(
    request: RagQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tool-using AI agent for campus event questions.

    Workflow:
      1. Interpret the user's question.
      2. Invoke the EventSearchTool (vector store) to retrieve relevant APPROVED events.
      3. Use the AI provider to formulate a grounded answer from the results.
    
    Only approved/published events are ever visible; draft/unpublished events
    are excluded at the tool level (authorization boundary).
    """
    agent = create_agent(provider=get_ai_provider(), db_session=db)
    try:
        result = await agent.run(request.query)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent query failed: {str(e)}",
        )


__all__ = ["router"]