import type { HelplineOut } from "../api/types";
import styles from "./AbstentionCard.module.css";

/**
 * Renders a considered refusal, not an error. Backend short-circuited
 * before calling the LLM at all (app.services.retrieval.is_abstention) —
 * this is the deliberate result of that decision, not a failed request, so
 * it gets its own designed layout rather than reusing an error/toast style
 * or the empty-sources fallback in SourcesPanel.
 *
 * C4: helplines come from the backend's static, hand-verified table
 * (app.services.helplines) — this is the ONE path with nowhere else to
 * send someone, so it's the most important place to get this right. Used
 * to hardcode just NALSA here; now renders whatever the backend actually
 * verified, so a wrong number here can never again drift out of sync with
 * what's actually been checked.
 */
export function AbstentionCard({
  message,
  confidence,
  helplines,
}: {
  message: string;
  confidence: number;
  helplines: HelplineOut[];
}) {
  return (
    <section className={styles.card} aria-label="No confident answer">
      <p className={styles.eyebrow}>CaseIQ's assessment</p>
      <h2 className={styles.heading}>Not confident enough to answer</h2>
      <p className={styles.body}>{message}</p>
      <p className={styles.matchStrength}>
        Best match against the statutory text: {Math.round(confidence * 100)}% — below the
        threshold CaseIQ requires before it will answer.
      </p>
      {helplines.length > 0 && (
        <div className={styles.helplines}>
          <p className={styles.helplinesLabel}>Verified helplines</p>
          <ul className={styles.helplinesList}>
            {helplines.map((h) => (
              <li key={h.number} className={styles.helplineItem}>
                <a className={styles.action} href={`tel:${h.number}`}>
                  📞 {h.name} — {h.number}
                </a>
                <p className={styles.helplineWhen}>{h.when_to_use}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
