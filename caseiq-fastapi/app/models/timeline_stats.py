"""Persisted counters for the legal-timeline verification layer
(app.services.timeline_verification). Same discipline as
PunishmentVerificationStats (app.models.punishment_stats) and for the same
reason: "how often does a proposed timeline stage actually have a real,
grounded time limit behind it" is a standing question this project needs a
real rate for, not a one-off debugging fact -- see docs/evaluation.md's
2026-09-20 scoping entry for why this feature was built deterministic-
verification-first rather than shipped and hoped about.
"""
from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class TimelineVerificationStats(UUIDPk, Timestamped, Base):
    __tablename__ = "timeline_verification_stats"

    stages_proposed_total: Mapped[int] = mapped_column(Integer, default=0)
    # A real, extracted time-limit clause matches the claimed value+unit for
    # the cited (act, section) -- the ONLY outcome this feature ever shows a
    # user. See app.services.timeline_verification's own module docstring
    # for why "grounded" is the sole bar here, unlike punishment
    # verification's three-way split -- this feature's whole premise is
    # "only emit what's grounded," not "assume innocent absent proof
    # otherwise."
    stages_grounded: Mapped[int] = mapped_column(Integer, default=0)
    # Dropped, never shown: either the cited section has no extractable time
    # limit at all, the claim itself didn't state a parseable value+unit, or
    # neither matched. Distinct from punishment_verification's
    # "unverifiable" in consequence (there it's kept; here it's dropped) but
    # tracked the same way -- "how often does this fire" must be answerable,
    # not just assumed rare.
    stages_dropped_unverifiable: Mapped[int] = mapped_column(Integer, default=0)
    # A real, extracted clause exists for the cited section, but its
    # value/unit disagrees with the claim -- the section is real, the number
    # is wrong. Tracked separately from stages_dropped_unverifiable because
    # "the model cited a real dated section and still got the number wrong"
    # is a different, worse failure mode than "nothing to check against at
    # all," and conflating the two would hide exactly the thing this counter
    # exists to surface.
    stages_dropped_mismatch: Mapped[int] = mapped_column(Integer, default=0)
