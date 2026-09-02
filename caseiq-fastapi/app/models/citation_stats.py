"""C5: persisted counters for the citation verification layer
(app.services.citation_verification). A single row, incremented on every
query that reaches the LLM -- not just logged, because "how often does the
prompt's grounding constraint actually get violated" is a standing question
this project keeps coming back to (see docs/evaluation.md), not a one-off
debugging fact that belongs only in log lines.
"""
from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class CitationVerificationStats(UUIDPk, Timestamped, Base):
    __tablename__ = "citation_verification_stats"

    citations_total: Mapped[int] = mapped_column(Integer, default=0)
    # Cited a section number that doesn't exist in the corpus at all (for
    # that act, as-of today) -- pure fabrication, same failure class as the
    # invented "BNS 2023, Section 499" incident this whole project traces
    # back to.
    citations_stripped_nonexistent: Mapped[int] = mapped_column(Integer, default=0)
    # Cited a section that IS real and in force, but was never in THIS
    # query's own retrieved set -- the model pulled a real section number
    # from memory and got lucky that it exists, which is still ungrounded:
    # nothing in this specific answer's evidence supports it being the
    # right citation for this specific question.
    citations_stripped_not_retrieved: Mapped[int] = mapped_column(Integer, default=0)
