"""C-lookup: "can I be arrested for this?" -- pure DB search over
offence_attributes, never an LLM, never a guess. Two search modes (by
offence name, by section number), one shared title-resolution step.

**The base-section-number join fix this whole feature rests on**: many
offence_attributes rows carry a sub-clause suffix (e.g. "80(2)") that
doesn't exist as its own row in section_versions, which stores whole
sections only. A naive exact-match join therefore missed 220 of 647 rows
(34%) -- confirmed directly, and confirmed every single one of those 220
had exactly this kind of suffix, none were a genuine data gap. Stripping
the suffix before joining brings that to 647/647 (100%), verified against
the live corpus before this was built, not assumed. See docs/evaluation.md
for the full investigation.

**Search text vs. display text, kept deliberately separate**: name search
matches against BOTH SectionVersion.marginal_note (the clean statutory
heading) and OffenceAttributes.offence_description (raw First Schedule
text -- real, but frequently garbled by the same column-bleed artifact C1
documented; a keyword like "dowry" sometimes survives there and nowhere
else). Matching on the garbled text is fine; showing it is not -- every
result's `title` comes from the marginal_note join, never from
offence_description, regardless of which field the match came from.
"""
from __future__ import annotations

import re

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corpus import Act, SectionVersion
from app.models.offence_attributes import OffenceAttributes

# offence_attributes.act is always "IPC" or "BNS" -- never CrPC/BNSS/BSA,
# see that model's own docstring (the classified act, not the schedule it
# was parsed from). A section-number search therefore only ever needs to
# check these two.
_CLASSIFIED_ACTS = ("IPC", "BNS")

_SECTION_NUMBER_RE = re.compile(
    r"^(?:ipc|bns)?\s*([0-9]{1,4}[a-z]{0,2}(?:\(\w+\))?)$", re.IGNORECASE,
)


def _base_number(section_number: str) -> str:
    return re.sub(r"\(\w+\)$", "", section_number)


def detect_mode(q: str) -> tuple[str, str | None]:
    """Returns ("section_number", <bare number>) if `q` looks like a
    section number (optionally act-prefixed, e.g. "IPC 302", "80(2)"),
    else ("name", None). A heuristic, not a classifier -- same accepted
    tradeoff as every other keyword-based dispatch in this app (see
    is_civil_scope_mismatch, implies_past_incident): a name that happens to
    be all digits would misfire, and none exist in this corpus's offences."""
    m = _SECTION_NUMBER_RE.match(q.strip())
    return ("section_number", m.group(1).upper()) if m else ("name", None)


def _row_to_dict(act: str, section_number: str, title: str, title_source: str,
                  *, cognizable: bool | None = None, cognizable_raw: str = "",
                  bailable: bool | None = None, bailable_raw: str = "",
                  compoundable: bool | None = None,
                  compoundable_with_permission: bool | None = None,
                  compoundable_by: str | None = None, triable_by: str = "",
                  source: str = "", has_data: bool = True,
                  section_exists: bool = True) -> dict:
    return {
        "act": act, "section_number": section_number, "title": title,
        "title_source": title_source, "cognizable": cognizable,
        "cognizable_raw": cognizable_raw, "bailable": bailable,
        "bailable_raw": bailable_raw, "compoundable": compoundable,
        "compoundable_with_permission": compoundable_with_permission,
        "compoundable_by": compoundable_by, "triable_by": triable_by,
        "source": source, "has_data": has_data, "section_exists": section_exists,
    }


_HEADING_RE_CACHE: dict[str, re.Pattern] = {}


def _heading_from_text(section_number: str, section_text: str) -> str | None:
    """BNS's own marginal_note column is empty for all 358 of its sections
    (confirmed directly, not assumed -- 0/358 non-empty, vs. 563/563 for
    IPC; a real BNS-ingestion gap, out of scope to re-parse here) -- so for
    BNS, the clean heading has to come out of section_text itself. Indian
    statutory text consistently reads "{number}. {heading}.--{body}", but
    a section can be preceded by an un-numbered chapter/group heading in
    the same field (e.g. "Of cheating 318. Cheating.--Whoever..."), so this
    anchors on the section's OWN number marker rather than the start of the
    string. `\\b` before the number keeps "18." from matching inside "318.".
    """
    pattern = _HEADING_RE_CACHE.get(section_number)
    if pattern is None:
        pattern = re.compile(rf"\b{re.escape(section_number)}\.\s*(.+?)(?:—|--)")
        _HEADING_RE_CACHE[section_number] = pattern
    m = pattern.search(section_text)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return None


async def _attach_titles(db: AsyncSession, rows: list[OffenceAttributes]) -> list[dict]:
    if not rows:
        return []
    pairs = {(r.act, _base_number(r.section_number)) for r in rows}
    stmt = (
        select(Act.act_code, SectionVersion.section_number, SectionVersion.marginal_note,
               SectionVersion.section_text)
        .join(Act, SectionVersion.act_id == Act.id)
        .where(or_(*[
            and_(Act.act_code == act, SectionVersion.section_number == base)
            for act, base in pairs
        ]))
    )
    section_by_key = {
        (act, sec): (note, text) for act, sec, note, text in (await db.execute(stmt)).all()
    }
    out = []
    for r in rows:
        key = (r.act, _base_number(r.section_number))
        found = section_by_key.get(key)
        title, title_source = None, None
        if found:
            note, text = found
            if note:
                title, title_source = note, "section_heading"
            else:
                derived = _heading_from_text(key[1], text)
                if derived:
                    title, title_source = derived, "section_heading"
        if title is None:
            # Safety net, not the normal path for either act -- truncated
            # so a genuinely garbled fallback can't blow out the layout.
            title, title_source = r.offence_description[:140], "schedule_description_fallback"
        out.append(_row_to_dict(
            r.act, r.section_number, title, title_source,
            cognizable=r.cognizable, cognizable_raw=r.cognizable_raw,
            bailable=r.bailable, bailable_raw=r.bailable_raw,
            compoundable=r.compoundable,
            compoundable_with_permission=r.compoundable_with_permission,
            compoundable_by=r.compoundable_by, triable_by=r.triable_by, source=r.source,
        ))
    return out


