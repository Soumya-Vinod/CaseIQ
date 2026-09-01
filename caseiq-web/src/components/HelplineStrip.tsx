import type { HelplineOut } from "../api/types";
import styles from "./HelplineStrip.module.css";

/**
 * Compact version of the same verified table AbstentionCard shows in full —
 * "alongside answers", per C4, not just on the refusal path. A resolved
 * answer isn't necessarily the end of what someone needs; this stays
 * low-key (a single wrapped line) rather than competing with the answer
 * itself for attention.
 */
export function HelplineStrip({ helplines }: { helplines: HelplineOut[] }) {
  if (helplines.length === 0) return null;
  return (
    <div className={styles.strip}>
      <span className={styles.label}>Need help now?</span>
      {helplines.map((h, i) => (
        <span key={h.number}>
          <a className={styles.link} href={`tel:${h.number}`}>
            {h.name} {h.number}
          </a>
          {i < helplines.length - 1 && <span className={styles.sep}>·</span>}
        </span>
      ))}
    </div>
  );
}
