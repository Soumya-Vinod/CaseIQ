import type { QueryOut } from "../api/types";
import { nonEmptyArray, nonEmptyString, type StructuredData } from "../api/structuredData";
import styles from "./AnswerBriefing.module.css";

const SEVERITY_LABEL: Record<string, string> = {
  low: "Low severity",
  medium: "Medium severity",
  high: "High severity",
  critical: "Critical",
};

const SEVERITY_VAR: Record<string, string> = {
  low: "var(--severity-low)",
  medium: "var(--severity-medium)",
  high: "var(--severity-high)",
  critical: "var(--struck)",
};

function formatAsOf(iso: string | undefined): string | null {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

/**
 * The answer, then what applies, then what to do -- a briefing, not a chat
 * reply. `structured_data` is untyped and untrusted (see api/structuredData.ts):
 * every block here is optional and renders only when something real is in
 * it, so an abstained or sparse response degrades to just the summary line,
 * never a half-empty section with a heading and nothing under it.
 */
export function AnswerBriefing({ result }: { result: QueryOut }) {
  const sd = (result.structured_data ?? {}) as StructuredData;
  const severityColor = sd.severity ? SEVERITY_VAR[sd.severity] : undefined;
  const severityLabel = sd.severity ? SEVERITY_LABEL[sd.severity] ?? sd.severity : undefined;

  // FIXED 2026-09-15 (docs/evaluation.md, "confident overview, empty
  // laws_applicable"): `?? true` is a deliberate fallback, not a guess --
  // this field didn't exist on responses generated before this fix shipped
  // (a cached/stored one from before still deserves the OLD, un-flagged
  // rendering it was actually correct for at the time, not a retroactive
  // false warning); every response generated from here on always sets it
  // explicitly (backend default is also `true`, but that default exists
  // for the abstention/incident-date short-circuit paths, which never
  // reach this component at all -- see QueryOut's own field docstring).
  const citationsGrounded = result.citations_grounded ?? true;

  const hasWhatApplies = nonEmptyArray(sd.laws_applicable) || nonEmptyArray(sd.punishments);
  const hasWhatToDo =
    nonEmptyArray(sd.immediate_steps) ||
    nonEmptyArray(sd.critical_deadlines) ||
    nonEmptyArray(sd.your_rights) ||
    nonEmptyArray(sd.dos_and_donts?.dos) ||
    nonEmptyArray(sd.dos_and_donts?.donts);

  const asOfLabel = formatAsOf(result.as_of);

  return (
    <section className={styles.briefing}>
      {asOfLabel && <p className={styles.asOf}>Law as it stood on {asOfLabel}</p>}

      {/* sections_carried_forward (docs/evaluation.md, follow-up-continuity entry): this
          turn's own retrieval found nothing -- the sections shown (and cited below) are
          carried forward from the most recent turn in this session that DID retrieve
          something. Deliberately visible, not silent -- per instruction, an answer that
          looks freshly retrieved but isn't is exactly the failure shape this project keeps
          finding. Placed before the summary so it frames the whole answer, not just the
          sources list. */}
      {result.sections_carried_forward && (
        <div className={styles.carriedForwardNotice} role="note">
          <span className={styles.carriedForwardIcon} aria-hidden="true">↩</span>
          <span>
            Continuing from your previous question — the sources below are from that answer,
            not a fresh search for this one.
          </span>
        </div>
      )}

      <div className={styles.topRow}>
        <p className={styles.confidence} title="Raw retrieval similarity, not a probability of correctness -- checked against the 44-pair golden set and found too small and too noisy to calibrate into one (see docs/evaluation.md).">
          Match strength{" "}
          <span className={styles.confidenceValue}>{Math.round(result.confidence_score * 100)}%</span>
        </p>
        {severityLabel && (
          <span
            className={styles.severityBadge}
            style={{ color: severityColor, borderColor: severityColor }}
          >
            {severityLabel}
          </span>
        )}
      </div>

      <div className={styles.answerBlock}>
        <p className={styles.summary}>{result.conversational_summary}</p>
        {nonEmptyString(sd.situation_overview) && (
          <p className={styles.overview}>{sd.situation_overview}</p>
        )}
        {nonEmptyString(sd.severity_reason) && (
          <p className={styles.severityReason}>{sd.severity_reason}</p>
        )}
      </div>

      {/* citations_grounded === false: a real generation happened, but
          nothing in it could be confirmed against the retrieved corpus --
          the backend already suppressed severity/severity_reason and
          reset the confidence score for this same reason (app.services.
          grounding.apply_grounding_check). Without this, "What applies"
          would just silently not render (hasWhatApplies is false too, for
          the same underlying reason) and the summary above would stand
          alone with nothing telling the reader why -- exactly the gap
          this fix exists to close. Rendered even when hasWhatApplies is
          also true in principle (it won't be, in practice, since an empty
          laws_applicable is what makes citations_grounded false) so this
          never depends on staying in sync with that separate check. */}
      {!citationsGrounded && (
        <div className={styles.ungroundedNotice} role="note">
          <span className={styles.ungroundedIcon} aria-hidden="true">⚠</span>
          <span>
            No specific law section could be confirmed for this answer. The summary above
            reflects general legal understanding, not a verified citation -- confirm with a
            lawyer before relying on it.
          </span>
        </div>
      )}

      {hasWhatApplies && (
        <div className={styles.block}>
          <div className={styles.blockHeading}>
            <span className={styles.blockNumber} aria-hidden="true">I</span>
            <h2 className={styles.blockTitle}>What applies</h2>
          </div>

          {nonEmptyArray(sd.laws_applicable) && (
            <ul className={styles.lawList}>
              {sd.laws_applicable.map((law, i) => (
                <li key={i} className={styles.lawItem}>
                  <div className={styles.lawLocus}>
                    {nonEmptyString(law.act) && <span className={styles.actTag}>{law.act}</span>}
                    {nonEmptyString(law.section) && (
                      <span className={styles.sectionTag}>§ {law.section}</span>
                    )}
                  </div>
                  {nonEmptyString(law.title) && <p className={styles.lawTitle}>{law.title}</p>}
                  {nonEmptyString(law.why_applies) && (
                    <p className={styles.lawWhy}>{law.why_applies}</p>
                  )}
                </li>
              ))}
            </ul>
          )}

          {nonEmptyArray(sd.punishments) && (
            <div className={styles.punishGrid}>
              {sd.punishments.map((p, i) => (
                <div key={i} className={styles.punishCard}>
                  {nonEmptyString(p.offence) && (
                    <p className={styles.punishOffence}>{p.offence}</p>
                  )}
                  <div className={styles.punishFields}>
                    {nonEmptyString(p.imprisonment) && (
                      <PunishField label="Imprisonment" value={p.imprisonment} />
                    )}
                    {nonEmptyString(p.fine) && <PunishField label="Fine" value={p.fine} />}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {hasWhatToDo && (
        <div className={styles.block}>
          <div className={styles.blockHeading}>
            <span className={styles.blockNumber} aria-hidden="true">
              {hasWhatApplies ? "II" : "I"}
            </span>
            <h2 className={styles.blockTitle}>What to do</h2>
          </div>

          {nonEmptyArray(sd.immediate_steps) && (
            <ol className={styles.stepList}>
              {sd.immediate_steps.map((step, i) => (
                <li key={i} className={styles.stepItem}>
                  <span className={styles.stepNumber}>{step.step ?? i + 1}</span>
                  <div>
                    {nonEmptyString(step.action) && (
                      <p className={styles.stepAction}>{step.action}</p>
                    )}
                    {nonEmptyString(step.details) && (
                      <p className={styles.stepDetails}>{step.details}</p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}

          {nonEmptyArray(sd.critical_deadlines) && (
            <ul className={styles.deadlineList}>
              {sd.critical_deadlines.map((d, i) => (
                <li key={i} className={styles.deadlineItem}>
                  {nonEmptyString(d.deadline) && (
                    <span className={styles.deadlineTag}>{d.deadline}</span>
                  )}
                  <div>
                    {nonEmptyString(d.what) && <p className={styles.deadlineWhat}>{d.what}</p>}
                    {nonEmptyString(d.consequence) && (
                      <p className={styles.deadlineConsequence}>⚠ {d.consequence}</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {nonEmptyArray(sd.your_rights) && (
            <ul className={styles.rightsList}>
              {sd.your_rights.map((r, i) => (
                <li key={i} className={styles.rightItem}>
                  {nonEmptyString(r.right) && <p className={styles.rightTitle}>{r.right}</p>}
                  {nonEmptyString(r.explanation) && (
                    <p className={styles.rightExplanation}>{r.explanation}</p>
                  )}
                </li>
              ))}
            </ul>
          )}

          {(nonEmptyArray(sd.dos_and_donts?.dos) || nonEmptyArray(sd.dos_and_donts?.donts)) && (
            <div className={styles.dosDontsGrid}>
              {nonEmptyArray(sd.dos_and_donts?.dos) && (
                <DoBox label="Do" items={sd.dos_and_donts!.dos!} kind="do" />
              )}
              {nonEmptyArray(sd.dos_and_donts?.donts) && (
                <DoBox label="Don't" items={sd.dos_and_donts!.donts!} kind="dont" />
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function PunishField({ label, value }: { label: string; value?: string }) {
  return (
    <div className={styles.punishField}>
      <p className={styles.punishLabel}>{label}</p>
      <p className={styles.punishValue}>{value}</p>
    </div>
  );
}

function DoBox({ label, items, kind }: { label: string; items: string[]; kind: "do" | "dont" }) {
  return (
    <div className={`${styles.doBox} ${kind === "do" ? styles.doBoxDo : styles.doBoxDont}`}>
      <p className={styles.doBoxLabel}>{label}</p>
      <ul className={styles.doBoxList}>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
