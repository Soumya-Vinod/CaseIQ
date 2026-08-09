"""Background worker using arq (async-native, Redis-backed) — the modern equivalent
of the original Celery setup, without dragging in a sync execution model.

Three jobs mirror the original Celery beat schedule:
  * refresh_news        — pull real legal news (every 6h)
  * backfill_embeddings — embed any section_versions rows missing a vector
  * cleanup_audit_logs  — delete audit_logs older than AUDIT_LOG_RETENTION_DAYS (daily)

Run with:  arq app.tasks.worker.WorkerSettings
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.db.base import SessionLocal
from app.models.audit import AuditLog
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


async def cleanup_audit_logs(ctx) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
    async with SessionLocal() as db:
        result = await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        await db.commit()
    deleted = result.rowcount or 0
    logger.info("audit_logs_cleaned", deleted=deleted, retention_days=settings.AUDIT_LOG_RETENTION_DAYS)
    return deleted


async def startup(ctx) -> None:
    configure_logging()


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [refresh_news, backfill_embeddings, cleanup_audit_logs]
    on_startup = startup
    cron_jobs = [
        cron(refresh_news, hour={0, 6, 12, 18}, minute=0),
        cron(backfill_embeddings, minute={5, 35}),
        cron(cleanup_audit_logs, hour=3, minute=0),  # daily, off-peak
    ]
