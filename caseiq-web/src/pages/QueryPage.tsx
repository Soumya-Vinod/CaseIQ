import { useState } from "react";
import { api } from "../api/client";
import type { QueryOut } from "../api/types";
import { AbstentionCard } from "../components/AbstentionCard";
import { AnswerBriefing } from "../components/AnswerBriefing";
import { HelplineStrip } from "../components/HelplineStrip";
import { IncidentDatePrompt } from "../components/IncidentDatePrompt";
import { RelatedQuestions } from "../components/RelatedQuestions";
import { SourcesPanel } from "../components/SourcesPanel";
import { useAuth } from "../contexts/AuthContext";
import { getSessionId } from "../utils/session";
import styles from "./QueryPage.module.css";

// Verified against live retrieval before being put here. The original three
// (2026-08-31) were chosen specifically to EXCLUDE "how do I file an FIR"
// and anything dowry-related -- both were known misses under LocalEmbedder
// at the time (see docs/evaluation.md). The embedding swap to
// LocalOnnxEmbedder (2026-09-06) fixed exactly that gap -- re-verified
// end-to-end against a local backend with the corrected corpus before
// adding them here, not assumed from the retrieval-only numbers alone:
// "file an FIR" now cites CrPC 154/BNSS 173 (the actual FIR sections, old
// and new regime) at confidence 0.49; "dowry harassment" cites IPC 498A at
// rank 1, confidence 0.67. Two of the system's better demonstrations now,
// not queries to avoid.
const EXAMPLE_QUESTIONS = [
  "What is the punishment for theft?",
  "What is the punishment for defamation?",
  "What is the punishment for murder?",
  "How do I file an FIR for a stolen phone?",
  "What is the punishment for dowry harassment?",
];

export function QueryPage() {
  const { user } = useAuth();
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
            // FIXED 2026-09-07: hardcoded "en" for every request, guest or
            // logged-in -- fine for a guest (the backend already
            // auto-detects per query whenever the incoming value IS "en",
            // see app.api.v1.legal.process_query), but meant a logged-in
            // user's own `preferred_language` (settable via the profile
            // page's preferences section) could never actually change
            // anything. This is an OVERRIDE of auto-detect, not a
            // replacement for it: a guest, or a logged-in user who's never
            // set a preference, still gets "en" here and full per-query
            // detection exactly as before -- only an explicitly-set
            // preference (anything other than the "en" default) skips
            // detection and forces that language directly.
            language: user?.preferred_language ?? "en",
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