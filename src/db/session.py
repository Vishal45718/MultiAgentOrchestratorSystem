"""Database session and engine management."""

from collections.abc import Generator
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings


def get_engine(url: Optional[str] = None, **kwargs) -> Engine:
    """Create a database engine with connection pooling options."""
    db_url = url or settings.sync_database_url
    return create_engine(db_url, **kwargs)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a SQLAlchemy sessionmaker bound to the given engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session(engine: Engine) -> Generator[Session, None, None]:
    """Yield a database session and ensure closure."""
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
