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
from app.services.cognizability import coverage_note_for, lookup_by_section
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
        assert len(ipc_results) == 2
        assert {r["bailable"] for r in ipc_results} == {False, True}
        assert all(r["has_data"] for r in ipc_results)

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
