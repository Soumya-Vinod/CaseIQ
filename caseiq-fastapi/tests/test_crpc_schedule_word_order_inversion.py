r"""Regression coverage for s.133/134's word-order inversion (docs/
evaluation.md) -- found scoping the "20 concatenation rows", but a
genuinely DIFFERENT, unrelated mechanism from everything else found this
session, so it gets its own file rather than being folded into either the
Ditto-propagation or row-boundary-collision test files.

THIS IS OUR BUG, NOT THE SOURCE DOCUMENT'S -- verified by checking the
actual word coordinates, not assumed either way. A first pass here
initially guessed this was a pdfplumber/source-rendering quirk (the same
category as the genuine "extent to N years" PDF typo already documented
elsewhere); checking the real x0/top values before writing that down
showed it was wrong, and it was corrected before being reported.

On the physical line carrying s.133's court value, "Magistrate" (x0=
500.52) and "of" (x0=537.12) are 0.37pt apart in `top` (414.84 vs
414.47) -- comfortably inside extract_lines()'s own 2.5pt line-clustering
tolerance, so pdfplumber correctly considers them part of the same visual
line, and x0 order (true reading order) says "Magistrate" comes first.
But `extract_lines()`'s own word sort --
`words.sort(key=lambda w: (round(w["top"]), w["x0"]))` -- uses ROUNDED
top as the PRIMARY key, computed over the WHOLE PAGE before clustering
ever runs: round(414.84)=415 and round(414.47)=414 land in different
integer buckets despite being well within the same line, so the page-
wide pre-sort places "of" (bucket 414) ahead of "Magistrate" (bucket
415) in final word order. pdfplumber's own coordinates are correct
throughout -- the bug is squarely in this project's own two-step
sort-then-cluster logic, at a rounding boundary neither step alone would
have hit.

s.134 has no independent instance of this -- it Ditto-inherits 133's own
(then-wrong, now-fixed) value, same shape as every other Ditto-dependent
correction this session (109/110, 117/118).

FIXED via _KNOWN_COURT_CORRECTIONS (a direct value patch), not a change
to extract_lines()'s shared sort/cluster logic -- the same "patch, don't
touch shared logic that every row in the schedule depends on, for one
confirmed instance" reasoning as every other correction in that dict. A
general fix (cluster first on raw top, sort each cluster by x0 after) is
possible and named in the dict's own comment, not built here.
"""
from __future__ import annotations

from scripts.parse_crpc_schedule import (
    PDF_PATH, apply_known_corrections, apply_known_row_replacements, extract_lines, reconstruct_rows,
)

# Deliberately NOT pytest.mark.integration -- no database dependency, only
# the tracked PDF already in the repo.

import pytest


@pytest.fixture(scope="module")
def rows():
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = apply_known_corrections(rows)
    return apply_known_row_replacements(rows)


def _triable_by_values(rows, section: str) -> list[str]:
    return [r.triable_by for r in rows if r.section_number == section]


class TestWordOrderInversionFixed:
    def test_s133_court_value_reads_in_correct_word_order(self, rows):
        assert "Magistrate of the first class." in _triable_by_values(rows, "133")

    def test_s133_scrambled_value_no_longer_present(self, rows):
        # The exact wrong value this fix removes -- asserting its absence
        # too, not just the presence of the right one, since a row that
        # accidentally produced BOTH would still pass the test above.
        assert "of Magistrate the first class." not in _triable_by_values(rows, "133")

    def test_s134_ditto_inherits_fixed_antecedent(self, rows):
        assert "Magistrate of the first class." in _triable_by_values(rows, "134")
