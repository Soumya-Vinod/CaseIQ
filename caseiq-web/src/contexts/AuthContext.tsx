import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { UserOut } from "../api/types";
import { clearTokens, getAccessToken, setTokens, subscribeToAuthChanges } from "../utils/auth";
import { resetSessionId } from "../utils/session";

interface RegisterFields {
  email: string;
  full_name: string;
  password: string;
  phone?: string;
  preferred_language?: string;
}

interface AuthState {
  user: UserOut | null;
  /** True only while the initial /auth/me check (on first load, or after a
   * token change elsewhere) is in flight -- lets a page show a neutral
   * "checking..." state instead of flashing "logged out" for a moment
   * before a real session is confirmed. */
  loading: boolean;
  login: (email: string, password: string) => Promise<{ error?: string }>;
  register: (fields: RegisterFields) => Promise<{ error?: string }>;
  logout: () => void;
  deleteAccount: (password: string) => Promise<{ error?: string }>;
}

const AuthContext = createContext<AuthState | null>(null);

/** Mounted once, at the top of the app (see App.tsx) -- every page reads
 * auth state through useAuth() rather than calling the API directly, so
 * "am I logged in" has exactly one source of truth. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  // `silent` skips the loading flip. login()/register() already have the
  // fresh user object in hand and call setUser() directly -- but they also
  // go through setTokens(), which notifies this same subscriber, triggering
  // a redundant refetch a moment later. Without `silent`, that refetch set
  // loading=true and briefly replaced the just-rendered account view with
  // "Checking your session..." (caught live: a Playwright check for the
  // account email right after registering saw it, then didn't, depending on
  // which side of the flicker it landed). The subscriber still needs to run
  // for the one case it actually matters -- a token cleared elsewhere (the
  // api client's 401 handler) without a setUser() call alongside it -- so it
  // stays wired up, just without visibly re-checking a session that was
  // never in doubt.
  async function refreshUser(silent = false) {
    if (!getAccessToken()) {
      setUser(null);
      if (!silent) setLoading(false);
      return;
    }
    if (!silent) setLoading(true);
    const { data, error } = await api.GET("/api/v1/auth/me");
    if (error) {
      // Token present but rejected (expired, user deactivated, etc.) --
      // the api client's own onResponse middleware already clears it on a
      // 401; this just makes sure local state agrees, for any other error.
      clearTokens();
      setUser(null);
    } else {
      setUser(data ?? null);
    }
    if (!silent) setLoading(false);
  }

  useEffect(() => {
    void refreshUser();
    // Re-check whenever a token is set/cleared anywhere -- login(), logout(),
    // or the api client's own 401 handler all go through utils/auth, so this
    // is the one place that needs to react to it. Silent: see refreshUser's
    // own comment on why this call must not toggle `loading`.
    return subscribeToAuthChanges(() => void refreshUser(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(email: string, password: string): Promise<{ error?: string }> {
    const { data, error } = await api.POST("/api/v1/auth/login", {
      body: { email, password },
    });
    if (error || !data) {
      return { error: "Incorrect email or password." };
    }
    setTokens(data.tokens.access, data.tokens.refresh);
    setUser(data.user);
    return {};
  }

  async function register(fields: RegisterFields): Promise<{ error?: string }> {
    const { data, error } = await api.POST("/api/v1/auth/register", {
      body: { preferred_language: "en", ...fields },
    });
    if (error || !data) {
      // app.core.exceptions' single JSON error envelope: {"error": {"code",
      // "message", "details"?}} -- e.g. code "email_taken" (409) for a
      // duplicate email, or "validation_error" (422) for a bad password/
      // email shape. Show the server's own message when it's the shape we
      // expect; fall back to a generic one rather than guessing at a
      // different shape.
      const message = (error as { error?: { message?: string } } | undefined)?.error?.message;
      return { error: message || "Could not create an account with those details." };
    }
    setTokens(data.tokens.access, data.tokens.refresh);
    setUser(data.user);
    return {};
  }

  function logout(): void {
    clearTokens();
    setUser(null);
    // FIXED 2026-09-06 (found in review): see utils/session.ts's
    // resetSessionId for the cross-user leak this closes on a shared tab.
    resetSessionId();
  }

  // Checklist item 6, Phase C: hard delete, password-confirmed (see
  // DELETE /auth/me's own docstring for why re-entering it matters). On
  // success, degrade exactly like logout() -- there's no "account" left to
  // stay signed into.
  async function deleteAccount(password: string): Promise<{ error?: string }> {
    const { error } = await api.DELETE("/api/v1/auth/me", { body: { password } });
    if (error) {
      const message = (error as { error?: { message?: string } } | undefined)?.error?.message;
      return { error: message || "Could not delete your account." };
    }
    clearTokens();
    setUser(null);
    resetSessionId();
    return {};
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, deleteAccount }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
