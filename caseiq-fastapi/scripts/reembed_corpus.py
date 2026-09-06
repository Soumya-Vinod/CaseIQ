"""One-time re-embed of every section_versions row after the embedding-swap
migration (0009_embedding_dim_384) NULLs the column out. Must run in the same
maintenance window as that migration -- semantic_search's vector candidate
query filters on `embedding IS NOT NULL`, so an un-re-embedded row is simply
invisible to vector search (not broken, just absent) until this runs.
Full-text search is untouched, so retrieval doesn't go to zero in the gap.

Uses LocalOnnxEmbedder explicitly, not the `embedder` module-level singleton
-- this script's entire purpose is re-embedding with that specific model
regardless of whatever EMBEDDING_PROVIDER happens to be set in the running
environment's .env, so it shouldn't depend on that being configured
correctly first.

Text construction matches app/legal_corpus/ingest.py's own convention
exactly (`f"{marginal_note}. {section_text[:2000]}"`, both _insert_new and
the update-in-place path) -- re-embedding with a different text shape than
normal ingestion uses would make this corpus inconsistent with itself for
every future ingest run. Deliberately does NOT carry over ingest.py's
`asyncio.sleep(0.7)` between calls -- that pause exists for GeminiEmbedder's
external API rate limit, which has no equivalent for local ONNX inference;
carrying it here would cost roughly 25 minutes of pure waste across 2,155
rows for no reason.

Usage:
    python scripts/reembed_corpus.py
    python scripts/reembed_corpus.py --batch-size 128
"""
from __future__ import annotations

import argparse
import asyncio
import time

from sqlalchemy import select, update

from app.db.base import SessionLocal
from app.models.corpus import SectionVersion
from app.services.embeddings import LocalOnnxEmbedder


async def main(batch_size: int) -> None:
    embedder = LocalOnnxEmbedder()
    started = time.perf_counter()

    async with SessionLocal() as db:
        rows = (await db.execute(
            select(SectionVersion.id, SectionVersion.marginal_note, SectionVersion.section_text)
        )).all()
        total = len(rows)
        print(f"Re-embedding {total} section_versions rows, batch_size={batch_size}", flush=True)

        done = 0
        for i in range(0, total, batch_size):
            batch = rows[i : i + batch_size]
            texts = [f"{marginal_note}. {section_text[:2000]}" for _, marginal_note, section_text in batch]
            vectors = await embedder.embed_batch(texts)

            # ORM-enabled bulk UPDATE (SQLAlchemy 2.0): one prepared statement,
            # executed once per row via asyncpg's executemany, matched by
            # primary key -- not db.get() + attribute-set per row, which would
            # add one extra network round trip per row on top of the update
            # itself. Matters here specifically: the whole point of this
            # script's timing is to report a wall-clock re-embed cost that
            # means something (see docs/evaluation.md), not one dominated by
            # this dev machine's round-trip latency to a remote Neon instance.
            await db.execute(
                update(SectionVersion),
                [{"id": row_id, "embedding": vector} for (row_id, _, _), vector in zip(batch, vectors)],
            )
            await db.commit()
            done += len(batch)
            elapsed = time.perf_counter() - started
            print(f"  {done}/{total} ({elapsed:.1f}s elapsed)", flush=True)

    elapsed = time.perf_counter() - started
    print(f"\nDone. {total} rows re-embedded in {elapsed:.1f}s ({elapsed / 60:.2f} min).")

    async with SessionLocal() as db:
        remaining_null = (await db.execute(
            select(SectionVersion.id).where(SectionVersion.embedding.is_(None))
        )).scalars().all()
        print(f"Rows still NULL after re-embed: {len(remaining_null)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    asyncio.run(main(args.batch_size))
