import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DB, OptionalUser
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import logger
from app.models.complaint import Complaint, ComplaintStatus
from app.schemas.complaint import ComplaintIn, ComplaintOut
from app.services.llm import llm_service
from app.services.pdf import generate_complaint_pdf
from sqlalchemy import select

router = APIRouter(prefix="/complaints", tags=["Complaints"])

MEDIA_ROOT = Path("media")
_DISCLAIMER = ("DRAFT ONLY: for reference purposes. CaseIQ does not provide legal advice. "
               "Review with a qualified advocate before submission.")


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
async def create_complaint(payload: ComplaintIn, db: DB, user: OptionalUser):
    c = Complaint(user_id=user.id if user else None, **payload.model_dump())
    db.add(c)
    await db.flush()
    try:
        draft = await llm_service.generate_complaint_draft({
            **payload.model_dump(mode="json"),
            "applicable_sections": ", ".join(payload.applicable_sections),
        })
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

    return ComplaintOut(
        id=c.id, complaint_type=c.complaint_type, complainant_name=c.complainant_name,
        status=c.status, generated_draft=c.generated_draft, pdf_available=bool(c.pdf_path),
        download_url=f"{settings.API_V1_PREFIX}/complaints/{c.id}/download" if c.pdf_path else None,
        disclaimer=_DISCLAIMER,
    )


@router.get("/{complaint_id}/download")
async def download(complaint_id: UUID, db: DB, user: OptionalUser):
    stmt = select(Complaint).where(Complaint.id == complaint_id)
    if user:
        stmt = stmt.where(Complaint.user_id == user.id)
    c = await db.scalar(stmt)
    if not c:
        raise NotFoundError("Complaint not found.")
    if not c.pdf_path or not (MEDIA_ROOT / c.pdf_path).exists():
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
    return [ComplaintOut(id=c.id, complaint_type=c.complaint_type,
                         complainant_name=c.complainant_name, status=c.status,
                         generated_draft=c.generated_draft, pdf_available=bool(c.pdf_path),
                         download_url=None, disclaimer=_DISCLAIMER) for c in rows]
