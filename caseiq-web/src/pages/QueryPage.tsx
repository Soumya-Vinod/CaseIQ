import { useState } from "react";
import { api } from "../api/client";
import type { QueryOut } from "../api/types";
import { AbstentionCard } from "../components/AbstentionCard";
import { SourcesPanel } from "../components/SourcesPanel";
import styles from "./QueryPage.module.css";

export function QueryPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryOut | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);
    try {
      const { data, error: apiError } = await api.POST("/api/v1/legal/query", {
        body: { query: trimmed },
      });
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
        <p className={styles.eyebrow}>Indian Law, Cited</p>
        <h1 className={styles.title}>Ask a legal question</h1>
        <p className={styles.subtitle}>
          Answers are grounded in the actual text of BNS, BNSS, BSA, IPC and CrPC — every answer
          cites the section it came from.
        </p>
      </header>

      <form className={styles.form} onSubmit={handleSubmit}>
        <textarea
          className={styles.textarea}
          placeholder="e.g. What are my rights if I'm arrested without a warrant?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={2000}
        />
        <div className={styles.submitRow}>
          <button className={styles.submit} type="submit" disabled={loading || !query.trim()}>
            {loading ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>

      {error && <div className={styles.errorBox}>{error}</div>}
      {loading && <p className={styles.loading}>Searching the corpus…</p>}

      {result && result.abstained && (
        <section className={styles.sourcesSection}>
          <AbstentionCard
            message={result.conversational_summary}
            confidence={result.confidence_score}
          />
        </section>
      )}

      {result && !result.abstained && (
        <>
          <section className={styles.answer}>
            <p className={styles.confidence}>
              Confidence <span className={styles.confidenceValue}>{Math.round(result.confidence_score * 100)}%</span>
            </p>
            <p className={styles.summary}>{result.conversational_summary}</p>
          </section>

          <section className={styles.sourcesSection}>
            <SourcesPanel sections={result.legal_sections} />
          </section>
        </>
      )}
    </main>
  );
}
