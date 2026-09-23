"""Regression coverage for the CrPC First Schedule row-count-mismatch hand transcription
(docs/evaluation.md, "row-mismatch transcription" entry): scripts/_crpc_row_mismatch_transcription.py
+ apply_row_mismatch_transcription() in scripts/parse_crpc_schedule.py, fixing the 40 sections (6
over-split, 34 under-split, 3 of the 34 previously missing their section entirely: 153AA, 353, 363)
that `complete_rows()`'s 2026-09-20 tightening (requiring cognizable_raw/bailable_raw, not just
triable_by) had excluded outright -- these were never merely incomplete, their stored
offence_description was visibly word-scrambled across all four fields, not just missing a value.

Provenance: 3 parallel subagents each read a cluster of the already-mapped page ranges directly from
PDF page images (not automated text extraction). A blind 25% sample (10 of 40 sections) was
independently re-read by fresh agents with no exposure to the primary values, specifically to catch a
same-page shared misread the cross-check below structurally cannot. 3 of 10 disagreed with the primary
read; all 3 settled by a direct tie-break read of the source page, not a coin flip -- see
scripts/_crpc_row_mismatch_transcription.py's own module docstring for exactly which three and how
each was resolved.

Three things worth a dedicated regression test here, not just a docs/evaluation.md mention:

  1. s.175 moved out of scripts/_crpc_first_schedule_transcription.py's own _ALL_RAW into this
     module's -- its old single-row entry there never modeled the real second printed row (found by
     cross-referencing that module's row count against this pass's own printed-row ground truth).
     TestS175MovedCorrectly below is the direct regression test for that move. It wasn't the only
     one: 11 MORE sections in that module (158, 173, 174, 177, 187, 188, 213, 214, 467, 471, 474)
     had the identical defect -- see that module's own comments at each point of removal, and
     TestTranscriptionSourceShape.test_disjoint_from_known_row_replacements_and_first_schedule_
     transcription below.

  2. The precedence risk named going in: once this pass fixes a section's row count,
     apply_cognizable_bailable_verification() naturally stops treating it as mismatched and
     re-verifies its cognizable_raw/bailable_raw against ITS OWN, separately-read data -- the same
     thing that already happens today, unremarked, for every one of the 173 sections this pass's
     sibling module covers. TestOrderDependenceSafe is the direct assertion for this -- refined
     while writing it, not assumed correct on the first try: the naive "downstream pass must never
     CHANGE a cognizable/bailable value this pass already resolved" turned out to be the WRONG
     invariant (this pass's own antecedent baseline is necessarily incomplete at its pipeline stage,
     so the downstream pass correctly overwriting a placeholder None with a real value is exactly
     the intended design, not a bug) -- see that class's own docstring for what's actually asserted
     instead: fields only this pass owns stay untouched, and cognizable/bailable end up either
     resolved or genuinely conditional, never silently wrong.

  3. Spot-verification layer 1: TestCrossCheckAgainstIndependentCognizableBailableRead compares the
     FINAL pipeline output (after apply_cognizable_bailable_verification() has run) against
     _crpc_cognizable_bailable_verification.py's own independently-read data for these 40 sections --
     a free, real second-source check, not a restatement of the same read.
"""
from __future__ import annotations

import copy

import pytest

from scripts._crpc_cognizable_bailable_verification import (
    _ALL_RAW as _COG_BAIL_ALL_RAW, compute_row_count_mismatches, resolve_cognizable_bailable,
)
from scripts._crpc_first_schedule_transcription import _ALL_RAW as _FIRST_SCHEDULE_TRANSCRIBED
from scripts._crpc_row_mismatch_transcription import _ALL_RAW
from scripts.parse_crpc_schedule import (
    PDF_PATH,
    _KNOWN_ROW_REPLACEMENTS,
    _structurally_complete_rows,
    apply_cognizable_bailable_verification,
    apply_first_schedule_transcription,
    apply_known_corrections,
    apply_known_row_replacements,
    apply_row_mismatch_transcription,
    extract_lines,
    reconstruct_rows,
)

# Deliberately NOT pytest.mark.integration -- no database needed, only the
# tracked PDF already in the repo.


@pytest.fixture(scope="module")
def pre_row_mismatch_rows():
    # apply_row_mismatch_transcription() now runs BEFORE apply_first_schedule_transcription() --
    # reversed from this module's own first version, see apply_row_mismatch_transcription()'s own
    # docstring in parse_crpc_schedule.py for why. This fixture is named "pre_row_mismatch_rows" for
    # historical continuity with its own test names below, not because it precedes the 173-pass any
    # more -- it precedes THIS pass, which now runs first.
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = apply_known_corrections(rows)
    return apply_known_row_replacements(rows)


