import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { QueryOut } from "../api/types";
import { AbstentionCard } from "../components/AbstentionCard";
import { AnswerBriefing } from "../components/AnswerBriefing";
import { HelplineStrip } from "../components/HelplineStrip";
import { IncidentDatePrompt } from "../components/IncidentDatePrompt";
import { RelatedQuestions } from "../components/RelatedQuestions";
import { SourcesPanel } from "../components/SourcesPanel";
import { useAuth } from "../contexts/AuthContext";
import { getSessionId, resetSessionId } from "../utils/session";
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

interface Turn {
  id: string;
  query: string;
  result: QueryOut;
}

export function QueryPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Per-turn thread, not a single replaced `result` (docs/evaluation.md,
  // "Defamation, first turn" entry's own follow-on UI-restructure scoping):
  // the previous single-`result` shape meant every new answer silently
  // erased the one before it, so there was no way to see what you'd already
  // asked in this session -- the exact condition ("stale history from
  // repeated same-session testing, but no visible record of what that
  // history actually was") that made tonight's bug hard to reason about
  // live. Each entry keeps the question that produced it alongside the
  // answer, so the thread itself is the record.
  const [turns, setTurns] = useState<Turn[]>([]);
  const threadEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [turns.length, loading]);

  async function runQuery(
    text: string,
    opts?: { incidentDate?: string; skipIncidentDate?: boolean; replaceLastTurn?: boolean },
  ) {
    if (!text.trim() || loading) return;

    setLoading(true);
    setError(null);

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

      // An incident-date prompt is a step within one logical question, not
      // a second question -- replace the turn it belongs to rather than
      // appending a new one, so answering "yes, it happened on..." doesn't
      // leave the prompt sitting in the thread above its own answer.
      const turn: Turn = { id: crypto.randomUUID(), query: text.trim(), result: data };
      setTurns((prev) =>
        opts?.replaceLastTurn ? [...prev.slice(0, -1), turn] : [...prev, turn],
      );
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
    const text = query;
    setQuery("");
    void runQuery(text);
  }

  function handleExample(q: string) {
    void runQuery(q);
  }

  function handleFollowUp(q: string) {
    void runQuery(q);
  }

  // Wires the already-existing resetSessionId() (built for logout/account
  // deletion, see utils/session.ts) to a visible control -- the backend
  // half of "new conversation" was already there; this is the button that
  // was missing, and the thing that would have prevented tonight's bug
  // (stale same-session history driving is_new_topic's follow-up
  // misclassification on a question the user considered a fresh start).
  function handleNewConversation() {
    resetSessionId();
    setTurns([]);
    setQuery("");
    setError(null);
  }

  const lastTurn = turns[turns.length - 1];
  const awaitingIncidentDate = Boolean(lastTurn?.result.needs_incident_date) && !loading;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerRow}>
          <div>
            <p className={styles.eyebrow}>Indian Law, Cited</p>
            <h1 className={styles.title}>Ask a legal question</h1>
          </div>

          {turns.length > 0 && (
            <button
              type="button"
              className={styles.newConversation}
              onClick={handleNewConversation}
            >
              New conversation
            </button>
          )}
        </div>

        <p className={styles.subtitle}>
          Answers are grounded in the actual text of BNS, BNSS, BSA, IPC and
          CrPC — five criminal statutes, every answer cites the section it
          came from.
        </p>
      </header>

      <div className={styles.rule} aria-hidden="true" />

      {turns.length === 0 && !loading && !error && (
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

      {turns.length > 0 && (
        <div className={styles.thread}>
          {turns.map((turn, i) => (
            <TurnBlock
              key={turn.id}
              turn={turn}
              isNewest={i === turns.length - 1}
              loading={loading}
              onSubmitIncidentDate={(d) =>
                void runQuery(turn.query, { incidentDate: d, replaceLastTurn: true })
              }
              onSkipIncidentDate={() =>
                void runQuery(turn.query, { skipIncidentDate: true, replaceLastTurn: true })
              }
              onFollowUp={handleFollowUp}
            />
          ))}
        </div>
      )}

      {error && <div className={styles.errorBox}>{error}</div>}
      {loading && <p className={styles.loading}>Searching the corpus…</p>}

      <div ref={threadEndRef} />

      <form className={styles.form} onSubmit={handleSubmit}>
        <textarea
          className={styles.textarea}
          placeholder="e.g. What is the punishment for theft?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={2000}
          disabled={awaitingIncidentDate}
        />

        <div className={styles.submitRow}>
          <button
            className={styles.submit}
            type="submit"
            disabled={loading || !query.trim() || awaitingIncidentDate}
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
    </main>
  );
}

