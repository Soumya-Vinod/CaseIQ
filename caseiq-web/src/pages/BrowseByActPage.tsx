import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SectionOut } from "../api/types";
import { SectionDetailSheet } from "../components/SectionDetailSheet";
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
  const [act, setAct] = useState("");
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
