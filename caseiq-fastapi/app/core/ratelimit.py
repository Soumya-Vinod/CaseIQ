"""Redis-backed rate limiting via slowapi. Falls back to in-memory if Redis is down."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=["200/hour"],
    headers_enabled=True,
)
