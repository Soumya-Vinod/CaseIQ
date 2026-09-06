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
from app.services.citation_verification import (
    NOTE_CITATIONS_STRIPPED,
    record_stats,
    scan_free_text_for_citations,
    verify_citations,
)
from app.services.helplines import select_helplines
from app.services.llm import llm_service
from app.services.pii_redaction import RedactionSession, restore_deep, restore_text
from app.services.retrieval import (
    build_rag_context,
    implies_past_incident,
    is_abstention,
    is_civil_scope_mismatch,
    regime_note,
    semantic_search,
    touches_violence_or_harm,
)
from app.services.safety import screen_query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

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

# C8: fixed text, not LLM-generated -- same reasoning as _ABSTENTION_MESSAGE
# above (a considered question, not a decoration the model could phrase
# inconsistently or get the cutover date wrong on). Shown only when
# implies_past_incident recognised the query as describing something that
# already happened AND no incident_date/skip was given -- see that
# function's docstring for what does and doesn't trigger this.
_INCIDENT_DATE_PROMPT = (
    "This sounds like something that already happened. Indian criminal law changed on "
    "1 July 2024 -- IPC/CrPC applied before that date, BNS/BNSS on or after -- so knowing when "
    "this happened lets me cite the law that actually applied, not just the current one. If you "
    "know the date, please share it. If you don't, let me know and I'll check both."
)
_SKIPPED_DATE_NOTE = (
    " (No incident date was given, so this searched across both the pre-2024 (IPC/CrPC) and "
    "current (BNS/BNSS) regimes.)"
)

router = APIRouter(prefix="/legal", tags=["Legal Query"])


async def _history(db: DB, session_id: str) -> list[dict]:
    """FIXED 2026-09-06: found live, not by review -- this is the first time
    this function has EVER run past its own early-return with real matching
    rows. The frontend hardcoded session_id: "" until today (see
    caseiq-web/src/utils/session.ts), so every call before now hit `if not
    session_id: return []` and never reached the loop below at all -- the
    lazy `q.response` access has been sitting here, structurally correct-
    looking, completely unexercised.

    The bug: `select(LegalQuery)` with no loader option leaves `.response`
    (a `relationship()`) to lazy-load on first access. Accessing it via
    plain attribute access (`if q.response:`) outside an explicit `await`
    tries to run that lazy SELECT through SQLAlchemy's implicit greenlet
    bridge, which -- confirmed directly against a real session_id with real
    rows, not assumed -- fails here with `greenlet_spawn has not been
    called; can't call await_only() here`. `RequestContextMiddleware`
    (BaseHTTPMiddleware) runs the endpoint in a task-group task whose
    context doesn't carry the greenlet the original session was opened
    under, which is exactly the class of situation an implicit lazy-load
    is unsafe in and an explicit, awaited query is not.

    Fixed by eager-loading the relationship in the original query
    (`selectinload` -- a second, explicit, properly-awaited SELECT) instead
    of touching `.response` lazily at all.
    """
    if not session_id:
        return []
    rows = (await db.execute(
        select(LegalQuery)
        .options(selectinload(LegalQuery.response))
        .where(LegalQuery.session_id == session_id, LegalQuery.status == QueryStatus.PROCESSED)
        .order_by(LegalQuery.created_at)
    )).scalars().all()
    history: list[dict] = []
    for q in rows:
        history.append({"role": "user", "content": q.original_query})
        if q.response:
            history.append({"role": "assistant", "content": q.response.conversational_summary})
    return history


