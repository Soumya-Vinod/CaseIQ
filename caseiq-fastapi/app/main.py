"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger
from app.core.ratelimit import limiter
from app.middleware.request_context import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("app_starting", env=settings.ENV, project=settings.PROJECT_NAME,
                db_host=settings.DATABASE_HOST_FOR_LOGGING)
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
