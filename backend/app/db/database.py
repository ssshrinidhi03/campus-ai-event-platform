import logging
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 DeclarativeBase for all entity models.
    All application models inherit from this base class.
    """
    pass


def get_database_url() -> str:
    """
    Resolve the database connection URL from settings.
    - Production: Expects a PostgreSQL connection string via DATABASE_URL
      (e.g., postgresql://user:password@localhost:5432/campus_events).
    - Local Development: Falls back to a local SQLite database file
      ('sqlite:///./campus_events_dev.db') if DATABASE_URL is not set.
    """
    url = settings.DATABASE_URL
    if not url:
        return "sqlite:///./campus_events_dev.db"

    # Normalize legacy 'postgres://' scheme to SQLAlchemy-preferred 'postgresql://'
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


DATABASE_URL = get_database_url()

# SQLite requires 'check_same_thread: False' for multi-threaded FastAPI execution
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Initialize SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enforce foreign key constraints when using SQLite.
    By default, SQLite does not enforce foreign keys unless PRAGMA foreign_keys=ON is set.
    """
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# SessionLocal factory for generating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional SQLAlchemy database session per request.
    Guarantees session cleanup after request lifecycle completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """
    Initialize database schema by creating all registered tables on Base.metadata.
    Ensures all models are imported before calling create_all.
    """
    # Import all models to register them on Base.metadata
    from app.models.user import User  # noqa: F401
    from app.models.event import Event  # noqa: F401
    from app.models.registration import EventRegistration  # noqa: F401
    from app.models.document import Document  # noqa: F401
    from app.models.source import EventSource  # noqa: F401

    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    logger.info("Database tables initialized successfully.")
