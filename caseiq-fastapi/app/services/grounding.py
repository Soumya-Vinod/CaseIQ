"""FOUND (docs/evaluation.md, "confident overview, empty laws_applicable"):
the model can write a confident, unhedged `situation_overview` -- "classified
as dowry death... critical... severe legal implications" -- while
`laws_applicable` stays empty, most often because the retrieved section's
punishment clause sat past the old RAG snippet's fixed 300-char cutoff (see
app.services.retrieval's `smart_snippet` fix, which closes the reproducible
cause structurally). This module is the downstream half: whatever the
retrieval fix doesn't catch -- the residual 28/2155 sections still at risk
after the ceiling, plus genuine no-coverage queries that will always exist
-- must never reach a user as a confident, unqualified conclusion.

Two distinct ungrounded shapes, tracked separately (see GroundingStats):
never cited anything (`laws_applicable` empty from generation itself) vs.
cited something that C5 (citation_verification.verify_citations) stripped
down to nothing. Both mean the same thing downstream -- nothing survived
verification, so severity/severity_reason are suppressed (a "Critical"
badge is the loudest, least-qualified claim on the screen) and
confidence_score is reset to 0 (it was computed from retrieval_strength
alone, before this response is known to have used none of it).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.grounding_stats import GroundingStats
from app.services.citation_verification import NOTE_CITATIONS_STRIPPED, NOTE_NO_GROUNDED_CITATIONS


async def apply_grounding_check(
    db: AsyncSession, structured_data: dict, conversational_summary: str, confidence_score: float,
    *, had_laws: bool,
) -> tuple[dict, str, float, bool]:
    """Call AFTER verify_citations has run. `had_laws` is whatever
    `bool(structured_data.get("laws_applicable"))` was BEFORE that call --
    the caller must capture it first, since this function only sees the
    post-verification state.

    Returns `(structured_data, conversational_summary, confidence_score,
    citations_grounded)` -- structured_data has severity/severity_reason
    popped and conversational_summary has exactly one deterministic note
    appended when nothing survived; both pass through unchanged when
    grounded. Also records the standing prevalence counters.
    """
    has_grounding = bool(structured_data.get("laws_applicable"))
    if had_laws and not has_grounding:
        conversational_summary += NOTE_CITATIONS_STRIPPED
    elif not had_laws:
        # had_laws already False means there was nothing for verify_citations
        # to strip -- NOTE_CITATIONS_STRIPPED's own wording ("the sections
        # the model initially named could not be confirmed") would
        # misdescribe this case, so a distinct, accurate note fires instead.
        conversational_summary += NOTE_NO_GROUNDED_CITATIONS

    if not has_grounding:
        structured_data = dict(structured_data)
        structured_data.pop("severity", None)
        structured_data.pop("severity_reason", None)
        confidence_score = 0.0
        logger.warning(
            "response_ungrounded_overview",
            reason="stripped_to_zero" if had_laws else "never_cited",
            situation_overview=structured_data.get("situation_overview"),
        )

    await _record_stats(
        db, never_cited=not had_laws and not has_grounding,
        stripped_to_zero=had_laws and not has_grounding,
    )
    return structured_data, conversational_summary, confidence_score, has_grounding


async def _record_stats(db: AsyncSession, *, never_cited: bool, stripped_to_zero: bool) -> None:
    """One call per real (non-abstained, non-incident-date-prompt)
    generation, always -- unlike C5's stats (which skip when there was
    nothing to verify at all), `responses_total` must count every real
    generation so it's a meaningful denominator for the two ungrounded
    counters. `never_cited` and `stripped_to_zero` are mutually exclusive;
    both False means this response was grounded.
    """
    row = (await db.execute(select(GroundingStats).limit(1))).scalar_one_or_none()
    if row is None:
        row = GroundingStats(
            responses_total=0, responses_ungrounded_never_cited=0,
            responses_ungrounded_stripped_to_zero=0, responses_grounded=0,
        )
        db.add(row)
        await db.flush()
    row.responses_total += 1
    if never_cited:
        row.responses_ungrounded_never_cited += 1
    elif stripped_to_zero:
        row.responses_ungrounded_stripped_to_zero += 1
    else:
        row.responses_grounded += 1
