"""Checklist item 6, Phase C: list/resume/delete a logged-in user's own
conversation history. A separate router from legal.py -- legal.py is the
query pipeline itself; this is account-scoped history management over rows
that pipeline already writes, the same split as complaints.py vs legal.py.

Ownership model (FIXED 2026-09-06, found in review, not by me): a
session_id's owner is the user_id on its EARLIEST row that has one at all
-- NOT "any row with a user_id", which is what this router shipped with
initially. The frontend keeps one session_id per browser tab regardless of
login state (see caseiq-web/src/utils/session.ts), so a person can ask a
couple of questions anonymously, log in mid-tab, and continue the SAME
session_id -- the anonymous turns before login have user_id NULL but are
still genuinely this person's conversation, and "any row matches" was
written to cover exactly that case.

But "any row matches" is also cross-user-reachable on a SHARED BROWSER
TAB, which the original version missed: A logs in, asks a question, logs
out; the tab's session_id survives logout (only the auth tokens were
cleared, see utils/auth.ts's clearTokens -- session_id lives in a separate
sessionStorage key, utils/session.ts, untouched by it). B then logs into
the SAME tab and continues the SAME session_id. That session now has rows
from both A and B, and "any row matches" made it belong to both --
B could list, read, and delete A's turns, and vice versa. Scoping
ownership to the EARLIEST logged-in row closes this: once a session is
first claimed by whoever's user_id appears on its first logged-in turn,
a later different user_id appearing in it (which the paired frontend fix
below should prevent from ever happening again, but this endpoint doesn't
get to assume that) never grants that second user access, and every
turn returned to the owner is filtered to (their own rows OR NULL-user
rows) -- a stray row tagged with a genuinely different user_id, however it
got there, is never included in what's shown or deleted.

The frontend fix this pairs with: AuthContext's logout() and
deleteAccount() now mint a fresh session_id (utils/session.ts's
resetSessionId) instead of leaving the old one in sessionStorage for
whoever uses the tab next. That closes the practical everyday case (and
the deeper one this router alone can't reach: app.api.v1.legal._history
feeds a session's full turn history to the LLM for continuity with NO
ownership check at all -- a stale shared session_id would have let B's
actual visible ANSWER reflect A's conversation, not just B's history page).
This router's own ownership fix is the defense that holds even if that
frontend fix is ever missing or bypassed.

Anonymous sessions -- explicitly, since it's not obvious from the code
alone: a session_id that has NEVER had a logged-in row has no owner
(_session_owner returns None), and None can never equal a real,
authenticated user's id. So holding/knowing a session_id is NEVER
sufficient by itself to GET or DELETE it here -- every route requires
CurrentUser (a valid access token) AND that token's user_id to match the
session's established owner. A purely-anonymous conversation is not
reachable through this router by anyone, logged in or not; it exists only
in the moment, for app.api.v1.legal._history's own use.

No pagination on GET (no path) today -- worth flagging honestly rather
than leaving unstated: an account with very many conversations gets them
all in one response. If pagination is added later, the LIMIT/OFFSET must
apply to `summaries` (the list AFTER grouping rows into conversations,
near the end of list_conversations below), never to the `rows` query
above it -- a limit on the raw row query would silently truncate a
conversation mid-thread rather than dropping whole conversations.

Every row's original_query/conversational_summary is the REDACTED text
stored at write time -- see ConversationTurnOut's own docstring
(app.schemas.legal) and LegalQuery.original_query's own comment
(app.models.legal) for why that can never be un-redacted here later.

GET /me/export (app.api.v1.auth) deliberately does NOT reuse this
ownership model -- it exports only rows where user_id == the current user,
not the wider session-owned set. Data-portability is about data collected
under this identity; the anonymous turns before login weren't. See
docs/dpdp-compliance.md §7 and docs/evaluation.md for this as a considered
call, not an oversight -- and for the resulting gap that a user's export
is narrower than what their own history page shows them.
"""
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DB
from app.core.exceptions import NotFoundError
from app.models.legal import LegalQuery, QueryStatus
from app.schemas.legal import ConversationDetailOut, ConversationSummaryOut, ConversationTurnOut

router = APIRouter(prefix="/legal/conversations", tags=["Conversation History"])


async def _session_owner(db: DB, session_id: str) -> UUID | None:
    """The user_id on this session's EARLIEST row that has one -- see this
    module's own docstring for why "earliest", not "any". None if the
    session has never had a logged-in row at all.
    """
    return await db.scalar(
        select(LegalQuery.user_id)
        .where(LegalQuery.session_id == session_id, LegalQuery.user_id.is_not(None))
        .order_by(LegalQuery.created_at)
        .limit(1)
    )


