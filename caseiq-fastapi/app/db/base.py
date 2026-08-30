"""Async SQLAlchemy 2.0 engine, session factory, and declarative Base."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Two things only apply when talking to a managed Postgres (Neon, the
# deployment spike) through its POOLED endpoint -- both explicit here, with
# reasons, rather than baked into the connection string, per the deployment
# spike's own warning: this is exactly the kind of fix that gets silently
# undone later by someone copy-pasting a stock connection string back in.
#   ssl="require"            -- Neon requires TLS; asyncpg needs this passed
#                               as a connect arg, NOT as `?sslmode=require`
#                               in the URL (see config.py's _strip_sslmode).
#   statement_cache_size=0   -- Neon's pooled endpoint runs pgbouncer in
#                               TRANSACTION mode, which breaks asyncpg's
#                               server-side prepared-statement cache (a
#                               "prepared" statement can silently end up
#                               running against a different underlying
#                               connection under the pooler). Local dev talks
#                               directly to Postgres with no pooler in the
#                               way, so this would be pure downside there --
#                               conditional on DATABASE_URL_RAW being set,
#                               not applied unconditionally.
_connect_args: dict = {}
if settings.DATABASE_URL_RAW:
    _connect_args = {"ssl": "require", "statement_cache_size": 0}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and settings.ENV == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
