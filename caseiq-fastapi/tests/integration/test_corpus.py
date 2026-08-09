"""Part K integration tests, against a real Postgres+pgvector (see conftest.py).

Written BEFORE the retrieval/ingestion rewrite -- these are RED until
app/services/retrieval.py grows get_section_as_of/acts_for_incident_date/the
as-of-aware semantic_search, and app/legal_corpus/versioning.py grows
resolve_valid_from. That's deliberate: these six scenarios are the actual
behaviours Part K exists to deliver, and if they aren't tested, the cutover
isn't done.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.corpus import Act, JudicialStatus, SectionVersion

pytestmark = pytest.mark.integration


async def _make_act(db, code: str, commenced_on: date | None = None) -> Act:
    act = Act(act_code=code, short_title=code, status="in_force", commenced_on=commenced_on)
    db.add(act)
    await db.flush()
    return act


async def _make_version(
    db, act: Act, section_number: str, text: str, valid_from: date, valid_to: date | None = None,
    version_no: int = 1,
) -> SectionVersion:
    sv = SectionVersion(
        act_id=act.id, section_number=section_number, version_no=version_no,
        marginal_note=text[:50], section_text=text, valid_from=valid_from, valid_to=valid_to,
    )
    db.add(sv)
    await db.flush()
    return sv


class TestAsOfQuerying:
    """K1/K3: as-of query returns the version in force on a given date, not latest."""

    async def test_as_of_returns_version_in_force_at_that_date(self, db):
        from app.services.retrieval import get_section_as_of

        act = await _make_act(db, "TESTACT")
        await _make_version(db, act, "1", "old text", date(2020, 1, 1), date(2023, 1, 1), version_no=1)
        await _make_version(db, act, "1", "new text", date(2023, 1, 1), None, version_no=2)
        await db.commit()

        result = await get_section_as_of(db, "TESTACT", "1", as_of=date(2021, 6, 1))
        assert result is not None
        assert result["section_text"] == "old text"

        result_now = await get_section_as_of(db, "TESTACT", "1", as_of=date(2024, 1, 1))
        assert result_now["section_text"] == "new text"


class TestValidToExclusion:
    """K1: a section with valid_to set does NOT appear for as_of after that date."""

    async def test_closed_version_excluded_after_valid_to_with_no_successor(self, db):
        from app.services.retrieval import get_section_as_of

        act = await _make_act(db, "TESTACT2")
        await _make_version(db, act, "5", "repealed text", date(2020, 1, 1), date(2022, 1, 1))
        await db.commit()

        # still in force during its window
        assert (await get_section_as_of(db, "TESTACT2", "5", as_of=date(2021, 1, 1))) is not None
        # excluded after valid_to, with nothing superseding it
        assert (await get_section_as_of(db, "TESTACT2", "5", as_of=date(2022, 6, 1))) is None


class TestJudicialStatusFiltering:
    """K2's hard rule: struck-down excluded entirely; read-down returned with scope_note."""

    async def test_struck_down_section_excluded_from_point_lookup(self, db):
        from app.services.retrieval import get_section_as_of

        act = await _make_act(db, "TESTACT3")
        await _make_version(db, act, "497", "adultery text", date(1862, 1, 1), None)
        db.add(JudicialStatus(
            act_id=act.id, section_number="497", status="struck_down",
            case_name="Joseph Shine v Union of India", citation="AIR 2018 SC 4898",
            citation_verified=True, court="Supreme Court of India", decided_on=date(2018, 9, 27),
        ))
        await db.commit()

        assert (await get_section_as_of(db, "TESTACT3", "497")) is None

    async def test_struck_down_section_excluded_from_semantic_search(self, db):
        from app.services.retrieval import semantic_search

        act = await _make_act(db, "TESTACT3B")
        await _make_version(db, act, "497", "unique adultery marker text for search", date(1862, 1, 1), None)
        db.add(JudicialStatus(
            act_id=act.id, section_number="497", status="struck_down",
            case_name="Joseph Shine v Union of India", citation="AIR 2018 SC 4898",
            citation_verified=True, court="Supreme Court of India", decided_on=date(2018, 9, 27),
        ))
        await db.commit()

        results = await semantic_search(db, "unique adultery marker text for search", top_k=5)
        assert all(r["section"] != "497" for r in results)

    async def test_read_down_section_returned_with_scope_note(self, db):
        from app.services.retrieval import get_section_as_of

        act = await _make_act(db, "TESTACT4")
        await _make_version(db, act, "377", "unnatural offences text", date(1862, 1, 1), None)
        db.add(JudicialStatus(
            act_id=act.id, section_number="377", status="read_down",
            case_name="Navtej Singh Johar v Union of India", citation="AIR 2018 SC 4321",
            citation_verified=True, court="Supreme Court of India", decided_on=date(2018, 9, 6),
            scope_note="Consensual adult conduct decriminalised; provision survives for "
                       "non-consensual acts and acts involving minors/animals.",
        ))
        await db.commit()

        result = await get_section_as_of(db, "TESTACT4", "377")
        assert result is not None
        assert result["judicial_status"]["status"] == "read_down"
        assert "decriminalised" in result["judicial_status"]["scope_note"]


