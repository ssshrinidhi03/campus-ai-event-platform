from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.errors import setup_exception_handlers
from app.schemas.health import HealthResponse
from app.api.router import api_router
from app.db.database import SessionLocal, init_db
from app.services.vector_store import SimpleVectorStore
from app.models.event import Event
from app.models.enums import EventStatus
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and reindex approved events on startup."""
    init_db()
    db = SessionLocal()
    try:
        # Reindex approved events into the vector store for RAG search
        vs = SimpleVectorStore()
        stats = await vs.reindex_all(db)
        logger.info(f"Vector store reindexed on startup: {stats}")
    except Exception as e:
        logger.warning(f"Startup reindex failed: {e}")
    finally:
        db.close()
    yield


# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API foundation for Campus AI Event Discovery Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS middleware using application settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register central error and exception handlers
setup_exception_handlers(app)

# Root-level health endpoint as required: GET /health -> {"status": "ok"}
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Root Health Check",
    tags=["Health"]
)
def root_health() -> HealthResponse:
    """
    Root health check endpoint.
    Used by load balancers, monitoring tools, and frontend connectivity checks.
    """
    return HealthResponse(status="ok")

# Mount API router prefix (e.g., /api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
