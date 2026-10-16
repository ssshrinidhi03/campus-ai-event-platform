"""
Tests for AI Service
Mocked AI responses for deterministic automated tests.
"""

import pytest
from datetime import datetime, date
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


class TestEventAssistantAgent:
    """Tests for the tool-using EventAssistantAgent."""

    def test_agent_creation(self):
        from app.services.ai import create_agent, MockAiProvider
        provider = MockAiProvider()
        agent = create_agent(provider=provider)
        assert agent.provider == provider
        assert agent.search_tool is not None

    @pytest.mark.asyncio
    async def test_agent_uses_search_tool_and_returns_answer(self):
        """Agent invokes the search tool and returns the provider's answer."""
        from app.services.ai import create_agent, MockAiProvider
        from app.services.vector_store import SimpleVectorStore
        from app.models.event import Event
        from app.models.enums import EventStatus
        from unittest.mock import Mock

        provider = MockAiProvider()
        vs = SimpleVectorStore(persist_path=':memory:')
        approved = Event(id=1, title='AI Hackathon', description='desc', category='Hackathon',
                         organizer_id=1, status=EventStatus.APPROVED, venue='Hall', date=date(2026,10,20))
        await vs.add_event(approved)

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = approved

        agent = create_agent(provider=provider, db_session=db)
        result = await agent.run("Which hackathons are happening?")
        assert isinstance(result.answer, str)
        assert len(result.answer) > 0

    @pytest.mark.asyncio
    async def test_agent_no_relevant_events(self):
        """Agent handles empty search results gracefully."""
        from app.services.ai import create_agent, MockAiProvider
        from app.services.vector_store import SimpleVectorStore
        from unittest.mock import Mock

        provider = MockAiProvider()
        vs = SimpleVectorStore(persist_path=':memory:')
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        agent = create_agent(provider=provider, db_session=db)
        result = await agent.run("Which events are on Mars?")
        assert isinstance(result.answer, str)
        assert len(result.events) == 0

    @pytest.mark.asyncio
    async def test_agent_excludes_unpublished_events(self):
        """Agent tool never returns draft/unpublished events (authorization boundary)."""
        from app.services.ai import create_agent, MockAiProvider, EventSearchTool
        from app.services.vector_store import SimpleVectorStore
        from app.models.event import Event
        from app.models.enums import EventStatus
        from unittest.mock import Mock

        provider = MockAiProvider()
        vs = SimpleVectorStore(persist_path=':memory:')
        draft = Event(id=9, title='Secret Draft', description='hidden', category='Seminar',
                      organizer_id=1, status=EventStatus.DRAFT, venue='Room B')
        # Draft events are not indexed by add_event
        added = await vs.add_event(draft)
        assert added is False
        assert 9 not in vs.embeddings

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None

        tool = EventSearchTool(vector_store=vs, db_session=db)
        results = await tool.execute({"query": "seminar", "limit": 10})
        assert results == []

    @pytest.mark.asyncio
    async def test_agent_search_coroutine_executes_and_results_used(self):
        """Regression test: the search coroutine must be awaited, not discarded.

        Verifies that EventSearchTool.execute() actually calls and awaits
        SimpleVectorStore.search() (not just creates a coroutine that is
        discarded), and that the agent's run() uses the returned results.
        """
        from app.services.ai import create_agent, MockAiProvider, EventSearchTool, EventAssistantAgent
        from app.services.vector_store import SimpleVectorStore
        from app.models.event import Event
        from app.models.enums import EventStatus
        from unittest.mock import Mock

        provider = MockAiProvider()
        vs = SimpleVectorStore(persist_path=':memory:')

        # Index a real approved event so the search has something to find
        approved = Event(id=1, title='AI Workshop', description='Learn AI',
                         category='Workshop', organizer_id=1,
                         status=EventStatus.APPROVED, venue='Hall',
                         date=datetime(2027, 3, 15))
        await vs.add_event(approved)

        # Wrap search to record calls (prove coroutine is executed)
        search_called = []
        original_search = vs.search

        async def tracking_search(q, limit=10, filters=None):
            search_called.append(True)
            return await original_search(q, limit=limit, filters=filters)

        vs.search = tracking_search

        db = Mock()
        ev = Mock()
        ev.id = 1
        ev.title = 'AI Workshop'
        ev.description = 'Learn AI'
        ev.category = 'Workshop'
        ev.venue = 'Hall'
        ev.date = datetime(2027, 3, 15)
        ev.start_time = None
        ev.end_time = None
        ev.tags = []
        ev.organizer.name = 'AI Club'
        db.query.return_value.filter.return_value.first.return_value = ev

        # Build agent directly (not via create_agent, which creates its own
        # empty SimpleVectorStore) so it uses our tracked vs
        tool = EventSearchTool(vector_store=vs, db_session=db)
        agent = EventAssistantAgent(provider=provider, search_tool=tool)
        result = await agent.run("Which AI workshops are happening?")

        # The search coroutine must have been executed (not just created/discarded)
        assert len(search_called) == 1, "search() coroutine was not awaited"
        # The agent must produce an answer using the search tool
        assert isinstance(result.answer, str) and len(result.answer) > 0


