"""
Backward compatibility module for session management.
Direct imports should use `app.db.database` or `app.db`.
"""
from app.db.database import engine, SessionLocal, get_db

__all__ = ["engine", "SessionLocal", "get_db"]
