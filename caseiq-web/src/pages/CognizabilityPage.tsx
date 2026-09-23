import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CognizabilitySearchOut, OffenceAttributesOut } from "../api/types";
import { OffenceAttributesBlock } from "../components/OffenceAttributesBlock";
import { SectionDetailSheet } from "../components/SectionDetailSheet";
import styles from "./CognizabilityPage.module.css";

// offence_attributes.section_number sometimes carries a sub-clause suffix
// e.g. "103(1)" -- real First Schedule structure, but section_versions (and
// therefore GET /knowledge/sections/{act}/{section}, which SectionDetailSheet
// calls) only stores whole-section numbers. Strip it before tapping through,
// same base-number logic as the backend's own join fix (see
// app/services/cognizability.py) -- otherwise this 404s on exactly the rows
// most worth viewing in full.
function baseSectionNumber(sectionNumber: string): string {
  return sectionNumber.replace(/\([^)]*\)$/, "");
}

/**
 * "Can I be arrested for this?" -- pure DB lookup over offence_attributes
 * (CrPC/BNSS First Schedule, C1), never an LLM, never a guess. Search by
 * offence name or section number; every result reuses the exact
 * three-state OffenceAttributesBlock the rest of the app already uses for
 * cognizable/bailable/court, plus a fourth state this page is the first to
 * need: `has_data: false` -- a real section with no row in this table at
 * all, rendered by passing `attrs: null` into that same component (its
 * existing null-case IS that state: "No row in our classification data").
 * Never confused with `cognizable: null` (a real row, genuinely
 * conditional per the schedule's own wording) -- those pass a real attrs
 * object through, this passes null.
 */
export function CognizabilityPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<CognizabilitySearchOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<{ act: string; section: string } | null>(null);
  const [triggerEl, setTriggerEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!query.trim()) {
      setResult(null);
      setError(null);
      return;
    }
    const handle = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const { data, error: apiError } = await api.GET("/api/v1/knowledge/cognizability", {
          params: { query: { q: query.trim() } },
        });
        if (apiError) {
          setError("Something went wrong reaching the backend. Please try again.");
          setResult(null);
          return;
        }
        setResult(data);
      } catch {
        setError("Could not reach the server. Check your connection and try again.");
        setResult(null);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(handle);
  }, [query]);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Arrest &amp; bail</p>
        <h1 className={styles.title}>Can I be arrested for this?</h1>
        <p className={styles.subtitle}>
          Search an offence by name or section number. Cognizable, bailable, and the trying
          court, straight from the CrPC/BNSS First Schedule — a database lookup, not a generated
          answer.
        </p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      <input
        className={styles.search}
        placeholder="e.g. theft, or 302, or 498A"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Search by offence name or section number"
      />

      {/* coverage_note is now computed PER RESPONSE by the backend (see
          app/services/cognizability.py's coverage_note_for()) -- empty/absent
          whenever what's actually on screen is verified data, so this only
          renders when there's a concrete reason to doubt it. Before any
          search, there's no response yet to judge that from, so this shows a
          neutral, number-accurate placeholder rather than either silence
          (which would misleadingly look like "everything's verified") or the
          old static per-response caveat (which is no longer a true
          description of a page that hasn't run a query yet). Not rendered at
          all when there's nothing to say -- .coverageNote has a visible
          border/padding, so an empty string would still show as a blank box. */}
      {(!result || result.coverage_note) && (
        <p className={styles.coverageNote}>
          {result?.coverage_note ??
            "IPC/CrPC cognizable/bailable classification is individually verified for " +
              "398 of 398 sections the First Schedule covers (100%); BNS is near-complete " +
              "(398 of 434 sections)."}
        </p>
      )}

      {loading && <p className={styles.loading}>Searching…</p>}
      {error && <div className={styles.errorBox}>{error}</div>}

      {!loading && !error && result && result.results.length === 0 && (
        <p className={styles.empty}>
          No match in this table for "{result.query}".
          {result.coverage_note
            ? " Given the note above, that may mean it genuinely isn't classified yet, not that it doesn't exist."
            : " That offence doesn't appear to be in this table."}
        </p>
      )}

      {!loading && !error && result && result.results.length > 0 && (
        <ol className={styles.list}>
          {result.results.map((r, i) => (
            <li key={`${r.act}-${r.section_number}-${i}`}>
              <article className={styles.card}>
                <div className={styles.cardHeader}>
                  <span className={styles.act}>{r.act}</span>
                  <span className={styles.sectionNo}>§ {r.section_number}</span>
                </div>
                <h2 className={styles.offenceTitle}>{r.title}</h2>

                {/* has_data:false is the fourth state -- a real section
                    with no row at all, distinct from a real row whose
                    cognizable/bailable is genuinely conditional. Passing
                    null (not the row) is what makes
                    OffenceAttributesBlock render THAT state rather than a
                    resolved or conditional pill. */}
                <OffenceAttributesBlock attrs={r.has_data ? (r as OffenceAttributesOut) : null} />

                <button
                  type="button"
                  className={styles.viewDetail}
                  onClick={(e) => {
                    setTriggerEl(e.currentTarget);
                    setDetail({ act: r.act, section: baseSectionNumber(r.section_number) });
                  }}
                >
                  View full section →
                </button>
              </article>
            </li>
          ))}
        </ol>
      )}

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
