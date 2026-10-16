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
from typing import Optional, List, Any, Dict, TYPE_CHECKING
from sqlalchemy.orm import Session
from datetime import datetime

if TYPE_CHECKING:
    from app.services.vector_store import SimpleVectorStore
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.event import Event
from app.models.enums import EventStatus
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
    async def get_embedding(self, text: str) -> List[float]:
        raise NotImplementedError
    embed = get_embedding

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

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Navigate Labs /embeddings endpoint (text-embedding-3-small)."""
        if not self.config.api_key:
            raise AiProviderUnavailableError("AI API key not configured")
        try:
            payload = {
                "model": self.config.embedding_model,
                "input": text,
            }
            result = await self._make_request("/embeddings", payload)
            data = result.get("data", [])
            if data and isinstance(data, list) and len(data) > 0:
                embedding = data[0].get("embedding")
                if isinstance(embedding, list):
                    return embedding
            logger.warning("Embedding response missing embedding data")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"Navigate Labs embedding API error: {e.response.status_code}")
            raise AiProviderError(f"AI service error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("Navigate Labs embedding API timeout")
            raise AiProviderError("AI service timeout")
        except Exception as e:
            logger.error(f"Embedding generation failed: {type(e).__name__}: {e}")
            raise AiProviderError(f"Embedding generation failed: {str(e)}")

    async def extract_event(self, request: EventExtractionRequest) -> EventExtractionResponse:
        """Extract event data using Navigate Labs extraction model."""
        start_time = time.time()

        if not self.config.api_key:
            logger.info("Using mock extraction response (API key not configured)")
            return self._mock_extraction_response(request, start_time)

        try:
            system_prompt = self._get_extraction_system_prompt()
            user_content = self._build_extraction_content(request)

            payload = {
                "model": self.config.extraction_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }

            result = await self._make_request("/chat/completions", payload)
            content = result["choices"][0]["message"]["content"]

            # Diagnostic logging of response structure (no sensitive data)
            choices = result.get("choices", [])
            content_type = type(content).__name__
            content_len = len(content) if isinstance(content, str) else 0
            logger.debug(
                "AI extraction response: choices=%d content_type=%s content_len=%d",
                len(choices), content_type, content_len,
            )

            extracted_data, warnings = self._parse_extraction_response(content, request)

            # Diagnostic logging of parsed fields (no sensitive announcement content)
            recognized_fields = [f for f in ["title", "category", "venue", "date", "start_time", "end_time"] if getattr(extracted_data, f, None)]
            logger.debug(
                "AI extraction parsed fields: recognized=%s venue=%s start_time=%s end_time=%s confidence=%.2f warnings=%d",
                recognized_fields,
                getattr(extracted_data, "venue", None),
                getattr(extracted_data, "start_time", None),
                getattr(extracted_data, "end_time", None),
                self._calculate_confidence(extracted_data, warnings),
                len(warnings),
            )

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
5. Categories must be exactly one of: Workshop, Hackathon, Seminar, Competition, Conference, Cultural, Sports, Other
6. Return ONLY valid JSON matching the exact schema provided. No markdown code fences, no explanatory text, no preamble.
7. Include warnings for any missing required fields or ambiguities.
8. For ambiguous information (e.g., unclear date/time, multiple possible venues), set field to null and add a warning.
9. Output must be parseable by json.loads() - raw JSON object only.
10. Do NOT confuse registration deadline with event date or end time - they are different fields.

REQUIRED FIELDS (must be present, use null if missing):
- title: string - The event name
- category: string - One of: Workshop, Hackathon, Seminar, Competition, Conference, Cultural, Sports, Other
- venue: string - Where the event takes place
- date: string - YYYY-MM-DD format (null if no year provided)
- start_time: string - HH:MM 24-hour format (null if missing)
- end_time: string - HH:MM 24-hour format (null if missing)

OPTIONAL FIELDS (use null if missing):
- description: string - Event description
- organization: string - Organizing club/department
- eligibility: string - Who can attend
- registration_deadline: string - ISO datetime (null if missing)
- registration_link: string - URL for registration
- tags: array of strings - Event tags
- capacity: integer - Maximum attendees

Required output JSON format:
{
  "title": "string or null",
  "description": "string or null",
  "category": "string or null",
  "organization": "string or null",
  "venue": "string or null",
  "eligibility": "string or null",
  "registration_deadline": "ISO datetime string or null",
  "registration_link": "string or null",
  "date": "ISO date string (YYYY-MM-DD) or null",
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

    def _build_extraction_content(self, request: EventExtractionRequest):
        """Build user message content for extraction.

        Returns a plain string for text-only requests, or a list of content
        parts (text + image_url) when an image is provided, so the model
        genuinely receives the poster image (multimodal input).
        """
        parts = []

        if request.text:
            parts.append({
                "type": "text",
                "text": f"TEXT ANNOUNCEMENT:\n{request.text}\n\nExtract structured event data as JSON.",
            })

        if request.image_base64:
            if not request.image_mime_type:
                raise AiProviderValidationError("image_mime_type is required when image_base64 is provided")
            # Validate MIME type is an image
            if not request.image_mime_type.startswith("image/"):
                raise AiProviderValidationError("image_mime_type must be an image MIME type")
            data_url = f"data:{request.image_mime_type};base64,{request.image_base64}"
            parts.append({
                "type": "text",
                "text": "\nPOSTER IMAGE (analyze the image directly for event details):\nExtract structured event data as JSON.",
            })
            parts.append({
                "type": "image_url",
                "image_url": {
                    "url": data_url,
                },
            })

        if not parts:
            raise AiProviderValidationError("Either text or image_base64 must be provided")

        # Return a plain string when there is no image (backward compatible)
        if request.image_base64:
            return parts
        return parts[0]["text"]

    def _extract_json_block(self, content: str) -> Optional[str]:
        """Extract a JSON object from content that may be wrapped in Markdown
        code fences or surrounded by explanatory text.

        Only strips surrounding fences when they are present; never blindly
        strips characters or corrupts JSON strings. Returns the JSON text,
        or None if no JSON object can be found.
        """
        text = content.strip()

        # Strip surrounding Markdown code fences when present.
        fence = "```"
        if text.startswith(fence):
            # Opening fence is at index 0; skip past it and an optional
            # language tag (e.g. ```json) to find the content start.
            first_newline = text.find("\n", 3)
            content_start = first_newline + 1 if first_newline != -1 else 3
            end = text.find(fence, content_start)
            if end != -1:
                return text[content_start:end].strip()
            # Opening fence with no closing fence: take the rest.
            return text[content_start:].strip()

        # No fences: locate the first balanced JSON object by scanning for
        # the first '{' and matching its closing '}', respecting strings.
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if in_string:
                if ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    def _parse_natural_language_date(self, value: Optional[str]) -> Optional[datetime]:
        """Parse a date from natural language text without inventing a year.

        Handles: "March 15, 2027", "March 15th, 2027", "2027-03-15", "March 15".
        Returns None when no year is provided (never invents one).
        """
        if not value or not isinstance(value, str):
            return None
        value = value.strip()

        # Already ISO format
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Strip ordinal suffixes (1st, 2nd, 15th, etc.)
        import re
        cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', value, flags=re.IGNORECASE)

        # "Month DD, YYYY" or "Month DD YYYY" - year required
        for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue

        # "Month DD" without year - do not invent one
        for fmt in ("%B %d", "%b %d"):
            try:
                datetime.strptime(cleaned, fmt)
                # Year missing: return None per the no-invention rule
                return None
            except ValueError:
                continue

        logger.warning(f"Could not parse natural language date: {value}")
        return None

    def _parse_natural_language_time(self, value: Optional[str]) -> Optional[str]:
        """Parse a time from natural language text to HH:MM 24-hour format.

        Handles: "10 AM", "10:00 AM", "2 PM", "10:00", "14:00".
        """
        if not value or not isinstance(value, str):
            return None
        value = value.strip().upper()

        # "H AM/PM" or "H:MM AM/PM" -- check AM/PM FIRST so "5:00 PM" -> "17:00"
        # not "05:00" (the HH:MM check below would ignore the PM).
        import re
        for fmt in ("%I:%M %p", "%I %p"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime("%H:%M")
            except ValueError:
                continue

        # Already HH:MM 24-hour
        try:
            parts = value.split(":")
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1][:2])
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return f"{hour:02d}:{minute:02d}"
        except (ValueError, IndexError):
            pass

        logger.warning(f"Could not parse natural language time: {value}")
        return None

    def _parse_time_range(self, value: Optional[str]) -> tuple:
        """Parse a time range string into (start_time, end_time).

        Handles formats like:
        - "09:00–17:00", "09:00-17:00", "09:00 to 17:00"
        - "9:00 AM – 5:00 PM", "9:00 AM - 5:00 PM"
        - "10 AM – 12 PM", "10 AM - 12 PM"

        Returns (start_time, end_time) in HH:MM format, or (None, None) if unparseable.
        Never invents times that aren't present.
        """
        if not value or not isinstance(value, str):
            return (None, None)

        import re

        # Normalize range separators
        normalized = value.strip()
        # Replace en-dash, em-dash, and "to" with a consistent separator
        normalized = re.sub(r"\s*[–—]\s*", " - ", normalized)
        normalized = re.sub(r"\s+to\s+", " - ", normalized, flags=re.IGNORECASE)

        parts = [p.strip() for p in normalized.split("-") if p.strip()]
        if len(parts) != 2:
            return (None, None)

        start = self._parse_natural_language_time(parts[0])
        end = self._parse_natural_language_time(parts[1])
        return (start, end)

    def _parse_natural_language_response(
        self, content: str, request: EventExtractionRequest
    ) -> tuple:
        """Parse event data from a natural language text response.

        The Navigate Labs Nova-micro model sometimes returns markdown-formatted
        text instead of JSON, with labels and values on separate lines, e.g.:
            **Event Title:**
            AI Hackathon

            **Date:**
            March 15, 2027

        Extracts fields by matching bold-header or label patterns and normalizing
        dates/times without inventing missing years.
        """
        import re

        field_map = {
            # Title variations
            "event title": "title",
            "title": "title",
            "event name": "title",
            "name": "title",
            # Category variations
            "category": "category",
            "event type": "category",
            "event category": "category",
            "event_category": "category",
            "type": "category",
            # Venue variations
            "venue": "venue",
            "event venue": "venue",
            "location": "venue",
            "event location": "venue",
            "place": "venue",
            # Date variations
            "date": "date",
            "event date": "date",
            "event day": "date",
            # Time variations
            "time": "start_time",
            "event time": "start_time",
            "start time": "start_time",
            "event start time": "start_time",
            "start": "start_time",
            "event start": "start_time",
            "begin": "start_time",
            "starts at": "start_time",
            "start-time": "start_time",
            "end time": "end_time",
            "event end time": "end_time",
            "end": "end_time",
            "event end": "end_time",
            "finish": "end_time",
            "ends at": "end_time",
            "end-time": "end_time",
            # Registration link variations
            "registration link": "registration_link",
            "link": "registration_link",
            "register link": "registration_link",
            "registration url": "registration_link",
            # Registration deadline variations
            "registration deadline": "registration_deadline",
            "deadline": "registration_deadline",
            "register by": "registration_deadline",
            # Other fields
            "eligibility": "eligibility",
            "target audience": "eligibility",
            "audience": "eligibility",
            "who can attend": "eligibility",
            "description": "description",
            "details": "description",
            "event description": "description",
            "topics covered": "description",
            "topics": "description",
            "organization": "organization",
            "organizer": "organization",
            "organised by": "organization",
            "organized by": "organization",
        }

        data: Dict[str, Any] = {"warnings": []}

        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # Strip leading dash/bullet markers for list-format responses.
            # Only strip "* " when NOT followed by another "*" (to avoid
            # corrupting bold markdown like **Field Name:**).
            line_clean = re.sub(r"^\s*[-•]\s*", "", line)
            line_clean = re.sub(r"^\s*\*(?!\*)\s*", "", line_clean)

            # Match a label line: **Field Name:** value  or  Field Name: value
            # (value may be on same line or next non-empty line)
            m = re.match(
                r"^\s*\*\*(?P<label>.+?)\*\*\s*(?P<same_line_value>.*?)\s*$"
                r"|^\s*(?P<label2>[A-Za-z][A-Za-z ]{1,59}?)\s*:\s*(?P<same_line_value2>.*?)\s*$",
                line_clean,
                re.IGNORECASE,
            )
            if not m:
                i += 1
                continue

            label = (m.group("label") or m.group("label2") or "").strip().lower().rstrip(":")
            # Normalize underscores to spaces so "event_category" matches "event category"
            label = label.replace("_", " ")
            same_line_value = (m.group("same_line_value") or m.group("same_line_value2") or "").strip()

            # Skip obvious non-field labels (introductory text, etc.)
            if len(label) > 60 or label.startswith(("here", "the", "this", "if", "note")):
                i += 1
                continue

            schema_field = field_map.get(label)
            if not schema_field:
                i += 1
                continue

            # Determine the value: same line, or next non-empty line
            if same_line_value:
                value = same_line_value
                i += 1
            else:
                # Value is on the next non-empty line(s). If the first value
                # line is a bullet/list item, collect all consecutive bullet
                # lines so multi-line values (e.g. "Topics Covered") are not
                # truncated. Otherwise use just the first line (original behavior).
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j >= len(lines):
                    i += 1
                    continue
                first_line = lines[j]
                bullet_cleaned = re.sub(r"^\s*[-•]\s*", "", first_line)
                bullet_cleaned = re.sub(r"^\s*\*(?!\*)\s*", "", bullet_cleaned).strip()
                if bullet_cleaned != first_line.strip():
                    # First line is a bullet: collect all consecutive bullet lines
                    value_lines = [bullet_cleaned]
                    j += 1
                    while j < len(lines):
                        raw_line = lines[j]
                        stripped = raw_line.strip()
                        if not stripped:
                            break
                        bc = re.sub(r"^\s*[-•]\s*", "", raw_line)
                        bc = re.sub(r"^\s*\*(?!\*)\s*", "", bc).strip()
                        if bc != stripped:
                            value_lines.append(bc)
                            j += 1
                        else:
                            break
                    value = " ".join(value_lines)
                    i = j
                else:
                    # First line is not a bullet: use it as the value
                    value = bullet_cleaned
                    i = j + 1

            # Remove trailing markdown artifacts
            value = re.sub(r"\*\*$", "", value).strip()

            # Strip markdown link syntax: [text](url) -> url
            value = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", r"\2", value).strip()

            if schema_field == "date":
                parsed = self._parse_natural_language_date(value)
                data[schema_field] = parsed
            elif schema_field in ("start_time", "end_time"):
                # Check if the value is a time range (e.g., "09:00-17:00", "9 AM - 5 PM")
                start_t, end_t = self._parse_time_range(value)
                if start_t is not None:
                    data["start_time"] = start_t
                if end_t is not None:
                    data["end_time"] = end_t
                # If range parsing didn't yield results, fall back to single time parse
                if start_t is None and end_t is None:
                    single = self._parse_natural_language_time(value)
                    if schema_field == "start_time":
                        data["start_time"] = single
                    else:
                        data["end_time"] = single
            elif schema_field == "registration_deadline":
                parsed = self._parse_natural_language_date(value)
                if parsed:
                    data[schema_field] = parsed
                else:
                    data["warnings"].append(
                        {"field": "registration_deadline",
                         "message": "Registration deadline date could not be parsed (no year provided)",
                         "severity": "warning"}
                    )
            else:
                data[schema_field] = value

        # Build ExtractedEventData from parsed fields
        # If no schema fields were extracted at all, the response is unparseable
        schema_fields = {
            "title", "description", "category", "organization", "venue",
            "eligibility", "registration_deadline", "registration_link",
            "date", "start_time", "end_time",
        }
        recognized = sorted(k for k in data if k in schema_fields and k != "warnings")
        logger.debug(
            "Natural language parse: recognized_fields=%s data_keys=%s",
            recognized,
            sorted(k for k in data.keys() if k != "warnings"),
        )
        if not any(k in data for k in schema_fields):
            logger.error(
                "Natural language response contained no recognizable event fields"
            )
            raise AiProviderValidationError("AI returned invalid JSON")

        reg_deadline = data.get("registration_deadline")
        extracted = ExtractedEventData(
            title=data.get("title"),
            description=data.get("description"),
            category=self._validate_category(data.get("category")),
            organization=data.get("organization"),
            venue=data.get("venue"),
            eligibility=data.get("eligibility"),
            registration_deadline=self._parse_datetime(
                reg_deadline.isoformat() if reg_deadline else None
            ),
            registration_link=self._validate_url(data.get("registration_link")),
            date=data.get("date"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            tags=[],
            capacity=None,
            poster_url=None,
            contact_email=None,
            online_meeting_url=None,
            speaker_info=None,
            additional_instructions=None,
        )

        warnings: List[ExtractionWarning] = []
        for w in data.get("warnings", []):
            try:
                warnings.append(ExtractionWarning(**w))
            except Exception:
                pass

        # Add warnings for missing required fields
        required_fields = ["title", "category", "venue", "date", "start_time", "end_time"]
        for field in required_fields:
            value = getattr(extracted, field)
            if not value:
                if not any(w.field == field for w in warnings):
                    warnings.append(ExtractionWarning(
                        field=field,
                        message=f"Required field '{field}' is missing or could not be extracted",
                        severity="warning"
                    ))

        return extracted, warnings

    def _parse_extraction_response(self, content: str, request: EventExtractionRequest) -> tuple:
        """Parse and validate AI extraction response.

        Tries JSON parsing first (direct, then from Markdown code fences or
        explanatory text). If the provider returns natural language text
        instead of JSON (e.g. Navigate Labs Nova-micro), falls back to
        parsing the text response for labeled fields.
        """
        if not content or not content.strip():
            logger.error("AI response content is empty or missing")
            raise AiProviderValidationError("AI returned empty response")

        # Strategy 1: Parse as JSON (direct or extracted from fences/text)
        json_text = content.strip()
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            extracted_block = self._extract_json_block(content)
            if extracted_block is not None:
                try:
                    data = json.loads(extracted_block)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON block: {e}")
                    data = None
            else:
                data = None

        if isinstance(data, dict):
            return self._build_extracted_data_from_dict(data, request)

        # Strategy 2: Parse natural language text response
        logger.debug("Response is not JSON; attempting natural language parsing")
        try:
            return self._parse_natural_language_response(content, request)
        except Exception as e:
            logger.error(
                "Failed to parse AI response as JSON or natural language: %s",
                type(e).__name__,
            )
            logger.debug("Raw content preview: %s", content[:200].replace("\n", "\\n"))
            raise AiProviderValidationError("AI returned invalid JSON")

    def _build_extracted_data_from_dict(
        self, data: Dict[str, Any], request: EventExtractionRequest
    ) -> tuple:
        """Build ExtractedEventData and warnings from a parsed JSON dict."""
        # Map alternative JSON key names to canonical schema fields
        # The provider may return event_name, event_title, name, etc. instead of title
        field_map = {
            # Title variations
            "event_name": "title",
            "event_title": "title",
            "name": "title",
            # Category variations
            "event_category": "category",
            "event_type": "category",
            # Description variations
            "description": "description",
            "event_description": "description",
            "details": "description",
            "topics_covered": "description",
            # Venue variations
            "event_venue": "venue",
            "location": "venue",
            # Date variations
            "event_date": "date",
            # Time variations
            "start": "start_time",
            "start_time_raw": "start_time",
            "event_start": "start_time",
            "event_start_time": "start_time",
            "end": "end_time",
            "end_time_raw": "end_time",
            "event_end": "end_time",
            "event_end_time": "end_time",
            # Organization variations
            "organization": "organization",
            "organizer": "organization",
            "event_organizer": "organization",
            "description": "description",
            "category": "category",
            "organization": "organization",
            "venue": "venue",
            "eligibility": "eligibility",
            "registration_deadline": "registration_deadline",
            "registration_link": "registration_link",
            "date": "date",
            "start_time": "start_time",
            "end_time": "end_time",
            "tags": "tags",
            "capacity": "capacity",
            "poster_url": "poster_url",
            "contact_email": "contact_email",
            "online_meeting_url": "online_meeting_url",
            "speaker_info": "speaker_info",
            "additional_instructions": "additional_instructions",
        }

        # Normalize keys using field_map
        normalized: Dict[str, Any] = {}
        list_fields = {"tags"}
        for key, value in data.items():
            canonical = field_map.get(key, key)
            if isinstance(value, list) and canonical not in list_fields:
                value = " ".join(str(v) for v in value)
            normalized[canonical] = value

        # Extract warnings from AI response
        warnings = []
        for w in data.get("warnings", []):
            try:
                warnings.append(ExtractionWarning(**w))
            except Exception as e:
                logger.warning(f"Invalid warning format from AI: {e}")

        # Build extracted data with validation
        extracted = ExtractedEventData(
            title=normalized.get("title"),
            description=normalized.get("description"),
            category=self._validate_category(normalized.get("category")),
            organization=normalized.get("organization"),
            venue=normalized.get("venue"),
            eligibility=normalized.get("eligibility"),
            registration_deadline=self._parse_datetime(normalized.get("registration_deadline")),
            registration_link=self._validate_url(normalized.get("registration_link")),
            date=self._parse_natural_language_date(normalized.get("date")),
            start_time=self._validate_time(normalized.get("start_time")),
            end_time=self._validate_time(normalized.get("end_time")),
            tags=self._validate_tags(normalized.get("tags", [])),
            capacity=self._validate_capacity(normalized.get("capacity")),
            poster_url=self._validate_url(normalized.get("poster_url")),
            contact_email=self._validate_email(normalized.get("contact_email")),
            online_meeting_url=self._validate_url(normalized.get("online_meeting_url")),
            speaker_info=normalized.get("speaker_info"),
            additional_instructions=normalized.get("additional_instructions"),
        )

        # Add warnings for missing required fields
        required_fields = ["title", "category", "venue", "date", "start_time", "end_time"]
        for field in required_fields:
            value = getattr(extracted, field)
            if not value:
                if not any(w.field == field for w in warnings):
                    warnings.append(ExtractionWarning(
                        field=field,
                        message=f"Required field '{field}' is missing or could not be extracted",
                        severity="warning"
                    ))

        # Diagnostic logging for JSON path
        recognized_fields = [f for f in required_fields if getattr(extracted, f, None)]
        logger.debug(
            "JSON parse: recognized_fields=%s venue=%s start_time=%s end_time=%s warnings=%d",
            recognized_fields,
            extracted.venue,
            extracted.start_time,
            extracted.end_time,
            len(warnings),
        )

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
        """Validate time format HH:MM or H:MM AM/PM.

        Handles: "10:00", "09:00", "9:00 AM", "5:00 PM", "12:00 PM".
        Returns HH:MM 24-hour format.
        """
        if not value or not isinstance(value, str):
            return None
        value = value.strip().upper()

        # "H AM/PM" or "H:MM AM/PM" -- check AM/PM FIRST so "5:00 PM" -> "17:00"
        # not "05:00" (the HH:MM check below would ignore the PM).
        import re
        for fmt in ("%I:%M %p", "%I %p"):
            try:
                from datetime import datetime as _dt
                dt = _dt.strptime(value, fmt)
                return dt.strftime("%H:%M")
            except ValueError:
                continue

        # Already HH:MM 24-hour
        try:
            parts = value.split(":")
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1][:2])
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return f"{hour:02d}:{minute:02d}"
        except (ValueError, IndexError):
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
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            logger.warning(f"Invalid datetime format: {value}")
            return None

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            logger.warning(f"Invalid date format: {value}")
            return None

    def _calculate_confidence(self, data: ExtractedEventData, warnings: List[ExtractionWarning]) -> float:
        """Calculate extraction confidence based on completeness and warnings.

        Weights required fields (title, category, venue, date, start_time,
        end_time) more heavily than optional fields, so missing required
        fields significantly lower confidence while optional fields provide
        partial credit.
        """
        required_fields = ["title", "category", "venue", "date", "start_time", "end_time"]
        optional_fields = [
            "description", "organization", "eligibility", "registration_link",
            "registration_deadline", "tags", "capacity", "poster_url",
            "contact_email", "online_meeting_url", "speaker_info",
            "additional_instructions",
        ]

        data_dict = data.model_dump()

        # Required field completion rate (70% of confidence)
        required_filled = sum(
            1 for f in required_fields
            if data_dict.get(f) not in (None, [], "")
        )
        required_rate = required_filled / len(required_fields)

        # Optional field completion rate (30% of confidence)
        optional_filled = sum(
            1 for f in optional_fields
            if data_dict.get(f) not in (None, [], "")
        )
        optional_rate = optional_filled / len(optional_fields) if optional_fields else 0.0

        base_confidence = 0.7 * required_rate + 0.3 * optional_rate

        # Penalty for warnings about missing required fields
        required_warnings = sum(1 for w in warnings if w.field in required_fields)
        penalty = required_warnings * 0.08

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

            prompt = f"""You are a campus event assistant. Answer the user's question using ONLY the provided event data below.

