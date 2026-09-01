from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DB, OptionalUser
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import logger
from app.models.complaint import Complaint, ComplaintStatus
from app.schemas.complaint import ComplaintIn, ComplaintOut
from app.services.llm import llm_service
from app.services.pdf import generate_complaint_pdf
from app.services.retrieval import build_rag_context, is_abstention, is_civil_scope_mismatch, semantic_search

router = APIRouter(prefix="/complaints", tags=["Complaints"])

MEDIA_ROOT = Path("media")
_DISCLAIMER = ("DRAFT ONLY: for reference purposes. CaseIQ does not provide legal advice. "
               "Review with a qualified advocate before submission.")


def _out(c: Complaint, *, download_url: str | None) -> ComplaintOut:
    return ComplaintOut(
        id=c.id, complaint_type=c.complaint_type, complainant_name=c.complainant_name,
        status=c.status, generated_draft=c.generated_draft, pdf_available=bool(c.pdf_path),
        download_url=download_url, disclaimer=_DISCLAIMER,
        legal_sections=c.retrieved_sections, grounded=bool(c.retrieved_sections),
    )


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
async def create_complaint(payload: ComplaintIn, db: DB, user: OptionalUser):
    c = Complaint(user_id=user.id if user else None, **payload.model_dump())
    db.add(c)
    await db.flush()
    try:
        # GROUNDING: same retrieval /legal/query uses, run against the
        # incident narrative -- never client-supplied section numbers (see
        # app/schemas/complaint.py and the 0006_complaint_grounding migration
        # for why `applicable_sections` was removed from ComplaintIn). What
        # the drafting LLM is allowed to cite is decided here, before it ever
        # sees the incident text, not by trusting its own output afterward.
        # FIXED 2026-09-01, found testing against the real corpus (not
        # assumed): relief_sought describes the remedy being asked for
        # ("Registration of FIR and protection order"), not the underlying
        # offense. Its words ("FIR" -> expand_query_synonyms -> "information
        # in cognizable cases") systematically outranked the actual offense
        # sections for a real dowry-cruelty narrative, surfacing CrPC 154/155
        # (FIR filing procedure) instead of BNS 85/86 (cruelty) -- confirmed
        # by comparing retrieval with/without this field. Retrieval must run
        # on what happened, not on what the complainant is asking for.
        narrative = " ".join(filter(None, [payload.incident_description, payload.accused_details]))
        civil_scope_mismatch = is_civil_scope_mismatch(narrative)
        sections = await semantic_search(db, narrative) if narrative.strip() else []
        if is_abstention(sections) or civil_scope_mismatch:
            sections = []  # same rule as legal.py: no citations alongside weak/no evidence
        c.retrieved_sections = sections
        c.applicable_sections = [f"{s['act']} {s['section']}" for s in sections]

        rag_context = build_rag_context(sections)
        draft = await llm_service.generate_complaint_draft(
            {k: v for k, v in payload.model_dump(mode="json").items() if k != "language"},
            rag_context=rag_context, language=payload.language,
        )
        c.generated_draft = draft
        c.status = ComplaintStatus.GENERATED

        pdf_rel = f"complaints/complaint_{c.id}.pdf"
        ok = await generate_complaint_pdf(c, str(MEDIA_ROOT / pdf_rel))
        if ok:
            c.pdf_path = pdf_rel
    except Exception as exc:
        c.status = ComplaintStatus.DRAFT
        logger.exception("complaint_generation_failed", error=str(exc))
        raise

    return _out(c, download_url=f"{settings.API_V1_PREFIX}/complaints/{c.id}/download" if c.pdf_path else None)


@router.get("/{complaint_id}/download")
async def download(complaint_id: UUID, db: DB, user: OptionalUser):
    stmt = select(Complaint).where(Complaint.id == complaint_id)
    if user:
        stmt = stmt.where(Complaint.user_id == user.id)
    c = await db.scalar(stmt)
    if not c:
        raise NotFoundError("Complaint not found.")
    if not c.pdf_path or not (MEDIA_ROOT / c.pdf_path).exists():
        # Render's disk is ephemeral (docs/deployment.md) -- a container
        # restart between create and download wipes media/ entirely. Safe to
        # regenerate on demand because everything the PDF needs (draft text,
        # retrieved_sections, complaint fields) is already persisted on this
        # row -- no re-run of retrieval or the LLM required.
        await generate_complaint_pdf(c, str(MEDIA_ROOT / f"complaints/complaint_{c.id}.pdf"))
        c.pdf_path = f"complaints/complaint_{c.id}.pdf"
    c.status = ComplaintStatus.DOWNLOADED
    return FileResponse(MEDIA_ROOT / c.pdf_path, media_type="application/pdf",
                        filename=f"CaseIQ_Complaint_{c.id}.pdf")


@router.get("/history", response_model=list[ComplaintOut])
async def history(user: CurrentUser, db: DB):
    rows = (await db.execute(
        select(Complaint).where(Complaint.user_id == user.id)
        .order_by(Complaint.created_at.desc()).limit(20)
    )).scalars().all()
    return [_out(c, download_url=None) for c in rows]
