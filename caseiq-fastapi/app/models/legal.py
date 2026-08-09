from datetime import date
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class QueryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    BLOCKED = "blocked"


class LegalSection(UUIDPk, Timestamped, Base):
    """A single section of an Act (BNS/BNSS/BSA/IPC/CrPC), with a real embedding."""

    __tablename__ = "legal_sections"
    __table_args__ = (UniqueConstraint("act", "section_number", name="uq_act_section"),)

    act: Mapped[str] = mapped_column(String(20), index=True)
    section_number: Mapped[str] = mapped_column(String(20), index=True)
    section_title: Mapped[str] = mapped_column(String(500))
    section_text: Mapped[str] = mapped_column(Text)
    simplified_text: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(255), default="", index=True)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # The fix: a real vector column. Nullable so ingestion can backfill embeddings.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.EMBEDDING_DIM))


class LegalQuery(UUIDPk, Timestamped, Base):
    __tablename__ = "legal_queries"

    user_id: Mapped[PgUUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    original_query: Mapped[str] = mapped_column(Text)
    detected_language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[QueryStatus] = mapped_column(String(20), default=QueryStatus.PENDING)
    session_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    is_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str] = mapped_column(String(255), default="")

    response: Mapped["QueryResponse"] = relationship(
        back_populates="query", uselist=False, cascade="all, delete-orphan"
    )


class QueryResponse(UUIDPk, Timestamped, Base):
    __tablename__ = "query_responses"

    query_id: Mapped[PgUUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("legal_queries.id", ondelete="CASCADE"), unique=True
    )
    conversational_summary: Mapped[str] = mapped_column(Text)
    structured_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    retrieved_sections: Mapped[list] = mapped_column(JSONB, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    response_language: Mapped[str] = mapped_column(String(10), default="en")
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    is_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    # Part K / K4: which corpus snapshot was live when this answer was generated,
    # so any past answer can be reproduced/audited. Nullable -- responses
    # generated before Part K landed have no snapshot to point at.
    corpus_version_id: Mapped[PgUUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("corpus_versions.id", ondelete="SET NULL")
    )
    # The date retrieval was filtered as-of (K3/K7) -- an answer must be able to
    # state what date it was computed against, independent of when it was recorded.
    as_of: Mapped[date | None] = mapped_column(Date)

    query: Mapped[LegalQuery] = relationship(back_populates="response")
