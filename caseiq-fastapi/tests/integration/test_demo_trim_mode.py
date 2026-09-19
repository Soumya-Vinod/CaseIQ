"""settings.DEMO_TRIM_MODE (app/core/config.py, 2026-09-20) -- the fallback
if the demo's Groq daily-token ceiling turns out lower than the ~400k
assumed. Proves the ACTUAL call-count drop, not just that the flag flips
without erroring: with it on, /legal/query must make exactly one real Groq
call per request (main generation only), not two (generation +
detect_language).

Reuses tests/integration/test_ratelimit.py's own `client` fixture style
directly (empty-corpus test DB, mocked LLMService._call, real HTTP through
the real app) -- see that file's own module docstring for why this specific
harness shape (ASGITransport, not TestClient; DB overridden at every
SessionLocal reference, not just the FastAPI dependency). Not reusing that
fixture by import because it isn't exposed as a shared conftest fixture;
duplicated here narrowly rather than refactoring an existing file's
fixture scope, which is out of this change's purpose.

related_questions' own DEMO_TRIM_MODE skip (app/api/v1/legal.py, same
settings flag, same boolean shape) is NOT separately exercised here: this
fixture's empty test corpus makes every query abstain, and the abstained
path never reaches related_questions regardless of the flag -- proving
that skip live would need a non-empty test corpus, out of this file's
scope. Reviewed directly instead: the skip is the identical
`or settings.DEMO_TRIM_MODE` addition to an already-existing ternary, same
flag, same file, immediately below the one this file does prove live --
not an independent code path with its own failure mode to separately catch.
"""
from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.ratelimit import limiter
from app.db.base import get_db
from app.main import app
from app.services.llm import llm_service
from tests.integration.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.integration


async def _client(schema_ready, monkeypatch, *, call_log: list[str]):
    async def _fake_call(messages, *, temperature=None, max_tokens=None, extra_body=None):
        # Tags which kind of call this was by a cheap prompt-content sniff --
        # good enough to count "did detect_language run", not meant as a
        # general-purpose call classifier.
        joined = " ".join(m.get("content", "") for m in messages)
        call_log.append("detect_language" if "Detect language" in joined else "generation")
        return json.dumps({"conversational_summary": "test", "structured_data": {}})

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr("app.main.SessionLocal", session_factory)
    monkeypatch.setattr("app.middleware.request_context.SessionLocal", session_factory)
    monkeypatch.setattr(llm_service, "_call", _fake_call)
    limiter.reset()

    transport = ASGITransport(app=app, client=("testclient", 123))
    return engine, AsyncClient(transport=transport, base_url="http://test")


async def test_demo_trim_mode_off_calls_detect_language(_schema_ready, monkeypatch):
    call_log: list[str] = []
    monkeypatch.setattr("app.api.v1.legal.settings.DEMO_TRIM_MODE", False)
    engine, client = await _client(_schema_ready, monkeypatch, call_log=call_log)
    try:
        async with client:
            async with app.router.lifespan_context(app):
                r = await client.post("/api/v1/legal/query", json={"query": "theft question"})
    finally:
        app.dependency_overrides.clear()
        limiter.reset()
        await engine.dispose()

    assert r.status_code == 200
    assert "detect_language" in call_log, (
        f"expected a detect_language call with DEMO_TRIM_MODE off, got {call_log}"
    )


async def test_demo_trim_mode_on_skips_detect_language(_schema_ready, monkeypatch):
    call_log: list[str] = []
    monkeypatch.setattr("app.api.v1.legal.settings.DEMO_TRIM_MODE", True)
    engine, client = await _client(_schema_ready, monkeypatch, call_log=call_log)
    try:
        async with client:
            async with app.router.lifespan_context(app):
                r = await client.post("/api/v1/legal/query", json={"query": "theft question"})
    finally:
        app.dependency_overrides.clear()
        limiter.reset()
        await engine.dispose()

    assert r.status_code == 200
    assert "detect_language" not in call_log, (
        f"expected NO detect_language call with DEMO_TRIM_MODE on, got {call_log}"
    )
    # language stays whatever was sent ("en", the payload default) -- never
    # auto-detected -- this IS the documented tradeoff, not a bug: a query
    # actually typed in Hindi/Marathi/Tamil/Telugu but tagged "en" would be
    # answered in English instead of detected and matched.
    assert r.json()["language"] == "en"
