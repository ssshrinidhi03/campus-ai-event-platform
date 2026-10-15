import json
import logging
import secrets
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables or .env file.
    Designed for easy extension across future development phases.
    """
    PROJECT_NAME: str = "Campus AI Event Discovery Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    TESTING: bool = False
    API_V1_STR: str = "/api/v1"

    # CORS Origins allowed to access backend APIs (e.g. React frontend on Vite dev server)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database connection string (configured in Phase 2)
    DATABASE_URL: str | None = None

    # Secret key for JWT / Session authentication (configured in Phase 3)
    # MUST be set in production - no default allowed
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Email Configuration
    EMAIL_BACKEND: str = "console"  # console, smtp, mock
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str = "CampusConnect"

    # Frontend URL for email links
    FRONTEND_URL: str = "http://localhost:5173"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_MINUTES: int = 15
    RATE_LIMIT_REGISTER_ATTEMPTS: int = 3
    RATE_LIMIT_REGISTER_WINDOW_MINUTES: int = 60
    RATE_LIMIT_VERIFY_ATTEMPTS: int = 3
    RATE_LIMIT_VERIFY_WINDOW_MINUTES: int = 60
    RATE_LIMIT_RESEND_ATTEMPTS: int = 2
    RATE_LIMIT_RESEND_WINDOW_MINUTES: int = 60

    # GenAI provider and key (configured in Phase 6)
    AI_PROVIDER: str | None = None
    AI_API_KEY: str | None = None
    
    # Navigate Labs API configuration
    NAVIGATE_API_BASE_URL: str = "https://api.navigateai.co"
    NAVIGATE_API_KEY: str | None = None
    NAVIGATE_MODEL_EXTRACTION: str = "nova-micro"
    NAVIGATE_MODEL_EMBEDDING: str = "text-embedding-3-small"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ORIGINS from a JSON array string or comma-separated string if provided."""
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                try:
                    return json.loads(v_trimmed)
                except Exception:
                    pass
            return [i.strip() for i in v_trimmed.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str | None) -> str | None:
        """Validate that SECRET_KEY is set in production."""
        if v is not None and len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def validate_startup_config() -> None:
    """Validate critical configuration at application startup."""
    if settings.ENVIRONMENT == "production":
        if not settings.SECRET_KEY:
            raise RuntimeError("SECRET_KEY must be set in production environment")
        if settings.SECRET_KEY == "dev-secret-key-change-in-production-32-chars-minimum":
            raise RuntimeError("Default SECRET_KEY detected in production - must generate a secure random key")
        if settings.DEBUG:
            logger.warning("DEBUG mode enabled in production")
