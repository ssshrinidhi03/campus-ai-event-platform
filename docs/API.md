# API Documentation

This document describes the REST API conventions, implemented endpoints in **Phase 1**, and the planned route hierarchy for subsequent phases.

---

## 1. General API Conventions

- **Base URL (Local)**: `http://127.0.0.1:8000`
- **API Versioning**: Standard routes are prefixed with `/api/v1`.
- **Response Format**: All responses use `application/json; charset=utf-8`.
- **Documentation**:
  - Swagger UI: `http://127.0.0.1:8000/docs`
  - ReDoc: `http://127.0.0.1:8000/redoc`

---

## 2. Error Response Format

Errors are returned with standard HTTP status codes and a consistent JSON payload:

```json
{
  "detail": "Descriptive error message"
}
```

For validation errors (HTTP 422 Unprocessable Entity):
```json
{
  "message": "Invalid request parameters",
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 3. Implemented Endpoints (Phase 1)

### Health Check (Root)
Check that the FastAPI application is alive and responding.

- **URL**: `/health`
- **Method**: `GET`
- **Authentication**: None
- **Response Code**: `200 OK`
- **Response Body**:
  ```json
  {
    "status": "ok"
  }
  ```

### Health Check (API Router)
Check the health of the `/api/v1` router namespace.

- **URL**: `/api/v1/health`
- **Method**: `GET`
- **Authentication**: None
- **Response Code**: `200 OK`
- **Response Body**:
  ```json
  {
    "status": "ok"
  }
  ```

---

## 4. Planned Endpoints (Future Phases)

> **Note**: These endpoints are planned and will be implemented incrementally in their respective phases. They are not active in Phase 1.

### Authentication & Users (Phase 3)
- `POST /api/v1/auth/register` - Register student or organizer account
- `POST /api/v1/auth/login` - Authenticate credentials and issue JWT
- `GET /api/v1/auth/me` - Retrieve current user profile

### Event Management (Phase 4)
- `GET /api/v1/events` - List and filter approved campus events
- `GET /api/v1/events/{id}` - View specific event details
- `POST /api/v1/events` - Create event (manual entry by organizer)
- `PUT /api/v1/events/{id}` - Update draft event
- `POST /api/v1/events/{id}/register` - Student registration for event

### Document Ingestion & Extraction (Phases 5–7)
- `POST /api/v1/documents/upload` - Upload flyer/notice (PDF, JPG, PNG)
- `POST /api/v1/documents/{id}/extract` - Trigger GenAI extraction
- `GET /api/v1/documents/{id}/extracted-data` - View extracted fields with source coordinates
- `PUT /api/v1/documents/{id}/verify` - Human verification and edits before publishing

### Search & Discovery (Phase 8)
- `GET /api/v1/search` - Natural language / semantic vector search

### Admin & Moderation (Phase 4)
- `GET /api/v1/admin/events/pending` - Review submitted events
- `POST /api/v1/admin/events/{id}/approve` - Approve event publication
- `POST /api/v1/admin/events/{id}/reject` - Reject event with feedback