// REVERTED (per instruction, 2026-09-24): sources collapsing into each turn
// was the wrong call -- the two-column briefing/sources layout is the
// product, not a search-results stack, and collapsing it lost that.
// Restored verbatim (resultsGrid, two columns, sources always visible
// alongside the briefing). What's new instead is turn-level collapse: only
// the NEWEST turn always renders its full two-column body; every older
// turn shows just its question by default, with a click to fold it back
// open for review, rather than flattening or hiding any one turn's own
// internal layout.
function TurnBlock({
  turn,
  isNewest,
  loading,
  onSubmitIncidentDate,
  onSkipIncidentDate,
  onFollowUp,
}: {
  turn: Turn;
  isNewest: boolean;
  loading: boolean;
  onSubmitIncidentDate: (date: string) => void;
  onSkipIncidentDate: () => void;
  onFollowUp: (q: string) => void;
}) {
  const { result } = turn;
  // `null` means "no manual override yet" -- deliberately NOT seeded from
  // `isNewest` at mount (that would freeze the value the instant a turn is
  // created, when it's always newest, and never auto-collapse it once a
  // later turn takes over). Recomputing `expanded` from the live `isNewest`
  // prop every render is what makes an older turn collapse automatically
  // the moment it stops being newest, while still letting a user who
  // clicked to review an older turn keep it open across further turns.
  const [expandOverride, setExpandOverride] = useState<boolean | null>(null);
  const expanded = isNewest || (expandOverride ?? false);

  return (
    <article className={styles.turn}>
      {isNewest ? (
        <p className={styles.turnQuery}>{turn.query}</p>
      ) : (
        <button
          type="button"
          className={styles.turnQueryButton}
          onClick={() => setExpandOverride((o) => !(o ?? false))}
          aria-expanded={expanded}
        >
          <span className={styles.turnQueryText}>{turn.query}</span>
          <span className={styles.turnQueryToggleIcon} aria-hidden="true">
            {expanded ? "▾" : "▸"}
          </span>
        </button>
      )}

      {expanded && (
        <>
          {result.needs_incident_date && (
            <section className={styles.sourcesSection}>
              <IncidentDatePrompt
                message={result.conversational_summary}
                disabled={loading}
                onSubmitDate={onSubmitIncidentDate}
                onSkip={onSkipIncidentDate}
              />
            </section>
          )}

          {!result.needs_incident_date && result.abstained && (
            <section className={styles.sourcesSection}>
              <AbstentionCard
                message={result.conversational_summary}
                confidence={result.confidence_score}
                helplines={result.helplines}
              />
            </section>
          )}

          {!result.needs_incident_date && !result.abstained && (
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
                        onSelect={onFollowUp}
                        disabled={loading}
                      />
                    </section>
                  )}
                </div>

                <div className={styles.resultsRight}>
                  <section className={styles.sourcesSection}>
                    <SourcesPanel
                      sections={result.legal_sections}
                      carriedForward={result.sections_carried_forward}
                    />
                  </section>
                </div>
              </div>

              <div className={styles.helplineRow}>
                <HelplineStrip helplines={result.helplines} />
              </div>
            </>
          )}

          {result.corpus_version_id && (
            <p className={styles.turnMeta}>
              Corpus version {result.corpus_version_id.slice(0, 8)}
            </p>
          )}
        </>
      )}
    </article>
  );
}