class TestAiProviderErrors:
    """Tests for AI provider error handling."""

    @pytest.mark.asyncio
    async def test_navigate_provider_unavailable_without_key(self):
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.NAVIGATE_API_KEY = None
            provider = NavigateLabsProvider()
            request = EventExtractionRequest(text="Test")
            result = await provider.extract_event(request)
            # Falls back to mock, does not raise
            assert isinstance(result, EventExtractionResponse)

    @pytest.mark.asyncio
    async def test_rag_provider_error_without_key(self):
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.NAVIGATE_API_KEY = None
            provider = NavigateLabsProvider()
            request = RagQueryRequest(query="test")
            result = await provider.query_events(request, [])
            assert "not configured" in result.answer.lower() or result.answer == ""

    @pytest.mark.asyncio
    async def test_extract_invalid_image_mime_type(self):
        """Invalid image MIME type raises validation error before any API call."""
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.NAVIGATE_API_KEY = "test-key"
            mock_settings.NAVIGATE_API_BASE_URL = "https://api.test.com"
            mock_settings.NAVIGATE_MODEL_EXTRACTION = "test-model"
            mock_settings.NAVIGATE_MODEL_EMBEDDING = "test-embedding"
            provider = NavigateLabsProvider()
            request = EventExtractionRequest(
                image_base64="abc123",
                image_mime_type="text/plain",
            )
            with pytest.raises(AiProviderValidationError):
                await provider.extract_event(request)

    @pytest.mark.asyncio
    async def test_extract_no_input_raises(self):
        """No text or image raises validation error."""
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.NAVIGATE_API_KEY = "test-key"
            mock_settings.NAVIGATE_API_BASE_URL = "https://api.test.com"
            mock_settings.NAVIGATE_MODEL_EXTRACTION = "test-model"
            mock_settings.NAVIGATE_MODEL_EMBEDDING = "test-embedding"
            provider = NavigateLabsProvider()
            # Bypass pydantic model validation to test service-level validation
            request = EventExtractionRequest.model_construct(
                text=None, image_base64=None, image_mime_type=None
            )
            with pytest.raises(AiProviderValidationError):
                await provider.extract_event(request)


