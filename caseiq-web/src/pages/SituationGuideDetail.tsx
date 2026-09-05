import { useState } from "react";
import { SectionDetailSheet } from "../components/SectionDetailSheet";
import type { SituationGuide } from "../data/situationGuides";
import styles from "./SituationGuideDetail.module.css";

export function SituationGuideDetail({
  guide,
  onBack,
}: {
  guide: SituationGuide;
  onBack: () => void;
}) {
  const [detail, setDetail] = useState<{ act: string; section: string } | null>(null);
  const [triggerEl, setTriggerEl] = useState<HTMLElement | null>(null);

  function openSection(e: React.MouseEvent<HTMLButtonElement>, act: string, section: string) {
    setTriggerEl(e.currentTarget);
    setDetail({ act, section });
  }

  return (
    <main className={styles.page}>
      <button type="button" className={styles.backLink} onClick={onBack}>
        ← All situation guides
      </button>

      <header className={styles.header}>
        <p className={styles.eyebrow}>{guide.eyebrow}</p>
        <h1 className={styles.title}>{guide.title}</h1>
        <p className={styles.subtitle}>{guide.subtitle}</p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      {/* Fix 4: what this page is for, in one line, before anything else --
          so someone landing from the list knows in two seconds whether
          they're in the right place. */}
      <p className={styles.openingLine}>{guide.openingLine}</p>

      {/* Practical guidance -- NOT a statutory quote. Visibly different from
          the entitlement cards below: no act/section badge, a different
          border/background (see .practicalBox), so the provenance
          difference is something you can SEE, not just a sentence claiming
          it. Rendered before any entitlement -- for cruelty specifically,
          before ANY statutory content at all, so 112/181 come first. */}
      {guide.leadCallout && (
        <section className={styles.practicalBox}>
          <h2 className={styles.practicalHeading}>{guide.leadCallout.heading}</h2>
          <p className={styles.practicalNote}>{guide.leadCallout.note}</p>
          {guide.leadCallout.paragraphs.map((p, i) => (
            <p key={i} className={styles.practicalPara}>
              {p}
            </p>
          ))}
        </section>
      )}

      {/* "Does this match what's happening to you?" -- real offence
          definitions, quoted, before the procedural entitlements. Same
          gold/statutory visual language as entitlement cards, just without
          the numbered-step framing (these aren't things to DO, they're
          things to recognise). */}
      {guide.recognition && (
        <section className={styles.section}>
          <p className={styles.intro}>{guide.recognition.intro}</p>
          <ul className={styles.recognitionList}>
            {guide.recognition.items.map((item, i) => (
              <li key={i} className={styles.recognitionCard}>
                <div className={styles.cardHeader}>
                  <span className={styles.act}>{item.act}</span>
                  <span className={styles.sectionNo}>§ {item.section}</span>
                </div>
                <p className={styles.entBody}>{item.label}</p>
                <blockquote className={styles.quote}>&ldquo;{item.quote}&rdquo;</blockquote>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className={styles.section}>
        <h2 className={styles.sectionHeading}>{guide.entitlementsHeading}</h2>
        <p className={styles.intro}>{guide.entitlementsIntro}</p>

        <ol className={styles.entitlementList}>
          {guide.entitlements.map((ent) => (
            <li key={ent.number}>
              <article
                className={`${styles.entitlementCard} ${ent.weighted ? styles.entitlementCardWeighted : ""}`}
              >
                <div className={styles.cardHeader}>
                  <span className={styles.entNumber}>{ent.number}</span>
                  <span className={styles.act}>{ent.act}</span>
                  <span className={styles.sectionNo}>§ {ent.section}</span>
                </div>
                <h3 className={styles.entHeading}>{ent.heading}</h3>
                {ent.body.map((p, i) => (
                  <p key={i} className={styles.entBody}>
                    {p}
                  </p>
                ))}
                <blockquote className={styles.quote}>&ldquo;{ent.quote}&rdquo;</blockquote>
                <button
                  type="button"
                  className={styles.viewDetail}
                  onClick={(e) => openSection(e, ent.act, ent.section)}
                >
                  Read the full section →
                </button>
              </article>

              {/* Zero or more practical tips attached to this specific
                  entitlement -- same "different look" rule as leadCallout. */}
              {guide.practicalTips
                ?.filter((t) => t.afterEntitlement === ent.number)
                .map((t, i) => (
                  <div key={i} className={styles.practicalBox}>
                    <h3 className={styles.practicalHeading}>{t.tip.heading}</h3>
                    <ul className={styles.tipList}>
                      {t.tip.items.map((item, j) => (
                        <li key={j}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
            </li>
          ))}
        </ol>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionHeading}>{guide.refusalHeading}</h2>
        <p className={styles.intro}>{guide.refusalIntro}</p>
        <ul className={styles.refusalBullets}>
          {guide.refusalBullets.map((b, i) => (
            <li key={i}>{b}</li>
          ))}
        </ul>
        <p className={styles.intro}>{guide.refusalOutro}</p>

        <ol className={styles.stepList}>
          {guide.refusalSteps.map((step, i) => (
            <li key={i}>
              <article className={styles.entitlementCard}>
                <div className={styles.cardHeader}>
                  <span className={styles.act}>{step.act}</span>
                  <span className={styles.sectionNo}>§ {step.section}</span>
                </div>
                <h3 className={styles.entHeading}>{step.heading}</h3>
                <p className={styles.entBody}>{step.body}</p>
                <button
                  type="button"
                  className={styles.viewDetail}
                  onClick={(e) => openSection(e, step.act, step.section)}
                >
                  Read the full section →
                </button>
              </article>
            </li>
          ))}
        </ol>
      </section>

      <footer className={styles.closing}>
        {guide.closingNote.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </footer>

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
