"""Integration coverage for scripts/retention_cleanup.py (docs/evaluation.md,
"Retention automation" scoping + build entries, 2026-09-20/21) -- the
highest-consequence automation in this project, so this needs a real
Postgres and real rows, not a mocked query.

test_claimed_sessions_pre_login_turns_survive_past_anonymous_window is the
one that matters most: seeded, per instruction, before any of the other
tests were written, because it's the exact case that would have shipped
silently with a naive `WHERE user_id IS NULL AND created_at < 30 days`
implementation -- a logged-in user's own pre-login turns deleted out from
under them, with no error and nothing to notice it by.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.complaint import Complaint, ComplaintStatus, ComplaintType
from app.models.legal import LegalQuery, QueryResponse, QueryStatus
from app.models.user import User
from scripts.retention_cleanup import (
    CleanupResult, _count_audit_logs, _count_complaints, _count_legal_queries,
    dry_run, execute_deletes,
)

pytestmark = pytest.mark.integration


async def _make_user(db, email="retention-test@example.com"):
    user = User(email=email, full_name="Retention Test", hashed_password=hash_password("testpassword"))
    db.add(user)
    await db.flush()
    return user


async def _seed_turn(db, session_id: str, created_at: datetime, *, user_id=None, with_response=True):
    q = LegalQuery(
        original_query="test query", detected_language="en",
        status=QueryStatus.PROCESSED, session_id=session_id, user_id=user_id,
        created_at=created_at,
    )
    db.add(q)
    await db.flush()
    if with_response:
        db.add(QueryResponse(
            query_id=q.id, conversational_summary="test summary", structured_data={},
            retrieved_sections=[], confidence_score=0.5, response_language="en",
            processing_time_ms=100, is_followup=False,
        ))
        await db.flush()
    return q


async def _seed_complaint(db, created_at: datetime, *, user_id=None):
    c = Complaint(
        user_id=user_id, complaint_type=ComplaintType.FIR,
        complainant_name="Test Complainant", complainant_address="123 Test St",
        incident_date=created_at.date(), incident_location="Test City",
        incident_description="test incident", status=ComplaintStatus.DRAFT,
        created_at=created_at,
    )
    db.add(c)
    await db.flush()
    return c


async def _seed_audit_log(db, created_at: datetime):
    a = AuditLog(action="test_action", details={}, created_at=created_at)
    db.add(a)
    await db.flush()
    return a


def _days_ago(n: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=n)


class TestSessionOwnershipIsTheGate:
    """The case the whole scoping pass existed to get right."""

    async def test_claimed_sessions_pre_login_turns_survive_past_anonymous_window(self, db):
        user = await _make_user(db)
        session_id = "claimed-session-with-old-preload-turn"
        # Pre-login turn: 45 days old -- past the 30-day anonymous window,
        # well under the 12-month claimed window. user_id is None on this
        # SPECIFIC row (it happened before login), but the SESSION is
        # claimed by a later logged-in turn.
        old_anonymous_turn = await _seed_turn(db, session_id, _days_ago(45), user_id=None)
        # The turn that claims the session, 10 days old.
        await _seed_turn(db, session_id, _days_ago(10), user_id=user.id)
        await db.commit()

        results = await dry_run(db)
        legal = next(r for r in results if r.table == "legal_queries")
        assert legal.would_delete == 0, (
            "a naive per-row user_id check would have counted the 45-day-old "
            "pre-login turn as anonymous-and-expired; it must not be, because "
            "its session is claimed"
        )

        await execute_deletes(db, results)
        await db.commit()

        survivor = await db.get(LegalQuery, old_anonymous_turn.id)
        assert survivor is not None, (
            "the pre-login turn of a claimed session was deleted -- exactly "
            "the silent data-loss case this whole design exists to prevent"
        )

    async def test_claimed_session_turn_deleted_once_past_12_months(self, db):
        user = await _make_user(db, "retention-test-2@example.com")
        session_id = "claimed-session-genuinely-old"
        ancient_turn = await _seed_turn(db, session_id, _days_ago(400), user_id=None)
        await _seed_turn(db, session_id, _days_ago(5), user_id=user.id)
        await db.commit()

        results = await dry_run(db)
        legal = next(r for r in results if r.table == "legal_queries")
        assert legal.would_delete == 1

        await execute_deletes(db, results)
        await db.commit()

        assert await db.get(LegalQuery, ancient_turn.id) is None

    async def test_never_claimed_session_deleted_after_30_days(self, db):
        session_id = "never-claimed-session"
        old_row = await _seed_turn(db, session_id, _days_ago(31), user_id=None)
        await db.commit()

        results = await dry_run(db)
        legal = next(r for r in results if r.table == "legal_queries")
        assert legal.would_delete == 1

        await execute_deletes(db, results)
        await db.commit()

        assert await db.get(LegalQuery, old_row.id) is None

    async def test_never_claimed_session_survives_under_30_days(self, db):
        session_id = "never-claimed-recent-session"
        recent_row = await _seed_turn(db, session_id, _days_ago(5), user_id=None)
        await db.commit()

        results = await dry_run(db)
        await execute_deletes(db, results)
        await db.commit()

        assert await db.get(LegalQuery, recent_row.id) is not None

    async def test_query_response_cascades_when_legal_query_deleted(self, db):
        session_id = "never-claimed-with-response"
        old_row = await _seed_turn(db, session_id, _days_ago(31), user_id=None, with_response=True)
        await db.commit()

        response = (await db.execute(
            select(QueryResponse).where(QueryResponse.query_id == old_row.id)
        )).scalar_one_or_none()
        assert response is not None, "seeding assumption failed -- fix the test fixture"

        results = await dry_run(db)
        await execute_deletes(db, results)
        await db.commit()

        assert (await db.execute(
            select(QueryResponse).where(QueryResponse.query_id == old_row.id)
        )).scalar_one_or_none() is None, "query_responses row must cascade-delete with its parent"


class TestAuditLogRetention:
    async def test_old_row_deleted(self, db):
        old = await _seed_audit_log(db, _days_ago(91))
        await db.commit()
        results = await dry_run(db)
        await execute_deletes(db, results)
        await db.commit()
        assert await db.get(AuditLog, old.id) is None

    async def test_recent_row_survives(self, db):
        recent = await _seed_audit_log(db, _days_ago(10))
        await db.commit()
        results = await dry_run(db)
        await execute_deletes(db, results)
        await db.commit()
        assert await db.get(AuditLog, recent.id) is not None


class TestComplaintRetention:
    async def test_old_complaint_deleted(self, db):
        old = await _seed_complaint(db, _days_ago(760))  # > 24 months
        await db.commit()
        results = await dry_run(db)
        await execute_deletes(db, results)
        await db.commit()
        assert await db.get(Complaint, old.id) is None

    async def test_recent_complaint_survives(self, db):
        recent = await _seed_complaint(db, _days_ago(30))
        await db.commit()
        results = await dry_run(db)
        await execute_deletes(db, results)
        await db.commit()
        assert await db.get(Complaint, recent.id) is not None


class TestDryRunNeverWrites:
    async def test_dry_run_deletes_nothing(self, db):
        old_audit = await _seed_audit_log(db, _days_ago(91))
        old_complaint = await _seed_complaint(db, _days_ago(760))
        old_query = await _seed_turn(db, "dry-run-session", _days_ago(31), user_id=None)
        await db.commit()

        results = await dry_run(db)
        assert all(r.deleted is None for r in results), "dry_run() itself must never populate .deleted"

        # Nothing was actually deleted -- dry_run() alone was called, execute_deletes() was not.
        assert await db.get(AuditLog, old_audit.id) is not None
        assert await db.get(Complaint, old_complaint.id) is not None
        assert await db.get(LegalQuery, old_query.id) is not None


class TestCeiling:
    def test_over_ceiling_flag(self):
        r = CleanupResult(table="audit_logs", would_delete=1000, ceiling=500)
        assert r.over_ceiling is True

    def test_under_ceiling_flag(self):
        r = CleanupResult(table="audit_logs", would_delete=10, ceiling=500)
        assert r.over_ceiling is False

    def test_exactly_at_ceiling_not_over(self):
        r = CleanupResult(table="audit_logs", would_delete=500, ceiling=500)
        assert r.over_ceiling is False