@router.post("/query", response_model=QueryOut)
async def process_query(payload: QueryIn, db: DB, user: OptionalUser, request: Request):
    # FIXED 2026-09-06 (checklist item 6, Phase A): every LegalQuery row
    # below used to store payload.query RAW. Storage now gets the same
    # redaction applied before this ever left the process for Groq (see
    # app.services.pii_redaction) -- for every row, logged-in or anonymous,
    # per instruction: "there's no reason to store raw text for users who
    # never log in either." Computed once, up front, and reused across all
    # three LegalQuery(...) constructions below (blocked / needs-incident-
    # date / normal) so which branch returns doesn't change what's stored.
    # A SEPARATE session from the one llm_service.process_query builds for
    # its own Groq call -- redundant computation, not redundant correctness:
    # this one exists purely to decide what's written to the database, and
    # doesn't need to match token numbering with the LLM-facing session.
    # screen_query below still runs on the RAW payload.query, deliberately:
    # harm-intent phrasing ("how to kill") isn't personal data and isn't
    # what this redaction pass targets.
    _query_redaction = RedactionSession()
    stored_query = _query_redaction.redact(payload.query)
    if _query_redaction.had_redactions:
        logger.info("pii_redacted", endpoint="legal_query_storage", counts=_query_redaction.counts)

    blocked, pattern = screen_query(payload.query)
    if blocked:
        # NOTE: this AuditLog.details still stores the RAW query, not
        # stored_query -- out of this pass's scope (Phase A targets
        # LegalQuery/QueryResponse specifically; audit_logs is a different
        # table with its own 90-day retention for a different purpose,
        # abuse investigation). Flagged rather than silently left
        # inconsistent -- same treatment as the ip_address note just below.
        db.add(AuditLog(user_id=user.id if user else None, action="dark_query_blocked",
                        details={"query": payload.query, "pattern": pattern},
                        ip_hash=hash_ip(client_ip(request))))
        # NOTE: LegalQuery.ip_address below still stores the raw IP -- a separate
        # model from AuditLog, out of M2's explicit scope ("hash IPs" was scoped
        # to audit logging). Flagged, not fixed here: same DPDP concern applies.
        db.add(LegalQuery(user_id=user.id if user else None, original_query=stored_query,
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

    # C8: ask BEFORE generating, not after -- a query that reads as
    # describing something that already happened, with no incident_date and
    # no explicit skip, gets the date prompt instead of an answer computed
    # against a guessed regime. Short-circuits before retrieval even runs,
    # same shape as the abstention short-circuit below (a designed pause,
    # not a failure -- persisted and returned the same way).
    if payload.incident_date is None and not payload.skip_incident_date \
            and implies_past_incident(payload.query):
        took_ms = int((time.perf_counter() - started) * 1000)
        q = LegalQuery(user_id=user.id if user else None, original_query=stored_query,
                       detected_language=language, status=QueryStatus.PROCESSED,
                       session_id=payload.session_id, ip_address=client_ip(request))
        db.add(q)
        await db.flush()
        db.add(QueryResponse(
            query_id=q.id, conversational_summary=_INCIDENT_DATE_PROMPT, structured_data={},
            retrieved_sections=[], confidence_score=0.0, response_language=language,
            processing_time_ms=took_ms, is_followup=False, as_of=as_of, corpus_version_id=None,
        ))
        return QueryOut(
            query_id=q.id, original_query=payload.query,
            conversational_summary=_INCIDENT_DATE_PROMPT, structured_data={}, confidence_score=0.0,
            legal_sections=[], language=language, related_questions=[], is_followup=False,
            processing_time_ms=took_ms, abstained=False, needs_incident_date=True, as_of=as_of,
            corpus_version_id=None, helplines=select_helplines(payload.query),
        )

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
    # FIXED 2026-09-04 (found live): a harm query came back the generic
    # abstention refusal at 23% similarity, never reaching the LLM -- which
    # meant it never reached the intent-aware discouragement-framing
    # instructions either, since those live entirely in _STRUCTURED_PROMPT,
    # not in any gate here. touches_violence_or_harm is checked on the
    # query's own text, independent of retrieval strength, and bypasses
    # this gate when it fires -- intent has to be checked BEFORE the
    # similarity threshold, not patched around it one failing phrase at a
    # time (see that function's docstring for why this is a structural fix,
    # not another synonym-map entry). Safe: the LLM still won't fabricate a
    # citation with weak/no evidence (_STRUCTURED_PROMPT's own GROUNDING
    # rules), and C5 backstops anything that slips through anyway -- this
    # only changes whether the LLM is asked, never what it's allowed to
    # answer with.
    abstained = (is_abstention(sections) or civil_scope_mismatch) \
        and not touches_violence_or_harm(payload.query)
    if abstained:
        # No fabricated citations alongside a refusal -- see is_abstention's
        # docstring for exactly what counts as "not enough evidence".
        sections = []
    rag_context = build_rag_context(sections)

    q = LegalQuery(user_id=user.id if user else None, original_query=stored_query,
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
        # Fixed, non-user-supplied text -- no PII possible, so no redaction
        # map needed; restore_text/restore_deep are no-ops against {} anyway.
        result = {
            "conversational_summary": _CIVIL_SCOPE_MESSAGE if civil_scope_mismatch else _ABSTENTION_MESSAGE,
            "structured_data": {},
            # Same formula as llm.py's confidence, computed here since the LLM
            # (and therefore that function) is never called on this path.
            "confidence_score": round(max(0.0, min(retrieval_strength, 1.0)), 3),
            "language": language,
            "is_followup": False,
            "redaction_map": {},
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

        # C5: _STRUCTURED_PROMPT only ASKS the model to cite only retrieved
        # sections -- nothing enforced that until now. Strip anything that
        # doesn't check out (either fabricated outright, or real-but-not-
        # retrieved-here), count both failure modes separately, persist the
        # counters (not just log them) so "how often does this actually
        # fire" is an answerable question, not a one-off debugging fact.
        had_laws = bool(result["structured_data"].get("laws_applicable"))
        result["structured_data"], citation_counters = await verify_citations(
            db, result["structured_data"], sections, as_of,
        )
        if had_laws and not result["structured_data"].get("laws_applicable"):
            result["conversational_summary"] += NOTE_CITATIONS_STRIPPED
        await record_stats(db, citation_counters)
        free_text_citations = scan_free_text_for_citations(
            result["structured_data"], result["conversational_summary"],
        )
        ungrounded_free_text = free_text_citations - {
            (s["act"], s["section"]) for s in sections
        }
        if ungrounded_free_text:
            logger.warning("citation_free_text_ungrounded", sections=sorted(ungrounded_free_text))

    related = [] if abstained or result["is_followup"] else await llm_service.related_questions(
        payload.query, result["conversational_summary"]
    )

    # C8: make the routing visible, not just correct -- computed here, from
    # the same acts_for_incident_date the retrieval call above already used,
    # never phrased by the LLM (see regime_note's docstring). Appended after
    # related_questions so that call sees the answer itself, not this note.
    if not abstained:
        if payload.incident_date is not None:
            result["conversational_summary"] += " " + regime_note(payload.incident_date)
        elif payload.skip_incident_date:
            result["conversational_summary"] += _SKIPPED_DATE_NOTE

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

    # result["conversational_summary"]/["structured_data"] are REDACTED at
    # this point (llm_service.process_query stopped restoring internally --
    # see its own comment) -- this is what gets stored, below, unmodified.
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

    # FIXED 2026-09-06 (checklist item 6, Phase A): restored HERE, on copies,
    # for this one live HTTP response only -- the row just stored above
    # already has the redacted text and is never touched again. See
    # docs/evaluation.md for why this moved out of llm.py.
    redaction_map = result.get("redaction_map", {})
    response_summary = restore_text(result["conversational_summary"], redaction_map)
    response_structured = restore_deep(result["structured_data"], redaction_map)

    return QueryOut(
        query_id=q.id, original_query=payload.query,
        conversational_summary=response_summary,
        structured_data=response_structured, confidence_score=result["confidence_score"],
        legal_sections=sections, language=language, related_questions=related,
        is_followup=result["is_followup"], processing_time_ms=took_ms, abstained=abstained,
        as_of=as_of, corpus_version_id=latest_corpus_version_id,
        # FIXED 2026-09-06 (checklist item 4): the abstention path used to
        # show the full five-number table unconditionally -- noise, not
        # help, per instruction ("we show all five on every abstention...
        # select by topic... one or two, never a wall"). Now the SAME
        # topic-selection select_helplines uses for an answered query, with
        # NALSA (15100) as the honest fallback when abstention has nothing
        # more specific to offer -- never zero numbers on a refusal, since
        # that's still the one path where the user got no answer at all.
        helplines=select_helplines(
            payload.query, fallback_on_empty="15100" if abstained else None,
        ),
    )
