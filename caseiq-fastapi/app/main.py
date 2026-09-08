"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.build_info import get_build_info
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger
from app.core.ratelimit import limiter
from app.db.base import SessionLocal
from app.middleware.request_context import RequestContextMiddleware
from app.services.domain_classifier import assert_domain_gate_matches_embedder
from app.services.embeddings import assert_embedding_config_matches_corpus, embedder


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
    # different embedding spaces is still a valid float. Checks the ACTUAL
    # running `embedder` object's identity, not just the EMBEDDING_PROVIDER
    # string -- get_embedder() no longer has a silent fallback (see its own
    # docstring), so these should always agree, but this check doesn't get
    # to assume that held. See that function's own docstring for the live
    # incident this closes. Deliberately NOT wrapped in try/except: a
    # mismatch must crash startup, not degrade to a logged warning nobody
    # reads until a user notices wrong answers.
    async with SessionLocal() as db:
        await assert_embedding_config_matches_corpus(db, embedder)
    # Option B, shipped 2026-09-08 (docs/evaluation.md): the domain-gate
    # classifier's weights are only meaningful against the exact embedding
    # space they were trained on -- same failure shape as the check just
    # above, one layer up (a swapped embedder produces a confident, wrong
    # classifier verdict, not an exception, for the identical reason a
    # swapped embedder produces a confident, wrong similarity score). No DB
    # needed for this one -- a pure in-process identity comparison against
    # the artifact's own stamped embedding_model_id. Deliberately NOT
    # wrapped in try/except, same reasoning as the check above.
    assert_domain_gate_matches_embedder(embedder)
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

    # FIXED 2026-09-08 (docs/evaluation.md): SlowAPIMiddleware was never
    # added -- app.state.limiter and the exception handler existed, but
    # nothing actually enforced any limit on any route (confirmed by
    # grep, not assumed: zero @limiter.limit usages anywhere before this).
    # This is what makes app.core.ratelimit's default_limits (and any
    # @limiter.limit override on a specific route) actually run.
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        # Same envelope every other error in this app uses
        # (app.core.exceptions._envelope's shape) -- slowapi's OWN default
        # handler returns {"error": "Rate limit exceeded: <detail>"}, a
        # flat string that doesn't match anything else this API returns.
        # `exc.detail` is slowapi's own human-readable description of
        # which limit was hit (e.g. "5 per 1 hour") -- included so the
        # message says something specific, not just "try again."
        # `_inject_headers` is the same call slowapi's default handler
        # makes -- Retry-After and the X-RateLimit-* headers, not
        # reimplemented here, just kept.
        #
        # FIXED 2026-09-08, found only by reading slowapi.middleware's own
        # source after a live trigger surfaced a related crash (see
        # app.api.v1.legal.process_query's comment): a route with NO
        # @limiter.limit decorator (i.e. every route except /legal/query and
        # /complaints, covered only by this Limiter's default_limits) has
        # its check run inside SlowAPIMiddleware's *synchronous* dispatch,
        # which explicitly does `if inspect.iscoroutinefunction(handler):
        # handler = _rate_limit_exceeded_handler` -- an async handler here
        # would have been silently swapped for slowapi's own flat-string
        # default on every one of those routes, while looking correctly
        # wired everywhere else. A plain `def` (nothing below needs to be
        # async) satisfies both call paths: Starlette's normal async
        # exception middleware for /legal/query and /complaints' decorator-
        # raised RateLimitExceeded, and this middleware's own manual sync
        # dispatch for every default_limits-only route.
        response = JSONResponse(
            status_code=429,
            content={"error": {
                "code": "rate_limited",
                "message": f"Too many requests ({exc.detail}) -- please wait and try again.",
            }},
        )
        return request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)

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
        # FIXED 2026-09-06: added after several rounds of being unable to
        # confirm, from outside, what a deployed instance was actually
        # running -- neither Render's dashboard env vars nor a git push are
        # visible from here, and the only prior signal was inferring from
        # query behaviour, which is exactly how a real embedding-provider/
        # corpus mismatch went unnoticed. embedding_model is the ACTUAL
        # running embedder's identity (app.services.embeddings.embedder
        # .model_id), not just the EMBEDDING_PROVIDER setting -- the two
        # should always agree now that get_embedder() has no silent
        # fallback, but this endpoint doesn't get to assume that either;
        # if they ever diverge, that divergence is itself the finding.
        # Deliberately no request-body echo, no secrets -- config shape
        # only, safe to leave public on a project with no user data at
        # stake in an env var name.
        build = get_build_info()
        return {
            "status": "ok",
            "env": settings.ENV,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_dim": settings.EMBEDDING_DIM,
            "embedding_model": embedder.model_id,
            "git_commit": build.get("git_commit"),
        }

    return app


app = create_app()
