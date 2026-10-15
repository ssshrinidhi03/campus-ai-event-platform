"""
AI Service Schemas
Pydantic models for AI-powered event extraction and RAG queries.
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, HttpUrl, model_validator


class EventExtractionRequest(BaseModel):
    """Request schema for AI event extraction from text or image."""
    text: Optional[str] = Field(None, description="Raw text announcement to extract event data from")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image for poster analysis")
    image_mime_type: Optional[str] = Field(None, description="MIME type of the image (e.g., image/png, image/jpeg)")
    
    @model_validator(mode='after')
    def check_at_least_one_input(self):
        if not self.text and not self.image_base64:
            raise ValueError("Either 'text' or 'image_base64' must be provided")
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Join us for the AI Hackathon on March 15th at 10 AM in the Main Auditorium. Open to all CS students. Register by March 10th at https://example.com/register",
                "image_base64": None,
                "image_mime_type": None
            }
        }
    )


class ExtractedEventData(BaseModel):
    """Structured event data extracted by AI."""
    title: Optional[str] = Field(None, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    category: Optional[str] = Field(None, description="Event category (Workshop, Hackathon, Seminar, Competition, Conference, Cultural, Sports, Other)")
    organization: Optional[str] = Field(None, description="Organizing club/department/organization")
    venue: Optional[str] = Field(None, description="Event venue/location")
    eligibility: Optional[str] = Field(None, description="Who can attend")
    registration_deadline: Optional[datetime] = Field(None, description="Registration deadline")
    registration_link: Optional[str] = Field(None, description="External registration URL")
    date: Optional[datetime] = Field(None, description="Event date")
    start_time: Optional[str] = Field(None, description="Start time in HH:MM format")
    end_time: Optional[str] = Field(None, description="End time in HH:MM format")
    tags: List[str] = Field(default_factory=list, description="Event tags")
    capacity: Optional[int] = Field(None, description="Maximum attendees")
    poster_url: Optional[str] = Field(None, description="Poster image URL")
    contact_email: Optional[str] = Field(None, description="Contact email")
    online_meeting_url: Optional[str] = Field(None, description="Online meeting URL")
    speaker_info: Optional[str] = Field(None, description="Speaker information")
    additional_instructions: Optional[str] = Field(None, description="Additional instructions")


class ExtractionWarning(BaseModel):
    """Warning about missing or uncertain extracted fields."""
    field: str = Field(description="Name of the field with issue")
    message: str = Field(description="Human-readable warning message")
    severity: Literal["warning", "error"] = Field(default="warning", description="Severity level")


class EventExtractionResponse(BaseModel):
    """Response schema for AI event extraction."""
    extracted_data: ExtractedEventData = Field(description="Extracted event fields")
    warnings: List[ExtractionWarning] = Field(default_factory=list, description="Extraction warnings and missing fields")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall extraction confidence score")
    processing_time_ms: int = Field(description="Time taken to process the request")


class RagQueryRequest(BaseModel):
    """Request schema for RAG-based event search."""
    query: str = Field(description="Natural language query about events")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    categories: Optional[List[str]] = Field(None, description="Filter by event categories")
    date_from: Optional[datetime] = Field(None, description="Filter events from this date")
    date_to: Optional[datetime] = Field(None, description="Filter events until this date")


class RagEventResult(BaseModel):
    """Event result in RAG search."""
    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    venue: Optional[str]
    date: Optional[datetime]
    start_time: Optional[str]
    end_time: Optional[str]
    organizer_name: Optional[str]
    tags: List[str]
    relevance_score: float = Field(description="Semantic similarity score")


class RagQueryResponse(BaseModel):
    """Response schema for RAG query."""
    answer: str = Field(description="Natural language answer to the query")
    events: List[RagEventResult] = Field(default_factory=list, description="Relevant events found")
    query_time_ms: int = Field(description="Time taken to process the query")


class AiHealthResponse(BaseModel):
    """AI service health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    provider: str
    extraction_model: str
    embedding_model: str
    api_reachable: bool
    message: Optional[str] = None


__all__ = [
    "EventExtractionRequest",
    "ExtractedEventData",
    "ExtractionWarning",
    "EventExtractionResponse",
    "RagQueryRequest",
    "RagEventResult",
    "RagQueryResponse",
    "AiHealthResponse",
]