from fastapi import APIRouter
from app.schemas.health import HealthResponse

api_router = APIRouter()

# Health endpoint within API router (/api/v1/health)
@api_router.get(
    "/health",
    response_model=HealthResponse,
    summary="API Health Check",
    tags=["Health"]
)
def api_health() -> HealthResponse:
    """
    Check the health of the API router.
    Returns status: 'ok' if service is responsive.
    """
    return HealthResponse(status="ok")

# Note: Future modules will be mounted here cleanly in subsequent phases:
# - Phase 3: api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# - Phase 4: api_router.include_router(events.router, prefix="/events", tags=["Events"])
# - Phase 5: api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
# - Phase 8: api_router.include_router(search.router, prefix="/search", tags=["Search"])
# - Phase 4/Admin: api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
