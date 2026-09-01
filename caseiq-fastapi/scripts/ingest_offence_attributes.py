"""C1: load CrPC First Schedule offence-attribute rows into the DB.

Only "complete" parser rows are ingested (see parse_crpc_schedule.complete_rows)
-- deliberately partial coverage (221/381 sections at time of writing, see
docs/evaluation.md), stated honestly rather than padded with fragments.
Idempotent: deletes and re-inserts this act's rows each run, so re-running
after a parser fix is safe.

Usage: python scripts/ingest_offence_attributes.py
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parse_crpc_schedule import PARSER_VERSION, PDF_PATH, complete_rows, extract_lines, reconstruct_rows
from sqlalchemy import delete

from app.db.base import SessionLocal
from app.models.offence_attributes import OffenceAttributes


async def main() -> None:
    pdf_bytes = Path(PDF_PATH).read_bytes()
    source_hash = hashlib.sha256(pdf_bytes).hexdigest()

    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = complete_rows(rows)

    # act='IPC', not 'CrPC': the First Schedule classifies IPC offences by
    # IPC section number -- CrPC itself is procedure. See
    # app/models/offence_attributes.py's `act` docstring.
    print(f"ingesting {len(rows)} complete rows (act=IPC, source=CrPC First Schedule, parser={PARSER_VERSION})")

    async with SessionLocal() as db:
        # FOUND running this twice during development: an earlier run (before
        # the act='IPC' fix, see offence_attributes.py's `act` docstring)
        # left 265 stale rows with act='CrPC' that this delete's original
        # act='IPC' filter never matched, so re-running silently doubled the
        # table instead of replacing it (500 rows, not 250; 498A resurfaced
        # from the stale batch even though the current parser correctly
        # excludes it). This table has exactly one writer (this script), so
        # deleting by source prefix regardless of act is the correct, safe
        # "replace everything this script has ever written" semantics.
        await db.execute(delete(OffenceAttributes).where(OffenceAttributes.source.like("CrPC 1973%")))
        for r in rows:
            db.add(OffenceAttributes(
                act="IPC", section_number=r.section_number,
                offence_description=r.offence_description,
                punishment_text=r.punishment_text,
                cognizable_raw=r.cognizable_raw, cognizable=r.cognizable,
                bailable_raw=r.bailable_raw, bailable=r.bailable,
                compoundable=None, compoundable_with_permission=None, compoundable_by=None,
                triable_by=r.triable_by,
                source=f"CrPC 1973 First Schedule, p.{r.source_page}",
                source_sha256=source_hash, parser_version=PARSER_VERSION,
            ))
        await db.commit()
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
