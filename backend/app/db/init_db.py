"""
Database Initialization Script.

Creates all application tables registered in SQLAlchemy models.
Usage:
    python -m app.db.init_db
"""
import sys
from app.db.database import init_db, engine, DATABASE_URL

if __name__ == "__main__":
    print(f"Initializing database tables using URL: {DATABASE_URL}")
    try:
        init_db(engine)
        print("Success: All database tables created successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)
