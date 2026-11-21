"""SQLite and SQLAlchemy setup for the Meeting Transcriber backend."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import PROJECT_ROOT, settings


class Base(DeclarativeBase):
    """Base class for database models."""


# SQLite permits one local process to access a connection from its request thread.
if settings.database_url.startswith("sqlite:///"):
    (PROJECT_ROOT / "storage").mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """Yield one database session for an HTTP request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create the Part 3 tables if they do not already exist."""
    # Importing registers the model classes with Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
