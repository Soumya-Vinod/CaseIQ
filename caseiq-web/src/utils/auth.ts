// Token storage: sessionStorage, deliberately -- decided over localStorage
// (XSS-exposed, persists indefinitely, shared across every tab) and over
// memory-only (safest against passive token theft, but forces a re-login on
// every page refresh -- bad fit for a tool people return to). sessionStorage
// survives a refresh but dies with the tab and isn't shared across tabs or
// devices -- a real feature for a legal tool on a possibly-shared device,
// not just a compromise.
//
// Stated honestly, not glossed over: this is still readable by any script
// that runs in this page's origin, so a successful XSS attack CAN read a
// live session's tokens for as long as that tab stays open. Refresh-token
// rotation via an httpOnly cookie (immune to this specific attack, since JS
// can never read an httpOnly cookie at all) is the correct long-term answer
// and is scoped future work, not attempted here -- it requires a backend
// change (the cookie has to be set server-side) and cross-origin cookie
// handling (frontend and backend are on different registrable domains),
// which is a materially bigger piece of work than this pass's scope.
const ACCESS_KEY = "caseiq_access_token";
const REFRESH_KEY = "caseiq_refresh_token";

type Listener = () => void;
const listeners = new Set<Listener>();

function notify(): void {
  for (const fn of listeners) fn();
}

/** Re-run whenever tokens change (login/logout/expiry), from anywhere --
 * lets AuthContext stay in sync without every caller having to know about
 * every other caller. */
export function subscribeToAuthChanges(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function getAccessToken(): string | null {
  try {
    return sessionStorage.getItem(ACCESS_KEY);
  } catch {
    return null;
  }
}

export function getRefreshToken(): string | null {
  try {
    return sessionStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export function setTokens(access: string, refresh: string): void {
  try {
    sessionStorage.setItem(ACCESS_KEY, access);
    sessionStorage.setItem(REFRESH_KEY, refresh);
  } catch {
    // sessionStorage unavailable (private-browsing edge cases, quota) --
    // login just won't persist across a reload in this tab. Not fatal;
    // matches the same degradation already accepted in utils/session.ts.
  }
  notify();
}

export function clearTokens(): void {
  try {
    sessionStorage.removeItem(ACCESS_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  } catch {
    // nothing to clean up if storage was never reachable
  }
  notify();
}
