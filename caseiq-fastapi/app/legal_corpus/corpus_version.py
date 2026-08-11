"""K4/K6: create a CorpusVersion snapshot marker. Deliberately NOT created
implicitly per-query (see app/api/v1/legal.py's process_query) -- a snapshot
is a deliberate act tied to a real change (a full ingest run, or a single
K5 approval), not a side effect of read traffic. Before this module, nothing
in the codebase ever called CorpusVersion() at all: the table and the K6
admin endpoint that lists it (GET /admin/corpus/versions) existed, but were
always empty -- found 2026-08-11 while finishing K7 (query_response.
corpus_version_id was always None for the same reason).
"""
from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corpus import CorpusVersion, SectionVersion


async def compute_checksum(db: AsyncSession) -> tuple[str, int]:
    """Deterministic checksum over every CURRENTLY in-force section
    (valid_to IS NULL): sha256 of act_id:section_number:version_no:
    sha256(section_text), one line per row, sorted for order-independence.
    Two corpora with identical live content hash identically regardless of
    ingestion order; any text/version change anywhere changes the checksum.
    """
    rows = (await db.execute(
        select(SectionVersion.act_id, SectionVersion.section_number,
               SectionVersion.version_no, SectionVersion.section_text)
        .where(SectionVersion.valid_to.is_(None))
    )).all()
    lines = sorted(
        f"{act_id}:{section_number}:{version_no}:"
        f"{hashlib.sha256(section_text.encode()).hexdigest()}"
        for act_id, section_number, version_no, section_text in rows
    )
    digest = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    return digest, len(rows)


async def create_corpus_version(db: AsyncSession, label: str, notes: str = "") -> CorpusVersion:
    """Snapshots the corpus's current state. Caller commits (this only
    flushes) -- same convention as CorpusStagingChange.stage_change()."""
    checksum, section_count = await compute_checksum(db)
    version = CorpusVersion(label=label, notes=notes, section_count=section_count, checksum=checksum)
    db.add(version)
    await db.flush()
    return version