@pytest.fixture(scope="module")
def post_row_mismatch_rows(pre_row_mismatch_rows):
    return apply_row_mismatch_transcription(copy.deepcopy(pre_row_mismatch_rows))


@pytest.fixture(scope="module")
def post_full_pipeline_rows(post_row_mismatch_rows):
    # Adds apply_first_schedule_transcription() then apply_cognizable_bailable_verification() on
    # top -- the real next two steps in the actual pipeline (parse_crpc_schedule.py's own __main__,
    # ingest_offence_attributes.py), in the real order. This is the fixture that reflects what
    # production actually ends up storing for these 40 sections.
    rows = apply_first_schedule_transcription(copy.deepcopy(post_row_mismatch_rows))
    return apply_cognizable_bailable_verification(rows)


class TestTranscriptionSourceShape:
    """Invariants about _ALL_RAW itself, independent of the parser pipeline."""

    def test_exactly_40_sections(self):
        assert len(_ALL_RAW) == 40

    def test_6_over_split_34_under_split(self, pre_row_mismatch_rows):
        mismatches = compute_row_count_mismatches(pre_row_mismatch_rows)
        ours = {s: v for s, v in mismatches.items() if s in _ALL_RAW}
        over = [s for s, v in ours.items() if v["shape"] == "over_split"]
        under = [s for s, v in ours.items() if v["shape"] == "under_split"]
        assert len(over) == 6, over
        assert len(under) == 34, under

    def test_disjoint_from_known_row_replacements_and_first_schedule_transcription(self):
        assert set(_ALL_RAW).isdisjoint(_KNOWN_ROW_REPLACEMENTS)
        assert set(_ALL_RAW).isdisjoint(_FIRST_SCHEDULE_TRANSCRIBED)

    def test_no_empty_raw_specs(self):
        for section, specs in _ALL_RAW.items():
            assert specs, f"section {section} has an empty spec list"
            for offence, cog, bail, court in specs:
                assert offence.strip(), f"section {section} has a blank offence text"
                assert cog.strip() and bail.strip() and court.strip(), (
                    f"section {section} has a blank classification cell"
                )

    def test_no_unverifiable_cells(self):
        # Unlike the 173/cognizable-bailable passes, every cell in this 40-section pass was read
        # with confidence -- the 3 first-pass disagreements were all settled by a direct source-page
        # tie-break, not left unresolved. Asserted explicitly so a future addition to this module
        # that DOES need to abstain doesn't silently ship a placeholder instead.
        for section, specs in _ALL_RAW.items():
            for offence, cog, bail, court in specs:
                assert "__UNVERIFIABLE__" not in (offence, cog, bail, court), section


class TestFullCoverageAfterTranscription:
    def test_every_target_section_present_with_correct_row_count(self, post_row_mismatch_rows):
        by_section: dict[str, list] = {}
        for r in post_row_mismatch_rows:
            by_section.setdefault(r.section_number, []).append(r)

        for section, specs in _ALL_RAW.items():
            rows_for_section = by_section.get(section, [])
            assert len(rows_for_section) == len(specs), (
                f"section {section}: expected {len(specs)} row(s), got {len(rows_for_section)}"
            )
            for row, spec in zip(rows_for_section, specs):
                assert row.offence_description == spec[0]
                assert row.triable_by.strip()

    def test_previously_missing_sections_now_addressable(self, post_row_mismatch_rows):
        # 153AA/353/363 had ZERO rows under their own section_number before this pass -- their
        # content was fully swallowed into a neighbouring section. Confirms they now exist as their
        # own addressable sections, not just that _ALL_RAW claims to cover them.
        by_section: dict[str, list] = {}
        for r in post_row_mismatch_rows:
            by_section.setdefault(r.section_number, []).append(r)
        for section in ("153AA", "353", "363"):
            assert len(by_section.get(section, [])) == 1
            assert by_section[section][0].offence_description.strip()


class TestS175MovedCorrectly:
    """s.175 moved out of _crpc_first_schedule_transcription.py's own _ALL_RAW into this module's --
    see that module's own comment at the point of removal. Its old entry there was a single row that
    never modeled the real second printed clause.
    """

    def test_175_has_two_rows_not_one(self, post_row_mismatch_rows):
        rows_175 = [r for r in post_row_mismatch_rows if r.section_number == "175"]
        assert len(rows_175) == 2
        assert rows_175[0].offence_description == _ALL_RAW["175"][0][0]
        assert rows_175[1].offence_description == _ALL_RAW["175"][1][0]
        # The real second clause's own text -- proof it's not just a duplicate of row 1.
        assert "Court of Justice" in rows_175[1].offence_description

    def test_175_not_in_first_schedule_transcription_module_anymore(self):
        assert "175" not in _FIRST_SCHEDULE_TRANSCRIBED
        assert "175" in _ALL_RAW


