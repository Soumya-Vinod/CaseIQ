"""Integration tests for checklist item 6, Phase C: DELETE /auth/me and
GET /auth/me/export (app.api.v1.auth) -- real deletion across
legal_queries/query_responses/complaints (not just unlinking via the FKs'
own ondelete=SET NULL default -- verified against the live schema, see
delete_account's own docstring), and the export's narrower (user_id only,
not the whole session, unlike app.api.v1.conversations) scope.
"""
from __future__ import annotations

import json
from datetime import date

import pytest
from sqlalchemy import select

from app.api.v1.auth import delete_account, export_my_data
from app.core.exceptions import AuthError
from app.core.security import hash_password
from app.models.complaint import Complaint, ComplaintType
from app.models.legal import LegalQuery, QueryResponse, QueryStatus
from app.models.user import User
from app.schemas.auth import DeleteAccountIn

pytestmark = pytest.mark.integration

_PASSWORD = "testpassword123"


async def _make_user(db, email="del@example.com"):
    user = User(email=email, full_name="Delete Me", hashed_password=hash_password(_PASSWORD))
    db.add(user)
    await db.flush()
    return user


async def test_delete_account_rejects_wrong_password(db):
    user = await _make_user(db)
    await db.commit()

    with pytest.raises(AuthError):
        await delete_account(DeleteAccountIn(password="wrong-password"), user, db)


async def test_delete_account_removes_user_and_their_queries_and_responses(db):
    user = await _make_user(db)
    q = LegalQuery(
        user_id=user.id, original_query="[NAME_1] was cheated",
        status=QueryStatus.PROCESSED, session_id="s1",
    )
    db.add(q)
    await db.flush()
    db.add(QueryResponse(
        query_id=q.id, conversational_summary="ans", structured_data={},
        retrieved_sections=[], confidence_score=0.5, response_language="en",
        processing_time_ms=1, is_followup=False,
    ))
    await db.commit()

    await delete_account(DeleteAccountIn(password=_PASSWORD), user, db)
    await db.commit()

    assert await db.get(User, user.id) is None
    remaining_queries = (
        await db.execute(select(LegalQuery).where(LegalQuery.user_id == user.id))
    ).scalars().all()
    assert remaining_queries == []
    remaining_responses = (
        await db.execute(select(QueryResponse).where(QueryResponse.query_id == q.id))
    ).scalars().all()
    assert remaining_responses == [], "should cascade via query_responses' own FK"


async def test_delete_account_removes_their_complaints_outright_not_just_unlinks(db):
    user = await _make_user(db)
    c = Complaint(
        user_id=user.id, complaint_type=ComplaintType.FIR, complainant_name="Real Name",
        complainant_address="Real Address", incident_date=date(2026, 1, 1),
        incident_location="Somewhere", incident_description="Something happened",
    )
    db.add(c)
    await db.commit()

    await delete_account(DeleteAccountIn(password=_PASSWORD), user, db)
    await db.commit()

    remaining = (await db.execute(select(Complaint).where(Complaint.id == c.id))).scalars().all()
    assert remaining == [], "complaint should be deleted outright, not merely unlinked via SET NULL"


async def test_delete_account_does_not_touch_another_users_data(db):
    user = await _make_user(db, "delete-me@example.com")
    keep = await _make_user(db, "keep-me@example.com")
    q = LegalQuery(
        user_id=keep.id, original_query="keep this",
        status=QueryStatus.PROCESSED, session_id="s-keep",
    )
    db.add(q)
    await db.commit()

    await delete_account(DeleteAccountIn(password=_PASSWORD), user, db)
    await db.commit()

    assert await db.get(User, keep.id) is not None
    still_there = (await db.execute(select(LegalQuery).where(LegalQuery.id == q.id))).scalars().all()
    assert len(still_there) == 1


async def test_export_my_data_excludes_shared_session_anonymous_turns(db):
    # Deliberately narrower than app.api.v1.conversations' ownership model --
    # export is scoped to user_id == this user only. See export_my_data's
    # own docstring for why.
    user = await _make_user(db)
    await db.commit()
    anon = LegalQuery(
        user_id=None, original_query="anonymous turn",
        status=QueryStatus.PROCESSED, session_id="s1",
    )
    mine = LegalQuery(
        user_id=user.id, original_query="my turn",
        status=QueryStatus.PROCESSED, session_id="s1",
    )
    db.add_all([anon, mine])
    await db.flush()
    db.add(QueryResponse(
        query_id=mine.id, conversational_summary="my answer", structured_data={},
        retrieved_sections=[], confidence_score=0.5, response_language="en",
        processing_time_ms=1, is_followup=False,
    ))
    await db.commit()

    response = await export_my_data(user, db)
    payload = json.loads(response.body)

    assert len(payload["conversations"]) == 1
    assert payload["conversations"][0]["your_message_as_stored"] == "my turn"


async def test_export_my_data_includes_the_redaction_note(db):
    user = await _make_user(db)
    await db.commit()

    response = await export_my_data(user, db)
    payload = json.loads(response.body)

    assert "placeholder" in payload["note"].lower()
