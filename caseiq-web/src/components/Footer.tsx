import styles from "./Footer.module.css";

/**
 * Persistent, site-wide disclaimer -- checklist item G5. Renders under every
 * tab's content (mounted once in App.tsx, inside `.content`) rather than as
 * a per-page addition, so "legal information, not legal advice" and the two
 * policy links are never one tab away from view. The Privacy Policy and
 * Terms of Use pages themselves are plain content, not part of the primary
 * eight-tab nav (Sidebar.tsx's NAV_ITEMS) -- reached only from here.
 */
export function Footer({
  onOpenPrivacy,
  onOpenTerms,
}: {
  onOpenPrivacy: () => void;
  onOpenTerms: () => void;
}) {
  return (
    <footer className={styles.footer}>
      <p className={styles.disclaimer}>
        CaseIQ provides legal information, not legal advice, and is not a substitute for a
        lawyer or the police. Answers are generated from statutory text and may be incomplete
        or wrong — always verify anything important with a qualified advocate or your nearest
        legal aid clinic.
      </p>
      <div className={styles.links}>
        <button type="button" className={styles.link} onClick={onOpenPrivacy}>
          Privacy Policy
        </button>
        <button type="button" className={styles.link} onClick={onOpenTerms}>
          Terms of Use
        </button>
      </div>
    </footer>
  );
}
