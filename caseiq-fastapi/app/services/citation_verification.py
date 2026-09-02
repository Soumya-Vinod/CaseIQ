"""C5: enforce the grounding rule _STRUCTURED_PROMPT only ASKS the model to
follow, not something anything downstream actually checks. Post-generation,
pre-response: every section named in `structured_data.laws_applicable` is
checked against two things -- does it exist in the corpus at all, and was
it actually in THIS query's own retrieved set. Right now, without this, a
model that ignores the prompt's "cite only what you were given" instruction
simply ships.

Two distinct failure modes, logged and counted separately (not merged into
one "bad citation" bucket) because they mean different things:
  - nonexistent: the model invented a section number outright. Pure
    fabrication -- the same failure class as this project's founding
    incident ("BNS 2023, Section 499", which doesn't exist).
  - not_retrieved: the section is real and in force, but wasn't retrieved
    for this specific query. The model pulled a real number from memory and
    got lucky it exists -- still ungrounded, since nothing about THIS
    answer's actual evidence supports citing it. A subtler, arguably more
    dangerous failure than outright invention, since a real section number
    looks completely unremarkable in the output.

`laws_applicable` is the only structured_data field that carries an (act,
section) pair at all (checked: punishments/immediate_steps/critical_deadlines/
your_rights/dos_and_donts are all free text or don't reference a specific
section) -- so it's the only field this verifies and can safely strip from,
by construction. Free-text mentions of a section number elsewhere in the
prose (conversational_summary, situation_overview, step details) are a
different, harder problem -- surgically removing "BNS 303" from a sentence
without breaking its grammar isn't the same operation as dropping a list
element -- and are deliberately out of scope here; see the module's own
`scan_free_text_for_citations` for a detection-only (not stripping) pass
over that surface, so at least how often it happens is measured rather than
ignored.
"""
from __future__ import annotations

import re

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.citation_stats import CitationVerificationStats
from app.models.corpus import Act, JudicialStatus, SectionVersion
from app.services.retrieval import in_force, not_struck_down

_ACT_CODES = ("BNS", "BNSS", "BSA", "IPC", "CrPC")
_ACT_LOOKUP = {a.lower(): a for a in _ACT_CODES}


def normalize_act(raw: str) -> str | None:
    """The LLM's own `act` field comes back as "BNS 2023" / "IPC 1860" /
    "CrPC 1973" (per _STRUCTURED_PROMPT's schema example) -- retrieved
    sections and the corpus itself key on the bare code. Takes the first
    whitespace token, matches case-insensitively against the known five;
    anything else is unrecognised, not guessed at."""
    if not raw:
        return None
    first = raw.strip().split()[0] if raw.strip() else ""
    return _ACT_LOOKUP.get(first.lower())


async def _section_exists(db: AsyncSession, act_code: str, section: str, as_of) -> bool:
    stmt = (
        select(SectionVersion.id)
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, and_(
            JudicialStatus.act_id == SectionVersion.act_id,
            JudicialStatus.section_number == SectionVersion.section_number,
        ))
        .where(
            Act.act_code == act_code, SectionVersion.section_number == section,
            in_force(as_of), not_struck_down(),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).first() is not None


_CITATION_RE = re.compile(
    r"\b(BNS|BNSS|BSA|IPC|CrPC)\b(?:\s+(?:2023|1860|1973|Sanhita,?\s*2023|Adhiniyam,?\s*2023))?"
    r"\s*(?:Section|§|s\.)?\s*(\d{1,4}[A-Z]{0,3})\b",
)


def scan_free_text_for_citations(structured_data: dict, conversational_summary: str) -> set[tuple[str, str]]:
    """Detection only, not stripping -- see module docstring for why prose
    isn't safely editable the way a list is. Feeds the same counters as the
    structured check so how often this happens is a measured fact, not an
    assumption either way."""
    texts = [conversational_summary]
    for key in ("situation_overview", "severity_reason"):
        v = structured_data.get(key)
        if isinstance(v, str):
            texts.append(v)
    for law in structured_data.get("laws_applicable") or []:
        if isinstance(law, dict) and isinstance(law.get("why_applies"), str):
            texts.append(law["why_applies"])
    for step in structured_data.get("immediate_steps") or []:
        if isinstance(step, dict) and isinstance(step.get("details"), str):
            texts.append(step["details"])

    found: set[tuple[str, str]] = set()
    for text in texts:
        for m in _CITATION_RE.finditer(text):
            act = normalize_act(m.group(1))
            if act:
                found.add((act, m.group(2)))
    return found


async def verify_citations(
    db: AsyncSession, structured_data: dict, retrieved_sections: list[dict], as_of,
) -> tuple[dict, dict]:
    """Returns (possibly-modified structured_data, counters this call
    observed -- caller persists them). Mutates a shallow copy, never the
    caller's own dict."""
    laws = structured_data.get("laws_applicable")
    counters = {"total": 0, "stripped_nonexistent": 0, "stripped_not_retrieved": 0}
    if not isinstance(laws, list) or not laws:
        return structured_data, counters

    retrieved_keys = {(s["act"], s["section"]) for s in retrieved_sections}
    kept: list[dict] = []
    for law in laws:
        if not isinstance(law, dict):
            continue
        counters["total"] += 1
        act = normalize_act(law.get("act", ""))
        section = str(law.get("section", "")).strip()
        if not act or not section:
            counters["stripped_nonexistent"] += 1
            logger.warning("citation_stripped_malformed", law=law)
            continue
        if (act, section) in retrieved_keys:
            kept.append(law)
            continue
        exists = await _section_exists(db, act, section, as_of)
        if exists:
            counters["stripped_not_retrieved"] += 1
            logger.warning("citation_stripped_not_retrieved", act=act, section=section)
        else:
            counters["stripped_nonexistent"] += 1
            logger.warning("citation_stripped_nonexistent", act=act, section=section)

    new_data = dict(structured_data)
    new_data["laws_applicable"] = kept
    return new_data, counters


async def record_stats(db: AsyncSession, counters: dict) -> None:
    if counters["total"] == 0:
        return
    row = (await db.execute(select(CitationVerificationStats).limit(1))).scalar_one_or_none()
    if row is None:
        row = CitationVerificationStats(
            citations_total=0, citations_stripped_nonexistent=0, citations_stripped_not_retrieved=0,
        )
        db.add(row)
        await db.flush()
    row.citations_total += counters["total"]
    row.citations_stripped_nonexistent += counters["stripped_nonexistent"]
    row.citations_stripped_not_retrieved += counters["stripped_not_retrieved"]


NOTE_CITATIONS_STRIPPED = (
    " None of the specific sections the model initially named could be confirmed against what "
    "was actually retrieved for this query, so no section citations are shown below -- treat the "
    "rest of this answer as general guidance, not a specific legal citation."
)
