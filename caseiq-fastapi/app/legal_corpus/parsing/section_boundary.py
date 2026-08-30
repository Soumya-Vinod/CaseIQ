"""Bounds where a section's REAL content ends, before the parser's naive
boundary (the next header match, or end of document) is reached. Neither
parser has ever bounded a section any more precisely than "everything up to
the next header match" -- which is correct when the two are adjacent, but
wrong whenever inter-section page furniture (a chapter heading, a page
break, a Gazette running masthead, a dash/asterisk separator rule) sits in
the gap between them. That furniture was silently becoming part of the
PRECEDING section's stored text.

Found 2026-08-14 via validate.py's new content-completeness check: ~330
sections (about 15% of the corpus) across all five acts had this kind of
trailing noise. Not cosmetic -- this text gets embedded and fed to the LLM
as retrieval context, so e.g. an IPC s.378 (Theft) vector blended with
"CHAPTER XVIII OF OFFENCES RELATING TO DOCUMENTS" is a vector for two
unrelated topics, which degrades retrieval quality directly.

FIRST VERSION OF THIS FIX WAS WRONG, caught by the same completeness check
it was meant to satisfy: matching "first furniture-shaped line found
anywhere" and trimming from there is only safe if furniture can't appear
mid-section -- it can. A section long enough to span a PDF page break (much
more common now that MAX_SECTION_TEXT_CHARS is 20000, not 5000) has a page
number/masthead/dash line in the MIDDLE of its own continuing text, not just
at its true end. Treating that as "the section is over" cut 12-31% of each
act's total text, all of it real content, most severely on exactly the
long, page-spanning sections this whole fix exists to stop truncating.
Gate correctly failed and caught it before it reached the corpus.

Fixed design: walk backward from the section's naive end, only ever
stripping a CONTIGUOUS trailing run of furniture-or-blank lines. The moment
a line that looks like real content is hit, stop -- everything from there
forward (toward the start) is kept, no matter what furniture-shaped lines
might appear earlier in the body. This can never cut into content that has
more real content after it, because by definition that later real content
would already have stopped the backward walk.

A SECOND WRONG TURN, 2026-08-15: the completeness gate still flagged ~80
sections after the fix above landed (e.g. IPC s.318 ending "...or with
fine, or with both. 77 Of Hurt"). Misread as furniture fused onto the same
RAW line as real content with no newline between them (true only of the
WHITESPACE-COLLAPSED section_text used to eyeball the symptom) -- built a
whole second mechanism, trim_glued_suffix, to split a line mid-string. That
mechanism itself then caused real, confirmed data loss (25 of BSA's 170
sections rejected as near-empty) because its furniture alternatives'
internal ".*" combined unsafely with re.DOTALL across the whole remaining
multi-page text. Root cause, once actually checked against the RAW
(pre-collapse) text: "77" and "Of Hurt" are each their OWN separate raw
lines -- there was no same-line fusion at all. The real bug was that this
module's own backward scan stopped one line too early, because neither
"Of Hurt" (mixed-case, not ALL-CAPS) nor a chapter title carrying a glued
footnote-index asterisk ("...DOCUMENTSAND TO 2*** PROPERTY MARKS", the "*"
not being in _SHORT_ALL_CAPS_RE's character class) was recognised as a
continuation/anchor line. Fixed at the right layer instead -- extending
_STRICT_FURNITURE_LINE_RE and _SHORT_ALL_CAPS_RE, not by inventing a
separate mid-line mechanism. trim_glued_suffix was removed entirely.
Lesson: diagnose from raw text, never from the already-collapsed
section_text -- whitespace-collapsing is exactly what makes separate lines
look fused.
"""
from __future__ import annotations

import re

from .completeness import TERMINAL_CHARS

# A line matching any of these, on its own, is unambiguously furniture, not
# operative section text -- checked against ANY line in isolation.
_STRICT_FURNITURE_LINE_RE = re.compile(
    r"^[ \t]*(?:"
    r"CHAPTER\s*[IVXLCDM]+[A-Z0-9]?\b.*"                           # "CHAPTER II", "CHAPTER XVIII ...",
                                                                    # "CHAPTER VA"/"CHAPTER IXA" (a chapter
                                                                    # inserted later by amendment, lettered
                                                                    # like a section is -- 5A, 9A, 20A...),
                                                                    # "CHAPTERIX" (glued, no space)
    r"|.*THE GAZETTE OF INDIA.*"                                   # Gazette page masthead
    r"|THE (?:INDIAN PENAL CODE|CODE OF CRIMINAL PROCEDURE)\b.*"   # legacy Bare Act running header
    r"|[_\-]{5,}.*"                                                # dash/underscore separator rule
    r"|\d{0,3}(?:\*[ \t]*){5,}.*"                                  # asterisk separator rule, optionally
                                                                    # led by a glued-on footnote index
                                                                    # ("7* * * * *")
    r"|[A-Z]\.[—-].*"                                              # lettered sub-part heading within a
                                                                    # chapter (BNSS/CrPC: "A.—Summons",
                                                                    # "D.—Other rules regarding processes")
    r"|(?:\d{1,3}\s*)?[Oo]f\s+[A-Z][a-zA-Z,\-\s]{0,58}"             # ToC/chapter part sub-heading, its own
                                                                    # line, optionally preceded on a PRIOR
                                                                    # line by its own page number ("77",
                                                                    # separately absorbed as a page-number
                                                                    # continuation) -- "Of Hurt", "Of
                                                                    # Criminal Trespass", "112 Of Currency-
                                                                    # Notes and Bank-Notes"
    r")[ \t]*$"
)

