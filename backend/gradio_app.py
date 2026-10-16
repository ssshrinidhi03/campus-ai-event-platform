"""
Gradio demonstration interface for CampusConnect GenAI capabilities.

Demonstrates (reusing existing backend services):
  1. Text-based event extraction (AI-powered structured extraction)
  2. RAG-based event question answering (tool-using agent over approved events)

Poster/image extraction is NOT included here because multimodal support
depends on the configured AI provider's vision capabilities and cannot be
guaranteed without live provider verification. Text extraction remains the
supported workflow.

Launch:
    cd backend
    python gradio_app.py
"""

import asyncio
import logging

import gradio as gr

from app.services.ai import (
    EventExtractionRequest,
    RagQueryRequest,
    create_agent,
    get_ai_provider,
)
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from Gradio's sync callback context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        # Already running (e.g., inside an async context); create a fresh loop
        loop = asyncio.new_event_loop()
    return loop.run_until_complete(coro)


def extract_event_text(text: str):
    """Extract structured event data from a text announcement."""
    if not text or not text.strip():
        return "Please enter an announcement text.", "", "", ""

    provider = get_ai_provider()
    request = EventExtractionRequest(text=text.strip())
    try:
        result = _run_async(provider.extract_event(request))
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return f"Extraction failed: {e}", "", "", ""

    data = result.extracted_data
    fields = (
        f"Title: {data.title or '—'}\n"
        f"Category: {data.category or '—'}\n"
        f"Venue: {data.venue or '—'}\n"
        f"Date: {data.date.strftime('%Y-%m-%d') if data.date else '—'}\n"
        f"Time: {data.start_time or '—'} – {data.end_time or '—'}\n"
        f"Organization: {data.organization or '—'}\n"
        f"Eligibility: {data.eligibility or '—'}\n"
        f"Registration Deadline: {data.registration_deadline or '—'}\n"
        f"Registration Link: {data.registration_link or '—'}\n"
        f"Tags: {', '.join(data.tags) if data.tags else '—'}\n"
        f"Capacity: {data.capacity or '—'}\n"
        f"Contact Email: {data.contact_email or '—'}"
    )
    warnings = "\n".join(f"⚠️ {w.field}: {w.message}" for w in result.warnings) or "No warnings."
    confidence = f"Confidence: {result.confidence:.0%}"
    processing = f"Processing time: {result.processing_time_ms} ms"
    return fields, warnings, confidence, processing


def answer_event_question(question: str):
    """Answer a natural-language question about campus events via the agent."""
    if not question or not question.strip():
        return "Please enter a question.", ""

    db = SessionLocal()
    try:
        agent = create_agent(provider=get_ai_provider(), db_session=db)
        result = _run_async(agent.run(question.strip()))
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        return f"Unable to answer: {e}", ""
    finally:
        db.close()

    answer = result.answer or "No answer returned."
    events_lines = []
    if result.events:
        for ev in result.events:
            events_lines.append(
                f"• {ev.title} ({ev.category or 'N/A'}) — "
                f"{ev.date or 'date TBD'} at {ev.venue or 'venue TBD'} "
                f"by {ev.organizer_name or 'organizer TBD'}"
            )
    events_text = "\n".join(events_lines) if events_lines else "No relevant events found."
    return answer, events_text


with gr.Blocks(title="CampusConnect — GenAI Demo") as demo:
    gr.Markdown("# CampusConnect — GenAI Demonstration")
    gr.Markdown(
        "Demo of AI-powered event extraction and RAG-based event Q&A. "
        "Reuses the existing FastAPI backend services. "
        "No API keys are exposed in this interface."
    )

    with gr.Tab("📝 Extract Event from Text"):
        gr.Markdown("Paste an event announcement to extract structured details.")
        text_in = gr.Textbox(
            label="Event Announcement",
            placeholder="e.g., Join us for the AI Hackathon on March 15th at 10 AM in the Main Auditorium. Open to all CS students. Register by March 10th at https://example.com/register",
            lines=5,
        )
        extract_btn = gr.Button("Extract Event Details", variant="primary")
        fields_out = gr.Textbox(label="Extracted Fields", lines=12)
        warnings_out = gr.Textbox(label="Warnings / Missing Fields", lines=6)
        confidence_out = gr.Textbox(label="Confidence")
        timing_out = gr.Textbox(label="Timing")
        extract_btn.click(
            fn=extract_event_text,
            inputs=text_in,
            outputs=[fields_out, warnings_out, confidence_out, timing_out],
        )

    with gr.Tab("🔍 Ask About Events (RAG Agent)"):
        gr.Markdown(
            "Ask a natural-language question about campus events. "
            "The agent searches approved events and answers using only retrieved data."
        )
        question_in = gr.Textbox(
            label="Your Question",
            placeholder="e.g., Which AI workshops are happening this month? Find hackathons open to Computer Science students.",
            lines=3,
        )
        ask_btn = gr.Button("Ask", variant="primary")
        answer_out = gr.Textbox(label="Answer", lines=8)
        events_out = gr.Textbox(label="Relevant Events", lines=8)
        ask_btn.click(
            fn=answer_event_question,
            inputs=question_in,
            outputs=[answer_out, events_out],
        )

    gr.Markdown(
        "---\n"
        "**Note:** The RAG agent only returns APPROVED (published) events. "
        "Draft, unpublished, or rejected events are never exposed. "
        "Image/poster extraction depends on the AI provider's vision capabilities "
        "and is not included in this demo."
    )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
