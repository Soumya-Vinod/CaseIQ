"""POST /legal/timeline, proven live through the real app -- not just the
service-level tests (tests/integration/test_timeline_verification.py) or the
pure-function extraction tests (tests/test_timeline_clause.py). Same
reasoning as tests/integration/test_ratelimit.py's own module docstring: a
guardrail whose only test is one level below where it actually runs can
still be broken by anything in the missing layer (request parsing, the
section-text pre-filter, the redaction-restore step, the response schema)
while every lower-level test stays green. Same harness shape as
tests/integration/test_demo_trim_mode.py -- real HTTP through the real app,
DB overridden at every SessionLocal reference, LLM mocked at
LLMService._call, not duplicated as a shared fixture since neither of those
two files shares one either (this project's own existing precedent, not
introduced fresh here).
"""
from __future__ import annotations

import json
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.ratelimit import limiter
from app.db.base import Base, get_db
from app.main import app
from app.services.llm import llm_service
from tests.integration.conftest import TEST_DATABASE_URL, _assert_safe_to_truncate
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration

BNSS_58_TEXT = (
    "58. No police officer shall detain in custody a person arrested without warrant for a "
    "longer period than under all the circumstances of the case is reasonable, and such period "
    "shall not, in the absence of a special order of a Magistrate under section 187, exceed more "
    "than twenty-four hours exclusive of the time necessary for the journey from the place of "
    "arrest to the Magistrate's Court, whether having jurisdiction or not."
)
# BNSS 200-shaped: real section text, no time-limit language at all.
BNSS_UNDATED_TEXT = (
    "200. Report to be signed.—Every report referred to in section 193 shall be signed by the "
    "informant and the officer in charge of the police station."
)


async def _client(_schema_ready, monkeypatch, *, fake_call):
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr("app.main.SessionLocal", session_factory)
    monkeypatch.setattr("app.middleware.request_context.SessionLocal", session_factory)
    monkeypatch.setattr(llm_service, "_call", fake_call)
    limiter.reset()

    transport = ASGITransport(app=app, client=("testclient", 123))
    return engine, AsyncClient(transport=transport, base_url="http://test")


async def _truncate_all(engine) -> None:
    # This file seeds through its own manually-created engine rather than
    # the shared `db` fixture (which truncates automatically after each
    # test) -- see module docstring for why. Without this, a second test in
    # this same file re-inserting "BNSS" collides with the first test's
    # still-present row (found live, not assumed: exactly this collision,
    # `UniqueViolationError` on `uq_acts_act_code`, the first time this file
    # ran with two seeding tests in one session). Same TRUNCATE the `db`
    # fixture itself runs, same safety guard against pointing it at the
    # wrong database.
    async with engine.begin() as conn:
        await _assert_safe_to_truncate(conn)
        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        await conn.exec_driver_sql(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE")


class TestGenerateTimelineEndpoint:
    async def test_grounded_stage_reaches_the_response(self, _schema_ready, monkeypatch):
        async def fake_call(messages, *, temperature=None, max_tokens=None, extra_body=None):
            return json.dumps([{
                "stage": "Production before Magistrate", "description": "Police must present you.",
                "act": "BNSS 2023", "section": "58", "time_limit_claim": "within 24 hours",
            }])

        async def seed(db):
            bnss = await _make_act(db, "BNSS", commenced_on=date(2024, 7, 1))
            await _make_version(db, bnss, "58", BNSS_58_TEXT, date(2024, 7, 1))
            await db.commit()

        # Seed through the same session factory the client fixture wires up.
        engine, client = await _client(_schema_ready, monkeypatch, fake_call=fake_call)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with session_factory() as db:
            await seed(db)
        try:
            async with client:
                async with app.router.lifespan_context(app):
                    r = await client.post("/api/v1/legal/timeline", json={
                        "query": "I was arrested, what happens next?",
                        "sections": [{"act": "BNSS 2023", "section": "58"}],
                    })
        finally:
            app.dependency_overrides.clear()
            limiter.reset()
            await _truncate_all(engine)
            await engine.dispose()

        assert r.status_code == 200
        body = r.json()
        assert body["stages_proposed"] == 1
        assert len(body["stages"]) == 1
        assert body["stages"][0]["time_limit"] == "within 24 hours"
        assert body["stages"][0]["section"] == "58"

    async def test_fabricated_stage_never_reaches_the_response(self, _schema_ready, monkeypatch):
        # BNSS 58's real limit is 24 hours; the model claims 72 -- must be
        # dropped by verification before the HTTP response is built, not
        # just internally counted.
        async def fake_call(messages, *, temperature=None, max_tokens=None, extra_body=None):
            return json.dumps([{
                "stage": "Production before Magistrate", "description": "Police must present you.",
                "act": "BNSS 2023", "section": "58", "time_limit_claim": "within 72 hours",
            }])

        engine, client = await _client(_schema_ready, monkeypatch, fake_call=fake_call)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with session_factory() as db:
            bnss = await _make_act(db, "BNSS", commenced_on=date(2024, 7, 1))
            await _make_version(db, bnss, "58", BNSS_58_TEXT, date(2024, 7, 1))
            await db.commit()
        try:
            async with client:
                async with app.router.lifespan_context(app):
                    r = await client.post("/api/v1/legal/timeline", json={
                        "query": "I was arrested, what happens next?",
                        "sections": [{"act": "BNSS 2023", "section": "58"}],
                    })
        finally:
            app.dependency_overrides.clear()
            limiter.reset()
            await _truncate_all(engine)
            await engine.dispose()

        assert r.status_code == 200
        body = r.json()
        assert body["stages_proposed"] == 1  # the model DID propose one
        assert body["stages"] == []          # but nothing survived verification

    async def test_no_dated_sections_abstains_without_calling_the_llm(self, _schema_ready, monkeypatch):
        called = {"count": 0}

        async def fake_call(messages, *, temperature=None, max_tokens=None, extra_body=None):
            called["count"] += 1
            return json.dumps([])

        engine, client = await _client(_schema_ready, monkeypatch, fake_call=fake_call)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with session_factory() as db:
            bnss = await _make_act(db, "BNSS", commenced_on=date(2024, 7, 1))
            await _make_version(db, bnss, "200", BNSS_UNDATED_TEXT, date(2024, 7, 1))
            await db.commit()
        try:
            async with client:
                async with app.router.lifespan_context(app):
                    r = await client.post("/api/v1/legal/timeline", json={
                        "query": "What happens with my report?",
                        "sections": [{"act": "BNSS 2023", "section": "200"}],
                    })
        finally:
            app.dependency_overrides.clear()
            limiter.reset()
            await _truncate_all(engine)
            await engine.dispose()

        assert r.status_code == 200
        body = r.json()
        assert body["stages"] == []
        assert body["stages_proposed"] == 0
        assert called["count"] == 0  # no Groq call spent on nothing groundable
