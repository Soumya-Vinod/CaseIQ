"""Also verifies startup completes with no real database anywhere -- found
live, same shape as tests/integration/test_ratelimit.py's own hidden-Neon
discovery (that file's client fixture docstring flags this exact test as
the one it didn't fix, out of its own scope): `with TestClient(app) as
client:` drives the app's real ASGI lifespan (app.main.lifespan) on
__enter__, which calls assert_embedding_config_matches_corpus through
app.main's own `from app.db.base import SessionLocal` -- the real global
engine, bound to whatever settings.DATABASE_URL actually resolves to.
Nothing here overrode that, so this test silently depended on either:
backend-ci.yml's job-level POSTGRES_* env vars happening to point
settings.DATABASE_URL at the same local container tests/integration/
conftest.py uses (that workflow's own top comment says this is
deliberate), or -- on a dev machine with DATABASE_URL_RAW set in .env, as
this project's own is for day-to-day work -- real production Neon. Passed
either way, undetected: assert_embedding_config_matches_corpus's own
"empty corpus" branch (see its docstring, app/services/embeddings.py)
returns cleanly with no rows to check, so an empty local container and a
fully-populated Neon corpus produce the identical "nothing failed" result,
for entirely unrelated reasons.

Checked every other independent `from app.db.base import SessionLocal`
import in this codebase before deciding this needed exactly one patch, not
more -- the same question test_ratelimit.py's client fixture had to answer
the hard way, where two believed-complete overrides turned out to be
missing a third:
  - app.main.SessionLocal -- used in the lifespan startup check. REACHED:
    this is exactly what runs when `with TestClient(app) as client:`
    drives the lifespan protocol. Patched below.
  - app.middleware.request_context.SessionLocal -- used only inside
    RequestContextMiddleware._audit, gated by `_is_audited(path)`, which
    requires the path to start with "/api/" (confirmed by reading
    _is_audited itself, not assumed). GET /health is registered directly
    on `app` in app/main.py, not under settings.API_V1_PREFIX ("/api/v1"),
    so this path is never reached by this test. NOT patched -- there's
    nothing here to override.
  - app.tasks.worker.SessionLocal -- only used inside arq job functions,
    run by a separate `arq` worker process this test never starts or
    imports. Not reachable from this test at all.

Rather than trading one real dependency (Neon) for another (the local
Postgres+pgvector container test_ratelimit.py's own fixture needs),
app.main.SessionLocal is patched to a minimal fake session whose
execute() always returns no rows -- deterministically hitting
assert_embedding_config_matches_corpus's own documented "fresh DB, first
ingest not run" skip branch. That's exactly what this test needs and no
more: a check that /health responds correctly, not a second copy of the
real corpus-content check nightly-eval.yml's ci_preflight_embedding_
check.py and test_ratelimit.py's own real-Postgres fixture already cover.
No real I/O anywhere in this fake, so -- unlike test_ratelimit.py's own
real asyncpg engine -- there's no event-loop-crossing hazard in still
using TestClient's own internally-managed loop here.
"""
from fastapi.testclient import TestClient

from app.main import app


class _EmptyCorpusResult:
    """Stands in for the one row assert_embedding_config_matches_corpus
    tries to fetch -- `.mappings().first()` returning None is exactly the
    "no embedded rows yet" case that function's own docstring documents as
    not a mismatch, just skipped.
    """

    def mappings(self):
        return self

    def first(self):
        return None


class _EmptyCorpusSession:
    """A fake AsyncSession -- no real connection, no real database, local
    or otherwise. Implements only execute() and the async context manager
    protocol, because assert_embedding_config_matches_corpus is the only
    thing this test's lifespan run actually calls against it.
    """

    async def execute(self, *args, **kwargs):
        return _EmptyCorpusResult()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


def test_health_endpoint(monkeypatch):
    # The one independent SessionLocal reference this test's lifespan run
    # actually reaches -- see module docstring for the other two checked
    # and ruled out.
    monkeypatch.setattr("app.main.SessionLocal", _EmptyCorpusSession)

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert "x-request-id" in r.headers
