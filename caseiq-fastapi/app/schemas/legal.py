from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class QueryIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    language: str = "en"
    session_id: str = ""


class RetrievedSection(BaseModel):
    act: str
    section: str
    title: str
    snippet: str
    category: str = ""
    similarity: float | None = None


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
