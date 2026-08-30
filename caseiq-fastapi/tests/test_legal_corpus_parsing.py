"""Regression guard for the Schedule/section-number collision bug
(app/legal_corpus/parsing/schedule_exclusion.py): CrPC's First Schedule
tabulates rows by IPC section number, which collide with CrPC's own section
numbering. Before the fix, the (usually longer) Schedule row won
dedup-keep-longest against the real section, silently replacing real
procedural text with unrelated Schedule content -- confirmed to have
happened to CrPC s.126 and s.276, found 2026-08-14 via validate.py's
content-completeness check while building the golden eval set.

Depends on documents/CrPC_1973.pdf, which is gitignored (not committed) --
skips rather than fails if it isn't present locally, same convention as
tests/integration/conftest.py skipping when no test DB is reachable.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.legal_corpus.parsing.registry import PARSERS
from app.legal_corpus.validate import validate

CRPC_PDF = Path(__file__).resolve().parent.parent / "documents" / "CrPC_1973.pdf"

# A CrPC section body containing the Schedule's own "Ditto" column-repeat
# marker several times over is a reliable, structural signal that a
# candidate is (First Schedule) table content, not section text -- real
# section prose has no occasion to repeat that word.
_SCHEDULE_MARKER_RE = re.compile(r"\bDitto\b")

# Two accepted sections legitimately contain "Ditto" repeatedly and are NOT
# instances of the schedule-collision defect this test guards against --
# confirmed by direct content inspection 2026-08-15, both excluded here by
# name (not by raising the occurrence threshold, which would just as easily
# hide a real recurrence):
#   - s.320 "Compounding of offences" is itself a large table (which
#     sections of the IPC may be compounded, by whom) as its OWN genuine,
#     correct content -- confirmed starting "320. Compounding of
#     offences.—(1) The offences punishable under the sections of the
#     Indian Penal Code..." Not a Schedule row; never touched by
#     schedule_exclusion.py.
#   - s.484 (the Act's LAST section) absorbs trailing non-section document
#     matter -- including the real First Schedule that follows it -- purely
#     because nothing bounds the final section's end besides EOF. This is
#     the pre-existing "last-section absorption" limitation already tracked
#     in docs/m1-verification.md ("Known limitations" section), a
#     distinct defect from schedule-row-wins-dedup: no collision occurs
#     (there's no *other* real s.484 the Schedule text could have beaten),
#     so schedule_exclusion.py's collision-based approach doesn't apply and
#     isn't expected to catch it.
_KNOWN_NON_COLLISIONS = {"320", "484"}


@pytest.mark.skipif(not CRPC_PDF.exists(), reason=f"{CRPC_PDF} not present (gitignored source document)")
def test_no_crpc_section_contains_schedule_table_markers():
    report = PARSERS["CrPC"].parse(CRPC_PDF)
    result = validate("CrPC", report)

    offenders = {
        s.section_number: len(_SCHEDULE_MARKER_RE.findall(s.section_text))
        for s in result.accepted
        if s.section_number not in _KNOWN_NON_COLLISIONS
        and len(_SCHEDULE_MARKER_RE.findall(s.section_text)) >= 2
    }
    assert not offenders, (
        f"section(s) contain Schedule-table markers ('Ditto' repeated), meaning the Schedule "
        f"region's row candidates won dedup against the real section again: {offenders}"
    )


@pytest.mark.skipif(not CRPC_PDF.exists(), reason=f"{CRPC_PDF} not present (gitignored source document)")
def test_crpc_126_and_276_are_the_real_procedural_sections():
    """The two sections actually confirmed corrupted before the fix --
    pinned to their real content, not just "no Ditto", so a future change
    that swaps in some OTHER wrong content (unlikely to contain "Ditto")
    still fails this test."""
    report = PARSERS["CrPC"].parse(CRPC_PDF)
    result = validate("CrPC", report)
    accepted_by_number = {s.section_number: s for s in result.accepted}

    assert "126" in accepted_by_number
    assert accepted_by_number["126"].section_text.startswith("126. Procedure.")

    assert "276" in accepted_by_number
    assert accepted_by_number["276"].section_text.startswith("276. Record in trial before Court of Session.")
