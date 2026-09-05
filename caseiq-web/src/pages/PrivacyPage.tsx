import styles from "./LegalPage.module.css";

// Plain-language version of docs/dpdp-compliance.md, kept consistent with
// it deliberately -- this page must never claim stronger protection than
// that document (or app/services/pii_redaction.py) actually delivers. See
// that doc's own note on why an accurate "detects and removes common
// personal details" is the honest claim, not "removes all personal details."
export function PrivacyPage({ onBack }: { onBack: () => void }) {
  return (
    <main className={styles.page}>
      <button type="button" className={styles.backLink} onClick={onBack}>
        ← Back
      </button>

      <p className={styles.eyebrow}>Legal</p>
      <h1 className={styles.title}>Privacy Policy</h1>
      <p className={styles.updated}>Last updated 5 September 2026</p>
      <div className={styles.rule} aria-hidden="true" />

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What we store</h2>
        <div className={styles.prose}>
          <p>
            You don't need an account to ask a question or draft a complaint — but if you use
            either feature, the text you type is stored, whether or not you're logged in. A
            complaint draft stores your name, address, phone number, and everything else you
            enter in the form, in full, exactly as typed.
          </p>
          <p>
            If you create an account, we also store your email, name, phone number, and the
            state/district you tell us, along with your password (never in plain text — it's
            hashed with argon2, an algorithm designed so the original password can't be
            recovered from what we store).
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Before your question reaches our AI model</h2>
        <div className={styles.prose}>
          <p>
            We run every question and complaint through a detector that removes common personal
            details — phone numbers, email addresses, Aadhaar and PAN numbers, vehicle
            registrations, and case/FIR numbers — before it's sent to the AI model that generates
            the answer, and puts your real details back only in the answer shown to you.
          </p>
          <div className={styles.callout}>
            <strong>This detection isn't perfect.</strong> Fixed-format details like phone numbers
            work reliably. Names and addresses are only caught when they follow a phrase like
            "my name is" or "residing at" — a name mentioned without one of those cues can pass
            through untouched. Please avoid including a full name or address you don't need to
            share, especially someone else's.
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Who else sees this data</h2>
        <div className={styles.prose}>
          <ul>
            <li>
              <strong>Groq</strong>, to generate the answer or draft — with the redaction above
              applied first.
            </li>
            <li>
              <strong>Neon</strong> and <strong>Render</strong>, who host our database and
              backend — they store and process the data as our infrastructure providers, not for
              their own purposes.
            </li>
          </ul>
          <p>
            We never sell your data, and we don't run advertising or tracking of any kind on this
            site.
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>How long we keep it</h2>
        <div className={styles.prose}>
          <p>
            Our target is 12 months for question history and 24 months for complaint drafts (so
            you can still come back for one), but we'll be honest that automatic deletion isn't
            built yet for either — today, deleting something you submitted means asking us
            directly (see below).
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Your rights</h2>
        <div className={styles.prose}>
          <p>
            You can ask us what we have stored about you, ask us to correct it, or ask us to
            delete it. Right now that's a manual request rather than a button in the app — a
            self-service option is planned. To make a request, open an issue on this project's
            GitHub repository describing what you submitted and roughly when; we'll locate and
            action it manually. This project is an academic one, not currently a live public
            service, so a formal, published grievance-officer contact isn't in place yet — see
            the full compliance note below for why.
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>The full technical version</h2>
        <div className={styles.prose}>
          <p>
            This page is a plain-language summary. The complete, more technical version — lawful
            basis, exact retention targets, breach process, and what's genuinely automated versus
            manual today — is documented in this project's public repository under{" "}
            <code>docs/dpdp-compliance.md</code>.
          </p>
        </div>
      </section>
    </main>
  );
}
