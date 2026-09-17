"""Thin CLI: seed judicial_status (K2). Idempotent -- safe to re-run.

Usage:
    python -m scripts.seed_judicial_status
    python -m scripts.seed_judicial_status --yes   # skip the confirmation prompt
"""
from __future__ import annotations

import argparse
import asyncio

from app.db.base import SessionLocal, engine
from app.legal_corpus.judicial_status_seed import ensure_judicial_status_seeded
from scripts.lib.production_guard import confirm_writable_target


async def main(skip_prompt: bool = False) -> None:
    confirm_writable_target("seed_judicial_status", skip_prompt=skip_prompt)
    async with SessionLocal() as db:
        added = await ensure_judicial_status_seeded(db)
        await db.commit()
    print(f"judicial_status: {added} row(s) added")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true",
                        help="Skip the production-write confirmation prompt.")
    args = parser.parse_args()
    asyncio.run(main(args.yes))
