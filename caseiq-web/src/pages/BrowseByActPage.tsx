import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SectionOut } from "../api/types";
import { SectionDetailSheet } from "../components/SectionDetailSheet";
import { getDefaultAct, setDefaultAct } from "../utils/preferences";
import { isRedundantTitle } from "../utils/text";
import styles from "./BrowseByActPage.module.css";

const ACTS = [
  { code: "", label: "All" },
  { code: "BNS", label: "BNS" },
  { code: "BNSS", label: "BNSS" },
  { code: "BSA", label: "BSA" },
  { code: "IPC", label: "IPC" },
  { code: "CrPC", label: "CrPC" },
];

// The endpoint's hard cap (GET /knowledge/sections, limit<=200) — there's no
// pagination beyond this, so "All" across ~2,155 sections only ever shows a
// slice. Said plainly in the UI rather than implying this is the full list.
const LIMIT = 200;

export function BrowseByActPage() {
  // Added 2026-09-07: remembered across visits (client-side only, works
  // for guests -- see utils/preferences.ts and docs/evaluation.md's
  // profile-page entry for why this never needed a server round-trip).
  // Lazy initializer -- read once, on mount, not on every render.
  const [act, setActState] = useState(() => getDefaultAct());
  function setAct(next: string) {
    setActState(next);
    setDefaultAct(next);
  }
  const [search, setSearch] = useState("");
  const [sections, setSections] = useState<SectionOut[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<{ act: string; section: string } | null>(null);
  const [triggerEl, setTriggerEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const handle = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const { data, error: apiError } = await api.GET("/api/v1/knowledge/sections", {
          params: {
            query: {
              act: act || undefined,
              q: search.trim() || undefined,
              limit: LIMIT,
            },
          },
        });
        if (apiError) {
          setError("Something went wrong reaching the backend. Please try again.");
          setSections(null);
          return;
        }
        setSections(data ?? []);
      } catch {
        setError("Could not reach the server. Check your connection and try again.");
        setSections(null);
      } finally {
        setLoading(false);
      }
    }, 300); // debounce so every keystroke doesn't fire a request
    return () => clearTimeout(handle);
  }, [act, search]);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Browse the corpus</p>
        <h1 className={styles.title}>All sections, by act</h1>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      {/* Why this list shows both old and new acts side by side -- the
          question this page itself raises just by listing IPC/CrPC next to
          BNS/BNSS/BSA. Deliberately no section-number correspondence table
          (murder 302->103, etc.): this project already checked whether that
          substrate exists anywhere in the corpus and found it doesn't (BNS's
          own text never mentions IPC section numbers; the one place that
          does, CrPC's First Schedule, is deliberately excluded from
          ingestion -- schedule_exclusion.py), and separately found an
          LLM-guessed `ipc_equivalent` field shipping unverified in
          production before it was removed (docs/evaluation.md, "the
          fabricated mapping this project refused to build was already
          shipping", 2026-09-02). Everything below is grounded in this
          project's own verified act metadata (app/legal_corpus/acts_seed.py)
          -- names and the 1 July 2024 cutover date -- not a number mapping. */}
      <details className={styles.explainer}>
        <summary className={styles.explainerSummary}>Why are old and new acts both here?</summary>
        <div className={styles.explainerBody}>
          <p>
            On 1 July 2024, three new laws replaced three colonial-era ones: Bharatiya Nyaya
            Sanhita (BNS) replaced the Indian Penal Code (IPC); Bharatiya Nagarik Suraksha Sanhita
            (BNSS) replaced the Code of Criminal Procedure (CrPC); Bharatiya Sakshya Adhiniyam
            (BSA) replaced the Indian Evidence Act, 1872.
          </p>
          <p>
            Which one applies to a specific incident depends on when it happened, not on when
            you're reading this. An offence committed before 1 July 2024 is still governed by the
            old law — IPC and CrPC didn't stop applying to cases already open when they were
            repealed. An offence on or after that date falls under BNS and BNSS instead.
          </p>
          <p>
            That's why both are still in this list. If your case was registered before the
            cutover, the section you need is the old one, not the new one.
          </p>
        </div>
      </details>

      <div className={styles.controls}>
        <div className={styles.actRow}>
          {ACTS.map((a) => (
            <button
              key={a.code}
              className={`${styles.actPill} ${act === a.code ? styles.actPillActive : ""}`}
              onClick={() => setAct(a.code)}
            >
              {a.label}
            </button>
          ))}
        </div>
        <input
          className={styles.search}
          placeholder="Search by section title…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading && <p className={styles.loading}>Loading…</p>}
      {error && <div className={styles.errorBox}>{error}</div>}

      {!loading && !error && sections && (
        <>
          <p className={styles.count}>
            Showing {sections.length}
            {sections.length === LIMIT ? `+ (capped at ${LIMIT} per view)` : ""} section
            {sections.length === 1 ? "" : "s"}
            {act && ` in ${act}`}
            {search && ` matching "${search}"`}
          </p>

          {sections.length === 0 ? (
            <p className={styles.empty}>No sections found.</p>
          ) : (
            <ol className={styles.list}>
              {sections.map((s) => {
                const showTitle =
                  s.section_title && !isRedundantTitle(s.section_title, s.section_text);
                return (
                  <li key={s.id}>
                    <article
                      className={styles.card}
                      role="button"
                      tabIndex={0}
                      onClick={(e) => {
                        setTriggerEl(e.currentTarget);
                        setDetail({ act: s.act, section: s.section_number });
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setTriggerEl(e.currentTarget);
                          setDetail({ act: s.act, section: s.section_number });
                        }
                      }}
                    >
                      <div className={styles.cardHeader}>
                        <span className={styles.act}>{s.act}</span>
                        <span className={styles.sectionNo}>§ {s.section_number}</span>
                      </div>
                      {showTitle && <h3 className={styles.title2}>{s.section_title}</h3>}
                      <p className={styles.snippet}>{s.section_text.slice(0, 220)}…</p>
                      {s.keywords?.length > 0 && (
                        <div className={styles.keywords}>
                          {s.keywords.map((kw, i) => (
                            <span key={i} className={styles.keyword}>
                              {String(kw)}
                            </span>
                          ))}
                        </div>
                      )}
                    </article>
                  </li>
                );
              })}
            </ol>
          )}
        </>
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
