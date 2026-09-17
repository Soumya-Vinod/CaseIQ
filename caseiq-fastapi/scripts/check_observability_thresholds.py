"""Standing, scheduled check against real production counters -- runs
entirely OUTSIDE the request path (see docs/evaluation.md, observability
entry, for why this and Sentry error capture are two different tools for
two different signal shapes: this is for signals that are individually
normal and only matter as a RATE -- grounding_stats / punishment_
verification_stats / citation_verification_stats, plus 429/503 volume from
audit_logs -- Sentry is for an unhandled exception or a total LLM outage,
which has no natural rate and needs a stack trace, not a count).

State (last-observed counter values + a timestamp) persisted via
actions/cache between scheduled runs, per instruction -- not a new DB
table, though this project already has three of exactly that shape (a
deliberate choice, not an oversight: this workflow only ever needs a delta
since its own last successful run, not a durable historical record).
KNOWN LIMITATION, stated rather than hidden: GitHub Actions caches are
evicted after roughly 7 days of no access -- a workflow that stops running
(disabled, or every run failing before the save step) for that long loses
its baseline, and the run after that silently evaluates a wider window than
intended (since its "last run" was actually the run before the gap). Not a
crash either way: a genuine cache miss (first run ever, or after eviction)
is treated as "no prior state" -- this run skips rate evaluation entirely,
just records current values, and evaluation resumes normally next run.

THRESHOLDS ARE PROVISIONAL, same discipline as app/core/ratelimit.py's own
documented "provisional, stated as such... revisit once there is" real
traffic -- there is currently none for this project. Wide enough not to
cry wolf on this project's own normal testing/demo traffic, narrow enough
to catch a real regression; expect to tighten (or loosen) these once real
numbers exist. Revisit this file's own numbers -- a threshold guessed once
and never revisited becomes noise people mute, which is worse than no
threshold at all.

MINIMUM SAMPLE SIZE, not just a rate: at this project's traffic volume, a
rate computed on n=2 is noise, not a signal -- each check below requires
its own minimum denominator before evaluating a rate at all, otherwise one
bad response landing right after a quiet stretch reads as a spike.

Usage: python -m scripts.check_observability_thresholds
Exit code 1 (fails the workflow -- GitHub's own default failure-email is
the delivery mechanism, no new webhook/service needed) if any threshold is
crossed. Always writes current_state.json regardless of pass/fail, so the
next run has a baseline.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.models.citation_stats import CitationVerificationStats
from app.models.grounding_stats import GroundingStats
from app.models.punishment_stats import PunishmentVerificationStats

STATE_PATH = "current_state.json"


@dataclass
class Check:
    name: str
    delta_bad: int
    delta_total: int
    min_sample: int
    threshold: float  # rate above which this fails

    @property
    def rate(self) -> float | None:
        return self.delta_bad / self.delta_total if self.delta_total > 0 else None

    @property
    def evaluated(self) -> bool:
        return self.delta_total >= self.min_sample

    @property
    def failed(self) -> bool:
        return self.evaluated and self.rate is not None and self.rate > self.threshold


async def _singleton_counts(db: AsyncSession, model) -> dict:
    row = (await db.execute(select(model).limit(1))).scalar_one_or_none()
    if row is None:
        return {}
    return {c.name: getattr(row, c.name) for c in model.__table__.columns
            if c.name not in ("id", "created_at", "updated_at")}


async def _audit_status_counts(db: AsyncSession, since: str | None) -> dict[str, int]:
    """429/503 volume from audit_logs -- the only place a rate-limited or
    LLM-failed request is recorded today (RequestContextMiddleware writes a
    `details.status` for every /api/ call). `since` is the last run's
    timestamp from cached state; None on a fresh run (no prior state)
    counts from the beginning of the table -- fine for a first run, and the
    resulting rate simply won't be evaluated if it's below min_sample.
    """
    where = "WHERE created_at > :since" if since else ""
    stmt = text(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE (details->>'status')::int = 429) AS rate_limited,
            COUNT(*) FILTER (WHERE (details->>'status')::int = 503) AS llm_failed
        FROM audit_logs
        {where}
    """)
    # asyncpg binds a `timestamptz` parameter against a real datetime object,
    # not an ISO string -- FOUND by actually running this against a real
    # Postgres (DataError: "expected a datetime.date or datetime.datetime
    # instance, got 'str'"), not assumed to work because psycopg2 (which
    # auto-casts) would have accepted it silently.
    params = {"since": datetime.fromisoformat(since)} if since else {}
    row = (await db.execute(stmt, params)).mappings().one()
    return {"total": row["total"], "rate_limited": row["rate_limited"], "llm_failed": row["llm_failed"]}


