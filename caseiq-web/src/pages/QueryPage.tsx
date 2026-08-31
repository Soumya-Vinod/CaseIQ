import { useState } from "react";
import { api } from "../api/client";
import type { QueryOut } from "../api/types";
import { AbstentionCard } from "../components/AbstentionCard";
import { AnswerBriefing } from "../components/AnswerBriefing";
import { RelatedQuestions } from "../components/RelatedQuestions";
import { SourcesPanel } from "../components/SourcesPanel";
import styles from "./QueryPage.module.css";

// Verified against live retrieval before being put here (2026-08-31): all
// three return their correct section in the top 6. Deliberately NOT "how do
// I file an FIR" or anything dowry-related -- both are known misses
// documented in docs/evaluation.md, and a landing-page example has to work.
const EXAMPLE_QUESTIONS = [
  "What is the punishment for theft?",
  "What is the punishment for defamation?",
  "What is the punishment for murder?",
];

export function QueryPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryOut | null>(null);

  async function runQuery(text: string) {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const { data, error: apiError } = await api.POST("/api/v1/legal/query", {
        // language/session_id are optional server-side (Pydantic defaults) but
        // openapi-typescript emits fields with a `default` as required-with-default,
        // not optional -- supplying the same defaults explicitly here satisfies
        // the generated type without fighting the generator.
        body: { query: text.trim(), language: "en", session_id: "" },
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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void runQuery(query);
  }

  function handleExample(q: string) {
    setQuery(q);
    void runQuery(q);
  }

  function handleFollowUp(q: string) {
    setQuery(q);
    void runQuery(q);
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Indian Law, Cited</p>
        <h1 className={styles.title}>Ask a legal question</h1>
        <p className={styles.subtitle}>
          Answers are grounded in the actual text of BNS, BNSS, BSA, IPC and CrPC — five criminal
          statutes, every answer cites the section it came from.
        </p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      <form className={styles.form} onSubmit={handleSubmit}>
        <textarea
          className={styles.textarea}
          placeholder="e.g. What is the punishment for theft?"
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

      {!result && !loading && !error && (
        <div className={styles.examples}>
          <p className={styles.examplesLabel}>Try one of these — verified to answer correctly:</p>
          <div className={styles.exampleList}>
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                className={styles.exampleButton}
                onClick={() => handleExample(q)}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

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
            <AnswerBriefing result={result} />
          </section>

          {result.related_questions.length > 0 && (
            <section className={styles.relatedSection}>
              <RelatedQuestions
                questions={result.related_questions}
                onSelect={handleFollowUp}
                disabled={loading}
              />
            </section>
          )}

          <section className={styles.sourcesSection}>
            <SourcesPanel sections={result.legal_sections} />
          </section>
        </>
      )}

      {result && (
        <footer className={styles.pageFooter}>
          {result.corpus_version_id && (
            <span>Corpus version {result.corpus_version_id.slice(0, 8)}</span>
          )}
        </footer>
      )}
    </main>
  );
}
