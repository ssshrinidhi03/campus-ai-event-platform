import asyncio
import sys
import json
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
        print(f"\n{'='*70}")
        print(f"RUN {run + 1}")
        print('='*70)
        
        request = EventExtractionRequest(text=TEST_ANNOUNCEMENT)
        
        try:
            result = await provider.extract_event(request)
            d = result.extracted_data
            
            print(f"Provider: NavigateLabsProvider")
            print(f"Title:        {d.title}")
            print(f"Category:     {d.category}")
            print(f"Venue:        {d.venue}")
            print(f"Date:         {d.date}")
            print(f"Start time:   {d.start_time}")
            print(f"End time:     {d.end_time}")
            print(f"Confidence:   {result.confidence:.2f}")
            print(f"Warnings:     {[(w.field, w.message) for w in result.warnings]}")
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")

asyncio.run(test())
