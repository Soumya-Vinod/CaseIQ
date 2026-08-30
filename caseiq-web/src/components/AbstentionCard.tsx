import styles from "./AbstentionCard.module.css";

/**
 * Renders a considered refusal, not an error. Backend short-circuited
 * before calling the LLM at all (app.services.retrieval.is_abstention) —
 * this is the deliberate result of that decision, not a failed request, so
 * it gets its own designed layout rather than reusing an error/toast style
 * or the empty-sources fallback in SourcesPanel.
 */
export function AbstentionCard({
  message,
  confidence,
}: {
  message: string;
  confidence: number;
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
      <div className={styles.actions}>
        <a className={styles.action} href="tel:15100">
          📞 NALSA Helpline — 15100
        </a>
        <a className={styles.action} href="https://nalsa.gov.in" target="_blank" rel="noreferrer">
          🔗 nalsa.gov.in
        </a>
      </div>
    </section>
  );
}