EVENT DATA (retrieved approved campus events):
{context}

USER QUERY: {request.query}

RULES:
1. Answer using ONLY information from the provided event data. Do not invent events, dates, venues, or details.
2. If no event in the data is genuinely relevant to the user's query, say "I couldn't find any relevant events matching your question." Do not stretch relevance to marginally related events.
3. When a relevant event is found, mention its specific title, date, venue, time, and organizer from the data.
4. Distinguish verified event facts from general suggestions.
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
            if e.get('start_time'):
                line += f" at {e['start_time']}"
            if e.get('venue'):
                line += f" in {e['venue']}"
            if e.get('organizer_name'):
                line += f" by {e['organizer_name']}"
            if e.get('description'):
                line += f". Description: {e['description']}"
            if e.get('tags'):
                line += f" | Tags: {', '.join(e['tags'])}"
            lines.append(line)
        return "\n".join(lines) if lines else "No events available."

    def _filter_relevant_events(self, request: RagQueryRequest, events: List[dict], answer: str) -> List[RagEventResult]:
        """Filter events that are relevant to the answer."""
        relevant = []
        answer_lower = answer.lower()
        
        for e in events:
            # Use the actual similarity score from vector search, default 0.0
            score = float(e.get('relevance_score', 0.0))
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
                        relevance_score=score,
                    ))
                except Exception as ex:
                    logger.warning(f"Failed to create RagEventResult: {ex}")
        
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

    async def get_embedding(self, text: str) -> List[float]:
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        v=[]
        for k in range(0,min(len(h),1536),4):
            v.append(((int(h[k:k+4],16)/(16**4-1))-0.5)*2)
        while len(v)<384: v.append(0.0)
        return v[:384]
    embed = get_embedding
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


