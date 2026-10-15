"""
AI Service Module
Provides AI-powered event extraction and RAG-based event search.
Supports multiple providers via configuration.
"""

import base64
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Any, Dict
from datetime import datetime
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.schemas.ai import (
    EventExtractionRequest,
    ExtractedEventData,
    ExtractionWarning,
    EventExtractionResponse,
    RagQueryRequest,
    RagEventResult,
    RagQueryResponse,
    AiHealthResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    name: str
    base_url: str
    api_key: Optional[str]
    extraction_model: str
    embedding_model: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_wait_min: float = 1.0
    retry_wait_max: float = 10.0


class AiProviderError(Exception):
    """Base exception for AI provider errors."""
    pass


class AiProviderUnavailableError(AiProviderError):
    """Raised when AI provider is not configured or unreachable."""
    pass


class AiProviderValidationError(AiProviderError):
    """Raised when AI response fails validation."""
    pass


class AiProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def extract_event(self, request: EventExtractionRequest) -> EventExtractionResponse:
        """Extract structured event data from text or image."""
        pass

    @abstractmethod
    async def query_events(self, request: RagQueryRequest, events_context: List[dict]) -> RagQueryResponse:
        """Answer natural language queries about events using RAG."""
        pass

    @abstractmethod
    async def health_check(self) -> AiHealthResponse:
        """Check AI service health."""
        pass

    @abstractmethod
    def get_config(self) -> ProviderConfig:
        """Get provider configuration."""
        pass


class NavigateLabsProvider(AiProvider):
    """Navigate Labs AI provider implementation."""

    def __init__(self):
        self.config = ProviderConfig(
            name="navigate_labs",
            base_url=settings.NAVIGATE_API_BASE_URL,
            api_key=settings.NAVIGATE_API_KEY,
            extraction_model=settings.NAVIGATE_MODEL_EXTRACTION,
            embedding_model=settings.NAVIGATE_MODEL_EMBEDDING,
            timeout=30.0,
            max_retries=3,
        )

        if not self.config.api_key:
            logger.warning("NAVIGATE_API_KEY not configured. AI features will be unavailable.")

    def get_config(self) -> ProviderConfig:
        return self.config

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _log_request(self, endpoint: str, payload: dict, masked: bool = True) -> None:
        """Log request details without exposing sensitive data."""
        log_payload = payload.copy()
        if masked and "messages" in log_payload:
            for msg in log_payload["messages"]:
                if "content" in msg and isinstance(msg["content"], str):
                    # Truncate long content for logging
                    if len(msg["content"]) > 200:
                        msg["content"] = msg["content"][:200] + "... [truncated]"
        logger.debug(f"AI Request: {endpoint} payload={json.dumps(log_payload, default=str)}")

    def _log_response(self, endpoint: str, response: dict, duration_ms: int) -> None:
        """Log response details without exposing sensitive data."""
        log_response = {"choices": len(response.get("choices", []))}
        if "usage" in response:
            log_response["usage"] = response["usage"]
        logger.debug(f"AI Response: {endpoint} duration_ms={duration_ms} response={json.dumps(log_response)}")

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _make_request(self, endpoint: str, payload: dict) -> dict:
        """Make HTTP request to Navigate Labs API with retry logic."""
        if not self.config.api_key:
            raise AiProviderUnavailableError("AI API key not configured")

        url = f"{self.config.base_url}{endpoint}"
        self._log_request(endpoint, payload)

        start_time = time.time()
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            result = response.json()

        duration_ms = int((time.time() - start_time) * 1000)
        self._log_response(endpoint, result, duration_ms)
        return result

    async def extract_event(self, request: EventExtractionRequest) -> EventExtractionResponse:
        """Extract event data using Navigate Labs extraction model."""
        start_time = time.time()

        if not self.config.api_key:
            logger.info("Using mock extraction response (API key not configured)")
            return self._mock_extraction_response(request, start_time)

        try:
            prompt = self._build_extraction_prompt(request)

            payload = {
                "model": self.config.extraction_model,
                "messages": [
                    {"role": "system", "content": self._get_extraction_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }

            result = await self._make_request("/chat/completions", payload)
            content = result["choices"][0]["message"]["content"]

            extracted_data, warnings = self._parse_extraction_response(content, request)

            processing_time = int((time.time() - start_time) * 1000)

            return EventExtractionResponse(
                extracted_data=extracted_data,
                warnings=warnings,
                confidence=self._calculate_confidence(extracted_data, warnings),
                processing_time_ms=processing_time,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Navigate Labs API error: {e.response.status_code} - {e.response.text[:500]}")
            raise AiProviderError(f"AI service error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("Navigate Labs API timeout")
            raise AiProviderError("AI service timeout")
        except AiProviderValidationError:
            raise
        except Exception as e:
            logger.error(f"Event extraction failed: {type(e).__name__}: {e}")
            raise AiProviderError(f"Event extraction failed: {str(e)}")

    def _get_extraction_system_prompt(self) -> str:
        return """You are an expert event information extractor for a campus event platform. 
Extract structured event data from unstructured text or image descriptions.

CRITICAL RULES:
1. NEVER invent dates, venues, deadlines, or other factual event details.
2. If information is missing or ambiguous, return null for that field. Explicitly mark ambiguities in warnings.
3. Normalize dates to ISO 8601 format (YYYY-MM-DD).
4. Normalize times to HH:MM 24-hour format.
5. Categories must be one of: Workshop, Hackathon, Seminar, Competition, Conference, Cultural, Sports, Other
6. Return valid JSON matching the exact schema provided.
7. Include warnings for any missing required fields or ambiguities.
8. For ambiguous information (e.g., unclear date/time, multiple possible venues), set field to null and add a warning.

Required output format:
{
  "title": "string or null",
  "description": "string or null",
  "category": "string or null",
  "organization": "string or null",
  "venue": "string or null",
  "eligibility": "string or null",
  "registration_deadline": "ISO datetime string or null",
  "registration_link": "string or null",
  "date": "ISO date string or null",
  "start_time": "HH:MM string or null",
  "end_time": "HH:MM string or null",
  "tags": ["string"],
  "capacity": "integer or null",
  "poster_url": "string or null",
  "contact_email": "string or null",
  "online_meeting_url": "string or null",
  "speaker_info": "string or null",
  "additional_instructions": "string or null",
  "warnings": [{"field": "string", "message": "string", "severity": "warning|error"}]
}"""

    def _build_extraction_prompt(self, request: EventExtractionRequest) -> str:
        parts = []
        if request.text:
            parts.append(f"TEXT ANNOUNCEMENT:\n{request.text}")
        if request.image_base64:
            parts.append(f"POSTER IMAGE: [Base64 encoded image, MIME type: {request.image_mime_type}]")
        
        if not parts:
            raise AiProviderValidationError("Either text or image_base64 must be provided")

        return "\n\n".join(parts) + "\n\nExtract structured event data as JSON."

    def _parse_extraction_response(self, content: str, request: EventExtractionRequest) -> tuple:
        """Parse and validate AI extraction response."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            raise AiProviderValidationError("AI returned invalid JSON")

        # Extract warnings from AI response
        warnings = []
        for w in data.get("warnings", []):
            try:
                warnings.append(ExtractionWarning(**w))
            except Exception as e:
                logger.warning(f"Invalid warning format from AI: {e}")

        # Build extracted data with validation
        extracted = ExtractedEventData(
            title=data.get("title"),
            description=data.get("description"),
            category=self._validate_category(data.get("category")),
            organization=data.get("organization"),
            venue=data.get("venue"),
            eligibility=data.get("eligibility"),
            registration_deadline=self._parse_datetime(data.get("registration_deadline")),
            registration_link=self._validate_url(data.get("registration_link")),
            date=self._parse_date(data.get("date")),
            start_time=self._validate_time(data.get("start_time")),
            end_time=self._validate_time(data.get("end_time")),
            tags=self._validate_tags(data.get("tags", [])),
            capacity=self._validate_capacity(data.get("capacity")),
            poster_url=self._validate_url(data.get("poster_url")),
            contact_email=self._validate_email(data.get("contact_email")),
            online_meeting_url=self._validate_url(data.get("online_meeting_url")),
            speaker_info=data.get("speaker_info"),
            additional_instructions=data.get("additional_instructions"),
        )

        # Add warnings for missing required fields
        required_fields = ["title", "category", "venue", "date", "start_time", "end_time"]
        for field in required_fields:
            value = getattr(extracted, field)
            if not value:
                # Avoid duplicate warnings if AI already added one
                if not any(w.field == field for w in warnings):
                    warnings.append(ExtractionWarning(
                        field=field,
                        message=f"Required field '{field}' is missing or could not be extracted",
                        severity="warning"
                    ))

        return extracted, warnings

    def _validate_category(self, value: Optional[str]) -> Optional[str]:
        """Validate event category against allowed values."""
        if not value:
            return None
        allowed = {"Workshop", "Hackathon", "Seminar", "Competition", "Conference", "Cultural", "Sports", "Other"}
        # Case-insensitive match
        for allowed_cat in allowed:
            if allowed_cat.lower() == value.lower():
                return allowed_cat
        logger.warning(f"Invalid category '{value}', defaulting to 'Other'")
        return "Other"

    def _validate_time(self, value: Optional[str]) -> Optional[str]:
        """Validate time format HH:MM."""
        if not value:
            return None
        if not isinstance(value, str):
            return None
        parts = value.split(":")
        if len(parts) >= 2:
            try:
                hour = int(parts[0])
                minute = int(parts[1])
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return f"{hour:02d}:{minute:02d}"
            except ValueError:
                pass
        logger.warning(f"Invalid time format: {value}")
        return None

    def _validate_tags(self, value: Any) -> List[str]:
        """Validate and normalize tags."""
        if not value:
            return []
        if isinstance(value, str):
            return [t.strip() for t in value.split(",") if t.strip()]
        if isinstance(value, list):
            return [str(t).strip() for t in value if str(t).strip()]
        return []

    def _validate_capacity(self, value: Any) -> Optional[int]:
        """Validate capacity as positive integer."""
        if value is None:
            return None
        try:
            cap = int(value)
            return cap if cap > 0 else None
        except (ValueError, TypeError):
            return None

    def _validate_url(self, value: Optional[str]) -> Optional[str]:
        """Validate URL format."""
        if not value:
            return None
        if isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
            return value
        return None

    def _validate_email(self, value: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if not value:
            return None
        if isinstance(value, str) and "@" in value and "." in value.split("@")[-1]:
            return value
        return None

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid datetime format: {value}")
            return None

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid date format: {value}")
            return None

    def _calculate_confidence(self, data: ExtractedEventData, warnings: List[ExtractionWarning]) -> float:
        """Calculate extraction confidence based on completeness and warnings."""
        total_fields = 17
        filled_fields = sum(1 for v in data.model_dump().values() if v is not None and v != [])
        error_warnings = sum(1 for w in warnings if w.severity == "error")
        base_confidence = filled_fields / total_fields
        penalty = error_warnings * 0.15
        return max(0.0, min(1.0, base_confidence - penalty))

    def _mock_extraction_response(self, request: EventExtractionRequest, start_time: float) -> EventExtractionResponse:
        """Return mock response for testing when API key not configured."""
        processing_time = int((time.time() - start_time) * 1000)
        
        if request.text and "hackathon" in request.text.lower():
            extracted = ExtractedEventData(
                title="AI Hackathon 2026",
                description="Join 500+ students in a 36-hour sprint to build AI-powered solutions for real campus challenges.",
                category="Hackathon",
                venue="Main Auditorium, Block A",
                eligibility="All UG and PG students",
                registration_deadline=datetime(2026, 10, 15, 23, 59),
                registration_link="https://forms.example.com/ai-hackathon",
                date=datetime(2026, 10, 18),
                start_time="09:00",
                end_time="21:00",
                tags=["AI", "Machine Learning", "Prizes", "Teamwork"],
            )
            warnings = []
        else:
            extracted = ExtractedEventData()
            warnings = [ExtractionWarning(
                field="all",
                message="AI API key not configured. Using mock response for demonstration.",
                severity="warning"
            )]

        return EventExtractionResponse(
            extracted_data=extracted,
            warnings=warnings,
            confidence=0.85 if extracted.title else 0.0,
            processing_time_ms=processing_time,
        )

    async def query_events(self, request: RagQueryRequest, events_context: List[dict]) -> RagQueryResponse:
        """Answer natural language queries using RAG with Navigate Labs."""
        start_time = time.time()

        if not self.config.api_key:
            logger.info("Using mock RAG response (API key not configured)")
            return self._mock_rag_response(request, events_context, start_time)

        try:
            context = self._build_events_context(events_context)

            prompt = f"""You are a campus event assistant. Answer the user's question based ONLY on the provided event data.

EVENT DATA:
{context}

USER QUERY: {request.query}

RULES:
1. Only use information from the provided event data.
2. If the query cannot be answered from the data, say so.
3. Be concise and helpful.
4. Mention specific event titles, dates, and organizers when relevant.
5. Return a natural language answer.

ANSWER:"""

            payload = {
                "model": self.config.extraction_model,
                "messages": [
                    {"role": "system", "content": "You are a helpful campus event assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            }

            result = await self._make_request("/chat/completions", payload)
            answer = result["choices"][0]["message"]["content"].strip()

            relevant_events = self._filter_relevant_events(request, events_context, answer)

            processing_time = int((time.time() - start_time) * 1000)

            return RagQueryResponse(
                answer=answer,
                events=relevant_events,
                query_time_ms=processing_time,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Navigate Labs API error: {e.response.status_code}")
            raise AiProviderError(f"AI service error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("Navigate Labs API timeout")
            raise AiProviderError("AI service timeout")
        except Exception as e:
            logger.error(f"RAG query failed: {type(e).__name__}: {e}")
            raise AiProviderError(f"RAG query failed: {str(e)}")

    def _build_events_context(self, events: List[dict]) -> str:
        """Build formatted context string from events."""
        lines = []
        for e in events:
            line = f"- {e.get('title', 'Unknown')} ({e.get('category', 'N/A')})"
            if e.get('date'):
                line += f" on {e['date'][:10]}"
            if e.get('venue'):
                line += f" at {e['venue']}"
            if e.get('organizer_name'):
                line += f" by {e['organizer_name']}"
            if e.get('tags'):
                line += f" | Tags: {', '.join(e['tags'])}"
            lines.append(line)
        return "\n".join(lines) if lines else "No events available."

    def _filter_relevant_events(self, request: RagQueryRequest, events: List[dict], answer: str) -> List[RagEventResult]:
        """Filter events that are relevant to the answer."""
        relevant = []
        answer_lower = answer.lower()
        
        for e in events:
            title_lower = e.get('title', '').lower()
            if title_lower in answer_lower or any(term in title_lower for term in request.query.lower().split()):
                try:
                    relevant.append(RagEventResult(
                        id=e.get('id', 0),
                        title=e.get('title', ''),
                        description=e.get('description'),
                        category=e.get('category'),
                        venue=e.get('venue'),
                        date=self._parse_date(e.get('date')) if e.get('date') else None,
                        start_time=e.get('start_time'),
                        end_time=e.get('end_time'),
                        organizer_name=e.get('organizer_name'),
                        tags=e.get('tags', []),
                        relevance_score=0.8,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to create RagEventResult: {e}")
        
        return relevant[:request.limit]

    def _mock_rag_response(self, request: RagQueryRequest, events_context: List[dict], start_time: float) -> RagQueryResponse:
        """Mock RAG response for testing."""
        processing_time = int((time.time() - start_time) * 1000)
        
        return RagQueryResponse(
            answer="AI service not configured. Please set NAVIGATE_API_KEY to enable AI features.",
            events=[],
            query_time_ms=processing_time,
        )

    async def health_check(self) -> AiHealthResponse:
        """Check AI service health."""
        if not self.config.api_key:
            return AiHealthResponse(
                status="unhealthy",
                provider=self.config.name,
                extraction_model=self.config.extraction_model,
                embedding_model=self.config.embedding_model,
                api_reachable=False,
                message="API key not configured"
            )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.config.base_url}/health",
                    headers=self._get_headers()
                )
                reachable = response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {type(e).__name__}")
            reachable = False

        return AiHealthResponse(
            status="healthy" if reachable else "degraded",
            provider=self.config.name,
            extraction_model=self.config.extraction_model,
            embedding_model=self.config.embedding_model,
            api_reachable=reachable,
            message=None if reachable else "API endpoint unreachable"
        )


class MockAiProvider(AiProvider):
    """Mock AI provider for testing."""

    def get_config(self) -> ProviderConfig:
        return ProviderConfig(
            name="mock",
            base_url="",
            api_key=None,
            extraction_model="mock",
            embedding_model="mock",
        )

    async def extract_event(self, request: EventExtractionRequest) -> EventExtractionResponse:
        start_time = time.time()
        extracted = ExtractedEventData(
            title="Mock Event",
            description="This is a mock extraction for testing.",
            category="Workshop",
            venue="Test Venue",
            date=datetime.now(),
            start_time="10:00",
            end_time="12:00",
            tags=["test", "mock"],
        )
        warnings = [ExtractionWarning(
            field="all",
            message="Using mock provider for testing",
            severity="warning"
        )]
        return EventExtractionResponse(
            extracted_data=extracted,
            warnings=warnings,
            confidence=0.9,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    async def query_events(self, request: RagQueryRequest, events_context: List[dict]) -> RagQueryResponse:
        start_time = time.time()
        return RagQueryResponse(
            answer="Mock RAG response for testing.",
            events=[],
            query_time_ms=int((time.time() - start_time) * 1000),
        )

    async def health_check(self) -> AiHealthResponse:
        return AiHealthResponse(
            status="healthy",
            provider="mock",
            extraction_model="mock",
            embedding_model="mock",
            api_reachable=True,
            message="Mock provider active"
        )


def get_ai_provider() -> AiProvider:
    """Get the configured AI provider."""
    provider_type = getattr(settings, "AI_PROVIDER", "").lower()
    
    if provider_type == "navigate_labs":
        return NavigateLabsProvider()
    elif provider_type == "mock":
        return MockAiProvider()
    else:
        # Default to Navigate Labs if configured, otherwise mock
        if settings.NAVIGATE_API_KEY:
            return NavigateLabsProvider()
        return MockAiProvider()