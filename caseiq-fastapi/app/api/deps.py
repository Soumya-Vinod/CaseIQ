"""Auth dependencies: required current user, optional current user, role guard."""
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, PermissionError_
from app.core.security import decode_token
from app.db.base import get_db
from app.models.user import Role, User

bearer = HTTPBearer(auto_error=False)
DB = Annotated[AsyncSession, Depends(get_db)]


async def _user_from_token(token: str, db: AsyncSession) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise AuthError("Invalid token type.")
        user_id = payload["sub"]
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired token.") from exc
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise AuthError("User not found or inactive.")
    return user


async def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], db: DB
) -> User:
    if creds is None:
        raise AuthError("Authentication required.")
    return await _user_from_token(creds.credentials, db)


async def optional_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], db: DB
) -> User | None:
    if creds is None:
        return None
    try:
        return await _user_from_token(creds.credentials, db)
    except AuthError:
        return None


def require_role(*roles: Role):
    async def _guard(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in roles:
            raise PermissionError_("Insufficient permissions.")
        return user

    return _guard


CurrentUser = Annotated[User, Depends(current_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]


def client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else None)
