"""Standing coverage of the actual production code path --
app.services.timeline_verification.verify_timeline_stages -- not just the
pure-function extraction tests (tests/test_timeline_clause.py). Same
reasoning as tests/integration/test_punishment_verification.py's own module
docstring: a guardrail whose only test is one level below where it actually
runs can still be broken by anything in the missing layer (DB fetch,
as_of filtering, the drop-vs-keep decision, the counters dict) while every
lower-level test stays green.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.timeline_verification import verify_timeline_stages
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration

# Real statute text, copied verbatim from production (same constant as
# tests/test_timeline_clause.py's BNSS_58, not re-typed).
BNSS_58_TEXT = (
    "58. No police officer shall detain in custody a person arrested without warrant for a "
    "longer period than under all the circumstances of the case is reasonable, and such period "
    "shall not, in the absence of a special order of a Magistrate under section 187, exceed more "
    "than twenty-four hours exclusive of the time necessary for the journey from the place of "
    "arrest to the Magistrate's Court, whether having jurisdiction or not."
)


async def _seed_bnss_58(db):
    bnss = await _make_act(db, "BNSS", commenced_on=date(2024, 7, 1))
    await _make_version(db, bnss, "58", BNSS_58_TEXT, date(2024, 7, 1))
    await db.commit()
    return bnss


class TestVerifyTimelineStagesProductionPath:
    async def test_grounded_stage_survives(self, db):
        await _seed_bnss_58(db)
        stages = [
            {"stage": "Production before Magistrate", "act": "BNSS 2023", "section": "58",
             "time_limit_claim": "within 24 hours of arrest"},
        ]

        kept, counters = await verify_timeline_stages(db, stages, date.today())

        assert counters == {"total": 1, "grounded": 1, "dropped_unverifiable": 0, "dropped_mismatch": 0}
        assert len(kept) == 1

    async def test_fabricated_time_limit_is_dropped_not_kept(self, db):
        # The exact fabrication risk this feature was scoped to close: BNSS
        # 58's real limit is 24 hours; the model claims 48.
        await _seed_bnss_58(db)
        stages = [
            {"stage": "Production before Magistrate", "act": "BNSS 2023", "section": "58",
             "time_limit_claim": "within 48 hours of arrest"},
        ]

        kept, counters = await verify_timeline_stages(db, stages, date.today())

        assert counters == {"total": 1, "grounded": 0, "dropped_unverifiable": 0, "dropped_mismatch": 1}
        assert kept == []  # unlike punishment_verification, dropped means GONE, not kept-with-a-flag

    async def test_unverifiable_claim_is_dropped_here_unlike_punishment_verification(self, db):
        # Deliberate, named policy difference from punishment_verification
        # (which KEEPS an unverifiable claim) -- see
        # app.services.timeline_verification's own module docstring for why:
        # a timeline stage's entire reason to exist IS the time limit it
        # claims, so nothing to check against means nothing worth showing.
        await _seed_bnss_58(db)
        stages = [
            {"stage": "Production before Magistrate", "act": "BNSS 2023", "section": "58",
             "time_limit_claim": "as soon as reasonably practicable"},
        ]

        kept, counters = await verify_timeline_stages(db, stages, date.today())

        assert counters == {"total": 1, "grounded": 0, "dropped_unverifiable": 1, "dropped_mismatch": 0}
        assert kept == []

    async def test_section_not_in_corpus_is_dropped_as_unverifiable(self, db):
        await _make_act(db, "BNSS", commenced_on=date(2024, 7, 1))  # act exists, section 58 not seeded
        stages = [
            {"stage": "Production before Magistrate", "act": "BNSS 2023", "section": "58",
             "time_limit_claim": "within 24 hours"},
        ]

        kept, counters = await verify_timeline_stages(db, stages, date.today())

        assert counters == {"total": 1, "grounded": 0, "dropped_unverifiable": 1, "dropped_mismatch": 0}
        assert kept == []

    async def test_missing_act_or_section_key_is_dropped_as_unverifiable(self, db):
        stages = [{"stage": "Some stage", "time_limit_claim": "within 24 hours"}]  # no act/section at all

        kept, counters = await verify_timeline_stages(db, stages, date.today())

        assert counters == {"total": 1, "grounded": 0, "dropped_unverifiable": 1, "dropped_mismatch": 0}
        assert kept == []

    async def test_empty_stages_list_is_a_noop(self, db):
        kept, counters = await verify_timeline_stages(db, [], date.today())
        assert counters == {"total": 0, "grounded": 0, "dropped_unverifiable": 0, "dropped_mismatch": 0}
        assert kept == []

    async def test_multiple_stages_only_grounded_ones_survive(self, db):
        await _seed_bnss_58(db)
        stages = [
            {"stage": "Real, grounded", "act": "BNSS 2023", "section": "58",
             "time_limit_claim": "within 24 hours"},
            {"stage": "Fabricated", "act": "BNSS 2023", "section": "58",
             "time_limit_claim": "within 72 hours"},
        ]

        kept, counters = await verify_timeline_stages(db, stages, date.today())

        assert counters == {"total": 2, "grounded": 1, "dropped_unverifiable": 0, "dropped_mismatch": 1}
        assert len(kept) == 1
        assert kept[0]["stage"] == "Real, grounded"
