"""Integration tests for checklist item 6, Phase C: app.api.v1.conversations
(list/get/delete a logged-in user's own conversation history) and the
ownership model documented on that module -- a session_id shared between an
anonymous pre-login turn and a later logged-in turn is owned, in full, by
whichever user has at least one row in it. Needs a real Postgres for the
same reason tests/integration/test_conversation_history.py does (see that
file's own module docstring) -- these call the endpoint functions directly
against a real committed row graph, not through the HTTP layer, same
pattern as that file's `_history` tests.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.api.v1.conversations import delete_conversation, get_conversation, list_conversations
from app.core.exceptions import NotFoundError
from app.core.security import hash_password
from app.models.legal import LegalQuery, QueryResponse, QueryStatus
from app.models.user import User

pytestmark = pytest.mark.integration


async def _make_user(db, email="a@example.com"):
    user = User(email=email, full_name="Test User", hashed_password=hash_password("testpassword"))
    db.add(user)
    await db.flush()
    return user


async def _seed_turn(db, session_id, query_text, summary, user_id=None):
    q = LegalQuery(
        user_id=user_id, original_query=query_text, detected_language="en",
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


async def test_list_conversations_is_empty_with_no_rows(db):
    user = await _make_user(db)
    assert await list_conversations(user, db) == []


async def test_list_conversations_only_shows_sessions_this_user_owns(db):
    user = await _make_user(db, "mine@example.com")
    other = await _make_user(db, "other@example.com")
    await _seed_turn(db, "s-mine", "what is theft", "Theft is BNS 303.", user_id=user.id)
    await _seed_turn(db, "s-other", "what is cheating", "Cheating is BNS 318.", user_id=other.id)
    await db.commit()

    summaries = await list_conversations(user, db)

    assert [s.session_id for s in summaries] == ["s-mine"]


async def test_list_conversations_groups_by_session_and_counts_turns(db):
    user = await _make_user(db)
    await _seed_turn(db, "s1", "what is theft", "Theft is BNS 303.", user_id=user.id)
    await _seed_turn(db, "s1", "is it cognizable", "Yes.", user_id=user.id)
    await db.commit()

    summaries = await list_conversations(user, db)

    assert len(summaries) == 1
    assert summaries[0].turn_count == 2
    assert summaries[0].preview == "what is theft"


async def test_list_conversations_orders_most_recent_first(db):
    user = await _make_user(db)
    await _seed_turn(db, "s-old", "old question", "old answer", user_id=user.id)
    await _seed_turn(db, "s-new", "new question", "new answer", user_id=user.id)
    await db.commit()

    summaries = await list_conversations(user, db)

    assert [s.session_id for s in summaries] == ["s-new", "s-old"]


async def test_get_conversation_includes_pre_login_anonymous_turns_in_the_same_session(db):
    # The exact scenario the ownership model exists for: a couple of
    # anonymous questions before logging in, then one more after, all in
    # the same browser-tab session_id (see caseiq-web/src/utils/session.ts
    # -- one id per tab, independent of login).
    user = await _make_user(db)
    await _seed_turn(db, "s1", "anonymous question", "anonymous answer", user_id=None)
    await _seed_turn(db, "s1", "logged in question", "logged in answer", user_id=user.id)
    await db.commit()

    detail = await get_conversation("s1", user, db)

    assert [t.original_query for t in detail.turns] == ["anonymous question", "logged in question"]


async def test_get_conversation_404s_for_a_session_this_user_never_touched(db):
    user = await _make_user(db)
    other = await _make_user(db, "other@example.com")
    await _seed_turn(db, "s-other", "not yours", "not yours either", user_id=other.id)
    await db.commit()

    with pytest.raises(NotFoundError):
        await get_conversation("s-other", user, db)


async def test_get_conversation_404s_for_an_unknown_session(db):
    user = await _make_user(db)
    with pytest.raises(NotFoundError):
        await get_conversation("no-such-session", user, db)


async def test_get_conversation_404s_for_a_session_that_was_never_logged_in(db):
    # A session with real rows, but none of them ever had a user_id -- e.g.
    # someone used the app anonymously and never logged in during that tab.
    # _session_owner returns None for this; None must never match a real
    # user's id. See app.api.v1.conversations' own "Anonymous sessions"
    # docstring paragraph.
    user = await _make_user(db)
    await _seed_turn(db, "s-anon", "anonymous only", "anonymous answer", user_id=None)
    await db.commit()

    with pytest.raises(NotFoundError):
        await get_conversation("s-anon", user, db)


async def test_shared_tab_cross_user_leak_is_closed(db):
    """The exact scenario found in review, 2026-09-06: A logs in, asks a
    question, logs out; B logs into the SAME browser tab (same session_id
    -- see utils/session.ts) and continues. Before the fix, ownership was
    "any row matches", so this session belonged to both A and B and each
    could read/delete the other's turns. Ownership is now the EARLIEST
    logged-in row's user_id -- A's, here, since A asked first.
    """
    user_a = await _make_user(db, "a@example.com")
    user_b = await _make_user(db, "b@example.com")
    await _seed_turn(db, "shared-tab", "a's question", "a's answer", user_id=user_a.id)
    # Simulates B continuing the same session_id after A logged out --
    # itself now prevented client-side by AuthContext's logout() resetting
    # the tab's session_id (utils/session.ts's resetSessionId), but this
    # endpoint must not depend on that frontend behaviour ever holding.
    await _seed_turn(db, "shared-tab", "b's question", "b's answer", user_id=user_b.id)
    await db.commit()

    # A still owns it (asked first) and sees only their own turn -- B's
    # row, carrying a genuinely different real user_id, is filtered out
    # even though A is the session's rightful owner.
    detail_for_a = await get_conversation("shared-tab", user_a, db)
    assert [t.original_query for t in detail_for_a.turns] == ["a's question"]

    # B does NOT own it -- being second, not first -- and cannot read it.
    with pytest.raises(NotFoundError):
        await get_conversation("shared-tab", user_b, db)
    with pytest.raises(NotFoundError):
        await delete_conversation("shared-tab", user_b, db)

    # B also never appears in A's conversation list for this session.
    summaries = await list_conversations(user_a, db)
    assert [s.session_id for s in summaries] == ["shared-tab"]
    assert summaries[0].turn_count == 1

    # A deleting "their" conversation removes only their own row -- B's
    # stray row (which should never have existed post-fix, but this
    # endpoint doesn't get to assume that) survives, since it isn't
    # NULL-user and isn't A's.
    await delete_conversation("shared-tab", user_a, db)
    await db.commit()
    remaining = (
        await db.execute(select(LegalQuery).where(LegalQuery.session_id == "shared-tab"))
    ).scalars().all()
    assert [q.user_id for q in remaining] == [user_b.id]


async def test_delete_conversation_removes_the_whole_session_including_anonymous_turns(db):
    user = await _make_user(db)
    await _seed_turn(db, "s1", "anonymous question", "anonymous answer", user_id=None)
    await _seed_turn(db, "s1", "logged in question", "logged in answer", user_id=user.id)
    await db.commit()

    await delete_conversation("s1", user, db)
    await db.commit()

    remaining = (
        await db.execute(select(LegalQuery).where(LegalQuery.session_id == "s1"))
    ).scalars().all()
    assert remaining == []


async def test_delete_conversation_404s_for_a_session_this_user_never_touched(db):
    user = await _make_user(db)
    other = await _make_user(db, "other@example.com")
    await _seed_turn(db, "s-other", "not yours", "not yours either", user_id=other.id)
    await db.commit()

    with pytest.raises(NotFoundError):
        await delete_conversation("s-other", user, db)

    # And the row must still be there -- a 404 has to mean nothing happened.
    still_there = (
        await db.execute(select(LegalQuery).where(LegalQuery.session_id == "s-other"))
    ).scalars().all()
    assert len(still_there) == 1
