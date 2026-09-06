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
from app.core.security import hash_password
from app.models.legal import LegalQuery, QueryResponse, QueryStatus
from app.models.user import User

pytestmark = __import__("pytest").mark.integration


async def _make_user(db, email="a@example.com"):
    user = User(email=email, full_name="Test User", hashed_password=hash_password("testpassword"))
    db.add(user)
    await db.flush()
    return user


async def _seed_turn(db, session_id: str, query_text: str, summary: str, user_id=None):
    q = LegalQuery(
        original_query=query_text, detected_language="en",
        status=QueryStatus.PROCESSED, session_id=session_id, user_id=user_id,
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


async def test_history_excludes_a_different_real_users_turns(db):
    """FIXED 2026-09-06, second fix on this function, same day: _history had
    no ownership filter at all -- it fed a session's FULL row set to the LLM
    as conversational context for whoever happened to be asking now. A
    stale shared session_id (survives logout by design -- see
    caseiq-web/src/utils/session.ts) would let a second real user's visible
    ANSWER reflect a first user's conversation, not just their history page.
    Same scenario as test_conversations.py's shared-tab leak, one layer
    deeper: this is the context fed to the model, not an HTTP response.
    """
    user_a = await _make_user(db, "history-a@example.com")
    user_b = await _make_user(db, "history-b@example.com")
    session_id = "history-shared-tab"
    await _seed_turn(db, session_id, "a's question", "a's answer", user_id=user_a.id)
    await db.commit()

    # A is the session's owner (earliest logged-in row) and gets their own
    # turn back as context.
    history_for_a = await _history(db, session_id, user_a.id)
    assert [h["content"] for h in history_for_a] == ["a's question", "a's answer"]

    # B is a different real user on the same session_id -- must see NONE of
    # A's turn, not a filtered version of it.
    history_for_b = await _history(db, session_id, user_b.id)
    assert history_for_b == []

    # An anonymous caller (no account at all) on this same stale session_id
    # must also see none of A's turn.
    history_anonymous = await _history(db, session_id, None)
    assert history_anonymous == []


async def test_history_includes_anonymous_turns_for_any_caller(db):
    """Anonymous (NULL-user) turns belong to no one specifically -- unlike a
    real owner's turns, they're always fair game as context, including for
    a caller who isn't the session's eventual owner. This is what lets a
    person ask a question anonymously, log in mid-tab, and have that earlier
    turn still count as part of the SAME conversation (see
    app.api.v1.conversations's module docstring for why "earliest owner",
    not "any row", was chosen in the first place)."""
    session_id = "history-anon-then-login"
    await _seed_turn(db, session_id, "anonymous question", "anonymous answer", user_id=None)
    await db.commit()
    user_a = await _make_user(db, "history-anon-a@example.com")

    history = await _history(db, session_id, user_a.id)
    assert [h["content"] for h in history] == ["anonymous question", "anonymous answer"]
