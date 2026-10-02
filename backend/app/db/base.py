"""
Backward compatibility module for Base declarative model.
Direct imports should use `app.db.database` or `app.db`.
"""
from app.db.database import Base

__all__ = ["Base"]
