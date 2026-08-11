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
    # K7: True when this version came into force within the last 12 months
    # AND it's not the section's first version (a brand-new section isn't
    # "amended", however recent its valid_from) -- see
    # app.services.retrieval._is_recently_amended. The old/new diff itself
    # isn't carried on every search result (would mean an extra query per
    # row); fetch it via GET /knowledge/sections/{act}/{section}.
    recently_amended: bool = False
    judicial_status: JudicialStatusOut | None = None


class PreviousVersionOut(BaseModel):
    version_no: int
    section_text: str
    valid_from: str
    valid_to: str | None = None


class SectionDetailOut(BaseModel):
    """GET /knowledge/sections/{act}/{section} -- see that endpoint's
    docstring for why this is the one path that can surface a struck-down
    section rather than excluding it."""
    act: str
    section: str
    title: str
    section_text: str
    category: str = ""
    version_no: int | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    recently_amended: bool = False
    previous_version: PreviousVersionOut | None = None
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
    # Part K / K7: the date retrieval was filtered as-of -- an answer must be
    # able to state what date it was computed against.
    as_of: date
    # K4/K7: which corpus snapshot was live when this answer was generated,
    # for reproducibility/audit. None if no CorpusVersion has been created
    # yet (e.g. a fresh dev DB before the first ingest run) -- absence is a
    # queryable fact, not silently defaulted to a fake id.
    corpus_version_id: UUID | None = None


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
