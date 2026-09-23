"""Background worker using arq (async-native, Redis-backed) — the modern equivalent
of the original Celery setup, without dragging in a sync execution model.

Three jobs mirror part of the original Celery beat schedule (plus Part K's K5):
  * refresh_news        — pull real legal news (every 6h)
  * backfill_embeddings — embed any section_versions rows missing a vector
  * check_for_updates   — K5 change detection (daily). Currently a no-op end to
                           end: app.legal_corpus.change_detection.poll_sources()
                           is a stub (see that module's docstring for why).
                           Scheduled now so the wiring is real and ready the
                           moment a source poller is implemented.

Data-retention cleanup (audit_logs, legal_queries/query_responses,
complaints) deliberately does NOT live here -- see scripts/retention_cleanup.py
and .github/workflows/retention-cleanup.yml. A `cleanup_audit_logs` cron job
used to live in this file; it was removed 2026-09-21 (docs/evaluation.md,
"audit_logs never self-pruning" entry) after this project's own retention
scoping pass found it had NEVER ACTUALLY RUN, arq worker never having been
deployed (docs/deployment.md: "No worker service deployed... background
workers aren't free on Render"), and audit_logs simply hadn't existed long
enough yet for any row to be old enough to expose that. Moved to a GitHub
Actions cron against DATABASE_URL_DIRECT -- the same pattern db-backup.yml
and observability-alerts.yml already use against production twice over --
rather than provisioning Redis to keep one cron job on arq. This file's
remaining three jobs are unrelated to retention and weren't touched.

Run with:  arq app.tasks.worker.WorkerSettings
"""
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.db.base import SessionLocal
from app.legal_corpus.change_detection import run_change_detection
from app.models.corpus import SectionVersion
from app.services.embeddings import embedder
from app.services.news import fetch_and_save


async def refresh_news(ctx) -> int:
    async with SessionLocal() as db:
        saved = await fetch_and_save(db, limit=15)
        await db.commit()
    return saved


async def backfill_embeddings(ctx, batch: int = 200) -> int:
    # Part K: section_versions, not the retired legal_sections -- see
    # app/services/retrieval.py's module docstring.
    async with SessionLocal() as db:
        rows = (await db.execute(
            select(SectionVersion).where(SectionVersion.embedding.is_(None)).limit(batch)
        )).scalars().all()
        for s in rows:
            s.embedding = await embedder.embed(f"{s.marginal_note}. {s.section_text[:2000]}")
        await db.commit()
    logger.info("embeddings_backfilled", count=len(rows))
    return len(rows)


async def check_for_updates(ctx) -> int:
    async with SessionLocal() as db:
        staged = await run_change_detection(db)
    logger.info("change_detection_run", staged=staged)
    return staged


async def startup(ctx) -> None:
    configure_logging()


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [refresh_news, backfill_embeddings, check_for_updates]
    on_startup = startup
    cron_jobs = [
        cron(refresh_news, hour={0, 6, 12, 18}, minute=0),
        cron(backfill_embeddings, minute={5, 35}),
        cron(check_for_updates, hour=4, minute=0),   # daily, off-peak
    ]
