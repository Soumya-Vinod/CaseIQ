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
from .footnotes import is_footnote_shaped

# Group 1: an optional marginal-note prefix sharing the line with the section
#          number (BNSS/BSA quirk). Marginal notes wrap across lines in the
#          PDF's original two-column layout and pdfplumber's column-unaware
#          extraction drops an arbitrary fragment of one next to the number --
#          e.g. "Trial of 4. (1) All offences..." or "Classes of 6. Besides
#          the High Courts...". The fragment does NOT reliably end in "." (it's
#          a mid-sentence wrap, not a full clause), so this only requires it to
#          start with a capital letter and end in whitespace before the digits.
# Group 2: the section number itself.
# Lookahead: the number's "." must be followed by whitespace, an immediate "("
#            (BNSS/BSA's "2.(1)" -- no space before the paren), or an immediate
#            capital letter (BNSS also has bare "15.The State Government..."
#            with no space at all after the period).
# The strong discriminator that keeps this from over-matching prose is the
# unconditional requirement immediately after the optional prefix: digits
# directly followed by a literal "." -- "Rules 45 and 46" never matches
# because "45" isn't immediately followed by ".".
_HEADER_RE = re.compile(
    r"(?:^|\n)"
    r"(?:[A-Z][^\n]{0,80}\s)?"
    r"(\d{1,3}[A-Z]{0,2})\."
    r"(?=[\sA-Z(])",
    re.MULTILINE,
)


class GazetteParser:
    name = "GazetteParser"
    version = "4"
    # v4: footnote excision now bounds each footnote's own span at its line end,
    #     not the next regex match (see legacy_parser.py's matching fix / CrPC
    #     s.57 for the concrete bug this closes -- the last footnote in a run
    #     was swallowing all the real section text that followed it).
    # v3: footnote/annotation defence added -- BNS's India Code "as on"
    #     consolidated reprint carries real footnotes ("...vide notification
    #     No. S.O. 850(E)...") that this parser had zero defence against,
    #     confirmed to have silently corrupted BNS s.1 (docs/m1-verification.md).
    #     BNSS/BSA are unconsolidated Gazette originals with no such footnotes,
    #     so this is a no-op for them, but the check runs uniformly.

    def __init__(self, x_tolerance: float = 3.0, engine: str = "pdfplumber") -> None:
        # pdfplumber's own x_tolerance default is 3.0. BSA's embedded font
        # drops spaces at that setting (words glue together); x_tolerance=1
        # fixes the body text but pdfplumber still garbles BSA's final pages
        # (Chapter XII / the repeal clause) into unrecoverable noise -- per
        # the BSA extraction ladder, PyMuPDF (engine="pymupdf") was tried next
        # and reads those same pages cleanly, so BSA uses it instead of a
        # pdfplumber tolerance tweak. BNS/BNSS stay on pdfplumber, which
        # already parses them exactly.
        self.x_tolerance = x_tolerance
        if engine not in ("pdfplumber", "pymupdf"):
            raise ValueError(f"unknown engine {engine!r}")
        self.engine = engine

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
            full_text=text,
        )

    def _extract_text(self, path: Path) -> str:
        if self.engine == "pymupdf":
            import fitz
            text = ""
            with fitz.open(path) as doc:
                for page in doc:
                    text += page.get_text() + "\n"
            return text
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text(x_tolerance=self.x_tolerance) or "") + "\n"
        return text

    def _find_candidates(self, text: str) -> list[RawSection]:
        matches = list(_HEADER_RE.finditer(text))
        # Checked against each match's own raw text immediately following it
        # (before whitespace normalisation) -- same rationale as
        # legacy_parser.py: a footnote must never be allowed to either win the
        # dedup-longest contest against real section text, or truncate real
        # text it happens to interrupt mid-sentence.
        is_footnote = [is_footnote_shaped(text[m.start():m.start() + 260]) for m in matches]

        def match_end(idx: int) -> int:
            return matches[idx + 1].start() if idx + 1 < len(matches) else len(text)

        def footnote_end(idx: int) -> int:
            # See legacy_parser.py's footnote_end -- a footnote's own text is
            # one line; bounding its excised span at the next MATCH instead
            # is wrong for the last footnote in a run, since match_end then
            # points at the next real header and would swallow all genuine
            # section text in between as if it were part of the footnote.
            # Search from .end(), not .start() -- _HEADER_RE's leading
            # "(?:^|\\n)" is part of the match itself, so .start() points at
            # the newline BEFORE the footnote's own text, not after it.
            nl = text.find("\n", matches[idx].end())
            line_end = nl if nl != -1 else len(text)
            return min(line_end, match_end(idx))

        out: list[RawSection] = []
        for i, m in enumerate(matches):
            if is_footnote[i]:
                continue

            j = i + 1
            while j < len(matches) and is_footnote[j]:
                j += 1
            end = matches[j].start() if j < len(matches) else len(text)

            pieces = []
            cursor = m.start()
            for k in range(i + 1, j):  # excise each interrupting footnote's own span
                pieces.append(text[cursor:matches[k].start()])
                cursor = footnote_end(k)
            pieces.append(text[cursor:end])
            body = re.sub(r"\s+", " ", "".join(pieces)).strip()

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
