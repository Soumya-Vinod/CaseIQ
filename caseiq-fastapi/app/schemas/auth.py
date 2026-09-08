from datetime import datetime
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
    # Added 2026-09-07 (profile page, checklist item 6 follow-up): the
    # column has existed on every user row since `User`'s `Timestamped`
    # mixin, it just was never exposed here -- no migration, this is
    # purely a read-path addition.
    created_at: datetime


class UpdatePreferencesIn(BaseModel):
    """Added 2026-09-07, same profile-page pass as the sidebar/preferences
    work (see docs/evaluation.md). All optional and independently
    settable -- a client sends only the field(s) it's actually changing,
    never a full profile replacement, so one page section updating
    `preferred_language` can't accidentally null out `state`/`district`
    set from a different section (or vice versa). `preferred_language`,
    `state`, `district` all already existed as columns on `User` (the
    first from registration, the other two declared but never
    write-reachable until now) -- deliberately NOT a new `user_preferences`
    table: nothing here needed one.
    """
    preferred_language: str | None = None
    state: str | None = None
    district: str | None = None


class AuthOut(BaseModel):
    user: UserOut
    tokens: Tokens
