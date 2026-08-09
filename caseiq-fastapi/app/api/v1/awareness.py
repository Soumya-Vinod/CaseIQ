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
    stmt = stmt.order_by(LegalNewsArticle.published_at.desc()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


@router.post("/news/refresh", dependencies=[Depends(require_role(Role.ADMIN))])
async def refresh_news(db: DB, limit: int = 10):
    saved = await fetch_and_save(db, limit=limit)
    return {"saved": saved}
