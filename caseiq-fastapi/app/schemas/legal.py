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
    # C8: set by the frontend's clarification prompt when the user picks "I
    # don't know" rather than entering a date -- tells the backend not to
    # ask again this turn and to proceed across both regimes, same as
    # incident_date=None always has, just now an explicit choice instead of
    # a default nobody was ever asked about. See
    # app.services.retrieval.implies_past_incident for what triggers the
    # prompt in the first place.
    skip_incident_date: bool = False


class JudicialStatusOut(BaseModel):
    status: str
    case_name: str
    citation: str
    court: str
    decided_on: str | None = None
    scope_note: str = ""


class OffenceAttributesOut(BaseModel):
    cognizable_raw: str
    cognizable: bool | None = None  # None = genuinely conditional, per the schedule's own wording
    bailable_raw: str
    bailable: bool | None = None
    compoundable: bool | None = None
    compoundable_with_permission: bool | None = None
    compoundable_by: str | None = None
    triable_by: str
    source: str


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
    # C1: real cognizable/bailable/court classification, joined from
    # offence_attributes (app.services.retrieval.attach_offence_attributes)
    # -- never LLM output. None means literally "no row in our data" -- an
    # explicit third state a consumer must render as such, not as blank
    # (which would read as "not a special classification" -- worse than
    # the LLM guess this replaced). Coverage is partial by design; see
    # docs/evaluation.md for the current figure.
    offence_attributes: OffenceAttributesOut | None = None


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
    # C1, same treatment as RetrievedSection.offence_attributes -- gated to
    # IPC/BNS at the DB level (attach_offence_attributes), same three-state
    # contract: a real value, a conditional with verbatim wording, or
    # explicitly absent, never blank.
    offence_attributes: OffenceAttributesOut | None = None


class HelplineOut(BaseModel):
    name: str
    number: str
    when_to_use: str
    source_url: str
    verified_on: str


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
    # True when app.services.retrieval.is_abstention short-circuited this query
    # before the LLM was ever called -- confidence_score and legal_sections are
    # deliberately not fabricated in that case (empty sections, low confidence).
    # A designed refusal, not an error: render it as one, not as a failure state.
    abstained: bool = False
    # C8: True when app.services.retrieval.implies_past_incident recognised
    # this query as describing a past incident and no incident_date (or
    # explicit skip) was given -- the LLM was never called, same
    # short-circuit shape as `abstained`. structured_data/legal_sections
    # stay empty; the frontend's job is to show the date prompt, get an
    # answer, and resubmit -- see QueryPage's handling of this flag.
    needs_incident_date: bool = False
    # Part K / K7: the date retrieval was filtered as-of -- an answer must be
    # able to state what date it was computed against.
    as_of: date
    # K4/K7: which corpus snapshot was live when this answer was generated,
    # for reproducibility/audit. None if no CorpusVersion has been created
    # yet (e.g. a fresh dev DB before the first ingest run) -- absence is a
    # queryable fact, not silently defaulted to a fake id.
    corpus_version_id: UUID | None = None
    # C4: a small, static, hand-verified table (app.services.helplines) --
    # never LLM output, never in a prompt. Chosen by topic
    # (app.services.helplines.select_helplines, on the query's own text),
    # capped at two -- never the wall of five every abstention used to show
    # regardless of what the query was about (checklist item 4). Empty for
    # an ordinary answered query with no topic signal; on abstention, falls
    # back to NALSA (15100) rather than ever showing nothing, since that's
    # still the one path where the user got no answer at all. See
    # docs/evaluation.md for the incident this whole field replaces
    # ("1516" / "1800-111-222", both fabricated, both wrong).
    helplines: list[HelplineOut] = []


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
