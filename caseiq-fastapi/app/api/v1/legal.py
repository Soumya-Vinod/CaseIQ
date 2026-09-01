import time
from datetime import date

from fastapi import APIRouter, Request, status

from app.api.deps import DB, OptionalUser, client_ip
from app.core.exceptions import BlockedQueryError
from app.core.logging import logger
from app.core.security import hash_ip
from app.models.audit import AuditLog
from app.models.corpus import CorpusVersion
from app.models.legal import LegalQuery, QueryResponse, QueryStatus
from app.schemas.legal import QueryIn, QueryOut, SituationIn
from app.services.helplines import get_helplines
from app.services.llm import llm_service
from app.services.retrieval import (
    build_rag_context,
    is_abstention,
    is_civil_scope_mismatch,
    semantic_search,
)
from app.services.safety import screen_query
from sqlalchemy import select

# Fixed abstention response text -- deliberately not LLM-generated (see
# is_abstention's docstring: the whole point is to skip the LLM call, not
# just to prompt it more carefully). A considered "no" with a next step, not
# an error message. Two variants: the scope one fires when is_civil_scope_mismatch
# recognises the query as a named civil-law domain this corpus doesn't cover;
# the generic one is the fallback for everything else that's weakly retrieved
# but not recognisably civil (Titan's methane question, e.g.) -- it still states
# the corpus's actual scope rather than a bare "not confident".
_ABSTENTION_MESSAGE = (
    # FIXED 2026-08-31: this used to list example out-of-scope domains
    # ("property, contract, tenancy, family, inheritance") even though this
    # generic path makes NO domain diagnosis at all -- it fires purely on low
    # similarity (see is_abstention). A marital-cruelty query ("marital
    # abuse") hit exactly this path (BNS s.85/IPC s.498A weren't retrieved,
    # unrelated to the civil-phrase check below) and the word "family" in
    # this message made a pure retrieval miss on a real criminal question
    # read as a confident, false claim that it was a civil matter. Say only
    # what's actually true here: what IS covered, not a guess at what isn't.
    "I couldn't find a confident match for this in the BNS, BNSS, BSA, IPC or CrPC text "
    "I have -- CaseIQ only covers Indian criminal law and procedure. Rather than guess, "
    "I'm not going to answer this one. For guidance specific to your situation, please "
    "consult a lawyer or your nearest legal aid clinic (NALSA helpline: 15100, or "
    "https://nalsa.gov.in)."
)
_CIVIL_SCOPE_MESSAGE = (
    # Wording kept in sync with is_civil_scope_mismatch's actual phrase list
    # (property/tenancy/succession-type civil domains only, as of the
    # 2026-08-31 audit -- "family" removed after divorce/child-custody were
    # dropped from that list for false-positive risk). Don't claim a domain
    # this message's own trigger no longer checks for.
    "CaseIQ covers Indian criminal law and procedure (BNS, BNSS, BSA, IPC, CrPC). This "
    "appears to be a civil matter -- property, tenancy, succession, or a similar civil-law "
    "area -- which is outside this corpus, so I'm not going to answer it. For guidance specific to "
    "your situation, please consult a lawyer or your nearest legal aid clinic (NALSA "
    "helpline: 15100, or https://nalsa.gov.in)."
)

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
    sims = [s["similarity"] for s in sections if s["similarity"] is not None]
    retrieval_strength = max(sims) if sims else 0.0
    # Two independent, both-imperfect signals, OR'd together: similarity alone
    # cannot separate a civil easement question (0.4768 max similarity) from
    # "punishment for theft" (0.478) or "punishment for defamation" (0.478) on
    # this corpus -- verified 2026-08-30, see docs/evaluation.md. No single
    # threshold catches the former without also catching the latter two. The
    # civil-phrase check is a second, narrower net for exactly that gap.
    civil_scope_mismatch = is_civil_scope_mismatch(payload.query)
    abstained = is_abstention(sections) or civil_scope_mismatch
    if abstained:
        # No fabricated citations alongside a refusal -- see is_abstention's
        # docstring for exactly what counts as "not enough evidence".
        sections = []
    rag_context = build_rag_context(sections)

    q = LegalQuery(user_id=user.id if user else None, original_query=payload.query,
                   detected_language=language, status=QueryStatus.PROCESSING,
                   session_id=payload.session_id, ip_address=client_ip(request))
    db.add(q)
    await db.flush()

    if abstained:
        # Short-circuit BEFORE the LLM call -- letting it free-associate over
        # weak/irrelevant retrieved sections is exactly what produced a 0.709
        # confidence + 6 citations alongside "I can only help with legal
        # questions" for an out-of-scope query (2026-08-30). See config.py's
        # ABSTENTION_SIMILARITY_THRESHOLD for where the cutoff came from.
        result = {
            "conversational_summary": _CIVIL_SCOPE_MESSAGE if civil_scope_mismatch else _ABSTENTION_MESSAGE,
            "structured_data": {},
            # Same formula as llm.py's confidence, computed here since the LLM
            # (and therefore that function) is never called on this path.
            "confidence_score": round(max(0.0, min(retrieval_strength, 1.0)), 3),
            "language": language,
            "is_followup": False,
        }
    else:
        try:
            result = await llm_service.process_query(
                payload.query, language=language, history=history,
                rag_context=rag_context, retrieval_strength=retrieval_strength,
            )
        except Exception as exc:
            q.status = QueryStatus.FAILED
            logger.exception("legal_query_failed", error=str(exc))
            raise

    related = [] if abstained or result["is_followup"] else await llm_service.related_questions(
        payload.query, result["conversational_summary"]
    )
    took_ms = int((time.perf_counter() - started) * 1000)

    # K4/K7: whatever corpus_version was live when this answer was generated,
    # so a stored answer can be reproduced/audited against the exact corpus
    # state it was computed from. Created deliberately by ingest/approve
    # (app.legal_corpus.corpus_version), never implicitly here -- this is a
    # read-only lookup of the latest one, not a create. None on a fresh DB
    # before the first ingest run has ever completed -- absence recorded
    # honestly rather than defaulted to a fake id.
    latest_corpus_version_id = (await db.execute(
        select(CorpusVersion.id).order_by(CorpusVersion.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    db.add(QueryResponse(
        query_id=q.id, conversational_summary=result["conversational_summary"],
        structured_data=result["structured_data"], retrieved_sections=sections,
        confidence_score=result["confidence_score"], response_language=language,
        processing_time_ms=took_ms, is_followup=result["is_followup"],
        as_of=as_of,  # K7: the date retrieval was filtered as-of, stamped on the answer
        corpus_version_id=latest_corpus_version_id,
    ))
    q.status = QueryStatus.PROCESSED
    q.is_followup = result["is_followup"]

    return QueryOut(
        query_id=q.id, original_query=payload.query,
        conversational_summary=result["conversational_summary"],
        structured_data=result["structured_data"], confidence_score=result["confidence_score"],
        legal_sections=sections, language=language, related_questions=related,
        is_followup=result["is_followup"], processing_time_ms=took_ms, abstained=abstained,
        as_of=as_of, corpus_version_id=latest_corpus_version_id,
        helplines=get_helplines(),
    )
