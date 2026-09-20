"""Regression coverage for the CrPC First Schedule Ditto-propagation fix
(docs/evaluation.md): a close-row heuristic firing early was the ORIGINAL
hypothesis for why some "complete" triable_by values were truncated/
corrupted, with Ditto-shaped rows correctly-but-wrongly copying the bad
value forward. Sizing it found the real picture narrower and more
mechanical than that hypothesis: not one cause, four independent, narrow
ones, none of them the close-row heuristic itself --

  (a) `extract_lines()`'s header-noise vocabulary filter dropped a genuine
      DATA line that happened to consist of a single word also in its own
      header word-set ("triable." alone on its own wrapped line).
      Confirmed against source: s.109, s.149. FIXED: minimum 2-token
      requirement before the vocabulary fallback fires.
  (b) `_SECTION_NO_RE` didn't recognise an amendment-bracket-prefixed
      section number ("1[174A") as a new section at all, so the whole of
      174A silently merged into 174's row instead of becoming its own
      addressable section -- the exact same amendment-bracket class of
      defect already found and fixed once this session in a completely
      different parser (section_versions ingestion, "1[376AB."). FIXED:
      `_clean_section_number` tolerates and strips the prefix.
  (c) `_resolve_col`'s Ditto-detection did an exact `in ("ditto", "do")`
      check after stripping only a trailing "." -- a real "Ditto]."
      (amendment-bracket closing after the word, not before) failed that
      check and fell through as a literal, nonsensical value instead of
      resolving via Ditto. FIXED: strip both "." and "]" from the end.
  (d) Column x0-bucketing bleed on specific pages: words land in the wrong
      column bucket. Confirmed against source (the real text is NOT
      scrambled; the extracted text was) -- s.109 (stacked with (a): fixing
      the dropped "triable." line exposed a second, independent bleed of
      "abetted is" into column 4 on the SAME row), s.117, s.178, s.181,
      s.373. FIXED via `_KNOWN_COURT_CORRECTIONS` -- direct value patches,
      not a change to the shared per-page boundary-detection logic every
      row on that page depends on. The blast radius of a general fix there
      isn't worth it for 4-6 rows when the correct values are already
      known and source-verified; see that dict's own comment.

(a)-(c) are narrow, additive parser fixes, confirmed by inspection not to
touch the close-row heuristic or any already-correct Ditto match -- the
`TestUnaffectedRowsStayCorrect` cases below are the direct evidence the
234 previously-correct rows weren't perturbed.

s.358's own second row was ORIGINALLY left deliberately UNRESOLVED, not
guessed at -- see `_KNOWN_UNRESOLVED_SECTION`'s own comment in
parse_crpc_schedule.py. SUPERSEDED 2026-09-20 (docs/evaluation.md): the
"First Schedule transcription" work read s.358 directly from the source PDF
twice, independently, and found it fully coherent -- the garbling was the
automated parser's own artifact, not a real ambiguity in the source. See
`TestS358NowResolvedByHandTranscription` below for the current behaviour;
`_KNOWN_UNRESOLVED_SECTION` itself is left in place in parse_crpc_schedule.py
as a real, working mechanism (not vestigial -- it would still catch an
equivalent case for some OTHER section in the future), just no longer
exercised BY s.358 specifically.

Every expected value below is copied verbatim from the tracked source PDF
(documents/CrPC_1973.pdf, checked directly page by page during sizing),
not inferred from the corrupted extraction -- a regression here is
against real statute-schedule text, not a synthetic fixture.

Every case in this file was `xfail(strict=True)` before the fix landed --
confirmed genuinely failing against the real parser at that point, not
vacuous, and confirmed each fix landed by watching every one flip to an
unexpected pass (XPASS, which `strict=True` turns into a real failure --
the deliberate signal that a marker needs removing). Now plain assertions:
this file's job from here on is to fail again if any of this regresses.
"""
from __future__ import annotations

from scripts.parse_crpc_schedule import (
    PDF_PATH, apply_first_schedule_transcription, apply_known_corrections,
    apply_known_row_replacements, complete_rows, extract_lines, reconstruct_rows,
)

# Deliberately NOT pytest.mark.integration -- that marker's own registered
# meaning (pyproject.toml) is specifically "requires a real Postgres+
# pgvector instance"; this needs no database at all, only the tracked PDF
# already in the repo. Runs in the normal fast suite every time, not
# conditionally.

