"""Persisted counters for the "confident overview, empty laws_applicable"
finding (docs/evaluation.md). The retrieval-side fix (smart_snippet,
app.legal_corpus.parsing.punishment_clause) closes the reproducible cause
structurally, but doesn't get every section to zero (28/2155 still at risk
after the ceiling, checked directly) -- and there will always be genuine
no-coverage queries where nothing SHOULD be cited. Same reasoning as
PunishmentVerificationStats: "how often does this still fire" must be a
standing, queryable number, not a one-off sample, precisely because a
counter sitting at a low number looks identical whether it means "the fix
worked" or "something else silently broke" -- this table is what tells
the two apart over real traffic instead of leaving that ambiguous.
"""
from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class GroundingStats(UUIDPk, Timestamped, Base):
    __tablename__ = "grounding_stats"

    # Every non-abstained, non-incident-date-prompt LLM generation --
    # the denominator for the two counters below.
    responses_total: Mapped[int] = mapped_column(Integer, default=0)
    # laws_applicable was empty in the RAW generation, before citation
    # verification even ran -- the model never attempted a citation, while
    # conversational_summary/situation_overview may still assert a
    # conclusion. Tracked separately from the counter below because the two
    # have different likely causes (still-truncated context vs. something
    # else) and conflating them would hide which one is actually recurring.
    responses_ungrounded_never_cited: Mapped[int] = mapped_column(Integer, default=0)
    # laws_applicable was non-empty from generation, but verify_citations
    # (C5) stripped every entry -- the model cited something real-but-not-
    # retrieved or outright nonexistent, for all of its citations.
    responses_ungrounded_stripped_to_zero: Mapped[int] = mapped_column(Integer, default=0)
    responses_grounded: Mapped[int] = mapped_column(Integer, default=0)
