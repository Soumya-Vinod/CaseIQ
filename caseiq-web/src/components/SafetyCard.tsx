import type { HelplineOut } from "../api/types";
import styles from "./AbstentionCard.module.css";

/**
 * Readiness E13: the two fixed safety responses (backend short-circuits
 * before retrieval). Renders ONLY the message and the verified numbers --
 * no statutes, no What-to-do panel, no rights list, no sources.
 */
export function SafetyCard({
  kind,
  message,
  helplines,
}: {
  kind: "crisis_support" | "evasion_refused";
  message: string;
  helplines: HelplineOut[];
}) {
  const crisis = kind === "crisis_support";
  return (
    <div className={styles.card} role={crisis ? "alert" : "status"}>
      <p className={styles.eyebrow}>{crisis ? "You're not alone" : "CaseIQ can't help with this"}</p>
      <h2 className={styles.heading}>{crisis ? "Please talk to someone now" : "Get help the right way"}</h2>
      <p className={styles.body}>{message}</p>
      {helplines.length > 0 && (
        <div className={styles.actions}>
          {helplines.map((h) => (
            <a key={h.number} className={styles.action} href={`tel:${h.number.replace(/-/g, "")}`}>
              {h.name} · {h.number}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
