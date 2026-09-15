"""Deterministic punishment-claim verification -- no LLM, no judgement
call. Closes the gap the answer-fidelity battery's own IPC 408/409 finding
named directly (docs/evaluation.md): C5 (citation_verification.py) checks
whether a CITATION exists and was retrieved, never whether a PUNISHMENT
CLAIM attached to it is actually true of that section's text. Free-text
`offence` matching was why 408/409 was never caught automatically -- this
requires `punishments[]` entries to carry their own (act, section) key,
the same shape `laws_applicable[]` already uses, so there's something
reliable to look the real text up by.

Uses app.legal_corpus.parsing.punishment_clause for both sides: the
statute's own text (extract_punishment_clauses, against the FULL
section_text, never a snippet) and the model's own claim string
(extract_claim_terms). A claim is GROUNDED if it's consistent with AT
LEAST ONE extracted statute clause (a section can carry several, see that
module's own docstring), MISMATCH if it disagrees with every one extracted,
and UNVERIFIABLE if either side couldn't be parsed at all.

CRITICAL, the one rule this module must never violate: only a genuine
MISMATCH gets suppressed. UNVERIFIABLE is never treated as, logged as, or
counted as a mismatch -- the corpus-completeness audit (docs/evaluation.md)
found the extraction rate genuinely tops out well under 100% (cross-
referential and purely procedural sections correctly have no fixed figure
to extract at all), and silently dropping every punishment line for those
would suppress real, useful, correct answers for no safety gain -- the
exact vacuous-pass shape this project keeps finding in other layers, just
inverted: instead of a check that silently passes what it should catch,
a check that silently drops what it never should have touched.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.legal_corpus.parsing.punishment_clause import (
    claim_consistent_with_clause,
    extract_claim_terms,
    extract_punishment_clauses,
)
from app.models.corpus import Act, SectionVersion
from app.models.punishment_stats import PunishmentVerificationStats
from app.services.citation_verification import normalize_act


async def _fetch_section_text(db: AsyncSession, act_code: str, section: str, as_of: date) -> str | None:
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


async def verify_punishments(
    db: AsyncSession, structured_data: dict, as_of: date,
) -> tuple[dict, dict]:
    """Returns (possibly-modified structured_data, counters this call
    observed -- caller persists them). Mutates a shallow copy, never the
    caller's own dict -- same contract as citation_verification.verify_citations.
    """
    punishments = structured_data.get("punishments")
    counters = {"total": 0, "suppressed_mismatch": 0, "unverifiable": 0, "grounded": 0}
    if not isinstance(punishments, list) or not punishments:
        return structured_data, counters

    kept: list[dict] = []
    for entry in punishments:
        if not isinstance(entry, dict):
            continue
        counters["total"] += 1
        act = normalize_act(entry.get("act", ""))
        section = str(entry.get("section", "")).strip()
        claim_text = entry.get("imprisonment", "")

        # No (act, section) key at all -- can't look anything up. NOT a
        # citation-existence question (C5 already owns that, on
        # laws_applicable) -- just nothing this layer can check, so it
        # abstains rather than either blocking or fabricating a verdict.
        if not act or not section:
            counters["unverifiable"] += 1
            kept.append(entry)
            continue

        section_text = await _fetch_section_text(db, act, section, as_of)
        if section_text is None:
            counters["unverifiable"] += 1
            kept.append(entry)
            continue

        statute_clauses = extract_punishment_clauses(section_text)
        claim = extract_claim_terms(claim_text) if isinstance(claim_text, str) else None

        if not statute_clauses or claim is None:
            counters["unverifiable"] += 1
            kept.append(entry)
            continue

        if any(claim_consistent_with_clause(claim, sc) for sc in statute_clauses):
            counters["grounded"] += 1
            kept.append(entry)
            continue

        # A genuine mismatch: the statute parsed, the claim parsed, and
        # they disagree. This is the ONLY branch that suppresses.
        counters["suppressed_mismatch"] += 1
        logger.warning(
            "punishment_claim_suppressed_mismatch",
            act=act, section=section, offence=entry.get("offence"),
            claimed_imprisonment=claim_text,
            extracted_statute_figures=[
                {"max_years": sc.max_years, "min_years": sc.min_years,
                 "max_months": sc.max_months, "min_months": sc.min_months,
                 "life": sc.life, "death": sc.death, "source_span": sc.source_span}
                for sc in statute_clauses
            ],
        )

    new_data = dict(structured_data)
    new_data["punishments"] = kept
    return new_data, counters


async def record_stats(db: AsyncSession, counters: dict) -> None:
    if counters["total"] == 0:
        return
    row = (await db.execute(select(PunishmentVerificationStats).limit(1))).scalar_one_or_none()
    if row is None:
        row = PunishmentVerificationStats(
            punishments_total=0, punishments_suppressed_mismatch=0,
            punishments_unverifiable=0, punishments_grounded=0,
        )
        db.add(row)
        await db.flush()
    row.punishments_total += counters["total"]
    row.punishments_suppressed_mismatch += counters["suppressed_mismatch"]
    row.punishments_unverifiable += counters["unverifiable"]
    row.punishments_grounded += counters["grounded"]
