"""C-lookup regression coverage for a bug found live while verifying the row-mismatch-transcription
re-ingestion (docs/evaluation.md, row-mismatch-transcription entry), not by inspection:
`lookup_by_section()` used `scalar_one_or_none()`, which raises `MultipleResultsFound` -- a 500, not
a wrong answer -- the instant a section has more than one `offence_attributes` row. Genuinely
conditional multi-clause sections have always stored one row per real sub-clause under the same
section_number (the contract every hand-transcription pass in this schedule uses, e.g. s.376's three
graded conditions) -- confirmed pre-existing, not introduced by this session's own work (s.376 itself
crashed this same way before today), but the row-mismatch-transcription pass made it far more common:
most of its 40 newly-fixed sections are themselves multi-row.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.models.offence_attributes import OffenceAttributes
from app.services.cognizability import coverage_note_for, lookup_by_section, search_by_name
from app.services.retrieval import attach_offence_attributes
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration


async def _seed_offence_row(db, act, section_number, *, cognizable=None, bailable=None,
                             triable_by="Court of Session.", offence="Test offence."):
    row = OffenceAttributes(
        act=act.act_code, section_number=section_number, offence_description=offence,
        punishment_text="", cognizable_raw="Cognizable" if cognizable else "Non-cognizable",
        cognizable=cognizable, bailable_raw="Bailable" if bailable else "Non-bailable",
        bailable=bailable, triable_by=triable_by, source="TEST", source_sha256="", parser_version="test",
    )
    db.add(row)
    await db.flush()
    return row


class TestLookupBySectionHandlesMultipleRows:
    async def test_multi_row_section_does_not_crash(self, db):
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _make_version(db, ipc, "999", "Test section text.", date(1862, 1, 1))
        await _seed_offence_row(db, ipc, "999", cognizable=True, bailable=False,
                                 offence="Base clause.")
        await _seed_offence_row(db, ipc, "999", cognizable=True, bailable=True,
                                 offence="If a lesser circumstance applies.")
        await db.commit()

        results = await lookup_by_section(db, "999")
        ipc_results = [r for r in results if r["act"] == "IPC"]
        # CHANGED 2026-10-10 (C1a (a)): this used to assert two cards with
        # contradictory bail values -- the defect itself. Rows that disagree
        # now come back as ONE card with no classification.
        assert len(ipc_results) == 1
        assert ipc_results[0]["unavailable_reason"] == "conditional"
        assert ipc_results[0]["has_data"] is True
        assert ipc_results[0]["bailable"] is None and ipc_results[0]["triable_by"] == ""

    async def test_multi_row_section_coverage_note_still_correct(self, db):
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _make_version(db, ipc, "998", "Test section text.", date(1862, 1, 1))
        await _seed_offence_row(db, ipc, "998", cognizable=True, bailable=False)
        await _seed_offence_row(db, ipc, "998", cognizable=True, bailable=True)
        await db.commit()

        results = await lookup_by_section(db, "998")
        # Every result has real data -- no coverage caveat needed.
        assert coverage_note_for("section_number", results) == ""

    async def test_single_row_section_still_works(self, db):
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _make_version(db, ipc, "997", "Test section text.", date(1862, 1, 1))
        await _seed_offence_row(db, ipc, "997", cognizable=False, bailable=True)
        await db.commit()

        results = await lookup_by_section(db, "997")
        ipc_results = [r for r in results if r["act"] == "IPC"]
        assert len(ipc_results) == 1
        assert ipc_results[0]["cognizable"] is False

    async def test_section_with_no_offence_row_still_reports_has_data_false(self, db):
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _make_version(db, ipc, "996", "Real section, never classified.", date(1862, 1, 1))
        await db.commit()

        results = await lookup_by_section(db, "996")
        ipc_results = [r for r in results if r["act"] == "IPC"]
        assert len(ipc_results) == 1
        assert ipc_results[0]["has_data"] is False
        assert coverage_note_for("section_number", results) != ""


class TestConditionalSectionsSuppress:
    """C1a (a): a section whose rows disagree on cognizable, bailable or court
    shows no classification -- in both serialisers."""

    async def test_court_only_difference_suppresses_without_normalising(self, db):
        # The bracket-artifact case (IPC 370A/376): same classification, court
        # strings differ only by a stray "]". Raw comparison suppresses it.
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _make_version(db, ipc, "995", "Test section text.", date(1862, 1, 1))
        await _seed_offence_row(db, ipc, "995", cognizable=True, bailable=False,
                                 triable_by="Court of Session.")
        await _seed_offence_row(db, ipc, "995", cognizable=True, bailable=False,
                                 triable_by="Court of Session.]")
        await db.commit()

        (card,) = [r for r in await lookup_by_section(db, "995") if r["act"] == "IPC"]
        assert card["unavailable_reason"] == "conditional"

    async def test_agreeing_multi_row_section_still_displays(self, db):
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _make_version(db, ipc, "994", "Test section text.", date(1862, 1, 1))
        await _seed_offence_row(db, ipc, "994", cognizable=True, bailable=False, offence="Base.")
        await _seed_offence_row(db, ipc, "994", cognizable=True, bailable=False, offence="Variant.")
        await db.commit()

        cards = [r for r in await lookup_by_section(db, "994") if r["act"] == "IPC"]
        assert len(cards) == 2
        assert all(c["unavailable_reason"] is None and c["bailable"] is False for c in cards)

    async def test_name_search_checks_all_rows_not_just_the_matched_one(self, db):
        # search_by_name's ilike can match one sub-row; the others still decide.
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _make_version(db, ipc, "993", "Test section text.", date(1862, 1, 1))
        await _seed_offence_row(db, ipc, "993", cognizable=True, bailable=True,
                                 offence="Zyxwv omission, lesser sentence.")
        await _seed_offence_row(db, ipc, "993", cognizable=True, bailable=False,
                                 offence="If under sentence of life.")
        await db.commit()

        (card,) = [r for r in await search_by_name(db, "zyxwv") if r["section_number"] == "993"]
        assert card["unavailable_reason"] == "conditional"

    async def test_no_row_section_reports_no_data_reason(self, db):
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _make_version(db, ipc, "992", "Real section, never classified.", date(1862, 1, 1))
        await db.commit()

        (card,) = [r for r in await lookup_by_section(db, "992") if r["act"] == "IPC"]
        assert card["unavailable_reason"] == "no_data"


class TestAttachOffenceAttributes:
    """The source-card / section-detail serialiser."""

    async def test_disagreeing_rows_suppress(self, db):
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _seed_offence_row(db, ipc, "991", cognizable=True, bailable=True)
        await _seed_offence_row(db, ipc, "991", cognizable=True, bailable=False)
        await db.commit()

        (s,) = await attach_offence_attributes(db, [{"act": "IPC", "section": "991"}])
        assert s["offence_attributes"] is None
        assert s["offence_attributes_unavailable"] == "conditional"

    async def test_agreeing_rows_display(self, db):
        ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
        await _seed_offence_row(db, ipc, "990", cognizable=True, bailable=False, offence="Base.")
        await _seed_offence_row(db, ipc, "990", cognizable=True, bailable=False, offence="Variant.")
        await db.commit()

        (s,) = await attach_offence_attributes(db, [{"act": "IPC", "section": "990"}])
        assert s["offence_attributes"]["bailable"] is False
        assert s["offence_attributes_unavailable"] is None

    async def test_no_row_is_no_data(self, db):
        (s,) = await attach_offence_attributes(db, [{"act": "BNS", "section": "77"}])
        assert s["offence_attributes"] is None
        assert s["offence_attributes_unavailable"] == "no_data"
