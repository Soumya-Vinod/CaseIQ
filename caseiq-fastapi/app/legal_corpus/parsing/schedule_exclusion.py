"""Structural exclusion of an Act's own trailing Schedule(s) from section
candidates -- found 2026-08-14 via validate.py's completeness check: CrPC's
First Schedule (Classification of Offences) tabulates rows *by IPC section
number*, using the exact same "NUMBER. text" header shape this parser looks
for. Where a Schedule row's number coincides with one of CrPC's own real
section numbers (e.g. both have a "126"), the row becomes a second, spurious
candidate for that number -- and because dedup-keep-longest has no way to
tell "real section" from "schedule row that happened to absorb a lot of
table text before hitting a boundary", the LONGER one (almost always the
schedule row, which runs on through many table entries) wins. CrPC's real
s.126 and s.276 were confirmed silently replaced by unrelated Schedule
content this way.

This is NOT the same problem as state_amendments.py solves: a state
amendment's inserted section number is a genuinely NEW number, so excluding
it after the parser's own dedup already ran is safe -- the real candidate
was never at risk. A Schedule row's number is NOT new; it collides with a
real section, so by the time validate.py would see a deduped list, the real
candidate has already lost and is gone. This exclusion MUST run before
dedup, inside the parser itself.

BNSS confirmed to have the identical structure (First Schedule = its own
classification-of-offences table, immediately after its last real section).
Applied to both parser families uniformly rather than patched into CrPC
alone -- the mechanism (a Schedule tabulating cross-references by number,
in a document format this parser also reads as section headers) isn't
specific to one act, and the next re-source or the next Act added to this
corpus could hit it exactly the same way.
"""
from __future__ import annotations

import re

from .base import RawSection

# Matches both "FIRST SCHEDULE" (BNSS: no separate ToC listing, one real
# occurrence) and "THE FIRST SCHEDULE" (CrPC: ToC lists it once, then the
# real heading repeats it) -- either way, the LAST occurrence in the
# document is always the real, operative heading: a ToC only ever lists it
# once, in passing, before the real one appears later in the body.
_SCHEDULE_HEADING_RE = re.compile(r"\bFIRST SCHEDULE\b")


def find_schedule_boundary(full_text: str) -> int | None:
    """Character offset where the document's own (non-ToC) Schedule begins
    -- everything from here to end-of-document is Schedule/Forms matter,
    never a real operative section. None if this document has no such
    heading at all (BSA, IPC, BNS -- none currently do, but this checks
    the actual document rather than assuming by act)."""
    hits = [m.start() for m in _SCHEDULE_HEADING_RE.finditer(full_text)]
    return hits[-1] if hits else None


def exclude_schedule_region(
    sections: list[RawSection], full_text: str
) -> tuple[list[RawSection], list[str]]:
    """Splits `sections` into (kept, excluded_numbers). Excludes any
    candidate whose char_start falls at/after the real Schedule boundary --
    called BEFORE dedup-keep-longest, from inside the parser, so a
    Schedule row never gets the chance to outcompete the real section it
    collides with in the first place. A candidate with char_start == -1
    (position not tracked) is kept untouched -- this exclusion needs a
    position to work at all.
    """
    boundary = find_schedule_boundary(full_text)
    if boundary is None:
        return sections, []
    kept: list[RawSection] = []
    excluded: list[str] = []
    for s in sections:
        if s.char_start >= 0 and s.char_start >= boundary:
            excluded.append(s.section_number)
        else:
            kept.append(s)
    return kept, excluded
