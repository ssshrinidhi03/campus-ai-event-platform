import asyncio
import sys
sys.path.insert(0, '.')
from app.services.ai import NavigateLabsProvider
from app.schemas.ai import EventExtractionRequest

TEST_ANNOUNCEMENT = """AI WORKSHOP
Category: Workshop
Date: October 20, 2026
Venue: Lab 204, CS Block
Start Time: 9:00 AM
End Time: 12:00 PM
Organizer: AI Club

Join us for a hands-on Artificial Intelligence workshop organized by the AI Club. The session covers neural networks and practical machine learning exercises for undergraduate students."""

async def test():
    provider = NavigateLabsProvider()
    
    for run in range(5):
        request = EventExtractionRequest(text=TEST_ANNOUNCEMENT)
        
        system_prompt = provider._get_extraction_system_prompt()
        user_content = provider._build_extraction_content(request)
        
        payload = {
            "model": provider.config.extraction_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        
        result = await provider._make_request("/chat/completions", payload)
        content = result["choices"][0]["message"]["content"]
        
        print(f"\n{'='*70}")
        print(f"RUN {run + 1} - RAW CONTENT")
        print('='*70)
        print(content)
        print()

asyncio.run(test())
