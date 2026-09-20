"""Regression coverage for the CrPC First Schedule hand transcription
(docs/evaluation.md, 2026-09-20 "First Schedule transcription" entry):
scripts/_crpc_first_schedule_transcription.py + apply_first_schedule_
transcription() in scripts/parse_crpc_schedule.py, taking the schedule from
222/395 to 395/395 complete sections.

Provenance: 4 parallel subagents each read a page range directly from PDF
page images (not automated text extraction) and reported the 6-column data
for their assigned sections; two small gaps between the ranges (195/199/
200/201/203 and 404/406/407/408/409/413/418/419/423/424) were filled by a
same-session direct read of the missing pages. Every value is transcribed
from the source, not inferred -- any cell that couldn't be read with
confidence was left unverifiable rather than guessed (see the
"__UNVERIFIABLE__" handling in resolve_first_schedule_transcription()).

Two defects were found and fixed along the way, both worth a dedicated
regression test here rather than only a mention in docs/evaluation.md:

  1. s.358's second row was previously excluded from complete_rows() as
     KNOWN-BAD (_KNOWN_UNRESOLVED_SECTION) on the theory that its garbled
     text might be genuinely misattributed from s.363's own row in the
     source. Two independent direct reads of the source PDF found the real
     text is fully coherent -- the garbling was the automated column-
     position parser's own artifact, not a real source ambiguity. See
     tests/test_crpc_schedule_ditto_corruption.py's
     TestS358NowResolvedByHandTranscription for the direct test of this;
     this file's job is the broader invariants around it.

  2. complete_rows()'s own exemption for _FIRST_SCHEDULE_TRANSCRIBED
     sections (added so the transcribed replacement rows, some of which
     combine multiple real sub-clauses past _MAX_SANE_OFFENCE_LEN, aren't
     rejected for length) is keyed on section number alone, with no
     awareness of whether the substitution has actually happened yet. Fed
     PRE-transcription rows, it let 9 sections' OLD, still-garbled rows
     (non-empty but wrong triable_by: 116, 120B, 175, 201, 225A, 358, 404,
     498A, 511) pass as "complete" -- which silently caused
     apply_first_schedule_transcription() to treat them as already-good
     antecedents and skip replacing them entirely, leaving the garbled text
     in the final output. Fixed by excluding _ALL_RAW's own section set
     from the rows apply_first_schedule_transcription() feeds into
     complete_rows() when computing its own antecedent baseline -- none of
     the 173 sections' pre-transcription rows are ever legitimate
     antecedents, that they need transcribing at all is exactly why
     complete_rows() exempts them in the first place.
     TestNoSectionSilentlyMaskedByExemption below is the direct regression
     test for this -- it would have caught it, and will catch a
     reintroduction.

A third, separate finding is NOT a bug in this transcription and is not
tested here: s.202, itself NOT one of the 173 (it was already "complete"
per complete_rows() before this work), has an empty cognizable_raw/
bailable_raw despite the real printed values being "Ditto"/"Ditto" --
complete_rows() never catches this because it only validates triable_by.
This was chain-repaired (_CHAIN_REPAIR_ANTECEDENTS in
_crpc_first_schedule_transcription.py) ONLY for the purposes of correctly
resolving s.203's own Ditto chain through it -- s.202's own stored row is
deliberately left untouched, since fixing pre-existing "complete" data
is out of scope for this transcription. TestChainRepairScopedCorrectly
below asserts exactly that boundary: 203 resolves correctly, 202 itself
stays exactly as buggy as it started.
"""
from __future__ import annotations

import pytest

from scripts._crpc_first_schedule_transcription import _ALL_RAW
from scripts.parse_crpc_schedule import (
    PDF_PATH,
    _KNOWN_ROW_REPLACEMENTS,
    _structurally_complete_rows,
    apply_first_schedule_transcription,
    apply_known_corrections,
    apply_known_row_replacements,
    extract_lines,
    reconstruct_rows,
)

# Deliberately NOT pytest.mark.integration -- no database needed, only the
# tracked PDF already in the repo.


@pytest.fixture(scope="module")
def pre_transcription_rows():
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = apply_known_corrections(rows)
    return apply_known_row_replacements(rows)


@pytest.fixture(scope="module")
def post_transcription_rows(pre_transcription_rows):
    return apply_first_schedule_transcription(pre_transcription_rows)


class TestTranscriptionSourceShape:
    """Invariants about _ALL_RAW itself, independent of the parser pipeline."""

    def test_exactly_173_sections(self):
        assert len(_ALL_RAW) == 173

    def test_disjoint_from_known_row_replacements(self):
        assert set(_ALL_RAW).isdisjoint(_KNOWN_ROW_REPLACEMENTS)

    def test_no_empty_raw_specs(self):
        for section, specs in _ALL_RAW.items():
            assert specs, f"section {section} has an empty spec list"
            for offence, cog, bail, court in specs:
                assert offence.strip(), f"section {section} has a blank offence text"