class TestOrderDependenceSafe:
    """The precedence risk named before transcribing started: apply_cognizable_bailable_
    verification() runs AFTER this pass, and once these 40 sections' row counts agree with what's
    printed, they naturally drop out of that function's own mismatch-exclusion set -- meaning it
    re-verifies their cognizable_raw/bailable_raw against its OWN, separately-read data. This is the
    same thing that already happens, unremarked, for the 173 sections apply_first_schedule_
    transcription() covers -- not a new interaction invented for this pass.

    IMPORTANT, found while writing this test, not assumed going in: "the downstream pass must never
    CHANGE a cognizable/bailable value this pass already set" is the WRONG invariant to assert for
    cognizable/bailable specifically. This pass's own internal Ditto-chain antecedent baseline is
    built from `_structurally_complete_rows(rows)` at a pipeline stage BEFORE apply_cognizable_
    bailable_verification() has run -- meaning plenty of legitimate antecedent sections still have
    empty cognizable_raw/bailable_raw at that point (they're not patched until the very next step),
    so this pass's own resolved cognizable/bailable for a "Ditto"-chained row is frequently a
    correct-but-uninformative None, not a wrong answer -- it's exactly WHY apply_cognizable_bailable_
    verification() exists as a separate, later, full-independent-read pass: to supply the real value
    this pass's own limited antecedent view cannot. Confirmed directly: running this pass alone and
    diffing against the independent read showed dozens of (None, None)-shaped "disagreements" for
    exactly this reason, not a defect in either pass.

    What actually matters, and what's asserted here instead: (1) fields ONLY this pass owns
    (offence_description, triable_by, row count) must be byte-identical before and after the
    downstream pass runs -- if those changed, that WOULD be a genuine silent overwrite outside the
    downstream pass's own scope; (2) after the downstream pass runs, cognizable/bailable must be
    FULLY resolved (non-None) for all 40 sections -- the safety property that actually matters is
    that the downstream pass successfully takes over and finishes the job, not that it leaves this
    pass's own incomplete intermediate resolution untouched.
    """

    def test_offence_and_court_fields_untouched_by_downstream_pass(
        self, post_row_mismatch_rows, post_full_pipeline_rows
    ):
        before_by_section: dict[str, list] = {}
        for r in post_row_mismatch_rows:
            before_by_section.setdefault(r.section_number, []).append(r)

        after_by_section: dict[str, list] = {}
        for r in post_full_pipeline_rows:
            after_by_section.setdefault(r.section_number, []).append(r)

        for section in _ALL_RAW:
            before_rows = before_by_section[section]
            after_rows = after_by_section[section]
            assert len(before_rows) == len(after_rows), (
                f"section {section}: row count changed by the downstream pass"
            )
            for before_row, after_row in zip(before_rows, after_rows):
                assert before_row.offence_description == after_row.offence_description, section
                assert before_row.triable_by == after_row.triable_by, section

    def test_cognizable_bailable_resolved_or_genuinely_conditional(self, post_full_pipeline_rows):
        # A None bool is only acceptable when the RAW text itself is a genuine conditional
        # ("according as..."/"if...") -- same test _resolve_col itself uses to decide a value is
        # conditional rather than guessed. This is real, printed, statutory behaviour (e.g. 110's
        # own classification genuinely depends on whatever offence was abetted, not a fixed value
        # -- it Ditto-chains from 109's own equally-conditional base clause) -- matches the SAME
        # pattern already accepted elsewhere in this schedule for 109/117/120B/149/511. Anything
        # else left None is a genuine unresolved antecedent, not a conditional clause, and IS a bug.
        import re
        conditional_re = re.compile(r"\bif\b|\baccording as\b", re.I)

        by_section: dict[str, list] = {}
        for r in post_full_pipeline_rows:
            by_section.setdefault(r.section_number, []).append(r)

        unresolved = [
            (section, row.offence_description[:50], row.cognizable_raw, row.bailable_raw)
            for section in _ALL_RAW
            for row in by_section[section]
            if (row.cognizable is None and not conditional_re.search(row.cognizable_raw))
            or (row.bailable is None and not conditional_re.search(row.bailable_raw))
        ]
        assert not unresolved, (
            "sections left with a genuinely unresolved (not conditional) cognizable/bailable after "
            f"the full pipeline: {unresolved}"
        )

    def test_all_40_sections_leave_the_mismatch_set(self, post_row_mismatch_rows):
        # Confirms the mechanism this whole test class depends on actually engages: if a section
        # were still reported as mismatched after this pass, apply_cognizable_bailable_
        # verification() would SKIP re-verifying it entirely, and the test above would be checking
        # nothing for that section.
        mismatches = compute_row_count_mismatches(post_row_mismatch_rows)
        assert set(_ALL_RAW).isdisjoint(mismatches), (
            f"sections still mismatched after this pass: {set(_ALL_RAW) & set(mismatches)}"
        )


