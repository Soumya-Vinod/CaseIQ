from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class QueryIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    language: str = "en"
    session_id: str = ""
    # Part K / K3: when the incident happened, if known -- routes retrieval to
    # the correct legal regime (pre/post 2024-07-01, see
    # app.services.retrieval.acts_for_incident_date). None = search both.
    incident_date: date | None = None
    # Part K / K3/K7: retrieve law as it stood on this date (default today).
    # Distinct from incident_date -- incident_date picks the REGIME (which
    # acts), as_of picks the VERSION within whichever acts are searched.
    as_of: date | None = None


class JudicialStatusOut(BaseModel):
    status: str
    case_name: str
    citation: str
    court: str
    decided_on: str | None = None
    scope_note: str = ""


class RetrievedSection(BaseModel):
    act: str
    section: str
    title: str
    snippet: str
    category: str = ""
    similarity: float | None = None
    version_no: int | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    judicial_status: JudicialStatusOut | None = None


class QueryOut(BaseModel):
    query_id: UUID
    original_query: str
    conversational_summary: str
    structured_data: dict[str, Any]
    confidence_score: float
    legal_sections: list[RetrievedSection]
    language: str
    related_questions: list[str]
    is_followup: bool
    processing_time_ms: int


class SituationIn(BaseModel):
    situation: str = Field(min_length=1, max_length=2000)


class SectionOut(ORMModel):
    id: UUID
    act: str
    section_number: str
    section_title: str
    section_text: str
    simplified_text: str
    category: str
    keywords: list
