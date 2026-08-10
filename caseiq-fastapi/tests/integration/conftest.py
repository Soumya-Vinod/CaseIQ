"""Fixtures for Part K's integration tests -- these need a REAL Postgres with
pgvector, not the pure-unit suite's no-DB style (see tests/conftest.py).
Deliberately separate from the rest of tests/ (I2 in
docs/caseiq-industry-readiness.md: "Integration tests against a real test
Postgres, Testcontainers or a compose service").

Bring up a throwaway Postgres instance with:
    docker run -d --name caseiq-test-db -e POSTGRES_DB=caseiq_test \
      -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
      -p 5434:5432 pgvector/pgvector:pg17

then create the DEDICATED integration-test database inside it (same
instance/port is fine -- what matters is the database NAME, see the guard
below):
    docker exec caseiq-test-db psql -U postgres -c \
      "CREATE DATABASE caseiq_integration_test"
    docker exec caseiq-test-db psql -U postgres -d caseiq_integration_test \
      -c "CREATE EXTENSION IF NOT EXISTS vector"

`make test` (plain `pytest -q`) does NOT require this -- these tests skip
themselves at collection time if the DB isn't reachable, rather than failing
the whole suite. Run them explicitly with:
    pytest tests/integration -m integration

INCIDENT (2026-08-10): this database used to default to the SAME name
(caseiq_test) as the database used for manual corpus verification during
active development. The `db` fixture below TRUNCATEs every app table after
every test -- correct for test isolation, catastrophic when pointed at data
someone is relying on. Running this suite silently wiped BNS/BNSS/BSA/CrPC
and judicial_status out of the manually-ingested corpus mid-session; all had
to be re-ingested. The database was renamed to caseiq_integration_test and
_assert_safe_to_truncate() below makes the failure mode structurally
impossible rather than merely-unlikely-by-convention: it refuses to run
TRUNCATE against anything whose current_database() doesn't match the
required name, no matter what TEST_DATABASE_URL someone points this at.

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

# The ONLY database name this suite will ever TRUNCATE. Not a substring/regex
# match against something merely containing "test" -- caseiq_test itself
# contains "test" and was exactly the database that got wiped by that
# looser reasoning. Must be exact, so pointing TEST_DATABASE_URL at the
# wrong database fails LOUD (RuntimeError, see _assert_safe_to_truncate)
# instead of quietly destroying whatever's there.
_REQUIRED_TEST_DB_NAME = "caseiq_integration_test"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql+asyncpg://postgres:postgres@localhost:5434/{_REQUIRED_TEST_DB_NAME}",
)
_SYNC_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


async def _assert_safe_to_truncate(conn) -> None:
    actual = (await conn.exec_driver_sql("SELECT current_database()")).scalar()
    if actual != _REQUIRED_TEST_DB_NAME:
        raise RuntimeError(
            f"refusing to TRUNCATE database {actual!r}: this fixture only ever truncates "
            f"{_REQUIRED_TEST_DB_NAME!r}. TEST_DATABASE_URL is pointed somewhere else -- fix "
            f"the env var, don't remove this guard. See this file's module docstring for the "
            f"2026-08-10 incident this exists to make structurally impossible."
        )

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
        await _assert_safe_to_truncate(conn)
        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        await conn.exec_driver_sql(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE")
    await engine.dispose()
