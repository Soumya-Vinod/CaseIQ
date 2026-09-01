from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.complaint import ComplaintType
from app.schemas.common import ORMModel
from app.schemas.legal import RetrievedSection


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
    # FIXED 2026-09-01: `applicable_sections` used to be accepted here as a
    # caller-supplied, free-form list and handed straight to the LLM as fact
    # -- flagged 2026-08-11, never checked against section_versions/
    # judicial_status, so a caller (or a not-yet-rewired frontend) could hand
    # the LLM "IPC 497" and nothing would catch that it's struck down or
    # doesn't exist before it landed in a generated legal complaint PDF. The
    # field is removed from client input entirely: the server now runs the
    # same semantic_search() /legal/query uses against the incident
    # narrative and stores what it actually found (Complaint.retrieved_sections).
    # See docs/caseiq-industry-readiness.md Part C/K.
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
    # Same treatment as QueryOut.legal_sections -- the sections CaseIQ actually
    # matched against the incident narrative, with their text, so the user can
    # see what law the draft rests on rather than trusting an opaque letter.
    legal_sections: list[RetrievedSection] = []
    # True when retrieval found nothing confidently relevant to the incident
    # narrative -- mirrors QueryOut.abstained. The draft still generates (a
    # complaint form isn't a yes/no legal question), but cites no sections and
    # says so plainly, rather than the LLM inventing a plausible one.
    grounded: bool = True
