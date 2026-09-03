import { useState } from "react";
import styles from "./IncidentDatePrompt.module.css";

/**
 * C8: the visible half of temporal routing. The backend recognised the
 * query as describing something that already happened
 * (app.services.retrieval.implies_past_incident) and paused before
 * generating -- this is that pause, rendered. Two ways forward, both
 * explicit: give a date (routes to the regime that actually applied) or
 * say you don't know (proceeds across both, same as today, just no longer
 * a silent default). No third way to dismiss this without choosing one --
 * unlike the section detail sheet, there's nothing to "come back to" here,
 * this IS the next step in getting an answer.
 */
export function IncidentDatePrompt({
  message,
  onSubmitDate,
  onSkip,
  disabled,
}: {
  message: string;
  onSubmitDate: (date: string) => void;
  onSkip: () => void;
  disabled: boolean;
}) {
  const [date, setDate] = useState("");

  return (
    <section className={styles.card} aria-label="When did this happen?">
      <p className={styles.eyebrow}>Before I answer</p>
      <p className={styles.body}>{message}</p>
      <form
        className={styles.row}
        onSubmit={(e) => {
          e.preventDefault();
          if (date) onSubmitDate(date);
        }}
      >
        <label className={styles.dateField}>
          <span className={styles.dateLabel}>Date it happened</span>
          <input
            type="date"
            className={styles.dateInput}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            max={new Date().toISOString().slice(0, 10)}
            disabled={disabled}
          />
        </label>
        <button type="submit" className={styles.continueButton} disabled={disabled || !date}>
          Continue
        </button>
      </form>
      <button type="button" className={styles.skipButton} onClick={onSkip} disabled={disabled}>
        I don't know — check both
      </button>
    </section>
  );
}
