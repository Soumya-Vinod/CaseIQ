"""C1a (a) (docs/caseiq-industry-readiness.md): when a section's offence_attributes
rows disagree, show no classification rather than one arbitrary branch.

A genuinely conditional section stores one row per printed First Schedule
sub-entry (IPC 222: bailable if under a sentence of less than 10 years, not
bailable if under a life sentence). Both serialisers used to keep one row per
section -- attach_offence_attributes the last one Postgres returned, which is
physical row order -- so a conditional classification reached the screen as
one unconditional value. Same suppress-on-mismatch pattern as
punishment_verification.verify_punishments, and the same outcome BNSS already
gets from parse_bnss_schedule.complete_rows dropping its contradictory merged
rows.

RAW comparison, deliberately: cognizable and bailable as stored (None is its
own value -- the UI renders it as "conditional", distinct from Yes/No) and
triable_by byte-for-byte. No normalisation, so the 3 sections whose court
strings differ only by a First Schedule markup artifact (IPC 354A, 370A, 376 --
"Court of Session." vs "Court of Session.]") are suppressed too, which keeps the
stray bracket off the screen until C1b strips it. Normalising to make those
pass would be loosening a gate to get a green.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal, Protocol

# BNSS's First Schedule classifies many BNS offences per sub-section, and the
# table stores them that way: "222(a)", "351(2)" -- 220 of 398 BNS rows. A
# retrieved section always carries the bare number ("222"), so an exact match
# found nothing for 82 BNS sections whose data exists, and they showed "No row
# in our classification data" (docs/evaluation.md, 2026-10-10). The fix groups
# at LOOKUP time; storage keeps the sub-sections, which is more faithful to the
# statute. Deliberately narrow: ONE trailing parenthesised group of digits or
# lowercase letters -- the only shapes stored (9(9), 9(a)). It never touches
# IPC's letter-suffixed numbering ("376AB", "120B"), which has no parentheses
# and must never collapse into its parent number. Python `re` and Postgres
# ARE both read this pattern the same way.
SUBSECTION_SUFFIX_PATTERN = r"\(([0-9]+|[a-z]+)\)$"
_SUBSECTION_SUFFIX_RE = re.compile(SUBSECTION_SUFFIX_PATTERN)


def base_section_number(section_number: str) -> str:
    """'222(a)' -> '222', '351(2)' -> '351'; '376AB' and '125' unchanged."""
    return _SUBSECTION_SUFFIX_RE.sub("", section_number)

# Why a section has no classification to show. Carried alongside a None
# offence_attributes so the frontend can say which -- they mean different things.
UnavailableReason = Literal["no_data", "conditional"]
NO_DATA: UnavailableReason = "no_data"          # no row for this section in our data
CONDITIONAL: UnavailableReason = "conditional"  # rows exist and disagree: schedule is conditional


class _ClassificationRow(Protocol):
    # Satisfied by both the OffenceAttributes model and the schedule parsers'
    # ScheduleRow, so the same check runs on production rows and on parser output.
    cognizable: bool | None
    bailable: bool | None
    triable_by: str


def rows_disagree(rows: Iterable[_ClassificationRow]) -> bool:
    """True when a section's rows don't all carry the same (cognizable,
    bailable, triable_by) -- i.e. no single value can honestly be shown."""
    return len({(r.cognizable, r.bailable, r.triable_by) for r in rows}) > 1
