"""Fixtures for Part K's integration tests -- these need a REAL Postgres with
pgvector, not the pure-unit suite's no-DB style (see tests/conftest.py).
Deliberately separate from the rest of tests/ (I2 in
docs/caseiq-industry-readiness.md: "Integration tests against a real test
Postgres, Testcontainers or a compose service").

Bring up a throwaway Postgres instance with:
    docker run -d --name caseiq-test-db -e POSTGRES_DB=caseiq_test \
      -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
      -p 5434:5432 pgvector/pgvector:pg17

That's the only manual step. FIXED 2026-09-07: the integration-test
database itself (DEDICATED name, see the guard below), its `vector`
extension, and its whole schema are now built automatically by the
`_schema_ready` fixture -- DROP DATABASE IF EXISTS + CREATE DATABASE +
`alembic upgrade head`, every session. No manual `CREATE DATABASE` /
`CREATE EXTENSION` step needed or wanted anymore; running that by hand
first just means the fixture drops it again on the next test run. See
`_schema_ready`'s own docstring for why (create_all() drift, twice, and
what replaced it).

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
    """FIXED 2026-09-07: rebuilds caseiq_integration_test from a clean
    DROP/CREATE DATABASE + real Alembic migrations (`alembic upgrade
    head`), not `Base.metadata.create_all()`. create_all() only ever
    creates MISSING tables/columns -- it never ALTERs an existing one.
    That drifted silently at least twice in one session: a model gained a
    column, the persistent container's schema didn't move, and tests
    failed confusingly downstream (a missing-column error deep in a query,
    not at schema setup) instead of at the one place that should have
    caught it. Each time cost a manual DROP DATABASE + full rerun to
    recover. Running the SAME migrations this project runs against real
    Postgres (dev, Render) means this fixture cannot silently diverge from
    what production actually has -- the exact guarantee create_all()
    structurally cannot make, no matter how often it's rerun.

    DROP DATABASE + CREATE DATABASE first, not just migrating whatever's
    already there: idempotent-by-construction instead of idempotent-by-
    convention. A stale caseiq_integration_test -- partial create_all()
    tables left over from before this fix, or a half-applied migration set
    from an interrupted previous run -- is now impossible to inherit,
    because nothing is ever inherited; every session-scoped test run
    starts from the same known-nothing state. This is the single most
    dangerous operation in this file (destroys a whole database, not just
    truncates tables) -- guarded by the SAME _REQUIRED_TEST_DB_NAME literal
    _assert_safe_to_truncate already uses below, checked against the
    parsed URL BEFORE any connection is made (there's no live database to
    query yet at drop-time), never against a value redirectable via env
    var alone.

    alembic/env.py hardcodes `settings.MIGRATION_DATABASE_URL` -- pointing
    it at the fresh test database runs `alembic upgrade head` in a
    SUBPROCESS with real env vars, not in-process monkeypatching:
    MIGRATION_DATABASE_URL is a read-only computed_field (no setter to
    monkeypatch), and env.py's own SSL flag (`_connect_args`) is computed
    at MODULE IMPORT time from settings.DATABASE_URL_RAW -- an in-process
    override only works if alembic.env has never been imported yet in this
    process, which is fragile to depend on across a whole pytest session. A
    subprocess has no such import history: it reads these env vars fresh,
    guaranteed, every time.
    """
    import os as _os
    import subprocess
    import sys
    from urllib.parse import urlparse

    parsed = urlparse(TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    db_name = parsed.path.lstrip("/")
    if db_name != _REQUIRED_TEST_DB_NAME:
        raise RuntimeError(
            f"refusing to DROP/CREATE database {db_name!r}: TEST_DATABASE_URL must point at "
            f"{_REQUIRED_TEST_DB_NAME!r}. Same guard as _assert_safe_to_truncate below, checked "
            f"here BEFORE any connection is made, since DROP DATABASE has no undo."
        )

    maintenance_url = _SYNC_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    maint_engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    with maint_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{_REQUIRED_TEST_DB_NAME}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{_REQUIRED_TEST_DB_NAME}"'))
    maint_engine.dispose()

    fresh_engine = create_engine(_SYNC_DATABASE_URL)
    with fresh_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    fresh_engine.dispose()

    plain_test_url = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    env = _os.environ.copy()
    env["DATABASE_URL_DIRECT"] = plain_test_url
    env["DATABASE_URL_RAW"] = ""  # falsy -- env.py's ssl="require" flag keys off this being unset
    project_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root, env=env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed against the fresh test database:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    import app.models  # noqa: F401  registers all tables on Base.metadata, for the `db` fixture's TRUNCATE below
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
