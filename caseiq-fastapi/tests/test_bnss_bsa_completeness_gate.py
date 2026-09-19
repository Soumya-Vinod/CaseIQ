"""Direct coverage for the completeness check that actually runs against
BNSS/BSA -- `app.legal_corpus.validate`'s `range_fallback` branch.

Added 2026-09-20 (docs/evaluation.md) after a scoping pass went looking for
"is there any way to detect a missing/absorbed section in BNSS/BSA, given
neither has an extractable ToC" and found the answer was already built:
`validate()` already falls back to a contiguous `{1..highest_section_number}`
expected set (from `documents/provenance.json`) whenever no ToC can be
bounded, and `enforce_gate` already treats a gap anywhere in that range --
including the highest number itself being absent -- as a blocking
`ValidationGateError`, exactly like a real ToC's own expected set would be.

What was actually missing, and what this file closes: **zero direct test
coverage of that branch** -- nothing here before this file exercised
`range_fallback` except a full, real ingestion run against the actual BNSS/
BSA PDFs, which is exactly how a mismatched parser-engine mistake (testing
`GazetteParser()`'s default pdfplumber engine instead of BSA's actual
configured pymupdf engine, which produced a false "section 170 is missing"
finding during this same scoping pass) went unnoticed until traced by hand.
A synthetic, fast, deterministic test that can't depend on which engine
happened to be used is the guard that class of mistake needed.

Scoped narrowly to what `range_fallback` actually claims to be sound for
(see its own comment in validate.py): a freshly-enacted act with contiguous
numbering and no lettered insertions -- i.e. BNSS/BSA specifically, never
IPC/CrPC. `test_toc_present_never_reaches_range_fallback` below is the
guard against that boundary being crossed by accident.
"""
from __future__ import annotations

import pytest

from app.legal_corpus.parsing.base import ParseReport, RawSection
from app.legal_corpus.validate import ValidationGateError, enforce_gate, validate


def _section(number: str, text: str = "Real operative provision text, long enough to pass the near-empty and short-flag thresholds comfortably on its own without tripping either one." * 2) -> RawSection:
    return RawSection(section_number=number, section_title=None, section_text=text)


def _report(act: str, sections: list[RawSection]) -> ParseReport:
    # full_text="" -- no ToC heading anywhere -- is exactly BNSS/BSA's real
    # shape (see gazette_parser.py's own corrected docstring): forces
    # extract_expected_entries() to return None, which is what makes
    # validate() fall through to range_fallback in the first place.
    return ParseReport(act=act, parser_name="GazetteParser", parser_version="10",
                        source_path="<test>", sections=sections, full_text="")


def _patch_highest(monkeypatch, act: str, highest: int) -> None:
    monkeypatch.setattr(
        "app.legal_corpus.validate.get_highest_section_number",
        lambda a: highest if a == act else None,
    )


def test_range_fallback_used_when_no_toc_and_highest_known(monkeypatch):
    _patch_highest(monkeypatch, "TESTACT", 5)
    sections = [_section(str(n)) for n in range(1, 6)]
    result = validate("TESTACT", _report("TESTACT", sections))

    assert result.expected_source == "range_fallback"
    assert result.expected_numbers == frozenset({"1", "2", "3", "4", "5"})


def test_complete_contiguous_sections_pass_the_gate(monkeypatch):
    _patch_highest(monkeypatch, "TESTACT", 5)
    sections = [_section(str(n)) for n in range(1, 6)]
    result = validate("TESTACT", _report("TESTACT", sections))

    enforce_gate(result)  # must not raise


def test_missing_highest_section_number_is_caught(monkeypatch):
    # The exact shape of the false alarm this scoping pass chased: the
    # act's own LAST section silently absent. Only sections 1-4, highest
    # claimed is 5 -- section 5 was never parsed at all.
    _patch_highest(monkeypatch, "TESTACT", 5)
    sections = [_section(str(n)) for n in range(1, 5)]
    result = validate("TESTACT", _report("TESTACT", sections))

    assert result.missing == ["5"]
    with pytest.raises(ValidationGateError) as exc_info:
        enforce_gate(result)
    assert "5" in str(exc_info.value)


def test_mid_sequence_gap_is_caught(monkeypatch):
    # A section missing from the MIDDLE of the range, not the end -- the
    # other half of "sequence gap" the scoping pass named as a candidate
    # signal, distinct from the highest-number case above.
    _patch_highest(monkeypatch, "TESTACT", 5)
    sections = [_section(str(n)) for n in (1, 2, 4, 5)]  # 3 missing
    result = validate("TESTACT", _report("TESTACT", sections))

    assert result.missing == ["3"]
    with pytest.raises(ValidationGateError):
        enforce_gate(result)


def test_toc_present_never_reaches_range_fallback(monkeypatch):
    # IPC/CrPC-shaped input (a real ToC) must use the ToC's own expected
    # set, never the range fallback -- range_fallback's "contiguous, no
    # lettered insertions" assumption is false for those acts (124A, 498A,
    # ...), which is exactly why this guard matters: it's the boundary that
    # keeps a BNSS/BSA-only mechanism from silently being relied on for an
    # amended, century-old Act it was never sound for.
    _patch_highest(monkeypatch, "TESTACT", 5)
    toc_text = (
        "ARRANGEMENT OF SECTIONS\n1. First.\n2. Second.\n3. Third.\n4. Fourth.\n5. Fifth.\n"
        "\nCHAPTER I\nbody text here\nCHAPTER I\n"
    )
    sections = [_section(str(n)) for n in range(1, 6)]
    report = ParseReport(act="TESTACT", parser_name="GazetteParser", parser_version="10",
                          source_path="<test>", sections=sections, full_text=toc_text)
    result = validate("TESTACT", report)

    assert result.expected_source == "toc"
