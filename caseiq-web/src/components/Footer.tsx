import { useAuth } from "../contexts/AuthContext";
import styles from "./Footer.module.css";

/**
 * Persistent, site-wide disclaimer -- checklist item G5. Renders under every
 * tab's content (mounted once in App.tsx, inside `.content`) rather than as
 * a per-page addition, so "legal information, not legal advice" and the
 * footer links are never one tab away from view. Privacy Policy, Terms of
 * Use, and Account are plain content, not part of the primary eight-tab nav
 * (Sidebar.tsx's NAV_ITEMS) -- reached only from here. See AccountPage's
 * own docstring for why login lives here rather than as a ninth tab.
 */
export function Footer({
  onOpenPrivacy,
  onOpenTerms,
  onOpenAccount,
}: {
  onOpenPrivacy: () => void;
  onOpenTerms: () => void;
  onOpenAccount: () => void;
}) {
  const { user } = useAuth();
  return (
    <footer className={styles.footer}>
      <p className={styles.disclaimer}>
        CaseIQ provides legal information, not legal advice, and is not a substitute for a
        lawyer or the police. Answers are generated from statutory text and may be incomplete
        or wrong — always verify anything important with a qualified advocate or your nearest
        legal aid clinic.
      </p>
      <div className={styles.links}>
        <button type="button" className={styles.link} onClick={onOpenAccount}>
          {user ? user.full_name : "Log in"}
        </button>
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
