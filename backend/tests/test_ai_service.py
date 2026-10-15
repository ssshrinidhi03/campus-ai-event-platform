"""
Tests for AI Service
Mocked AI responses for deterministic automated tests.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from app.services.ai import (
    NavigateLabsProvider,
    MockAiProvider,
    get_ai_provider,
    AiProviderUnavailableError,
    AiProviderValidationError,
    AiProviderError,
    ProviderConfig,
)
from app.schemas.ai import (
    EventExtractionRequest,
    ExtractedEventData,
    ExtractionWarning,
    EventExtractionResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagEventResult,
    AiHealthResponse,
)


class TestMockAiProvider:
    """Tests for MockAiProvider."""

    @pytest.mark.asyncio
    async def test_extract_event_returns_valid_response(self):
        provider = MockAiProvider()
        request = EventExtractionRequest(text="Test announcement")
        
        result = await provider.extract_event(request)
        
        assert isinstance(result, EventExtractionResponse)
        assert result.extracted_data.title == "Mock Event"
        assert result.extracted_data.category == "Workshop"
        assert result.confidence == 0.9
        assert len(result.warnings) == 1
        assert result.warnings[0].field == "all"

    @pytest.mark.asyncio
    async def test_query_events_returns_valid_response(self):
        provider = MockAiProvider()
        request = RagQueryRequest(query="Find events")
        
        result = await provider.query_events(request, [])
        
        assert isinstance(result, RagQueryResponse)
        assert result.answer == "Mock RAG response for testing."
        assert result.events == []

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self):
        provider = MockAiProvider()
        
        result = await provider.health_check()
        
        assert isinstance(result, AiHealthResponse)
        assert result.status == "healthy"
        assert result.provider == "mock"
        assert result.api_reachable is True

    def test_get_config(self):
        provider = MockAiProvider()
        config = provider.get_config()
        
        assert isinstance(config, ProviderConfig)
        assert config.name == "mock"
        assert config.extraction_model == "mock"


class TestNavigateLabsProviderMocked:
    """Tests for NavigateLabsProvider with mocked HTTP responses."""

    @pytest.fixture
    def provider(self):
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.NAVIGATE_API_KEY = "test-api-key"
            mock_settings.NAVIGATE_API_BASE_URL = "https://api.test.com"
            mock_settings.NAVIGATE_MODEL_EXTRACTION = "test-model"
            mock_settings.NAVIGATE_MODEL_EMBEDDING = "test-embedding"
            provider = NavigateLabsProvider()
            return provider

    @pytest.mark.asyncio
    async def test_extract_event_with_mock_response(self, provider):
        """Test extraction when API key is not configured (uses mock)."""
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.NAVIGATE_API_KEY = None
            provider_no_key = NavigateLabsProvider()
            request = EventExtractionRequest(text="Test hackathon announcement")
            
            result = await provider_no_key.extract_event(request)
            
            assert isinstance(result, EventExtractionResponse)
            assert result.extracted_data.title == "AI Hackathon 2026"
            assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_extract_event_raises_when_no_api_key_and_no_mock_match(self, provider):
        """Test extraction returns mock with warnings when no API key and text doesn't match mock."""
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.NAVIGATE_API_KEY = None
            provider_no_key = NavigateLabsProvider()
            request = EventExtractionRequest(text="Random text about a seminar")
            
            result = await provider_no_key.extract_event(request)
            
            # When no API key and no mock match, it returns empty extracted data with warning
            assert result.extracted_data.title is None
            assert len(result.warnings) == 1
            assert "AI API key not configured" in result.warnings[0].message

    @pytest.mark.asyncio
    async def test_extract_event_successful_api_response(self, provider):
        """Test successful API response parsing."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "title": "Test Event",
                        "description": "Test description",
                        "category": "Workshop",
                        "venue": "Test Venue",
                        "date": "2026-10-20",
                        "start_time": "10:00",
                        "end_time": "12:00",
                        "tags": ["test", "workshop"],
                        "warnings": []
                    })
                }
            }]
        }
        
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = EventExtractionRequest(text="Test announcement")
            
            result = await provider.extract_event(request)
            
            assert result.extracted_data.title == "Test Event"
            assert result.extracted_data.category == "Workshop"
            assert result.extracted_data.venue == "Test Venue"
            assert result.extracted_data.date is not None
            assert result.extracted_data.start_time == "10:00"
            assert result.extracted_data.end_time == "12:00"
            assert "test" in result.extracted_data.tags

    @pytest.mark.asyncio
    async def test_extract_event_invalid_json_raises_validation_error(self, provider):
        """Test that invalid JSON from AI raises validation error."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "not valid json"
                }
            }]
        }
        
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = EventExtractionRequest(text="Test announcement")
            
            with pytest.raises(AiProviderValidationError):
                await provider.extract_event(request)

    @pytest.mark.asyncio
    async def test_extract_event_http_error_raises_provider_error(self, provider):
        """Test that HTTP errors raise provider error."""
        import httpx
        
        # Create a proper mock response object
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_request = Mock()
        mock_request.url = "https://api.test.com/chat/completions"
        
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_make_request:
            mock_make_request.side_effect = httpx.HTTPStatusError(
                "Server Error", request=mock_request, response=mock_response
            )
            request = EventExtractionRequest(text="Test announcement")
            
            with pytest.raises(AiProviderError):
                await provider.extract_event(request)

    @pytest.mark.asyncio
    async def test_extract_event_timeout_raises_provider_error(self, provider):
        """Test that timeout raises provider error."""
        import httpx
        
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Timeout")
            request = EventExtractionRequest(text="Test announcement")
            
            with pytest.raises(AiProviderError):
                await provider.extract_event(request)

    @pytest.mark.asyncio
    async def test_query_events_successful(self, provider):
        """Test successful RAG query."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "The AI Hackathon event is happening on October 20th."
                }
            }]
        }
        
        events_context = [{
            "id": 1,
            "title": "AI Hackathon",
            "category": "Hackathon",
            "date": "2026-10-20T00:00:00",
            "venue": "Main Auditorium",
            "organizer_name": "AI Club",
            "tags": ["AI", "Hackathon"]
        }]
        
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = RagQueryRequest(query="AI Hackathon")
            
            result = await provider.query_events(request, events_context)
            
            assert "hackathon" in result.answer.lower()
            assert len(result.events) == 1
            assert result.events[0].title == "AI Hackathon"

    @pytest.mark.asyncio
    async def test_health_check_with_api_key(self, provider):
        """Test health check when API key is configured."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Mock(status_code=200)
            
            result = await provider.health_check()
            
            assert result.status == "healthy"
            assert result.api_reachable is True
            assert result.provider == "navigate_labs"

    @pytest.mark.asyncio
    async def test_health_check_unreachable(self, provider):
        """Test health check when API is unreachable."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            
            result = await provider.health_check()
            
            assert result.status == "degraded"
            assert result.api_reachable is False

    def test_parse_datetime_valid(self, provider):
        """Test datetime parsing with valid formats."""
        result = provider._parse_datetime("2026-10-20T10:30:00")
        assert result == datetime(2026, 10, 20, 10, 30)
        result = provider._parse_datetime("2026-10-20T10:30:00Z")
        assert result is not None
        assert result.year == 2026 and result.month == 10 and result.day == 20 and result.hour == 10 and result.minute == 30
        result = provider._parse_datetime("2026-10-20T10:30:00+00:00")
        assert result is not None
        assert result.year == 2026 and result.month == 10 and result.day == 20 and result.hour == 10 and result.minute == 30

    def test_parse_datetime_invalid(self, provider):
        """Test datetime parsing with invalid formats."""
        assert provider._parse_datetime("invalid") is None
        assert provider._parse_datetime(None) is None
        assert provider._parse_datetime("") is None

    def test_parse_date_valid(self, provider):
        """Test date parsing with valid formats."""
        result = provider._parse_date("2026-10-20")
        assert result == datetime(2026, 10, 20, 0, 0)
        result = provider._parse_date("2026-10-20T00:00:00")
        assert result == datetime(2026, 10, 20, 0, 0)

    def test_validate_category(self, provider):
        """Test category validation."""
        assert provider._validate_category("Workshop") == "Workshop"
        assert provider._validate_category("workshop") == "Workshop"
        assert provider._validate_category("HACKATHON") == "Hackathon"
        assert provider._validate_category("Invalid") == "Other"
        assert provider._validate_category(None) is None

    def test_validate_time(self, provider):
        """Test time validation."""
        assert provider._validate_time("10:00") == "10:00"
        assert provider._validate_time("09:30") == "09:30"
        assert provider._validate_time("23:59") == "23:59"
        assert provider._validate_time("24:00") is None
        assert provider._validate_time("10:60") is None
        assert provider._validate_time("invalid") is None
        assert provider._validate_time(None) is None

    def test_validate_tags(self, provider):
        """Test tags validation."""
        assert provider._validate_tags(["tag1", "tag2"]) == ["tag1", "tag2"]
        assert provider._validate_tags("tag1, tag2, tag3") == ["tag1", "tag2", "tag3"]
        assert provider._validate_tags([]) == []
        assert provider._validate_tags(None) == []
        assert provider._validate_tags("  ") == []

    def test_validate_capacity(self, provider):
        """Test capacity validation."""
        assert provider._validate_capacity(100) == 100
        assert provider._validate_capacity("50") == 50
        assert provider._validate_capacity(0) is None
        assert provider._validate_capacity(-10) is None
        assert provider._validate_capacity("invalid") is None
        assert provider._validate_capacity(None) is None

    def test_validate_url(self, provider):
        """Test URL validation."""
        assert provider._validate_url("https://example.com") == "https://example.com"
        assert provider._validate_url("http://example.com") == "http://example.com"
        assert provider._validate_url("ftp://example.com") is None
        assert provider._validate_url("invalid") is None
        assert provider._validate_url(None) is None

    def test_validate_email(self, provider):
        """Test email validation."""
        assert provider._validate_email("test@example.com") == "test@example.com"
        assert provider._validate_email("user.name@domain.org") == "user.name@domain.org"
        assert provider._validate_email("invalid") is None
        assert provider._validate_email("no@domain") is None
        assert provider._validate_email(None) is None


class TestGetAiProvider:
    """Tests for get_ai_provider factory function."""

    def test_get_mock_provider_when_configured(self):
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "mock"
            mock_settings.NAVIGATE_API_KEY = None
            
            provider = get_ai_provider()
            
            assert isinstance(provider, MockAiProvider)

    def test_get_navigate_labs_when_configured(self):
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.AI_PROVIDER = "navigate_labs"
            mock_settings.NAVIGATE_API_KEY = "test-key"
            
            provider = get_ai_provider()
            
            assert isinstance(provider, NavigateLabsProvider)

    def test_get_navigate_labs_when_key_exists_no_provider_set(self):
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.AI_PROVIDER = ""
            mock_settings.NAVIGATE_API_KEY = "test-key"
            
            provider = get_ai_provider()
            
            assert isinstance(provider, NavigateLabsProvider)

    def test_get_mock_when_no_key_and_no_provider_set(self):
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.AI_PROVIDER = ""
            mock_settings.NAVIGATE_API_KEY = None
            
            provider = get_ai_provider()
            
            assert isinstance(provider, MockAiProvider)


# Import json for test
import json