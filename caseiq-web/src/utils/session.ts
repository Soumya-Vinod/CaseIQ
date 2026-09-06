// FIXED 2026-09-06: /legal/query's own multi-turn follow-up mechanism
// (app.api.v1.legal._history, keyed by session_id -- see docs/evaluation.md)
// has existed since before this file did, but QueryPage.tsx always sent
// session_id: "" -- and _history() returns [] for an empty session_id -- so
// no user of the deployed app has ever gotten real follow-up continuity.
// This is independent of login: _history() groups by session_id, not
// user_id, so a stable per-tab id is enough to fix it for anonymous and
// logged-in users alike, with no backend change needed.
//
// Deliberately sessionStorage, not localStorage: a "conversation" here means
// one sitting in one tab, not a permanent identity that persists after the
// tab closes and gets reused for an unrelated visit weeks later -- that
// would silently feed old, unrelated queries into the LLM's context as if
// they were part of a new question. Cleared when the tab closes, which is
// the correct lifetime for this, not a limitation to work around.
const SESSION_ID_KEY = "caseiq_session_id";

// In-memory fallback for when sessionStorage itself throws (some private-
// browsing modes, storage quota exhaustion) -- keeps the id stable for the
// rest of THIS page load even then, rather than minting a fresh one on
// every single call, which would silently reintroduce the exact bug this
// fix exists to close for that subset of users. Lost on reload, same as
// sessionStorage would be in the normal case, so this is a same-tier
// degradation, not a worse one.
let memoryFallbackId: string | null = null;

export function getSessionId(): string {
  try {
    let id = sessionStorage.getItem(SESSION_ID_KEY);
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem(SESSION_ID_KEY, id);
    }
    return id;
  } catch {
    if (!memoryFallbackId) memoryFallbackId = crypto.randomUUID();
    return memoryFallbackId;
  }
}

// Checklist item 6, Phase C: "resume" a past conversation from the history
// list. QueryPage never renders a scrolling thread of past turns -- it only
// ever shows the latest answer (the backend's _history() supplies prior
// turns to the LLM as context, invisibly) -- so "resume" doesn't mean
// re-displaying old messages there. It means: make this tab's ACTIVE
// session_id the historical one, so the next question the person types on
// the Ask page continues that same server-side thread instead of starting
// a new one. The history page itself (AccountPage) is what actually shows
// the past turns.
export function setSessionId(id: string): void {
  try {
    sessionStorage.setItem(SESSION_ID_KEY, id);
  } catch {
    memoryFallbackId = id;
  }
}

// FIXED 2026-09-06 (found in review, not by me): logging out only ever
// cleared the auth tokens (utils/auth.ts's clearTokens) -- this tab's
// session_id lived on, untouched, in a separate sessionStorage key. On a
// SHARED browser tab that's a real cross-user leak, not a theoretical one:
// A logs in, asks a question, logs out; B logs into the same tab and
// continues -- without this, B's next question would carry A's own
// session_id, and app.api.v1.conversations' ownership model (see that
// module's docstring) would need to defend against a session actually
// containing two different real users' rows. Called from AuthContext's
// logout() and deleteAccount() -- crossing either boundary starts a fresh
// thread. Deliberately NOT called from login()/register(): those are
// meant to preserve continuity with whatever was asked anonymously in this
// tab just before signing in (see getSessionId's own comment) -- only
// leaving an account behind should end a thread, not joining one.
export function resetSessionId(): string {
  const id = crypto.randomUUID();
  try {
    sessionStorage.setItem(SESSION_ID_KEY, id);
  } catch {
    memoryFallbackId = id;
  }
  return id;
}
