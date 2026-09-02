import { useState } from "react";
import type { RetrievedSection } from "../api/types";
import { ACT_LABELS } from "../utils/acts";
import { isRedundantTitle } from "../utils/text";
import { JudicialStatusBadge } from "./JudicialStatusBadge";
import { OFFENCE_ATTR_ACTS, OffenceAttributesBlock } from "./OffenceAttributesBlock";
import { SectionDetailSheet } from "./SectionDetailSheet";
import styles from "./SourcesPanel.module.css";

/**
 * The centrepiece of the query screen, not a collapsed footer. Statutory
 * text is presented the way a legal document is: sectioned, with the act
 * and section number leading every card, not buried in a snippet.
 */
export function SourcesPanel({ sections }: { sections: RetrievedSection[] }) {
  const [detail, setDetail] = useState<{ act: string; section: string } | null>(null);
  const [triggerEl, setTriggerEl] = useState<HTMLElement | null>(null);

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
            <SourceCard
              section={s}
              onViewDetail={(el) => {
                setTriggerEl(el);
                setDetail({ act: s.act, section: s.section });
              }}
            />
          </li>
        ))}
      </ol>

      {detail && (
        <SectionDetailSheet
          act={detail.act}
          section={detail.section}
          triggerEl={triggerEl}
          onClose={() => setDetail(null)}
        />
      )}
    </section>
  );
}

function SourceCard({
  section,
  onViewDetail,
}: {
  section: RetrievedSection;
  onViewDetail: (triggerEl: HTMLElement) => void;
}) {
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

      {OFFENCE_ATTR_ACTS.has(section.act) && (
        <OffenceAttributesBlock attrs={section.offence_attributes} />
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

      <button
        type="button"
        className={styles.viewDetail}
        onClick={(e) => onViewDetail(e.currentTarget)}
      >
        View full details →
      </button>
    </article>
  );
}
