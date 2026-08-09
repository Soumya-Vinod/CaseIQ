from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB, client_ip
from app.core.exceptions import AuthError
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password, verify_password,
)
from app.models.user import User
from app.schemas.auth import AuthOut, ChangePasswordIn, LoginIn, RefreshIn, RegisterIn, Tokens, UserOut
from fastapi import Request
import jwt

router = APIRouter(prefix="/auth", tags=["Auth"])


def _tokens(user: User) -> Tokens:
    return Tokens(access=create_access_token(str(user.id), role=user.role),
                  refresh=create_refresh_token(str(user.id)))


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, db: DB):
    if await db.scalar(select(User).where(User.email == payload.email)):
        raise AuthError("Email already registered.", code="email_taken", status_code=409)
    user = User(
        email=payload.email, full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        phone=payload.phone, preferred_language=payload.preferred_language,
    )
    db.add(user)
    await db.flush()
    return AuthOut(user=UserOut.model_validate(user), tokens=_tokens(user))


@router.post("/login", response_model=AuthOut)
async def login(payload: LoginIn, db: DB, request: Request):
    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password) or not user.is_active:
        raise AuthError("Invalid credentials or inactive account.")
    return AuthOut(user=UserOut.model_validate(user), tokens=_tokens(user))


@router.post("/refresh", response_model=Tokens)
async def refresh(payload: RefreshIn, db: DB):
    try:
        data = decode_token(payload.refresh)
        if data.get("type") != "refresh":
            raise AuthError("Not a refresh token.")
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired refresh token.") from exc
    user = await db.get(User, data["sub"])
    if not user or not user.is_active:
        raise AuthError("User not found.")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return UserOut.model_validate(user)


@router.post("/change-password")
async def change_password(payload: ChangePasswordIn, user: CurrentUser, db: DB):
    if not verify_password(payload.old_password, user.hashed_password):
        raise AuthError("Old password is incorrect.", code="bad_password", status_code=400)
    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    return {"message": "Password changed."}
