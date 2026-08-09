"""Shared parser contract. One implementation per source-DOCUMENT-FORMAT family
(gazette_parser.py, legacy_parser.py), not one per act -- BNS/BNSS/BSA share a
parser because they're the same typesetting family, not because they're the
same act. See registry.py for the act -> parser mapping.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class RawSection:
    """One parsed provision, before validation or DB upsert."""

    section_number: str
    section_title: str | None
    section_text: str
    marginal_note: str | None = None
    page_start: int | None = None
    is_repealed: bool = False

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
