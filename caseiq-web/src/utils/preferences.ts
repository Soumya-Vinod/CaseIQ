// Added 2026-09-07: client-side-only preferences (checklist item 6 follow-
// up, the profile page's preferences section -- see docs/evaluation.md).
// Deliberately localStorage, not sessionStorage (contrast utils/session.ts):
// these are meant to survive a closed tab and a later visit, for guests and
// logged-in users alike, unlike a session_id which must NOT outlive its tab.
// No server round-trip, no schema -- see AccountPage's own docstring for
// why these two specifically never needed a user_preferences table.

const DEFAULT_ACT_KEY = "caseiq_default_act";
const REDACTION_NOTE_DISMISSED_KEY = "caseiq_redaction_note_dismissed";

export function getDefaultAct(): string {
  try {
    return localStorage.getItem(DEFAULT_ACT_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setDefaultAct(act: string): void {
  try {
    localStorage.setItem(DEFAULT_ACT_KEY, act);
  } catch {
    /* per-viewer convenience only -- fine to lose silently */
  }
}

export function isRedactionNoteDismissed(): boolean {
  try {
    return localStorage.getItem(REDACTION_NOTE_DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function dismissRedactionNote(): void {
  try {
    localStorage.setItem(REDACTION_NOTE_DISMISSED_KEY, "1");
  } catch {
    /* per-viewer convenience only -- fine to lose silently; worst case the
       note just shows again next time, not a functional problem */
  }
}
