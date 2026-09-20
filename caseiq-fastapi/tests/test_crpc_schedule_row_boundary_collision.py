r"""Regression coverage for mechanism (e) + the stacked-bracket section
marker (docs/evaluation.md, s.373/374/376 finding). Distinct from, and
found AFTER, the Ditto-propagation patch (tests/test_crpc_schedule_ditto_
corruption.py) -- deliberately investigated and reported separately per
instruction, since the last two times a "known mechanism" framing went in
early it turned out wrong (the close heuristic wasn't the Ditto cause;
s.109 had a stacked SECOND mechanism nobody checked for).

THE FAILURE, and why it's more serious than a corruption cosmetic issue:
s.373's real triable_by ("Any Magistrate.") splits across a row-boundary
-- "Any" lands in 373's own buffer before it closes; "Magistrate." lands
on the immediately following raw line, which carries no column-0 section
number of its own, so it gets folded into whichever row is now open
(374) instead of the row it actually continues. This ALONE would just be
another truncation -- but it collided with a second, independent defect
on the exact same physical lines: the base Rape entry's own section
number is printed as "1[ 2[376" (TWO stacked amendment-footnote bracket
markers, since IPC 376 has been amended twice -- Act 13/2013, Act
22/2018 -- and the PDF's own typesetting keeps both still-open markers
visible). The single-bracket tolerance already built for 174A
(`(?:\d+\[)?`, zero-or-ONE) doesn't match a STACKED prefix at all, so
"376" was never recognised as a section boundary -- its real content
(three independent sub-clauses: base rape, rape by a person in
authority, rape on a woman under sixteen) had nowhere of its own to
land, and got absorbed into the already-corrupted "374" row instead.

CONFIRMED LIVE IN PRODUCTION (2026-09-18), not just a parser curiosity:
before this fix, TWO rows survived complete_rows() under section_
number="374" -- one with 373's stolen/truncated court value, one whose
offence_description began "Rape. or fine, or both. Rigorous
imprisonment not less than 10 years..." -- REAL Rape (IPC 376) content,
confidently and specifically misclassified under "Unlawful compulsory
labour" (IPC 374). Removed from production directly (a targeted DELETE,
backed up first) before this parser fix even existed, per instruction:
wrong data is strictly worse than missing data, and shouldn't wait for
the fix to land.

CONFIRMED PRE-EXISTING, not introduced by this session's earlier (a)/(b)/
(c) patch: the old parser (crpc-schedule-v3, before ANY of this session's
fixes) produces the identical wrong s.373/374 output -- checked directly
by running the pre-session version of parse_crpc_schedule.py against the
same PDF. This has been live and wrong since at least the original
ingestion (2026-09-01), in exactly the same shape, not a regression from
today's other work.

MECHANISM (e) CHECKED FOR PREVALENCE, not assumed to be a one-off or a
systemic pattern -- a scan (scripts/_scratch_mechanism_e_scan.py, one-off,
not committed) of every row-close in the whole schedule for "closed via
new-section-detected while its own court column doesn't look finished"
found 7 candidates; cross-referenced against every already-fixed/already-
known case, exactly ONE (s.373/374) was a genuinely new, unaddressed
instance. s.228 was a false positive of the scan's own narrow detection
vocabulary (its value was already fully correct, verified directly) --
not a real defect. Reported as contained, not systemic, on that basis.

BRACKET PATTERN CHECKED FOR A GENERAL FORM: the real vocabulary of every
bracketed col0 token in this schedule (15 distinct values) shows the
general shape is "zero or more digit+bracket prefixes, optionally
separated by whitespace" -- not a third special case. _SECTION_NO_RE's
`(?:\d+\[\s*)*` (was `(?:\d+\[)?`) covers all 15 directly. The SAME
general-form gap was checked against legacy_parser.py (the parser
responsible for the earlier, separately-fixed IPC 376AB/174A finding) --
that parser's own bracket-stripping preprocessing is single-pass and
would also fail on a stacked prefix, but no LIVE triggered instance was
found there (IPC's own body text for s.376 has no bracket at all; a
synthetic single-bracket test there -- s.376DA -- initially looked
missing but was a false signal from an incomplete test reproduction, not
a real gap, once the real preprocessing step was correctly replicated).
Named as a latent, not live, structural weakness in that OTHER parser --
distinct in severity from this file's own confirmed-live findings, not
fixed here since nothing currently depends on it being fixed.
"""
from __future__ import annotations