import pytest


@pytest.fixture(scope="module")
def rows():
    # Matches the real ingestion pipeline (scripts/ingest_offence_
    # attributes.py) exactly -- apply_known_corrections() is what mechanism
    # (d)'s direct value patches depend on; apply_known_row_replacements()
    # is what mechanism (e)'s whole-row replacements (s.374/376) depend on.
    # Without both, this fixture would only exercise what's fixed upstream
    # in reconstruct_rows()/_SECTION_NO_RE itself.
    diags: list[dict] = []
    raw_lines = extract_lines(PDF_PATH, diags)
    rows = reconstruct_rows(raw_lines, diags)
    rows = apply_known_corrections(rows)
    return apply_known_row_replacements(rows)


def _triable_by_values(rows, section: str) -> list[str]:
    return [r.triable_by for r in rows if r.section_number == section]


class TestHeaderFilterAndColumnBleedFixed:
    """(a) alone: s.149. (a)+(d) stacked on the same row: s.109 -- fixing
    the dropped 'triable.' line (a) exposed that 'abetted is' was
    independently bleeding into column 4 on this row too, found by this
    exact test still failing after (a) landed alone, not assumed fixed
    because one known cause was addressed. Original correction dict had
    only s.117/118 for the abetment-family template; s.109/110 were added
    once this test caught the gap.
    """

    def test_s109_abetment_family_antecedent(self, rows):
        assert "Court by which offence abetted is triable." in _triable_by_values(rows, "109")

    def test_s110_ditto_inherits_fixed_antecedent(self, rows):
        assert "Court by which offence abetted is triable." in _triable_by_values(rows, "110")

    def test_s149_unlawful_assembly_antecedent(self, rows):
        assert "The Court by which the offence is triable." in _triable_by_values(rows, "149")

    def test_s150_ditto_inherits_fixed_antecedent(self, rows):
        assert "The Court by which the offence is triable." in _triable_by_values(rows, "150")


class TestColumnBleedPatched:
    """(d): x0-bucketing bleed on specific pages -- the real text was not
    scrambled; the extracted text was. Direct value patches
    (_KNOWN_COURT_CORRECTIONS), not a change to shared boundary-detection
    logic -- see that dict's own comment for why.
    """

    def test_s117_abetting_by_public_antecedent(self, rows):
        assert "Court by which offence abetted is triable." in _triable_by_values(rows, "117")

    def test_s118_ditto_inherits_fixed_antecedent(self, rows):
        assert "Court by which offence abetted is triable." in _triable_by_values(rows, "118")

    def test_s178_refusing_oath_antecedent(self, rows):
        expected = ("The Court in which the offence is committed, subject to the provisions of "
                    "Chapter XXVI; or, if not committed in a Court, any Magistrate.")
        assert expected in _triable_by_values(rows, "178")

    def test_s179_ditto_inherits_fixed_antecedent(self, rows):
        expected = ("The Court in which the offence is committed, subject to the provisions of "
                    "Chapter XXVI; or, if not committed in a Court, any Magistrate.")
        assert expected in _triable_by_values(rows, "179")

    def test_s181_false_statement_antecedent(self, rows):
        assert "Magistrate of the first class." in _triable_by_values(rows, "181")

    def test_s373_buying_minor_antecedent(self, rows):
        assert "Any Magistrate." in _triable_by_values(rows, "373")


class TestAmendmentBracketSectionMergeFixed:
    """(b)+(c): "1[174A" now correctly recognised via _clean_section_number,
    so 174A's own two clauses are their own addressable section instead of
    silently merging into 174's row. The second clause's own court value
    ("Ditto].") additionally needed (c) -- the bracket closes AFTER "Ditto"
    rather than before the trailing period.
    """

    def test_174a_exists_as_its_own_section(self, rows):
        assert any(r.section_number == "174A" for r in rows), (
            "174A's content must be reachable under its own section number, not merged into 174"
        )

    def test_174a_first_clause_court_value(self, rows):
        assert "Magistrate of the first class." in _triable_by_values(rows, "174A")

    def test_174a_second_clause_ditto_resolves(self, rows):
        # Real source: "Ditto]." -- resolves via Ditto to 174A's own value,
        # not a literal, nonsensical string.
        assert "Magistrate of the first class." in _triable_by_values(rows, "174A")


