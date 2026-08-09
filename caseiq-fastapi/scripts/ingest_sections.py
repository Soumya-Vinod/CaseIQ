"""Ingest legal-act PDFs into legal_sections AND compute embeddings in one pass.

Usage:
    python -m scripts.ingest_sections --act BNS
    python -m scripts.ingest_sections --all   # uses the default documents/ layout

Thin CLI only: arg parsing, wiring together the provenance guard, the
act-specific parser, the shared validation gate, and DB upsert+embed. No
parsing or validation logic lives here -- see app/legal_corpus/.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.db.base import SessionLocal, engine
from app.legal_corpus.parsing.registry import PARSERS
from app.legal_corpus.provenance import ProvenanceError, assert_ingestable
from app.legal_corpus.validate import ValidationGateError, enforce_gate, print_report, validate
from app.models.legal import LegalSection
from app.services.embeddings import embedder

DEFAULTS = {
    "BNS": "documents/BNS_2023.pdf",
    "BNSS": "documents/BNSS_2023.pdf",
    "BSA": "documents/BSA_2023.pdf",
    "IPC": "documents/IPC_1860.pdf",
    "CrPC": "documents/CrPC_1973.pdf",
}


async def ingest(act: str, pdf_path: str) -> None:
    assert_ingestable(act, pdf_path)  # raises ProvenanceError if not an Act; see NOTE below
    # re: the manifest entry's content_as_on/source_sha256 -- not yet persisted per-row.

    parser = PARSERS[act]
    report = parser.parse(Path(pdf_path))
    result = validate(act, report)
    print_report(result)
    enforce_gate(result)  # raises ValidationGateError on rejection-rate or coverage failure

    # NOTE: LegalSection has no source_sha256/parser_name/parser_version/content_as_on
    # columns yet (checked app/models/legal.py -- they don't exist). Provenance is fully
    # tracked in documents/provenance.json (manifest_entry, unused below) and in this
    # ingestion run's printed report, but is NOT yet persisted per-row in the DB. Adding
    # those columns is still open -- it's M1/B4 ("provenance columns") but is schema work
    # this session hasn't done; needs an Alembic migration before this insert can carry
    # them. Tracking as a gap rather than silently expanding this change into a migration.
    async with SessionLocal() as db:
        for s in result.accepted:
            vector = await embedder.embed(f"{s.section_title or ''}. {s.section_text[:2000]}")
            await asyncio.sleep(0.7)
            stmt = insert(LegalSection).values(
                act=act,
                section_number=s.section_number,
                section_title=s.section_title or "",
                section_text=s.section_text,
                embedding=vector,
            ).on_conflict_do_update(
                index_elements=["act", "section_number"],
                set_={
                    "section_title": s.section_title or "",
                    "section_text": s.section_text,
                    "embedding": vector,
                },
            )
            await db.execute(stmt)
        await db.commit()
    print(f"[{act}] ingested + embedded {len(result.accepted)} sections.")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--act")
    p.add_argument("--pdf")
    p.add_argument("--all", action="store_true")
    args = p.parse_args()
    targets = DEFAULTS if args.all else {args.act: args.pdf or DEFAULTS.get(args.act)}

    exit_code = 0
    for act, pdf in targets.items():
        if not (act and pdf and Path(pdf).exists()):
            print(f"skip {act}: missing pdf {pdf}")
            continue
        try:
            await ingest(act, pdf)
        except ProvenanceError as e:
            print(f"[{act}] BLOCKED (provenance): {e}")
            exit_code = 1
        except ValidationGateError as e:
            print(f"[{act}] BLOCKED (validation gate): {e}")
            exit_code = 1
    await engine.dispose()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