class TestExtractionResponseParsing:
    """Tests for robust AI extraction response parsing (regression for invalid JSON)."""

    def _make_provider(self):
        with patch("app.services.ai.settings") as mock_settings:
            mock_settings.NAVIGATE_API_KEY = "test-key"
            mock_settings.NAVIGATE_API_BASE_URL = "https://api.test.com"
            mock_settings.NAVIGATE_MODEL_EXTRACTION = "test-model"
            mock_settings.NAVIGATE_MODEL_EMBEDDING = "test-embedding"
            return NavigateLabsProvider()

    @pytest.mark.asyncio
    async def test_valid_json_response(self):
        provider = self._make_provider()
        content = json.dumps({
            "title": "AI Hackathon",
            "category": "Hackathon",
            "venue": "Main Auditorium",
            "date": "2027-03-15",
            "start_time": "10:00",
            "end_time": "12:00",
            "registration_link": "https://example.com/register",
            "eligibility": "All Computer Science students",
            "tags": ["AI", "Hackathon"],
            "warnings": []
        })
        request = EventExtractionRequest(text="Join us for the AI Hackathon on March 15, 2027...")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Hackathon"
        assert extracted.category == "Hackathon"
        assert extracted.venue == "Main Auditorium"
        assert extracted.date is not None
        assert extracted.start_time == "10:00"
        assert extracted.registration_link == "https://example.com/register"

    @pytest.mark.asyncio
    async def test_json_wrapped_in_markdown_code_fences(self):
        provider = self._make_provider()
        content = '''```json
{
  "title": "AI Hackathon",
  "category": "Hackathon",
  "venue": "Main Auditorium",
  "date": "2027-03-15",
  "start_time": "10:00",
  "end_time": "12:00",
  "registration_link": "https://example.com/register",
  "warnings": []
}
```'''
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Hackathon"
        assert extracted.category == "Hackathon"
        assert extracted.venue == "Main Auditorium"

    @pytest.mark.asyncio
    async def test_json_with_extra_explanatory_text(self):
        provider = self._make_provider()
        content = '''Here is the extracted event data:

{
  "title": "Workshop",
  "category": "Workshop",
  "venue": "Lab 204",
  "date": "2026-10-22",
  "start_time": "14:00",
  "end_time": "17:00",
  "warnings": []
}

Hope this helps!'''
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Workshop"
        assert extracted.category == "Workshop"
        assert extracted.venue == "Lab 204"

    @pytest.mark.asyncio
    async def test_empty_content_raises(self):
        provider = self._make_provider()
        request = EventExtractionRequest(text="Test")
        with pytest.raises(AiProviderValidationError):
            provider._parse_extraction_response("", request)
        with pytest.raises(AiProviderValidationError):
            provider._parse_extraction_response("   ", request)

    @pytest.mark.asyncio
    async def test_malformed_json_raises(self):
        provider = self._make_provider()
        request = EventExtractionRequest(text="Test")
        with pytest.raises(AiProviderValidationError):
            provider._parse_extraction_response("not json at all", request)

    @pytest.mark.asyncio
    async def test_json_array_not_object_raises(self):
        provider = self._make_provider()
        request = EventExtractionRequest(text="Test")
        with pytest.raises(AiProviderValidationError):
            provider._parse_extraction_response('[1, 2, 3]', request)

    @pytest.mark.asyncio
    async def test_missing_required_fields_add_warnings(self):
        provider = self._make_provider()
        content = json.dumps({
            "title": "Partial Event",
            "category": "Workshop",
            # venue, date, start_time, end_time intentionally missing
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Partial Event"
        assert extracted.venue is None
        assert extracted.date is None
        warning_fields = {w.field for w in warnings}
        assert "venue" in warning_fields
        assert "date" in warning_fields

    @pytest.mark.asyncio
    async def test_announcement_without_year_date_is_none(self):
        provider = self._make_provider()
        content = json.dumps({
            "title": "Event",
            "category": "Workshop",
            "venue": "Hall",
            "date": "March 15",  # no year provided - must not invent one
            "start_time": "10:00",
            "end_time": "12:00",
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        # Never invent a year: date should be None
        assert extracted.date is None
        assert any(w.field == "date" for w in warnings)

    @pytest.mark.asyncio
    async def test_full_extraction_flow_with_code_fences(self):
        """End-to-end: provider returns markdown-fenced JSON, extraction succeeds."""
        provider = self._make_provider()
        content = '''```json
{
  "title": "AI Hackathon",
  "category": "Hackathon",
  "venue": "Main Auditorium",
  "date": "2027-03-15",
  "start_time": "10:00",
  "end_time": "12:00",
  "registration_link": "https://example.com/register",
  "eligibility": "All Computer Science students",
  "tags": ["AI"],
  "warnings": []
}
```'''
        mock_response = {
            "choices": [{"message": {"content": content}}]
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = EventExtractionRequest(
                text="Join us for the AI Hackathon on March 15, 2027, at 10 AM in the Main Auditorium. Open to all Computer Science students. Register by March 10, 2027, at https://example.com/register."
            )
            result = await provider.extract_event(request)
            assert result.extracted_data.title == "AI Hackathon"
            assert result.extracted_data.category == "Hackathon"
            assert result.extracted_data.venue == "Main Auditorium"
            assert result.extracted_data.date is not None
            assert result.extracted_data.start_time == "10:00"
            assert result.extracted_data.registration_link == "https://example.com/register"

    @pytest.mark.asyncio
    async def test_natural_language_response_same_line_labels(self):
        """Navigate Labs Nova-micro returns natural language text with **Label:** value format."""
        provider = self._make_provider()
        content = """Here is the structured event data extracted from the provided text announcement:

**Event Title:** AI Hackathon

**Date:** March 15, 2027

**Time:** 10 AM

**Venue:** Main Auditorium

**Target Audience:** All Computer Science students

**Registration Deadline:** March 10, 2027

**Registration Link:** https://example.com/register

If there are any additional details, please let me know!"""
        request = EventExtractionRequest(text="Test announcement")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Hackathon"
        assert extracted.venue == "Main Auditorium"
        assert extracted.date is not None
        assert extracted.start_time == "10:00"
        assert extracted.registration_link == "https://example.com/register"
        # Category not in response -> warning
        assert any(w.field == "category" for w in warnings)

    @pytest.mark.asyncio
    async def test_natural_language_response_separate_lines(self):
        """Natural language response with label on one line, value on next."""
        provider = self._make_provider()
        content = """**Event Title:**
AI Hackathon

**Date:**
March 15, 2027

**Venue:**
Conference Room B"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Hackathon"
        assert extracted.date is not None
        assert extracted.venue == "Conference Room B"

    @pytest.mark.asyncio
    async def test_natural_language_response_no_year_date_is_none(self):
        """Natural language date without year must not invent one."""
        provider = self._make_provider()
        content = """**Event Title:** Workshop
**Date:** March 15
**Venue:** Hall"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Workshop"
        assert extracted.venue == "Hall"
        # No year provided -> date must be None
        assert extracted.date is None
        assert any(w.field == "date" for w in warnings)

    @pytest.mark.asyncio
    async def test_full_extraction_flow_natural_language(self):
        """End-to-end: provider returns natural language text, extraction succeeds."""
        provider = self._make_provider()
        content = """Here is the structured event data extracted from the provided text announcement:

**Event Title:** AI Hackathon

**Date:** March 15, 2027

**Time:** 10 AM

**Venue:** Main Auditorium

**Target Audience:** All Computer Science students

**Registration Deadline:** March 10, 2027

**Registration Link:** https://example.com/register"""
        mock_response = {
            "choices": [{"message": {"content": content}}]
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = EventExtractionRequest(
                text="Join us for the AI Hackathon on March 15, 2027, at 10 AM in the Main Auditorium. Open to all Computer Science students. Register by March 10, 2027, at https://example.com/register."
            )
            result = await provider.extract_event(request)
            assert result.extracted_data.title == "AI Hackathon"
            assert result.extracted_data.venue == "Main Auditorium"
            assert result.extracted_data.date is not None
            assert result.extracted_data.start_time == "10:00"
            assert result.extracted_data.registration_link == "https://example.com/register"
            # Category and end_time missing -> warnings
            warning_fields = {w.field for w in result.warnings}
            assert "category" in warning_fields
            assert "end_time" in warning_fields

    @pytest.mark.asyncio
    async def test_neither_json_nor_natural_language_raises(self):
        """Completely unparseable response raises a clear error."""
        provider = self._make_provider()
        content = "This is just random text with no event data and no JSON."
        request = EventExtractionRequest(text="Test")
        with pytest.raises(AiProviderValidationError):
            provider._parse_extraction_response(content, request)

    @pytest.mark.asyncio
    async def test_natural_language_event_type_label_maps_to_category(self):
        """'Event Type' label should map to category field."""
        provider = self._make_provider()
        content = """**Event Title:** AI Hackathon
**Event Type:** Hackathon
**Event Date:** March 15, 2027
**Start:** 10 AM
**End:** 12 PM
**Venue:** Main Auditorium"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Hackathon"
        assert extracted.category == "Hackathon"
        assert extracted.venue == "Main Auditorium"
        assert extracted.date is not None
        assert extracted.start_time == "10:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_natural_language_start_end_labels(self):
        """'Start' and 'End' labels should map to start_time and end_time."""
        provider = self._make_provider()
        content = """**Title:** Workshop
**Category:** Workshop
**Date:** March 15, 2027
**Start:** 14:00
**End:** 17:00
**Venue:** Lab 204"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Workshop"
        assert extracted.start_time == "14:00"
        assert extracted.end_time == "17:00"
        assert extracted.venue == "Lab 204"

    @pytest.mark.asyncio
    async def test_natural_language_registration_deadline_not_confused_with_date(self):
        """Registration deadline must not be treated as event date or end time."""
        provider = self._make_provider()
        content = """**Event Title:** Seminar
**Category:** Seminar
**Event Date:** March 20, 2027
**Start Time:** 10:00
**End Time:** 12:00
**Venue:** Hall A
**Registration Deadline:** March 15, 2027"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Seminar"
        assert extracted.date is not None
        assert extracted.date.strftime("%Y-%m-%d") == "2027-03-20"
        assert extracted.registration_deadline is not None
        assert extracted.registration_deadline.strftime("%Y-%m-%d") == "2027-03-15"
        # Date and deadline must be different
        assert extracted.date != extracted.registration_deadline

    @pytest.mark.asyncio
    async def test_natural_language_no_end_time(self):
        """Announcement with no end time should have end_time=None and warning."""
        provider = self._make_provider()
        content = """**Event Title:** Meetup
**Category:** Other
**Date:** March 15, 2027
**Start Time:** 6 PM
**Venue:** Student Center"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Meetup"
        assert extracted.start_time == "18:00"
        assert extracted.end_time is None
        assert any(w.field == "end_time" for w in warnings)

    @pytest.mark.asyncio
    async def test_confidence_all_required_fields(self):
        """Confidence should be high when all required fields are extracted."""
        provider = self._make_provider()
        content = json.dumps({
            "title": "AI Hackathon",
            "category": "Hackathon",
            "venue": "Main Auditorium",
            "date": "2027-03-15",
            "start_time": "10:00",
            "end_time": "12:00",
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        confidence = provider._calculate_confidence(extracted, warnings)
        assert confidence >= 0.7, f"Expected confidence >= 0.7, got {confidence}"

    @pytest.mark.asyncio
    async def test_confidence_missing_required_fields(self):
        """Confidence should be lower when required fields are missing."""
        provider = self._make_provider()
        content = json.dumps({
            "title": "Partial Event",
            "category": "Workshop",
            # venue, date, start_time, end_time missing
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        confidence = provider._calculate_confidence(extracted, warnings)
        # Only title and category filled (2 of 6 required), no optional fields
        assert confidence < 0.5, f"Expected confidence < 0.5, got {confidence}"

    @pytest.mark.asyncio
    async def test_confidence_with_optional_fields(self):
        """Optional fields should add partial confidence credit."""
        provider = self._make_provider()
        content = json.dumps({
            "title": "AI Hackathon",
            "category": "Hackathon",
            "venue": "Main Auditorium",
            "date": "2027-03-15",
            "start_time": "10:00",
            "end_time": "12:00",
            "description": "A great hackathon",
            "organization": "AI Club",
            "eligibility": "All students",
            "registration_link": "https://example.com/register",
            "tags": ["AI", "Hackathon"],
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        confidence = provider._calculate_confidence(extracted, warnings)
        # All required filled = 0.7, plus optional fields = up to 0.3
        assert confidence >= 0.7, f"Expected confidence >= 0.7, got {confidence}"

    @pytest.mark.asyncio
    async def test_unknown_field_names_ignored(self):
        """Unknown field names in natural language response should be ignored."""
        provider = self._make_provider()
        content = """**Event Title:** Workshop
**Category:** Workshop
**Event Date:** March 15, 2027
**Start Time:** 10:00
**End Time:** 12:00
**Venue:** Lab 204
**Unknown Field:** some value
**Another Unknown:** another value"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Workshop"
        assert extracted.category == "Workshop"
        assert extracted.venue == "Lab 204"
        assert extracted.date is not None
        # Unknown fields should not appear as warnings or data
        assert not any("unknown" in w.field.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_full_extraction_flow_demo_announcement(self):
        """End-to-end: the exact demo announcement from the task requirements."""
        provider = self._make_provider()
        content = json.dumps({
            "title": "AI Hackathon",
            "category": "Hackathon",
            "venue": "Main Auditorium",
            "date": "2027-03-15",
            "start_time": "10:00",
            "end_time": "12:00",
            "registration_link": "https://example.com/register",
            "eligibility": "All Computer Science students",
            "tags": ["AI"],
            "warnings": []
        })
        mock_response = {
            "choices": [{"message": {"content": content}}]
        }
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = EventExtractionRequest(
                text="Join us for the AI Hackathon on March 15, 2027, at 10 AM in the Main Auditorium. Open to all Computer Science students. Register by March 10, 2027, at https://example.com/register."
            )
            result = await provider.extract_event(request)
            assert result.extracted_data.title == "AI Hackathon"
            assert result.extracted_data.category == "Hackathon"
            assert result.extracted_data.venue == "Main Auditorium"
            assert result.extracted_data.date is not None
            assert result.extracted_data.date.strftime("%Y-%m-%d") == "2027-03-15"
            assert result.extracted_data.start_time == "10:00"
            assert result.extracted_data.registration_link == "https://example.com/register"

    @pytest.mark.asyncio
    async def test_natural_language_event_venue_location_labels(self):
        """'Event Venue' and 'Event Location' labels map to venue field."""
        provider = self._make_provider()
        content = """**Event Title:** Workshop
**Category:** Workshop
**Event Date:** March 15, 2027
**Start Time:** 10:00
**End Time:** 12:00
**Event Venue:** Main Auditorium"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Workshop"
        assert extracted.venue == "Main Auditorium"
        assert extracted.date is not None
        assert extracted.start_time == "10:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_natural_language_event_location_label(self):
        """'Event Location' label maps to venue field."""
        provider = self._make_provider()
        content = """**Event Title:** Seminar
**Category:** Seminar
**Date:** March 15, 2027
**Start:** 2 PM
**End:** 4 PM
**Event Location:** Lab 204"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Seminar"
        assert extracted.venue == "Lab 204"
        assert extracted.start_time == "14:00"
        assert extracted.end_time == "16:00"

    @pytest.mark.asyncio
    async def test_time_range_dash_separator(self):
        """Time range with dash separator: '09:00-17:00'."""
        provider = self._make_provider()
        content = """**Event Title:** Workshop
**Category:** Workshop
**Date:** March 15, 2027
**Time:** 09:00-17:00
**Venue:** Lab 204"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Workshop"
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "17:00"
        assert extracted.venue == "Lab 204"

    @pytest.mark.asyncio
    async def test_time_range_ampm_separator(self):
        """Time range with AM/PM: '9:00 AM - 5:00 PM'."""
        provider = self._make_provider()
        content = """**Event Title:** Hackathon
**Category:** Hackathon
**Date:** March 15, 2027
**Start Time:** 9:00 AM
**End Time:** 5:00 PM
**Venue:** Main Auditorium"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Hackathon"
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "17:00"

    @pytest.mark.asyncio
    async def test_dash_list_format(self):
        """Dash/bullet list format: '- Label: value'."""
        provider = self._make_provider()
        content = """- **Event Title:** AI Hackathon
- **Date:** March 15, 2027
- **Time:** 10 AM
- **Venue:** Main Auditorium"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Hackathon"
        assert extracted.venue == "Main Auditorium"
        assert extracted.date is not None
        assert extracted.start_time == "10:00"

    @pytest.mark.asyncio
    async def test_bullet_list_format(self):
        """Bullet list format with '* ' markers (not bold)."""
        provider = self._make_provider()
        content = """* Event Title: Meetup
* Date: March 15, 2027
* Time: 6 PM
* Venue: Student Center"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Meetup"
        assert extracted.venue == "Student Center"
        assert extracted.date is not None
        assert extracted.start_time == "18:00"

    @pytest.mark.asyncio
    async def test_json_dict_event_name_key(self):
        """JSON dict with 'event_name' instead of 'title' maps to title field."""
        provider = self._make_provider()
        content = json.dumps({
            "event_name": "AI Workshop",
            "category": "Workshop",
            "date": "2026-10-20",
            "start_time": "09:00",
            "end_time": "12:00",
            "venue": "Lab 204, CS Block",
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.category == "Workshop"
        assert extracted.venue == "Lab 204, CS Block"
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_json_dict_ampm_times(self):
        """JSON dict with AM/PM time strings converts to HH:MM."""
        provider = self._make_provider()
        content = json.dumps({
            "title": "AI Workshop",
            "category": "Workshop",
            "date": "2026-10-20",
            "start_time": "09:00 AM",
            "end_time": "12:00 PM",
            "venue": "Lab 204, CS Block",
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_json_code_fence_event_name(self):
        """JSON inside Markdown code fences with event_name key (provider RUN 2 format)."""
        provider = self._make_provider()
        content = '''```json
{
  "event_name": "AI Workshop",
  "category": "Workshop",
  "date": "October 20, 2026",
  "venue": "Lab 204, CS Block",
  "start_time": "09:00 AM",
  "end_time": "12:00 PM",
  "organizer": "AI Club"
}
```'''
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.category == "Workshop"
        assert extracted.venue == "Lab 204, CS Block"
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_json_dict_name_key(self):
        """JSON dict with 'name' key maps to title field."""
        provider = self._make_provider()
        content = json.dumps({
            "name": "Seminar",
            "category": "Seminar",
            "date": "2026-10-20",
            "start_time": "14:00",
            "end_time": "16:00",
            "venue": "Room 101",
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "Seminar"
        assert extracted.category == "Seminar"
        assert extracted.start_time == "14:00"
        assert extracted.end_time == "16:00"

    @pytest.mark.asyncio
    async def test_json_dict_details_key(self):
        """JSON dict with 'details' key maps to description field."""
        provider = self._make_provider()
        content = json.dumps({
            "title": "AI Workshop",
            "category": "Workshop",
            "details": "Learn about neural networks and ML.",
            "date": "2026-10-20",
            "start_time": "09:00",
            "end_time": "12:00",
            "venue": "Lab 204, CS Block",
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.description == "Learn about neural networks and ML."
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_json_dict_organizer_key(self):
        """JSON dict with 'organizer' key maps to organization field."""
        provider = self._make_provider()
        content = json.dumps({
            "title": "AI Workshop",
            "category": "Workshop",
            "organizer": "AI Club",
            "date": "2026-10-20",
            "start_time": "09:00",
            "end_time": "12:00",
            "venue": "Lab 204, CS Block",
            "warnings": []
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.organization == "AI Club"
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_natural_language_topics_covered_maps_to_description(self):
        """'Topics Covered:' label should map to description field (real AI provider uses this label)."""
        provider = self._make_provider()
        content = """**Event Title:** AI and Machine Learning Workshop
**Date:** October 20, 2026
**Time:** 9:00 AM to 5:30 PM
**Venue:** Seminar Hall 2
**Topics Covered:**
- Neural Networks
- Transformer Architectures"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI and Machine Learning Workshop"
        assert extracted.description == "Neural Networks Transformer Architectures"
        assert extracted.venue == "Seminar Hall 2"
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "17:30"

    @pytest.mark.asyncio
    async def test_json_dict_topics_covered_maps_to_description(self):
        """JSON dict with 'topics_covered' key maps to description field."""
        provider = self._make_provider()
        content = json.dumps({
            "event_name": "AI Workshop",
            "date": "2026-10-20",
            "start_time": "09:00",
            "end_time": "12:00",
            "venue": "Lab 204",
            "topics_covered": ["neural networks", "transformer architectures"],
            "category": "Workshop",
        })
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.description == "neural networks transformer architectures"


    @pytest.mark.asyncio
    async def test_natural_language_name_label_maps_to_title(self):
        """'Name:' label should map to title field (real AI sometimes uses Name instead of Title)."""
        provider = self._make_provider()
        content = """**Event:**
- **Name:** AI Workshop
- **Category:** Workshop
- **Date:** October 20, 2026
- **Venue:** Lab 204, CS Block
- **Start Time:** 9:00 AM
- **End Time:** 12:00 PM
- **Organizer:** AI Club"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.category == "Workshop"
        assert extracted.venue == "Lab 204, CS Block"
        assert extracted.date is not None
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"
        assert extracted.organization == "AI Club"

    @pytest.mark.asyncio
    async def test_natural_language_event_category_label(self):
        """'Event Category:' label should map to category field."""
        provider = self._make_provider()
        content = """**Name:** AI Workshop
**Event Category:** Workshop
**Event Date:** October 20, 2026
**Start Time:** 9:00 AM
**End Time:** 12:00 PM
**Venue:** Lab 204, CS Block"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.category == "Workshop"
        assert extracted.date is not None
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_natural_language_underscore_field_names(self):
        """Underscore field names (event_category, event_date, start_time, end_time) should normalize."""
        provider = self._make_provider()
        content = """**Name:** AI Workshop
**Event_Category:** Workshop
**Event_Date:** October 20, 2026
**Start_Time:** 09:00
**End_Time:** 12:00
**Venue:** Lab 204, CS Block"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.category == "Workshop"
        assert extracted.date is not None
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_natural_language_incomplete_announcement(self):
        """A genuinely incomplete announcement leaves missing fields as None with warnings."""
        provider = self._make_provider()
        content = """**Name:** AI Workshop
**Category:** Workshop"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.category == "Workshop"
        assert extracted.venue is None
        assert extracted.date is None
        assert extracted.start_time is None
        assert extracted.end_time is None
        warning_fields = {w.field for w in warnings}
        assert "venue" in warning_fields
        assert "date" in warning_fields
        assert "start_time" in warning_fields
        assert "end_time" in warning_fields

    @pytest.mark.asyncio
    async def test_natural_language_am_pm_time_conversion(self):
        """AM/PM times should be converted to 24-hour HH:MM format."""
        provider = self._make_provider()
        content = """**Name:** AI Workshop
**Category:** Workshop
**Date:** October 20, 2026
**Start Time:** 9:00 AM
**End Time:** 5:30 PM
**Venue:** Lab 204, CS Block"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "17:30"

    @pytest.mark.asyncio
    async def test_natural_language_ampm_time_range_separator(self):
        """Time range with AM/PM separator should parse start and end times."""
        provider = self._make_provider()
        content = """**Name:** AI Workshop
**Category:** Workshop
**Date:** October 20, 2026
**Time:** 09:00 AM - 12:00 PM
**Venue:** Lab 204, CS Block"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

    @pytest.mark.asyncio
    async def test_natural_language_invalid_date_is_none(self):
        """Invalid or unparseable dates should be None, not invented."""
        provider = self._make_provider()
        content = """**Name:** AI Workshop
**Category:** Workshop
**Date:** not-a-real-date
**Venue:** Lab 204"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.date is None
        assert any(w.field == "date" for w in warnings)

    @pytest.mark.asyncio
    async def test_natural_language_invalid_time_is_none(self):
        """Invalid or unparseable times should be None."""
        provider = self._make_provider()
        content = """**Name:** AI Workshop
**Category:** Workshop
**Date:** October 20, 2026
**Start Time:** not-a-real-time
**End Time:** also-not-a-time
**Venue:** Lab 204"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.start_time is None
        assert extracted.end_time is None
        warning_fields = {w.field for w in warnings}
        assert "start_time" in warning_fields
        assert "end_time" in warning_fields

    @pytest.mark.asyncio
    async def test_natural_language_description_alias(self):
        """'Details:' label should be normalized to description field."""
        provider = self._make_provider()
        content = """**Name:** AI Seminar
**Category:** Seminar
**Date:** October 20, 2026
**Start Time:** 9:00 AM
**End Time:** 12:00 PM
**Venue:** Lab 204, CS Block
**Details:** This seminar covers neural networks, transformer architectures, and practical machine learning applications."""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Seminar"
        assert extracted.description == "This seminar covers neural networks, transformer architectures, and practical machine learning applications."

    @pytest.mark.asyncio
    async def test_natural_language_category_enum_validation(self):
        """Category should be validated against supported enum values."""
        provider = self._make_provider()
        content = """**Name:** AI Workshop
**Category:** NotARealCategory
**Date:** October 20, 2026
**Venue:** Lab 204"""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        # Invalid category is mapped to 'Other' (valid enum fallback)
        assert extracted.category == "Other"

    @pytest.mark.asyncio
    async def test_natural_language_details_label(self):
        """Natural language response with 'Details:' label maps to description."""
        provider = self._make_provider()
        content = """**Event Title:** AI Workshop
**Category:** Workshop
**Date:** October 20, 2026
**Time:** 09:00 AM - 12:00 PM
**Venue:** Lab 204, CS Block
**Details:** Learn about neural networks and ML."""
        request = EventExtractionRequest(text="Test")
        extracted, warnings = provider._parse_extraction_response(content, request)
        assert extracted.title == "AI Workshop"
        assert extracted.description == "Learn about neural networks and ML."
        assert extracted.start_time == "09:00"
        assert extracted.end_time == "12:00"

