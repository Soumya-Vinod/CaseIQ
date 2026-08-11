from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, select

from app.api.deps import DB, OptionalUser
from app.models.corpus import Act, JudicialStatus, SectionVersion
from app.schemas.legal import RetrievedSection, SectionDetailOut, SectionOut
from app.services.retrieval import get_section_with_history, in_force, judicial_status_dict, \
    not_struck_down, semantic_search

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.get("/sections", response_model=list[SectionOut])
async def list_sections(
    db: DB, user: OptionalUser, act: str | None = None,
    q: str | None = Query(None, description="keyword filter on title/text"),
    as_of: date | None = Query(None, description="defaults to today -- see Part K K3"),
    limit: int = Query(50, le=200),
):
    """Browses the section IN FORCE as of `as_of` (default today) -- see
    app/services/retrieval.py's module docstring. Never queries the retired
    legal_sections table.

    K2 hard rule applies HERE too, not just to semantic_search/keyword_search:
    a browse listing that showed IPC s.497 with no indication it's struck
    down would violate the same "never present as live law" rule through a
    different door. Found 2026-08-11 while finishing K7 -- this endpoint had
    no judicial_status join or exclusion at all until now.
    """
    as_of = as_of or date.today()
    stmt = (
        select(SectionVersion, Act.act_code)
        .join(Act, SectionVersion.act_id == Act.id)
        .outerjoin(JudicialStatus, and_(
            JudicialStatus.act_id == SectionVersion.act_id,
            JudicialStatus.section_number == SectionVersion.section_number,
        ))
        .where(in_force(as_of), not_struck_down())
    )
    if act:
        stmt = stmt.where(Act.act_code.ilike(act))
    if q:
        stmt = stmt.where(SectionVersion.marginal_note.ilike(f"%{q}%"))
    stmt = stmt.order_by(Act.act_code, SectionVersion.section_number).limit(limit)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": sv.id, "act": act_code, "section_number": sv.section_number,
            "section_title": sv.marginal_note, "section_text": sv.section_text,
            "simplified_text": sv.simplified_text, "category": sv.category,
            "keywords": sv.keywords,
        }
        for sv, act_code in rows
    ]


@router.get("/sections/{act}/{section_number}", response_model=SectionDetailOut)
async def get_section(
    act: str, section_number: str, db: DB, user: OptionalUser,
    as_of: date | None = Query(None, description="defaults to today -- see Part K K3"),
):
    """K7's explicit, direct-citation lookup -- the one path in this app that
    CAN return a struck-down section, always with its judicial_status
    attached (never silently omitted, per K7), unlike list_sections/
    semantic_search/keyword_search which exclude struck-down entirely (K2's
    hard rule for organic/ranked results). Also carries the previous
    version's text when recently_amended, for K7's old/new diff.
    """
    result = await get_section_with_history(db, act.upper(), section_number, as_of)
    if result is None:
        raise HTTPException(404, f"no in-force version of {act} {section_number} as of "
                                  f"{as_of or date.today()}")
    return result


@router.post("/semantic-search", response_model=list[RetrievedSection])
async def search(payload: dict, db: DB, user: OptionalUser):
    """REAL pgvector semantic search, as-of + judicial-status aware (Part K)."""
    query = (payload.get("query") or "").strip()
    top_k = int(payload.get("top_k", 5))
    if not query:
        return []
    as_of = date.fromisoformat(payload["as_of"]) if payload.get("as_of") else None
    incident_date = date.fromisoformat(payload["incident_date"]) if payload.get("incident_date") else None
    return await semantic_search(db, query, top_k=top_k, as_of=as_of, incident_date=incident_date)
