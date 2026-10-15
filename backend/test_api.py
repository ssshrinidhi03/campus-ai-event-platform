import asyncio
import httpx
import json
from app.core.config import settings

async def test():
    headers = {'Authorization': f'Bearer {settings.NAVIGATE_API_KEY}', 'Content-Type': 'application/json'}
    prompt = """You are an expert event information extractor for a campus event platform. 
Extract structured event data from unstructured text or image descriptions.

CRITICAL RULES:
1. NEVER invent dates, venues, deadlines, or other factual event details.
2. If information is missing or ambiguous, return null for that field.
3. Normalize dates to ISO 8601 format (YYYY-MM-DD).
4. Normalize times to HH:MM 24-hour format.
5. Categories must be one of: Workshop, Hackathon, Seminar, Competition, Conference, Cultural, Sports, Other
6. Return valid JSON matching the exact schema provided.
7. Include warnings for any missing required fields or ambiguities.

Required output format:
{
  "title": "string or null",
  "description": "string or null",
  "category": "string or null",
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
    
    payload = {
        'model': 'nova-micro',
        'messages': [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': 'TEXT ANNOUNCEMENT:\nJoin us for the AI Hackathon on March 15th at 10 AM in the Main Auditorium. Open to all CS students. Register by March 10th at https://example.com/register\n\nExtract structured event data as JSON.'},
        ],
        'temperature': 0.1,
        'response_format': {'type': 'json_object'},
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f'{settings.NAVIGATE_API_BASE_URL}/chat/completions', headers=headers, json=payload)
            print('Status:', resp.status_code)
            result = resp.json()
            print('Response:', json.dumps(result, indent=2)[:2000])
            content = result['choices'][0]['message']['content']
            print('Content:', content[:500])
            try:
                parsed = json.loads(content)
                print('Parsed JSON:', json.dumps(parsed, indent=2)[:1000])
            except json.JSONDecodeError as e:
                print('JSON Parse Error:', e)
    except Exception as e:
        print('Error:', type(e).__name__, e)

asyncio.run(test())