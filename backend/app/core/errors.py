import logging
import json
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


def _serialize_errors(errors):
    """Serialize validation errors, converting any non-JSON-serializable values."""
    serialized = []
    for error in errors:
        serialized_error = {}
        for key, value in error.items():
            if key == 'ctx' and isinstance(value, dict):
                serialized_ctx = {}
                for ctx_key, ctx_value in value.items():
                    if hasattr(ctx_value, '__class__') and ctx_value.__class__.__name__ == 'ValueError':
                        serialized_ctx[ctx_key] = str(ctx_value)
                    else:
                        serialized_ctx[ctx_key] = ctx_value
                serialized_error[key] = serialized_ctx
            else:
                try:
                    json.dumps(value)
                    serialized_error[key] = value
                except (TypeError, ValueError):
                    serialized_error[key] = str(value)
        serialized.append(serialized_error)
    return serialized


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Registers central exception handlers on the FastAPI application.
    Provides consistent JSON error responses and prevents leaking internal stack traces.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": _serialize_errors(exc.errors()),
                "message": "Invalid request parameters",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        
        detail_message = str(exc) if settings.DEBUG else "Internal server error"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail_message},
        )
