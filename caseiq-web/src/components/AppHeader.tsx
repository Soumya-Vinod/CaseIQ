import styles from "./AppHeader.module.css";

/**
 * The wordmark + tagline, distinct from the tab nav below it (App.tsx) --
 * presence, not another row of chrome. The mark is typographic (a serif "§"
 * in a bordered square), not an icon-library glyph: it ties directly to
 * "cites its sources" rather than reading as generic SaaS iconography.
 */
export function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.brandRow}>
        <span className={styles.mark} aria-hidden="true">
          §
        </span>
        <span className={styles.wordmark}>
          Case<span className={styles.wordmarkAccent}>IQ</span>
        </span>
      </div>
      <p className={styles.tagline}>Indian Criminal Law — Cited, Not Assumed</p>
    </header>
  );
}