# A chapter's TITLE line (e.g. "OF PUNISHMENTS", "GENERAL EXCEPTIONS") is a
# SEPARATE line from "CHAPTER II" and doesn't match the pattern above on its
# own -- short, fully uppercase (once spaces/punctuation are ignored) lines
# are only treated as furniture continuation, never as a furniture line that
# can START a trim on its own (too easy to collide with genuine short
# all-caps content) -- see _is_furniture_or_blank's caller. Not actually
# "short" (despite the name, kept for history) -- the length cap is 119,
# not 59: a long chapter title wraps across MULTIPLE lines, and requiring
# every wrapped line to be under 60 chars broke the backward-scan chain one
# line before ever reaching the "CHAPTER VIII"/"CHAPTER XVI" anchor itself
# (BNSS s.110's "RECIPROCAL ARRANGEMENTS FOR ASSISTANCE IN CERTAIN MATTERS
# AND PROCEDURE FOR" continuation line alone is ~75 chars; found
# 2026-08-15). Still bounded, not unlimited -- a whole line of nothing but
# uppercase letters/digits/punctuation for 120 characters is not something
# genuine operative prose does, so raising the cap doesn't meaningfully
# raise collision risk with real content, only extends how long a
# continuation run can be. "*" is in the allowed character class because a
# chapter title can carry a glued-on footnote-index digit run mid-title
# ("...DOCUMENTSAND TO 2*** PROPERTY MARKS") -- its absence separately
# broke the scan on IPC s.462, also found 2026-08-15.
_SHORT_ALL_CAPS_RE = re.compile(r"^[ \t]*[A-Z][A-Z0-9 ,.\-—'\"*]{0,119}[ \t]*$")

# A bare page number, same reasoning as the all-caps continuation above: on
# its OWN, this collides with real content far too easily (a cross-reference
# like "...of section 106" can coincidentally line-wrap with just "106" left
# alone -- confirmed to have caused 12-31% over-trimming in this fix's first
# version, all of it real content). Only ever absorbed into an already-
# anchored run, never a strict furniture line on its own.
_BARE_PAGE_NUMBER_RE = re.compile(r"^[ \t]*\d{1,4}[ \t]*$")


def _is_blank(line: str) -> bool:
    return not line.strip()


def _is_strict_furniture(line: str) -> bool:
    return bool(_STRICT_FURNITURE_LINE_RE.match(line))


def _is_caps_continuation(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and bool(_SHORT_ALL_CAPS_RE.match(line)) and any(c.isalpha() for c in stripped)


def _is_page_number_continuation(line: str) -> bool:
    return bool(_BARE_PAGE_NUMBER_RE.match(line))


def _ends_cleanly(line: str) -> bool:
    stripped = line.rstrip()
    return bool(stripped) and stripped[-1] in TERMINAL_CHARS


def trim_trailing_furniture(raw_body: str) -> str:
    """`raw_body` is the still-multi-line text assembled for one section
    (footnotes already excised), starting at its own header. Strips a
    trailing contiguous run of furniture/blank lines and returns what's
    left; returns `raw_body` unchanged if its last line is already real
    content. Callers do the whitespace-collapse AFTER this, not before --
    these patterns rely on real newlines to identify a "line" at all.

    Two phases, not one pass, because a chapter's TITLE line ("OF
    PUNISHMENTS") comes AFTER its "CHAPTER II" line in reading order --
    walking backward, the title is reached first, before the anchor that
    justifies treating it as furniture rather than short real content.
    Phase 1 greedily collects the maximal trailing run of candidate lines
    (blank / strict-furniture / all-caps-continuation / bare-page-number)
    without judging any of them individually. Phase 2 only commits the trim
    if that run contains at least one STRICT furniture line -- a run made
    up entirely of blank/continuation lines with no strict anchor is left
    alone, since neither a short all-caps line nor a bare number on its own
    is confident enough evidence (both collide with real content: an
    all-caps case-party name, or a cross-reference like "...of section 106"
    line-wrapping with just "106" left alone).
    """
    lines = raw_body.split("\n")
    run_start = len(lines)
    saw_strict_furniture = False
    i = len(lines) - 1
    while i >= 0:
        line = lines[i]
        if (_is_blank(line) or _is_strict_furniture(line)
                or _is_caps_continuation(line) or _is_page_number_continuation(line)):
            if _is_strict_furniture(line):
                saw_strict_furniture = True
            run_start = i
            i -= 1
            continue
        break  # first real-content line, walking backward -- stop here
    if run_start == len(lines):
        return raw_body  # nothing collected at all
    if saw_strict_furniture:
        return "\n".join(lines[:run_start])

    # No strict anchor in the run -- normally left alone (see the module
    # docstring on why an unanchored all-caps/page-number line isn't
    # trusted on its own). One narrow exception: a run that's ENTIRELY
    # bare page numbers (plus optional blanks), where the real content
    # line immediately before the run already ends cleanly. The original
    # over-trim failure always cut mid-sentence -- e.g. "...by its
    # sentence," ending in a comma -- never after a complete, cleanly
    # punctuated sentence, so requiring a clean ending right before an
    # unanchored lone page number is a materially different, much safer
    # claim than trusting the page number alone.
    run_lines = lines[run_start:]
    non_blank_run = [ln for ln in run_lines if not _is_blank(ln)]
    only_page_numbers = bool(non_blank_run) and all(
        _is_page_number_continuation(ln) for ln in non_blank_run
    )
    preceding_line = lines[run_start - 1] if run_start > 0 else ""
    if only_page_numbers and _ends_cleanly(preceding_line):
        return "\n".join(lines[:run_start])
    return raw_body
