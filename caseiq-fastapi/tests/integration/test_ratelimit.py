"""Rate limiting, proven live -- not read. Four tests, one per bug this
project's own scaffolding carried before it was actually wired
(docs/evaluation.md, HEADLINE RESULT 6), each found only by triggering a
real request through the real app, never by reading the code:

  1. The middleware enforced nothing at all (no SlowAPIMiddleware).
  2. Once wired, every enforced request crashed (missing `response:
     Response` param -- slowapi injects headers onto it, and without it
     falls back to `kwargs.get("response")`, which was None).
  3. Once THAT was fixed, routes covered only by `default_limits` (not a
     per-route decorator) silently bypassed this project's own error
     envelope -- SlowAPIMiddleware's own synchronous dispatch swaps an
     async exception handler for slowapi's bare-string default.
  4. `key_func` was blind to X-Forwarded-For, collapsing every anonymous
     client behind Render's proxy onto one shared key.

Real HTTP requests through the real app (httpx.AsyncClient over
ASGITransport -- see the `client` fixture's own comment for why this,
not TestClient), real middleware, real decorator. Only two things are
swapped for a test environment:
  - The DB session (this project's local integration-test Postgres, not
    Neon -- both the per-request dependency AND the app's own lifespan-
    time SessionLocal, so this suite has no live-Neon dependency at all).
  - The LLM call (app.services.llm.LLMService._call) -- same mocking
    boundary tests/test_llm_pii_redaction.py already uses; no real Groq
    call, no real network dependency, same discipline as every other
    test in this suite.

The local integration-test DB starts with an empty corpus -- no
section_versions rows -- so every /legal/query call abstains (no
sections to retrieve). That's a feature here, not a gap: it means every
request completes fast and deterministically without needing a real
corpus, while still exercising detect_language's one real (mocked) LLM
call and the full real request/response cycle end to end.
"""
from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.requests import Request

from app.api.deps import client_ip
from app.core.ratelimit import limiter, rate_limit_key
from app.db.base import get_db
from app.main import app
from app.services.llm import llm_service
from tests.integration.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.integration


async def _fake_call(messages, *, temperature=None, max_tokens=None):
    # Deliberately generic: detect_language falls back to "en" on anything
    # that isn't a recognised 2-letter code (see LLMService.detect_language's
    # own except/fallback), and process_query/related_questions each parse
    # this into a valid, if minimal, dict -- no test here depends on the
    # LLM's actual output, only on the real request cycle completing.
    return json.dumps({"conversational_summary": "test", "structured_data": {}})


