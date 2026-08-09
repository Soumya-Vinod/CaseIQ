"""Parser for the old-style bare-Act format: IPC, CrPC. Section headers extract
cleanly at line start ("19. “Judge”.—The word..."). The defect
here isn't the header shape -- it's that per-page amendment footnotes
("1. Ins. by Act 21 of 2000, s. 91...") are numbered independently on every
page and are textually indistinguishable from a real section header by shape
alone. They're excluded here, structurally, using knowledge specific to this
document family (the footnote-verb prefix), rather than left for the shared
gate to catch after the fact -- a footnote must never be allowed to win the
longest-candidate dedupe against a real section of the same number.
"""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from .base import ActParser, ParseReport, RawSection

_HEADER_RE = re.compile(
    r"(?:^|\n)\s*(\d{1,3}[A-Z]?)\.\s+(?:\(1\)\s+)?([^\n]{5,200})",
    re.MULTILINE,
)

# Amendment/footnote lines always open with one of these verbs. Matched
# case-sensitively against the start of the captured body -- these are fixed
# legislative-drafting phrases, not prose that would coincidentally start a
# real provision.
_FOOTNOTE_PREFIXES = ("Ins. by", "Subs. by", "Rep. by", "Added by", "Omitted by", "Omitted,")


def _is_footnote(body: str) -> bool:
    return body.lstrip().startswith(_FOOTNOTE_PREFIXES)


class LegacyActParser:
    name = "LegacyActParser"
    version = "1"

    def parse(self, path: Path) -> ParseReport:
        text = self._extract_text(path)
        candidates = self._find_candidates(text)
        sections = _dedupe_keep_longest(candidates)
        return ParseReport(
            act="",
            parser_name=self.name,
            parser_version=self.version,
            source_path=str(path),
            sections=sections,
        )

    def _extract_text(self, path: Path) -> str:
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text

    def _find_candidates(self, text: str) -> list[RawSection]:
        matches = list(_HEADER_RE.finditer(text))
        out: list[RawSection] = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = re.sub(r"\s+", " ", text[start:end]).strip()
            if not body or _is_footnote(m.group(2)):
                continue
            out.append(
                RawSection(
                    section_number=m.group(1).strip(),
                    section_title=re.sub(r"\s+", " ", m.group(2)).strip()[:500],
                    section_text=body[:5000],
                )
            )
        return out


def _dedupe_keep_longest(candidates: list[RawSection]) -> list[RawSection]:
    """Same rationale as gazette_parser: a section number can legitimately
    appear in both the ToC and the operative text. Footnotes are already
    excluded above, so this only needs to resolve ToC-vs-body duplication.
    """
    best: dict[str, RawSection] = {}
    for c in candidates:
        prev = best.get(c.section_number)
        if prev is None or c.raw_char_count > prev.raw_char_count:
            best[c.section_number] = c
    return list(best.values())
