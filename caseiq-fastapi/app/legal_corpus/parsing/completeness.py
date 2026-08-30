"""Structural truncation detection -- runs on every accepted section, every
ingestion. This is the third defect of the same underlying class this
project has now hit: correct section NUMBER, wrong or incomplete TEXT
(BNS/IPC footnote overwrites, the IPC s.1 dedup bug, and now this -- a flat
5000-char parser cap silently cutting off 38 real sections, discovered
2026-08-14 while building the golden eval set). validate.py's existing
set-diff gate cannot catch any of these, by design: it only ever checks
which NUMBERS exist, never whether a given number's TEXT is actually
complete. Hand-verification (docs/m1-verification.md) caught this defect
class twice before by manual sampling and missed most of it both times --
sampling cannot scale to "check every section for truncation"; this can,
because it runs on all of them, every time.

Three independent signals, each cheap and structural (no LLM, no semantic
judgement):
  1. Does the text end at a sentence-terminal character? A truncated cut
     lands mid-word/mid-sentence; real operative text (or a citation, a
     bracketed insertion, a quoted closing) does not.
  2. Is the text at or suspiciously near ANY known hard cap? Landing exactly
     at a length limit is close to definitional proof of truncation by that
     limit, whatever the limit's current value is.
  3. Is the text shorter than the document's own ToC entry for that same
     section number? A ToC line listing several defined terms describes a
     section that cannot legitimately be shorter than the listing itself.
"""
from __future__ import annotations

from .base import MAX_SECTION_TEXT_CHARS, RawSection

# Characters real, complete section text in this corpus is observed to end
# on: a full stop, a closing bracket/parenthesis/quote (a bracketed
# insertion, a citation, a quoted illustration), a semicolon or colon
# (rare, but legitimate mid-list positions when a section IS the sentence
# fragment continuing into a schedule), or "]" specifically for a
# "[Repealed.]"-style notice. Deliberately a closed set rather than "not a
# letter" -- a truncation cut almost always lands on an ordinary word
# character, which this correctly flags; the closed set is what keeps this
# from firing on the wide variety of genuinely valid endings. Public (not
# underscore-prefixed) because section_boundary.py reuses it too -- same
# "does this text end cleanly" question, asked for a different purpose.
TERMINAL_CHARS = set(".)]\"'”’;:")
_TERMINAL_CHARS = TERMINAL_CHARS  # kept for any existing internal references

# Sections known to legitimately run long enough to approach even the raised
# cap are rare but real (e.g. a definitions section enumerating dozens of
# terms) -- "near" the cap is deliberately a small margin, not a large one,
# so this stays a true near-miss signal rather than flagging every
# comfortably-long section.
_NEAR_CAP_MARGIN = 50


def ends_mid_sentence(text: str) -> bool:
    stripped = text.rstrip()
    if not stripped:
        return False
    return stripped[-1] not in _TERMINAL_CHARS


def near_cap(text: str, cap: int = MAX_SECTION_TEXT_CHARS, margin: int = _NEAR_CAP_MARGIN) -> bool:
    return len(text) >= cap - margin


def shorter_than_toc_entry(text: str, toc_line: str | None) -> bool:
    if not toc_line:
        return False
    return len(text) < len(toc_line)


def check_completeness(section: RawSection, toc_entries: dict[str, str] | None) -> str | None:
    """Returns a human-readable reason string if `section` looks truncated,
    else None. Checked against ALL three signals so the reported reason
    names exactly which one(s) fired, rather than a generic "looks bad"."""
    reasons: list[str] = []
    if ends_mid_sentence(section.section_text):
        reasons.append(f"ends mid-sentence/mid-word: ...{section.section_text[-40:]!r}")
    if near_cap(section.section_text):
        reasons.append(f"length {len(section.section_text)} at/near the {MAX_SECTION_TEXT_CHARS}-char cap")
    toc_line = (toc_entries or {}).get(section.section_number)
    if shorter_than_toc_entry(section.section_text, toc_line):
        reasons.append(f"body ({len(section.section_text)} chars) shorter than its own ToC "
                        f"listing ({len(toc_line)} chars): {toc_line!r}")
    return "; ".join(reasons) if reasons else None