@pytest.fixture
async def client(_schema_ready, monkeypatch):
    """Real requests against the real app -- httpx.AsyncClient over
    ASGITransport, not TestClient. Found live, not by review, why it has
    to be this and not the more obvious choice:

    TestClient wraps its sync interface around its OWN internally-managed
    event loop (one per `with TestClient(app) as c:` block), separate from
    whatever loop this async fixture and its DB engine run in. A per-route
    async DB dependency's actual connection gets used from THAT internal
    loop, not this fixture's -- and asyncpg connections (or their pending
    internal cleanup/cancellation tasks) are never safe to survive past
    the loop that created them. Reproduced directly: a two-test file
    (this one + tests/test_health.py) failed with "Event loop is closed"
    inside asyncpg's own protocol layer, on the SECOND file's test, not
    this one -- the damage shows up downstream of where it's caused. Fixed
    by staying in ONE loop end to end: httpx.AsyncClient + ASGITransport
    runs entirely inside pytest-asyncio's own per-test loop, the same loop
    this fixture's DB engine and every awaited call in it share -- no
    internal TestClient loop to cross at all. ASGITransport doesn't drive
    the app's lifespan automatically (unlike `with TestClient(app) as c:`),
    so it's triggered explicitly via `app.router.lifespan_context`.

    DB is overridden at two levels, not one -- easy to miss, so noted
    explicitly:
      - `get_db` (the per-request dependency every route uses) via
        `app.dependency_overrides`, FastAPI's own documented mechanism.
      - `app.main.SessionLocal` (what the app's OWN LIFESPAN uses directly
        for its startup assertions -- assert_embedding_config_matches_
        corpus, in particular) via monkeypatch. Overriding only `get_db`
        leaves the lifespan's own corpus check hitting whatever
        settings.DATABASE_URL resolves to outside this override -- real
        Neon, per .env -- which would make this "self-contained" suite
        secretly depend on live network access. Found while building this,
        not assumed: this project's only prior TestClient usage
        (tests/test_health.py) has carried that exact hidden dependency
        the whole time, undetected because it happens to pass either way.
        Flagged separately, not fixed here -- out of this file's scope.

    `client=("testclient", 123)` on the transport matches the "ip:testclient"
    key convention this session's own live verification already established
    (docs/evaluation.md) for a synthetic test client's rate-limit key,
    rather than ASGITransport's own default (127.0.0.1).
    """
    # Created AND disposed within this one fixture, entirely inside this
    # one test's own pytest-asyncio loop -- no module-level sharing across
    # tests. NullPool on top of that: even within a single test, a
    # per-request pooled connection getting reused/pinged is one more way
    # to touch asyncpg state outside the coroutine that owns it.
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr("app.main.SessionLocal", session_factory)
    # FOUND ONLY BY TRACING THE ACTUAL FAILING CONNECTION, not guessed: this
    # is the real root cause of the "Event loop is closed" pollution below,
    # not an asyncpg/asyncio quirk. RequestContextMiddleware writes an
    # audit_logs row for every /api/ request via its OWN direct
    # `from app.db.base import SessionLocal` -- a THIRD reference to the
    # real global engine, independent of both the dependency override above
    # and the app.main.SessionLocal patch (which only rebinds the name as
    # it exists in app.main's own namespace). Every one of this fixture's
    # requests to /api/v1/legal/query was, until this line existed, ACTUALLY
    # writing a real row to production Neon via that middleware, using the
    # real global connection pool -- confirmed directly from the failing
    # traceback's own captured log ("app_starting ... neon.tech", a real
    # AsyncAdaptedQueuePool connection failing to terminate against a
    # closed loop). That pool then held a connection orphaned by this
    # fixture's own closed loop, which the NEXT test to boot the real app
    # (tests/test_health.py) inherited and crashed on. Patched here too --
    # the same three-places-import-SessionLocal shape as the other two
    # patches above, just less obvious because this one isn't reached via
    # app.main or FastAPI's own dependency system at all.
    monkeypatch.setattr("app.middleware.request_context.SessionLocal", session_factory)
    monkeypatch.setattr(llm_service, "_call", _fake_call)
    limiter.reset()  # in-memory storage is a module-level singleton -- never leak state across tests

    transport = ASGITransport(app=app, client=("testclient", 123))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()
    limiter.reset()  # never leak this test's rate-limit state into whatever test runs next either
    await engine.dispose()  # explicit, awaited, still inside this test's own loop


class TestDecoratedRouteEnforcement:
    """/legal/query carries @limiter.limit("8/hour") -- see app/api/v1/legal.py."""

    async def test_middleware_actually_enforces_a_limit(self, client):
        # FIXED bug 1: this used to never happen at all -- SlowAPIMiddleware
        # was never added, so nothing capped anything regardless of how
        # many requests came through. 9 requests against an "8/hour" limit
        # MUST produce at least one 429 -- if the middleware regresses to
        # inert, every one of these returns 200 and this assertion catches it.
        statuses = []
        for i in range(9):
            r = await client.post("/api/v1/legal/query", json={"query": f"theft question {i}"})
            statuses.append(r.status_code)
        assert 429 in statuses, (
            f"expected a 429 somewhere in 9 requests against an 8/hour limit, got {statuses} -- "
            f"rate limiting is not enforcing anything"
        )

    async def test_enforced_route_does_not_crash_on_success_or_on_limit(self, client):
        # FIXED bug 2: slowapi's per-route decorator injects headers onto
        # whatever the wrapped function returns; process_query returns a
        # QueryOut (response_model), not a Response, so without a
        # `response: Response` parameter slowapi fell back to
        # kwargs.get("response") == None and crashed INSIDE THE DECORATOR --
        # on every request, 200s included, not just the 429. A regression
        # here doesn't show up as a wrong status code, it shows up as this
        # test raising instead of asserting, which is exactly what makes it
        # easy to miss without a test that actually sends real requests.
        for i in range(8):
            r = await client.post("/api/v1/legal/query", json={"query": f"theft question {i}"})
            assert r.status_code == 200, f"request {i} should succeed under the limit, got {r.status_code}: {r.text}"
            assert "x-ratelimit-limit" in {k.lower() for k in r.headers}

        r9 = await client.post("/api/v1/legal/query", json={"query": "theft question 9"})
        assert r9.status_code == 429
        body = r9.json()
        assert body["error"]["code"] == "rate_limited"
        assert "Retry-After" in r9.headers


