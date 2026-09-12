"""One-off backfill for alembic/versions/0011_hash_legal_query_ip.py.

That migration only renames legal_queries.ip_address -> ip_hash -- a schema
change, not a data one (same convention 0003_hash_audit_ip used, but that
one ran before audit_logs had any real rows, so a rename alone was enough
there; this table already has real rows with raw IPs in it). Run this once,
right after the migration deploys, to actually hash them.

Uses the real app.core.security.hash_ip() -- the same function AuditLog and
(as of this fix) LegalQuery's own write path now call -- not a
reimplementation, so a backfilled row's hash correlates with audit_logs
rows for the same visitor exactly the way newly-written rows do.

Idempotent, safe to re-run: only touches rows that don't already look like
a hash_ip() output (40 lowercase hex chars) -- a raw IPv4/IPv6 address
never matches that shape, so a second run after the first is a no-op, not
a double-hash.

Usage:
    python -m scripts.backfill_legal_query_ip_hash
    python -m scripts.backfill_legal_query_ip_hash --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import re

from sqlalchemy import select

from app.core.security import hash_ip
from app.db.base import SessionLocal, engine
from app.models.legal import LegalQuery

_ALREADY_HASHED = re.compile(r"^[0-9a-f]{40}$")


async def main(dry_run: bool) -> None:
    async with SessionLocal() as db:
        rows = (await db.execute(
            select(LegalQuery).where(LegalQuery.ip_hash.is_not(None))
        )).scalars().all()

        to_fix = [r for r in rows if not _ALREADY_HASHED.match(r.ip_hash)]
        print(f"{len(rows)} row(s) with a non-null ip_hash; "
              f"{len(to_fix)} still look like a raw address, not a hash.")

        if dry_run:
            for r in to_fix:
                print(f"  would hash: {r.id} ({r.ip_hash!r})")
            print("dry run -- no changes written.")
            return

        for r in to_fix:
            r.ip_hash = hash_ip(r.ip_hash)
        await db.commit()
        print(f"hashed {len(to_fix)} row(s).")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing anything.")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
