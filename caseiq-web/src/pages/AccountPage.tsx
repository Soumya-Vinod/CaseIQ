import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConversationDetailOut, ConversationSummaryOut } from "../api/types";
import { useAuth } from "../contexts/AuthContext";
import { dismissRedactionNote, isRedactionNoteDismissed } from "../utils/preferences";
import { setSessionId } from "../utils/session";
import styles from "./AccountPage.module.css";

// Added 2026-09-07: the preferred-language selector. "en" is deliberately
// the same value for both "auto-detect" and "explicitly want English" --
// the backend (app.api.v1.legal.process_query) only ever runs per-query
// detection when the incoming language IS "en", and `preferred_language`'s
// own DB default is also "en", so there is no way to distinguish "never
// set a preference" from "chose English" given the current schema. Not
// worth a schema change for: auto-detect already answers an English query
// in English, so the two cases behave identically in practice. Named here
// rather than silently offering a choice that doesn't really exist.
const LANGUAGE_OPTIONS: { value: string; label: string }[] = [
  { value: "en", label: "Auto-detect (default)" },
  { value: "hi", label: "Hindi" },
  { value: "mr", label: "Marathi" },
  { value: "ta", label: "Tamil" },
  { value: "te", label: "Telugu" },
];

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
 *
 * EXTENDED 2026-09-07 into the actual profile page (kept this component and
 * file name -- see docs/evaluation.md's undiscoverable-profile-UI entry for
 * why: this already did the job, the problem was never what this page
 * contained, only that nothing pointed at it). Added: account-created date,
 * a guest-state value proposition, and the preferences section --
 * `preferred_language`/`state`/`district` (server-side, PATCH /auth/me,
 * logged-in only) plus a note on the two preferences that work without an
 * account at all (Browse by act's remembered filter, the redaction note's
 * own dismiss button below) -- see utils/preferences.ts for why those two
 * specifically never needed a server round-trip.
 */
export function AccountPage({
  onBack,
  onGoToAsk,
}: {
  onBack: () => void;
  onGoToAsk: () => void;
}) {
  const { user, loading, login, register, logout, deleteAccount, updatePreferences } = useAuth();
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

  // Added 2026-09-07: preferences section. State/district are drafted
  // separately from `user` (a plain object, no form state of its own)
  // and only written on explicit Save, not on every keystroke -- language
  // saves immediately on change since a <select> has no "still typing"
  // state to protect against. Redrafted from `user` whenever it changes
  // (e.g. right after a save, or on first load) via the effect below.
  const [savingLanguage, setSavingLanguage] = useState(false);
  const [stateDraft, setStateDraft] = useState("");
  const [districtDraft, setDistrictDraft] = useState("");
  const [savingLocation, setSavingLocation] = useState(false);
  const [locationSaved, setLocationSaved] = useState(false);
  const [preferencesError, setPreferencesError] = useState<string | null>(null);
  const [redactionNoteDismissed, setRedactionNoteDismissed] = useState(() => isRedactionNoteDismissed());

  useEffect(() => {
    setStateDraft(user?.state ?? "");
    setDistrictDraft(user?.district ?? "");
  }, [user?.state, user?.district]);

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

  async function handleLanguageChange(value: string) {
    setSavingLanguage(true);
    setPreferencesError(null);
    const result = await updatePreferences({ preferred_language: value });
    setSavingLanguage(false);
    if (result.error) setPreferencesError(result.error);
  }

  async function handleSaveLocation(e: React.FormEvent) {
    e.preventDefault();
    setSavingLocation(true);
    setLocationSaved(false);
    setPreferencesError(null);
    const result = await updatePreferences({
      state: stateDraft.trim() || null,
      district: districtDraft.trim() || null,
    });
    setSavingLocation(false);
    if (result.error) setPreferencesError(result.error);
    else setLocationSaved(true);
  }

  function handleDismissRedactionNote() {
    dismissRedactionNote();
    setRedactionNoteDismissed(true);
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
            <div className={styles.accountRow}>
              <span className={styles.accountLabel}>Member since</span>
              <span>
                {new Date(user.created_at).toLocaleDateString(undefined, {
                  year: "numeric", month: "long", day: "numeric",
                })}
              </span>
            </div>
          </div>
          <button type="button" className={styles.logoutButton} onClick={logout}>
            Log out
          </button>

          <h2 className={styles.sectionTitle}>Preferences</h2>

          {preferencesError && <div className={styles.errorBox}>{preferencesError}</div>}

          <label className={styles.field}>
            <span className={styles.label}>Answer language</span>
            <select
              className={styles.input}
              value={user.preferred_language}
              disabled={savingLanguage}
              onChange={(e) => void handleLanguageChange(e.target.value)}
            >
              {LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <p className={styles.fieldHint}>
            Overrides CaseIQ's automatic per-question language detection. Leave on Auto-detect
            unless you specifically want every answer in one language regardless of how you ask.
          </p>

          <form className={styles.inlineForm} onSubmit={handleSaveLocation}>
            <label className={styles.field}>
              <span className={styles.label}>State</span>
              <input
                className={styles.input}
                value={stateDraft}
                onChange={(e) => {
                  setStateDraft(e.target.value);
                  setLocationSaved(false);
                }}
                placeholder="e.g. Maharashtra"
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>District</span>
              <input
                className={styles.input}
                value={districtDraft}
                onChange={(e) => {
                  setDistrictDraft(e.target.value);
                  setLocationSaved(false);
                }}
                placeholder="e.g. Mumbai Suburban"
              />
            </label>
            <button type="submit" className={styles.saveButton} disabled={savingLocation}>
              {savingLocation ? "Saving…" : locationSaved ? "Saved ✓" : "Save"}
            </button>
          </form>
          <p className={styles.fieldHint}>
            Prefills the Nearby Stations search when location access isn't available, instead of
            defaulting to Mumbai. You can still search a different city any time — this only sets
            the starting point.
          </p>

          <h2 className={styles.sectionTitle}>Your question history</h2>

          {!redactionNoteDismissed && (
            <div className={styles.noteBox}>
              <p>
                Your privacy is protected — names, numbers and addresses you type are replaced
                with placeholders before your question reaches the AI, and only this version is
                stored. That's why you'll see [NAME] and [PHONE] here instead of what you wrote.
              </p>
              <button type="button" className={styles.linkButton} onClick={handleDismissRedactionNote}>
                Got it, don't show this again
              </button>
            </div>
          )}
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
          <div className={styles.guestCard}>
            <p className={styles.guestEyebrow}>Guest</p>
            <p>
              You're using CaseIQ without an account — every feature works fully this way,
              including asking questions and filing complaint drafts. Logging in adds two things:
              your question history is kept for <strong>12 months</strong> instead of{" "}
              <strong>30 days</strong>, and you can set a preferred answer language and a default
              location for nearby police stations, below.
            </p>
          </div>

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

          <h2 className={styles.sectionTitle}>Preferences without an account</h2>
          <p className={styles.retentionLine}>
            A couple of things are remembered on this device even without logging in, and work
            the same either way: Browse by act keeps your last-used act filter, and the retention
            note above only needs dismissing once per device. Preferences tied to your identity
            specifically — answer language, a saved location — need an account, since they follow
            you across devices rather than staying on this one.
          </p>
        </>
      )}
    </main>
  );
}
