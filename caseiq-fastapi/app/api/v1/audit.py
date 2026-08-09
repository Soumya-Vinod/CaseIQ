from fastapi import APIRouter, Depends, Query

from app.api.deps import DB, require_role
from app.models.audit import AuditLog
from app.models.user import Role
from sqlalchemy import select

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", dependencies=[Depends(require_role(Role.ADMIN))])
async def list_logs(db: DB, action: str | None = None, limit: int = Query(50, le=200)):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": str(r.id), "action": r.action, "details": r.details,
             "ip": r.ip_address, "request_id": r.request_id,
             "created_at": r.created_at.isoformat()} for r in rows]
