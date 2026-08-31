from fastapi import APIRouter, Query

from app.api.deps import DB, OptionalUser, require_role
from app.models.news import LegalNewsArticle
from app.models.user import Role
from app.schemas.news import NewsOut
from app.services.news import fetch_and_save
from fastapi import Depends
from sqlalchemy import select

router = APIRouter(prefix="/awareness", tags=["Awareness"])


@router.get("/news", response_model=list[NewsOut])
async def list_news(db: DB, user: OptionalUser, featured: bool | None = None, limit: int = Query(20, le=50)):
    stmt = select(LegalNewsArticle)
    if featured is not None:
        stmt = stmt.where(LegalNewsArticle.is_featured.is_(featured))
    # Real articles first, always -- app/services/news.py's evergreen explainer
    # fallback has no genuine publication date (it's authored content, not
    # news) and previously got `datetime.now()` at insert time, which made it
    # sort ABOVE real, older news and made the tab look like it had no current
    # articles at all (found 2026-08-31 seeding explainers for a screenshot).
    # source_url == '' is the same "no real source to link to" signal the
    # frontend uses to badge an explainer -- sorting on it directly here means
    # this doesn't silently break if is_featured's meaning ever changes.
    stmt = stmt.order_by(
        (LegalNewsArticle.source_url == "").asc(),
        LegalNewsArticle.published_at.desc(),
    ).limit(limit)
    return (await db.execute(stmt)).scalars().all()


@router.post("/news/refresh", dependencies=[Depends(require_role(Role.ADMIN))])
async def refresh_news(db: DB, limit: int = 10):
    saved = await fetch_and_save(db, limit=limit)
    return {"saved": saved}
