"""Bitemporal ingestion: parse -> validate -> upsert into section_versions.
scripts/ingest_sections.py stays a thin CLI; this is where the DB-writing
logic lives, same "thin CLI, real logic in app/" split M1 established.

Upsert rule, per section:
  - no current version (valid_to IS NULL) exists for (act, section_number)
    -> insert version_no=1.
  - a current version exists and its valid_from equals the newly-resolved
    valid_from -> this is a re-parse of the SAME real-world validity window
    (e.g. a parser bug fix), not a new legal reality. Update the existing
    row's text/embedding IN PLACE rather than forking a version -- forking
    would misrepresent "we read it better" as "the law changed on this date".
  - a current version exists and valid_from has moved forward -> a genuine
    new version: close the old one (valid_to = new valid_from) and insert
    version_no+1.
"""
from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.legal_corpus.acts_seed import ensure_act
from app.legal_corpus.parsing.base import RawSection
from app.legal_corpus.provenance import assert_ingestable, load_manifest
from app.legal_corpus.validate import ValidationResult, enforce_gate, print_report, validate
from app.legal_corpus.versioning import resolve_valid_from
from app.models.corpus import SectionVersion
from app.services.embeddings import embedder


class IngestOutcome:
    def __init__(self, act: str) -> None:
        self.act = act
        self.inserted = 0
        self.updated_in_place = 0
        self.new_versions = 0
        self.skipped_resume = 0

    def __str__(self) -> str:
        return (f"[{self.act}] inserted={self.inserted} updated_in_place={self.updated_in_place} "
                f"new_versions={self.new_versions} skipped(resume)={self.skipped_resume}")


async def ingest_act(db: AsyncSession, act_code: str, pdf_path: str, parser, resume: bool = False) -> IngestOutcome:
    """Runs the full pipeline for one act against an already-open session.
    Raises ProvenanceError / ValidationGateError -- caller decides how to
    report/exit; nothing here swallows those.
    """
    assert_ingestable(act_code, pdf_path)
    manifest_entry = load_manifest()[act_code]
    content_as_on_str = (manifest_entry.get("content_as_on") or {}).get("value")
    content_as_on = date.fromisoformat(content_as_on_str) if content_as_on_str else None
    source_url = (manifest_entry.get("source_url") or {}).get("value")
    source_sha256 = manifest_entry.get("source_sha256")

    from pathlib import Path

    report = parser.parse(Path(pdf_path))
    result: ValidationResult = validate(act_code, report)
    print_report(result)
    enforce_gate(result)  # raises ValidationGateError

    act = await ensure_act(db, act_code)
    valid_from = resolve_valid_from(content_as_on, act.commenced_on)

    outcome = IngestOutcome(act_code)

    current_rows = (await db.execute(
        select(SectionVersion).where(
            SectionVersion.act_id == act.id, SectionVersion.valid_to.is_(None)
        )
    )).scalars().all()
    current_by_number = {r.section_number: r for r in current_rows}

    for s in result.accepted:
        current = current_by_number.get(s.section_number)

        if current is None:
            await _insert_new(db, act.id, s, version_no=1, valid_from=valid_from,
                               source_url=source_url, source_sha256=source_sha256,
                               content_as_on=content_as_on, parser=parser, resume=resume,
                               outcome=outcome)
            continue

        if current.valid_from == valid_from:
            if resume and current.section_text == s.section_text and current.embedding is not None:
                outcome.skipped_resume += 1
                continue
            current.marginal_note = s.section_title or current.marginal_note
            current.section_text = s.section_text
            current.is_repealed = s.is_repealed
            current.source_url = source_url
            current.source_sha256 = source_sha256
            current.content_as_on = content_as_on
            current.parser_name = parser.name
            current.parser_version = parser.version
            current.embedding = await embedder.embed(f"{current.marginal_note}. {s.section_text[:2000]}")
            await asyncio.sleep(0.7)
            outcome.updated_in_place += 1
        else:
            # genuine new version -- valid_from advanced, close the old one
            current.valid_to = valid_from
            await _insert_new(db, act.id, s, version_no=current.version_no + 1, valid_from=valid_from,
                               source_url=source_url, source_sha256=source_sha256,
                               content_as_on=content_as_on, parser=parser, resume=False,
                               outcome=outcome)
            outcome.new_versions += 1

    await db.commit()
    return outcome


async def _insert_new(db, act_id, s: RawSection, *, version_no: int, valid_from, source_url,
                       source_sha256, content_as_on, parser, resume: bool, outcome: IngestOutcome) -> None:
    vector = await embedder.embed(f"{s.section_title or ''}. {s.section_text[:2000]}")
    await asyncio.sleep(0.7)
    db.add(SectionVersion(
        act_id=act_id, section_number=s.section_number, version_no=version_no,
        marginal_note=s.section_title or "", section_text=s.section_text,
        is_repealed=s.is_repealed, valid_from=valid_from, valid_to=None,
        source_url=source_url, source_sha256=source_sha256, content_as_on=content_as_on,
        parser_name=parser.name, parser_version=parser.version, embedding=vector,
    ))
    outcome.inserted += 1