class TestDefaultLimitRouteEnvelope:
    """/health carries no @limiter.limit decorator -- covered only by
    Limiter's own default_limits, checked inside SlowAPIMiddleware's
    synchronous dispatch, not the per-route decorator's async path.
    """

    async def test_default_limit_route_uses_the_project_envelope_not_slowapis_default(self, client):
        # FIXED bug 3: SlowAPIMiddleware's own synchronous dispatch resolves
        # the registered RateLimitExceeded handler itself and explicitly
        # swaps an async handler for slowapi's own bare-string default
        # ({"error": "Rate limit exceeded: ..."}) -- correct-looking on
        # /legal/query (decorator path, real async exception middleware)
        # and silently wrong on every route covered only by default_limits,
        # which is every OTHER route in this app. Pre-seeds the real
        # in-memory counter directly (same storage/key the middleware
        # itself checks) to avoid 200 real requests just to reach the
        # boundary -- same technique used to verify this live in
        # docs/evaluation.md.
        default_limit = list(limiter._default_limits[0])[0].limit
        key = ["ip:testclient", "/health"]
        for _ in range(200):
            assert limiter.limiter.hit(default_limit, *key), "pre-seed hit unexpectedly rejected"

        r = await client.get("/health")
        assert r.status_code == 429, (
            "expected the pre-seeded default limit to reject this request -- if it's 200, "
            "either the pre-seed key/scope no longer matches what the middleware checks, "
            "or default_limits stopped applying to this route"
        )
        body = r.json()
        assert body["error"]["code"] == "rate_limited", (
            f"got slowapi's own default envelope instead of this project's -- "
            f"the sync/async handler bug is back: {body}"
        )
        assert "Retry-After" in r.headers


class TestRateLimitKeyForwardedFor:
    """No DB, no HTTP -- a direct unit test of app.core.ratelimit.rate_limit_key."""

    def test_uses_x_forwarded_for_over_socket_address(self):
        # FIXED bug 4: the original key_func was slowapi's own
        # get_remote_address, which reads request.client.host directly and
        # never looks at X-Forwarded-For -- behind Render's reverse proxy
        # that's Render's own internal address for every request, collapsing
        # all anonymous traffic onto one shared key. rate_limit_key (via
        # app.api.deps.client_ip, already used for audit logging) must
        # prefer the forwarded header. Constructs a bare Starlette Request
        # directly -- no app, no DB, cheapest possible check for this.
        scope = {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.7, 10.0.0.1")],
            "client": ("10.0.0.1", 54321),  # Render's own proxy address, not the real client
        }
        request = Request(scope)

        assert client_ip(request) == "203.0.113.7"  # sanity check on the primitive itself
        assert rate_limit_key(request) == "ip:203.0.113.7"

    def test_falls_back_to_socket_address_when_no_forwarded_header(self):
        scope = {"type": "http", "headers": [], "client": ("198.51.100.9", 54321)}
        request = Request(scope)

        assert rate_limit_key(request) == "ip:198.51.100.9"
