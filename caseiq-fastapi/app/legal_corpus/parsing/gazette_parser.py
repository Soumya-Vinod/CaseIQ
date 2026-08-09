"""Parser for the Gazette-of-India-Extraordinary enacted-Act format: BNS, BNSS,
BSA. All three are single-column, no Bill-style line-number gutter, but each
carries a clean "ARRANGEMENT OF SECTIONS/CLAUSES" table of contents ahead of
the operative text, and marginal notes are sometimes fused onto the same line
as the section number with no space before a following "(" (e.g. BNSS's
"Definitions. 2.(1) In this Sanhita...").
"""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from .base import ActParser, ParseReport, RawSection

# Group 1: an optional marginal-note prefix sharing the line with the section
#          number (BNSS/BSA quirk) -- a short capitalised phrase ending in ".".
# Group 2: the section number itself.
# Lookahead: the number's "." must be followed by whitespace OR an immediate
#            "(" (BNSS/BSA's "2.(1)" -- no space before the paren).
_HEADER_RE = re.compile(
    r"(?:^|\n)"
    r"(?:[A-Z][^\n.]{0,80}\.\s+)?"
    r"(\d{1,3}[A-Z]{0,2})\."
    r"(?=[\s(])",
    re.MULTILINE,
)


class GazetteParser:
    name = "GazetteParser"
    version = "1"

    def __init__(self, x_tolerance: float = 3.0) -> None:
        # pdfplumber's own default is 3.0. BSA's embedded font drops spaces
        # at that setting (words glue together) -- pass 1.0 for BSA only.
        self.x_tolerance = x_tolerance

    def parse(self, path: Path) -> ParseReport:
        text = self._extract_text(path)
        candidates = self._find_candidates(text)
        sections = _dedupe_keep_longest(candidates)
        return ParseReport(
            act="",  # filled in by the caller, which knows which act it asked for
            parser_name=self.name,
            parser_version=self.version,
            source_path=str(path),
            sections=sections,
        )

    def _extract_text(self, path: Path) -> str:
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text(x_tolerance=self.x_tolerance) or "") + "\n"
        return text

    def _find_candidates(self, text: str) -> list[RawSection]:
        matches = list(_HEADER_RE.finditer(text))
        out: list[RawSection] = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = re.sub(r"\s+", " ", text[start:end]).strip()
            if not body:
                continue
            out.append(
                RawSection(
                    section_number=m.group(1).strip(),
                    section_title=None,  # Gazette body text doesn't reliably separate
                    section_text=body[:5000],  # a marginal-note title from operative text
                )
            )
        return out


def _dedupe_keep_longest(candidates: list[RawSection]) -> list[RawSection]:
    """A section number legitimately appears twice in these documents: once in
    the ToC (short: just the heading) and once in the operative text (long:
    the actual provision). Rather than rely on whichever happens to be
    processed last, explicitly keep the longer candidate for each number --
    correct regardless of document ordering.
    """
    best: dict[str, RawSection] = {}
    for c in candidates:
        prev = best.get(c.section_number)
        if prev is None or c.raw_char_count > prev.raw_char_count:
            best[c.section_number] = c
    return list(best.values())
