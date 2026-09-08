import json
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DB, client_ip
from app.core.exceptions import AuthError
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password, verify_password,
)
from app.models.complaint import Complaint
from app.models.legal import LegalQuery, QueryStatus
from app.models.user import User
from app.schemas.auth import (
    AuthOut, ChangePasswordIn, DeleteAccountIn, LoginIn, RefreshIn, RegisterIn, Tokens,
    UpdatePreferencesIn, UserOut,
)
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


@router.patch("/me", response_model=UserOut)
async def update_preferences(payload: UpdatePreferencesIn, user: CurrentUser, db: DB):
    """Added 2026-09-07: the profile page's preferences section. `/auth/me`
    was GET-only until now -- `preferred_language` could be set at
    registration and never changed again; `state`/`district` existed on
    the model and were never write-reachable at all. `exclude_unset`, not
    a full-object overwrite: a request that only sends `state` must not
    silently null out `preferred_language` (or vice versa) just because
    the client didn't include it -- see UpdatePreferencesIn's own
    docstring for why this shape was chosen over a `user_preferences`
    table.
    """
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.add(user)
    await db.flush()
    return UserOut.model_validate(user)


@router.post("/change-password")
async def change_password(payload: ChangePasswordIn, user: CurrentUser, db: DB):
    if not verify_password(payload.old_password, user.hashed_password):
        raise AuthError("Old password is incorrect.", code="bad_password", status_code=400)
    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    return {"message": "Password changed."}


@router.get("/me/export")
async def export_my_data(user: CurrentUser, db: DB):
    """Checklist item 6, Phase C: a JSON export of a user's own conversation
    history -- scoped to rows where user_id == this user, deliberately
    narrower than the conversations router's ownership model (which also
    surfaces a session's pre-login, NULL-user turns for continuity). Data
    portability is about data collected under this identity; the anonymous
    turns before login weren't. See app.api.v1.conversations' own docstring
    and docs/evaluation.md for this as a considered call.

    Text below is the REDACTED, as-stored version, same as everywhere else
    in this feature -- the original wording was never persisted anywhere to
    export. Said plainly in the payload itself, not just in a doc someone
    exporting their data may never have read.
    """
    rows = (await db.execute(
        select(LegalQuery)
        .options(selectinload(LegalQuery.response))
        .where(LegalQuery.user_id == user.id, LegalQuery.status == QueryStatus.PROCESSED)
        .order_by(LegalQuery.created_at)
    )).scalars().all()

    payload = {
        "exported_at": datetime.now(UTC).isoformat(),
        "note": (
            "Personal details you typed (names, phone numbers, addresses, and similar) were "
            "replaced with placeholders like [NAME] before being stored, and only that "
            "redacted version is included below -- see CaseIQ's Privacy Policy."
        ),
        "account": {
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat(),
        },
        "conversations": [
            {
                "session_id": q.session_id,
                "query_id": str(q.id),
                "asked_at": q.created_at.isoformat(),
                "your_message_as_stored": q.original_query,
                "assistant_response": q.response.conversational_summary if q.response else None,
            }
            for q in rows
        ],
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=caseiq-my-data.json"},
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(payload: DeleteAccountIn, user: CurrentUser, db: DB):
    """Checklist item 6, Phase C: hard delete, no soft-delete, no grace
    period, no admin recovery -- per instruction. Deletes this user's own
    legal_queries (query_responses cascade via their own FK -- verified
    against the live schema, ondelete=CASCADE) and complaints explicitly,
    rather than leaving them merely orphaned: both legal_queries.user_id and
    complaints.user_id are ondelete=SET NULL at the DB level, which would
    disconnect the rows from this account but leave their content (redacted
    query text; UN-redacted complainant name/address/phone -- complaint
    drafting was never in scope for Phase A's redaction) sitting in the
    table. A request to delete an account is a request to erase personal
    data, not just to unlink it, so both are deleted outright here rather
    than relying on the FK's default behaviour.

    No separate token-revocation step needed: current_user/optional_user
    (app.api.deps) re-fetch the user row by id on every authenticated
    request rather than trusting the JWT payload alone, so an access token
    issued before this call stops working the moment the user row is gone
    -- verified live, not assumed from reading the dependency.
    """
    if not verify_password(payload.password, user.hashed_password):
        raise AuthError("Incorrect password.", code="bad_password", status_code=400)
    await db.execute(delete(LegalQuery).where(LegalQuery.user_id == user.id))
    await db.execute(delete(Complaint).where(Complaint.user_id == user.id))
    await db.delete(user)
