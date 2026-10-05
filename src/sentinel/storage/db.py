"""SQLite database engine and session management."""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from sentinel.config import settings


def _ensure_sqlite_parent_dir(url: str) -> None:
    """Ensure parent directory exists for SQLite database files."""
    if url.startswith("sqlite:///"):
        raw_path = url[len("sqlite:///") :]
        if raw_path and raw_path != ":memory:":
            Path(raw_path).resolve().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.database_url)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing database sessions to FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all database tables."""
    _ensure_sqlite_parent_dir(settings.database_url)
    Base.metadata.create_all(bind=engine)
