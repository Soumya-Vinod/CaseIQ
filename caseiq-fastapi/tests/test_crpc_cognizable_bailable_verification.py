"""Regression coverage for the CrPC First Schedule cognizable/bailable
hand-verification pass (docs/evaluation.md, 2026-09-20 "Cognizable/bailable
hand-verification" entry): complete_rows() only ever validated triable_by,
so 192 of the 395 sections it accepted as "complete" had no usable
cognizable and/or bailable value at all. This closes that gap the same way
the First Schedule transcription closed the triable_by gap -- values read
directly off the source PDF page images, never inferred or guessed.

Two real defects were found and fixed along the way, both worth a
dedicated regression test here, not just a docs/evaluation.md mention:

  1. Row-count mismatches (scripts/_crpc_cognizable_bailable_verification.py,
     compute_row_count_mismatches()): 38 of 397 sections read have a
     mismatch between what's actually printed and what the parser stores --
     the same row-boundary/close-heuristic defect class already documented
     repeatedly in test_crpc_schedule_ditto_corruption.py, here affecting
     cognizable/bailable specifically. These sections are excluded from the
     patch (would mean inventing or guessing which stored row a printed
     clause's data belongs to) and reported separately -- a cognizable/
     bailable coverage claim is 395 minus this excluded set, not 395.

  2. apply_first_schedule_transcription()'s own antecedent-building bug
     (found via this pass's independent page-read disagreeing with an
     already-shipped value): `complete_by_section` kept only the FIRST row
     of a multi-row baseline section as the Ditto-chain antecedent, not its
     LAST -- real Ditto semantics need the value immediately above, which
     for a multi-row section is its last printed row. This silently shipped
     a wrong bailable value for s.355-358 (all Ditto-chained through
     s.354D) to production during THIS session's own earlier re-ingestion.
     Fixed with a further refinement: an OVER-SPLIT baseline section (the
     parser stores more rows than are actually printed, e.g. s.110) has a
     phantom "last row" that isn't real content, so over-split sections
     still use their first (real) row -- confirmed by re-running the full
     corpus diff, not assumed safe from the s.354D case alone.
"""
from __future__ import annotations

import copy

import pytest

from scripts._crpc_cognizable_bailable_verification import (
    _ALL_RAW, compute_row_count_mismatches, resolve_cognizable_bailable,
)
from scripts.parse_crpc_schedule import (
    PDF_PATH, _structurally_complete_rows, apply_cognizable_bailable_verification,
    apply_first_schedule_transcription, apply_known_corrections, apply_known_row_replacements,
    complete_rows, extract_lines, reconstruct_rows,
)

# Deliberately NOT pytest.mark.integration -- no database needed, only the
# tracked PDF already in the repo.


@pytest.fixture(scope="module")
def pre_verification_rows():
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = apply_known_corrections(rows)
    rows = apply_known_row_replacements(rows)
    return apply_first_schedule_transcription(rows)


@pytest.fixture(scope="module")
def post_verification_rows(pre_verification_rows):
    # apply_cognizable_bailable_verification() mutates ScheduleRow objects in
    # place (matching how the real pipeline calls it) -- deep-copy first so
    # this module-scoped fixture doesn't retroactively corrupt the shared
    # pre_verification_rows fixture other tests still read as "before" state.
    return apply_cognizable_bailable_verification(copy.deepcopy(pre_verification_rows))


class TestVerificationSourceShape:
    def test_covers_the_full_first_schedule_page_range(self):
        # Every page 196-223 was read; the exact count drifts slightly from
        # 395 (397) because a couple of printed sub-clauses (e.g. 153AA)
        # aren't addressable as their own parser section at all -- read for
        # chain-continuity, not expected to reconcile 1:1 with the schedule's
        # own section count.
        assert len(_ALL_RAW) >= 370

    def test_no_empty_raw_specs(self):
        for section, specs in _ALL_RAW.items():
            assert specs, f"section {section} has an empty spec list"
            for cog, bail in specs:
                assert cog.strip(), f"section {section} has a blank cognizable value"
                assert bail.strip(), f"section {section} has a blank bailable value"


