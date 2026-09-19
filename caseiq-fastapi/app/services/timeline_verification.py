"""Deterministic legal-timeline verification -- no LLM, no judgement call.
Same shape as app.services.punishment_verification (read that module first;
this one mirrors its structure deliberately), built for the scoping this
project did before writing any of it (docs/evaluation.md, 2026-09-20): a
procedural timeline is the feature most likely to fabricate a confident,
plausible, WRONG deadline with no visible tell (unlike a wrong citation,
which a reader could at least look up) -- the scoping's accepted answer was
"only emit a stage that cites a real section with an explicit time limit,"
never a full generic procedural walkthrough.

ONE DELIBERATE, NAMED DIFFERENCE from punishment_verification's own policy,
stated here because getting this backwards would silently reopen the exact
fabrication risk this feature was scoped to close: punishment_verification
KEEPS an unverifiable claim (no statute figure to check against, or an
unparseable claim string) on the reasoning that most of an answer is still
useful even with one auxiliary field unconfirmed. This module DROPS an
unverifiable stage instead. The two features have different premises --
punishment claims ride alongside an already-grounded citation as one field
among several; a timeline stage's ENTIRE reason to exist is the time limit
it claims. A stage with nothing behind it just IS the fabrication risk this
was built to prevent, not a stage worth keeping with a caveat.

A SECOND, NAMED, ACCEPTED LIMIT, not fixed here -- see
app.legal_corpus.parsing.timeline_clause's own module docstring for the
mechanism: this checks that a claimed value+unit (e.g. "90 days") is a REAL
figure extracted from the cited section's text. It does NOT check that the
figure is paired with the correct QUALIFYING CONDITION (e.g. that "90 days"
is claimed specifically for an offence carrying death/life/10+ years, not
for "any other offence," BNSS 187(3)'s own two-branch case) -- extraction
finds every value+unit pair stated anywhere in the section, not which
offence category each one attaches to. A stage claiming the right number for
the wrong condition passes this check. Same shape as the IPC 408/409 finding
punishment_verification itself was built to close (checks WHICH section was
cited, never WHAT was claimed about it) -- named directly rather than
discovered again the same way.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.legal_corpus.parsing.timeline_clause import (
    claim_matches_clause,
    extract_claim_time_limit,
    extract_time_limit_clauses,
)
from app.models.corpus import Act, SectionVersion
from app.models.timeline_stats import TimelineVerificationStats
from app.services.citation_verification import normalize_act


async def _fetch_section_text(db: AsyncSession, act_code: str, section: str, as_of: date) -> str | None:
    # Identical query shape to punishment_verification._fetch_section_text
    # -- full section_text, never a snippet, same reasoning: a snippet is
    # sized for what the GENERATOR needs to see, not for what a verifier
    # needs to check against.
    stmt = (
        select(SectionVersion.section_text)
        .join(Act, SectionVersion.act_id == Act.id)
        .where(
            Act.act_code == act_code, SectionVersion.section_number == section,
            SectionVersion.valid_from <= as_of,
            (SectionVersion.valid_to.is_(None)) | (SectionVersion.valid_to > as_of),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def verify_timeline_stages(
    db: AsyncSession, stages: list[dict], as_of: date,
) -> tuple[list[dict], dict]:
    """`stages` is the LLM's own proposed list, each a dict expected to carry
    `act`, `section`, and `time_limit_claim` (free text, e.g. "within 24
    hours" or "90 days"). Returns (kept_stages, counters this call
    observed -- caller persists them). Only GROUNDED stages survive; see
    this module's own docstring for why that's a wider drop policy than
    punishment_verification's.
    """
    counters = {"total": 0, "grounded": 0, "dropped_unverifiable": 0, "dropped_mismatch": 0}
    if not stages:
        return [], counters

    kept: list[dict] = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        counters["total"] += 1
        act = normalize_act(stage.get("act", ""))
        section = str(stage.get("section", "")).strip()
        claim_text = stage.get("time_limit_claim", "")

        if not act or not section:
            counters["dropped_unverifiable"] += 1
            continue

        section_text = await _fetch_section_text(db, act, section, as_of)
        if section_text is None:
            counters["dropped_unverifiable"] += 1
            continue

        statute_clauses = extract_time_limit_clauses(section_text)
        claim = extract_claim_time_limit(claim_text) if isinstance(claim_text, str) else None

        if not statute_clauses or claim is None:
            counters["dropped_unverifiable"] += 1
            logger.info(
                "timeline_stage_dropped_unverifiable", act=act, section=section,
                claim=claim_text, statute_clause_count=len(statute_clauses),
            )
            continue

        if any(claim_matches_clause(claim, sc) for sc in statute_clauses):
            counters["grounded"] += 1
            kept.append(stage)
            continue

        counters["dropped_mismatch"] += 1
        logger.warning(
            "timeline_stage_dropped_mismatch",
            act=act, section=section, claimed=claim_text,
            extracted_statute_values=[(sc.value, sc.unit) for sc in statute_clauses],
        )

    return kept, counters


async def record_stats(db: AsyncSession, counters: dict) -> None:
    if counters["total"] == 0:
        return
    row = (await db.execute(select(TimelineVerificationStats).limit(1))).scalar_one_or_none()
    if row is None:
        row = TimelineVerificationStats(
            stages_proposed_total=0, stages_grounded=0,
            stages_dropped_unverifiable=0, stages_dropped_mismatch=0,
        )
        db.add(row)
        await db.flush()
    row.stages_proposed_total += counters["total"]
    row.stages_grounded += counters["grounded"]
    row.stages_dropped_unverifiable += counters["dropped_unverifiable"]
    row.stages_dropped_mismatch += counters["dropped_mismatch"]
