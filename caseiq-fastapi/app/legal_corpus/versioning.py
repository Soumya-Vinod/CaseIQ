"""Part K helpers for turning a parsed section into a bitemporal SectionVersion
row. Kept separate from ingestion I/O so the core rule -- valid_from must
reflect real-world validity, never ingestion time -- is a small, pure,
directly-testable function.
"""
from __future__ import annotations

from datetime import date


def resolve_valid_from(content_as_on: date | None, act_commenced_on: date | None) -> date:
    """valid_from must NEVER be date.today() / ingestion time -- that would
    conflate valid_time (when the provision was/is in force in the real
    world) with transaction_time (when CaseIQ recorded it; SectionVersion
    already has recorded_at for that axis).

    Preference order:
      1. The source document's own content_as_on (documents/provenance.json)
         -- the most direct evidence of what the text reflects.
      2. The Act's commencement date -- a section is presumed in force since
         its Act commenced, absent more specific amendment information.
    Raises rather than silently falling back to today if neither is known --
    an ingestion run should surface that gap, not paper over it.
    """
    if content_as_on is not None:
        return content_as_on
    if act_commenced_on is not None:
        return act_commenced_on
    raise ValueError(
        "cannot resolve valid_from: no content_as_on (documents/provenance.json) and "
        "no act.commenced_on -- valid_from must never silently default to ingestion time"
    )
