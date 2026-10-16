"""Additional tests for AI extraction edge cases"""
import pytest
from app.services.ai import NavigateLabsProvider
from app.schemas.ai import EventExtractionRequest
from unittest.mock import patch, AsyncMock

class TestExtractionEdgeCases:
    @pytest.mark.asyncio
    async def test_complete_announcement_extraction(self):
        with patch('app.services.ai.settings') as mock_settings, patch('app.services.ai.httpx.AsyncClient') as mock_client:
            mock_settings.NAVIGATE_API_KEY = 'test'
            mock_settings.NAVIGATE_API_BASE_URL = 'https://api.test.com'
            mock_settings.NAVIGATE_MODEL_EXTRACTION = 'test'
            mock_settings.NAVIGATE_MODEL_EMBEDDING = 'test'
            p = NavigateLabsProvider()
            mock_resp = AsyncMock()
            mock_resp.raise_for_status = lambda: None
            mock_resp.json = lambda: {'choices': [{'message': {'content': '{"title":"AI Hackathon","category":"Hackathon","venue":"Main Auditorium","date":"2027-03-15","start_time":"10:00","end_time":"12:00","registration_deadline":"2027-03-10T23:59:00","registration_link":"https://example.com/register","eligibility":"Open to all Computer Science students","tags":[],"warnings":[]}'} }]}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            r = EventExtractionRequest(text='Join us for the AI Hackathon on March 15, 2027, at 10 AM in the Main Auditorium. Open to all Computer Science students. Register by March 10, 2027, at https://example.com/register.')
            res = await p.extract_event(r)
            assert res.extracted_data.title == 'AI Hackathon'
            assert res.extracted_data.category == 'Hackathon'
            assert res.extracted_data.venue == 'Main Auditorium'
            assert res.extracted_data.date is not None
