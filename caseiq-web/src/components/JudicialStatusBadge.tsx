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
export function JudicialStatusBadge({ status }: { status: JudicialStatusOut }) {
  const isStruckDown = status.status === "struck_down";
  const isReadDown = status.status === "read_down";

  const label = isStruckDown
    ? "Struck down"
    : isReadDown
      ? "Read down"
      : status.status === "stayed"
        ? "Stayed"
        : status.status === "referred"
          ? "Referred to larger bench"
          : status.status;

  const kind = isStruckDown ? "struck" : isReadDown ? "readdown" : "neutral";

  return (
    <div className={`${styles.badge} ${styles[kind]}`} role="note">
      <span className={styles.icon} aria-hidden="true">
        {isStruckDown ? "✕" : isReadDown ? "⚠" : "ℹ"}
      </span>
      <div className={styles.body}>
        <p className={styles.label}>
          {label}
          {isStruckDown && (
            <span className={styles.subLabel}>— not live law, do not cite as in force</span>
          )}
        </p>
        <p className={styles.citation}>
          {status.case_name}
          {status.citation ? `, ${status.citation}` : ""}
          {status.court ? ` (${status.court}${status.decided_on ? `, ${status.decided_on}` : ""})` : ""}
        </p>
        {status.scope_note && <p className={styles.scopeNote}>{status.scope_note}</p>}
      </div>
    </div>
  );
}
