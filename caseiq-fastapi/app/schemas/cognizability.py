"""Response shapes for the cognizability/bail lookup ("can I be arrested for
this?") -- see app/services/cognizability.py for the search logic this
serves and docs/evaluation.md for the coverage numbers behind it.
"""
from __future__ import annotations

from pydantic import BaseModel


class OffenceResultOut(BaseModel):
    act: str
    section_number: str
    # Always the clean statutory heading (SectionVersion.marginal_note),
    # joined on the base section number -- NEVER the raw offence_description
    # text, which is real First Schedule content but frequently garbled by
    # the same column-bleed artifact C1 documented (see docs/evaluation.md).
    # title_source records which path produced it -- "section_heading" is
    # the normal, verified-100%-of-the-time case; "schedule_description_
    # fallback" exists only as a safety net if that join ever fails, and
    # should be rare-to-never in practice.
    title: str
    title_source: str
    # Three-state, same contract as OffenceAttributesOut elsewhere in this
    # app: a real bool, or None when the schedule's own wording is
    # genuinely conditional (cognizable_raw/bailable_raw carry that wording
    # verbatim either way, never blank).
    cognizable: bool | None = None
    cognizable_raw: str = ""
    bailable: bool | None = None
    bailable_raw: str = ""
    compoundable: bool | None = None
    compoundable_with_permission: bool | None = None
    compoundable_by: str | None = None
    triable_by: str = ""
    source: str = ""
    # The fourth state (2026-09-04): True for a real offence_attributes row
    # (resolved or conditional -- both are "we have data"), False when the
    # section itself is real and in the corpus but this table has no row
    # for it at all. Deliberately never coerced to look like a conditional
    # NULL -- "we have this row and the schedule says it's conditional" and
    # "we don't have a row for this section" mean different things and a
    # user searching by section number gets a real answer to which one it
    # is, not the same blank-looking three-state card either way.
    has_data: bool = True
    # Always True for anything returned by name search (which can only
    # find rows that HAVE offence_attributes text to match against) --
    # meaningful only on the section-number path, where the section can be
    # confirmed real (in section_versions) even with has_data=False.
    section_exists: bool = True


class CognizabilitySearchOut(BaseModel):
    query: str
    mode: str  # "section_number" | "name"
    results: list[OffenceResultOut]
    # Stated on every response, not just in documentation -- see
    # docs/evaluation.md: BNS is 398/434 sections (92%), IPC/CrPC is 249
    # rows covering 212/381 sections (56%). A name search returning nothing
    # for a real IPC offence is very plausibly a coverage gap, not proof
    # the offence doesn't exist -- the UI states this on-screen rather than
    # letting an empty result read as more confident than it is.
    coverage_note: str = (
        "Coverage: BNS is near-complete (398 of 434 sections). IPC/CrPC is partial "
        "(212 of 381 sections) -- a section not found here may still be real; it may "
        "simply not be in this table yet."
    )
