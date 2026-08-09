"""Thin CLI: seed judicial_status (K2). Idempotent -- safe to re-run.

Usage:
    python -m scripts.seed_judicial_status
"""
from __future__ import annotations

import asyncio

from app.db.base import SessionLocal, engine
from app.legal_corpus.judicial_status_seed import ensure_judicial_status_seeded


async def main() -> None:
    async with SessionLocal() as db:
        added = await ensure_judicial_status_seeded(db)
        await db.commit()
    print(f"judicial_status: {added} row(s) added")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
