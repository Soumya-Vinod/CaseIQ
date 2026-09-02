import type { OffenceAttributesOut } from "../api/types";
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
 */
export const OFFENCE_ATTR_ACTS = new Set(["IPC", "BNS"]);

export function OffenceAttributesBlock({ attrs }: { attrs: OffenceAttributesOut | null | undefined }) {
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
