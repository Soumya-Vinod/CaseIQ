"""Real hybrid retrieval over legal_sections.

Replaces the original keyword-only `Q(section_text__icontains=word)` with:
  * pgvector cosine similarity (the actual semantic step), plus
  * a keyword fallback when no section clears the similarity floor.

Returns sections WITH a real similarity score, instead of the hardcoded 0.85.
"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.legal import LegalSection
from app.services.embeddings import embedder


async def semantic_search(
    db: AsyncSession, query: str, top_k: int | None = None
) -> list[dict]:
    top_k = top_k or settings.RAG_TOP_K
    qvec = await embedder.embed(query)

    # cosine_distance is in [0, 2]; similarity = 1 - distance.
    distance = LegalSection.embedding.cosine_distance(qvec).label("distance")
    stmt = (
        select(LegalSection, distance)
        .where(LegalSection.is_active.is_(True), LegalSection.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )
    rows = (await db.execute(stmt)).all()

    results: list[dict] = []
    for section, dist in rows:
        similarity = 1.0 - float(dist)
        if similarity < settings.RAG_MIN_SIMILARITY:
            continue
        results.append(_serialise(section, round(similarity, 4)))

    if results:
        return results
    return await keyword_search(db, query, top_k)


async def keyword_search(db: AsyncSession, query: str, top_k: int) -> list[dict]:
    stop = {"what", "how", "when", "where", "why", "the", "and", "for", "with", "from"}
    words = [w.strip(".,?!;:").lower() for w in query.split() if len(w) > 3 and w.lower() not in stop]
    if not words:
        return []
    clauses = []
    for w in words[:6]:
        clauses.append(LegalSection.section_title.ilike(f"%{w}%"))
        clauses.append(LegalSection.section_text.ilike(f"%{w}%"))
        clauses.append(LegalSection.category.ilike(f"%{w}%"))
    stmt = (
        select(LegalSection)
        .where(LegalSection.is_active.is_(True), or_(*clauses))
        .limit(top_k)
    )
    sections = (await db.execute(stmt)).scalars().all()
    return [_serialise(s, None) for s in sections]


def _serialise(s: LegalSection, similarity: float | None) -> dict:
    return {
        "act": s.act,
        "section": s.section_number,
        "title": s.section_title,
        "snippet": s.section_text[:300],
        "category": s.category,
        "similarity": similarity,  # None for keyword fallback — honest about provenance
    }


def build_rag_context(sections: list[dict]) -> str:
    if not sections:
        return ""
    parts = ["--- RETRIEVED LEGAL SECTIONS (authoritative reference) ---"]
    for s in sections:
        parts.append(f"{s['act']} Section {s['section']} — {s['title']}:\n{s['snippet']}")
    parts.append("--- END RETRIEVED SECTIONS ---")
    return "\n\n".join(parts)
