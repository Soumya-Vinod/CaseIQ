"""K5: change-detection pipeline. Scope decision (2026-08-09): build the
review-queue workflow fully (staging -> diff -> human approval -> promote --
see app.models.corpus.CorpusStagingChange and app.api.v1.admin_corpus), but
STUB the actual source polling. Scraping India Code, e-Gazette, and PRS
Legislative Research each requires verifying that site's real structure
(stable selectors/endpoints, rate limits, terms of use) -- none of which has
been done. Building a scraper against an unverified guess at their HTML
would be worse than not having one: silent breakage nobody notices, or
technically-against-terms scraping nobody reviewed.

poll_sources() is the pluggable seam a real implementation replaces. Nothing
downstream cares HOW a StagedChange candidate was produced -- stage_change()
below is the same path a real scraper and a manually-supplied correction
would both call.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.legal_corpus.acts_seed import ensure_act
from app.models.corpus import CorpusStagingChange, SectionVersion


@dataclass(frozen=True)
class SourceCandidate:
    """What a source poller (real or manual) proposes as new text for a
    section. Deliberately doesn't assume WHERE it came from beyond a URL.
    """
    act_code: str
    section_number: str
    text: str
    source_url: str


async def poll_sources() -> list[SourceCandidate]:
    """STUB -- always returns []. Replace with real polling of India Code /
    e-Gazette / PRS once each source's structure is verified. Kept as an
    async function now so callers (the arq cron job below) don't need to
    change shape when a real implementation lands.
    """
    return []


async def stage_change(db: AsyncSession, candidate: SourceCandidate) -> CorpusStagingChange | None:
    """Diffs `candidate` against the current in-force version and writes a
    CorpusStagingChange row if the text actually differs. Returns None (and
    writes nothing) if the text is unchanged from what's already live --
    checksum-and-compare, no change -> exit, per K5's spec. Never touches
    section_versions directly; only app.api.v1.admin_corpus's approve()
    (human-gated) does that.
    """
    act = await ensure_act(db, candidate.act_code)
    current = (await db.execute(
        select(SectionVersion).where(
            SectionVersion.act_id == act.id, SectionVersion.section_number == candidate.section_number,
            SectionVersion.valid_to.is_(None),
        )
    )).scalar_one_or_none()

    new_hash = hashlib.sha256(candidate.text.encode()).hexdigest()
    if current is not None and hashlib.sha256(current.section_text.encode()).hexdigest() == new_hash:
        return None  # no change -> exit, per K5 spec

    diff_summary = (
        f"current ({len(current.section_text) if current else 0} chars) -> "
        f"staged ({len(candidate.text)} chars)"
    )
    change = CorpusStagingChange(
        act_id=act.id, section_number=candidate.section_number, source_url=candidate.source_url,
        source_sha256=new_hash, staged_text=candidate.text, diff_summary=diff_summary, status="pending",
    )
    db.add(change)
    await db.flush()
    return change


async def run_change_detection(db: AsyncSession) -> int:
    """The arq-scheduled entrypoint (see app.tasks.worker.check_for_updates).
    Currently a no-op end to end, since poll_sources() returns []. Returns
    the number of new staging rows written.
    """
    staged = 0
    for candidate in await poll_sources():
        change = await stage_change(db, candidate)
        if change is not None:
            staged += 1
    await db.commit()
    return staged
