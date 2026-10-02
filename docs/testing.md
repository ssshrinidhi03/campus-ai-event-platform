# Testing Guide — Campus AI Event Discovery Platform

This document defines the testing principles, phase-by-phase checklists, test categories,
test matrix, commands, manual procedures, and bug-reporting format for the platform.

> **Rule**: A feature is **NOT** complete merely because the application starts.

---

## 1. Testing Principle

Every development phase must follow this mandatory sequence before being marked complete:

```
IMPLEMENT
    |
UNIT TEST          <- Isolate functions and modules
    |
INTEGRATION TEST   <- Components working together
    |
MANUAL TEST        <- Visual and usability verification
    |
REGRESSION TEST    <- All previous phase tests still pass
    |
GIT COMMIT         <- Only after all tests pass
```

No phase may be committed or declared complete until every step above is satisfied.

---

## 2. Phase 1 Test Checklist

Run through this checklist before marking Phase 1 complete.

### 2.1 Project Setup

| # | Check | Status |
|---|-------|--------|
| 1 | Git repository exists (`git status` succeeds) | PASS |
| 2 | Git working tree is clean after final phase commit | PASS |
| 3 | `.gitignore` file exists at project root | PASS |
| 4 | `.env` is ignored by Git (excluded by `.gitignore`) | PASS |
| 5 | `.venv/` directory is ignored by Git | PASS |
| 6 | `node_modules/` is ignored by Git | PASS |

### 2.2 Python Environment

| # | Check | Status |
|---|-------|--------|
| 7 | Virtual environment activates (`.venv\Scripts\activate` on Windows) | PASS |
| 8 | All dependencies install without errors (`pip install -r requirements.txt`) | PASS |

### 2.3 Backend Startup

| # | Check | Status |
|---|-------|--------|
| 9  | FastAPI application initializes without errors | PASS |
| 10 | Uvicorn starts and binds to port 8000 | PASS |
| 11 | `GET /health` returns HTTP 200 | PASS |
| 12 | `GET /health` returns `{"status": "ok"}` | PASS |
| 13 | `GET /api/v1/health` returns HTTP 200 | PASS |
| 14 | `GET /api/v1/health` returns `{"status": "ok"}` | PASS |
| 15 | `/docs` (Swagger UI) loads and renders | PASS |
| 16 | `/redoc` (ReDoc UI) loads and renders | PASS |

### 2.4 Automated Tests

| # | Check | Status |
|---|-------|--------|
| 17 | `pytest` runs without collection errors | PASS |
| 18 | `test_root_health_endpoint` passes | PASS |
| 19 | `test_api_v1_health_endpoint` passes | PASS |
| 20 | `test_docs_endpoints` passes | PASS |
| 21 | **Total: 3 tests pass, 0 failures** | PASS |

---

## 3. Regression Test Rule

Every phase **must** run **all tests from all previous phases** before committing.

```
Phase 1 tests:   Health endpoint tests (3 tests)

Phase 2 tests:   Phase 1 tests  +  Database model and constraint tests

Phase 3 tests:   Phase 1 tests  +  Phase 2 tests  +  Auth and JWT tests

Phase 4 tests:   Phase 1 tests  +  Phase 2 tests  +  Phase 3 tests  +  Event CRUD API tests

Phase 5 tests:   All prior  +  Document upload and storage tests

Phase 6 tests:   All prior  +  GenAI extraction tests

Phase 7 tests:   All prior  +  Source tracking and provenance tests

Phase 8 tests:   All prior  +  Semantic search / RAG pipeline tests

Phase 9 tests:   All prior  +  Frontend component tests

Phase 10 tests:  All prior  +  Recommendations engine tests

Phase 11 tests:  All prior  +  End-to-end user workflow tests

Phase 12 tests:  All prior  +  Deployment and configuration tests
```

**Rule**: Never delete an old test because the project has evolved.
Old tests must remain runnable; adapt test fixtures and mocks instead.

---

## 4. Test Categories

### 4.1 Unit Tests
Test one function, class, or module in complete isolation.
- All external dependencies (database, HTTP, file I/O) are mocked.
- Fast to run; no network or disk access required.
- **Examples**: validate a Pydantic schema, test a business-logic helper, test enum values.

### 4.2 Integration Tests
Test multiple components interacting together under realistic conditions.
- May use a real in-memory database (e.g., SQLite) or a test PostgreSQL database.
- No mocking of internal application layers.
- **Examples**: create a User row and read it back, verify a foreign-key constraint fires.

