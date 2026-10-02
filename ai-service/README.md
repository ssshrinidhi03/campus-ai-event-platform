# AI Service & GenAI Pipeline

> **Status: Not Implemented (Scheduled for Phases 6–8)**

## Overview
The AI layer provides automated extraction of structured campus event data from unstructured flyers/notices, natural language semantic search, and personalized recommendations.

## Core Architectural Principles
1. **Modular & Provider-Agnostic**:
   - The AI integration is isolated behind service interfaces.
   - It will not be locked to a single LLM vendor (support for OpenAI, Anthropic, Google Gemini, or local models via Ollama can be swapped via configuration).
2. **Deterministic Extraction & Grounding**:
   - Extraction will map directly to structured Pydantic schemas.
   - Every extracted field will retain source references/coordinates from the original document for human verification (Phase 7).
3. **Semantic Search / RAG**:
   - Vector embeddings will be generated for approved events to enable intuitive natural language event discovery (Phase 8).

## Planned Capabilities
- **Phase 6**: GenAI Document Extraction (parsing notices, brochures, and circulars into structured JSON).
- **Phase 7**: Source Tracking & Human Verification (highlighting extracted spans for organizer review).
- **Phase 8**: Semantic / Vector Search over campus events.
- **Phase 10**: Context-aware student recommendations based on interests and major.

*Implementation begins during **Phase 6** of the development plan.*
