"""
AI API Routes
Endpoints for AI-powered event extraction and RAG queries.
"""

import base64
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import get_current_user
from app.schemas.ai import (
    EventExtractionRequest,
    EventExtractionResponse,
    RagQueryRequest,
    RagQueryResponse,
    AiHealthResponse,
)
from app.services.ai import get_ai_provider, AiProviderError, AiProviderUnavailableError, AiProviderValidationError
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
    # Build base query - only published/approved events visible to students
    query = db.query(Event).filter(Event.status == EventStatus.APPROVED)
    
    # Apply filters
    if request.categories:
        query = query.filter(Event.category.in_(request.categories))
    if request.date_from:
        query = query.filter(Event.date >= request.date_from)
    if request.date_to:
        query = query.filter(Event.date <= request.date_to)
    
    # Get events for context
    events = query.order_by(Event.date.desc()).limit(100).all()
    
    # Convert to dict for RAG context
    events_context = []
    for event in events:
        events_context.append({
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "category": event.category,
            "venue": event.venue,
            "date": event.date.isoformat() if event.date else None,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "organizer_name": event.organizer.full_name if event.organizer else None,
            "tags": event.tags or [],
        })

    provider = get_ai_provider()
    
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


@router.get("/health", response_model=AiHealthResponse)
async def ai_health():
    """Check AI service health and configuration."""
    provider = get_ai_provider()
    return await provider.health_check()


__all__ = ["router"]