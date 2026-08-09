from fastapi import APIRouter, Query

from app.api.deps import DB, OptionalUser
from app.models.legal import LegalSection
from app.schemas.legal import RetrievedSection, SectionOut
from app.services.retrieval import semantic_search
from sqlalchemy import select

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.get("/sections", response_model=list[SectionOut])
async def list_sections(
    db: DB, user: OptionalUser, act: str | None = None,
    q: str | None = Query(None, description="keyword filter on title/text"),
    limit: int = Query(50, le=200),
):
    stmt = select(LegalSection).where(LegalSection.is_active.is_(True))
    if act:
        stmt = stmt.where(LegalSection.act.ilike(act))
    if q:
        stmt = stmt.where(LegalSection.section_title.ilike(f"%{q}%"))
    stmt = stmt.order_by(LegalSection.act, LegalSection.section_number).limit(limit)
    return (await db.execute(stmt)).scalars().all()


@router.post("/semantic-search", response_model=list[RetrievedSection])
async def search(payload: dict, db: DB, user: OptionalUser):
    """REAL pgvector semantic search (the original endpoint could only ever hit
    its keyword fallback because the embedding service was an empty file)."""
    query = (payload.get("query") or "").strip()
    top_k = int(payload.get("top_k", 5))
    if not query:
        return []
    return await semantic_search(db, query, top_k=top_k)