### 4.3 API Tests
Test HTTP endpoints via the FastAPI `TestClient` or real HTTP calls.
- Verify HTTP status codes, response bodies, headers, and error messages.
- Verify input validation rejects malformed requests.
- **Examples**: `GET /health` returns 200, posting invalid JSON returns 422.

### 4.4 Database Tests
Test database operations, relationships, and constraints directly via SQLAlchemy.
- Use a separate test database (SQLite in-memory or a dedicated test PostgreSQL schema).
- Verify CRUD operations, foreign key enforcement, uniqueness constraints, and cascade deletes.
- **Examples**: duplicate EventRegistration raises `IntegrityError`, cascade delete removes child rows.

### 4.5 AI Tests (Phases 6-8)
Test AI extraction pipeline accuracy, structured output compliance, and failure handling.
- Use fixed sample documents with known expected outputs.
- Verify field extraction, confidence scores, and provenance attribution.
- Verify graceful degradation when the AI model is unavailable.

### 4.6 Frontend Tests (Phase 9+)
Test UI component rendering, state management, and API integration.
- Unit-test individual components in isolation.
- Use mock API responses for API integration tests.
- **Tools** (planned): Vitest, React Testing Library.

### 4.7 End-to-End Tests (Phase 11)
Test complete user workflows from browser to database and back.
- Simulate real user journeys: register, browse events, register for an event.
- Verify the entire system acts coherently across all layers.
- **Tools** (planned): Playwright.

### 4.8 Manual Tests
Test behavior that automated tests cannot reliably verify.
- Visual rendering, typography, spacing, and layout.
- Usability flows and navigation feel.
- Browser compatibility.
- Upload UX (drag-and-drop, progress indicators).

### 4.9 Security Tests (Phase 3+)
Test authentication, authorization, secret handling, and invalid/adversarial input.
- Verify protected endpoints reject unauthenticated requests.
- Verify role-based access control is enforced.
- Verify no secrets are logged or exposed in API responses.
- Verify SQL injection and path traversal inputs are rejected.

---

## 5. Test Matrix

| Phase | Feature | Automated Test | Manual Test | Regression Test | Status |
|:-----:|---------|:--------------:|:-----------:|:---------------:|--------|
| 1 | Backend foundation (FastAPI, Uvicorn, health endpoint) | [x] pytest: 3 tests | [x] Smoke test | N/A (first phase) | COMPLETE |
| 2 | Database foundation (SQLAlchemy models, constraints) | [ ] pytest: DB tests | [ ] Verify tables created | [x] Phase 1 tests | IN PROGRESS |
| 3 | Authentication and RBAC (JWT, password hashing) | [ ] pytest: auth tests | [ ] Login flow | [x] Phases 1-2 | Planned |
| 4 | Event management CRUD APIs | [ ] pytest: event API tests | [ ] Swagger CRUD walkthrough | [x] Phases 1-3 | Planned |
| 5 | Document upload and storage | [ ] pytest: upload tests | [ ] Upload a PDF | [x] Phases 1-4 | Planned |
| 6 | GenAI extraction pipeline | [ ] pytest: extraction tests | [ ] Upload notice, verify fields | [x] Phases 1-5 | Planned |
| 7 | Source tracking and provenance | [ ] pytest: provenance tests | [ ] View extraction evidence | [x] Phases 1-6 | Planned |
| 8 | Human verification UI | [ ] pytest: verification tests | [ ] Edit extracted values | [x] Phases 1-7 | Planned |
| 9 | Semantic search and RAG | [ ] pytest: search tests | [ ] Natural language query | [x] Phases 1-8 | Planned |
| 10 | Frontend application | [ ] Vitest: component tests | [ ] Full UI walkthrough | [x] Phases 1-9 | Planned |
| 11 | Recommendations engine | [ ] pytest: recommendation tests | [ ] Personalized feed check | [x] Phases 1-10 | Planned |
| 12 | Comprehensive testing (E2E) | [ ] Playwright: E2E workflows | [ ] Full user journeys | [x] All phases | Planned |
| 13 | Deployment and DevOps | [ ] Docker smoke tests | [ ] Staging environment check | [x] All phases | Planned |

---

## 6. Phase Completion Rule

A phase is **complete** only when **all** of the following are satisfied:

