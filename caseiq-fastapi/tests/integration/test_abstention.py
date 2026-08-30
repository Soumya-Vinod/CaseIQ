"""Priority 2 / abstention: an out-of-scope query must short-circuit before
the LLM is ever called, not get a confidently-worded wrong answer alongside
fabricated citations. See app.services.retrieval.is_abstention and
app.core.config.Settings.ABSTENTION_SIMILARITY_THRESHOLD for the mechanism
and where the cutoff came from.

Written 2026-08-30 after finding the previous behaviour live: a query about
Titan's methane boiling point returned confidence_score=0.709 and 6
irrelevant citations alongside the LLM's own refusal text -- worse than no
abstention path at all, since it looked like a confident, cited answer.

This exercises the real retrieval path (real DB, real embedding computation)
feeding the real decision function -- not the full HTTP endpoint, which
would additionally need a live GROQ_API_KEY to reach the non-abstained
branch. is_abstention is exactly the function app.api.v1.legal.process_query
calls to decide whether to skip the LLM at all.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.embeddings import embedder
from app.services.retrieval import is_abstention, semantic_search
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration

_SECTION_TEXT = (
    "Whoever dishonestly takes any movable property out of the possession of any person "
    "without that person's consent, moves that property in order to such taking, is said "
    "to commit theft of movable property belonging to another."
)


async def _seed_one_theft_section(db):
    act = await _make_act(db, "TESTABSTAIN", commenced_on=date(2023, 1, 1))
    sv = await _make_version(db, act, "1", _SECTION_TEXT, date(2023, 1, 1))
    sv.embedding = await embedder.embed(f"Theft. {_SECTION_TEXT}")
    await db.commit()
    return act, sv


class TestAbstention:
    async def test_out_of_scope_query_abstains_with_no_citations(self, db):
        await _seed_one_theft_section(db)

        sections = await semantic_search(
            db, "What is the boiling point of methane on Saturn's moon Titan?"
        )

        assert is_abstention(sections) is True
        # process_query clears sections to [] once is_abstention is True --
        # asserted here as the contract the endpoint relies on, not just the
        # boolean.
        if sections:
            assert max(s["similarity"] for s in sections if s["similarity"] is not None) \
                < 0.40  # ABSTENTION_SIMILARITY_THRESHOLD, see config.py

    async def test_empty_corpus_abstains(self, db):
        # No section seeded at all -- nothing for either the vector or the
        # keyword-fallback path to find.
        sections = await semantic_search(db, "What is the punishment for theft?")
        assert sections == []
        assert is_abstention(sections) is True

    async def test_on_topic_query_against_seeded_section_does_not_abstain(self, db):
        await _seed_one_theft_section(db)

        sections = await semantic_search(db, "What is the punishment for theft of property?")

        assert sections != []
        assert is_abstention(sections) is False