class TestRowCountMismatchesReportedNotGuessed:
    def test_mismatch_count_within_expected_range(self, pre_verification_rows):
        mismatches = compute_row_count_mismatches(pre_verification_rows)
        # 38 confirmed this session; asserting a bounded range (not an exact
        # pin) so a legitimate future data addition doesn't need a hair-
        # trigger test update, while still catching a large unexpected swing.
        assert 30 <= len(mismatches) <= 50

    def test_every_mismatch_has_a_shape(self, pre_verification_rows):
        mismatches = compute_row_count_mismatches(pre_verification_rows)
        for section, info in mismatches.items():
            assert info["shape"] in ("over_split", "under_split")
            assert info["parser_rows"] != info["printed_rows"]

    def test_s195a_is_under_split(self, pre_verification_rows):
        mismatches = compute_row_count_mismatches(pre_verification_rows)
        assert mismatches["195A"]["shape"] == "under_split"

    def test_s110_is_over_split(self, pre_verification_rows):
        mismatches = compute_row_count_mismatches(pre_verification_rows)
        assert mismatches["110"]["shape"] == "over_split"

    def test_mismatched_sections_not_patched(self, pre_verification_rows, post_verification_rows):
        mismatches = compute_row_count_mismatches(pre_verification_rows)
        before_by_section: dict[str, list] = {}
        for r in complete_rows(pre_verification_rows):
            before_by_section.setdefault(r.section_number, []).append(r)
        after_by_section: dict[str, list] = {}
        for r in complete_rows(post_verification_rows):
            after_by_section.setdefault(r.section_number, []).append(r)

        for section in mismatches:
            before_rows = before_by_section.get(section, [])
            after_rows = after_by_section.get(section, [])
            before_vals = [(r.cognizable_raw, r.bailable_raw) for r in before_rows]
            after_vals = [(r.cognizable_raw, r.bailable_raw) for r in after_rows]
            assert before_vals == after_vals, f"section {section} was patched despite being a row-count mismatch"


