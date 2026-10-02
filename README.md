# Campus AI Event Discovery Platform

> **Current Development Status**: **Phase 1: Backend Foundation**  
> *The application is currently in the backend-foundation stage. Backend scaffolding, routing, CORS, configuration, database session preparation, and health check endpoints are initialized. Database schemas, authentication, frontend, and GenAI extraction will be implemented in subsequent phases.*

---

## 1. Project Overview
The **Campus AI Event Discovery Platform** is an AI-powered web platform designed for college campuses. It helps students discover, search, and register for campus events through intuitive category filters and natural language semantic search.

For campus clubs and organizers, the platform automates event creation by ingesting unstructured event flyers, notices, and PDF circulars, extracting structured event data via a GenAI pipeline, and enabling organizer verification before publishing.

---

## 2. Technology Stack

### Backend (Current Foundation)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Server**: [Uvicorn](https://www.uvicorn.org/) (ASGI Server)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/) & [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **ORM & Data Access**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Testing**: [Pytest](https://docs.pytest.org/) & [HTTPX](https://www.python-httpx.org/)

### Database (Planned - Phase 2)
- **Production Database**: PostgreSQL
- **Development Database**: SQLite (zero-config local development fallback)

### Frontend (Planned - Phase 9)
- **Framework**: React with Vite
- **Language**: JavaScript / TypeScript

### GenAI & Search Pipeline (Planned - Phases 6–8)
- **Extraction**: Modular LLM adapters (OpenAI / Gemini / Local LLMs)
- **Search**: Vector embeddings and semantic search (RAG)

---

## 3. Repository Structure

```
campus-ai-event-platform/
│
├── backend/                      # FastAPI Backend Service
│   ├── app/
│   │   ├── __init__.py           # Application package
│   │   ├── main.py               # Application entry point, CORS, root health check
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py         # Central environment configuration
│   │   │   └── errors.py         # Consistent JSON error handlers
│   │   ├── models/
│   │   │   └── __init__.py       # Placeholder for Phase 2 database models
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── health.py         # Pydantic schemas (HealthResponse)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── router.py         # Modular API router (/api/v1)
│   │   ├── services/
│   │   │   └── __init__.py       # Placeholder for business logic services
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── base.py           # SQLAlchemy 2.0 DeclarativeBase
│   │       └── session.py        # Database engine & session management
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py        # Automated test for health check endpoint
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Environment variables template
│   └── README.md                 # Detailed backend guide
│
├── frontend/
│   └── README.md                 # Planned React + Vite frontend (Phase 9)
│
├── ai-service/
│   └── README.md                 # Planned GenAI extraction pipeline (Phases 6–8)
│
├── docs/
│   ├── architecture.md           # System architecture diagrams & flows
│   ├── API.md                    # REST API documentation & planned routes
│   └── development-plan.md       # Incremental 13-phase roadmap
│
├── .gitignore                    # Git ignore file for Python, Node, Vite, etc.
└── README.md                     # Root project documentation (this file)
```

---

## 4. Quickstart Guide (Local Backend Setup)

### Prerequisites
- Python 3.10 or higher installed. Verify with:
  ```bash
  python --version
  ```

### Step 1: Create a Python Virtual Environment
Navigate to the `backend/` directory and create a virtual environment:

On Windows:
```powershell
cd backend
python -m venv .venv
```

On macOS / Linux:
```bash
cd backend
python3 -m venv .venv
```

### Step 2: Activate the Virtual Environment
On Windows (PowerShell):
```powershell
.venv\Scripts\activate
```

On Windows (Command Prompt):
```cmd
.venv\Scripts\activate.bat
```

On macOS / Linux:
```bash
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Start the Backend Server
Run Uvicorn with auto-reload enabled:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 5. Endpoints & Documentation

Once the server is running locally:

| Endpoint | Method | Description | URL |
| :--- | :--- | :--- | :--- |
| **Health Check** | `GET` | Service liveness probe | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) |
| **API Health Check** | `GET` | Versioned API probe | [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) |
| **Swagger UI** | `GET` | Interactive API documentation | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| **ReDoc** | `GET` | Alternative API reference | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) |

### Health Check Response:
```json
{
  "status": "ok"
}
```

---

## 6. Running Tests

To verify that the health endpoint passes all assertions:
```bash
cd backend
pytest
```

---

## 7. Development Roadmap

We are following an incremental, 13-phase development approach:

1. **Phase 1: Backend Foundation** *(CURRENT - Completed)*
2. **Phase 2: Database Design & Models** *(NEXT)*
3. **Phase 3: Authentication & Authorization**
4. **Phase 4: Event CRUD APIs & Moderation**
5. **Phase 5: Document Upload & Storage**
6. **Phase 6: GenAI Document Extraction**
7. **Phase 7: Source Tracking & Human Verification**
8. **Phase 8: Semantic / RAG Search**
9. **Phase 9: React Frontend**
10. **Phase 10: Personalized Recommendations**
11. **Phase 11: Comprehensive Testing**
12. **Phase 12: Deployment & Containerization**

For full phase details, see [docs/development-plan.md](file:///c:/Users/apram/Desktop/campus-ai-event-platform/docs/development-plan.md).