- [ ] The feature works as specified
- [ ] All automated tests for this phase pass
- [ ] All automated tests from all prior phases still pass (regression)
- [ ] The manual test checklist for this phase is completed
- [ ] No critical errors or exceptions remain in logs
- [ ] Documentation is updated (architecture, development plan, API docs where applicable)
- [ ] A clean Git commit is created with a descriptive message
- [ ] `.env` and secrets are **not** included in the commit

---

## 7. Test Commands

All commands are run from the `backend/` directory with the virtual environment activated.

### Activate the virtual environment

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\activate
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### Run all tests

```bash
pytest
```

### Run with verbose output (recommended for phase verification)

```bash
pytest -v
```

### Run a specific test file

```bash
pytest tests/test_health.py -v
```

### Run tests matching a keyword

```bash
pytest -v -k "database"
```

### Run with coverage report (requires pytest-cov)

```bash
pytest --cov=app --cov-report=term-missing
```

Note: `pytest-cov` is not yet installed. Add `pytest-cov>=5.0.0,<6.0.0` to `requirements.txt`
in a future phase when coverage reporting is needed.

### Start the backend development server

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- `http://127.0.0.1:8000` — API root
- `http://127.0.0.1:8000/health` — Health endpoint
- `http://127.0.0.1:8000/docs` — Swagger UI
- `http://127.0.0.1:8000/redoc` — ReDoc UI

---

## 8. Manual Smoke Test

Run this checklist after every significant code change and before every commit.

```
MANUAL SMOKE TEST

Step 1:  Start the backend:
             uvicorn app.main:app --reload

Step 2:  Open a browser and navigate to:
             http://127.0.0.1:8000/health

Step 3:  Verify the HTTP status is 200 OK.

Step 4:  Verify the response body is exactly:
             {"status": "ok"}

Step 5:  Navigate to:
             http://127.0.0.1:8000/docs

Step 6:  Verify the Swagger UI loads without errors.

Step 7:  In Swagger UI, expand "Health" and select "GET /health".

Step 8:  Click "Try it out", then "Execute".

Step 9:  Verify the response shows HTTP 200 and {"status": "ok"}.

Step 10: Open a terminal (with .venv activated) and run:
             pytest -v

Step 11: Verify output shows 3 passed, 0 failed.

All steps must pass. If any step fails, do NOT commit.
```

---

## 9. Bug Reporting Format

When a bug is found during any test phase, document it using this format:

```
Bug:
    [Short description of the defect]

Expected:
    [What should happen according to requirements or previous behavior]

Actual:
    [What actually happened -- include error messages, status codes, or screenshots]

Steps to Reproduce:
    1. [First step]
    2. [Second step]
    3. [Result observed]

Severity:
    [ ] Critical -- Application crashes or data is corrupted
    [ ] High     -- Core feature is broken, no workaround
    [ ] Medium   -- Feature partially broken, workaround exists
    [ ] Low      -- Minor visual or UX issue

Phase Introduced:
    [Phase number and name where the bug was first observed]

Fixed In:
    [Commit hash or phase where the fix was applied]

Regression Test Added:
    [ ] Yes -- Test file: [path/to/test_file.py]
    [ ] No  -- Reason: [explain why no test was added]
```

---

## 10. Test File Conventions

### File naming

| Type | Location | Naming Pattern |
|------|----------|----------------|
| Phase 1 health tests | `backend/tests/test_health.py` | `test_<feature>.py` |
| Phase 2 DB model tests | `backend/tests/test_models.py` | `test_<feature>.py` |
| Phase 3 auth tests | `backend/tests/test_auth.py` | `test_<feature>.py` |
| Phase 4 event API tests | `backend/tests/test_events.py` | `test_<feature>.py` |

### Test function naming

```python
# Pattern: test_<subject>_<condition>_<expected_outcome>
def test_user_creation_with_valid_data_succeeds(): ...
def test_duplicate_registration_raises_integrity_error(): ...
def test_health_endpoint_returns_200(): ...
```

### Database test isolation

- Use a separate in-memory SQLite database (`sqlite:///:memory:`) for all database tests.
- Never run database tests against the production or development database.
- Each test function gets a fresh database session via pytest fixtures.
- Tear down the database schema after each test module.

---

## 11. Current Test Results

Last updated: Phase 1 complete, Phase 2 in progress.

```
pytest -v

============================= test session starts ==============================
tests/test_health.py::test_root_health_endpoint     PASSED
tests/test_health.py::test_api_v1_health_endpoint   PASSED
tests/test_health.py::test_docs_endpoints           PASSED

======================== 3 passed in 0.69s ==============================
```

All 3 Phase 1 tests passing. No regressions.
