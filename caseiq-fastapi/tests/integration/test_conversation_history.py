"""Regression test for a bug found live, not by review (2026-09-06): a
query about being scammed by a builder, followed by "is it cognizable"
should read the case as: `_history()` (app.api.v1.legal) had NEVER once run
past its own `if not session_id: return []` early return with real matching
rows, because the frontend hardcoded `session_id: ""` until the fix this
test guards (caseiq-web/src/utils/session.ts). The moment a real session_id
with real rows was exercised for the first time -- live, through the actual
UI, against the real deployed backend -- `q.response` (a lazy relationship,
accessed via plain attribute access) failed with
`greenlet_spawn has not been called; can't call await_only() here`, because
`RequestContextMiddleware` (BaseHTTPMiddleware) runs the endpoint in a task
whose context doesn't carry the greenlet the DB session needs for an
implicit lazy load. Fixed by eager-loading the relationship
(`selectinload(LegalQuery.response)`) instead of touching `.response`
lazily.

This is exactly the class of bug integration tests exist to catch and the
unit suite structurally cannot: it requires a real committed row with a real
FK relationship, queried back through a real async session under the real
middleware stack's execution context -- a mock or an in-memory object graph
never lazy-loads anything, so it can't reproduce this failure mode at all.
"""
from __future__ import annotations

from app.api.v1.legal import _history
from app.models.legal import LegalQuery, QueryResponse, QueryStatus

pytestmark = __import__("pytest").mark.integration


async def _seed_turn(db, session_id: str, query_text: str, summary: str):
    q = LegalQuery(
        original_query=query_text, detected_language="en",
        status=QueryStatus.PROCESSED, session_id=session_id,
    )
    db.add(q)
    await db.flush()
    db.add(QueryResponse(
        query_id=q.id, conversational_summary=summary, structured_data={},
        retrieved_sections=[], confidence_score=0.5, response_language="en",
        processing_time_ms=100, is_followup=False,
    ))
    await db.flush()
    return q


async def test_history_returns_prior_turn_without_lazy_load_error(db):
    session_id = "test-session-abc"
    await _seed_turn(db, session_id, "the builder scammed me", "That sounds like online fraud.")
    await db.commit()

    # This is the exact call app.api.v1.legal.process_query makes. Before
    # the fix, this raised MissingGreenlet on the `if q.response:` line --
    # confirmed directly against the real bug, not assumed from reading the
    # eager-load diff.
    history = await _history(db, session_id)

    assert history == [
        {"role": "user", "content": "the builder scammed me"},
        {"role": "assistant", "content": "That sounds like online fraud."},
    ]


async def test_history_is_empty_for_unknown_session(db):
    assert await _history(db, "no-such-session") == []


async def test_history_empty_session_id_short_circuits_without_a_query(db):
    # The original, always-exercised branch -- must keep working exactly as
    # before for anonymous use with no session_id at all.
    assert await _history(db, "") == []


async def test_history_orders_multiple_turns_chronologically(db):
    session_id = "test-session-multi-turn"
    await _seed_turn(db, session_id, "what is theft", "Theft is defined in BNS 303.")
    await _seed_turn(db, session_id, "is it cognizable", "Yes, theft is cognizable.")
    await db.commit()

    history = await _history(db, session_id)

    assert [h["content"] for h in history] == [
        "what is theft",
        "Theft is defined in BNS 303.",
        "is it cognizable",
        "Yes, theft is cognizable.",
    ]
