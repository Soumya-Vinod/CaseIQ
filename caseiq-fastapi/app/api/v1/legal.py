import time
from datetime import date

from fastapi import APIRouter, Request, status

from app.api.deps import DB, OptionalUser, client_ip
from app.core.exceptions import BlockedQueryError
from app.core.logging import logger
from app.core.security import hash_ip
from app.models.audit import AuditLog
from app.models.legal import LegalQuery, QueryResponse, QueryStatus
from app.schemas.legal import QueryIn, QueryOut, SituationIn
from app.services.llm import llm_service
from app.services.retrieval import build_rag_context, semantic_search
from app.services.safety import screen_query
from sqlalchemy import select

router = APIRouter(prefix="/legal", tags=["Legal Query"])


async def _history(db: DB, session_id: str) -> list[dict]:
    if not session_id:
        return []
    rows = (await db.execute(
        select(LegalQuery).where(
            LegalQuery.session_id == session_id, LegalQuery.status == QueryStatus.PROCESSED
        ).order_by(LegalQuery.created_at)
    )).scalars().all()
    history: list[dict] = []
    for q in rows:
        history.append({"role": "user", "content": q.original_query})
        if q.response:
            history.append({"role": "assistant", "content": q.response.conversational_summary})
    return history


@router.post("/query", response_model=QueryOut)
async def process_query(payload: QueryIn, db: DB, user: OptionalUser, request: Request):
    blocked, pattern = screen_query(payload.query)
    if blocked:
        db.add(AuditLog(user_id=user.id if user else None, action="dark_query_blocked",
                        details={"query": payload.query, "pattern": pattern},
                        ip_hash=hash_ip(client_ip(request))))
        # NOTE: LegalQuery.ip_address below still stores the raw IP -- a separate
        # model from AuditLog, out of M2's explicit scope ("hash IPs" was scoped
        # to audit logging). Flagged, not fixed here: same DPDP concern applies.
        db.add(LegalQuery(user_id=user.id if user else None, original_query=payload.query,
                          status=QueryStatus.BLOCKED, is_flagged=True,
                          flag_reason=f"pattern:{pattern}", session_id=payload.session_id,
                          ip_address=client_ip(request)))
        raise BlockedQueryError(
            "This query was flagged as potentially harmful. CaseIQ helps citizens understand "
            "their legal rights, not facilitate harm. This incident has been logged."
        )

    started = time.perf_counter()
    language = payload.language
    if language == "en":
        language = await llm_service.detect_language(payload.query)

    history = await _history(db, payload.session_id)
    as_of = payload.as_of or date.today()
    sections = await semantic_search(
        db, payload.query, as_of=as_of, incident_date=payload.incident_date
    )
    rag_context = build_rag_context(sections)
    sims = [s["similarity"] for s in sections if s["similarity"] is not None]
    retrieval_strength = max(sims) if sims else 0.0

    q = LegalQuery(user_id=user.id if user else None, original_query=payload.query,
                   detected_language=language, status=QueryStatus.PROCESSING,
                   session_id=payload.session_id, ip_address=client_ip(request))
    db.add(q)
    await db.flush()

    try:
        result = await llm_service.process_query(
            payload.query, language=language, history=history,
            rag_context=rag_context, retrieval_strength=retrieval_strength,
        )
    except Exception as exc:
        q.status = QueryStatus.FAILED
        logger.exception("legal_query_failed", error=str(exc))
        raise

    related = [] if result["is_followup"] else await llm_service.related_questions(
        payload.query, result["conversational_summary"]
    )
    took_ms = int((time.perf_counter() - started) * 1000)

    db.add(QueryResponse(
        query_id=q.id, conversational_summary=result["conversational_summary"],
        structured_data=result["structured_data"], retrieved_sections=sections,
        confidence_score=result["confidence_score"], response_language=language,
        processing_time_ms=took_ms, is_followup=result["is_followup"],
        as_of=as_of,  # K7: the date retrieval was filtered as-of, stamped on the answer
        # corpus_version_id intentionally not stamped yet -- see K6 admin API (task 8):
        # corpus_versions should be created deliberately (e.g. after a successful
        # ingest run), not implicitly on every query.
    ))
    q.status = QueryStatus.PROCESSED
    q.is_followup = result["is_followup"]

    return QueryOut(
        query_id=q.id, original_query=payload.query,
        conversational_summary=result["conversational_summary"],
        structured_data=result["structured_data"], confidence_score=result["confidence_score"],
        legal_sections=sections, language=language, related_questions=related,
        is_followup=result["is_followup"], processing_time_ms=took_ms, as_of=as_of,
    )
