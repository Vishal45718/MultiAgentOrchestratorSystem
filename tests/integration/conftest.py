"""Integration test configuration for repository tests.

Test strategy
-------------
All repository integration tests run against a real PostgreSQL 15 instance
(the same Docker service used for development).  We use a *separate database*
(``test_orchestrator``) to avoid touching production data.

Isolation per test
------------------
Each test receives a transaction that is rolled back at teardown, so no test
data persists between tests and the schema state is always clean.  This is
cheaper than truncating tables and avoids schema migration overhead.

Why PostgreSQL (not SQLite)
---------------------------
The schema uses PostgreSQL-specific behaviour:
- ``JSONB`` columns (queries, containment operators, indexing)
- Non-native ``Enum`` types stored as strings in VARCHAR columns
- ``UUID`` primary keys using the ``Uuid`` type

SQLite supports some of these as fallbacks but the dialect behaviour differs
enough to make it an unreliable proxy for production behaviour.  See D008 in
``planning/DECISION_LOG.md``.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.models import Base

# ---------------------------------------------------------------------------
# Test database URL
# ---------------------------------------------------------------------------
# Reads from the environment variable TEST_DATABASE_URL if set; otherwise
# falls back to the Docker Compose Postgres with the dedicated test DB.
_DEFAULT_TEST_URL = "postgresql://postgres:postgres@localhost:5432/test_orchestrator"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_URL)


@pytest.fixture(scope="session")
def pg_engine():
    """Create the test schema once per session and drop it afterwards."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(pg_engine):
    """Provide a per-test transactional session that rolls back on teardown.

    Every test gets a fresh database state without any DDL overhead.
    """
    connection = pg_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Ensure SQLAlchemy sub-transactions (savepoints) behave correctly
    session.begin_nested()

    yield session

    session.close()
    try:
        transaction.rollback()
    except Exception:
        # The transaction may already be rolled back (e.g. after an
        # IntegrityError that invalidates the connection's transaction).
        pass
    connection.close()
