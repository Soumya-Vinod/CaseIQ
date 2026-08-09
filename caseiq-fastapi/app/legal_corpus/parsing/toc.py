"""Derive the set of section numbers an Act's OWN table of contents says
should exist -- "ARRANGEMENT OF SECTIONS"/"ARRANGEMENT OF CLAUSES" -- rather
than trusting any externally supplied count. This is what validate.py's gate
compares parsed output against: self-validating, no dependency on a folk
figure like "IPC has 511 sections" (which is the Act's highest section
NUMBER, not a count -- see the 2026-08-09 correction in project history).

Not every source document has an extractable ToC (BNSS/BSA's Gazette
originals don't carry one at all -- see gazette_parser.py's docstring), so
extract_expected_numbers() returns None when it can't find one, and callers
must treat that as "no set-based check possible for this act", not as zero
expected sections.
"""
from __future__ import annotations

import re

_TOC_HEADING_RE = re.compile(r"ARRANGEMENT OF (?:SECTIONS|CLAUSES)", re.IGNORECASE)

# The ToC's own first chapter heading ("CHAPTER I") is repeated verbatim when
# the real, operative Chapter I begins -- its SECOND occurrence is a reliable
# end-of-ToC boundary. A phrase-based boundary ("BE it enacted...") was tried
# first and silently failed on IPC (that phrase never appears verbatim in
# this PDF's extraction), which is exactly the kind of failure that must
# produce an explicit None/empty result, not a wrong-but-quiet 400,000-char
# region -- see this module's own tests.
_CHAPTER_I_RE = re.compile(r"\nCHAPTER I\n")

# Mirrors gazette_parser/legacy_parser's own header shape closely enough for
# a ToC's clean, single-column listing (which doesn't have the marginal-note
# noise the operative text does) -- but the same "no space after the period"
# quirk shows up here too, e.g. IPC's own ToC has "171D.Personation at
# elections." and "489A.Counterfeiting currency-notes..." with no space, so
# the separator is \s* (zero or more), not \s+.
_TOC_ENTRY_RE = re.compile(r"(?:^|\n)\s*(\d{1,3}[A-Z]{0,2})\.\s*\S", re.MULTILINE)

# Some ToC entries (and the corresponding operative text) consolidate an
# entire repealed range under one number, e.g. "161. to 165A. [Repealed.]" --
# the intermediate numbers (162, 163, 164, 165) are not separately addressable
# sections at all and must not be synthesized into the expected set.
_RANGE_ENTRY_RE = re.compile(r"(\d{1,3}[A-Z]{0,2})\.\s+to\s+(\d{1,3})([A-Z]?)\.")


def extract_expected_numbers(full_text: str) -> frozenset[str] | None:
    """The set of section numbers listed in this document's own
    "ARRANGEMENT OF SECTIONS/CLAUSES" table of contents, or None if no such
    ToC could be bounded (caller must not treat None as "zero expected").
    """
    heading = _TOC_HEADING_RE.search(full_text)
    if not heading:
        return None

    chapter_hits = [m.start() for m in _CHAPTER_I_RE.finditer(full_text, heading.end())]
    if len(chapter_hits) < 2:
        return None  # can't bound the end of the ToC -- don't guess
    toc_text = full_text[heading.end():chapter_hits[1]]

    numbers = {m.group(1) for m in _TOC_ENTRY_RE.finditer(toc_text)}
    # a range entry like "161. to 165A." is matched above as an ordinary
    # single entry ("161") plus stray fragments -- explicitly note the range
    # is understood, not expanded, by recording it nowhere further: the
    # intermediate numbers were never added to `numbers` in the first place
    # since _TOC_ENTRY_RE only captures what's immediately after "\n\s*".
    return frozenset(numbers)


def extract_repealed_ranges(full_text: str) -> list[tuple[str, str]]:
    """[(start_number, end_number), ...] for consolidated repealed ranges
    like "161. to 165A." -- informational, for the validation report, so a
    reviewer can see why e.g. 162-165 are correctly absent rather than
    wondering if the parser dropped them.
    """
    return [(m.group(1), m.group(2) + m.group(3)) for m in _RANGE_ENTRY_RE.finditer(full_text)]
