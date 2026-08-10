"""Format-agnostic validation gate. Runs after every parser, regardless of
which document family produced the candidates -- content-quality rejection
and coverage checking live here exactly once, not duplicated per parser.

Coverage is checked against the SET of section numbers the document's own
table of contents says should exist (parsing/toc.py), not against an
externally supplied scalar count. "IPC has 511 sections" turned out to be
the Act's highest section NUMBER, not a count -- IPC's true distinct-entry
total is higher once lettered insertions (124A, 498A, ...) are counted, and
a scalar tolerance check against 511 can't tell a legitimate lettered
section apart from a formatting artifact. A set difference can: it names
exactly which numbers are missing and which accepted numbers the source
document's own ToC never listed at all.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .parsing.base import ParseReport, RawSection
from .parsing.state_amendments import find_and_exclude
from .parsing.toc import extract_expected_numbers, extract_repealed_ranges
from .provenance import get_highest_section_number

REJECTION_RATE_LIMIT = 0.05           # M1 acceptance criterion
NEAR_EMPTY_LEN = 20                   # below this, treat as a genuine capture failure
SHORT_FLAG_LEN = 150                  # below this (but not near-empty), just flag for review

_FOOTNOTE_PREFIXES = ("Ins. by", "Subs. by", "Rep. by", "Added by", "Omitted by", "Omitted,")


class ValidationGateError(Exception):
    """Raised -- never sys.exit -- so both the CLI (scripts/ingest_sections.py)
    and the arq worker (Part K's K5 change-detection pipeline) can catch this
    and decide what to do; sys.exit would kill the worker process outright.
    """


@dataclass(frozen=True)
class RejectedSection:
    section_number: str
    reason: str  # "near_empty" | "title_echo" | "duplicate" | "footnote_shaped"
    detail: str = ""


@dataclass(frozen=True)
class ValidationResult:
    act: str
    accepted: list[RawSection]
    repealed: list[RawSection]
    rejected: list[RejectedSection]
    short_flagged: list[str] = field(default_factory=list)   # accepted but < SHORT_FLAG_LEN chars
    expected_numbers: frozenset[str] | None = None            # from the document's own ToC
    expected_source: str = "unavailable"                      # "toc" | "range_fallback" | "unavailable"
    missing: list[str] = field(default_factory=list)          # expected - (accepted | repealed)
    unexpected: list[str] = field(default_factory=list)       # accepted - expected
    repealed_ranges: list[tuple[str, str]] = field(default_factory=list)
    highest_section_number: int | None = None
    # (section_number, heading_name) for every accepted-but-not-in-ToC
    # candidate structurally identified as a state amendment (see
    # parsing/state_amendments.py) and removed from `accepted`/`unexpected`
    # -- never silent, always reported (see print_report). Tracked as C9.
    excluded_state_amendments: list[tuple[str, str]] = field(default_factory=list)

    @property
    def rejection_rate(self) -> float:
        total = len(self.accepted) + len(self.repealed) + len(self.rejected)
        return len(self.rejected) / total if total else 0.0


def _is_title_echo(section: RawSection) -> bool:
    """True if section_text is essentially just its own number+title restated
    with no operative content -- the ToC-row-echoed-as-body defect (D1)."""
    if section.section_title is None:
        return False
    norm_text = re.sub(r"\W+", "", section.section_text).lower()
    norm_title = re.sub(r"\W+", "", section.section_title).lower()
    return bool(norm_title) and norm_text == norm_title


def _is_footnote_shaped(section: RawSection) -> bool:
    """Defense in depth: parsers should already exclude these structurally
    (see legacy_parser.py), this is a second, independent check."""
    return section.section_text.lstrip().startswith(_FOOTNOTE_PREFIXES)


def validate(act: str, report: ParseReport) -> ValidationResult:
    accepted: list[RawSection] = []
    repealed: list[RawSection] = []
    rejected: list[RejectedSection] = []
    short_flagged: list[str] = []
    seen_numbers: set[str] = set()

    for s in report.sections:
        if s.section_number in seen_numbers:
            rejected.append(RejectedSection(s.section_number, "duplicate",
                                             "duplicate (act, section_number) within this batch"))
            continue
        if _is_footnote_shaped(s):
            rejected.append(RejectedSection(s.section_number, "footnote_shaped",
                                             "starts with an amendment-footnote verb"))
            continue
        if s.is_repealed:
            seen_numbers.add(s.section_number)
            repealed.append(s)
            continue
        if len(s.section_text) < NEAR_EMPTY_LEN:
            rejected.append(RejectedSection(s.section_number, "near_empty",
                                             f"{len(s.section_text)} chars < {NEAR_EMPTY_LEN} "
                                             f"and not identified as repealed"))
            continue
        if _is_title_echo(s):
            rejected.append(RejectedSection(s.section_number, "title_echo",
                                             "section_text is just the title restated"))
            continue
        seen_numbers.add(s.section_number)
        accepted.append(s)
        if len(s.section_text) < SHORT_FLAG_LEN:
            short_flagged.append(s.section_number)

    accepted_numbers = {s.section_number for s in accepted}
    repealed_numbers = {s.section_number for s in repealed}
    highest = get_highest_section_number(act)

    expected_numbers = extract_expected_numbers(report.full_text)
    expected_source = "toc"
    if expected_numbers is None:
        # No extractable ToC (BNSS/BSA's Gazette originals have none at all --
        # they go straight from the notification header to the operative
        # text). For a freshly enacted Act with contiguous numbering and no
        # lettered insertions, highest-number-as-range IS a valid expected
        # set -- this was the pre-2026-08-09 check, kept here explicitly as a
        # labeled fallback rather than silently reused as if it were the
        # primary method. It is NOT valid for an amended, century-old Act
        # (IPC/CrPC), which is exactly why those two have a real ToC to use
        # instead and don't hit this branch.
        if highest is not None:
            expected_numbers = frozenset(str(n) for n in range(1, highest + 1))
            expected_source = "range_fallback"
        else:
            expected_source = "unavailable"

    excluded_state_amendments: list[tuple[str, str]] = []
    if expected_numbers is not None:
        accepted, excluded_state_amendments = find_and_exclude(
            accepted, report.full_text, expected_numbers
        )
        accepted_numbers = {s.section_number for s in accepted}

    missing: list[str] = []
    unexpected: list[str] = []
    if expected_numbers is not None:
        missing = sorted(expected_numbers - accepted_numbers - repealed_numbers,
                          key=_sort_key)
        unexpected = sorted(accepted_numbers - expected_numbers, key=_sort_key)

    return ValidationResult(
        act=act,
        accepted=accepted,
        repealed=repealed,
        rejected=rejected,
        short_flagged=short_flagged,
        expected_numbers=expected_numbers,
        expected_source=expected_source,
        missing=missing,
        unexpected=unexpected,
        repealed_ranges=extract_repealed_ranges(report.full_text),
        highest_section_number=highest,
        excluded_state_amendments=excluded_state_amendments,
    )


def _sort_key(section_number: str) -> tuple[int, str]:
    m = re.match(r"(\d+)", section_number)
    return (int(m.group(1)) if m else 0, section_number)


def enforce_gate(result: ValidationResult) -> None:
    """Raises ValidationGateError if:
      - rejection rate exceeds REJECTION_RATE_LIMIT, or
      - the document's own ToC could not be bounded (expected_numbers is None
        -- coverage cannot be checked at all, so the act is not considered
        provenanced), or
      - any section number the ToC lists is neither accepted nor explicitly
        recorded as repealed (an unexplained gap -- the same failure mode
        that let BNS s.356 go silently missing before this gate existed).
    Does NOT raise on `unexpected` entries (accepted numbers the ToC never
    listed) -- those are reported for review but don't block ingestion,
    since a ToC extraction miss is more likely than a genuine false-positive
    accepted section.
    """
    if result.rejection_rate > REJECTION_RATE_LIMIT:
        total = len(result.accepted) + len(result.repealed) + len(result.rejected)
        raise ValidationGateError(
            f"{result.act}: rejection rate {result.rejection_rate:.1%} exceeds "
            f"{REJECTION_RATE_LIMIT:.0%} limit ({len(result.rejected)} of {total} rejected)."
        )

    if result.expected_source == "unavailable":
        raise ValidationGateError(
            f"{result.act}: could not derive expected_section_numbers from this document's own "
            f"table of contents (parsing/toc.py), AND no highest_section_number is recorded in "
            f"documents/provenance.json to fall back on. Coverage cannot be checked against an "
            f"unbounded/unknown target -- this act is not considered provenanced."
        )

    if result.missing:
        raise ValidationGateError(
            f"{result.act}: {len(result.missing)} section(s) listed in the document's own ToC "
            f"are neither accepted nor recorded as repealed: {result.missing[:30]}"
            f"{'...' if len(result.missing) > 30 else ''}"
        )


def print_report(result: ValidationResult) -> None:
    total = len(result.accepted) + len(result.repealed) + len(result.rejected)
    print(f"[{result.act}] parsed={total} accepted={len(result.accepted)} "
          f"repealed={len(result.repealed)} rejected={len(result.rejected)} "
          f"({result.rejection_rate:.1%})")
    reasons: dict[str, int] = {}
    for r in result.rejected:
        reasons[r.reason] = reasons.get(r.reason, 0) + 1
    for reason, count in sorted(reasons.items()):
        print(f"[{result.act}]   rejected/{reason}: {count}")
    if result.short_flagged:
        print(f"[{result.act}]   accepted-but-short (<{SHORT_FLAG_LEN} chars, review "
              f"recommended): {result.short_flagged}")
    if result.expected_source == "unavailable":
        print(f"[{result.act}] expected_section_numbers: UNAVAILABLE (no ToC, no highest_section_number)")
    else:
        print(f"[{result.act}] expected ({result.expected_source}): "
              f"{len(result.expected_numbers)}")
        print(f"[{result.act}] missing (expected, not accepted or repealed): "
              f"{len(result.missing)} {result.missing}")
        print(f"[{result.act}] unexpected (accepted, not in ToC): "
              f"{len(result.unexpected)} {result.unexpected}")
    if result.excluded_state_amendments:
        by_heading: dict[str, list[str]] = {}
        for number, heading in result.excluded_state_amendments:
            by_heading.setdefault(heading, []).append(number)
        for heading, numbers in by_heading.items():
            numbers_sorted = sorted(numbers, key=_sort_key)
            print(f"[{result.act}] excluded {len(numbers_sorted)} state-amendment section(s) "
                  f"({', '.join(numbers_sorted)}) under schedule heading {heading!r} "
                  f"-- not pan-India, see C9.")
    if result.repealed:
        print(f"[{result.act}] repealed sections recorded: "
              f"{sorted((s.section_number for s in result.repealed), key=_sort_key)}")
    if result.repealed_ranges:
        print(f"[{result.act}] consolidated repealed ranges in source text: "
              f"{result.repealed_ranges}")
    if result.highest_section_number is not None:
        accepted_max = max((int(re.match(r'\d+', s.section_number).group())
                             for s in result.accepted), default=0)
        print(f"[{result.act}] highest_section_number (provenanced): "
              f"{result.highest_section_number}, highest accepted number seen: {accepted_max}")
