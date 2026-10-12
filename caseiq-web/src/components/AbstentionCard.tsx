import type { AbstentionSignalOut, HelplineOut } from "../api/types";
import styles from "./AbstentionCard.module.css";

/**
 * Renders a considered refusal, not an error. Backend short-circuited
 * before generating an answer (app.services.answer_gate) —
 * this is the deliberate result of that decision, not a failed request, so
 * it gets its own designed layout rather than reusing an error/toast style
 * or the empty-sources fallback in SourcesPanel.
 *
 * C4: helplines come from the backend's static, hand-verified table
 * (app.services.helplines) — this is the ONE path with nowhere else to
 * send someone, so it's the most important place to get this right. Used
 * to hardcode just NALSA here; now renders whatever the backend actually
 * verified, so a wrong number here can never again drift out of sync with
 * what's actually been checked. Chosen by topic and capped at two, same
 * as an answered query — this used to always be the full five regardless
 * of what the query was about (checklist item 4); NALSA is still the
 * floor when nothing more specific matched, never an empty list here.
 */
const pct = (v: number | null | undefined) => `${Math.round((v ?? 0) * 100)}%`;
const pts = (v: number | null | undefined) => `${Math.round((v ?? 0) * 100)} points`;

/**
 * One line per gate signal that actually refused, with the value it read
 * (app.services.answer_gate). `confidence` is the best retrieved similarity,
 * which is usually NOT what refused -- this card used to claim it was below
 * the threshold for every refusal, and none of the traced ones were
 * (docs/retrieval-fix-brief.md, step 1).
 */
function reasonText(s: AbstentionSignalOut): string {
  switch (s.signal) {
    case "domain_classifier":
      return `CaseIQ's topic check rated this ${pct(s.value)} likely to be a criminal-law question; it needs ${pct(s.threshold)}.`;
    case "low_similarity":
      return `The closest statutory text matched at ${pct(s.value)}; CaseIQ needs ${pct(s.threshold)} when no section matches the question's words directly.`;
    case "similarity_floor":
      return `The closest statutory text matched at only ${pct(s.value)}, under the ${pct(s.threshold)} minimum.`;
    case "ambiguous_top_hit":
      return `No section stood out: the best match led the others by ${pts(s.value)}; CaseIQ needs ${pts(s.threshold)}.`;
    case "civil_scope":
      return "The question reads as a civil-law matter, which CaseIQ's statutes don't cover.";
    case "relevance_verdict":
      return s.detail
        ? `On reading the sections it found, CaseIQ judged they don't answer this question. Missing: ${s.detail}.`
        : "On reading the sections it found, CaseIQ judged they don't answer this question.";
    case "relevance_unavailable":
      return "CaseIQ couldn't check this question against the statutes just now, so it won't guess. Please try again in a moment.";
    default:
      return `Refused by the ${s.signal} check.`;
  }
}

/** Signals whose own value is the best-match number, so showing it again is noise. */
const SHOWS_BEST_MATCH = new Set(["low_similarity", "similarity_floor"]);

export function AbstentionCard({
  message,
  confidence,
  signals,
  helplines,
}: {
  message: string;
  confidence: number;
  signals: AbstentionSignalOut[];
  helplines: HelplineOut[];
}) {
  return (
    <section className={styles.card} aria-label="No confident answer">
      <p className={styles.eyebrow}>CaseIQ's assessment</p>
      <h2 className={styles.heading}>Not confident enough to answer</h2>
      <p className={styles.body}>{message}</p>
      {signals.map((s) => (
        <p key={s.signal} className={styles.matchStrength}>
          Why: {reasonText(s)}
        </p>
      ))}
      {!signals.some((s) => SHOWS_BEST_MATCH.has(s.signal)) && (
        <p className={styles.matchStrength}>
          Closest statutory match: {pct(confidence)}.
        </p>
      )}
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
