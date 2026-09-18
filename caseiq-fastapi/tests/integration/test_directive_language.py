"""app.services.directive_language.record_stats -- the DB-backed half of
directive-language detection (docs/evaluation.md, directive-language
entry). Runs against a real Postgres (the `db` fixture, see
tests/integration/conftest.py) because it writes DirectiveLanguageStats;
no corpus rows needed, since the function only counts hits it's handed
directly. Mirrors tests/integration/test_grounding.py's own structure.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.directive_language_stats import DirectiveLanguageStats
from app.services.directive_language import record_stats

pytestmark = pytest.mark.integration


async def _stats_row(db) -> DirectiveLanguageStats:
    return (await db.execute(select(DirectiveLanguageStats).limit(1))).scalar_one()


class TestRecordStats:
    async def test_no_hits_counts_total_only(self, db):
        await record_stats(db, [])

        row = await _stats_row(db)
        assert row.responses_total == 1
        assert row.responses_flagged == 0
        assert row.hits_total == 0

    async def test_single_hit_flags_response_and_counts_one_hit(self, db):
        await record_stats(db, [{"field": "conversational_summary", "phrase": "you should"}])

        row = await _stats_row(db)
        assert row.responses_total == 1
        assert row.responses_flagged == 1
        assert row.hits_total == 1

    async def test_multiple_hits_in_one_response_counts_once_flagged_all_hits(self, db):
        # One response, two hits: responses_flagged must NOT double-count
        # the response itself, but hits_total must reflect both.
        await record_stats(db, [
            {"field": "conversational_summary", "phrase": "you should"},
            {"field": "conversational_summary", "phrase": "hire a lawyer"},
        ])

        row = await _stats_row(db)
        assert row.responses_total == 1
        assert row.responses_flagged == 1
        assert row.hits_total == 2

    async def test_stats_accumulate_across_calls(self, db):
        await record_stats(db, [])
        await record_stats(db, [{"field": "situation_overview", "phrase": "you must"}])
        await record_stats(db, [])

        row = await _stats_row(db)
        assert row.responses_total == 3
        assert row.responses_flagged == 1
        assert row.hits_total == 1
