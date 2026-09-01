"""C1: offence classification (cognizable/bailable/court) as real structured
data, parsed from CrPC's First Schedule (and, when built, BNSS's equivalent)
-- never from LLM memory. See docs/evaluation.md's C1 write-up for why this
exists: `ipc_equivalent`/`bailable`/`cognizable` were removed from the LLM's
answer schema because the corpus had no way to ground them; this table is
what grounding them properly looks like.

Schema refined from the original working-agreement draft after reading the
actual source structure (see docs/evaluation.md): cognizable/bailable each
get a `_raw` (the schedule's own wording, verbatim, always populated) and a
resolved boolean that's deliberately NULL whenever the schedule's own answer
is genuinely conditional (e.g. IPC/BNS's cruelty provision: "cognizable IF
information is given by the person aggrieved...") -- forcing that to a flat
boolean would be the exact fabrication this table exists to prevent.

`compoundable` lives in a structurally separate part of the source (CrPC
s.320 / BNSS's equivalent, not the First Schedule) and is not yet populated
-- left NULL until that table is parsed too. Its meaning is asymmetric with
cognizable/bailable when it IS populated: absence from s.320's enumerated
list is itself a real `false` (the section opens as an opt-in list), not an
unresolved-conditional NULL.

Coverage is intentionally partial and stated as such, not hidden: only rows
the parser resolved COMPLETELY (a real triable_by value, not a fragment cut
short mid-parse) are ingested here -- see scripts/parse_crpc_schedule.py's
`reconstruct_rows` for what "complete" means and docs/evaluation.md for the
measured yield (221 of 381 CrPC sections, 58%, at first ingestion).
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class OffenceAttributes(UUIDPk, Timestamped, Base):
    __tablename__ = "offence_attributes"
    __table_args__ = (
        Index("ix_offence_attributes_act_section", "act", "section_number"),
    )

    # The classified act -- 'IPC' or 'BNS' -- NOT the schedule it was parsed
    # from. CrPC's First Schedule tabulates BY IPC SECTION NUMBER (it
    # classifies IPC offences; CrPC itself is procedure, not offences), and
    # BNSS's equivalent tabulates by BNS section number the same way. Found
    # this the hard way: shipping act='CrPC' here would have made the join
    # in attach_offence_attributes() never match anything, since retrieved
    # sections carry act='IPC', not 'CrPC' -- caught before ingestion, not
    # after. `source` records which schedule the row actually came from.
    act: Mapped[str] = mapped_column(String(20))
    section_number: Mapped[str] = mapped_column(String(20))
    offence_description: Mapped[str] = mapped_column(Text)
    punishment_text: Mapped[str] = mapped_column(Text, default="")

    cognizable_raw: Mapped[str] = mapped_column(Text)  # schedule's own wording, always present
    cognizable: Mapped[bool | None] = mapped_column(Boolean)  # NULL = genuinely conditional, not unresolved

    bailable_raw: Mapped[str] = mapped_column(Text)
    bailable: Mapped[bool | None] = mapped_column(Boolean)

    compoundable: Mapped[bool | None] = mapped_column(Boolean)  # NULL = not yet parsed (s.320/equivalent)
    compoundable_with_permission: Mapped[bool | None] = mapped_column(Boolean)
    compoundable_by: Mapped[str | None] = mapped_column(Text)

    triable_by: Mapped[str] = mapped_column(Text)

    source: Mapped[str] = mapped_column(String(255))  # e.g. "CrPC 1973 First Schedule, p.221"
    source_sha256: Mapped[str] = mapped_column(String(64), default="")
    parser_version: Mapped[str] = mapped_column(String(20), default="")
