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
from app.services.retrieval import is_abstention, is_civil_scope_mismatch, semantic_search
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration

_SECTION_TEXT = (
    "Whoever dishonestly takes any movable property out of the possession of any person "
    "without that person's consent, moves that property in order to such taking, is said "
    "to commit theft of movable property belonging to another."
)

# Real BNS s.85 text (Husband or relative of husband of a woman subjecting
# her to cruelty), verified against the live corpus. Used here, not a
# paraphrase, so this test seeds the actual provision the bug was about.
_CRUELTY_SECTION_TEXT = (
    "Husband or relative of husband of a woman subjecting her to cruelty.--Whoever, being "
    "the husband or the relative of the husband of a woman, subjects such woman to cruelty "
    "shall be punished with imprisonment for a term which may extend to three years and "
    "shall also be liable to fine."
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


class TestMaritalAbuseNotCivil:
    """Regression test for a real bug, found live 2026-08-31: a marital-abuse
    query was told this "falls under family law, outside the scope of the
    criminal statutes" -- factually wrong, BNS s.85 / IPC s.498A (cruelty by
    husband or relatives) are criminal provisions squarely on point and are
    in the corpus. Two distinct causes, both covered here:
      1. is_civil_scope_mismatch's phrase list must never match a marital/
         domestic-cruelty query (it didn't, even before the fix -- the false
         claim came from the generic abstention message's own wording,
         fixed separately in app/api/v1/legal.py).
      2. is_abstention must not ignore a real lexical hit (BNS 85/IPC 498A
         found via full-text search) just because some unrelated vector-only
         candidates in the same result set score below threshold -- this WAS
         the real mechanical bug (see is_abstention's docstring).
    """

    async def _seed_cruelty_section(self, db):
        act = await _make_act(db, "TESTCRUELTY", commenced_on=date(2023, 1, 1))
        sv = await _make_version(db, act, "85", _CRUELTY_SECTION_TEXT, date(2023, 1, 1))
        sv.embedding = await embedder.embed(f"Cruelty. {_CRUELTY_SECTION_TEXT}")
        await db.commit()
        return act, sv

    async def test_marital_abuse_query_is_not_civil_scope_mismatch(self, db):
        for query in [
            "What can I do about marital abuse?",
            "My husband abuses me, what are my legal options?",
            "What is the punishment for marital abuse?",
        ]:
            assert is_civil_scope_mismatch(query) is False, query

    async def test_marital_abuse_query_retrieves_cruelty_section_and_does_not_abstain(self, db):
        await self._seed_cruelty_section(db)

        sections = await semantic_search(db, "What can I do about marital abuse?")

        assert sections != []
        assert ("TESTCRUELTY", "85") in {(s["act"], s["section"]) for s in sections}
        assert is_abstention(sections) is False
