# Backend - Campus AI Event Discovery Platform

This directory contains the FastAPI backend service for the **Campus AI Event Discovery Platform**.

> **Current Status: Phase 1 (Backend Foundation)**  
> The backend foundation is initialized with configuration, CORS, central error handling, database session scaffolding, and health endpoints. Database schema, authentication, and AI extraction are deferred to subsequent phases.

---

## 1. Tech Stack
- **Language**: Python 3.10+ (Tested on Python 3.13)
- **Framework**: FastAPI (high-performance async web framework)
- **Server**: Uvicorn (ASGI web server)
- **Validation & Settings**: Pydantic v2 & Pydantic-Settings
- **ORM & Database**: SQLAlchemy 2.0 (PostgreSQL planned, SQLite fallback for local development)
- **Testing**: Pytest & HTTPX (TestClient)

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── __init__.py           # Package indicator
│   ├── main.py               # Application entry point, CORS, and GET /health
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic BaseSettings loaded from environment
│   │   └── errors.py         # Global error handling and exception interceptors
│   ├── models/
│   │   └── __init__.py       # Placeholder for Phase 2 database entities
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── health.py         # Pydantic schemas (HealthResponse)
│   ├── api/
│   │   ├── __init__.py
│   │   └── router.py         # Central API router (/api/v1)
│   ├── services/
│   │   └── __init__.py       # Placeholder for business logic services
│   └── db/
│       ├── __init__.py
│       ├── base.py           # SQLAlchemy 2.0 DeclarativeBase
│       └── session.py        # Engine, SessionLocal, and get_db dependency
│
├── tests/
│   ├── __init__.py
│   └── test_health.py        # Automated test for health check
├── requirements.txt          # Python package requirements
├── .env.example              # Environment variables template
└── README.md                 # Backend documentation
```

---

## 3. Local Setup Instructions

### Step 1: Navigate to the Backend Directory
```bash
cd backend
```

### Step 2: Create a Python Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv .venv
```

On macOS / Linux:
```bash
python3 -m venv .venv
```

### Step 3: Activate the Virtual Environment
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

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Environment Variables (Optional for Phase 1)
Copy `.env.example` to `.env` if you wish to override any default settings:
```bash
copy .env.example .env     # Windows
cp .env.example .env       # macOS/Linux
```
*(No real secrets are needed for Phase 1. Default local settings work out of the box).*

---

## 4. Running the Backend Server

Run Uvicorn from the `backend/` directory:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

When running, the following endpoints are available:
- **Root Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **API Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 5. Running Tests

Run the test suite from the `backend/` directory with `pytest`:
```bash
pytest
```
Or with verbose output:
```bash
pytest -v
```

---

## 6. Architecture & Viva Notes for CSE Students
- **Why FastAPI?** Native asynchronous support, automatic OpenAPI/Swagger documentation, fast execution, and strict data validation using Pydantic.
- **Why Pydantic v2?** Ensures type safety, automatically converts query/body types, and serializes clean JSON responses.
- **Why SQLAlchemy 2.0?** Industry standard Python ORM providing clean separation between database engine, session lifecycle (`get_db`), and declarative models.
- **Why a separate `db/session.py`?** Centralizes connection pooling and session management. Yielding sessions in `get_db()` ensures that every HTTP request closes its database connection even if an unexpected exception occurs.
- **How does CORS work?** Browser security prevents a frontend (e.g., `http://localhost:5173`) from making requests to an API at a different origin (`http://127.0.0.1:8000`) unless the backend explicitly declares permitted origins in headers. This is handled dynamically via `CORSMiddleware` and `settings.CORS_ORIGINS`.
