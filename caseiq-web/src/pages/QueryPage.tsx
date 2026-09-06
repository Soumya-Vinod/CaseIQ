import { useState } from "react";
import { api } from "../api/client";
import type { QueryOut } from "../api/types";
import { AbstentionCard } from "../components/AbstentionCard";
import { AnswerBriefing } from "../components/AnswerBriefing";
import { HelplineStrip } from "../components/HelplineStrip";
import { IncidentDatePrompt } from "../components/IncidentDatePrompt";
import { RelatedQuestions } from "../components/RelatedQuestions";
import { SourcesPanel } from "../components/SourcesPanel";
import { getSessionId } from "../utils/session";
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

  // The text a needs_incident_date prompt is waiting on an answer for.
  const [pendingQuery, setPendingQuery] = useState("");

  async function runQuery(
    text: string,
    opts?: { incidentDate?: string; skipIncidentDate?: boolean },
  ) {
    if (!text.trim() || loading) return;

    setLoading(true);
    setError(null);
    setPendingQuery(text);

    try {
      const { data, error: apiError } = await api.POST(
        "/api/v1/legal/query",
        {
          body: {
            query: text.trim(),
            language: "en",
            // FIXED 2026-09-06: this was hardcoded "" -- and the backend's
            // own follow-up mechanism (app.api.v1.legal._history) returns
            // no history at all for an empty session_id, so no user of the
            // deployed app has ever gotten real multi-turn continuity. One
            // stable id per tab, independent of login. See utils/session.ts.
            session_id: getSessionId(),
            incident_date: opts?.incidentDate ?? null,
            // FIXED 2026-09-04: this previously defaulted to
            // `!opts?.incidentDate`, which is true whenever opts is
            // unset -- i.e. every ordinary first-time query, not just an
            // explicit "I don't know" skip. That made every plain answer
            // append the C8 both-regimes note regardless of whether a
            // date was ever relevant. Only the IncidentDatePrompt's own
            // "I don't know" button should ever set this true.
            skip_incident_date: opts?.skipIncidentDate ?? false,
          },
        },
      );

      if (apiError) {
        setError(
          "Something went wrong reaching the backend. Please try again.",
        );
        return;
      }

      setResult(data);
    } catch {
      setError(
        "Could not reach the server. Check your connection and try again.",
      );
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
          Answers are grounded in the actual text of BNS, BNSS, BSA, IPC and
          CrPC — five criminal statutes, every answer cites the section it
          came from.
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
          <button
            className={styles.submit}
            type="submit"
            disabled={loading || !query.trim()}
          >
            {loading ? "Asking…" : "Ask"}
          </button>
        </div>

        <p className={styles.privacyNote}>
          CaseIQ detects and removes common personal details (phone numbers, email
          addresses, Aadhaar/PAN numbers, and similar) before your question reaches our
          AI model. This detection isn't perfect, especially for names and addresses —
          please avoid including a full name or address you don't need to share.
        </p>
      </form>

      {!result && !loading && !error && (
        <div className={styles.examples}>
          <p className={styles.examplesLabel}>Try one of these</p>

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

      {loading && (
        <p className={styles.loading}>Searching the corpus…</p>
      )}

      {result && result.needs_incident_date && (
        <section className={styles.sourcesSection}>
          <IncidentDatePrompt
            message={result.conversational_summary}
            disabled={loading}
            onSubmitDate={(d) =>
              void runQuery(pendingQuery, {
                incidentDate: d,
              })
            }
            onSkip={() =>
              void runQuery(pendingQuery, {
                skipIncidentDate: true,
              })
            }
          />
        </section>
      )}

      {result && !result.needs_incident_date && result.abstained && (
        <section className={styles.sourcesSection}>
          <AbstentionCard
            message={result.conversational_summary}
            confidence={result.confidence_score}
            helplines={result.helplines}
          />
        </section>
      )}

      {result &&
        !result.needs_incident_date &&
        !result.abstained && (
          <>
            {/* Briefing left, sources right at wide viewports -- the two
                halves of an answer someone reads together, not one after
                the other; collapses to the same stacked single column as
                before once there's no room to set them side by side. */}
            <div className={styles.resultsGrid}>
              <div className={styles.resultsLeft}>
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
              </div>

              <div className={styles.resultsRight}>
                <section className={styles.sourcesSection}>
                  <SourcesPanel sections={result.legal_sections} />
                </section>
              </div>
            </div>

            <div className={styles.helplineRow}>
              <HelplineStrip helplines={result.helplines} />
            </div>
          </>
        )}

      {result && (
        <footer className={styles.pageFooter}>
          {result.corpus_version_id && (
            <span>
              Corpus version {result.corpus_version_id.slice(0, 8)}
            </span>
          )}
        </footer>
      )}
    </main>
  );
}