class TestCleanSectionsPatchedCorrectly:
    def test_strict_coverage_is_367_not_395(self, post_verification_rows):
        # complete_rows() now requires all three fields (2026-09-20 tightening) -- 395 was
        # the triable_by-only number; 22 sections whose only row(s) are row-count mismatches
        # (real content, not guessed at, just not attachable to a correct stored row) drop
        # out entirely. This is the deliberately-NOT-395 number docs/evaluation.md's
        # "395/395 measured the wrong field" entry is about -- asserting it explicitly here
        # so a future change that silently pads this back to 395 fails loudly.
        #
        # Was 373. Now 367: this fixture doesn't run apply_row_mismatch_transcription() (docs/
        # evaluation.md, row-mismatch-transcription entry), so the 12 sections moved out of
        # _crpc_first_schedule_transcription.py's _ALL_RAW (see tests/
        # test_crpc_first_schedule_transcription.py's own test_exactly_161_sections) are no
        # longer resolved at this checkpoint either. Of those 12: 6 (158, 173, 174, 467, 471, 474)
        # were counted here before this session's work via that module's own now-superseded
        # single-row entries -- these are exactly the 6 the count drops by. The other 6 split as
        # 5 (177, 187, 188, 213, 214) already excluded before this session even started (already
        # among the pre-existing 22), unaffected either way, and 175, which stays counted
        # regardless -- its stale pre-fix row still structurally qualifies (just with wrong,
        # garbled values). Confirmed directly by diffing the exact section set, not inferred from
        # the arithmetic alone. The real, correct number lives in tests/
        # test_crpc_row_mismatch_transcription.py, against the fixture that actually runs the
        # pass that now owns these 12.
        complete = complete_rows(post_verification_rows)
        assert len(set(r.section_number for r in complete)) == 367

    def test_previously_empty_rows_mostly_filled(self, pre_verification_rows, post_verification_rows):
        # _structurally_complete_rows, not complete_rows() -- complete_rows() now filters
        # out any row still missing cognizable/bailable entirely, so counting "still empty"
        # rows through it would trivially always be zero. _structurally_complete_rows keeps
        # the triable_by-only signal this test actually needs (does the row exist at all).
        before = _structurally_complete_rows(pre_verification_rows)
        after = _structurally_complete_rows(post_verification_rows)
        before_empty = sum(1 for r in before if not r.cognizable_raw.strip() or not r.bailable_raw.strip())
        after_empty = sum(1 for r in after if not r.cognizable_raw.strip() or not r.bailable_raw.strip())
        # Was 211, then 213 (mid-session), now 208. 211->213: adding apply_row_mismatch_
        # transcription()'s own section set to _structurally_complete_rows()'s length-check
        # exemption is a shared change (it has to apply everywhere that function is called, not
        # just after the new pass has run) -- it let through 2 rows here whose garbled pre-fix
        # offence_description exceeds 250 chars (s.119's first row, s.222's second row), both
        # previously excluded entirely, both with genuinely empty cognizable_raw. 213->208: moving
        # 12 sections' entries out of _crpc_first_schedule_transcription.py (see tests/
        # test_crpc_first_schedule_transcription.py's own test_exactly_161_sections) removed 5 of
        # them (177, 187, 188, 213, 214) from the exemption they'd been getting via THAT module's
        # membership -- without any exemption at this checkpoint (this fixture doesn't run the new
        # pass that now owns them), their long/malformed pre-fix rows are excluded entirely by the
        # length check rather than counted here as "empty", so they simply disappear from this
        # list rather than reappearing in it. Confirmed directly by diffing this exact fixture's
        # output against each prior baseline: exactly the rows named above account for each step,
        # nothing else changes.
        assert before_empty == 208
        assert after_empty < before_empty
        # every row still empty after the fix must belong to a reported mismatch
        mismatches = compute_row_count_mismatches(pre_verification_rows)
        still_empty_sections = {
            r.section_number for r in after
            if not r.cognizable_raw.strip() or not r.bailable_raw.strip()
        }
        assert still_empty_sections <= set(mismatches)

    def test_s202_resolves_via_repaired_antecedent(self, post_verification_rows):
        s202 = [r for r in complete_rows(post_verification_rows) if r.section_number == "202"]
        assert len(s202) == 1
        assert s202[0].cognizable_raw == "Non-cognizable" and s202[0].cognizable is False
        assert s202[0].bailable_raw == "Bailable" and s202[0].bailable is True


class TestAntecedentLastRowFix:
    """s.354D's own second row (the real, LAST printed row) has
    bailable=Non-bailable/False; its first row has Bailable/True.
    s.355-358 all Ditto-chain their bailable value from whatever came
    immediately before them -- which is s.354D's LAST row, not its first.
    """

    def test_s355_through_358_use_354ds_last_row_as_antecedent(self, post_verification_rows):
        complete = complete_rows(post_verification_rows)
        by_section: dict[str, list] = {}
        for r in complete:
            by_section.setdefault(r.section_number, []).append(r)

        for section in ("355", "356", "357", "358"):
            rows_for_section = by_section[section]
            assert len(rows_for_section) == 1
            assert rows_for_section[0].bailable_raw == "Non-bailable"
            assert rows_for_section[0].bailable is False

    def test_over_split_baseline_section_still_uses_first_row(self, post_verification_rows):
        # s.111/113/114 Ditto-chain cognizable from s.110's antecedent. s.110
        # is over-split (parser stores a phantom empty second row) -- using
        # its real FIRST row keeps these resolved to the genuine conditional
        # text, not empty.
        complete = complete_rows(post_verification_rows)
        by_section: dict[str, list] = {}
        for r in complete:
            by_section.setdefault(r.section_number, []).append(r)

        for section in ("111", "113", "114"):
            rows_for_section = by_section[section]
            assert len(rows_for_section) == 1
            assert rows_for_section[0].cognizable_raw == (
                "According as offence abetted is cognizable or non-cognizable."
            )

    def test_no_stray_amendment_bracket_leaks_into_inherited_triable_by(self, post_verification_rows):
        # s.354D's OWN triable_by legitimately ends "]" (closes a multi-row
        # amendment span) -- real content for that row, but not something
        # s.355 (which just says "Ditto" for its court) should inherit.
        complete = complete_rows(post_verification_rows)
        by_section: dict[str, list] = {}
        for r in complete:
            by_section.setdefault(r.section_number, []).append(r)

        assert by_section["354D"][-1].triable_by == "Any Magistrate.]"
        for section in ("355", "356", "357", "358"):
            assert not by_section[section][0].triable_by.endswith("]"), (
                f"section {section} inherited a stray amendment-bracket artifact"
            )


