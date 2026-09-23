"""app.db.write_guard, tested against a real live connection, not just the classification regex
in isolation (tests/test_write_guard_classification.py) -- per instruction: "every guard in this
project that turned out to be inert looked correct until someone made it fire." A write attempt
against a non-local host with CONFIRM_PRODUCTION_WRITE unset must actually raise, and the row must
actually not be there afterward -- not just "an exception was raised somewhere."

Can't safely point this at a REAL non-local host without risking exactly what the guard exists to
prevent -- instead, points a fresh engine at the real, reachable, throwaway integration-test
Postgres (TEST_DATABASE_URL) and installs the guard with `local_hosts=set()`, so the guard treats
this genuinely-local, genuinely-safe database as "non-local" for the purpose of this test only.
The connection, the statement, and the block/allow decision are all real; only which set of
hostnames counts as "local" is substituted, via the same `local_hosts` parameter
install_write_guard() exists to make testable in the first place.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.write_guard import ProductionWriteBlocked, install_write_guard
from app.models.corpus import Act
from tests.integration.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.integration


async def _guarded_session_factory(local_hosts: set[str]):
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    install_write_guard(engine, local_hosts=local_hosts)
    return engine, async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class TestWriteGuardBlocksForReal:
    async def test_write_raises_and_row_is_not_persisted(self, _schema_ready, monkeypatch):
        monkeypatch.delenv("CONFIRM_PRODUCTION_WRITE", raising=False)
        engine, factory = await _guarded_session_factory(local_hosts=set())
        try:
            async with factory() as session:
                session.add(Act(act_code="GUARDTEST1", short_title="x", status="in_force",
                                 commenced_on=date(2020, 1, 1)))
                with pytest.raises(ProductionWriteBlocked, match="GUARDTEST1|BLOCKED"):
                    await session.flush()
        finally:
            await engine.dispose()

        # Prove the block was real, not just an exception with the write going through anyway --
        # a fresh, UNGUARDED connection to the same real test DB must see nothing.
        plain_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        try:
            async with async_sessionmaker(plain_engine, expire_on_commit=False, class_=AsyncSession)() as check:
                from sqlalchemy import select
                rows = (await check.execute(
                    select(Act).where(Act.act_code == "GUARDTEST1")
                )).scalars().all()
                assert rows == [], "the blocked write must not have reached the database"
        finally:
            await plain_engine.dispose()

    async def test_write_succeeds_once_env_var_is_set(self, _schema_ready, monkeypatch):
        monkeypatch.setenv("CONFIRM_PRODUCTION_WRITE", "1")
        engine, factory = await _guarded_session_factory(local_hosts=set())
        try:
            async with factory() as session:
                session.add(Act(act_code="GUARDTEST2", short_title="x", status="in_force",
                                 commenced_on=date(2020, 1, 1)))
                await session.commit()  # must NOT raise

            from sqlalchemy import select
            async with factory() as check:
                rows = (await check.execute(
                    select(Act).where(Act.act_code == "GUARDTEST2")
                )).scalars().all()
                assert len(rows) == 1
        finally:
            await engine.dispose()

    async def test_read_is_never_blocked_regardless_of_env_var(self, _schema_ready, monkeypatch):
        monkeypatch.delenv("CONFIRM_PRODUCTION_WRITE", raising=False)
        engine, factory = await _guarded_session_factory(local_hosts=set())
        try:
            from sqlalchemy import select
            async with factory() as session:
                # Must not raise -- a plain SELECT against a "non-local" host, no env var set.
                await session.execute(select(Act).limit(1))
        finally:
            await engine.dispose()