class TestUnaffectedRowsStayCorrect:
    """Direct evidence the narrow fixes don't perturb the rows that
    already parsed correctly before this change. A small, representative
    sample: a plain direct value, a simple Ditto chain, and a section
    adjacent on the same PAGE as a known-bad one (154, right after the
    s.149 family) -- the ones most likely to be accidentally touched by a
    careless fix.

    Checked directly, not assumed: 184-190 (adjacent to the s.181-183
    family, an obvious first choice for a fourth control here) all have
    EMPTY triable_by -- part of the already-known, already-accepted
    44%-incomplete bucket, not this finding's affected rows, and not a
    safe "must stay passing" control either. Confirmed by actually running
    this fixture before picking a value, the same way an earlier draft of
    this test picked s.184 for this same slot, found it already broken for
    an unrelated reason, and had to be corrected before it shipped.
    """

    def test_s148_plain_direct_value_unaffected(self, rows):
        assert "Magistrate of the first class." in _triable_by_values(rows, "148")

    def test_s154_adjacent_to_s149_family_unaffected(self, rows):
        assert "Any Magistrate." in _triable_by_values(rows, "154")

    def test_s371_court_of_session_unaffected(self, rows):
        assert "Court of Session." in _triable_by_values(rows, "371")


class TestS358NowResolvedByHandTranscription:
    """SUPERSEDED 2026-09-20 (docs/evaluation.md, "First Schedule
    transcription" entry) -- this class's own original name was
    TestS358StaysHonestlyUnresolved, and its one test asserted the OPPOSITE
    of what it asserts now: that s.358's garbled "Kidnapping..." second row
    (possibly misattributed from s.363, per _KNOWN_UNRESOLVED_SECTION's own
    comment, still in parse_crpc_schedule.py as a kept-not-deleted piece of
    history) must be excluded from complete_rows(), never shipped with a
    guessed value.

    That protection is still real and still correct for what it was built
    to catch -- but it's no longer the LAST word on s.358, because the
    ambiguity it was guarding against turned out to be resolvable: two
    independent direct reads of the actual source PDF (one by a
    transcription agent, one a same-session follow-up spot-check, both
    landing on the identical clean text) found s.358's real row is fully
    coherent -- "Assault or use of criminal force on grave and sudden
    provocation..." -- with no genuine bleed from s.363 at all. The
    garbling was an artifact of the automated column-position parser, not a
    real ambiguity in the source. s.358 is now one of the 173 sections
    `apply_first_schedule_transcription` replaces outright, so THIS
    fixture (unlike the module-scoped `rows` fixture every other test in
    this file still deliberately uses, which stays on the PRE-transcription
    pipeline on purpose) applies that step too, and asserts the new,
    correct reality instead of the old, honest absence.
    """

    def test_s358_resolves_to_the_real_clean_row_not_the_old_kidnapping_fragment(self):
        diags: list[dict] = []
        raw_lines = extract_lines(PDF_PATH, diags)
        rows = reconstruct_rows(raw_lines, diags)
        rows = apply_known_corrections(rows)
        rows = apply_known_row_replacements(rows)
        rows = apply_first_schedule_transcription(rows)
        complete = complete_rows(rows)

        s358 = [r for r in complete if r.section_number == "358"]
        assert len(s358) == 1, f"expected exactly one resolved row for s.358, got {len(s358)}"
        assert s358[0].offence_description.startswith("Assault or use of criminal force")
        assert not s358[0].offence_description.lower().startswith("kidnapping")
        assert s358[0].cognizable_raw == "Non-cognizable" and s358[0].cognizable is False
        # Bailable/Non-bailable corrected 2026-09-20 (docs/evaluation.md, cognizable/bailable
        # hand-verification entry): the ORIGINAL value here (Bailable/True) was itself wrong --
        # apply_first_schedule_transcription()'s own antecedent-building kept only the FIRST row
        # of a multi-row baseline section (s.354D) as the Ditto-chain antecedent for 355-358,
        # not its LAST -- real Ditto semantics need the value immediately above, which for a
        # multi-row section is its last printed row. Found by the independent cognizable/
        # bailable verification pass disagreeing with this already-shipped value; confirmed
        # against the source page directly, not just by fixing the code and re-running.
        assert s358[0].bailable_raw == "Non-bailable" and s358[0].bailable is False
        assert s358[0].triable_by == "Any Magistrate."
