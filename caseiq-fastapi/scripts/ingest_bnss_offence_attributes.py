"""C1: load BNSS First Schedule offence-attribute rows into the DB.

act='BNS' (not 'BNSS') -- BNSS's First Schedule classifies BNS offences,
same pattern as CrPC classifying IPC (see app/models/offence_attributes.py's
`act` docstring). Idempotent: deletes and re-inserts rows from this source
each run.

Usage: python scripts/ingest_bnss_offence_attributes.py
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parse_bnss_schedule import PARSER_VERSION, PDF_PATH, complete_rows, extract_lines, reconstruct_rows
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

    print(f"ingesting {len(rows)} complete rows (act=BNS, source=BNSS First Schedule, parser={PARSER_VERSION})")

    async with SessionLocal() as db:
        await db.execute(delete(OffenceAttributes).where(OffenceAttributes.source.like("BNSS 2023%")))
        for r in rows:
            db.add(OffenceAttributes(
                act="BNS", section_number=r.section_number,
                offence_description=r.offence_description,
                punishment_text=r.punishment_text,
                cognizable_raw=r.cognizable_raw, cognizable=r.cognizable,
                bailable_raw=r.bailable_raw, bailable=r.bailable,
                compoundable=None, compoundable_with_permission=None, compoundable_by=None,
                triable_by=r.triable_by,
                source=f"BNSS 2023 First Schedule, p.{r.source_page}",
                source_sha256=source_hash, parser_version=PARSER_VERSION,
            ))
        await db.commit()
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