class TestFullCoverageAfterTranscription:
    def test_395_of_395_sections_complete(self, post_transcription_rows):
        # _structurally_complete_rows, not the public complete_rows() -- this fixture
        # doesn't run apply_cognizable_bailable_verification(), so most rows' cognizable_raw/
        # bailable_raw are still empty at this pipeline stage; complete_rows() now also
        # requires those (2026-09-20 tightening) and would undercount here for a reason
        # unrelated to what THIS test checks (triable_by/offence coverage from the
        # transcription itself). See docs/evaluation.md and tests/
        # test_crpc_cognizable_bailable_verification.py for the post-cog/bail-fix number
        # (373/395), which is the right place to assert the public complete_rows() count.
        complete = _structurally_complete_rows(post_transcription_rows)
        distinct_sections = {r.section_number for r in post_transcription_rows}
        complete_sections = {r.section_number for r in complete}
        assert len(distinct_sections) == 395
        assert complete_sections == distinct_sections

    def test_every_transcribed_section_present_with_real_text(self, post_transcription_rows):
        by_section: dict[str, list] = {}
        for r in post_transcription_rows:
            by_section.setdefault(r.section_number, []).append(r)

        for section, specs in _ALL_RAW.items():
            rows_for_section = by_section.get(section, [])
            assert len(rows_for_section) == len(specs), (
                f"section {section}: expected {len(specs)} row(s), got {len(rows_for_section)}"
            )
            for row, (expected_offence, _, _, _) in zip(rows_for_section, specs):
                assert row.offence_description == expected_offence
                assert row.triable_by.strip()


class TestNoSectionSilentlyMaskedByExemption:
    """The 9 sections whose pre-transcription row had a non-empty (but
    wrong) triable_by, and so were at risk of being silently skipped by
    complete_rows()'s own _FIRST_SCHEDULE_TRANSCRIBED exemption firing on
    stale data (finding #2 in the module docstring). Confirmed by direct
    inspection of pre_transcription_rows that these 9, and only these 9,
    have this property -- not an arbitrary sample.
    """

    _AFFECTED = ["116", "120B", "175", "201", "225A", "358", "404", "498A", "511"]

    def test_affected_sections_have_nonempty_pretranscription_triable_by(
        self, pre_transcription_rows
    ):
        # Confirms the precondition that made this a real risk still holds --
        # if this ever goes empty for one of these, the exemption can no
        # longer mask it and the section can be dropped from this list.
        by_section: dict[str, list] = {}
        for r in pre_transcription_rows:
            by_section.setdefault(r.section_number, []).append(r)
        for section in self._AFFECTED:
            assert any(r.triable_by.strip() for r in by_section[section]), (
                f"section {section} no longer has a non-empty pre-transcription "
                "triable_by -- it may no longer need this specific protection, "
                "but check before removing it from _AFFECTED"
            )

    def test_affected_sections_resolve_to_transcribed_text_not_old_text(
        self, pre_transcription_rows, post_transcription_rows
    ):
        old_offences: dict[str, set[str]] = {}
        for r in pre_transcription_rows:
            old_offences.setdefault(r.section_number, set()).add(r.offence_description)

        new_offences: dict[str, set[str]] = {}
        for r in post_transcription_rows:
            new_offences.setdefault(r.section_number, set()).add(r.offence_description)

        for section in self._AFFECTED:
            expected = {spec[0] for spec in _ALL_RAW[section]}
            assert new_offences[section] == expected, (
                f"section {section} did not resolve to its transcribed text"
            )
            # None of the new rows' text should be any of the stale old rows' text
            assert new_offences[section].isdisjoint(old_offences[section])


class TestChainRepairScopedCorrectly:
    """s.202 (not one of the 173) has a pre-existing, out-of-scope bug --
    empty cognizable_raw/bailable_raw despite real values "Ditto"/"Ditto".
    _CHAIN_REPAIR_ANTECEDENTS fixes this ONLY for s.203's own Ditto-chain
    resolution, not for s.202's own stored row.
    """

    def test_s202_own_row_unchanged_bug_still_present(self, post_transcription_rows):
        s202 = [r for r in post_transcription_rows if r.section_number == "202"]
        assert len(s202) == 2
        assert s202[0].cognizable_raw == "" and s202[0].cognizable is None
        assert s202[0].bailable_raw == "" and s202[0].bailable is None

    def test_s203_resolves_correctly_despite_s202s_bug(self, post_transcription_rows):
        s203 = [r for r in post_transcription_rows if r.section_number == "203"]
        assert len(s203) == 1
        assert s203[0].cognizable_raw == "Non-cognizable" and s203[0].cognizable is False
        assert s203[0].bailable_raw == "Bailable" and s203[0].bailable is True
        assert s203[0].triable_by == "Any Magistrate."


class TestNoRegressionOnPreviouslyCompleteSections:
    """Every section that was already complete before this transcription
    (i.e. NOT one of the 173) must come out of
    apply_first_schedule_transcription() byte-for-byte identical --
    apply_first_schedule_transcription() should only ever touch its own 173
    target sections.
    """

    def test_previously_complete_sections_are_untouched(
        self, pre_transcription_rows, post_transcription_rows
    ):
        # _structurally_complete_rows, not complete_rows() -- see
        # test_395_of_395_sections_complete's own comment above for why.
        before_complete = [
            r for r in _structurally_complete_rows(pre_transcription_rows)
            if r.section_number not in _ALL_RAW
        ]
        before_by_section: dict[str, list] = {}
        for r in before_complete:
            before_by_section.setdefault(r.section_number, []).append(r)

        after_by_section: dict[str, list] = {}
        for r in _structurally_complete_rows(post_transcription_rows):
            after_by_section.setdefault(r.section_number, []).append(r)

        assert len(before_by_section) == 222, (
            "expected exactly 222 previously-complete, non-transcribed sections "
            f"as the regression baseline, got {len(before_by_section)}"
        )

        for section, old_rows in before_by_section.items():
            new_rows = after_by_section.get(section)
            assert new_rows is not None, f"section {section} missing after transcription"
            old_tuples = sorted(
                (r.offence_description, r.cognizable_raw, r.bailable_raw, r.triable_by)
                for r in old_rows
            )
            new_tuples = sorted(
                (r.offence_description, r.cognizable_raw, r.bailable_raw, r.triable_by)
                for r in new_rows
            )
            assert old_tuples == new_tuples, f"section {section} changed unexpectedly"
