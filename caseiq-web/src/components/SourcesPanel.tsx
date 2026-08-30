import type { RetrievedSection } from "../api/types";
import { isRedundantTitle } from "../utils/text";
import { JudicialStatusBadge } from "./JudicialStatusBadge";
import styles from "./SourcesPanel.module.css";

const ACT_LABELS: Record<string, string> = {
  BNS: "Bharatiya Nyaya Sanhita, 2023",
  BNSS: "Bharatiya Nagarik Suraksha Sanhita, 2023",
  BSA: "Bharatiya Sakshya Adhiniyam, 2023",
  IPC: "Indian Penal Code, 1860",
  CrPC: "Code of Criminal Procedure, 1973",
};

/**
 * The centrepiece of the query screen, not a collapsed footer. Statutory
 * text is presented the way a legal document is: sectioned, with the act
 * and section number leading every card, not buried in a snippet.
 */
export function SourcesPanel({ sections }: { sections: RetrievedSection[] }) {
  if (sections.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyTitle}>No cited sections</p>
        <p className={styles.emptyBody}>
          This answer isn't grounded in a specific statutory provision — treat it as general
          context rather than a citation.
        </p>
      </div>
    );
  }

  return (
    <section className={styles.panel} aria-label="Cited sections">
      <h2 className={styles.heading}>
        Sources <span className={styles.count}>{sections.length}</span>
      </h2>
      <ol className={styles.list}>
        {sections.map((s, i) => (
          <li key={`${s.act}-${s.section}-${i}`}>
            <SourceCard section={s} />
          </li>
        ))}
      </ol>
    </section>
  );
}

function SourceCard({ section }: { section: RetrievedSection }) {
  return (
    <article className={styles.card}>
      <header className={styles.cardHeader}>
        <div className={styles.locus}>
          <span className={styles.act}>{section.act}</span>
          <span className={styles.sectionNo}>§ {section.section}</span>
        </div>
        {section.recently_amended && <span className={styles.amendedTag}>Recently amended</span>}
      </header>

      <p className={styles.actFullName}>{ACT_LABELS[section.act] ?? section.act}</p>

      {section.title && !isRedundantTitle(section.title, section.snippet) && (
        <h3 className={styles.title}>{section.title}</h3>
      )}

      {section.judicial_status && (
        <div className={styles.statusRow}>
          <JudicialStatusBadge status={section.judicial_status} />
        </div>
      )}

      <p className={styles.text}>
        {section.snippet}
        {!/[.;”"]\s*$/.test(section.snippet) && <span className={styles.ellipsis}> …</span>}
      </p>

      <footer className={styles.meta}>
        {section.valid_from && <span>In force from {section.valid_from}</span>}
        {section.version_no != null && <span>Version {section.version_no}</span>}
        {section.similarity != null && (
          <span>Relevance {(section.similarity * 100).toFixed(0)}%</span>
        )}
      </footer>
    </article>
  );
}
