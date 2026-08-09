"""Adds a request_id to every request, binds it to structlog, returns it as a header,
and writes one async audit-log row per /api/ call WITHOUT blocking the response.
"""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger
from app.db.base import SessionLocal
from app.models.audit import AuditLog


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

        if request.url.path.startswith("/api/"):
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
                    ip_address=(request.client.host if request.client else None),
                    request_id=request_id,
                ))
                await db.commit()
        except Exception as exc:  # never let auditing break a response
            logger.warning("audit_write_failed", error=str(exc))