def _load_state() -> dict | None:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


async def main() -> None:
    engine = create_async_engine(settings.MIGRATION_DATABASE_URL)
    async with AsyncSession(engine) as db:
        grounding = await _singleton_counts(db, GroundingStats)
        punishment = await _singleton_counts(db, PunishmentVerificationStats)
        citation = await _singleton_counts(db, CitationVerificationStats)
        prior = _load_state()
        audit = await _audit_status_counts(db, prior.get("timestamp") if prior else None)
    await engine.dispose()

    current = {
        "timestamp": datetime.now(UTC).isoformat(),
        "grounding": grounding, "punishment": punishment, "citation": citation,
    }

    if prior is None:
        print("No prior state (first run, or the cache was evicted/never saved) -- "
              "recording a baseline only, not evaluating any rate this run.")
        _save_state(current)
        return

    def delta(cur: dict, prev: dict, key: str) -> int:
        return cur.get(key, 0) - prev.get(key, 0)

    checks = [
        Check(
            name="grounding: ungrounded response rate",
            delta_bad=(delta(grounding, prior["grounding"], "responses_ungrounded_never_cited")
                       + delta(grounding, prior["grounding"], "responses_ungrounded_stripped_to_zero")),
            delta_total=delta(grounding, prior["grounding"], "responses_total"),
            min_sample=20, threshold=0.25,
        ),
        Check(
            name="punishment: suppressed-mismatch rate",
            delta_bad=delta(punishment, prior["punishment"], "punishments_suppressed_mismatch"),
            delta_total=delta(punishment, prior["punishment"], "punishments_total"),
            min_sample=10, threshold=0.10,
        ),
        Check(
            name="citation: stripped (fabricated/not-retrieved) rate",
            delta_bad=(delta(citation, prior["citation"], "citations_stripped_nonexistent")
                       + delta(citation, prior["citation"], "citations_stripped_not_retrieved")),
            delta_total=delta(citation, prior["citation"], "citations_total"),
            min_sample=20, threshold=0.15,
        ),
        Check(
            name="429 rate-limited request rate",
            delta_bad=audit["rate_limited"], delta_total=audit["total"],
            min_sample=20, threshold=0.30,
        ),
        Check(
            name="503 LLM-unavailable request rate",
            delta_bad=audit["llm_failed"], delta_total=audit["total"],
            min_sample=20, threshold=0.10,
        ),
    ]

    failures = []
    for c in checks:
        if not c.evaluated:
            print(f"[skip] {c.name}: only {c.delta_total} sample(s) since last run "
                  f"(need {c.min_sample}) -- not enough traffic to evaluate.")
            continue
        status = "FAIL" if c.failed else "ok"
        print(f"[{status}] {c.name}: {c.delta_bad}/{c.delta_total} = {c.rate:.1%} "
              f"(threshold {c.threshold:.0%})")
        if c.failed:
            failures.append(c)

    _save_state(current)

    if failures:
        print(f"\n{len(failures)} threshold(s) crossed -- see FAIL lines above. "
              f"Thresholds are provisional (this file's own module docstring); "
              f"if this is a false alarm on normal traffic, revisit the number, "
              f"don't just re-run.")
        sys.exit(1)
    print("\nAll evaluated thresholds held.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
