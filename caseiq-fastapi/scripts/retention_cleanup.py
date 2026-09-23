"""Data retention enforcement (docs/dpdp-compliance.md §6) -- the highest-
consequence automation in this project: it permanently destroys user data
on a schedule with nobody watching. Scoped in docs/evaluation.md before a
line of this was written ("Retention automation" entry, 2026-09-20); read
that entry for the full reasoning behind every design choice below, not
just this docstring's summary.

Three tables, three rules:
  - audit_logs:      created_at older than AUDIT_LOG_RETENTION_DAYS (90).
  - legal_queries:   session-ownership aware, see below. query_responses is
                      NOT touched directly -- its FK (query_id, ondelete=
                      CASCADE, verified against the live schema) cleans it
                      up automatically when the parent legal_queries row
                      goes, same mechanism DELETE /legal/conversations/{id}
                      already relies on.
  - complaints:      created_at older than COMPLAINT_RETENTION_MONTHS (24).
                      Real row removal, not anonymisation -- an anonymised
                      complaint is neither filable nor useful for anything,
                      so anonymising it keeps the storage cost with none of
                      the benefit (docs/evaluation.md's scoping entry).

**Session ownership, the one genuine correctness trap this whole scope
exists to avoid**: a `legal_queries` row's applicable window is NOT decided
by that row's own `user_id`. `app/api/v1/conversations.py`'s own ownership
model -- a session_id's owner is the user_id on its EARLIEST logged-in row,
not "any row with user_id set" -- means a session that started anonymous
and was later claimed by a mid-conversation login has PRE-LOGIN turns with
user_id NULL that are still genuinely that user's own conversation (visible
on their history page, deletable via DELETE /legal/conversations/{id}).
A naive `WHERE user_id IS NULL AND created_at < 30 days` would silently
delete a logged-in user's own history out from under them. This module
computes "claimed" at the SESSION level (does this session_id have ANY row
with user_id set, ever) and applies LEGAL_QUERY_RETENTION_MONTHS_CLAIMED to
EVERY row in a claimed session -- including its pre-login ones -- and
LEGAL_QUERY_RETENTION_DAYS_ANONYMOUS only to a session that has never been
claimed. tests/test_retention_cleanup.py's
test_claimed_sessions_pre_login_turns_survive_past_anonymous_window is the
direct regression test for this -- the case that would have shipped
silently, per instruction.

A `legal_queries` row with an empty session_id (shouldn't happen in
practice -- the frontend always sets one -- but not assumed impossible)
has no session to group into; it falls back to its OWN user_id as if it
were a session of one.

**Safety, all four pieces named in the scoping pass, all four built**:
  1. Dry-run is the DEFAULT. Nothing is ever deleted without --delete.
  2. A row-count CEILING per table -- a hardcoded constant, not a rolling
     average (deliberately: an average learns from its own failures, one
     over-deleting run inflates the average and loosens the guard for the
     next run, which is backwards -- see docs/evaluation.md). Seeded from
     this module's own first real dry-run against production, not guessed.
     Exceeding ANY table's ceiling aborts the ENTIRE run before anything is
     deleted from ANY table -- an all-or-nothing check, not per-table, so a
     bug that inflates one table's count can't be partially masked by the
     other two tables looking fine.
  3. No dedicated pre-delete backup -- relies on the existing nightly
     `db-backup.yml` (02:17 UTC), which already dumps every table this
     script touches (users, legal_queries, query_responses, complaints,
     audit_logs, corpus_versions). This script's own cron (see
     .github/workflows/retention-cleanup.yml) is scheduled at 04:00 UTC,
     after both db-backup.yml (02:17) and nightly-eval.yml (03:30), so the
     most recent backup is never more than ~26 hours stale relative to any
     delete this script performs.
  4. Structured logging + a counter per table, per run -- see `logger.info`
     calls below, same shape as the cleanup_audit_logs job this replaces.

Usage:
    python -m scripts.retention_cleanup                # dry run (default)
    python -m scripts.retention_cleanup --delete        # real run
    python -m scripts.retention_cleanup --delete --yes  # skip the confirmation prompt (CI)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.db.base import SessionLocal, engine
from app.models.complaint import Complaint
from app.models.legal import LegalQuery
from app.models.audit import AuditLog
from scripts.lib.production_guard import confirm_writable_target

# Hardcoded, not a rolling average -- see module docstring. NOT genuinely
# "seeded from a dry-run" the way the original plan intended: this script's
# own first real dry-run against production (2026-09-21, docs/evaluation.md)
# returned 0/0/0 for all three tables -- the project is too young for any
# row to have crossed even the shortest (30-day, never-claimed) window yet,
# so there was no real deletion volume to calibrate against. These are
# deliberately conservative placeholder guesses instead, sized well above
# what this project's current traffic could plausibly produce in one day but
# nowhere near "large enough to never fire" -- and they MUST be revisited
# once the first real, non-zero dry-run numbers exist (soon: the oldest
# audit_logs row is already ~39 days old as of this writing, under the
# 90-day cutoff but not by much), not left as this initial guess
# indefinitely. Revisit by hand roughly yearly after that, or sooner if
# traffic genuinely grows past these -- a constant that occasionally blocks
# a legitimate large batch fails in the safe direction; that's the point.
_CEILINGS = {
    "audit_logs": 500,
    "legal_queries": 200,
    "complaints": 50,
}


def _months_ago(n: int) -> datetime:
    # Calendar-months-aware, not a flat 30*n days -- "24 months" should mean
    # 24 months, not 720 days (a 2-day/year drift over the complaints
    # window). No extra dependency: 30.44 days/month average, then corrected
    # to the exact day-of-month where possible.
    now = datetime.now(UTC)
    year = now.year
    month = now.month - n
    while month <= 0:
        month += 12
        year -= 1
    try:
        return now.replace(year=year, month=month)
    except ValueError:
        # e.g. today is the 31st and the target month has fewer days --
        # fall back to that month's last day rather than raising.
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        return now.replace(year=year, month=month, day=last_day)


@dataclass
class CleanupResult:
    table: str
    would_delete: int
    ceiling: int
    deleted: int | None = None  # None until a real (non-dry-run) delete actually runs

    @property
    def over_ceiling(self) -> bool:
        return self.would_delete > self.ceiling


async def _claimed_session_ids(db: AsyncSession) -> set[str]:
    """Every session_id that has EVER had a row with user_id set -- same
    definition app.api.v1.conversations._session_owner() uses ("earliest
    logged-in row"), just as a set membership test rather than a per-session
    lookup, since this module needs it for every row at once.
    """
    rows = (await db.execute(
        select(LegalQuery.session_id)
        .where(LegalQuery.user_id.is_not(None), LegalQuery.session_id != "")
        .distinct()
    )).scalars().all()
    return set(rows)


async def _legal_query_delete_predicate(db: AsyncSession):
    """Returns (predicate, claimed_session_count) -- the predicate is a
    SQLAlchemy boolean expression selecting exactly the legal_queries rows
    eligible for deletion under the session-ownership-aware rule this
    module's docstring describes. Built once, reused for both the dry-run
    COUNT and the real DELETE, so the two can never disagree.
    """
    claimed = await _claimed_session_ids(db)
    anon_cutoff = datetime.now(UTC) - timedelta(days=settings.LEGAL_QUERY_RETENTION_DAYS_ANONYMOUS)
    claimed_cutoff = _months_ago(settings.LEGAL_QUERY_RETENTION_MONTHS_CLAIMED)

    # false() (a real SQL FALSE, not Python's falsy `False` -- and_/or_ need an
    # actual SQL expression) when `claimed` is empty, so "session is claimed"
    # cleanly evaluates to never-true and its negation to always-true, with no
    # special-casing needed below for the empty-set case.
    session_is_claimed = LegalQuery.session_id.in_(claimed) if claimed else false()

    predicate = or_(
        # Non-empty session_id: governed by whether the SESSION is claimed,
        # never this row's own user_id -- the whole reason this function
        # exists rather than a plain per-row WHERE.
        and_(LegalQuery.session_id != "", session_is_claimed, LegalQuery.created_at < claimed_cutoff),
        and_(LegalQuery.session_id != "", ~session_is_claimed, LegalQuery.created_at < anon_cutoff),
        # Empty session_id (shouldn't happen -- frontend always sets one --
        # but handled, not assumed impossible): falls back to this row's own
        # user_id, as if it were a session of one.
        and_(LegalQuery.session_id == "", LegalQuery.user_id.is_not(None), LegalQuery.created_at < claimed_cutoff),
        and_(LegalQuery.session_id == "", LegalQuery.user_id.is_(None), LegalQuery.created_at < anon_cutoff),
    )
    return predicate, len(claimed)


async def _count_legal_queries(db: AsyncSession) -> int:
    predicate, _ = await _legal_query_delete_predicate(db)
    return (await db.execute(select(func.count()).where(predicate))).scalar_one()


async def _count_audit_logs(db: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
    return (await db.execute(select(func.count()).where(AuditLog.created_at < cutoff))).scalar_one()


async def _count_complaints(db: AsyncSession) -> int:
    cutoff = _months_ago(settings.COMPLAINT_RETENTION_MONTHS)
    return (await db.execute(select(func.count()).where(Complaint.created_at < cutoff))).scalar_one()


async def dry_run(db: AsyncSession) -> list[CleanupResult]:
    audit_count = await _count_audit_logs(db)
    legal_count = await _count_legal_queries(db)
    complaint_count = await _count_complaints(db)
    return [
        CleanupResult("audit_logs", audit_count, _CEILINGS["audit_logs"]),
        CleanupResult("legal_queries", legal_count, _CEILINGS["legal_queries"]),
        CleanupResult("complaints", complaint_count, _CEILINGS["complaints"]),
    ]


async def execute_deletes(db: AsyncSession, results: list[CleanupResult]) -> list[CleanupResult]:
    """Only called after the caller has already confirmed no result is
    over_ceiling -- see main(). Re-derives each delete's own predicate
    fresh (not reusing dry_run's counts as the delete condition) so a
    row that changed state between the count and the delete can't cause a
    mismatch; rowcount is what's actually reported, not the earlier count.
    """
    out = []
    for r in results:
        if r.table == "audit_logs":
            cutoff = datetime.now(UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
            result = await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        elif r.table == "legal_queries":
            predicate, _ = await _legal_query_delete_predicate(db)
            result = await db.execute(delete(LegalQuery).where(predicate))
        elif r.table == "complaints":
            cutoff = _months_ago(settings.COMPLAINT_RETENTION_MONTHS)
            result = await db.execute(delete(Complaint).where(Complaint.created_at < cutoff))
        else:
            raise ValueError(f"unknown table {r.table!r}")
        deleted = result.rowcount or 0
        out.append(CleanupResult(r.table, r.would_delete, r.ceiling, deleted=deleted))
        logger.info("retention_cleanup_deleted", table=r.table, deleted=deleted,
                    ceiling=r.ceiling, expected=r.would_delete)
    await db.commit()
    return out


def _print_results(results: list[CleanupResult], *, executed: bool) -> None:
    verb = "deleted" if executed else "would delete"
    for r in results:
        count = r.deleted if executed and r.deleted is not None else r.would_delete
        flag = "  ** OVER CEILING **" if r.over_ceiling else ""
        print(f"  {r.table}: {verb} {count} row(s) (ceiling {r.ceiling}){flag}")


async def main(do_delete: bool, skip_prompt: bool) -> int:
    configure_logging()
    if do_delete:
        confirm_writable_target("retention_cleanup", skip_prompt=skip_prompt)

    async with SessionLocal() as db:
        results = await dry_run(db)
        print("Retention cleanup -- counts as of this run:")
        _print_results(results, executed=False)

        over_ceiling = [r for r in results if r.over_ceiling]
        if over_ceiling:
            names = ", ".join(f"{r.table} ({r.would_delete} > {r.ceiling})" for r in over_ceiling)
            print(f"\nABORTING -- over ceiling: {names}. Nothing deleted from ANY table "
                  f"(all-or-nothing check, see module docstring). Investigate before "
                  f"raising the ceiling by hand -- a number this far over the seeded "
                  f"baseline is more likely a bug than organic growth.",
                  file=sys.stderr)
            logger.warning("retention_cleanup_aborted_over_ceiling",
                            tables={r.table: r.would_delete for r in over_ceiling})
            return 1

        if not do_delete:
            print("\nDry run -- no changes written. Re-run with --delete to actually delete.")
            return 0

        executed = await execute_deletes(db, results)
        print("\nDeleted:")
        _print_results(executed, executed=True)
        logger.info("retention_cleanup_completed",
                    **{r.table: r.deleted for r in executed})

    await engine.dispose()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true",
                         help="Actually delete. Without this, always a dry run.")
    parser.add_argument("--yes", action="store_true",
                         help="Skip the interactive production-write confirmation prompt.")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.delete, args.yes)))
