"""Shared parser contract. One implementation per source-DOCUMENT-FORMAT family
(gazette_parser.py, legacy_parser.py), not one per act -- BNS/BNSS/BSA share a
parser because they're the same typesetting family, not because they're the
same act. See registry.py for the act -> parser mapping.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

# Safety cap on a single section's captured text -- guards against a genuine
# parsing-runaway pathology (e.g. the "last section absorbs everything to
# EOF" failure mode noted in docs/m1-verification.md's Known limitations),
# NOT a limit real operative text is expected to hit. Previously 5000, which
# turned out to be well within range for real, long, illustration-heavy
# sections -- found 2026-08-14 while building the golden eval set: BNS 356
# (Defamation) and BNS 303 (Theft) were BOTH silently missing real content
# (BNS 303's own punishment subsection wasn't even in the database) because
# they legitimately exceeded 5000 characters. 38 sections across all five
# acts were affected. validate.py's content-completeness check treats
# anything landing at or near this cap as a truncation signal worth
# flagging regardless of its exact value -- so raising this number moves
# where "near the cap" starts, but doesn't remove the safety net.
MAX_SECTION_TEXT_CHARS = 20_000


@dataclass(frozen=True)
class RawSection:
    """One parsed provision, before validation or DB upsert."""

    section_number: str
    section_title: str | None
    section_text: str
    marginal_note: str | None = None
    page_start: int | None = None
    is_repealed: bool = False
    # Character offset of this section's header match within the parser's
    # own ParseReport.full_text, or -1 when a parser doesn't track it (safe
    # default -- callers that need it, like state_amendments.py, must treat
    # -1 as "position unknown" and skip, never as offset 0).
    char_start: int = -1

    @property
    def raw_char_count(self) -> int:
        return len(self.section_text)


@dataclass(frozen=True)
class ParseReport:
    """What a parser actually did, independent of validation outcome."""

    act: str
    parser_name: str
    parser_version: str
    source_path: str
    sections: list[RawSection] = field(default_factory=list)
    # The full extracted text, carried forward so validate.py can derive
    # expected_section_numbers from the document's OWN table of contents
    # (parsing/toc.py) instead of depending on an externally supplied count.
    # Empty string, not None, when a parser has no text to offer -- keeps
    # callers from needing an extra None-check before slicing/searching it.
    full_text: str = ""
    # Section numbers excluded because they were candidates found INSIDE
    # the document's own trailing Schedule (parsing/schedule_exclusion.py)
    # -- e.g. CrPC's First Schedule tabulates rows by IPC section number,
    # which collide with CrPC's own numbering and would otherwise win the
    # dedup-longest contest against the real section. Populated by the
    # parser itself (this exclusion must happen BEFORE dedup, unlike state
    # amendments), carried here purely for validate.py's print_report to
    # surface -- never silent, same principle as excluded_state_amendments.
    excluded_schedule_rows: list[str] = field(default_factory=list)


class ActParser(Protocol):
    """Implemented once per source-document family. parse() takes a path and
    returns every candidate section it found -- deduplication (e.g. a section
    number appearing in both a table of contents and the operative text) is
    the parser's job, since only the parser knows its own document's shape.
    A parser MAY drop candidates it can positively identify as not being a
    provision at all, using knowledge specific to its own document family
    (e.g. LegacyActParser drops IPC/CrPC's per-page amendment footnotes,
    which only exist in that format). It must NOT drop something merely
    because it looks short, low-quality, or duplicate-ish -- that judgment
    is validate.py's job, applied uniformly across every parser, so quality
    rejection is visible and consistent rather than silently baked into
    each format's own logic.
    """

    name: str
    version: str

    def parse(self, path: Path) -> ParseReport: ...