class TestCrossCheckAgainstIndependentCognizableBailableRead:
    """Spot-verification layer 1 (free, covers all 40, cognizable/bailable only -- see
    scripts/_crpc_row_mismatch_transcription.py's own module docstring for why this doesn't replace
    the blind re-read layer): _crpc_cognizable_bailable_verification.py's own _ALL_RAW already holds
    an independently-read cognizable/bailable pair for every one of these 40 sections -- that's
    literally how the row-count mismatch was first detected. Comparing the FINAL pipeline output
    (after apply_cognizable_bailable_verification() has run -- see TestOrderDependenceSafe's own
    docstring for why that function, not this pass's own intermediate resolution, is the right thing
    to compare) against that independent dataset's own resolution is a genuine second-source check on
    apply_cognizable_bailable_verification()'s own work for these 40 sections, not a restatement of
    the same read.
    """

    def test_final_cognizable_bailable_agrees_with_independent_source(self, post_full_pipeline_rows):
        # resolve_cognizable_bailable(mismatched_sections=set()) -- passing an empty set, not the
        # real mismatch set, so NONE of the 40 are excluded from its own returned dict. The Ditto-
        # chain WALK itself doesn't change based on the exclusion set (every section is always
        # walked, for correct chain-continuity into whatever follows it) -- only which sections make
        # it into the OUTPUT does, so this doesn't change what values get computed, only whether we
        # can see them for the 40 sections that function normally hides.
        cog_bail_resolved = resolve_cognizable_bailable(set())

        by_section: dict[str, list] = {}
        for r in post_full_pipeline_rows:
            by_section.setdefault(r.section_number, []).append(r)

        disagreements = []
        for section in _ALL_RAW:
            if section not in _COG_BAIL_ALL_RAW:
                continue  # not covered by the independent cog/bail-only read at all -- nothing to cross-check
            ours = [(r.cognizable, r.bailable) for r in by_section[section]]
            theirs = [(cog_bool, bail_bool) for _, cog_bool, _, bail_bool in cog_bail_resolved[section]]
            if len(ours) != len(theirs):
                disagreements.append((section, "row count differs", ours, theirs))
                continue
            for o, t in zip(ours, theirs):
                if o != t:
                    disagreements.append((section, "value differs", o, t))
        assert not disagreements, (
            "final pipeline output disagrees with the independent cognizable/bailable read:\n"
            + "\n".join(str(d) for d in disagreements)
        )


class TestNoRegressionOnPreviouslyCompleteSections:
    """Every section not one of these 40 (and not the 172 the sibling 173-module owns) must come out
    of apply_row_mismatch_transcription() byte-for-byte identical.
    """

    def test_previously_complete_sections_are_untouched(self, pre_row_mismatch_rows, post_row_mismatch_rows):
        before_complete = [
            r for r in _structurally_complete_rows(pre_row_mismatch_rows)
            if r.section_number not in _ALL_RAW
        ]
        before_by_section: dict[str, list] = {}
        for r in before_complete:
            before_by_section.setdefault(r.section_number, []).append(r)

        after_by_section: dict[str, list] = {}
        for r in _structurally_complete_rows(post_row_mismatch_rows):
            after_by_section.setdefault(r.section_number, []).append(r)

        for section, old_rows in before_by_section.items():
            new_rows = after_by_section.get(section)
            assert new_rows is not None, f"section {section} missing after row-mismatch transcription"
            old_tuples = sorted(
                (r.offence_description, r.cognizable_raw, r.bailable_raw, r.triable_by)
                for r in old_rows
            )
            new_tuples = sorted(
                (r.offence_description, r.cognizable_raw, r.bailable_raw, r.triable_by)
                for r in new_rows
            )
            assert old_tuples == new_tuples, f"section {section} changed unexpectedly"
