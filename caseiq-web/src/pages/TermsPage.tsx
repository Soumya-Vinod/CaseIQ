import styles from "./LegalPage.module.css";

export function TermsPage({ onBack }: { onBack: () => void }) {
  return (
    <main className={styles.page}>
      <button type="button" className={styles.backLink} onClick={onBack}>
        ← Back
      </button>

      <p className={styles.eyebrow}>Legal</p>
      <h1 className={styles.title}>Terms of Use</h1>
      <p className={styles.updated}>Last updated 5 September 2026</p>
      <div className={styles.rule} aria-hidden="true" />

      <section className={styles.section}>
        <div className={styles.callout}>
          <strong>CaseIQ provides legal information, not legal advice.</strong> Nothing in this
          app creates a lawyer-client relationship, and no answer or complaint draft should be
          treated as a substitute for advice from a qualified advocate who knows the full facts
          of your situation.
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What CaseIQ is</h2>
        <div className={styles.prose}>
          <p>
            CaseIQ answers questions about Indian criminal law and procedure — the Bharatiya
            Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS), Bharatiya Sakshya
            Adhiniyam (BSA), the Indian Penal Code (IPC), and the Code of Criminal Procedure
            (CrPC) — grounded in the actual statutory text, and helps draft a complaint letter.
            It does not cover civil law (property, tenancy, inheritance, contract disputes) or
            constitutional law, and will tell you so rather than guess when a question falls
            outside that scope.
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Accuracy and limitations</h2>
        <div className={styles.prose}>
          <p>
            Answers are generated from retrieved statutory text and may still be incomplete,
            outdated, or wrong. Coverage of some details — for example, whether a specific offence
            is cognizable or bailable — is partial, and CaseIQ will say so explicitly rather than
            guess when it doesn't have verified data for a section. A full account of what's
            measured and what's known to be incomplete is public in this project's evaluation
            record (<code>docs/evaluation.md</code> and <code>docs/model-card.md</code>).
          </p>
          <p>
            Always verify anything that matters — a filing deadline, whether you can be arrested,
            what a court will actually do — with a qualified advocate, the police, or your nearest
            legal aid clinic (NALSA helpline: 15100) before acting on it.
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Acceptable use</h2>
        <div className={styles.prose}>
          <ul>
            <li>Don't use CaseIQ to seek help committing an offence, evading detection, or
              obstructing an investigation — requests read that way are refused, and may be
              logged.</li>
            <li>Don't submit someone else's personal details (name, address, contact
              information) without their knowledge, beyond what's necessary for a complaint
              you're genuinely filing.</li>
            <li>Don't rely on CaseIQ as your only source before taking an action with real legal
              consequences.</li>
          </ul>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Your data</h2>
        <div className={styles.prose}>
          <p>
            What we store, why, and for how long is described in our Privacy Policy (linked
            alongside these Terms in the site footer). Using CaseIQ without an account still
            stores what you submit — see that page before entering anything you'd rather not
            have kept.
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Changes</h2>
        <div className={styles.prose}>
          <p>
            This project is under active development, and these terms may change as features are
            added or refined. Material changes will update the date at the top of this page.
          </p>
        </div>
      </section>
    </main>
  );
}
