"""Adds a request_id to every request, binds it to structlog, returns it as a header,
and writes one async audit-log row per /api/ call WITHOUT blocking the response --
except Swagger/ReDoc/OpenAPI-schema requests (_AUDIT_EXCLUDED_PREFIXES), which carry
no audit signal and were previously logged on every docs-page load. The client IP is
never stored raw, only a keyed hash (see app.core.security.hash_ip), and rows older
than settings.AUDIT_LOG_RETENTION_DAYS are deleted daily by
app.tasks.worker.cleanup_audit_logs.
"""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger
from app.core.security import hash_ip
from app.db.base import SessionLocal
from app.models.audit import AuditLog

# Swagger/ReDoc/OpenAPI-schema requests fire on every docs-page load (assets,
# schema re-fetch on each interaction) and carry no audit signal -- excluding
# them was M2 hygiene item 2 (docs/caseiq-industry-readiness.md F3 / D6).
# These are fixed paths set directly on the FastAPI app in main.py
# (docs_url/redoc_url/openapi_url), not under API_V1_PREFIX, so they're
# excluded by exact prefix regardless of that setting.
_AUDIT_EXCLUDED_PREFIXES = ("/api/docs", "/api/redoc", "/api/openapi.json")


def _is_audited(path: str) -> bool:
    return path.startswith("/api/") and not path.startswith(_AUDIT_EXCLUDED_PREFIXES)


def _action_for(path: str) -> str:
    for key, action in (
        ("/auth/login", "user_login"), ("/auth/logout", "user_logout"),
        ("/auth/register", "user_register"), ("/legal", "legal_query"),
        ("/complaints", "complaint"), ("/knowledge", "knowledge_search"),
        ("/awareness", "news"),
    ):
        if key in path:
            return action
    return "api_request"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id", "path")
        took_ms = int((time.perf_counter() - start) * 1000)
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = str(took_ms)

        if _is_audited(request.url.path):
            await self._audit(request, response, request_id, took_ms)
        return response

    @staticmethod
    async def _audit(request: Request, response: Response, request_id: str, took_ms: int) -> None:
        try:
            async with SessionLocal() as db:
                db.add(AuditLog(
                    action=_action_for(request.url.path),
                    details={
                        "method": request.method, "path": request.url.path,
                        "status": response.status_code, "took_ms": took_ms,
                        "user_agent": request.headers.get("user-agent", "")[:500],
                    },
                    ip_hash=hash_ip(request.client.host if request.client else None),
                    request_id=request_id,
                ))
                await db.commit()
        except Exception as exc:  # never let auditing break a response
            logger.warning("audit_write_failed", error=str(exc))
