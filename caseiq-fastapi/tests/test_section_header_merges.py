"""Regression guard for the three merged-section pairs (docs/evaluation.md,
"Corpus completeness: a parser boundary failure" 2026-09-14, and the
2026-10-09 entry on why that fix never reached the parser).

BNS 255, IPC 174A and IPC 376AB each had a section header the parsers didn't
recognise ("255.—Public...", "174A .Non-appearance...", "376AB.Punishment..."),
so each body was appended to the PRECEDING section (BNS 254, IPC 174, IPC
376A) and only the ToC stub survived under the right number. On 2026-09-14
all six rows were corrected directly in production; the parsers were not. The
divergence stayed invisible for 26 nights because the only thing that
re-parses from source -- nightly-eval's fresh ingest -- was the job the fix
itself broke (removing "255" from KNOWN_TRUNCATION_EXCEPTIONS).

These tests run the REAL parsers against the REAL tracked PDFs, so a
row-level fix can never again stand in for a parser fix unnoticed. No skipif:
documents/*.pdf are tracked, and a missing source must fail here, not skip.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.legal_corpus.parsing import gazette_parser, legacy_parser
from app.legal_corpus.parsing.registry import PARSERS
from app.legal_corpus.validate import enforce_gate, validate
from scripts.ingest_sections import KNOWN_TRUNCATION_EXCEPTIONS

DOCS = Path(__file__).resolve().parent.parent / "documents"


def _accepted(act: str, pdf: str):
    result = validate(act, PARSERS[act].parse(DOCS / pdf))
    return result, {s.section_number: s.section_text for s in result.accepted}


@pytest.fixture(scope="module")
def bns():
    return _accepted("BNS", "BNS_2023.pdf")


@pytest.fixture(scope="module")
def ipc():
    return _accepted("IPC", "IPC_1860.pdf")


@pytest.fixture(scope="module")
def crpc():
    return _accepted("CrPC", "CrPC_1973.pdf")


# --- the header regexes themselves (fast, synthetic) -----------------------

def _gazette_numbers(text: str) -> list[str]:
    return [m.group("num") for m in gazette_parser._HEADER_RE.finditer(text)]


def test_gazette_header_accepts_em_dash_after_bare_number():
    assert _gazette_numbers("\n255.—Public servant disobeying direction of law") == ["255"]


@pytest.mark.parametrize("line", [
    "\nExplanation 1.—If sufficient evidence has been obtained",
    "\nException 2.—Wills admitted to probate in India",
])
def test_gazette_header_rejects_em_dash_reached_through_marginal_prefix(line):
    # 100 of the 101 line-start "N.—" occurrences across BNS/BNSS/BSA are this
    # shape; accepting them split ~40 real sections when measured.
    assert _gazette_numbers(line) == []


@pytest.mark.parametrize("line,expected", [
    ("\n15.The State Government may", ["15"]),
    ("\nTrial of 4. (1) All offences", ["4"]),
    ("\n2.(1) In this Sanhita", ["2"]),
])
def test_gazette_header_existing_shapes_unchanged(line, expected):
    assert _gazette_numbers(line) == expected


def _legacy_numbers(text: str) -> list[str]:
    return [m.group(1) for m in legacy_parser._HEADER_RE.finditer(text)]


@pytest.mark.parametrize("line,expected", [
    ("\n376AB.Punishment for rape on woman under twelve years of age.", ["376AB"]),
    ("\n174A .Non-appearance in response to a proclamation", ["174A"]),
    ("\n376. Punishment for rape.—(1) Whoever", ["376"]),
])
def test_legacy_header_accepts_glued_and_spaced_periods(line, expected):
    assert _legacy_numbers(line) == expected


@pytest.mark.parametrize("line", [
    "\n1.5 lakh rupees shall be",     # decimal, not a header
    "\n12.and in that case the",      # lowercase continuation
])
def test_legacy_header_still_rejects_non_headers(line):
    assert _legacy_numbers(line) == []


# --- the three pairs, against the real source ------------------------------

def test_bns_255_is_its_own_section(bns):
    _, s = bns
    assert s["255"].startswith("255.—Public servant disobeying direction of law")
    assert "Whoever, being a public servant, knowingly disobeys" in s["255"]
    assert s["255"].endswith("or with fine, or with both.")


def test_bns_254_no_longer_carries_255(bns):
    _, s = bns
    assert "Public servant disobeying direction of law" not in s["254"]
    assert s["254"].endswith("the harbour is by the spouse of the offender.")


def test_ipc_174a_is_its_own_section(ipc):
    _, s = ipc
    assert s["174A"].startswith("174A .Non-appearance in response to a proclamation")
    assert s["174A"].endswith("shall also be liable to fine.]")
    assert "Non-appearance in response to a proclamation" not in s["174"]


def test_ipc_376ab_is_its_own_section(ipc):
    _, s = ipc
    assert s["376AB"].startswith("376AB.Punishment for rape on woman under twelve years of age.")
    assert "Whoever, commits rape on a woman under twelve years of age" in s["376AB"]
    assert "rape on woman under twelve years of age" not in s["376A"]
    assert s["376A"].endswith("natural life, or with death.")


def test_crpc_185_loses_only_its_glued_footnote(crpc):
    # The one side effect of the legacy-parser fix: this footnote line now
    # matches as a header candidate and is excised by the existing footnote
    # check. Verified 2026-10-09 as exactly the final 53 chars of the old
    # text, nothing operative.
    _, s = crpc
    assert "Ins. by Act 45 of 1978" not in s["185"]
    assert s["185"].endswith("or any other law for the time being in force.")


@pytest.mark.parametrize("fixture_name,act", [("bns", "BNS"), ("ipc", "IPC")])
def test_gate_passes_with_documented_allowlist(request, fixture_name, act):
    # The exact failure nightly-eval hit for 26 nights: BNS blocked on '255'.
    result, _ = request.getfixturevalue(fixture_name)
    enforce_gate(result, KNOWN_TRUNCATION_EXCEPTIONS[act])
    assert "255" not in KNOWN_TRUNCATION_EXCEPTIONS["BNS"]
