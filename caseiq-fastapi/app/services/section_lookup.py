"""Readiness E12: name the sections first, then fetch them exactly.

Five retrieval fixes this week (E5, E8-E11) moved no failing query into the
top 6, because those queries need legal classification, not text
similarity: BNS 85 never says "dowry", and CrPC 154(3) -- the remedy when
police won't register an FIR -- doesn't say it in words a user would use.
So, behind settings.SECTION_LOOKUP_ENABLED (default off, and only together
with RELEVANCE_GATE_ENABLED -- config.py):

  1. one Groq call names the sections the question's situation falls under
     (llm_service.identify_sections);
  2. each named reference is parsed and normalised (`parse_reference`);
  3. each is fetched by exact act code + section number from the in-force
     corpus -- not similarity. Anything that doesn't exist is dropped and
     logged, so the hallucination rate is visible;
  4. the found sections are PREPENDED to the hybrid-retrieval results,
     de-duplicated (`merge`). Never fused into RRF at equal weight: adding an
     equal-weight input to fusion is how E9's any-term matching and E5's
     query expansion both failed.

The relevance gate and the citation/grounding checks downstream are the
safety net, unchanged: a named section still has to be judged to answer the
question, and the answer can still only cite what's in the list.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.corpus import Act, JudicialStatus, SectionVersion
from app.services.llm import llm_service
from app.services.retrieval import (
    _serialise, acts_for_incident_date, attach_offence_attributes, in_force, judicial_status_dict,
    not_struck_down,
)

# Longest aliases first, so "BNSS" isn't read as "BNS" and "CrPC" not as "PC".
_ACT_ALIASES: list[tuple[str, str]] = sorted([
    ("bharatiya nagarik suraksha sanhita", "BNSS"), ("bnss", "BNSS"),
    ("bharatiya nyaya sanhita", "BNS"), ("bns", "BNS"),
    ("bharatiya sakshya adhiniyam", "BSA"), ("bsa", "BSA"),
    ("code of criminal procedure", "CrPC"), ("criminal procedure code", "CrPC"),
    ("cr.p.c.", "CrPC"), ("cr.p.c", "CrPC"), ("cr. p.c.", "CrPC"), ("crpc", "CrPC"),
    ("indian penal code", "IPC"), ("penal code", "IPC"), ("i.p.c.", "IPC"), ("ipc", "IPC"),
    # Not in this corpus; recognised so it's reported as such, not as a parse failure.
    ("indian evidence act", "IEA"), ("evidence act", "IEA"), ("iea", "IEA"),
], key=lambda a: -len(a[0]))
CORPUS_ACTS = frozenset({"IPC", "CrPC", "BNS", "BNSS", "BSA"})

# Base number with an optional letter suffix glued on or hyphenated ("498A",
# "498-A", "265a"), then any sub-section/clause suffix ("(3)", "(1)(b)").
_NUMBER_RE = re.compile(r"(?<!\d)(\d{1,3})(?:-?([A-Za-z]{1,2}))?(?![A-Za-z\d])((?:\s*\(\s*[0-9A-Za-z]+\s*\))*)")
_SECTION_WORD_RE = re.compile(r"\b(?:section|sec\.?|s\.|u/s\.?|§)\s*", re.IGNORECASE)


@dataclass(frozen=True)
class Reference:
    act: str           # normalised act code, "IPC" | "CrPC" | "BNS" | "BNSS" | "BSA" | "IEA"
    section: str       # base number for lookup, "498A"
    cited_as: str      # as named, for display: "154(3)"
    reason: str = ""
    title: str = ""    # the heading the model claims the section has -- checked by `title_matches`


def _find_act(text: str) -> str | None:
    low = f" {text.lower()} "
    for alias, code in _ACT_ALIASES:
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", low):
            return code
    return None


def _find_number(text: str) -> tuple[str, str] | None:
    """(base section for lookup, cited form with any sub-section)."""
    m = _SECTION_WORD_RE.search(text)
    candidates = [_NUMBER_RE.search(text, m.end())] if m else []
    candidates.append(_NUMBER_RE.search(text))
    for c in candidates:
        if c is None:
            continue
        base = c.group(1) + (c.group(2) or "").upper()
        sub = re.sub(r"\s+", "", c.group(3) or "")
        return base, base + sub
    return None


def parse_reference(entry, reason: str = "") -> Reference | None:
    """One reference from a model entry: a dict {"act", "section", "reason"}
    or a free string ("Section 498A IPC", "IPC 498A", "s. 154(3) CrPC",
    "Section 173(4) of the BNSS"). None when no act or no number can be read."""
    if isinstance(entry, dict):
        act_text = str(entry.get("act") or "")
        sec_text = str(entry.get("section") or "")
        reason = str(entry.get("reason") or reason)[:200]
        title = str(entry.get("title") or "")[:200]
        act = _find_act(act_text) or _find_act(sec_text)
        num = _find_number(sec_text) or _find_number(act_text)
    else:
        text = str(entry)
        act = _find_act(text)
        # Drop the act's name before reading the number, so a year in it
        # ("Bharatiya Nyaya Sanhita, 2023") can't be taken for a section.
        stripped = re.sub(r"\b(?:18|19|20)\d\d\b", " ", text)
        num = _find_number(stripped)
    if not act or not num:
        return None
    return Reference(act=act, section=num[0], cited_as=num[1], reason=reason,
                     title=title if isinstance(entry, dict) else "")


def parse_references(raw) -> list[Reference]:
    """Every reference in the model's reply, in order, de-duplicated on
    (act, section). Tolerates {"sections": [...]}, a bare list, or strings."""
    entries = raw.get("sections") if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        return []
    seen, out = set(), []
    for e in entries:
        ref = parse_reference(e)
        if ref and (ref.act, ref.section) not in seen:
            seen.add((ref.act, ref.section))
            out.append(ref)
    return out


@dataclass
class LookupResult:
    sections: list[dict] = field(default_factory=list)   # found, serialised like semantic_search's rows
    named: list[Reference] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)    # {"ref", "reason"}
    unparsed: int = 0
    error: str | None = None

    def log(self, query_id=None) -> None:
        logger.info(
            "section_lookup", query_id=str(query_id) if query_id else None,
            named=[f"{r.act} {r.cited_as}" for r in self.named],
            found=[f"{s['act']} {s['section']}" for s in self.sections],
            dropped=self.dropped, unparsed=self.unparsed, error=self.error,
        )


_STOPWORDS = frozenset(
    "a an and as at be by for from in into is of on or the to under with any other such its "
    "their his her which who whom section act code".split())
TITLE_MATCH_MIN = 0.6
_HEAD_CHARS = 400
SNIPPET_CHARS = 1500  # retrieval's DEFAULT_SNIPPET_CEILING


def _words(text: str) -> set[str]:
    # Plural "s" off, then the first five letters: case/cases, cognizable/cognisable.
    return {(w[:-1] if len(w) > 3 and w.endswith("s") else w)[:5]
            for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOPWORDS and len(w) > 2}


def title_matches(claimed: str, marginal_note: str, section_text: str, act: str = "") -> float:
    """Share of the claimed title's content words found in the section's own
    opening (marginal note + first _HEAD_CHARS of text). Existence alone is
    not identity: the model carries IPC/CrPC numbers into the renumbered 2023
    codes, and many such numbers exist as different sections (BNS 302 is
    wounding religious feelings, not murder). BNSS/BSA rows have no
    marginal note, but their heading words sit in the opening text -- except
    BSA's: its parse mostly moved headings into neighbouring rows (readiness
    E11), so a BSA title is checked against the whole section text."""
    want = _words(claimed)
    if not want:
        return 0.0
    body = section_text if act == "BSA" else section_text[:_HEAD_CHARS]
    have = _words(f"{marginal_note} {body}")
    return len(want & have) / len(want)


def _snippet_for(section_text: str, cited_as: str, base: str) -> str:
    """The passage that answers, not retrieval's punishment-clause snippet:
    up to SNIPPET_CHARS of the section, or -- when the named sub-section
    starts past that -- the opening plus that sub-section."""
    sub = cited_as[len(base):]
    if sub:
        first = sub[:sub.index(")") + 1] if ")" in sub else sub
        at = section_text.find(first, 1)
        if at > SNIPPET_CHARS - 300:
            head = section_text[:600].rsplit(" ", 1)[0]
            return f"{head} … {section_text[at:at + SNIPPET_CHARS - 600]}"
    return section_text[:SNIPPET_CHARS]


async def _fetch(db: AsyncSession, act_code: str, section_number: str, as_of: date) -> dict | None:
    """Exact in-force lookup -- same filters every organic retrieval path
    applies (as-of validity, K2 struck-down exclusion)."""
    stmt = (
        select(SectionVersion, JudicialStatus.status, JudicialStatus.case_name,
               JudicialStatus.citation, JudicialStatus.court, JudicialStatus.decided_on,
               JudicialStatus.scope_note)
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, and_(
            JudicialStatus.act_id == SectionVersion.act_id,
            JudicialStatus.section_number == SectionVersion.section_number,
        ))
        .where(Act.act_code == act_code, SectionVersion.section_number == section_number,
               in_force(as_of), not_struck_down())
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    sv, *js = row
    out = _serialise(sv, act_code, None, as_of, judicial_status_dict(*js))
    out["_text"] = sv.section_text
    return out


def start_identification(query: str) -> asyncio.Task:
    """Starts the model call without waiting, so it runs while hybrid retrieval
    does (the call needs no database; the session isn't shared)."""
    return asyncio.create_task(llm_service.identify_sections(query))


async def lookup_sections(db: AsyncSession, query: str, as_of: date,
                          incident_date: date | None = None,
                          identification: asyncio.Task | None = None) -> LookupResult:
    """Never raises: a failed or unusable model call returns an empty result
    with `error` set, and the caller carries on with hybrid retrieval alone.
    `identification`: a task from `start_identification`, if already started."""
    result = LookupResult()
    try:
        raw = await (identification or llm_service.identify_sections(query))
    except Exception as exc:  # noqa: BLE001 -- lookup is additive; hybrid retrieval still runs
        result.error = f"call_failed: {exc}"[:300]
        return result

    entries = raw.get("sections") if isinstance(raw, dict) else raw
    result.named = parse_references(raw)
    result.unparsed = (len(entries) if isinstance(entries, list) else 0) - len(result.named)
    allowed = set(acts_for_incident_date(incident_date)) if incident_date else CORPUS_ACTS

    for ref in result.named:
        label = f"{ref.act} {ref.cited_as}"
        if ref.act not in CORPUS_ACTS:
            result.dropped.append({"ref": label, "reason": "act_not_in_corpus"})
            continue
        if ref.act not in allowed:
            result.dropped.append({"ref": label, "reason": "outside_incident_date_regime"})
            continue
        if len(result.sections) >= settings.SECTION_LOOKUP_MAX_SECTIONS:
            result.dropped.append({"ref": label, "reason": "over_cap"})
            continue
        found = await _fetch(db, ref.act, ref.section, as_of)
        if found is None:
            result.dropped.append({"ref": label, "reason": "not_in_corpus"})
            continue
        full_text = found.pop("_text")
        match = title_matches(ref.title, found["title"] or "", full_text, ref.act)
        if match < TITLE_MATCH_MIN:
            result.dropped.append({"ref": label, "reason": "title_mismatch", "claimed_title": ref.title,
                                   "match": round(match, 2), "actual_opening": full_text[:90]})
            continue
        found.update(source="section_lookup", cited_as=ref.cited_as, lookup_reason=ref.reason,
                     snippet=_snippet_for(full_text, ref.cited_as, ref.section))
        result.sections.append(found)

    if result.sections:
        result.sections = await attach_offence_attributes(db, result.sections)
    return result


def merge(looked_up: list[dict], retrieved: list[dict]) -> list[dict]:
    """Looked-up sections first, in the model's order, then the hybrid
    results not already present. The query-level values semantic_search
    attaches to every row (top_hit_margin, classifier_in_scope_prob) are
    copied onto the looked-up rows, so signals that read sections[0] still
    read retrieval's numbers, not a missing key."""
    if not looked_up:
        return retrieved
    query_level = {k: retrieved[0].get(k) for k in ("top_hit_margin", "classifier_in_scope_prob")} if retrieved else {}
    head = [{**s, **query_level} for s in looked_up]
    have = {(s["act"], s["section"]) for s in head}
    return head + [s for s in retrieved if (s["act"], s["section"]) not in have]
