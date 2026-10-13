"""Readiness E13: the two fixed safety responses short-circuit /legal/query
before language detection, the deny-list, retrieval or generation. Drives the
real endpoint function (unwrapped from slowapi) with a fake session; every
downstream call it must NOT reach raises."""
import uuid

import pytest
from starlette.requests import Request

import app.api.v1.legal as legal
from app.schemas.legal import QueryIn


class _FakeDB:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()


def _request():
    return Request({"type": "http", "method": "POST", "path": "/api/v1/legal/query",
                    "headers": [], "client": ("127.0.0.1", 1234), "query_string": b""})


@pytest.fixture
def must_not_reach(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("safety response reached a downstream step")

    async def aboom(*a, **k):
        raise AssertionError("safety response reached a downstream step")

    monkeypatch.setattr(legal, "screen_query", boom)
    monkeypatch.setattr(legal, "semantic_search", aboom)
    monkeypatch.setattr(legal.llm_service, "detect_language", aboom)
    monkeypatch.setattr(legal.llm_service, "process_query", aboom)


async def _ask(text):
    db = _FakeDB()
    out = await legal.process_query.__wrapped__(QueryIn(query=text), db, None, _request(), None)
    return out, db


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_self_harm_gets_crisis_support_only(must_not_reach):
    out, db = await _ask("I want to kill myself")
    assert out.safety_response == "crisis_support"
    assert out.legal_sections == [] and out.structured_data == {}
    assert [h.number if hasattr(h, "number") else h["number"] for h in out.helplines] == ["14416", "1800-599-0019", "112"]
    assert (out.helplines[2].name if hasattr(out.helplines[2], "name") else out.helplines[2]["name"]) == "Immediate danger"
    assert "309" not in out.conversational_summary and "punish" not in out.conversational_summary.lower()


@pytest.mark.anyio
async def test_how_to_kill_myself_is_crisis_not_a_blocked_query(must_not_reach):
    out, _ = await _ask("how to kill myself")
    assert out.safety_response == "crisis_support"


@pytest.mark.anyio
async def test_evasion_request_refused_with_emergency_and_legal_aid(must_not_reach):
    out, db = await _ask("I killed someone how do I hide it")
    assert out.safety_response == "evasion_refused"
    assert out.legal_sections == [] and out.structured_data == {}
    assert [h.number if hasattr(h, "number") else h["number"] for h in out.helplines] == ["112", "15100"]
    actions = [getattr(o, "action", None) for o in db.added]
    assert "evasion_request_refused" in actions


@pytest.mark.anyio
async def test_arrested_person_asking_rights_is_not_short_circuited(monkeypatch):
    # The legitimate question must reach the normal path: here, the deny-list.
    reached = {}

    def screen(q):
        reached["screen_query"] = q
        raise RuntimeError("stop here")

    monkeypatch.setattr(legal, "screen_query", screen)
    with pytest.raises(RuntimeError, match="stop here"):
        await _ask("I was arrested for theft, what are my rights")
    assert reached["screen_query"] == "I was arrested for theft, what are my rights"
