import { useState } from "react";
import { SectionDetailSheet } from "../components/SectionDetailSheet";
import styles from "./RightsOnArrestPage.module.css";

/**
 * "Your rights on arrest" -- a reference card, not a Q&A. Five rights,
 * each one BNSS's own words, no LLM anywhere in this page. The survey
 * finding this serves: 70% of respondents wanted to learn their rights
 * generally, not solve a specific problem -- so this is reachable without
 * typing a question at all.
 *
 * Every quote below is a verified, exact substring of the live
 * section_text for that section (checked directly against the corpus
 * before this was written, not transcribed from memory) -- BNSS's own
 * ingestion carries a column-interleaving artifact (short marginal-note
 * fragments injected mid-sentence into the body text, the same root cause
 * as marginal_note being empty for every BNSS section -- see
 * docs/evaluation.md), so each quote is a hand-picked CONTIGUOUS clean
 * span, never a splice across an interruption and never the raw
 * interleaved text verbatim. Tapping through opens the same
 * SectionDetailSheet every other screen uses, which fetches the section
 * fresh -- if the corpus is ever re-ingested cleanly, the full text there
 * updates on its own; only this card's short excerpt is fixed.
 */
const RIGHTS = [
  {
    act: "BNSS",
    section: "47",
    label: "The grounds of your arrest must be told to you",
    detail:
      "Communicated immediately, not after questioning has started -- and if you're accused of a bailable offence, you must also be told you have a right to bail.",
    quote: "full particulars of the offence for which he is arrested",
  },
  {
    act: "BNSS",
    section: "48",
    label: "A relative or friend must be informed of your arrest",
    detail:
      "The police must tell someone you name -- and where you're being held -- as soon as you're brought to the station, and record who was told.",
    quote:
      "give the information regarding such arrest and place where the arrested person is",
  },
  {
    act: "BNSS",
    section: "58",
    label: "You must be produced before a magistrate within 24 hours",
    detail:
      "Detention beyond 24 hours (excluding travel time to court) needs a magistrate's own order -- police custody alone cannot extend it.",
    quote:
      "exceed more than twenty-four hours exclusive of the time necessary for the journey from the place of arrest",
  },
  {
    act: "BNSS",
    section: "38",
    label: "You can meet a lawyer of your choice during interrogation",
    detail:
      "Not throughout continuous questioning, but the right to meet your own advocate during it is explicit, not implied.",
    quote:
      "to meet an advocate of his choice during interrogation, though not throughout interrogation.",
  },
  {
    act: "BNSS",
    section: "53",
    label: "You have a right to a medical examination",
    detail:
      "A medical officer must examine you soon after arrest and record any injuries -- and if you're a woman, that examination must be done by or under a female medical officer.",
    quote: "When any person is arrested, he shall be examined by a medical officer",
  },
] as const;

export function RightsOnArrestPage() {
  const [detail, setDetail] = useState<{ act: string; section: string } | null>(null);
  const [triggerEl, setTriggerEl] = useState<HTMLElement | null>(null);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Your rights</p>
        <h1 className={styles.title}>Your rights on arrest</h1>
        <p className={styles.subtitle}>
          Five rights that apply the moment you're arrested, in BNSS's own words -- not a
          summary of what a question-and-answer session happened to cover. No model wrote any of
          this; every quote below is checked directly against the statute.
        </p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      <ol className={styles.list}>
        {RIGHTS.map((r) => (
          <li key={r.section}>
            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <span className={styles.act}>{r.act}</span>
                <span className={styles.sectionNo}>§ {r.section}</span>
              </div>
              <h2 className={styles.label}>{r.label}</h2>
              <p className={styles.detail}>{r.detail}</p>
              <blockquote className={styles.quote}>&ldquo;{r.quote}&hellip;&rdquo;</blockquote>
              <button
                type="button"
                className={styles.viewDetail}
                onClick={(e) => {
                  setTriggerEl(e.currentTarget);
                  setDetail({ act: r.act, section: r.section });
                }}
              >
                Read the full section →
              </button>
            </article>
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
    </main>
  );
}
