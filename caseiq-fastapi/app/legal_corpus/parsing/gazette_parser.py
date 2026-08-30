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

from .base import MAX_SECTION_TEXT_CHARS, ActParser, ParseReport, RawSection
from .footnotes import is_footnote_shaped
from .schedule_exclusion import exclude_schedule_region
from .section_boundary import trim_trailing_furniture

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
    version = "10"
    # v10: parsing/section_boundary.py's whole-line furniture recognition
    #     (trim_trailing_furniture, unchanged in structure since v7) now
    #     also recognises two more line SHAPES: a chapter/ToC sub-heading
    #     line ("Of Hurt", "112 Of Currency-Notes and Bank-Notes"), and an
    #     ALL-CAPS chapter-title line carrying a glued footnote-index
    #     asterisk run mid-title ("...DOCUMENTSAND TO 2*** PROPERTY
    #     MARKS"). A same-session detour (v9, since reverted) misdiagnosed
    #     these as furniture fused onto the same RAW line as real content
    #     with no newline -- true only of the whitespace-COLLAPSED text
    #     used to eyeball the symptom. The real bug was that the backward
    #     scan stopped one line early because neither shape was recognised
    #     as a continuation/anchor line -- see section_boundary.py's module
    #     docstring for the full account, including v9's mid-line-split
    #     mechanism (trim_glued_suffix) and the data-loss regression it
    #     caused (25 of BSA's 170 sections rejected as near-empty) before
    #     being removed. Roughly half the ~80 sections the completeness
    #     gate flagged 2026-08-15 (post-v8) are now fixed by this; the
    #     remainder is a fifth, distinct root cause (a different feature --
    #     _HEADER_RE's marginal-note-prefix group -- misfiring on ordinary
    #     sentence-final capitalised phrases) plus a handful of other known
    #     shapes, tracked not fixed per the stopping rule agreed
    #     2026-08-15: see docs/m1-verification.md.
    # v8: candidates found inside the document's own trailing Schedule are
    #     now excluded BEFORE dedup (parsing/schedule_exclusion.py) --
    #     same fix as legacy_parser.py v8. No confirmed corruption found
    #     in BNS/BNSS/BSA yet, but BNSS has the identical First-Schedule-
    #     classification-table structure as CrPC, so the same collision
    #     mechanism applies; excluding structurally rather than waiting
    #     for it to actually corrupt a section first.
    # v7: section boundaries now trimmed at the first trailing furniture
    #     line (chapter heading, Gazette masthead, dash/asterisk separator,
    #     standalone page number) via parsing/section_boundary.py, instead
    #     of always running to the next header match -- ~330 sections (15%
    #     of the corpus) had this furniture bled onto the end of otherwise-
    #     complete text, found 2026-08-14 via validate.py's completeness
    #     check. Not cosmetic: this text is embedded and fed to the LLM as
    #     retrieval context.
    # v6: section_text's hard cap raised from 5000 to MAX_SECTION_TEXT_CHARS
    #     (20000, see base.py) -- 5000 was silently truncating real, long
    #     sections, found 2026-08-14 building the golden eval set: BNS 356
    #     (Defamation) and BNS 303 (Theft) were both missing real content --
    #     BNS 303's own punishment subsection wasn't in the database at all.
    #     38 sections across all five acts were affected in total.
    # v5: footnotes.py gained a third footnote vocabulary (extension/
    #     application-history, e.g. IPC's "has been extended to Berar
    #     by..." -- see legacy_parser.py v5 / footnotes.py for the concrete
    #     bug this closes). No observed effect on BNS/BNSS/BSA text, but the
    #     shared check runs uniformly and the version bump records that its
    #     behaviour changed.
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
        # MUST run before dedup -- see schedule_exclusion.py and
        # legacy_parser.py's identical call for why (a Schedule row's
        # number collides with a real section's, so post-dedup exclusion
        # is too late; the real candidate would already be gone).
        candidates, excluded_schedule_rows = exclude_schedule_region(candidates, text)
        sections = _dedupe_keep_longest(candidates)
        return ParseReport(
            act="",  # filled in by the caller, which knows which act it asked for
            parser_name=self.name,
            parser_version=self.version,
            source_path=str(path),
            sections=sections,
            full_text=text,
            excluded_schedule_rows=excluded_schedule_rows,
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
            raw = trim_trailing_furniture("".join(pieces))
            body = re.sub(r"\s+", " ", raw).strip()

            if not body:
                continue
            out.append(
                RawSection(
                    section_number=m.group(1).strip(),
                    section_title=None,  # Gazette body text doesn't reliably separate
                    section_text=body[:MAX_SECTION_TEXT_CHARS],  # a marginal-note title from operative text
                    char_start=m.start(),
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
