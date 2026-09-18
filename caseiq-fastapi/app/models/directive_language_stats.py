"""Persisted counters for directive-language detection (app.services.
directive_language). Same discipline as GroundingStats/PunishmentVerification
Stats: "how often does this fire" must be a standing, queryable number, not
a one-off debugging fact -- especially here, since this check is
DETECTION ONLY (docs/evaluation.md, directive-language entry) and the
counter is the only thing that will ever tell anyone whether it's worth
building enforcement at all, or what shape that enforcement should take.
"""
from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class DirectiveLanguageStats(UUIDPk, Timestamped, Base):
    __tablename__ = "directive_language_stats"

    # Every real (non-abstained, non-incident-date-prompt) generation
    # checked -- the denominator.
    responses_total: Mapped[int] = mapped_column(Integer, default=0)
    # At least one directive-phrase hit in a scoped free-text field.
    responses_flagged: Mapped[int] = mapped_column(Integer, default=0)
    # Total individual hits across all flagged responses -- a single
    # response can hit more than once ("you should file an FIR and you
    # must preserve evidence" is two hits, one response) -- tracked
    # separately from responses_flagged so neither number silently stands
    # in for the other.
    hits_total: Mapped[int] = mapped_column(Integer, default=0)
