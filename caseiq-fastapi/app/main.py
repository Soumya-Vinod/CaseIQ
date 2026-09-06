"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.build_info import get_build_info
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger
from app.core.ratelimit import limiter
from app.db.base import SessionLocal
from app.middleware.request_context import RequestContextMiddleware
from app.services.embeddings import assert_embedding_dim_matches_corpus


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # A stale --reload worker on Windows logs no error (see
    # app.core.build_info's docstring for the incident this is for) -- this
    # is what makes that visible: compare this line's source_fingerprint
    # against a fresh call to get_build_info() run separately, right now,
    # against the files on disk. Different fingerprint means this worker
    # is running old code no matter what its own logs claim.
    logger.info("app_starting", env=settings.ENV, project=settings.PROJECT_NAME,
                db_host=settings.DATABASE_HOST_FOR_LOGGING, **get_build_info())
    # FIXED 2026-09-06, found live on Render: the corpus (Neon) and the
    # embedding provider (Render's own env vars) are two independently
    # changeable places that must agree, and nothing enforced that -- a
    # mismatch here produces silently wrong answers at normal-looking
    # confidence, not an exception, because cosine similarity between two
    # different embedding spaces is still a valid float. See that function's
    # own docstring for the live incident this closes. Deliberately NOT
    # wrapped in try/except: a mismatch must crash startup, not degrade to a
    # logged warning nobody reads until a user notices wrong answers.
    async with SessionLocal() as db:
        await assert_embedding_dim_matches_corpus(db)
    yield
    logger.info("app_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.PROJECT_NAME} API",
        description="AI-powered Indian legal-awareness platform (FastAPI).",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "env": settings.ENV}

    return app


app = create_app()