async def search_by_name(db: AsyncSession, q: str, limit: int = 20) -> list[dict]:
    base = func.regexp_replace(OffenceAttributes.section_number, r"\(\w+\)$", "")
    stmt = (
        select(OffenceAttributes)
        .outerjoin(Act, Act.act_code == OffenceAttributes.act)
        .outerjoin(SectionVersion, and_(
            SectionVersion.act_id == Act.id, SectionVersion.section_number == base,
        ))
        .where(or_(
            SectionVersion.marginal_note.ilike(f"%{q}%"),
            OffenceAttributes.offence_description.ilike(f"%{q}%"),
        ))
        .order_by(OffenceAttributes.act, OffenceAttributes.section_number)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return await _attach_titles(db, rows)


async def lookup_by_section(db: AsyncSession, section_number: str) -> list[dict]:
    """Each of the two classified acts gets one of three outcomes for this number -- one or more
    real rows, a real section with no row (the fourth state), or nothing (that act never had this
    section, so it's omitted, not fabricated as a third kind of empty card).

    FIXED (docs/evaluation.md, row-mismatch-transcription entry): "one real row" was `scalar_one_
    or_none()` -- a genuinely conditional section with more than one printed sub-clause (e.g. s.376's
    three graded conditions, s.109's own base/exception pair) has always stored MULTIPLE rows under
    the same section_number, the same contract every hand-transcription pass in this schedule uses.
    `scalar_one_or_none()` raises `MultipleResultsFound` the instant a section has 2+ rows -- a 500,
    not a wrong answer, for any such lookup. Confirmed pre-existing, not introduced by this session's
    own row-mismatch-transcription work (s.376 crashed this same way before today) -- but that work
    just made it far more common: many of the 40 newly-fixed sections are themselves multi-row.
    Fixed by fetching all matching rows and returning each as its own card, the same one-card-per-
    real-row shape `search_by_name()` and the frontend's own `results.map(...)` already assume."""
    results: list[dict] = []
    for act in _CLASSIFIED_ACTS:
        oa_rows = (await db.execute(
            select(OffenceAttributes).where(
                OffenceAttributes.act == act, OffenceAttributes.section_number == section_number,
            )
        )).scalars().all()
        if oa_rows:
            results.extend(await _attach_titles(db, oa_rows))
            continue

        sv_row = (await db.execute(
            select(SectionVersion.marginal_note, SectionVersion.section_text)
            .join(Act, SectionVersion.act_id == Act.id)
            .where(Act.act_code == act, SectionVersion.section_number == section_number)
        )).first()
        if sv_row is not None:
            note, text = sv_row
            # Same fallback chain as _attach_titles -- BNS's marginal_note
            # is empty for every section (see that function's docstring),
            # so the "no data row, but the section is real" card needs the
            # same derived-from-text heading, not a blank title.
            title = note or _heading_from_text(section_number, text) or section_number
            results.append(_row_to_dict(
                act, section_number, title, "section_heading", has_data=False,
            ))
        # else: this act never had this section number -- not a result.
    return results


_BLANKET_COVERAGE_NOTE = (
    "Coverage: BNS is near-complete (398 of 434 sections). IPC/CrPC cognizable/bailable "
    "classification is individually verified against the source law for 398 of 398 "
    "sections the First Schedule covers (100%) -- the remaining known gap is s.501/s.502 "
    "(a real printed table entry not yet addressable under its own section number), so this "
    "search finding nothing may be one of those rather than proof the offence doesn't exist."
)

_PER_SECTION_COVERAGE_NOTE = (
    "This section's cognizable/bailable classification hasn't been independently verified "
    "against the source law yet -- it's one of a known, tracked set of gaps, not a guess "
    "presented as fact. A free legal aid clinic can confirm it for you. NALSA: 15100."
)


def coverage_note_for(mode: str, results: list[dict]) -> str:
    """Computes docs/evaluation.md's cognizable/bailable coverage caveat PER RESPONSE
    instead of stating it unconditionally on every response -- silent (empty string) when
    everything actually shown is verified data, populated only when there's a concrete
    reason to doubt what's on screen:

      - section_number mode: any result with has_data=False means this specific section
        has no verified row (it may be s.501/s.502, the last known cognizable/bailable gap,
        or a section the First Schedule never covered at all -- either way, nothing to show
        for it). Note attaches to that response; a response where every result has_data=True
        needs no caveat at all.
      - name mode: search_by_name() can only ever match a row that EXISTS in
        offence_attributes, so any non-empty result set is inherently already-verified data
        -- silent. An EMPTY result set is exactly the ambiguous case the caveat protects
        against: a real offence among the 22 known gaps would produce zero matches here,
        indistinguishable from "not in the corpus at all" without this note.
    """
    if mode == "section_number":
        if any(not r.get("has_data", True) for r in results):
            return _PER_SECTION_COVERAGE_NOTE
        return ""
    # mode == "name"
    return "" if results else _BLANKET_COVERAGE_NOTE


async def search_offences(db: AsyncSession, q: str) -> tuple[str, list[dict], str]:
    mode, section_number = detect_mode(q)
    if mode == "section_number":
        results = await lookup_by_section(db, section_number)
    else:
        results = await search_by_name(db, q)
    return mode, results, coverage_note_for(mode, results)
