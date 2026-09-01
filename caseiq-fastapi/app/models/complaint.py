from enum import StrEnum

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import Timestamped, UUIDPk


class ComplaintType(StrEnum):
    FIR = "fir"
    WRITTEN = "written_complaint"
    MAGISTRATE = "magistrate_complaint"
    CONSUMER = "consumer_complaint"
    CYBER = "cyber_complaint"


class ComplaintStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    DOWNLOADED = "downloaded"


class Complaint(UUIDPk, Timestamped, Base):
    __tablename__ = "complaints"

    user_id: Mapped[PgUUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    complaint_type: Mapped[ComplaintType] = mapped_column(String(30))
    complainant_name: Mapped[str] = mapped_column(String(255))
    complainant_address: Mapped[str] = mapped_column(Text)
    complainant_phone: Mapped[str] = mapped_column(String(15), default="")
    police_station_name: Mapped[str] = mapped_column(String(255), default="")
    police_station_address: Mapped[str] = mapped_column(String(500), default="")
    incident_date: Mapped["Date"] = mapped_column(Date)
    incident_location: Mapped[str] = mapped_column(String(500))
    incident_description: Mapped[str] = mapped_column(Text)
    accused_details: Mapped[str] = mapped_column(Text, default="")
    witnesses: Mapped[str] = mapped_column(Text, default="")
    evidence_description: Mapped[str] = mapped_column(Text, default="")
    relief_sought: Mapped[str] = mapped_column(Text, default="")
    # Short citation strings ("BNS 85", "IPC 498A") derived server-side from
    # retrieved_sections below, for the PDF's compact "Sections:" line. Never
    # written from client input -- see retrieved_sections' docstring and the
    # 0006_complaint_grounding migration for why that changed.
    applicable_sections: Mapped[list] = mapped_column(JSONB, default=list)
    # Full grounded retrieval result (same semantic_search() /legal/query uses),
    # same shape as QueryResponse.retrieved_sections (app/models/legal.py): act,
    # section, title, snippet, judicial_status, similarity. Stored so the PDF
    # and the frontend "sources" panel can be rebuilt from this row alone --
    # Render's disk is ephemeral, so a later /download call may hit a
    # container that never ran the original retrieval.
    retrieved_sections: Mapped[list] = mapped_column(JSONB, default=list)
    generated_draft: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(5), default="en")
    status: Mapped[ComplaintStatus] = mapped_column(String(20), default=ComplaintStatus.DRAFT)
