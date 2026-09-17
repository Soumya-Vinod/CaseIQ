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
    python -m scripts.backfill_legal_query_ip_hash --yes   # skip the confirmation prompt

FIXED 2026-09-12, found only after the fact: the first real run of this
script against production used a SECRET_KEY left over from unrelated local
testing (a shell env var override that never got cleared), hashing all 69
rows with the wrong key -- well-formed 40-hex output, right row count,
looked completely correct, and was completely wrong. Recovered from a
fresh pre-migration backup taken for exactly this reason; see
docs/evaluation.md and docs/disaster-recovery.md for the full incident.
Same principle as backup_dump.sh's pg_dump-version assertion (which has
since caught two real failures of its own): the thing this script depends
on but doesn't control -- here, which SECRET_KEY and which database are
actually active in this shell -- gets checked and shown, not assumed.
Below: a hard block on values that look like a placeholder, plus the
shared write-confirmation gate (scripts.lib.production_guard, skippable
with --yes) every writable script under scripts/ now uses.

FIXED 2026-09-16 (docs/evaluation.md, observability entry): the
host-and-confirmation half of this script's own gate was extracted into
scripts.lib.production_guard after a SECOND, structurally identical
incident two days later -- a different one-off script, hitting
production through a different partially-overridden environment. Only the
SECRET_KEY-placeholder check stays here, since it's specific to what THIS
script depends on (hash_ip's correctness); the target-host confirmation is
now shared, not reimplemented per script.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_ip
from app.db.base import SessionLocal, engine
from app.models.legal import LegalQuery
from scripts.lib.production_guard import confirm_writable_target

_ALREADY_HASHED = re.compile(r"^[0-9a-f]{40}$")

# Substrings no real production SECRET_KEY should ever contain -- if one
# does, this is a placeholder/test value, full stop, no override needed
# because there's no legitimate reason for a real key to match this.
_PLACEHOLDER_MARKERS = ("test", "change-me", "changeme", "example", "placeholder", "dummy", "sample")


def _assert_real_key(skip_prompt: bool) -> None:
    key = settings.SECRET_KEY
    lowered = key.lower()
    for marker in _PLACEHOLDER_MARKERS:
        if marker in lowered:
            print(f"FATAL: SECRET_KEY contains '{marker}' -- this looks like a "
                  f"placeholder/test value, not a real production key. Refusing "
                  f"to write anything. If this really is correct, the key itself "
                  f"is the problem, not this check.", file=sys.stderr)
            sys.exit(1)

    fingerprint = hashlib.sha256(key.encode()).hexdigest()[:12]
    print(f"Using SECRET_KEY fingerprint: {fingerprint} "
          f"(not the key itself -- compare this against a known-good run's "
          f"fingerprint if you have one, to confirm it's the same key)")
    confirm_writable_target("backfill_legal_query_ip_hash", skip_prompt=skip_prompt)


async def main(dry_run: bool, skip_prompt: bool = False) -> None:
    if not dry_run:
        _assert_real_key(skip_prompt)
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
    parser.add_argument("--yes", action="store_true",
                        help="Skip the interactive confirmation prompt (still refuses "
                             "outright if SECRET_KEY looks like a placeholder).")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run, args.yes))
