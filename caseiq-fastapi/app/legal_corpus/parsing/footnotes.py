"""Shared footnote/annotation detection, used by both parser families to keep
a footnote or editorial annotation from winning the dedup-longest contest
against real operative section text.

Found during the 2026-08-09 hand-verification pass (docs/m1-verification.md):
BNS s.1, IPC s.1, and IPC s.15 were all silently serving footnote/annotation
text instead of the real provision -- the coverage gate (validate.py) never
caught this because it only checks section NUMBERS, not content. This is the
exact defect class D1/D2 were about (corrupted text, correct numbers) showing
up again through a different mechanism: dedup-keep-longest picking whichever
candidate is longest, with no defense against a long footnote beating a short
real section.

Three footnote vocabularies observed across the five source documents:
  - amendment-history style (IPC/CrPC's per-page footnotes): "Ins. by Act 21
    of 2000...". The verb does NOT reliably open the sentence -- most
    observed cases are "The <description> <verb> by ..." (e.g. "The proviso
    ins. by Act 24 of 2003...", "The word "and" omitted by Act 42 of
    1953..."), so this searches for the verb near "by"/"ibid" ANYWHERE in the
    checked span, not just at its start (the original narrower check missed
    most real footnotes, which is how IPC s.15 got corrupted).
  - notification/commencement style (India Code's consolidated "as on"
    reprints, e.g. BNS_2023.pdf, which GazetteParser previously had zero
    defence against): "...vide notification No. S.O. 850(E)..., see Gazette
    of India, Extraordinary...".
  - extension/application-history style (IPC's per-page footnotes recording
    which territories a provision was extended to, e.g. "1. The Indian Penal
    Code has been extended to Berar by the Berar Laws Act, 1941 ... and has
    been declared in force in Sonthal Parganas, by ..."). Found 2026-08-10,
    still sitting live in the corpus as IPC s.1's stored text (flagged but
    not fixed during the original 2026-08-09 hand-verification pass, see
    docs/m1-verification.md): this footnote happened to be page-locally
    numbered "1", the exact same collision mechanism as the amendment-style
    footnotes, just a vocabulary neither existing check recognised, so it
    won its dedup-longest contest against the real (much shorter) s.1 body.

Checked against a BOUNDED prefix of a candidate's text (its header line, or
the first ~200 chars) -- NOT the full body -- so a long, genuine operative
section that happens to cite an amending Act deep in its own text (legitimate,
e.g. a savings clause referencing "the corresponding provisions") isn't
misclassified just because the phrase appears somewhere far downstream.
"""
from __future__ import annotations

import re

_AMENDMENT_VERB_RE = re.compile(
    r"\b(?:Ins|Subs|Rep|Repealed|Omitted|Added)\b\.?[^\n]{0,40}?\bby\s+"
    r"(?:Act\s+\d|the\s+A\.?\s*O\.?|s\.?\s*\d)"
    r"|,\s*ibid\b",
    re.IGNORECASE,
)

_NOTIFICATION_RE = re.compile(
    r"\bvide notification\b|\bw\.e\.f\.?\b|\bsee Gazette of India\b|\bS\.O\.\s*\d|\bG\.S\.R\.\s*\d",
    re.IGNORECASE,
)

# "has been extended"/"has been declared" (past-perfect passive) is
# distinctive to this editorial-history phrasing and does not collide with
# genuine operative text, which describes what a provision DOES ("shall
# extend to...", "extends to causing death") rather than a territorial
# application history. "extended/declared under s. N" catches the same
# footnote's later sentences (e.g. "extended under s. 5 of the same Act to
# the Lushai Hills") in case the scan window starts partway through one.
_EXTENSION_HISTORY_RE = re.compile(
    r"\bhas been (?:extended|declared)\b|\b(?:extended|declared) under s\.\s*\d",
    re.IGNORECASE,
)

HEADER_SCAN_CHARS = 220  # a bit past the 200-char title-capture width elsewhere


def is_footnote_shaped(text_prefix: str) -> bool:
    scan = text_prefix[:HEADER_SCAN_CHARS]
    return bool(
        _AMENDMENT_VERB_RE.search(scan)
        or _NOTIFICATION_RE.search(scan)
        or _EXTENSION_HISTORY_RE.search(scan)
    )
