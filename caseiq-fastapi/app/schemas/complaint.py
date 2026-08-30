from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.complaint import ComplaintType
from app.schemas.common import ORMModel


class ComplaintIn(BaseModel):
    complaint_type: ComplaintType
    complainant_name: str = Field(max_length=255)
    complainant_address: str
    complainant_phone: str = ""
    police_station_name: str = ""
    police_station_address: str = ""
    incident_date: date
    incident_location: str = Field(max_length=500)
    incident_description: str
    accused_details: str = ""
    witnesses: str = ""
    evidence_description: str = ""
    relief_sought: str = ""
    # FLAGGED 2026-08-11, not fixed: caller-supplied, free-form, and never
    # checked against section_versions/judicial_status before reaching
    # generate_complaint_draft() (app/api/v1/complaints.py). This is a
    # different, more basic gap than the K2 audit's "does this path filter
    # struck-down sections" question -- this path doesn't query the DB for
    # section content AT ALL, so a caller (or a not-yet-rewired frontend)
    # could hand the LLM "IPC 497" and nothing here would catch that it's
    # struck down, or that it doesn't exist, before it lands in a generated
    # legal complaint PDF. See docs/caseiq-industry-readiness.md Part C/K.
    applicable_sections: list[str] = []
    language: str = "en"


class ComplaintOut(ORMModel):
    id: UUID
    complaint_type: ComplaintType
    complainant_name: str
    status: str
    generated_draft: str | None = None
    pdf_available: bool = False
    download_url: str | None = None
    disclaimer: str
