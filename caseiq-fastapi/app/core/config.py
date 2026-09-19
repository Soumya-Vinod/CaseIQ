"""Centralised, type-safe configuration via pydantic-settings.

Everything is read from the environment (.env locally). No secrets in code.
Access through the cached `settings` singleton: `from app.core.config import settings`.
"""
from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, PostgresDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _swap_scheme(url: str, driver: str) -> str:
    """postgres:// or postgresql:// -> postgresql+<driver>://. Managed
    providers (Neon included) commonly hand out the bare `postgres://` /
    `postgresql://` form; SQLAlchemy needs the driver named explicitly."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url.replace("postgresql://", f"postgresql+{driver}://", 1)


# Query-string params that break asyncpg when the URL goes through
# SQLAlchemy's asyncpg dialect. Discovered empirically during the deployment
# spike (2026-08-11), not documented anywhere in advance:
#   sslmode          -- the well-known one (raw asyncpg.connect() rejects it
#                        outright, whether called directly or via SQLAlchemy).
#   channel_binding  -- NEWER: Neon's current connection strings include
#                        `channel_binding=require` (SCRAM channel binding).
#                        Raw `asyncpg.connect(url, ...)` tolerates it fine --
#                        a direct test connected successfully with it still
#                        in the URL. But SQLAlchemy's asyncpg dialect parses
#                        the URL's query string itself and forwards every
#                        param as a kwarg straight to asyncpg.connect(),
#                        which does NOT accept a `channel_binding` kwarg --
#                        TypeError, not a connection error, and only through
#                        SQLAlchemy (create_async_engine), not asyncpg
#                        itself. Confirms the spike's own warning that this
#                        class of gotcha needs to be explicit in code with
#                        comments, not fixed once and forgotten -- a NEWER
#                        Neon default already needed a second fix beyond
#                        what the spike instructions anticipated.
_ASYNCPG_INCOMPATIBLE_QUERY_PARAMS = {"sslmode", "channel_binding"}


def _strip_asyncpg_incompatible_params(url: str) -> str:
    """SSL is instead passed via connect_args (see app/db/base.py and
    alembic/env.py's async engine construction). psycopg2 URLs are left
    untouched by _swap_scheme alone -- psycopg2 handles both of these params
    in the URL fine, no stripping needed for that driver."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query)
             if k.lower() not in _ASYNCPG_INCOMPATIBLE_QUERY_PARAMS]
    return urlunsplit(parts._replace(query=urlencode(query)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- App ---
    PROJECT_NAME: str = "CaseIQ"
    ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Optional, unset by default -- see app.core.sentry.configure_sentry. Every
    # capture call in the SDK degrades to a cheap no-op when this is None
    # (measured directly, not assumed), so nothing in dev/CI/tests needs a
    # guard around it; only a real Render env var turns it on.
    SENTRY_DSN: str | None = None

    # --- Security ---
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database (async) ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "caseiq"

    # Managed-Postgres (Neon, deployment spike) override. When set, takes
    # precedence over the discrete POSTGRES_* fields above -- local dev keeps
    # using those untouched, a deployed environment sets these instead.
    # Both are plain `postgres://...`/`postgresql://...` strings exactly as
    # the provider hands them out (e.g. with `?sslmode=require`) -- NOT
    # pre-converted to a specific driver scheme, since DATABASE_URL and
    # MIGRATION_DATABASE_URL below both need asyncpg and handle the
    # sslmode-stripping differently from how a hypothetical psycopg2 caller
    # would.
    #   DATABASE_URL_RAW    -- the POOLED (pgbouncer) endpoint. The app's
    #                          runtime engine uses this.
    #   DATABASE_URL_DIRECT -- the DIRECT endpoint, bypassing the pooler.
    #                          Migrations use this (falls back to
    #                          DATABASE_URL_RAW if unset) -- Neon's pooled
    #                          endpoint runs pgbouncer in TRANSACTION mode,
    #                          which breaks the prepared-statement/advisory-
    #                          lock behaviour Alembic depends on for DDL, not
    #                          just the app's ordinary query traffic (which
    #                          is why the app's fix is statement_cache_size=0
    #                          rather than switching endpoints -- see
    #                          app/db/base.py).
    DATABASE_URL_RAW: str | None = None
    DATABASE_URL_DIRECT: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_RAW:
            return _swap_scheme(_strip_asyncpg_incompatible_params(self.DATABASE_URL_RAW), "asyncpg")
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def MIGRATION_DATABASE_URL(self) -> str:
        """What alembic/env.py connects with. This project's migrations run
        via async_engine_from_config (asyncpg), not psycopg2, despite what
        SYNC_DATABASE_URL's name might suggest -- see that field's docstring.
        Always the DIRECT endpoint when a managed-Postgres override is
        configured (never the pooled one, unlike DATABASE_URL above)."""
        direct = self.DATABASE_URL_DIRECT or self.DATABASE_URL_RAW
        if direct:
            return _swap_scheme(_strip_asyncpg_incompatible_params(direct), "asyncpg")
        return self.DATABASE_URL

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """psycopg2 URL. Currently unused by this app's own alembic/env.py
        (which is async -- see MIGRATION_DATABASE_URL) or anywhere else in
        app/; kept for any future sync tooling. Still made DIRECT-endpoint-
        aware so it can't quietly hand out the pooled endpoint to something
        that later gets wired to it and needs DDL/migration semantics."""
        direct = self.DATABASE_URL_DIRECT or self.DATABASE_URL_RAW
        if direct:
            return _swap_scheme(direct, "psycopg2")  # psycopg2 accepts sslmode in the URL fine
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_HOST_FOR_LOGGING(self) -> str:
        """host:port/dbname the app actually resolved for DATABASE_URL --
        NEVER credentials. Logged once at startup (app/main.py's lifespan)
        so "which database did this resolve to" is one glance at the log,
        not a traceback dig -- added after a 2026-08-13 Render deploy hit
        ConnectionRefusedError with no host in the traceback at all
        (ConnectionRefusedError's args are just the errno + "Connection
        refused", asyncio doesn't attach the target address), and the only
        way to tell "wrong DATABASE_URL_RAW value" apart from "DB is
        actually down" was to add this rather than guess from the
        traceback. See docs/deployment.md."""
        parts = urlsplit(self.DATABASE_URL)
        return f"{parts.hostname}:{parts.port or 5432}{parts.path}"

    @model_validator(mode="after")
    def _assert_database_url_direct_agrees_with_database_url(self) -> "Settings":
        """FOUND 2026-09-16 (docs/evaluation.md, observability entry): a
        script explicitly overrode DATABASE_URL_DIRECT to point at a local
        test database but left DATABASE_URL_RAW unset -- DATABASE_URL (which
        prefers DATABASE_URL_RAW) silently fell through to the real
        production value already sitting in this machine's own .env file.
        The write landed on production before anyone noticed the two URLs
        no longer agreed. This makes that class of mistake structurally
        impossible: whenever DATABASE_URL_DIRECT is set at all, it must
        resolve to the SAME target as DATABASE_URL, or this raises here, at
        settings-load time, before any engine is ever created -- an error,
        never a silent fallback to whichever one happened to be set.

        Compares host, port, and database name -- not just host. A bare
        hostname match would still pass two local Postgres instances on
        different ports (or different database names on the same instance)
        as "the same target", which is exactly the kind of partial-override
        mistake this exists to catch, just with lower stakes than the
        production incident that prompted it.

        NORMALIZED FOR NEON'S OWN POOLED/DIRECT NAMING CONVENTION
        SPECIFICALLY -- flagged HERE, at the rule itself, not only in the
        design discussion that produced it, because a silently-wrong
        assumption in exactly this spot is the failure class this project
        keeps finding: Neon's pooled endpoint hostname is its direct
        endpoint hostname with "-pooler" inserted immediately before the
        first "." (confirmed against this project's own real values --
        "ep-winter-river-ax8tv54p-pooler.c-4.us-east-2.aws.neon.tech" vs
        "ep-winter-river-ax8tv54p.c-4.us-east-2.aws.neon.tech"). That is a
        fact about Neon, not about managed Postgres in general. If this
        project ever moves providers, or Neon changes its own naming, this
        check does not fail safe -- it fails as a FALSE PASS: a genuine
        disagreement would stop being recognised as one, because the
        provider's real pooled/direct hosts no longer differ by this exact
        pattern, and this function would compare two now-different-looking
        strings that no longer collapse to equal after normalization,
        OR (the more dangerous direction) two hosts that use some other
        provider's OWN suffix convention that happens to still collapse
        here by coincidence. Revisit this function specifically -- not just
        rerun it and trust a green result -- if the connection provider
        ever changes.
        """
        if not self.DATABASE_URL_DIRECT:
            return self
        direct = urlsplit(self.DATABASE_URL_DIRECT)
        resolved = urlsplit(self.DATABASE_URL)
        if direct.hostname is None or resolved.hostname is None:
            return self  # a malformed URL is a different failure, not this check's job
        normalized_resolved_host = resolved.hostname.replace("-pooler.", ".", 1)
        resolved_port = resolved.port or 5432
        direct_port = direct.port or 5432
        if (direct.hostname, direct_port, direct.path) != (normalized_resolved_host, resolved_port, resolved.path):
            raise ValueError(
                f"DATABASE_URL_DIRECT ({direct.hostname}:{direct_port}{direct.path}) disagrees with "
                f"DATABASE_URL's resolved target ({resolved.hostname}:{resolved_port}{resolved.path}, "
                f"normalized host: {normalized_resolved_host}) -- refusing to start with an ambiguous "
                f"database target. This almost always means a PARTIAL override: one of "
                f"DATABASE_URL_RAW/DATABASE_URL_DIRECT was set explicitly while the other silently fell "
                f"through to .env's own value. Set both consistently, or unset the one you didn't mean "
                f"to override."
            )
        return self

    # --- Redis / Cache / Rate limit ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- LLM / Embeddings / News ---
    GROQ_API_KEY: str | None = None
    # FIXED 2026-09-07: found live, measured, not guessed -- the concurrency
    # ceiling this key sits behind is arithmetic (8000 TPM / ~3151
    # tokens/request ~= 2 concurrent requests), not an implementation bug --
    # see docs/evaluation.md's concurrency-ceiling entry. A second key on a
    # second Groq account gives real extra headroom under the SAME
    # arithmetic, not a fix for the arithmetic itself. Optional and
    # additive: absent, `LLMService` behaves exactly as it did with one key
    # (see its own docstring) -- no crash, no behaviour change.
    #
    # EXTENDED 2026-09-20 (docs/evaluation.md): generalized from a hardcoded
    # two-key pool to GROQ_API_KEY_2 through GROQ_API_KEY_9 -- a third key
    # was added for a live demo, and `app.services.llm.LLMService._groq_keys`
    # now walks this whole numbered range rather than checking `_2` alone.
    # Each one is independently optional; a gap or a stop anywhere in the
    # range just means a smaller pool, never a crash -- see that property's
    # own docstring. No functional "primary/secondary" role split exists or
    # ever did: every key here is an equal member of one ordered pool, tried
    # in ascending order, differing only in WHEN each is reached, never in
    # WHAT it's allowed to do.
    GROQ_API_KEY_2: str | None = None
    GROQ_API_KEY_3: str | None = None
    GROQ_API_KEY_4: str | None = None
    GROQ_API_KEY_5: str | None = None
    GROQ_API_KEY_6: str | None = None
    GROQ_API_KEY_7: str | None = None
    GROQ_API_KEY_8: str | None = None
    GROQ_API_KEY_9: str | None = None
    # llama-3.3-70b-versatile was retired from Groq's catalog (404 model_not_found,
    # discovered 2026-08-30 -- see docs/deployment.md). This default is a fallback for
    # environments with no GROQ_MODEL env var set; re-check Groq's /models list before
    # trusting it, since their catalog can drift again without notice.
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_TEMPERATURE: float = 0.1
    GROQ_MAX_TOKENS: int = 3000
    # ADDED 2026-09-20 (docs/evaluation.md), for a live demo whose real token
    # cost per query turned out to be ~3,600-4,000, not the ~2,900 originally
    # assumed -- detect_language and related_questions are each a REAL,
    # separate Groq call on top of the main generation call, and the
    # two-key-daily-pool assumption behind the demo's rate-limit increase was
    # never independently confirmed for TPD (only for TPM). This flag is the
    # fallback if the daily ceiling turns out lower than expected mid-demo:
    # True skips both auxiliary calls, dropping real per-query cost back to
    # ~2,900. See app.api.v1.legal.process_query for exactly what breaks with
    # this on (language auto-detection and suggested follow-up questions,
    # nothing else) -- deliberately named DEMO_-prefixed and surfaced on
    # /health (app/main.py) specifically so it cannot plausibly stay on by
    # accident after the event it was built for: anyone checking prod config
    # the way this project already habitually does sees it immediately.
    #
    # HOW A CHANGE ACTUALLY TAKES EFFECT, confirmed 2026-09-20 (docs/
    # evaluation.md), stated precisely because this is meant to work as a
    # mid-demo escape hatch: `settings` (this file's bottom) is a single
    # `@lru_cache`d object read from the environment ONCE at process start
    # -- toggling this on Render's dashboard does NOT reach an already-
    # running process; it takes effect only once the process actually
    # restarts and re-imports this module. Render does trigger that restart
    # automatically when an env var is saved (no git push, no new build), so
    # this is still usable live without a deploy in that sense -- but it is
    # a real process restart, not an instantaneous in-place flip, and this
    # project has no measured timing for that specific restart path (as
    # opposed to the well-documented 30-60s wake-from-15-minutes-idle cold
    # start). Expect a brief interruption when toggling this mid-demo, not
    # a silent, zero-disruption change.
    DEMO_TRIM_MODE: bool = False

    GEMINI_API_KEY: str | None = None
    GEMINI_EMBED_MODEL: str = "models/gemini-embedding-001"
    # "onnx": app.services.embeddings.LocalOnnxEmbedder -- a real, self-hosted
    # sentence embedding model (all-MiniLM-L6-v2, ONNX Runtime via fastembed,
    # no PyTorch), vendored under app/assets/embeddings/ so it never depends
    # on a runtime download. See docs/evaluation.md's embedding-swap entry
    # for the measured Render-512MB feasibility check this choice is based
    # on. EMBEDDING_DIM changes to 384 when this is selected -- see the
    # 0007_embedding_dim_384 migration; "local" (LocalEmbedder, hash-based)
    # and "gemini" both keep their original 768-dim behaviour unchanged.
    EMBEDDING_PROVIDER: Literal["gemini", "local", "onnx"] = "onnx"
    EMBEDDING_DIM: int = 384

    NEWS_API_KEY: str | None = None

    # --- Retrieval ---
    RAG_TOP_K: int = 6
    RAG_MIN_SIMILARITY: float = 0.25  # cosine similarity floor for a "match"

    # Below this, the top VECTOR-similarity match is treated as too weak to
    # answer from -- see app.services.retrieval.is_abstention. Chosen from a
    # small, real sample against the live LocalEmbedder corpus (2026-08-30),
    # NOT tuned or validated against a golden set (none exists yet -- see
    # docs/evaluation.md Priority 2):
    #   garbage  ("boiling point of methane on Titan"): max similarity 0.386-0.398
    #   legit    ("dowry harassment punishment"):        max similarity 0.489
    #   legit    ("file an FIR for cybercrime fraud"):    max similarity 0.252
    # That last row is the honest problem with this cutoff: ANY single
    # threshold that catches the garbage query above also catches this real,
    # in-scope one -- 0.252 < 0.398, so no cutoff separates them correctly.
    # The relationship INVERTS: nonsense retrieved better than a real
    # question. See docs/evaluation.md's "similarity does not separate
    # in-scope from out-of-scope" finding.
    #
    # Raised 0.20 -> 0.40 (2026-08-30, later same day). 0.20 caught NOTHING --
    # a civil easement/right-of-way question (not in this corpus at all) came
    # back at 66% confidence, cited against IPC 376/BNS 64 (rape), IPC 466
    # (forgery) -- nonsense citations presented as an answer. Before changing
    # the number, tested 0.55 and 0.60 (as asked) against real queries on the
    # live corpus:
    #   civil   ("right of way" / easement, OUT of scope):    max similarity 0.4768
    #   garbage ("boiling point of methane on Titan"):         max similarity 0.398
    #   legit   ("punishment for theft"):                      max similarity 0.478
    #   legit   ("punishment for defamation"):                 max similarity 0.478
    #   legit   ("dowry harassment punishment"):                max similarity 0.489
    #   legit   ("FIR filing procedure"):                       max similarity 0.535
    # Both 0.55 and 0.60 are ABOVE every one of those in-scope, legitimate
    # queries -- they would abstain on theft, defamation, dowry, AND the FIR
    # question, the most basic criminal-law queries this product exists to
    # answer. Evidence says don't use either value; a threshold that high
    # breaks the product, it doesn't fix the easement case.
    #
    # The harder finding: the civil easement question (0.4768) sits BETWEEN
    # the garbage query (0.398) and the legitimate ones (0.478-0.535) --
    # closer to "theft" (0.478, a 0.0012 gap) than to Titan. No single
    # threshold value separates "in-scope" from "out-of-scope" here; this
    # embedder's similarity score is not a scope signal for this specific
    # kind of case. Settled on 0.40 -- restores catching pure gibberish
    # (Titan, 0.398) without abstaining on any tested legitimate query -- and
    # added a SEPARATE, independent signal for cases like the easement one:
    # see is_civil_scope_mismatch in retrieval.py. Neither signal alone is
    # adequate; both together are still a heuristic, not a classifier. A real
    # embedding model remains the actual fix -- a concrete argument for the
    # Gemini/hybrid retrieval work in Priority 4. Still not tuned or
    # validated against a golden set -- none exists yet.
    #
    # RE-DERIVED 2026-09-06 for the embedding swap (LocalOnnxEmbedder,
    # all-MiniLM-L6-v2 -- see app/services/embeddings.py), against the
    # golden set (44 real queries, docs/golden_set.json) plus the same
    # out-of-scope cases above, exactly as instructed -- NOT carried over
    # from the old value on the assumption a "real" embedder needs the same
    # number. The similarity scale is fundamentally different now, and the
    # separation is no longer razor-thin:
    #   garbage ("boiling point of methane on Titan"):  max similarity 0.1469
    #     (down from 0.398 under LocalEmbedder -- the canonical false-
    #     positive this whole mechanism exists to catch now scores far
    #     BELOW threshold instead of drifting above it)
    #   civil   ("right of way" / easement, OUT of scope): max similarity 0.4609
    #     (still NOT separable from real queries by similarity alone -- see
    #     below; is_civil_scope_mismatch still does real work here)
    #   golden set (44 real, in-scope queries): minimum observed 0.4805,
    #     spread 0.48-0.90, mean well above 0.70 -- measured via
    #     scripts/calibrate_confidence.py, which also confirms this
    #     embedder produces the monotonic confidence/correctness
    #     relationship LocalEmbedder structurally couldn't (23 of 44 queries
    #     landing in ONE bucket regardless of correctness, previously --
    #     see docs/evaluation.md's confidence-calibration entry). Now
    #     correctness rate climbs from 0.00 (0.45-0.50 bucket, n=1, one real
    #     miss) to 1.00 (0.75+ buckets), with only small-N noise below 0.65.
    # 0.35 sits with real margin on both sides: ~0.20 above Titan, ~0.13
    # below the weakest of all 44 real golden-set queries -- not a
    # razor-thin gap the way 0.40-vs-0.398 was under the old embedder. The
    # civil-easement case (0.4609) still sits ABOVE this threshold, same as
    # before: pure similarity was never going to catch that specific
    # failure mode, real embeddings or not -- is_civil_scope_mismatch
    # remains a necessary second signal, not a legacy crutch this swap
    # retires. Still not validated against a dedicated out-of-scope golden
    # set (docs/golden_set.json's 44 entries are all in-scope, zero
    # negative examples -- a real gap, named in docs/evaluation.md, not
    # silently worked around here).
    ABSTENTION_SIMILARITY_THRESHOLD: float = 0.35

    # --- Audit log retention (M2 hygiene) ---
    # Unbounded audit-log growth was flagged as a defect (D6); rows older than
    # this are deleted daily by app.tasks.worker.cleanup_audit_logs.
    AUDIT_LOG_RETENTION_DAYS: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
