import type { OffenceAttributesOut, RetrievedSection } from "../api/types";
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

      {_OFFENCE_ATTR_ACTS.has(section.act) && (
        <OffenceAttributesRow attrs={section.offence_attributes} />
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

/**
 * C1: three states, never allowed to look alike (see docs/evaluation.md):
 *   1. resolved value -- a clean "Cognizable" / "Non-cognizable" pill
 *   2. conditional -- the schedule's own wording shown verbatim, labelled
 *      as conditional rather than flattened into a guess
 *   3. no row in our data -- stated explicitly. A blank field here would
 *      read as "checked, nothing special" -- worse than the LLM guess this
 *      replaced, since it looks like an answer instead of an admitted gap.
 * Gated to IPC and BNS only: offence_attributes comes from CrPC's First
 * Schedule (act='IPC' -- classifies IPC offences, not CrPC's own procedural
 * sections) and BNSS's equivalent (act='BNS', same relationship). Rendering
 * "no row in our data" for a BNSS/BSA/CrPC citation would misrepresent a
 * class of data never attempted yet as one that was tried and came up
 * empty -- those acts get this block only if their own schedule is ever
 * parsed too.
 */
const _OFFENCE_ATTR_ACTS = new Set(["IPC", "BNS"]);

function OffenceAttributesRow({ attrs }: { attrs: OffenceAttributesOut | null | undefined }) {
  return (
    <div className={styles.offenceAttrs}>
      <p className={styles.offenceAttrsLabel}>Cognizable / bailable / court</p>
      {attrs == null ? (
        <p className={styles.offenceAttrsMissing}>
          No row in our classification data for this section — not verified either way.
        </p>
      ) : (
        <>
          <div className={styles.offenceAttrsPills}>
            <AttrPill label="Cognizable" value={attrs.cognizable} raw={attrs.cognizable_raw} />
            <AttrPill label="Bail" value={attrs.bailable} raw={attrs.bailable_raw} />
            <span className={styles.offenceAttrsCourt}>{attrs.triable_by}</span>
          </div>
          <p className={styles.offenceAttrsSource}>Source: {attrs.source}</p>
        </>
      )}
    </div>
  );
}

function AttrPill({ label, value, raw }: { label: string; value: boolean | null | undefined; raw: string }) {
  if (value == null) {
    return (
      <span className={styles.offenceAttrsConditional} title={raw}>
        {label}: conditional — {raw}
      </span>
    );
  }
  return (
    <span className={styles.offenceAttrsPill}>
      {label}: {value ? "Yes" : "No"}
    </span>
  );
}
