"""Persisted counters for the punishment-verification layer
(app.services.punishment_verification). Same discipline as
CitationVerificationStats (app.models.citation_stats, C5) and for the same
reason: "how often does a stated sentence actually disagree with the
statute it cites" is a standing question, not a one-off debugging fact --
this is the prevalence data the answer-fidelity battery's own IPC 408/409
finding (docs/evaluation.md) had no way to produce on its own, since a
periodic sample can only ever show "this happened at least once", never a
real rate against production traffic.
"""
from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class PunishmentVerificationStats(UUIDPk, Timestamped, Base):
    __tablename__ = "punishment_verification_stats"

    punishments_total: Mapped[int] = mapped_column(Integer, default=0)
    # A real, extracted statute figure DISAGREES with the claim -- IPC
    # 408/409's own failure shape. The only outcome this layer suppresses.
    punishments_suppressed_mismatch: Mapped[int] = mapped_column(Integer, default=0)
    # Either side (the statute text or the model's own claim string)
    # couldn't be parsed at all -- NEVER suppressed, see
    # app.services.punishment_verification's own module docstring for why
    # treating this the same as a mismatch would be the vacuous-pass shape
    # this project keeps finding in other layers, just inverted.
    punishments_unverifiable: Mapped[int] = mapped_column(Integer, default=0)
    punishments_grounded: Mapped[int] = mapped_column(Integer, default=0)
