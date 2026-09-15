"""app.services.grounding.apply_grounding_check -- the production function
behind "confident overview, empty laws_applicable" (docs/evaluation.md).
Runs against a real Postgres (the `db` fixture, see conftest.py) because it
writes GroundingStats; no corpus rows needed, since the function only reads
`structured_data` it's handed directly.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.grounding_stats import GroundingStats
from app.services.grounding import apply_grounding_check

pytestmark = pytest.mark.integration


async def _stats_row(db) -> GroundingStats:
    return (await db.execute(select(GroundingStats).limit(1))).scalar_one()


class TestApplyGroundingCheck:
    async def test_never_cited_confident_overview_is_suppressed_and_noted(self, db):
        # The real, confirmed bug case: dowry death, unhedged.
        structured = {
            "situation_overview": "The death of a woman caused by dowry harassment is "
                                   "classified as dowry death under the relevant criminal statutes.",
            "severity": "critical",
            "severity_reason": "Dowry death is a serious criminal offence with severe legal implications.",
            "laws_applicable": [],
            "punishments": [],
        }
        structured, summary, confidence, grounded = await apply_grounding_check(
            db, structured, "See below for details.", 0.75, had_laws=False,
        )

        assert grounded is False
        assert "severity" not in structured
        assert "severity_reason" not in structured
        assert confidence == 0.0
        assert "No specific section could be confirmed" in summary
        # Must NOT claim sections were named and then failed verification --
        # nothing was ever named here.
        assert "initially named" not in summary
        # The rest of the answer (what the offence generically is) survives --
        # this suppresses the specific ungrounded claims, not the whole answer.
        assert structured["situation_overview"]

        row = await _stats_row(db)
        assert row.responses_total == 1
        assert row.responses_ungrounded_never_cited == 1
        assert row.responses_ungrounded_stripped_to_zero == 0
        assert row.responses_grounded == 0

    async def test_cited_then_fully_stripped_is_suppressed_with_distinct_note(self, db):
        structured = {
            "situation_overview": "Some overview.",
            "severity": "high", "severity_reason": "Reason.",
            "laws_applicable": [],  # already stripped by verify_citations before this call
        }
        structured, summary, confidence, grounded = await apply_grounding_check(
            db, structured, "See below for details.", 0.6, had_laws=True,
        )

        assert grounded is False
        assert "severity" not in structured
        assert confidence == 0.0
        assert "initially named" in summary  # the OTHER note this time

        row = await _stats_row(db)
        assert row.responses_ungrounded_never_cited == 0
        assert row.responses_ungrounded_stripped_to_zero == 1

    async def test_grounded_response_is_untouched(self, db):
        structured = {
            "situation_overview": "Overview.",
            "severity": "high", "severity_reason": "Reason.",
            "laws_applicable": [{"act": "IPC 1860", "section": "304B"}],
        }
        structured, summary, confidence, grounded = await apply_grounding_check(
            db, dict(structured), "Original summary.", 0.9, had_laws=True,
        )

        assert grounded is True
        assert structured["severity"] == "high"
        assert structured["severity_reason"] == "Reason."
        assert confidence == 0.9
        assert summary == "Original summary."  # no note appended

        row = await _stats_row(db)
        assert row.responses_grounded == 1
        assert row.responses_ungrounded_never_cited == 0
        assert row.responses_ungrounded_stripped_to_zero == 0

    async def test_stats_accumulate_across_calls(self, db):
        grounded_structured = {"laws_applicable": [{"act": "IPC 1860", "section": "379"}]}
        ungrounded_structured = {"situation_overview": "x", "laws_applicable": []}

        await apply_grounding_check(db, dict(grounded_structured), "s", 0.5, had_laws=True)
        await apply_grounding_check(db, dict(ungrounded_structured), "s", 0.5, had_laws=False)
        await apply_grounding_check(db, dict(ungrounded_structured), "s", 0.5, had_laws=True)

        row = await _stats_row(db)
        assert row.responses_total == 3
        assert row.responses_grounded == 1
        assert row.responses_ungrounded_never_cited == 1
        assert row.responses_ungrounded_stripped_to_zero == 1