class EventSearchTool:
    """
    Tool interface for searching approved campus events via the vector store.

    Only APPROVED events are ever returned, enforcing authorization at the
    tool level so the agent cannot expose draft/unpublished events.
    """

    name = "search_events"

    def __init__(self, vector_store: "SimpleVectorStore", db_session: Session):
        from app.services.vector_store import SimpleVectorStore  # lazy import (avoids circular import)
        if not isinstance(vector_store, SimpleVectorStore):
            raise TypeError("vector_store must be a SimpleVectorStore instance")
        self.vector_store = vector_store
        self.db = db_session

    def get_input_schema(self) -> dict:
        """Return the JSON Schema for the tool's input arguments."""
        return {
            "name": self.name,
            "description": "Search for approved campus events matching a natural language query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query about campus events",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional filter by event category",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        }

    def validate_args(self, args: dict) -> dict:
        """Validate and normalize tool arguments. Raises ValueError on invalid input."""
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be an object")
        query = args.get("query")
        if not query or not str(query).strip():
            raise ValueError("'query' is required and must be a non-empty string")
        query = str(query).strip()

        limit = args.get("limit", 10)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        category = args.get("category")
        if category is not None:
            category = str(category).strip()
            if not category:
                category = None

        return {"query": query, "limit": limit, "category": category}

    async def execute(self, args: dict) -> List[dict]:
        """
        Execute the search tool.

        Queries the vector store (which only contains APPROVED events) and
        re-verifies approval status against the database before returning.
        Never exposes draft, unpublished, or rejected events.
        """
        validated = self.validate_args(args)

        try:
            results = await self.vector_store.search(
                validated["query"],
                limit=validated["limit"],
                filters={"category": validated["category"]} if validated.get("category") else None,
            )
        except Exception as e:
            logger.warning(f"Vector store search failed: {e}")
            results = []

        events: List[dict] = []
        for emb, score in results:
            # Re-verify approval status in the database (authorization boundary)
            ev = (
                self.db.query(Event)
                .filter(Event.id == emb.event_id, Event.status == EventStatus.APPROVED)
                .first()
            )
            if not ev:
                continue
            events.append(
                {
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
                }
            )
        return events


class EventAssistantAgent:
    """
    Simple tool-using AI agent for answering questions about campus events.

    Workflow:
      1. Interpret the user's question.
      2. Invoke the EventSearchTool to retrieve relevant approved events.
      3. Use the AI provider to formulate a grounded answer from the results.
      4. Clearly state when information is unavailable.

    The agent never bypasses authorization: the search tool only returns
    APPROVED events, and unpublished/draft events are never exposed.
    """

    def __init__(self, provider: AiProvider, search_tool: EventSearchTool):
        self.provider = provider
        self.search_tool = search_tool

    async def run(self, query: str) -> RagQueryResponse:
        """
        Execute the agent workflow: search (tool) -> generate grounded answer.
        """
        start_time = time.time()

        # Step 2: Invoke the search tool to retrieve relevant approved events.
        try:
            tool_args = self.search_tool.validate_args({"query": query, "limit": 10})
            events_context = await self.search_tool.execute(tool_args)
        except ValueError as e:
            logger.warning(f"Invalid tool arguments: {e}")
            events_context = []
        except Exception as e:
            logger.error(f"Search tool execution failed: {type(e).__name__}: {e}")
            events_context = []

        # Step 3: Use the AI provider to formulate a grounded answer from results.
        rag_request = RagQueryRequest(query=query, limit=10)
        try:
            result = await self.provider.query_events(rag_request, events_context)
        except AiProviderError:
            # Provider error: return a graceful, honest answer.
            total_ms = int((time.time() - start_time) * 1000)
            return RagQueryResponse(
                answer="I'm unable to search for events right now because the AI service is unavailable. Please try again later.",
                events=[],
                query_time_ms=total_ms,
            )

        # Ensure timing is reported.
        if result.query_time_ms == 0:
            result.query_time_ms = int((time.time() - start_time) * 1000)
        return result


def create_agent(provider: AiProvider | None = None, db_session: Session | None = None) -> EventAssistantAgent:
    """Factory to build an EventAssistantAgent with default dependencies."""
    from app.services.vector_store import SimpleVectorStore  # lazy import (avoids circular import)
    if provider is None:
        provider = get_ai_provider()
    if db_session is None:
        db_session = SessionLocal()
    vs = SimpleVectorStore()
    tool = EventSearchTool(vector_store=vs, db_session=db_session)
    return EventAssistantAgent(provider=provider, search_tool=tool)


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