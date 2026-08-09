"""Ingest legal-act PDFs into legal_sections AND compute embeddings in one pass.

Usage:
    python -m scripts.ingest_sections --act BNS --pdf documents/BNS_2023.pdf
    python -m scripts.ingest_sections --all   # uses the default documents/ layout

This unifies the original two-step (Django ingest_pdfs command + the never-run
embedding step) so every ingested section is immediately vector-searchable.
"""
from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

import pdfplumber
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.base import SessionLocal, engine
from app.models.legal import LegalSection
from app.services.embeddings import embedder
from scripts.provenance import ProvenanceError, assert_ingestable

DEFAULTS = {
    "BNS": "documents/BNS_2023.pdf",
    "BNSS": "documents/BNSS_2023.pdf",
    "BSA": "documents/BSA_2023.pdf",
    "IPC": "documents/IPC_1860.pdf",
    "CrPC": "documents/CrPC_1973.pdf",
}
_SECTION_RE = re.compile(r"(?:^|\n)\s*(\d{1,3}[A-Z]?)\.\s+(?:\(1\)\s+)?([^\n]{5,200})", re.MULTILINE)


def parse_pdf(path: str) -> list[dict]:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    matches = list(_SECTION_RE.finditer(text))
    out: list[dict] = []
    for i, m in enumerate(matches):
        start, end = m.start(), matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = re.sub(r"\s+", " ", text[start:end]).strip()[:5000]
        if len(body) > 20:
            out.append({"section_number": m.group(1).strip(),
                        "section_title": re.sub(r"\s+", " ", m.group(2)).strip()[:500],
                        "section_text": body})
    return out


async def ingest(act: str, pdf_path: str) -> None:
    assert_ingestable(act, pdf_path)  # raises ProvenanceError for anything not a notified Act
    sections = parse_pdf(pdf_path)
    print(f"[{act}] parsed {len(sections)} sections from {pdf_path}")
    async with SessionLocal() as db:
        for s in sections:
            vector = await embedder.embed(f"{s['section_title']}. {s['section_text'][:2000]}")
            await asyncio.sleep(0.7)
            stmt = insert(LegalSection).values(
                act=act, section_number=s["section_number"], section_title=s["section_title"],
                section_text=s["section_text"], embedding=vector,
            ).on_conflict_do_update(
                index_elements=["act", "section_number"],
                set_={"section_title": s["section_title"], "section_text": s["section_text"],
                      "embedding": vector},
            )
            await db.execute(stmt)
        await db.commit()
    print(f"[{act}] ingested + embedded.")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--act")
    p.add_argument("--pdf")
    p.add_argument("--all", action="store_true")
    args = p.parse_args()
    targets = DEFAULTS if args.all else {args.act: args.pdf}
    for act, pdf in targets.items():
        if act and pdf and Path(pdf).exists():
            try:
                await ingest(act, pdf)
            except ProvenanceError as e:
                print(f"[{act}] BLOCKED: {e}")
        else:
            print(f"skip {act}: missing pdf {pdf}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
