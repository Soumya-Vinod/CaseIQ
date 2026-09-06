import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConversationDetailOut, ConversationSummaryOut } from "../api/types";
import { useAuth } from "../contexts/AuthContext";
import { setSessionId } from "../utils/session";
import styles from "./AccountPage.module.css";

/**
 * Terms/Privacy/Account are reachable only from the footer, not the primary
 * eight-tab nav -- see App.tsx's own comment on FooterPage. This is also
 * where checklist item 6, Phase C's history surface lives: a logged-in
 * user's own past conversations, listed, resumable, and deletable.
 *
 * "Resume" doesn't replay old messages here -- QueryPage never renders a
 * scrolling thread (see its own file), so there's nothing to hand it. It
 * means: point this tab's active session_id at the historical one
 * (utils/session.ts's setSessionId) and jump to the Ask tab, so the next
 * question typed there continues that same server-side conversation.
 */
export function AccountPage({
  onBack,
  onGoToAsk,
}: {
  onBack: () => void;
  onGoToAsk: () => void;
}) {
  const { user, loading, login, register, logout, deleteAccount } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [conversations, setConversations] = useState<ConversationSummaryOut[] | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [openSessionId, setOpenSessionId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetailOut | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);

  const [showDeleteAccount, setShowDeleteAccount] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [accountDeleted, setAccountDeleted] = useState(false);

  useEffect(() => {
    if (!user) {
      setConversations(null);
      return;
    }
    let cancelled = false;
    setHistoryError(null);
    void (async () => {
      const { data, error: apiError } = await api.GET("/api/v1/legal/conversations");
      if (cancelled) return;
      if (apiError) setHistoryError("Could not load your question history.");
      else setConversations(data ?? []);
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const result =
      mode === "login"
        ? await login(email, password)
        : await register({ email, password, full_name: fullName });
    if (result.error) setError(result.error);
    setSubmitting(false);
  }

  async function toggleConversation(sessionId: string) {
    if (openSessionId === sessionId) {
      setOpenSessionId(null);
      setDetail(null);
      return;
    }
    setOpenSessionId(sessionId);
    setDetail(null);
    setDetailLoading(true);
    const { data, error: apiError } = await api.GET(
      "/api/v1/legal/conversations/{session_id}",
      { params: { path: { session_id: sessionId } } },
    );
    setDetailLoading(false);
    if (!apiError) setDetail(data ?? null);
  }

  async function handleDeleteConversation(sessionId: string) {
    setDeletingSessionId(sessionId);
    const { error: apiError } = await api.DELETE(
      "/api/v1/legal/conversations/{session_id}",
      { params: { path: { session_id: sessionId } } },
    );
    setDeletingSessionId(null);
    if (!apiError) {
      setConversations((prev) => (prev ?? []).filter((c) => c.session_id !== sessionId));
      if (openSessionId === sessionId) {
        setOpenSessionId(null);
        setDetail(null);
      }
    }
  }

  function handleResume(sessionId: string) {
    setSessionId(sessionId);
    onGoToAsk();
  }

  async function handleExport() {
    const { data, error: apiError } = await api.GET("/api/v1/auth/me/export");
    if (apiError || data === undefined) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "caseiq-my-data.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function handleDeleteAccount(e: React.FormEvent) {
    e.preventDefault();
    setDeleting(true);
    setDeleteError(null);
    const result = await deleteAccount(deletePassword);
    setDeleting(false);
    if (result.error) setDeleteError(result.error);
    // Deliberately not an immediate onBack() -- that would silently drop
    // whoever just deleted their account back onto whatever sidebar tab was
    // showing underneath, with nothing on screen confirming it worked.
    else setAccountDeleted(true);
  }

  return (
    <main className={styles.page}>
      <button type="button" className={styles.backLink} onClick={onBack}>
        ← Back
      </button>

      <p className={styles.eyebrow}>Account</p>
      <h1 className={styles.title}>
        {accountDeleted ? "Account deleted" : user ? "Your account" : "Log in or create an account"}
      </h1>
      <p className={styles.subtitle}>
        {accountDeleted
          ? "You can create a new account at any time -- CaseIQ works fully without one too."
          : user
            ? "Manage your CaseIQ account."
            : "An account isn't required to use CaseIQ — everything works fully without one. Creating one will let you save and revisit your question history."}
      </p>
      <div className={styles.rule} aria-hidden="true" />

      {loading && <p className={styles.comingSoon}>Checking your session…</p>}

      {accountDeleted && (
        <>
          <p className={styles.noteBox}>
            Your account and saved conversations have been permanently deleted.
          </p>
          <button type="button" className={styles.submit} onClick={onBack}>
            Continue
          </button>
        </>
      )}

      {!accountDeleted && !loading && user && (
        <>
          <div className={styles.accountCard}>
            <div className={styles.accountRow}>
              <span className={styles.accountLabel}>Name</span>
              <span>{user.full_name}</span>
            </div>
            <div className={styles.accountRow}>
              <span className={styles.accountLabel}>Email</span>
              <span>{user.email}</span>
            </div>
          </div>
          <button type="button" className={styles.logoutButton} onClick={logout}>
            Log out
          </button>

          <h2 className={styles.sectionTitle}>Your question history</h2>

          <p className={styles.noteBox}>
            Your privacy is protected — names, numbers and addresses you type are replaced with
            placeholders before your question reaches the AI, and only this version is stored.
            That's why you'll see [NAME] and [PHONE] here instead of what you wrote.
          </p>
          <p className={styles.retentionLine}>
            CaseIQ's stated retention period is 12 months for a logged-in account's conversations
            (30 days for anonymous use). This is CaseIQ's documented policy, not an automated
            deletion — no scheduled job currently enforces it, so treat this as a stated
            commitment rather than a guarantee, and use "Delete" below for anything you want
            gone now. See the Privacy Policy for the full retention section.
          </p>

          {historyError && <div className={styles.errorBox}>{historyError}</div>}

          {conversations && conversations.length === 0 && !historyError && (
            <p className={styles.comingSoon}>
              No saved conversations yet — ask a question on the Ask tab while logged in to
              start one.
            </p>
          )}

          {conversations && conversations.length > 0 && (
            <div className={styles.conversationList}>
              {conversations.map((c) => (
                <div key={c.session_id} className={styles.conversationItem}>
                  <p className={styles.conversationPreview}>{c.preview}</p>
                  <p className={styles.conversationMeta}>
                    {c.turn_count} {c.turn_count === 1 ? "turn" : "turns"} · last activity{" "}
                    {new Date(c.last_activity).toLocaleDateString()}
                  </p>
                  <div className={styles.conversationActions}>
                    <button
                      type="button"
                      className={styles.linkButton}
                      onClick={() => void toggleConversation(c.session_id)}
                    >
                      {openSessionId === c.session_id ? "Hide" : "View"}
                    </button>
                    <button
                      type="button"
                      className={styles.linkButton}
                      onClick={() => handleResume(c.session_id)}
                    >
                      Continue
                    </button>
                    <button
                      type="button"
                      className={styles.dangerLink}
                      disabled={deletingSessionId === c.session_id}
                      onClick={() => void handleDeleteConversation(c.session_id)}
                    >
                      {deletingSessionId === c.session_id ? "Deleting…" : "Delete"}
                    </button>
                  </div>

                  {openSessionId === c.session_id && (
                    <div className={styles.turnList}>
                      {detailLoading && <p className={styles.comingSoon}>Loading…</p>}
                      {detail?.turns.map((t) => (
                        <div key={t.query_id}>
                          <div className={styles.turn}>
                            <p className={styles.turnRole}>You asked</p>
                            <p className={styles.turnText}>{t.original_query}</p>
                          </div>
                          {t.conversational_summary && (
                            <div className={styles.turn}>
                              <p className={styles.turnRole}>CaseIQ answered</p>
                              <p className={styles.turnText}>{t.conversational_summary}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <h2 className={styles.sectionTitle}>Your data</h2>
          <button type="button" className={styles.linkButton} onClick={() => void handleExport()}>
            Download a copy of your conversations (JSON)
          </button>

          <div className={styles.dangerZone}>
            <p className={styles.turnRole}>Delete account</p>
            <p className={styles.retentionLine}>
              Permanently deletes your account, your saved conversations, and any complaint
              drafts you created. This can't be undone — there's no grace period or recovery.
            </p>
            {!showDeleteAccount && (
              <button
                type="button"
                className={styles.dangerButton}
                onClick={() => setShowDeleteAccount(true)}
              >
                Delete my account
              </button>
            )}
            {showDeleteAccount && (
              <form className={styles.form} onSubmit={handleDeleteAccount}>
                <label className={styles.field}>
                  <span className={styles.label}>Confirm your password</span>
                  <input
                    className={styles.input}
                    type="password"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    required
                  />
                </label>
                {deleteError && <div className={styles.errorBox}>{deleteError}</div>}
                <button type="submit" className={styles.dangerButton} disabled={deleting}>
                  {deleting ? "Deleting…" : "Permanently delete my account"}
                </button>
              </form>
            )}
          </div>
        </>
      )}

      {!accountDeleted && !loading && !user && (
        <>
          <div className={styles.tabs}>
            <button
              type="button"
              className={`${styles.tab} ${mode === "login" ? styles.tabActive : ""}`}
              onClick={() => {
                setMode("login");
                setError(null);
              }}
            >
              Log in
            </button>
            <button
              type="button"
              className={`${styles.tab} ${mode === "register" ? styles.tabActive : ""}`}
              onClick={() => {
                setMode("register");
                setError(null);
              }}
            >
              Create account
            </button>
          </div>

          <form className={styles.form} onSubmit={handleSubmit}>
            {mode === "register" && (
              <label className={styles.field}>
                <span className={styles.label}>Full name</span>
                <input
                  className={styles.input}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </label>
            )}
            <label className={styles.field}>
              <span className={styles.label}>Email</span>
              <input
                className={styles.input}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Password</span>
              <input
                className={styles.input}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
            </label>

            {error && <div className={styles.errorBox}>{error}</div>}

            <button type="submit" className={styles.submit} disabled={submitting}>
              {submitting ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
            </button>
          </form>
        </>
      )}
    </main>
  );
}
