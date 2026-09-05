import { useState } from "react";
import { SITUATION_GUIDES } from "../data/situationGuides";
import { SituationGuideDetail } from "./SituationGuideDetail";
import styles from "./SituationGuidesPage.module.css";

/**
 * Index + detail in one component, same self-contained multi-state pattern
 * ComplaintPage's step wizard already uses -- no router in this app, and a
 * guide detail is reached only from this list, never from the sidebar
 * directly (mirrors how Terms/Privacy are reached only from the footer).
 */
export function SituationGuidesPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const guide = selected ? SITUATION_GUIDES.find((g) => g.slug === selected) : null;
  if (guide) {
    return <SituationGuideDetail guide={guide} onBack={() => setSelected(null)} />;
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Situation guides</p>
        <h1 className={styles.title}>What you're entitled to, step by step</h1>
        <p className={styles.subtitle}>
          Not a legal question to type in — a walkthrough for a specific situation. What to do
          right now, what the law says the police must do, and what to say if you're turned away.
        </p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      <ul className={styles.list}>
        {SITUATION_GUIDES.map((g) => (
          <li key={g.slug}>
            <button
              type="button"
              className={styles.card}
              onClick={() => setSelected(g.slug)}
            >
              <h2 className={styles.cardTitle}>{g.navLabel}</h2>
              <p className={styles.cardSummary}>{g.navSummary}</p>
              <span className={styles.cardLink}>Read the guide →</span>
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
