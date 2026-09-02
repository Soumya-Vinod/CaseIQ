"""C5: the prompt tells the model to cite only retrieved sections; nothing
enforced that until app.services.citation_verification existed. These
three cases are the ones the working agreement named explicitly:
  1. a response citing a non-existent section has it removed
  2. a response citing a real-but-not-retrieved section has it removed
  3. a response citing only retrieved sections passes through untouched

Verified directly against the real Neon corpus too (not just this suite --
see docs/evaluation.md), since the integration-test DB isn't always
available; recorded here so it stays a real, re-runnable test, not just a
one-off verification.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.citation_verification import verify_citations
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration


async def _seed_theft_and_murder(db):
    # act_code MUST be a real one ("IPC") -- unlike test_abstention.py's
    # fake "TESTABSTAIN" (fine there, since retrieval doesn't care what an
    # act is called), normalize_act() only recognises the five real corpus
    # acts, matching what _STRUCTURED_PROMPT actually asks the model to
    # name. Section numbers are still test-only fakes, safe in the isolated
    # integration-test DB (truncated between tests, see conftest.py).
    ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
    theft = await _make_version(db, ipc, "379", "Theft text.", date(1862, 1, 1))
    murder = await _make_version(db, ipc, "302", "Murder text.", date(1862, 1, 1))
    await db.commit()
    return ipc, theft, murder


class TestCitationVerification:
    async def test_nonexistent_section_is_stripped(self, db):
        ipc, theft, murder = await _seed_theft_and_murder(db)
        structured_data = {
            "laws_applicable": [
                {"act": "IPC 1860", "section": "379"},
                {"act": "IPC 1860", "section": "999999"},  # never seeded -- doesn't exist
            ]
        }
        retrieved = [{"act": "IPC", "section": "379"}]

        result, counters = await verify_citations(db, structured_data, retrieved, date.today())

        kept_sections = [law["section"] for law in result["laws_applicable"]]
        assert kept_sections == ["379"]
        assert counters == {"total": 2, "stripped_nonexistent": 1, "stripped_not_retrieved": 0}

    async def test_real_but_not_retrieved_section_is_stripped(self, db):
        ipc, theft, murder = await _seed_theft_and_murder(db)
        structured_data = {
            "laws_applicable": [
                {"act": "IPC 1860", "section": "379"},
                # 302 is real and seeded, but NOT in `retrieved` below --
                # the model pulled it from memory, not from this query's
                # own evidence.
                {"act": "IPC 1860", "section": "302"},
            ]
        }
        retrieved = [{"act": "IPC", "section": "379"}]

        result, counters = await verify_citations(db, structured_data, retrieved, date.today())

        kept_sections = [law["section"] for law in result["laws_applicable"]]
        assert kept_sections == ["379"]
        assert counters == {"total": 2, "stripped_nonexistent": 0, "stripped_not_retrieved": 1}

    async def test_fully_grounded_response_passes_through_untouched(self, db):
        ipc, theft, murder = await _seed_theft_and_murder(db)
        structured_data = {
            "laws_applicable": [
                {"act": "IPC 1860", "section": "379"},
                {"act": "IPC 1860", "section": "302"},
            ]
        }
        retrieved = [{"act": "IPC", "section": "379"}, {"act": "IPC", "section": "302"}]

        result, counters = await verify_citations(db, structured_data, retrieved, date.today())

        assert result["laws_applicable"] == structured_data["laws_applicable"]
        assert counters == {"total": 2, "stripped_nonexistent": 0, "stripped_not_retrieved": 0}

    async def test_no_laws_applicable_is_a_no_op(self, db):
        result, counters = await verify_citations(db, {}, [], date.today())
        assert result == {}
        assert counters == {"total": 0, "stripped_nonexistent": 0, "stripped_not_retrieved": 0}
