"""Part K K6: minimal admin surface over the corpus review queue and version
history. Nothing here auto-publishes a change -- approve/reject are the only
way a CorpusStagingChange (K5's review queue) reaches section_versions, and
both require Role.ADMIN.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DB, require_role
from app.legal_corpus.corpus_version import create_corpus_version
from app.models.corpus import Act, Amendment, CorpusStagingChange, CorpusVersion, SectionVersion
from app.models.user import Role
from app.schemas.corpus import ApproveIn, CorpusVersionOut, RejectIn, SectionHistoryEntry, StagingChangeOut
from app.services.embeddings import embedder

router = APIRouter(prefix="/admin", tags=["Admin: Corpus"], dependencies=[Depends(require_role(Role.ADMIN))])


@router.get("/corpus/pending", response_model=list[StagingChangeOut])
async def list_pending(db: DB, limit: int = Query(50, le=200)):
    rows = (await db.execute(
        select(CorpusStagingChange, Act.act_code)
        .join(Act, CorpusStagingChange.act_id == Act.id)
        .where(CorpusStagingChange.status == "pending")
        .order_by(CorpusStagingChange.detected_at.desc())
        .limit(limit)
    )).all()
    return [
        {"id": c.id, "act_code": act_code, "section_number": c.section_number,
         "source_url": c.source_url, "diff_summary": c.diff_summary,
         "status": c.status, "detected_at": c.detected_at}
        for c, act_code in rows
    ]


@router.post("/corpus/{staging_id}/approve")
async def approve(staging_id: str, payload: ApproveIn, db: DB, user: CurrentUser):
    change = await db.get(CorpusStagingChange, staging_id)
    if change is None or change.status != "pending":
        raise HTTPException(404, "no pending staging change with that id")

    effective_from = payload.effective_from or date.today()

    amendment_id = None
    if payload.amending_act_name:
        amendment = Amendment(
            amending_act_name=payload.amending_act_name, amending_act_year=payload.amending_act_year,
            gazette_ref=payload.gazette_ref, effective_from=effective_from, summary=payload.summary,
        )
        db.add(amendment)
        await db.flush()
        amendment_id = amendment.id

    current = (await db.execute(
        select(SectionVersion).where(
            SectionVersion.act_id == change.act_id, SectionVersion.section_number == change.section_number,
            SectionVersion.valid_to.is_(None),
        )
    )).scalar_one_or_none()

    next_version_no = 1
    if current is not None:
        current.valid_to = effective_from
        current.superseded_by_id = None  # set below, after the new row has an id
        next_version_no = current.version_no + 1

    vector = await embedder.embed(change.staged_text[:2000])
    new_version = SectionVersion(
        act_id=change.act_id, section_number=change.section_number, version_no=next_version_no,
        marginal_note=current.marginal_note if current else "", section_text=change.staged_text,
        valid_from=effective_from, valid_to=None, source_url=change.source_url,
        source_sha256=change.source_sha256, content_as_on=effective_from,
        amended_by_amendment_id=amendment_id, embedding=vector,
    )
    db.add(new_version)
    await db.flush()
    if current is not None:
        current.superseded_by_id = new_version.id

    change.status = "approved"
    change.reviewed_by_id = user.id
    change.reviewed_at = datetime.now(timezone.utc)

    # K5 step 7 / K4: an approval changes what's live, so it gets its own
    # snapshot -- same reasoning as scripts/ingest_sections.py, just
    # triggered by a single-section change instead of a full re-ingest.
    version = await create_corpus_version(
        db, label=f"approve-{change.section_number}-{new_version.id}",
        notes=f"approved staging change {change.id} for {change.section_number}",
    )
    await db.commit()
    return {"status": "approved", "new_section_version_id": str(new_version.id),
            "corpus_version_id": str(version.id)}


@router.post("/corpus/{staging_id}/reject")
async def reject(staging_id: str, payload: RejectIn, db: DB, user: CurrentUser):
    change = await db.get(CorpusStagingChange, staging_id)
    if change is None or change.status != "pending":
        raise HTTPException(404, "no pending staging change with that id")
    change.status = "rejected"
    change.reject_reason = payload.reason
    change.reviewed_by_id = user.id
    change.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "rejected"}


@router.get("/corpus/versions", response_model=list[CorpusVersionOut])
async def list_versions(db: DB, limit: int = Query(50, le=200)):
    rows = (await db.execute(
        select(CorpusVersion).order_by(CorpusVersion.created_at.desc()).limit(limit)
    )).scalars().all()
    return rows


@router.get("/sections/{act_code}/{section_number}/history", response_model=list[SectionHistoryEntry])
async def section_history(act_code: str, section_number: str, db: DB):
    act = (await db.execute(select(Act).where(Act.act_code == act_code))).scalar_one_or_none()
    if act is None:
        raise HTTPException(404, f"no act {act_code!r}")
    rows = (await db.execute(
        select(SectionVersion)
        .where(SectionVersion.act_id == act.id, SectionVersion.section_number == section_number)
        .order_by(SectionVersion.version_no)
    )).scalars().all()
    if not rows:
        raise HTTPException(404, f"no version history for {act_code} {section_number}")
    return [
        {"version_no": r.version_no, "marginal_note": r.marginal_note,
         "valid_from": r.valid_from.isoformat(), "valid_to": r.valid_to.isoformat() if r.valid_to else None,
         "is_repealed": r.is_repealed, "source_url": r.source_url, "parser_version": r.parser_version}
        for r in rows
    ]
