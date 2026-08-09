"""Background worker using arq (async-native, Redis-backed) — the modern equivalent
of the original Celery setup, without dragging in a sync execution model.

Two jobs mirror the original Celery beat schedule:
  * refresh_news   — pull real legal news (every 6h)
  * backfill_embeddings — embed any LegalSection rows missing a vector

Run with:  arq app.tasks.worker.WorkerSettings
"""
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.db.base import SessionLocal
from app.models.legal import LegalSection
from app.services.embeddings import embedder
from app.services.news import fetch_and_save


async def refresh_news(ctx) -> int:
    async with SessionLocal() as db:
        saved = await fetch_and_save(db, limit=15)
        await db.commit()
    return saved


async def backfill_embeddings(ctx, batch: int = 200) -> int:
    async with SessionLocal() as db:
        rows = (await db.execute(
            select(LegalSection).where(LegalSection.embedding.is_(None)).limit(batch)
        )).scalars().all()
        for s in rows:
            s.embedding = await embedder.embed(f"{s.section_title}. {s.section_text[:2000]}")
        await db.commit()
    logger.info("embeddings_backfilled", count=len(rows))
    return len(rows)


async def startup(ctx) -> None:
    configure_logging()


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [refresh_news, backfill_embeddings]
    on_startup = startup
    cron_jobs = [
        cron(refresh_news, hour={0, 6, 12, 18}, minute=0),
        cron(backfill_embeddings, minute={5, 35}),
    ]
