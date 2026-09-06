from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None
    preferred_language: str = "en"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountIn(BaseModel):
    # Re-entering the password, not just requiring a valid access token, so
    # a session left signed in on a shared/borrowed device can't be used to
    # erase the account without the person present. No soft-delete, no
    # grace period, no admin recovery flow -- see docs/dpdp-compliance.md.
    password: str


class Tokens(BaseModel):
    access: str
    refresh: str


class UserOut(ORMModel):
    id: UUID
    email: str
    full_name: str
    role: str
    preferred_language: str
    state: str | None = None
    district: str | None = None
    is_verified: bool


class AuthOut(BaseModel):
    user: UserOut
    tokens: Tokens
