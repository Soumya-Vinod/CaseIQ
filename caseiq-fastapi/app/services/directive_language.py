"""Directive-language detection -- DETECTION ONLY, no enforcement (docs/
evaluation.md, directive-language entry). "You should file an FIR" has
moved from explaining what the law says to advising a specific person on
what to do -- a real distinction this product's whole premise rests on
(legal AWARENESS, not legal advice), and nothing currently checks for it
anywhere in this codebase.

FRAMING, stated precisely because it was gotten wrong once already: this is
NOT "porting Django's ethics filter." Checked directly against the retired
Django backend before building anything here: `EthicsRule` (the model
carrying "you should"/"I recommend"/"hire a lawyer" block-phrase patterns)
was a real database model, seeded with 7 real rows, registered in Django
admin for a human to view -- and never once queried by any view, service,
or middleware in that whole codebase. The only thing that ran on every
response there (`apps/ethics/filter.py`'s `EthicsFilter.filter_response`)
only unwrapped JSON, logged (never blocked) a HARM-facilitation phrase hit
(a different list entirely, already superseded here by app.services.safety's
input-side screening), and deduplicated a disclaimer emoji. Directive-
language screening was designed there and never built. This module is that
build, not a restoration -- the 7 patterns below are seeded from Django's
own EthicsRule rows as a starting design, not copied working code, because
there was no working code to copy.

WHY DETECTION ONLY, STAGED THE SAME WAY grounding.py AND punishment_
verification.py WERE: those two modules earned their eventual enforcement
behaviour by shipping detection with a stats counter FIRST, against real
traffic, before deciding what happens on a hit. Django's own history is a
warning here, not a template: it shipped the DATA (rules, seeded, visible
in admin) with no consumer at all, which is its own vacuous-pass shape --
looking like a real safety feature while doing nothing. Detection with a
real counter, wired into the real request path, is a stronger starting
position than Django ever reached, even before any enforcement decision is
made.

SCOPED TO FREE-TEXT PROSE ONLY -- checked directly against a real
production response before deciding this, not assumed: `immediate_steps[].
action` is DELIBERATELY imperative by field design ("Consult a qualified
criminal defence lawyer", "Preserve all relevant documents and evidence")
-- the whole POINT of that field is to tell the user what to do next. A
blanket phrase filter across the whole response would flag exactly the
content that's supposed to be directive, the same shape as the original
Django EthicsRule list would have been risking if it had ever actually run
unscoped. Checked here: `conversational_summary`, `structured_data.
situation_overview`, and every `structured_data.laws_applicable[].
why_applies` -- the fields whose whole job is to describe what the law
says, not to tell the reader what to do. `immediate_steps` and
`dos_and_donts` are explicitly NEVER scanned.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.directive_language_stats import DirectiveLanguageStats

# Seeded from the retired Django backend's EthicsRule rows (apps/knowledge_
# base/management/commands/seed_disclaimers.py's seed_ethics_rules()) as a
# starting design -- these are the 7 patterns that database held, never the
# product of this project's own measurement (there is none yet; that's what
# this detector exists to produce). Word-boundary, case-insensitive, same
# style as app.services.safety's own _DENY_PATTERNS.
_DIRECTIVE_PATTERNS = [
    (r"\byou should\b", "you should"),
    (r"\byou must\b", "you must"),
    (r"\bi recommend\b", "i recommend"),
    (r"\bi advise\b", "i advise"),
    (r"\bfile a case\b", "file a case"),
    (r"\bhire a lawyer\b", "hire a lawyer"),
    (r"\btake legal action\b", "take legal action"),
]
_DIRECTIVE_RE = [(re.compile(p, re.IGNORECASE), label) for p, label in _DIRECTIVE_PATTERNS]


def _scan_field(field_name: str, text: str | None) -> list[dict]:
    if not text:
        return []
    hits = []
    for rx, label in _DIRECTIVE_RE:
        if rx.search(text):
            hits.append({"field": field_name, "phrase": label})
    return hits


def detect_directive_language(structured_data: dict, conversational_summary: str) -> list[dict]:
    """Returns every hit found -- empty list if none. NEVER modifies
    structured_data or conversational_summary; this is detection only, per
    instruction. Each hit is {"field": ..., "phrase": ...}; a single field
    can contribute more than one hit if it matches more than one pattern.
    """
    hits = _scan_field("conversational_summary", conversational_summary)
    hits += _scan_field("situation_overview", structured_data.get("situation_overview"))
    for i, law in enumerate(structured_data.get("laws_applicable") or []):
        if not isinstance(law, dict):
            continue
        hits += _scan_field(f"laws_applicable[{i}].why_applies", law.get("why_applies"))
    return hits


async def record_stats(db: AsyncSession, hits: list[dict]) -> None:
    """One call per real (non-abstained, non-incident-date-prompt)
    generation, always -- responses_total must count every real
    generation so it's a meaningful denominator, matching GroundingStats'
    own convention.
    """
    row = (await db.execute(select(DirectiveLanguageStats).limit(1))).scalar_one_or_none()
    if row is None:
        row = DirectiveLanguageStats(responses_total=0, responses_flagged=0, hits_total=0)
        db.add(row)
        await db.flush()
    row.responses_total += 1
    if hits:
        row.responses_flagged += 1
        row.hits_total += len(hits)
        # Logged, not just counted -- a human needs to see the actual
        # phrase and field to judge whether this is a real problem or a
        # false positive, the same reasoning behind every other suppression
        # log in this codebase (punishment_claim_suppressed_mismatch,
        # response_ungrounded_overview).
        logger.warning("directive_language_detected", hits=hits)