class TestTemporalRouting:
    """K3: incident_date before 2024-07-01 routes to IPC/CrPC; on/after routes to BNS/BNSS."""

    def test_acts_for_incident_date_pre_cutover(self):
        from app.services.retrieval import acts_for_incident_date

        acts = acts_for_incident_date(date(2024, 6, 30))
        assert "IPC" in acts and "CrPC" in acts
        assert "BNS" not in acts

    def test_acts_for_incident_date_post_cutover(self):
        from app.services.retrieval import acts_for_incident_date

        acts = acts_for_incident_date(date(2024, 7, 1))
        assert "BNS" in acts
        assert "IPC" not in acts

    async def test_semantic_search_incident_date_routes_to_correct_regime(self, db):
        from app.services.retrieval import semantic_search

        ipc = await _make_act(db, "IPC")
        bns = await _make_act(db, "BNS")
        shared_text = "distinctive shared offence description for routing test"
        await _make_version(db, ipc, "302", shared_text, date(1862, 1, 1), None)
        await _make_version(db, bns, "103", shared_text, date(2024, 7, 1), None)
        await db.commit()

        pre = await semantic_search(db, shared_text, top_k=5, incident_date=date(2024, 1, 1))
        assert any(r["act"] == "IPC" for r in pre)
        assert all(r["act"] != "BNS" for r in pre)

        post = await semantic_search(db, shared_text, top_k=5, incident_date=date(2024, 8, 1))
        assert any(r["act"] == "BNS" for r in post)
        assert all(r["act"] != "IPC" for r in post)


class TestValidFromProvenance:
    """valid_from is seeded from content_as_on, never ingestion time (K1)."""

    def test_resolve_valid_from_prefers_content_as_on(self):
        from app.legal_corpus.versioning import resolve_valid_from

        assert resolve_valid_from(
            content_as_on=date(2025, 10, 6), act_commenced_on=date(2023, 12, 25)
        ) == date(2025, 10, 6)

    def test_resolve_valid_from_falls_back_to_act_commencement(self):
        from app.legal_corpus.versioning import resolve_valid_from

        assert resolve_valid_from(
            content_as_on=None, act_commenced_on=date(1862, 1, 1)
        ) == date(1862, 1, 1)

    def test_resolve_valid_from_never_defaults_to_today(self):
        from app.legal_corpus.versioning import resolve_valid_from

        with pytest.raises(ValueError):
            resolve_valid_from(content_as_on=None, act_commenced_on=None)

    async def test_ingested_row_valid_from_is_not_todays_date(self, db):
        """A section ingested today, whose source document's content_as_on is
        years in the past, must carry that past date as valid_from -- not
        today's date, which would be conflating valid_time with
        transaction_time (recorded_at already captures transaction_time).
        """
        act = await _make_act(db, "TESTACT5", commenced_on=date(1862, 1, 1))
        sv = await _make_version(db, act, "1", "text", valid_from=date(1862, 1, 1))
        await db.commit()

        assert sv.valid_from == date(1862, 1, 1)
        assert sv.valid_from != date.today()
        # recorded_at (transaction_time) is separate and IS "now" -- both axes
        # must be present and must differ for an old Act ingested today.
        assert sv.recorded_at.date() == date.today()
