import type { JudicialStatusOut } from "../api/types";
import styles from "./JudicialStatusBadge.module.css";

/**
 * Judicial-status warnings are the differentiator this tool has over a
 * generic chatbot: a struck-down or read-down provision must be impossible
 * to miss. Two distinct treatments, deliberately not colour-only — icon +
 * label + case citation, so the warning survives colour-blindness and
 * doesn't rely on "coloured word" alone.
 *
 * `struck_down` should in practice only ever reach this component via the
 * single section-detail endpoint that deliberately surfaces it (K2's hard
 * rule excludes it from every other read path) — see
 * GET /knowledge/sections/{act}/{section}. `read_down` is the one normal
 * retrieval is allowed to return, always with a scope_note.
 */
type Kind = "struck" | "readdown" | "neutral";

/**
 * Every status the backend is known to send. A value missing from here is
 * NOT an error: the database can hold a status before the frontend that
 * understands it is deployed (readiness E13 -- `not_operative` was written to
 * Neon ahead of this code). Unknown values fall back to `fallback()` below.
 */
const KNOWN: Record<string, { label: string; kind: Kind; icon: string; subLabel?: string }> = {
  struck_down: { label: "Struck down", kind: "struck", icon: "✕",
                 subLabel: "— not live law, do not cite as in force" },
  // Readiness E13: still in the statute but not operative as written -- a later
  // Act overrode it, or a court holds it in abeyance. Same warning treatment as
  // read_down: it must be impossible to read as plain live law.
  not_operative: { label: "Not operative", kind: "readdown", icon: "⚠",
                   subLabel: "— in the statute, but not in operation as written" },
  read_down: { label: "Read down", kind: "readdown", icon: "⚠" },
  stayed: { label: "Stayed", kind: "neutral", icon: "ℹ" },
  referred: { label: "Referred to larger bench", kind: "neutral", icon: "ℹ" },
  valid: { label: "Upheld", kind: "neutral", icon: "ℹ" },
};

/** An unrecognised status still means the backend flagged this section, so
 *  it gets the cautious (warning) treatment, a readable label made from the
 *  raw value, and a sub-label telling the reader to check -- never a blank,
 *  never the bare machine string. */
function fallback(raw: string | null | undefined) {
  const text = String(raw ?? "").replace(/[_-]+/g, " ").trim();
  const label = text ? text.charAt(0).toUpperCase() + text.slice(1) : "Legal status note";
  return { label, kind: "readdown" as Kind, icon: "⚠",
           subLabel: "— check this section's current legal status before relying on it" };
}

export function JudicialStatusBadge({ status }: { status: JudicialStatusOut }) {
  const view = KNOWN[status.status] ?? fallback(status.status);

  return (
    <div className={`${styles.badge} ${styles[view.kind]}`} role="note">
      <span className={styles.icon} aria-hidden="true">
        {view.icon}
      </span>
      <div className={styles.body}>
        <p className={styles.label}>
          {view.label}
          {view.subLabel && <span className={styles.subLabel}>{view.subLabel}</span>}
        </p>
        {(status.case_name || status.citation || status.court) && (
          <p className={styles.citation}>
            {status.case_name}
            {status.citation ? `${status.case_name ? ", " : ""}${status.citation}` : ""}
            {status.court ? ` (${status.court}${status.decided_on ? `, ${status.decided_on}` : ""})` : ""}
          </p>
        )}
        {status.scope_note && <p className={styles.scopeNote}>{status.scope_note}</p>}
      </div>
    </div>
  );
}
