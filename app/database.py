"""
brAInfection V2 — Database engine, session management and dependency.

Uses SQLAlchemy 2.x with async-compatible patterns.
SQLite in development, PostgreSQL in production.
"""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


def _get_engine():
    """Create the SQLAlchemy engine based on settings."""
    settings = get_settings()
    url = settings.database_url

    connect_args = {}
    if url.startswith("sqlite"):
        # Ensure the directory exists for SQLite
        if ":///" in url:
            db_path = url.split("///", 1)[1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        url,
        connect_args=connect_args,
        echo=settings.is_dev,
        pool_pre_ping=True,
    )

    # Enable foreign keys for SQLite
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI dependency: yields a database session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