@router.get("", response_model=list[ConversationSummaryOut])
async def list_conversations(user: CurrentUser, db: DB):
    # DISTINCT ON (session_id), ordered by created_at -- Postgres's own idiom
    # for "the first row per group by this order", computed in one query
    # rather than fetching every row and picking earliest-per-session in
    # Python. This IS the ownership check, run for every session this user
    # has ever touched at once, not just the ones where they happen to be
    # first -- the WHERE below is what actually filters to theirs.
    owner_subq = (
        select(LegalQuery.session_id, LegalQuery.user_id.label("owner_id"))
        .distinct(LegalQuery.session_id)
        .where(LegalQuery.session_id != "", LegalQuery.user_id.is_not(None))
        .order_by(LegalQuery.session_id, LegalQuery.created_at)
        .subquery()
    )
    owned_ids = (await db.execute(
        select(owner_subq.c.session_id).where(owner_subq.c.owner_id == user.id)
    )).scalars().all()
    if not owned_ids:
        return []

    rows = (await db.execute(
        select(LegalQuery)
        .where(
            LegalQuery.session_id.in_(owned_ids),
            LegalQuery.status == QueryStatus.PROCESSED,
            # Belt and braces alongside the owner_subq filter above: even
            # inside a session this user owns, never count a row explicitly
            # tagged with a DIFFERENT real user_id (see module docstring --
            # shouldn't be reachable after the frontend fix, but this
            # endpoint doesn't get to assume that held).
            or_(LegalQuery.user_id.is_(None), LegalQuery.user_id == user.id),
        )
        .order_by(LegalQuery.session_id, LegalQuery.created_at)
    )).scalars().all()

    by_session: dict[str, list[LegalQuery]] = {}
    for q in rows:
        by_session.setdefault(q.session_id, []).append(q)

    summaries = [
        ConversationSummaryOut(
            session_id=session_id,
            preview=turns[0].original_query[:140],
            turn_count=len(turns),
            last_activity=turns[-1].created_at,
        )
        for session_id, turns in by_session.items()
        if turns  # a session_id with only BLOCKED/FAILED rows has no PROCESSED turns at all
    ]
    summaries.sort(key=lambda s: s.last_activity, reverse=True)
    # No pagination yet -- see this module's docstring. If added, slice
    # HERE, after grouping, never on the `rows` query above.
    return summaries


@router.get("/{session_id}", response_model=ConversationDetailOut)
async def get_conversation(session_id: str, user: CurrentUser, db: DB):
    owner_id = await _session_owner(db, session_id)
    if owner_id != user.id:
        # Same message whether the session doesn't exist, was never
        # logged-in, or belongs to someone else -- never confirm which, to
        # someone probing ids. owner_id is None for a purely-anonymous
        # session, which can never equal a real user.id -- see module
        # docstring's "Anonymous sessions" paragraph.
        raise NotFoundError("No conversation found with that id.")

    rows = (await db.execute(
        select(LegalQuery)
        .options(selectinload(LegalQuery.response))
        .where(
            LegalQuery.session_id == session_id,
            LegalQuery.status == QueryStatus.PROCESSED,
            or_(LegalQuery.user_id.is_(None), LegalQuery.user_id == owner_id),
        )
        .order_by(LegalQuery.created_at)
    )).scalars().all()

    return ConversationDetailOut(
        session_id=session_id,
        turns=[
            ConversationTurnOut(
                query_id=q.id,
                original_query=q.original_query,
                conversational_summary=q.response.conversational_summary if q.response else None,
                created_at=q.created_at,
            )
            for q in rows
        ],
    )


@router.delete("/{session_id}", status_code=204)
async def delete_conversation(session_id: str, user: CurrentUser, db: DB):
    owner_id = await _session_owner(db, session_id)
    if owner_id != user.id:
        raise NotFoundError("No conversation found with that id.")
    # A bulk Core DELETE, not session.delete() per row -- query_responses'
    # own FK (query_id, ondelete=CASCADE -- verified directly against the
    # live schema, not assumed from the model file) cleans up the paired
    # response rows without the ORM needing to load them first. Scoped to
    # (this session AND (NULL-user OR this owner)) -- never touches a row
    # explicitly tagged with a different real user_id, same reasoning as
    # get_conversation's filter above.
    await db.execute(delete(LegalQuery).where(
        LegalQuery.session_id == session_id,
        or_(LegalQuery.user_id.is_(None), LegalQuery.user_id == owner_id),
    ))