from scripts.parse_crpc_schedule import (
    PDF_PATH, apply_known_corrections, apply_known_row_replacements, complete_rows,
    extract_lines, reconstruct_rows,
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


def _values_for(rows, section: str) -> list[dict]:
    return [
        {"triable_by": r.triable_by, "offence_description": r.offence_description,
         "cognizable": r.cognizable, "bailable": r.bailable}
        for r in rows if r.section_number == section
    ]


class TestMechanismEShortColumnAcrossRowBoundary:
    """s.373's real "Any Magistrate." must not lose its second word to the
    next row -- fixed via _KNOWN_COURT_CORRECTIONS (same mechanism (d)
    shape, since a single-field correction is sufficient here: 373's own
    offence_description was never wrong, only its court value).
    """

    def test_s373_court_value_is_not_truncated(self, rows):
        values = _values_for(rows, "373")
        assert any(v["triable_by"] == "Any Magistrate." for v in values)


class TestStackedBracketSectionRecognised:
    """"1[ 2[376" must resolve to section "376", not merge into 374 or
    vanish. _SECTION_NO_RE's generalised `(?:\\d+\\[\\s*)*` covers this.
    """

    def test_376_exists_as_its_own_section(self, rows):
        assert any(r.section_number == "376" for r in rows), (
            "376's content must be reachable under its own section number, not merged into 374"
        )

    def test_376_not_merged_into_374(self, rows):
        s374 = _values_for(rows, "374")
        assert not any("Rape" in v["offence_description"] for v in s374), (
            "IPC 376 (Rape) content must not appear under section 374 (Unlawful compulsory labour)"
        )


class TestS374WholeRowCorrect:
    """s.374's real content ("Unlawful compulsory labour.") must be
    reachable, complete, and correctly classified -- not the stolen/
    truncated court value, not merged with unrelated Rape text.
    """

    def test_s374_offence_is_unlawful_compulsory_labour(self, rows):
        values = _values_for(rows, "374")
        assert any(v["offence_description"].startswith("Unlawful compulsory labour.") for v in values)

    def test_s374_offence_includes_its_own_punishment(self, rows):
        values = _values_for(rows, "374")
        target = next(v for v in values if v["offence_description"].startswith("Unlawful compulsory labour."))
        assert "Imprisonment for 1 year, or fine, or both." in target["offence_description"]

    def test_s374_court_value_is_its_own_not_stolen(self, rows):
        # CORRECTED 2026-09-20 (docs/evaluation.md, cognizable/bailable hand-verification
        # entry): "Court of Session." was itself the WRONG value here -- this test's own
        # name is about the court value not being stolen from a neighbouring row, and the
        # original hand-verification for s.374 (this file's own subject) had in fact
        # transcribed 373's chained court value instead of 374's own. Confirmed directly
        # against page 214: 374's own column 6 prints "Any Magistrate.", a fresh value, not
        # "Ditto" chaining from 373's "Court of Session."
        values = _values_for(rows, "374")
        target = next(v for v in values if v["offence_description"].startswith("Unlawful compulsory labour."))
        assert target["triable_by"] == "Any Magistrate."

    def test_s374_classification_correct(self, rows):
        # Bailable corrected 2026-09-20 (docs/evaluation.md, cognizable/bailable
        # hand-verification entry): originally recorded as Non-bailable/False, itself wrong
        # -- confirmed directly against page 214, column 5 prints "Bailable", a fresh value.
        values = _values_for(rows, "374")
        target = next(v for v in values if v["offence_description"].startswith("Unlawful compulsory labour."))
        assert target["cognizable"] is True
        assert target["bailable"] is True

    def test_s374_survives_complete_rows(self, rows):
        complete = complete_rows(rows)
        s374 = [r for r in complete if r.section_number == "374"]
        assert len(s374) == 1
        assert s374[0].offence_description.startswith("Unlawful compulsory labour.")

    def test_s374_no_longer_carries_bogus_rape_row(self, rows):
        complete = complete_rows(rows)
        s374 = [r for r in complete if r.section_number == "374"]
        assert not any("Rape" in r.offence_description for r in s374)


class TestS376ThreeSubClauses:
    """376 is genuinely THREE independent sub-clauses in the source: base
    rape, rape by a person in authority, rape on a woman under sixteen --
    each with its own real offence/punishment/classification. All three
    must be reachable, none merged or truncated, none rejected by the
    length-based garbling heuristic (they are legitimately long, not
    garbled -- ground truth overrides that proxy for these hand-verified
    rows specifically, see complete_rows()'s own comment).
    """

    def test_376_base_clause_present(self, rows):
        values = _values_for(rows, "376")
        assert any(v["offence_description"].startswith("Rape.") for v in values)

    def test_376_person_in_authority_clause_present(self, rows):
        values = _values_for(rows, "376")
        assert any(v["offence_description"].startswith("Rape by a police officer") for v in values)

    def test_376_under_sixteen_clause_present(self, rows):
        values = _values_for(rows, "376")
        assert any(v["offence_description"].startswith("Persons committing offence of rape on a woman under "
                                                          "sixteen years of age.") for v in values)

    def test_376_all_three_clauses_triable_by_court_of_session(self, rows):
        values = _values_for(rows, "376")
        assert len(values) == 3
        assert all(v["triable_by"].startswith("Court of Session.") for v in values)

    def test_376_all_three_clauses_survive_complete_rows_despite_length(self, rows):
        complete = complete_rows(rows)
        s376 = [r for r in complete if r.section_number == "376"]
        assert len(s376) == 3
        # At least one is genuinely long -- confirms the length exemption
        # for known-good rows is actually doing something, not vacuous.
        assert any(len(r.offence_description) > 250 for r in s376)

    def test_376_classification_correct_for_all_three(self, rows):
        complete = complete_rows(rows)
        s376 = [r for r in complete if r.section_number == "376"]
        assert all(r.cognizable is True and r.bailable is False for r in s376)
