from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DB, OptionalUser
from app.models.corpus import Act, SectionVersion
from app.schemas.legal import RetrievedSection, SectionOut
from app.services.retrieval import semantic_search

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
    """
    as_of = as_of or date.today()
    stmt = (
        select(SectionVersion, Act.act_code)
        .join(Act, SectionVersion.act_id == Act.id)
        .where(SectionVersion.valid_from <= as_of,
               (SectionVersion.valid_to.is_(None)) | (SectionVersion.valid_to > as_of))
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
