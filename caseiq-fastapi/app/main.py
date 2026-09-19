"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import sentry_sdk

from app.api.v1.router import api_router
from app.core.build_info import get_build_info
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger
from app.core.ratelimit import limiter
from app.core.sentry import configure_sentry
from app.db.base import SessionLocal
from app.db.migration_check import assert_alembic_head_matches_db
from app.middleware.request_context import RequestContextMiddleware
from app.services.domain_classifier import assert_domain_gate_matches_embedder
from app.services.embeddings import assert_embedding_config_matches_corpus, embedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    # FIRST, before configure_logging or anything else that could plausibly
    # fail -- see app.core.sentry.configure_sentry's own docstring for why
    # this has to be active before the two assertions below run, not after.
    configure_sentry()
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
    # incident this closes.
    #
    # FIXED 2026-09-16 (docs/evaluation.md, observability entry): still
    # deliberately crashes startup on a mismatch -- that part is unchanged
    # and correct, a mismatch must never degrade to a logged warning nobody
    # reads until a user notices wrong answers. What changed: a crash here
    # used to reach nobody -- Render would show a failed deploy in its own
    # dashboard and nothing else. Automatic capture (Sentry's global
    # exception hook, sys.excepthook) can't be relied on for THIS specific
    # failure -- checked directly against the installed uvicorn source
    # (uvicorn/lifespan/on.py's LifespanOn.main()), not assumed: it wraps
    # the whole lifespan call in `except BaseException`, logs it, and
    # returns WITHOUT re-raising -- this exception never becomes a raw,
    # process-level uncaught exception at all, so there's nothing for a
    # global hook to see. Explicit capture + flush (the process exits right
    # after this, so the event must be sent before that happens, not queued
    # and lost) + re-raise the SAME exception, unmodified -- the
    # crash-startup behaviour is bit-for-bit identical to before, Sentry is
    # just now also watching.
    try:
        async with SessionLocal() as db:
            # FIXED 2026-09-19 (docs/evaluation.md): checked FIRST, before the
            # embedder/corpus check below -- a schema the code doesn't match is
            # the more fundamental problem, and catching it here gives a clean,
            # specific error instead of letting the embedder check fail with a
            # confusing raw "relation does not exist" if the corpus tables
            # themselves were part of what never got migrated. See
            # app.db.migration_check's own module docstring for the live
            # incident this closes: 0014_directive_language_stats shipped as
            # code and 500'd on every real query for as long as its migration
            # hadn't been run, with nothing watching for that gap.
            await assert_alembic_head_matches_db(db)
            await assert_embedding_config_matches_corpus(db, embedder)
        # Option B, shipped 2026-09-08 (docs/evaluation.md): the domain-gate
        # classifier's weights are only meaningful against the exact
        # embedding space they were trained on -- same failure shape as the
        # check just above, one layer up (a swapped embedder produces a
        # confident, wrong classifier verdict, not an exception, for the
        # identical reason a swapped embedder produces a confident, wrong
        # similarity score). No DB needed for this one -- a pure in-process
        # identity comparison against the artifact's own stamped
        # embedding_model_id.
        assert_domain_gate_matches_embedder(embedder)
    except Exception:
        sentry_sdk.capture_exception()
        sentry_sdk.flush(timeout=5)
        raise
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
        #
        # FIXED 2026-09-16 (docs/evaluation.md, observability entry): a 429
        # used to be invisible to structlog entirely -- the ONLY record was
        # a per-request AuditLog row's `status` field (RequestContextMiddleware),
        # queryable but not in the structured log stream everything else
        # goes through. Logged here directly (not via contextvars, which
        # this handler's two different call paths -- see the comment above
        # -- don't reliably bind) so the signal exists at all; volume-based
        # alerting on this lives in scripts/check_observability_thresholds.py
        # (a rate, not a per-event capture -- a single rate-limited user is
        # normal, expected behaviour, not an incident on its own).
        logger.warning("rate_limited", path=request.url.path, detail=exc.detail)
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
        # allowed_origins added 2026-09-19: same blind spot as the rest of this
        # endpoint's docstring, applied to CORS specifically -- a Render
        # dashboard env var being saved and a deploy completing are both
        # externally observable, but "what did settings.ALLOWED_ORIGINS
        # actually resolve to inside the running container" was not, which is
        # why a browser had to find this instead of anything on our side. No
        # secrets in this value (it's a list of public frontend origins),
        # same safety rationale as the rest of this endpoint.
        build = get_build_info()
        return {
            "status": "ok",
            "env": settings.ENV,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_dim": settings.EMBEDDING_DIM,
            "embedding_model": embedder.model_id,
            "allowed_origins": settings.ALLOWED_ORIGINS,
            "git_commit": build.get("git_commit"),
        }

    return app


app = create_app()
