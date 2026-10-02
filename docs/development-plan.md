# Development Plan

This document outlines the step-by-step phased development plan for the **Campus AI Event Discovery Platform**. Development is executed incrementally to ensure every layer is tested, robust, and easy to explain during academic defense and code review.

---

## Current Status: Phase 1 (Backend Foundation) Completed

---

## Phased Roadmap

### Phase 1: Backend Foundation (CURRENT PHASE)
- Establish repository structure, Git configuration, and directory boundaries.
- Set up FastAPI backend application with Uvicorn.
- Implement central configuration management using Pydantic Settings and `.env.example`.
- Set up modular API routing structure and health check endpoints (`GET /health`).
- Implement basic consistent error handling and configurable CORS.
- Set up database connection scaffolding and session management without declaring full schemas.
- Add initial automated health test suite.

### Phase 2: Database Design & Models
- Design relational database schema for PostgreSQL (with SQLite for local development).
- Implement SQLAlchemy 2.0 ORM models (`User`, `Event`, `Document`, `Registration`, etc.).
- Configure database migration framework using Alembic.
- Set up database seeding scripts for local development and testing.

### Phase 3: Authentication & Authorization
- Implement user registration, login, and token generation using JWT (JSON Web Tokens).
- Add password hashing with Passlib/Bcrypt.
- Implement Role-Based Access Control (RBAC) supporting **Student**, **Organizer**, and **Admin** roles.
- Create security dependency functions (`get_current_user`, `require_role`).

### Phase 4: Event Management & CRUD APIs
- Implement event lifecycle management (Draft, Pending Approval, Approved, Rejected, Cancelled).
- Build CRUD endpoints for creating, reading, updating, and deleting events.
- Implement filtering, pagination, and sorting by date, category, department, and organizer.
- Build admin approval and moderation workflows.

### Phase 5: Document Upload & Storage
- Create secure file upload endpoints for event flyers, circulars, and notices (PDF, PNG, JPG).
- Implement file validation (file size limits, MIME type verification).
- Configure local storage abstraction with easy extensibility to cloud storage (e.g., S3/Cloud Storage).
- Associate uploaded documents with event draft entities in the database.

### Phase 6: GenAI Document Extraction
- Extract raw text from uploaded documents (using OCR or PDF parsers).
- Integrate an LLM provider (OpenAI, Gemini, or local models) using structured outputs.
- Extract event metadata: Title, description, dates, time, venue, organizer, registration deadline, fees, and contact info into strict Pydantic models.
- Maintain provider independence to easily switch models.

### Phase 7: Source Tracking & Human Verification
- Track provenance and bounding boxes/text excerpts for each AI-extracted field.
- Allow organizers to view extracted values side-by-side with original notices.
- Allow organizers to manually edit, correct, and verify extracted data before submission.

### Phase 8: Semantic Search & RAG
- Implement text chunking and vector embedding generation for approved events.
- Store embeddings in a vector database or pgvector.
- Build natural language semantic search endpoint allowing students to search queries like *"workshops on machine learning this weekend"*.

### Phase 9: Frontend Development
- Initialize React single-page application using Vite.
- Implement responsive UI components:
  - Student event discovery feed, search, and details.
  - Organizer event creation and document upload workflow with verification UI.
  - Admin approval dashboard.
- Connect frontend to backend REST APIs using configured CORS.

### Phase 10: Recommendations Engine
- Implement personalized event recommendations for students based on past registrations, saved events, and academic department/interests.
- Combine collaborative filtering and content-based similarity.

### Phase 11: Comprehensive Testing & Quality Assurance
- Implement unit tests for backend services and endpoints using `pytest`.
- Implement integration tests for the GenAI pipeline and database workflows.
- Implement frontend component and end-to-end user journey tests.

### Phase 12: Deployment & DevOps
- Prepare Docker containers for backend, frontend, and database services.
- Write `docker-compose.yml` for unified local execution.
- Set up production environment configuration and deployment guides.