class TestNoRegressionOnAlreadyCorrectSections:
    def test_previously_resolved_booleans_unchanged(self, pre_verification_rows, post_verification_rows):
        """Checks the RESOLVED boolean, not the raw text -- reading every row (not just
        the empty ones) also cleans up column-bleed garbage in already-resolving raw text
        (e.g. "years, Cognizable" -> "Cognizable") for dozens of sections, which is a real,
        intended improvement from this pass, not a regression. A semantic (boolean) change
        is the only thing that would actually indicate something broke.
        """
        mismatches = compute_row_count_mismatches(pre_verification_rows)

        before_complete = [
            r for r in complete_rows(pre_verification_rows)
            if r.cognizable_raw.strip() and r.bailable_raw.strip()
            and r.section_number not in mismatches
        ]
        before_by_section: dict[str, list] = {}
        for r in before_complete:
            before_by_section.setdefault(r.section_number, []).append(r)

        after_by_section: dict[str, list] = {}
        for r in complete_rows(post_verification_rows):
            after_by_section.setdefault(r.section_number, []).append(r)

        def _sort_key(pair):
            return (pair[0] is None, pair[0], pair[1] is None, pair[1])

        regressed = []
        for section, old_rows in before_by_section.items():
            new_rows = after_by_section.get(section, [])
            old_vals = sorted(((r.cognizable, r.bailable) for r in old_rows), key=_sort_key)
            new_vals = sorted(((r.cognizable, r.bailable) for r in new_rows), key=_sort_key)
            if old_vals != new_vals:
                regressed.append((section, old_vals, new_vals))

        # Known, deliberate, source-verified exceptions -- each traced to a specific root
        # cause during this pass, not just accepted because the diff was large:
        #  - s.355-358: antecedent-building bug (kept the first row of a multi-row baseline
        #    section as the Ditto antecedent, not the last) -- fixed this same session.
        #  - s.374: _KNOWN_ROW_REPLACEMENTS's own original hand-verification had bailable
        #    wrong (Non-bailable instead of the real Bailable) -- confirmed against page 214.
        #  - s.117/229A/352: the OLD raw text had column-bleed garbage that accidentally
        #    still matched a keyword regex (e.g. "Non- bailable" with a stray line-wrap
        #    space missed the `\bnon-bailable\b` check, fell through to matching the bare
        #    word "bailable", resolving True instead of the real False) -- confirmed against
        #    this pass's own clean, garbage-free read of the same cells.
        #  - s.475/476/477/477A: all Ditto-chain from s.474, which THIS pass correctly
        #    flagged as under-split (the original 173-section transcription merged s.474's
        #    two real printed rows into one, with only the merged row's own value feeding
        #    the OLD chain). s.474 itself stays excluded from patching (out of scope, a
        #    structural row-merge, not a cognizable/bailable defect) but downstream sections
        #    correctly inherit its TRUE last-row value now instead of the old merged one.
        known_exceptions = {"355", "356", "357", "358", "374", "117", "229A", "352",
                             "475", "476", "477", "477A"}
        unexpected = [r for r in regressed if r[0] not in known_exceptions]
        assert not unexpected, f"unexpected boolean regressions: {unexpected}"
