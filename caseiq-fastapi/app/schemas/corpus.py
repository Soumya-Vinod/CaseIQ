from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class StagingChangeOut(ORMModel):
    id: UUID
    act_code: str
    section_number: str
    source_url: str | None
    diff_summary: str
    status: str
    detected_at: datetime


class ApproveIn(BaseModel):
    effective_from: date | None = None  # defaults to today if omitted
    amending_act_name: str = ""
    amending_act_year: int | None = None
    gazette_ref: str = ""
    summary: str = ""


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class CorpusVersionOut(ORMModel):
    id: UUID
    label: str
    notes: str
    section_count: int
    checksum: str
    created_at: datetime


class SectionHistoryEntry(BaseModel):
    version_no: int
    marginal_note: str
    valid_from: str
    valid_to: str | None
    is_repealed: bool
    source_url: str | None
    parser_version: str | None
