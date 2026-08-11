"""Async Alembic environment wired to app settings + model metadata."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401  (import side-effect: registers all tables)

config = context.config
# MIGRATION_DATABASE_URL, not DATABASE_URL: migrations must always hit the
# DIRECT endpoint against a managed Postgres (Neon), never the pooled one --
# see app/core/config.py's MIGRATION_DATABASE_URL docstring.
config.set_main_option("sqlalchemy.url", settings.MIGRATION_DATABASE_URL)
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Same SSL requirement as app/db/base.py's runtime engine (Neon requires TLS,
# asyncpg needs it as a connect arg, not `?sslmode=require` in the URL) --
# NOT statement_cache_size=0, since migrations deliberately bypass the
# pooler entirely by using the direct endpoint, so that pgbouncer-specific
# fix doesn't apply here.
_connect_args: dict = {"ssl": "require"} if settings.DATABASE_URL_RAW else {}


def do_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata,
                      compare_type=True, compare_server_default=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = settings.MIGRATION_DATABASE_URL
    engine = async_engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool,
                                       connect_args=_connect_args)
    async with engine.connect() as conn:
        await conn.run_sync(do_migrations)
    await engine.dispose()


def run_offline() -> None:
    context.configure(url=settings.MIGRATION_DATABASE_URL, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_offline()
else:
    asyncio.run(run_async())
