"""Legal-news ingestion — REAL sources only.

The original `fetch_from_groq` asked the LLM to *invent* court judgments with fake
livelaw.in URLs. For a legal-information product that is a credibility hazard, so it
is removed. Order: NewsAPI (if key) -> curated static evergreen explainers (clearly
labelled as CaseIQ explainers, not news). No fabricated 'judgments'.
"""
from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.news import LegalNewsArticle

_QUERIES = [
    "India Supreme Court judgment", "India High Court ruling", "BNS BNSS criminal law India",
    "cybercrime India law", "consumer court India verdict", "women rights India law",
]

# Evergreen, factual explainers authored by the platform — labelled as such.
_EXPLAINERS = [
    ("BNS 2023: Guide to the New Criminal Code", "The Bharatiya Nyaya Sanhita replaced the IPC from 1 July 2024.", ["BNS", "Reform"]),
    ("How to File a Zero FIR", "A Zero FIR can be filed at any police station regardless of jurisdiction (BNSS s.173).", ["Zero FIR", "BNSS"]),
    ("Cybercrime Helpline 1930", "Report online fraud to 1930 or cybercrime.gov.in; fast reporting aids fund recovery.", ["Cybercrime"]),
    ("RTI Act: Seeking Information from Government", "The RTI Act 2005 lets citizens request info from public authorities within 30 days.", ["RTI"]),
    ("Anticipatory Bail: When and How", "Anticipatory bail under BNSS s.482 lets you seek bail before arrest.", ["Bail", "BNSS"]),
]


async def _from_newsapi(limit: int) -> list[dict]:
    if not settings.NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY not configured")
    out: list[dict] = []
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=10) as client:
        for q in _QUERIES:
            try:
                r = await client.get("https://newsapi.org/v2/everything", params={
                    "q": q, "language": "en", "sortBy": "publishedAt",
                    "pageSize": 5, "apiKey": settings.NEWS_API_KEY,
                })
                r.raise_for_status()
                for item in r.json().get("articles", []):
                    title = (item.get("title") or "")[:500]
                    if not title or title == "[Removed]" or title in seen:
                        continue
                    seen.add(title)
                    out.append({
                        "title": title,
                        "source": (item.get("source") or {}).get("name", "NewsAPI"),
                        "source_url": item.get("url", ""),
                        "summary": (item.get("description") or title)[:1000],
                        "published_at": item.get("publishedAt"),
                        "tags": q.split()[:3],
                        "is_featured": False,
                    })
            except Exception as exc:
                logger.warning("newsapi_query_failed", query=q, error=str(exc))
    return out[:limit]


def _explainers() -> list[dict]:
    now = datetime.now(UTC).isoformat()
    return [{"title": t, "source": "CaseIQ Explainer", "source_url": "", "summary": s,
             "published_at": now, "tags": tags, "is_featured": True} for t, s, tags in _EXPLAINERS]


async def fetch_and_save(db: AsyncSession, limit: int = 10) -> int:
    try:
        articles = await _from_newsapi(limit) or _explainers()
    except Exception as exc:
        logger.warning("newsapi_unavailable_using_explainers", error=str(exc))
        articles = _explainers()

    saved = 0
    for a in articles:
        exists = await db.scalar(select(LegalNewsArticle).where(LegalNewsArticle.title == a["title"]))
        if exists:
            continue
        try:
            pub = datetime.fromisoformat(str(a["published_at"]).replace("Z", "+00:00"))
        except Exception:
            pub = datetime.now(UTC)
        db.add(LegalNewsArticle(
            title=a["title"][:500], source=a["source"][:200], source_url=a["source_url"][:500],
            summary=a["summary"][:1000], published_at=pub, tags=a["tags"],
            is_featured=a["is_featured"], relevance_score=0.8,
        ))
        saved += 1
    await db.flush()
    logger.info("news_ingested", saved=saved)
    return saved
