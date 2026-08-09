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
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5434/caseiq_test"
)

pytestmark = pytest.mark.integration


def _skip_if_unreachable() -> None:
    import asyncio

    import asyncpg

    async def _ping() -> bool:
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")),
                timeout=3,
            )
            await conn.close()
            return True
        except Exception:
            return False

    if not asyncio.run(_ping()):
        pytest.skip(
            f"no test Postgres reachable at {TEST_DATABASE_URL} -- see this file's docstring "
            f"for the docker run command to start one",
            allow_module_level=True,
        )


_skip_if_unreachable()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        from app.db.base import Base
        import app.models  # noqa: F401  registers all tables on Base.metadata

        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncSession:
    """Function-scoped session. Truncates every app table after each test --
    simpler and more reliable across asyncpg + FastAPI's session style than
    nested SAVEPOINTs, and cheap enough at this table count.
    """
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        from app.db.base import Base

        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        await conn.exec_driver_sql(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE")
