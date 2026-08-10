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
from .footnotes import is_footnote_shaped

# A section that has been repealed/omitted typically retains its number and
# marginal note but has no operative text -- just a bracketed repeal notice,
# e.g. "138A. [Repealed.]" (bracket IS the notice) or "15. [Definition of
# “British India”.] Rep. by the A. O. 1937." (bracket is a DESCRIPTIVE title;
# the actual repeal verb trails after it). Allow up to ~60 chars of optional
# bracketed-or-plain text between the number and the repeal verb so both
# shapes match, while staying anchored near the start of the body so a real
# operative section that merely *mentions* "repealed" somewhere in a savings
# clause doesn't get misclassified. These are real, complete captures (not
# parse failures) and must be reported as such, not lumped in with
# "too_short"/generic-accepted -- see RawSection.is_repealed.
_REPEALED_RE = re.compile(
    r"^\d{1,3}[A-Z]{0,2}\.?\s*(?:to\s+\d{1,3}[A-Z]?\.?\s*)?"
    r"(?:"
    r"\[[^\]\n]{0,60}\]\.?\s*(?:Rep\.|Repealed|Omitted)"  # "[Title.] Rep. by..."
    r"|"
    r"\[?\s*(?:Rep\.|Repealed|Omitted)"                   # "[Repealed.]" / "Rep. by..." directly
    r")",
    re.IGNORECASE,
)

# IPC's "General Explanations" chapter defines quoted terms like
# 17 "Government".-The word... with NO period after the number (inconsistent
# with the surrounding offence-section style, e.g. "18. "India".-..." which
# does have one two lines later in the same PDF) -- accept either a literal
# period, or the number being followed directly by whitespace then an opening
# quote mark, as valid separators. The 2026 India Code reprint (re-sourced
# 2026-08-10) renders that same opening quote glyph as U+2015 HORIZONTAL BAR
# ("―") rather than a curly/straight quote -- a font-substitution artifact of
# that specific print run, not a new grammatical shape -- so s.17 (the one
# General-Explanations entry with no period) silently fell back to its
# near-empty ToC stub and was reported "missing" until this was added.
_HEADER_RE = re.compile(
    r"(?:^|\n)\s*(\d{1,3}[A-Z]{0,2})(?:\.\s+(?:\(1\)\s+)?|\s+(?=[“\"'―]))([^\n]{5,200})",
    re.MULTILINE,
)

# See parsing/footnotes.py: most real footnotes here do NOT open with the
# verb ("The proviso ins. by Act 24 of 2003...", not "Ins. by..."), which the
# original prefix-only check here missed -- confirmed to have silently
# corrupted IPC s.15 (see docs/m1-verification.md).


class LegacyActParser:
    name = "LegacyActParser"
    version = "5"
    # v5: footnotes.py now also recognises extension/application-history
    #     footnotes ("has been extended to Berar by...", "has been declared
    #     in force in..."), a third vocabulary distinct from amendment- and
    #     notification-style footnotes -- fixes IPC s.1, whose real operative
    #     "Title and extent of operation" text was losing the dedup-longest
    #     contest to a page footnote that happened to share its number by
    #     the same per-page-footnote-numbering collision as every other
    #     footnote bug in this parser. Flagged but not fixed in the original
    #     2026-08-09 hand-verification pass (docs/m1-verification.md);
    #     closed 2026-08-10 rather than carried forward into the corpus.
    # v4: header quote-lookahead now also accepts U+2015 "―" (the 2026 India
    #     Code IPC reprint's font-substituted opening-quote glyph) -- fixes
    #     IPC s.17 ("Government" definition, no period after the number)
    #     silently falling back to its near-empty ToC stub. char_start is now
    #     recorded on every RawSection too, for
    #     parsing/state_amendments.py's structural exclusion of state-
    #     amendment schedules appended inline in the same reprint.
    # v3: footnote excision now bounds each footnote's own span at
    #     its line end, not the next regex match -- fixes CrPC s.57
    #     (last footnote in a run was swallowing the real section text
    #     that followed it, all the way to the next section's header)

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
            full_text=text,
        )

    def _extract_text(self, path: Path) -> str:
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        # IPC/CrPC mark amended text with a footnote-index bracket directly
        # abutting the following word, e.g. "1[17 “Government”.—..." or
        # "3[18. “India”.—...". When that word is itself a section number
        # at logical line start, the digit+"[" sits between the newline and the
        # number with no whitespace, which breaks the header regex's
        # "(?:^|\\n)\\s*" anchor -- so the real section header is invisible to
        # the parser and only the (shorter) ToC entry for that number survives.
        # Strip the marker only when it directly follows a newline, so mid-
        # sentence occurrences ("... imprisonment for 1[life] ...") are left
        # untouched.
        text = re.sub(r"(?<=\n)\d{1,2}\[", "", text)
        return text

    def _find_candidates(self, text: str) -> list[RawSection]:
        matches = list(_HEADER_RE.finditer(text))
        is_footnote = [is_footnote_shaped(m.group(2)) for m in matches]

        def match_end(idx: int) -> int:
            return matches[idx + 1].start() if idx + 1 < len(matches) else len(text)

        def footnote_end(idx: int) -> int:
            # A footnote's own text is always one line in these documents.
            # Bounding its excised span at the next MATCH (match_end) is
            # wrong when this footnote is the last in a consecutive run --
            # match_end then points at the next REAL section header, which
            # can be thousands of characters away, silently swallowing all
            # the genuine section text in between as if it were part of the
            # footnote (confirmed to have truncated CrPC s.57 this way: the
            # real continuation "...detain in custody a person arrested..."
            # sat between the last footnote and s.58's header and was
            # entirely excised). Take whichever boundary is closer.
            # NOTE: search from matches[idx].end(), not .start() -- _HEADER_RE's
            # leading "(?:^|\\n)" is part of the MATCH itself (not a lookbehind),
            # so .start() points at the newline BEFORE the footnote's own text.
            # Searching from .start() immediately finds that same leading
            # newline (zero-width forward), which left the footnote's own text
            # completely unexcised -- confirmed via CrPC s.57 still containing
            # the literal footnote text after the first version of this fix.
            nl = text.find("\n", matches[idx].end())
            line_end = nl if nl != -1 else len(text)
            return min(line_end, match_end(idx))

        out: list[RawSection] = []
        for i, m in enumerate(matches):
            if is_footnote[i]:
                continue

            # A footnote match must never truncate the real section it
            # interrupts -- a footnote can land mid-sentence inside a real
            # section's body (e.g. CrPC s.57's real text is "...No police
            # officer shall <FOOTNOTE> detain in custody..."). Walk forward
            # past any run of footnote matches to find the true end (the next
            # REAL section, or end of document), then excise each footnote's
            # own span from the accumulated text rather than stopping at it.
            j = i + 1
            while j < len(matches) and is_footnote[j]:
                j += 1
            end = matches[j].start() if j < len(matches) else len(text)

            pieces = []
            cursor = m.start()
            for k in range(i + 1, j):  # the footnote matches being excised
                pieces.append(text[cursor:matches[k].start()])
                cursor = footnote_end(k)
            pieces.append(text[cursor:end])
            body = re.sub(r"\s+", " ", "".join(pieces)).strip()

            if not body:
                continue
            out.append(
                RawSection(
                    section_number=m.group(1).strip(),
                    section_title=re.sub(r"\s+", " ", m.group(2)).strip()[:500],
                    section_text=body[:5000],
                    is_repealed=bool(_REPEALED_RE.match(body)),
                    char_start=m.start(),
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
