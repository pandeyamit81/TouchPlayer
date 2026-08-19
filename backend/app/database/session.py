"""
TouchPlayer Database Session Management
"""
import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database path
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = os.environ.get("TOUCHPLAYER_DB_PATH", str(PROJECT_DIR / "cache" / "touchplayer.db"))

# Ensure cache directory exists
cache_dir = PROJECT_DIR / "cache"
cache_dir.mkdir(parents=True, exist_ok=True)

# SQLite uses a NullPool by default; pool sizing options are not supported.
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_session() -> Generator:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with all models"""
    import app.database.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
