"""Centralised, type-safe configuration via pydantic-settings.

Everything is read from the environment (.env locally). No secrets in code.
Access through the cached `settings` singleton: `from app.core.config import settings`.
"""
from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _swap_scheme(url: str, driver: str) -> str:
    """postgres:// or postgresql:// -> postgresql+<driver>://. Managed
    providers (Neon included) commonly hand out the bare `postgres://` /
    `postgresql://` form; SQLAlchemy needs the driver named explicitly."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url.replace("postgresql://", f"postgresql+{driver}://", 1)


def _strip_sslmode(url: str) -> str:
    """asyncpg does NOT accept `sslmode=require` as a URL query parameter the
    way psycopg2 does -- passing Neon's stock connection string straight into
    an asyncpg engine fails. SSL is instead passed via connect_args (see
    app/db/base.py and alembic/env.py's async engine construction), so strip
    the param here rather than leaving it for asyncpg to choke on. psycopg2
    URLs are left untouched by _swap_scheme alone -- psycopg2 handles
    sslmode in the URL fine, no stripping needed for that driver."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() != "sslmode"]
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
            return _swap_scheme(_strip_sslmode(self.DATABASE_URL_RAW), "asyncpg")
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
            return _swap_scheme(_strip_sslmode(direct), "asyncpg")
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

    # --- Redis / Cache / Rate limit ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- LLM / Embeddings / News ---
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.1
    GROQ_MAX_TOKENS: int = 3000

    GEMINI_API_KEY: str | None = None
    GEMINI_EMBED_MODEL: str = "models/gemini-embedding-001"
    EMBEDDING_PROVIDER: Literal["gemini", "local"] = "local"
    EMBEDDING_DIM: int = 768

    NEWS_API_KEY: str | None = None

    # --- Retrieval ---
    RAG_TOP_K: int = 6
    RAG_MIN_SIMILARITY: float = 0.25  # cosine similarity floor for a "match"

    # --- Audit log retention (M2 hygiene) ---
    # Unbounded audit-log growth was flagged as a defect (D6); rows older than
    # this are deleted daily by app.tasks.worker.cleanup_audit_logs.
    AUDIT_LOG_RETENTION_DAYS: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
