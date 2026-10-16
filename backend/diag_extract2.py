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
    
    # Build the same payload extract_event uses
    system_prompt = provider._get_extraction_system_prompt()
    request = EventExtractionRequest(text=TEST_ANNOUNCEMENT)
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
    
    print("=" * 70)
    print("RAW PROVIDER RESPONSE")
    print("=" * 70)
    print(content)
    print("=" * 70)
    print()
    print("Content type:", type(content).__name__)
    print("Content length:", len(content))
    print()
    
    # Try JSON parse
    import json
    try:
        parsed = json.loads(content.strip())
        print("JSON PARSE: SUCCESS")
        print("Keys:", list(parsed.keys()))
    except json.JSONDecodeError as e:
        print("JSON PARSE: FAILED -", e)
    
    print()
    print("=" * 70)
    print("PARSER OUTPUT")
    print("=" * 70)
    try:
        extracted, warnings = provider._parse_extraction_response(content, request)
        print(f"title:        {extracted.title}")
        print(f"category:     {extracted.category}")
        print(f"venue:        {extracted.venue}")
        print(f"date:         {extracted.date}")
        print(f"start_time:   {extracted.start_time}")
        print(f"end_time:     {extracted.end_time}")
        print(f"confidence:   {provider._calculate_confidence(extracted, warnings):.2f}")
        print(f"warnings:     {[(w.field, w.message) for w in warnings]}")
    except Exception as e:
        print(f"PARSER ERROR: {type(e).__name__}: {e}")

asyncio.run(test())
