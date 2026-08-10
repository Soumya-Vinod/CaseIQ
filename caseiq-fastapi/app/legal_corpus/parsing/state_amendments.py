"""Structural detection of state amendments appended inline in an India Code
consolidated PDF.

States can amend/insert into a central Act under the Concurrent List, and
India Code appends the resulting text inline in the consolidated PDF, headed
literally "STATE AMENDMENT" followed by the jurisdiction's name (e.g.
"Jammu and Kashmir and Ladakh (UTs)", "Tripura.--"), immediately before the
inserted section(s). Those inserted sections use the exact same numbered-
header shape as the Act's own sections (e.g. "382B. Whoever commits..."), so
a structural parser cannot tell them apart from real central-Act provisions
by shape alone -- discovered 2026-08-10 while re-sourcing IPC from India Code
(the file previously in this repo predated this problem because it predated
the state-amendment content being present at all). This is NOT the same
document family's footnote problem (parsing/footnotes.py): footnotes are
per-page amendment citations; state amendments are complete alternate
provisions that are real, valid law -- just not part of the pan-India Act.

Design question of whether/how to represent state-specific law properly
(rather than excluding it) is tracked as backlog item C9, NOT solved here.
For now: detect structurally and EXCLUDE from the pan-India corpus, but
NEVER silently -- find_and_exclude() always returns what it dropped and
under which heading, and callers (validate.py) must report it.

Uses the document's own table-of-contents-derived expected_numbers (see
toc.py) as the anchor for "where does the state-amendment block end and the
real Act resume" -- not a hardcoded page range or section-number blocklist,
since neither generalises across states/acts/print runs. A section is only
ever classified as a state amendment when there's a literal "STATE AMENDMENT"
heading between it and the nearest preceding ToC-listed (real) section.
"""
from __future__ import annotations

import re

from .base import RawSection

_HEADING_RE = re.compile(r"^[ \t]*STATE AMENDMENT[ \t]*$", re.MULTILINE)


def heading_positions(full_text: str) -> list[tuple[int, str]]:
    """Every 'STATE AMENDMENT' heading in the document, paired with the
    jurisdiction name taken from the next non-blank line after it (trailing
    punctuation like the dash in "Tripura.--" stripped for readability)."""
    out: list[tuple[int, str]] = []
    for m in _HEADING_RE.finditer(full_text):
        name = ""
        for line in full_text[m.end():m.end() + 200].splitlines():
            line = line.strip()
            if line:
                name = line.rstrip(".—–- ").strip()
                break
        out.append((m.start(), name))
    return out


def find_and_exclude(
    sections: list[RawSection], full_text: str, expected_numbers: frozenset[str]
) -> tuple[list[RawSection], list[tuple[str, str]]]:
    """Splits `sections` into (kept, excluded).

    `excluded` is [(section_number, heading_name), ...] for every section
    that is NOT in the document's own ToC (expected_numbers) AND sits after
    a 'STATE AMENDMENT' heading with no ToC-listed section header in
    between -- i.e. structurally inside a state-amendment block. A ToC-
    absent section with NO such heading nearby is left in `kept` untouched:
    it's still an unexplained gap (validate.py's existing `unexpected`
    reporting), not something this module has grounds to explain away.
    """
    headings = heading_positions(full_text)
    if not headings:
        return sections, []

    real_positions = sorted(
        s.char_start for s in sections
        if s.section_number in expected_numbers and s.char_start >= 0
    )

    def nearest_real_before(pos: int) -> int:
        result = -1
        for p in real_positions:
            if p >= pos:
                break
            result = p
        return result

    kept: list[RawSection] = []
    excluded: list[tuple[str, str]] = []
    for s in sections:
        if s.section_number in expected_numbers or s.char_start < 0:
            kept.append(s)
            continue
        anchor = nearest_real_before(s.char_start)
        heading_name = None
        for hpos, hname in headings:
            if anchor < hpos < s.char_start:
                heading_name = hname  # last (closest) heading before this section wins
        if heading_name is not None:
            excluded.append((s.section_number, heading_name))
        else:
            kept.append(s)
    return kept, excluded
