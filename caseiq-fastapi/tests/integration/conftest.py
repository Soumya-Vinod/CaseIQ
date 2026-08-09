"""Fixtures for Part K's integration tests -- these need a REAL Postgres with
pgvector, not the pure-unit suite's no-DB style (see tests/conftest.py).
Deliberately separate from the rest of tests/ (I2 in
docs/caseiq-industry-readiness.md: "Integration tests against a real test
Postgres, Testcontainers or a compose service").

Bring up a throwaway test database with:
    docker run -d --name caseiq-test-db -e POSTGRES_DB=caseiq_test \
      -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
      -p 5434:5432 pgvector/pgvector:pg17

`make test` (plain `pytest -q`) does NOT require this -- these tests skip
themselves at collection time if the DB isn't reachable, rather than failing
the whole suite. Run them explicitly with:
    pytest tests/integration -m integration

Design note: schema setup is done with a SYNCHRONOUS engine in a session
fixture, deliberately not async -- an async session-scoped fixture's asyncpg
connections get bound to whichever event loop was active when it first ran,
and pytest-asyncio gives each TEST FUNCTION its own function-scoped loop by
default independently of a fixture's own loop_scope setting. Mixing the two
produced "Future attached to a different loop" / "Event loop is closed" on
every test after the first. A sync engine has no event loop to mismatch, and
the per-test `db` fixture below creates and disposes its own async engine
entirely within that one test's loop, so nothing outlives its loop.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5434/caseiq_test"
)
_SYNC_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

pytestmark = pytest.mark.integration


def _skip_if_unreachable() -> None:
    # A plain TCP probe -- no event loop involved, nothing to poison (see
    # module docstring for why an asyncio-based probe here was a problem).
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        with socket.create_connection((parsed.hostname, parsed.port or 5432), timeout=3):
            pass
    except OSError:
        pytest.skip(
            f"no test Postgres reachable at {TEST_DATABASE_URL} -- see this file's docstring "
            f"for the docker run command to start one",
            allow_module_level=True,
        )


_skip_if_unreachable()


@pytest.fixture(scope="session")
def _schema_ready():
    """Creates the vector extension + all tables ONCE, synchronously."""
    from app.db.base import Base
    import app.models  # noqa: F401  registers all tables on Base.metadata

    engine = create_engine(_SYNC_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(conn)
    engine.dispose()
    yield


@pytest_asyncio.fixture
async def db(_schema_ready) -> AsyncSession:
    """Function-scoped: its own engine, created and disposed entirely within
    this one test's event loop. Truncates every app table after each test.
    """
    from app.db.base import Base

    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        await conn.exec_driver_sql(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE")
    await engine.dispose()
