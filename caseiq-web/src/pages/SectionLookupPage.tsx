import { useState } from "react";
import { api } from "../api/client";
import type { SectionDetailOut } from "../api/types";
import { JudicialStatusBadge } from "../components/JudicialStatusBadge";
import { isRedundantTitle } from "../utils/text";
import styles from "./SectionLookupPage.module.css";

const ACTS = ["BNS", "BNSS", "BSA", "IPC", "CrPC"];

/**
 * The direct act+section lookup — the one read path that's allowed to
 * surface a struck-down section rather than excluding it (K2's hard rule
 * excludes struck_down from every other path, including ordinary /legal/query
 * results). This is deliberately a separate, explicit route: you have to ask
 * for a specific provision by name to see that it's dead law.
 */
export function SectionLookupPage() {
  const [act, setAct] = useState("IPC");
  const [sectionNumber, setSectionNumber] = useState("497");
  const [loading, setLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SectionDetailOut | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!sectionNumber.trim() || loading) return;
    setLoading(true);
    setNotFound(false);
    setError(null);
    setResult(null);
    try {
      const { data, error: apiError, response } = await api.GET(
        "/api/v1/knowledge/sections/{act}/{section_number}",
        { params: { path: { act, section_number: sectionNumber.trim() } } },
      );
      if (response.status === 404) {
        setNotFound(true);
        return;
      }
      if (apiError) {
        setError("Something went wrong reaching the backend. Please try again.");
        return;
      }
      setResult(data);
    } catch {
      setError("Could not reach the server. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Exact citation</p>
        <h1 className={styles.title}>Look up a specific section</h1>
        <p className={styles.subtitle}>
          The one place a struck-down or read-down provision is shown directly, rather than
          excluded — so you can see it's dead law instead of finding nothing.
        </p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      <form className={styles.form} onSubmit={handleSubmit}>
        <select className={styles.select} value={act} onChange={(e) => setAct(e.target.value)}>
          {ACTS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <input
          className={styles.input}
          value={sectionNumber}
          onChange={(e) => setSectionNumber(e.target.value)}
          placeholder="Section number, e.g. 497"
        />
        <button className={styles.submit} type="submit" disabled={loading}>
          {loading ? "Looking up…" : "Look up"}
        </button>
      </form>

      {loading && <p className={styles.loading}>Looking up…</p>}
      {error && <div className={styles.errorBox}>{error}</div>}
      {notFound && <p className={styles.notFound}>No section {sectionNumber} found in {act}.</p>}

      {result && (
        <article className={styles.result}>
          <div className={styles.locus}>
            <span className={styles.act}>{act}</span>
            <span className={styles.sectionNo}>§ {result.section}</span>
          </div>
          {result.title && !isRedundantTitle(result.title, result.section_text) && (
            <h3 className={styles.title2}>{result.title}</h3>
          )}

          {result.judicial_status && (
            <div className={styles.statusRow}>
              <JudicialStatusBadge status={result.judicial_status} />
            </div>
          )}

          <p className={styles.text}>{result.section_text}</p>
        </article>
      )}
    </main>
  );
}
