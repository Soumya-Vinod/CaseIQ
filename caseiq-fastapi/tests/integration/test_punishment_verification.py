"""The gap the mismatch branch itself named: 16 pure-function tests
(tests/test_punishment_clause.py) prove the PARSER can tell a real
punishment fabrication apart from a grounded claim, but nothing exercised
`app.services.punishment_verification.verify_punishments` -- the actual
production code path wired into /legal/query (act+section DB lookup,
as-of filtering, the suppress-vs-keep decision, the counters dict). A
guardrail whose only test is one level below where it actually runs can
still be broken by anything in that missing layer (wrong column name,
wrong as_of comparison, a normalize_act mismatch) while every existing
test stays green.

This is the standing version of the live production check already run
once by hand (2026-09-14: real Neon, real /legal/query call, punishments_
suppressed_mismatch confirmed 0 -> 0 because that generation didn't
happen to fabricate anything that day -- a real but inconclusive result,
since production traffic is not obligated to reproduce a specific failure
on demand). A synthetic, deliberately-fabricated claim closes that gap:
it doesn't wait for the model to misbehave, it forces the exact shape of
misbehaviour already confirmed real (docs/evaluation.md's IPC 408/409
finding) through the real function, against a real seeded row, every CI
run. If `punishments_suppressed_mismatch` stays at 0 for weeks of real
traffic, THIS test is what tells you whether that's the prompt fix
working or the branch silently broken -- the same reasoning as this
project's own rate-limiting scaffolding finding: present and plausible is
not the same claim as enforcing.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.punishment_verification import verify_punishments
from tests.integration.test_corpus import _make_act, _make_version

pytestmark = pytest.mark.integration

# Real statute text, copied verbatim from the corpus -- same constant as
# tests/test_punishment_clause.py's IPC_408, not re-typed, so a drift
# between the two would be caught by keeping this identical rather than by
# hand-verifying it twice.
IPC_408_TEXT = (
    "408. Criminal breach of trust by clerk or servant.—Whoever, being a clerk or servant or "
    "employed as a clerk or servant, and being in any manner entrusted in such capacity with "
    "property, or with any dominion over property, commits criminal breach of trust in respect "
    "of that property, shall be punished with imprisonment of either description for a term "
    "which may extend to seven years, and shall also be liable to fine."
)


async def _seed_408(db):
    ipc = await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))
    await _make_version(db, ipc, "408", IPC_408_TEXT, date(1862, 1, 1))
    await db.commit()
    return ipc


class TestVerifyPunishmentsProductionPath:
    async def test_fabricated_term_is_suppressed(self, db):
        """The real, confirmed shape of the bug this whole system exists to
        catch: IPC 408's real text says seven years; the model claimed
        three (this exact fabrication, docs/evaluation.md). Runs through
        verify_punishments() itself -- DB fetch, parser, comparison,
        counters -- not the parser functions directly.
        """
        await _seed_408(db)
        structured_data = {
            "punishments": [
                {"act": "IPC 1860", "section": "408", "offence": "Criminal breach of trust by clerk",
                 "imprisonment": "Up to 3 years", "fine": "As court decides"},
            ]
        }

        result, counters = await verify_punishments(db, structured_data, date.today())

        assert counters == {"total": 1, "suppressed_mismatch": 1, "unverifiable": 0, "grounded": 0}
        assert result["punishments"] == []  # the fabricated line must not reach the user

    async def test_grounded_term_passes_through(self, db):
        """Same section, the TRUE figure -- must survive untouched, so this
        test also proves the branch isn't just suppressing everything.
        """
        await _seed_408(db)
        structured_data = {
            "punishments": [
                {"act": "IPC 1860", "section": "408", "offence": "Criminal breach of trust by clerk",
                 "imprisonment": "Up to 7 years", "fine": "As court decides"},
            ]
        }

        result, counters = await verify_punishments(db, structured_data, date.today())

        assert counters == {"total": 1, "suppressed_mismatch": 0, "unverifiable": 0, "grounded": 1}
        assert len(result["punishments"]) == 1
        assert result["punishments"][0]["imprisonment"] == "Up to 7 years"

    async def test_unparseable_claim_is_unverifiable_not_suppressed(self, db):
        """CRITICAL rule from this module's own docstring: an unparseable
        claim must be UNVERIFIABLE, never treated as a mismatch. A claim
        this vague ("as determined by the court") isn't a lie -- it's just
        not machine-checkable, and the entry must still reach the user.
        """
        await _seed_408(db)
        structured_data = {
            "punishments": [
                {"act": "IPC 1860", "section": "408", "offence": "Criminal breach of trust by clerk",
                 "imprisonment": "As determined by the court", "fine": "As court decides"},
            ]
        }

        result, counters = await verify_punishments(db, structured_data, date.today())

        assert counters == {"total": 1, "suppressed_mismatch": 0, "unverifiable": 1, "grounded": 0}
        assert len(result["punishments"]) == 1  # kept -- unverifiable must never mean removed

    async def test_section_not_in_corpus_is_unverifiable_not_suppressed(self, db):
        """No row seeded for this section at all -- the DB fetch itself
        returns None. Must degrade to unverifiable, the same as an
        unparseable claim, never a false mismatch.
        """
        await _make_act(db, "IPC", commenced_on=date(1862, 1, 1))  # act exists, but no section 408 seeded
        structured_data = {
            "punishments": [
                {"act": "IPC 1860", "section": "408", "offence": "Criminal breach of trust by clerk",
                 "imprisonment": "Up to 3 years", "fine": "As court decides"},
            ]
        }

        result, counters = await verify_punishments(db, structured_data, date.today())

        assert counters == {"total": 1, "suppressed_mismatch": 0, "unverifiable": 1, "grounded": 0}
        assert len(result["punishments"]) == 1

    async def test_empty_punishments_list_is_a_noop(self, db):
        structured_data = {"punishments": []}
        result, counters = await verify_punishments(db, structured_data, date.today())
        assert counters == {"total": 0, "suppressed_mismatch": 0, "unverifiable": 0, "grounded": 0}
        assert result["punishments"] == []
