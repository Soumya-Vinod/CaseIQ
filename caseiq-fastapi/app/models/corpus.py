"""Part K — bitemporal legal corpus: acts, versioned sections, amendments,
judicial status, corpus snapshots, and the change-review queue.

section_versions is the source of truth for retrieval, replacing the flat
legal_sections table (see app/models/legal.py — kept as a table, deliberately
no longer written to; see app/services/retrieval.py for why the old
LegalSection-based path was removed rather than left as a silent fallback).

Two independent time axes on section_versions, never conflated:
  valid_from / valid_to  — valid_time: when the provision was/is in force in
                           the real world. Seeded from the source document's
                           own content_as_on (documents/provenance.json),
                           NEVER from ingestion time — see K1/K3 in
                           docs/caseiq-industry-readiness.md.
  recorded_at            — transaction_time: when CaseIQ found out. Always
                           "now" at insert; this is what an audit trail is
                           built from, not what "in force" means.
"""
from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class Act(UUIDPk, Timestamped, Base):
    __tablename__ = "acts"

    act_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # 'BNS', 'IPC', ...
    short_title: Mapped[str] = mapped_column(String(255))
    year: Mapped[int | None] = mapped_column(Integer)
    enacted_on: Mapped[date | None] = mapped_column(Date)
    commenced_on: Mapped[date | None] = mapped_column(Date)
    repealed_on: Mapped[date | None] = mapped_column(Date)
    repealed_by_act_id: Mapped[PgUUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("acts.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), default="in_force")  # in_force | repealed | not_yet_commenced
    jurisdiction: Mapped[str] = mapped_column(String(50), default="India")
    source_url: Mapped[str | None] = mapped_column(Text)

    sections: Mapped[list["SectionVersion"]] = relationship(back_populates="act")


class SectionVersion(UUIDPk, Timestamped, Base):
    __tablename__ = "section_versions"
    __table_args__ = (
        UniqueConstraint("act_id", "section_number", "version_no", name="uq_act_section_version"),
        Index("ix_section_versions_lookup", "act_id", "section_number", "valid_from", "valid_to"),
    )

    act_id: Mapped[PgUUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("acts.id", ondelete="CASCADE"), index=True
    )
    section_number: Mapped[str] = mapped_column(String(20), index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    marginal_note: Mapped[str] = mapped_column(String(500), default="")
    section_text: Mapped[str] = mapped_column(Text)
    simplified_text: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(255), default="", index=True)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    is_repealed: Mapped[bool] = mapped_column(default=False)

    # valid_time -- see module docstring. valid_to NULL = currently in force.
    valid_from: Mapped[date] = mapped_column(Date, index=True)
    valid_to: Mapped[date | None] = mapped_column(Date, index=True)
    # transaction_time -- when CaseIQ recorded this row, never used for "in force" logic.
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    superseded_by_id: Mapped[PgUUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("section_versions.id", ondelete="SET NULL")
    )
    amended_by_amendment_id: Mapped[PgUUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("amendments.id", ondelete="SET NULL")
    )

    # Provenance -- checklist item B4. Stamped from documents/provenance.json at
    # ingestion time, not re-derived.
    source_url: Mapped[str | None] = mapped_column(Text)
    source_sha256: Mapped[str | None] = mapped_column(String(64))
    content_as_on: Mapped[date | None] = mapped_column(Date)  # seeds valid_from; kept for auditing
    parser_name: Mapped[str | None] = mapped_column(String(50))
    parser_version: Mapped[str | None] = mapped_column(String(20))

    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.EMBEDDING_DIM))

    act: Mapped[Act] = relationship(back_populates="sections", foreign_keys=[act_id])


class JudicialStatus(UUIDPk, Timestamped, Base):
    """Judicial invalidity is a DIFFERENT event from repeal -- a struck-down or
    read-down provision can still be sitting in the Bare Act with full text
    (SectionVersion.is_repealed stays False), and only a court judgment records
    that it isn't enforceable. This is what closes D7 -- see
    docs/m1-verification.md's IPC 497 finding, which is exactly the case this
    table exists for. Retrieval MUST exclude 'struck_down' entirely and MUST
    attach scope_note to any 'read_down' result (K2's hard rule).
    """
    __tablename__ = "judicial_status"
    __table_args__ = (Index("ix_judicial_status_lookup", "act_id", "section_number"),)

    act_id: Mapped[PgUUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("acts.id", ondelete="CASCADE"), index=True
    )
    section_number: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20))  # valid | struck_down | read_down | stayed | referred
    case_name: Mapped[str] = mapped_column(String(500))
    citation: Mapped[str] = mapped_column(String(255), default="")
    # Explicit, queryable "not yet confirmed against a primary source" flag --
    # same pattern as documents/provenance.json's {value, verified} fields.
    # Written false for anything not directly checked against a citation
    # this session actually fetched, rather than guessed from memory.
    citation_verified: Mapped[bool] = mapped_column(default=False)
    court: Mapped[str] = mapped_column(String(255), default="")
    decided_on: Mapped[date | None] = mapped_column(Date)
    scope_note: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(Text)


class Amendment(UUIDPk, Timestamped, Base):
    __tablename__ = "amendments"

    amending_act_name: Mapped[str] = mapped_column(String(500))
    amending_act_year: Mapped[int | None] = mapped_column(Integer)
    gazette_ref: Mapped[str] = mapped_column(String(255), default="")
    effective_from: Mapped[date | None] = mapped_column(Date)
    notification_url: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")

    effects: Mapped[list["AmendmentEffect"]] = relationship(back_populates="amendment")


class AmendmentEffect(UUIDPk, Timestamped, Base):
    __tablename__ = "amendment_effects"

    amendment_id: Mapped[PgUUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("amendments.id", ondelete="CASCADE"), index=True
    )
    target_act_id: Mapped[PgUUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("acts.id", ondelete="CASCADE")
    )
    target_section_number: Mapped[str] = mapped_column(String(20))
    effect_type: Mapped[str] = mapped_column(String(20))  # inserted|substituted|omitted|renumbered|repealed
    old_text: Mapped[str] = mapped_column(Text, default="")
    new_text: Mapped[str] = mapped_column(Text, default="")

    amendment: Mapped[Amendment] = relationship(back_populates="effects")


class CorpusVersion(UUIDPk, Base):
    """A named, reproducible snapshot marker -- query_responses stamp the
    corpus_version_id that was live when they were generated (K4), so any past
    answer can be reproduced/audited and the eval harness can pin a version.
    No Timestamped mixin: created_at IS the snapshot moment, no updated_at
    concept applies to an immutable snapshot marker.
    """
    __tablename__ = "corpus_versions"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    label: Mapped[str] = mapped_column(String(100), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    section_count: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), default="")


class CorpusStagingChange(UUIDPk, Timestamped, Base):
    """K5's review queue. A detected (or manually supplied) change to a
    section sits here, PENDING, until a human approves or rejects it --
    nothing here is ever auto-promoted into section_versions. See
    app/legal_corpus/change_detection.py for the (currently stubbed) source
    polling that would populate this table automatically.
    """
    __tablename__ = "corpus_staging_changes"

    act_id: Mapped[PgUUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("acts.id", ondelete="CASCADE"), index=True
    )
    section_number: Mapped[str] = mapped_column(String(20), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_sha256: Mapped[str | None] = mapped_column(String(64))
    staged_text: Mapped[str] = mapped_column(Text)
    diff_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|approved|rejected
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_by_id: Mapped[PgUUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str] = mapped_column(Text, default="")
