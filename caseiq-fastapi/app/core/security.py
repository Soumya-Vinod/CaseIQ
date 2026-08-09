"""Password hashing (argon2), JWT access/refresh token helpers, and IP hashing."""
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_ip(ip: str | None) -> str | None:
    """A keyed (HMAC-SHA256) hash of a client IP, truncated to fit the storage
    column -- never store the raw address. IP is personal data under India's
    DPDP Act 2023 (see docs/caseiq-claude-code-prompt.md D6). Keying with
    SECRET_KEY (rather than a plain unkeyed hash) matters: IPv4 is only ~4
    billion values, trivially rainbow-tabled without a secret pepper. Still
    deterministic per IP, so the same visitor's rows can be correlated for
    abuse/rate-limit investigation without the value being reversible.
    Truncated to 40 hex chars to fit the existing ip_hash column (String(45))
    without a wider migration -- still far more collision-resistant than the
    IP space itself.
    """
    if not ip:
        return None
    return hmac.new(settings.SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()[:40]


def _create_token(subject: str, expires_delta: timedelta, token_type: str, **extra: Any) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        **extra,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, **extra: Any) -> str:
    return _create_token(
        subject, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access", **extra
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh"
    )


def decode_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError subclasses on invalid/expired tokens."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
