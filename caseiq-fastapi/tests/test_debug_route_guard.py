"""GET /legal/debug/retrieval needs ENV=development AND a localhost
DATABASE_URL AND ENABLE_DEBUG_ROUTES -- any one missing is a 404. ENV alone
was the original guard, and a local .env had ENV=development pointing at
production Neon. get_db is overridden so no database is ever contacted, and
the trace itself is stubbed: this tests the guard, not the trace."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.base import get_db
from app.main import app
from app.services import retrieval_debug

LOCAL_URL = "postgresql://u:p@localhost:5432/caseiq"
LOOPBACK_URL = "postgresql://u:p@127.0.0.1:5432/caseiq"
NEON_URL = "postgresql://u:p@ep-example-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"


@pytest.fixture
def client(monkeypatch):
    async def no_db():
        yield None

    async def fake_trace(db, q, show=10):
        return {"traced": q}

    monkeypatch.setattr(retrieval_debug, "trace_retrieval", fake_trace)
    app.dependency_overrides[get_db] = no_db
    # Not `with TestClient(app)`: that runs startup, which checks the real DB.
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def _configure(monkeypatch, *, env, url, enabled):
    monkeypatch.setattr(settings, "ENV", env)
    monkeypatch.setattr(settings, "DATABASE_URL_RAW", url)
    monkeypatch.setattr(settings, "ENABLE_DEBUG_ROUTES", enabled)


def _get(client):
    return client.get("/api/v1/legal/debug/retrieval", params={"q": "theft"})


def test_404_when_db_host_not_local_even_with_env_development(client, monkeypatch):
    _configure(monkeypatch, env="development", url=NEON_URL, enabled=True)
    assert _get(client).status_code == 404


@pytest.mark.parametrize("env,url,enabled", [
    ("development", LOCAL_URL, False),   # flag off
    ("staging", LOCAL_URL, True),        # not development
    ("production", LOCAL_URL, True),
    ("development", NEON_URL, False),    # the local .env as it stands
])
def test_404_when_any_condition_missing(client, monkeypatch, env, url, enabled):
    _configure(monkeypatch, env=env, url=url, enabled=enabled)
    assert _get(client).status_code == 404


@pytest.mark.parametrize("url", [LOCAL_URL, LOOPBACK_URL])
def test_served_when_all_three_hold(client, monkeypatch, url):
    _configure(monkeypatch, env="development", url=url, enabled=True)
    resp = _get(client)
    assert resp.status_code == 200
    assert resp.json() == {"traced": "theft"}


def test_flag_defaults_off():
    from app.core.config import Settings
    assert Settings.model_fields["ENABLE_DEBUG_ROUTES"].default is False
