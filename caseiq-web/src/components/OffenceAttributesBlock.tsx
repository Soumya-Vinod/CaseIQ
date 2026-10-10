import type { OffenceAttributesOut, OffenceUnavailableReason } from "../api/types";
import styles from "./OffenceAttributesBlock.module.css";

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
 *
 * Extracted from SourcesPanel once SectionDetailSheet needed the identical
 * treatment -- one definition of the three states, not two that could drift.
 *
 * C1a (a), 2026-10-10: `attrs == null` now carries a reason. "no_data" is
 * state 3 above. "conditional" means the rows exist and the First Schedule
 * classifies the section differently for different cases (IPC 222: bailable
 * under a sentence of less than 10 years, not under a life sentence) -- the
 * backend sends no single value for those, because any one would be wrong for
 * some case. That's the correct answer for the section, so it's worded as an
 * answer, not as missing data.
 */
export const OFFENCE_ATTR_ACTS = new Set(["IPC", "BNS"]);

export function OffenceAttributesBlock({
  attrs,
  unavailableReason,
}: {
  attrs: OffenceAttributesOut | null | undefined;
  unavailableReason?: OffenceUnavailableReason | null;
}) {
  return (
    <div className={styles.offenceAttrs}>
      <p className={styles.offenceAttrsLabel}>Cognizable / bailable / court</p>
      {attrs == null && unavailableReason === "conditional" ? (
        <p className={styles.offenceAttrsDepends}>
          Depends on the circumstances of the offence. The First Schedule classifies this section
          differently for different cases, so there is no single answer to show. Read the section
          text to see which case applies.
        </p>
      ) : attrs == null ? (
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
