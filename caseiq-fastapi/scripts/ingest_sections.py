"""Ingest legal-act PDFs into section_versions (Part K's bitemporal source of
truth -- see app/models/corpus.py) and compute embeddings in one pass.

Usage:
    python -m scripts.ingest_sections --act BNS
    python -m scripts.ingest_sections --all   # uses the default documents/ layout
    python -m scripts.ingest_sections --all --resume   # skip unchanged, already-embedded rows

Thin CLI only: arg parsing, wiring together the provenance guard, the
act-specific parser, the shared validation gate, and the bitemporal upsert.
No parsing, validation, or DB-writing logic lives here -- see
app/legal_corpus/ingest.py and app/legal_corpus/.

legal_sections (the old, flat, pre-Part-K table) is intentionally never
written to by this script -- see app/services/retrieval.py's module
docstring for why the cutover removed that path rather than leaving it as a
fallback.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.db.base import SessionLocal, engine
from app.legal_corpus.ingest import ingest_act
from app.legal_corpus.parsing.registry import PARSERS
from app.legal_corpus.provenance import ProvenanceError
from app.legal_corpus.validate import ValidationGateError

DEFAULTS = {
    "BNS": "documents/BNS_2023.pdf",
    "BNSS": "documents/BNSS_2023.pdf",
    "BSA": "documents/BSA_2023.pdf",
    "IPC": "documents/IPC_1860.pdf",
    "CrPC": "documents/CrPC_1973.pdf",
}


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--act")
    p.add_argument("--pdf")
    p.add_argument("--all", action="store_true")
    p.add_argument("--resume", action="store_true",
                    help="skip re-embedding sections whose text is unchanged and "
                         "already embedded (continue an interrupted run)")
    args = p.parse_args()
    targets = DEFAULTS if args.all else {args.act: args.pdf or DEFAULTS.get(args.act)}

    exit_code = 0
    async with SessionLocal() as db:
        for act, pdf in targets.items():
            if not (act and pdf and Path(pdf).exists()):
                print(f"skip {act}: missing pdf {pdf}")
                continue
            try:
                outcome = await ingest_act(db, act, pdf, PARSERS[act], resume=args.resume)
                print(outcome)
            except ProvenanceError as e:
                await db.rollback()  # leave the shared session clean for the next act
                print(f"[{act}] BLOCKED (provenance): {e}")
                exit_code = 1
            except ValidationGateError as e:
                await db.rollback()
                print(f"[{act}] BLOCKED (validation gate): {e}")
                exit_code = 1
    await engine.dispose()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
