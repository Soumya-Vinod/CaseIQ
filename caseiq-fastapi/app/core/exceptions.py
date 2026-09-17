"""Domain exceptions + a single JSON error envelope for the whole API."""
import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import logger


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "app_error"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class PermissionError_(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class BlockedQueryError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "query_blocked"


def _envelope(code: str, message: str, *, details: object = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_envelope(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("validation_error", "Invalid request.", details=exc.errors()),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", error=str(exc))
        # FIXED 2026-09-16 (docs/evaluation.md, observability entry): this is
        # the ONE seam every truly unhandled exception in the whole app
        # funnels through -- captured explicitly here rather than relied on
        # via Sentry's own automatic exception hook. This handler catches
        # the exception and returns a normal JSONResponse instead of letting
        # it propagate; whether Sentry's FastAPI integration still sees an
        # exception a registered handler already caught isn't something
        # this project verified live (would need a real DSN and a triggered
        # request), so an explicit call here is the version that's certain
        # to work regardless -- a possible duplicate event if the automatic
        # hook also fires is a far smaller problem than a silent gap. No-op
        # when SENTRY_DSN is unset (app.core.sentry).
        sentry_sdk.capture_exception(exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "Something went wrong."),
        )