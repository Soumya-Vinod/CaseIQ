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
