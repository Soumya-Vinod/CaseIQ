"""C1a (a) (docs/caseiq-industry-readiness.md): a section whose First Schedule
rows disagree shows no classification instead of one arbitrary branch.

Runs on the real parser output from the tracked PDFs, like the other
schedule tests -- no database. On 2026-10-10 the CrPC pipeline's output was
checked equal to production's offence_attributes on (section, cognizable,
bailable, triable_by) for all 479 rows, so the sets pinned here are the
sets production suppresses. The serialisers themselves are covered against
a real database in tests/integration/test_cognizability_lookup.py.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pytest

# parse_bnss_schedule imports parse_crpc_schedule as a top-level module, the
# same way the ingest scripts run it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from app.services.offence_attribute_consistency import (  # noqa: E402
    base_section_number, rows_disagree,
)
from scripts import parse_bnss_schedule, parse_crpc_schedule  # noqa: E402

# Measured against production 2026-10-10: 61 multi-row sections, 27 of them
# disagreeing on raw cognizable / bailable / triable_by.
EXPECTED_CONDITIONAL_IPC = {
    "118", "119", "120", "120B", "153", "171F", "193", "201", "211", "221", "222",
    "225", "225A", "235", "354A", "354C", "354D", "363A", "370A", "376", "389",
    "451", "454", "467", "474", "505", "506",
}
# Differ only by a First Schedule markup artifact in the court string. Raw
# comparison suppresses them on purpose (keeps "Court of Session.]" off the
# screen until C1b) -- normalising them away would make this test pass by
# loosening the check.
BRACKET_ARTIFACT_SECTIONS = {"354A", "370A", "376"}

# BNSS sections whose sub-rows differ in classification. parse_bnss_schedule's
# complete_rows drops their merged row, so they reach the UI as "no row in our
# classification data" rather than one branch -- the honest behaviour C1a (a)
# gives CrPC. Nothing designed that as a suppression rule, so it's pinned here.
BNSS_CONDITIONAL_DROPPED = ["77", "78(2)", "303(2)", "338", "339"]


@pytest.fixture(scope="module")
def crpc_groups():
    rows = parse_crpc_schedule.complete_rows(parse_crpc_schedule.pipeline_rows([]))
    groups = defaultdict(list)
    for r in rows:
        groups[r.section_number].append(r)
    return groups


@pytest.fixture(scope="module")
def bnss_rows():
    diags: list[dict] = []
    raw = parse_bnss_schedule.reconstruct_rows(
        parse_bnss_schedule.extract_lines(parse_bnss_schedule.PDF_PATH, diags), diags,
    )
    return raw, parse_bnss_schedule.complete_rows(raw)


class TestCrPCConditionalSectionsSuppress:
    def test_exactly_the_27_disagreeing_sections_suppress(self, crpc_groups):
        suppressed = {s for s, g in crpc_groups.items() if rows_disagree(g)}
        assert suppressed == EXPECTED_CONDITIONAL_IPC

    def test_multi_row_count_unchanged(self, crpc_groups):
        assert sum(1 for g in crpc_groups.values() if len(g) > 1) == 61

    @pytest.mark.parametrize("section", sorted(BRACKET_ARTIFACT_SECTIONS))
    def test_bracket_artifact_sections_suppress(self, crpc_groups, section):
        group = crpc_groups[section]
        # Same classification on every row; only the court string's markup differs.
        assert len({(r.cognizable, r.bailable) for r in group}) == 1
        assert rows_disagree(group)

    def test_ipc_222_suppresses(self, crpc_groups):
        # The motivating case: bailable under a <10-year sentence, not under life.
        group = crpc_groups["222"]
        assert {r.bailable for r in group} == {True, False}
        assert rows_disagree(group)


class TestCleanMultiRowSectionStillDisplays:
    def test_ipc_370_six_agreeing_rows_display(self, crpc_groups):
        group = crpc_groups["370"]
        assert len(group) == 6
        assert not rows_disagree(group)

    def test_single_row_sections_never_suppress(self, crpc_groups):
        assert not any(rows_disagree(g) for g in crpc_groups.values() if len(g) == 1)


class TestBNSSConditionalSectionsStayNoData:
    @pytest.mark.parametrize("section", BNSS_CONDITIONAL_DROPPED)
    def test_present_in_parse_but_dropped(self, bnss_rows, section):
        raw, clean = bnss_rows
        # Pins the mechanism, not just the outcome: the section IS in the
        # schedule (so it's not simply missing from the PDF), its merged raw
        # text contradicts itself, and complete_rows drops it.
        merged = [r for r in raw if r.section_number == section]
        assert merged, f"BNS {section} not found in the raw parse"
        assert any(
            _says_both(r.cognizable_raw, "cognizable") or _says_both(r.bailable_raw, "bailable")
            for r in merged
        )
        assert section not in {r.section_number for r in clean}

    def test_no_bnss_section_is_multi_row(self, bnss_rows):
        # If a parser change ever starts keeping BNSS sub-rows as separate rows,
        # this fails, and C1a (a)'s cross-row check becomes the thing that
        # protects BNSS too -- re-check before shipping that change.
        _, clean = bnss_rows
        counts: dict[str, int] = defaultdict(int)
        for r in clean:
            counts[r.section_number] += 1
        assert max(counts.values()) == 1



class TestBNSSubsectionGrouping:
    """Sub-sections grouped at lookup (2026-10-10). The BNSS parser's output
    equals production's BNS rows on (section, cognizable, bailable, court), so
    these are the outcomes production shows once the lookup groups."""

    @pytest.mark.parametrize("stored, base", [
        ("222(a)", "222"), ("351(2)", "351"), ("125", "125"),
        # Never collapsed: IPC letter-suffixed numbering has no parentheses.
        ("376AB", "376AB"), ("120B", "120B"), ("376A", "376A"),
        # Only ONE trailing group, and only digits or lowercase letters.
        ("111(2)(a)", "111(2)"), ("80(A)", "80(A)"), ("80(2a)", "80(2a)"),
    ])
    def test_base_section_number(self, stored, base):
        assert base_section_number(stored) == base

    @pytest.fixture(scope="class")
    def bnss_groups(self, bnss_rows):
        _, clean = bnss_rows
        groups = defaultdict(list)
        for r in clean:
            groups[base_section_number(r.section_number)].append(r)
        return groups

    def test_bns_222_displays(self, bnss_groups):
        group = bnss_groups["222"]
        assert sorted(r.section_number for r in group) == ["222(a)", "222(b)"]
        assert not rows_disagree(group)

    def test_bns_351_is_conditional(self, bnss_groups):
        group = bnss_groups["351"]
        assert sorted(r.section_number for r in group) == ["351(2)", "351(3)", "351(4)"]
        assert len({r.triable_by for r in group}) > 1  # court differs by sub-section
        assert rows_disagree(group)

    def test_bns_125_stored_under_both_keys_agrees(self, bnss_groups):
        group = bnss_groups["125"]
        assert sorted(r.section_number for r in group) == ["125", "125(a)", "125(b)"]
        assert not rows_disagree(group)

    def test_counts_moving_off_no_data(self, bnss_groups):
        # The 82 BNS sections stored only under sub-section numbers: before the
        # fix every one said "No row in our classification data".
        only_suffixed = {
            k: g for k, g in bnss_groups.items()
            if all(base_section_number(r.section_number) != r.section_number for r in g)
        }
        assert len(only_suffixed) == 82
        assert sum(1 for g in only_suffixed.values() if not rows_disagree(g)) == 50
        assert sum(1 for g in only_suffixed.values() if rows_disagree(g)) == 32

    def test_crpc_rows_have_no_subsection_suffix(self, crpc_groups):
        # So the grouping can't merge anything on the IPC side.
        assert all(base_section_number(s) == s for s in crpc_groups)


def _says_both(raw: str, word: str) -> bool:
    low = raw.lower()
    return f"non-{word}" in low and any(
        low[i - 4:i] != "non-" for i in _find_all(low, word)
    )


def _find_all(text: str, word: str):
    i = text.find(word)
    while i != -1:
        yield i
        i = text.find(word, i + 1)
